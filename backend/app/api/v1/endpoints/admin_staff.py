import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.identity import Employee, Role
from app.core.passwords import hash_password
from app.repositories import staff_repo, role_repo, department_repo
from app.services.cp_governance_service import sync_franchisee_staff_to_partners

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Schemas ---

class DepartmentResponse(BaseModel):
    id: int
    name: str
    code: str
    is_active: bool

    model_config = {"from_attributes": True}


class StaffCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    mobile: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = Field(None, max_length=255)
    department_code: str = Field(..., description="Target department code, e.g. SALES, OPERATIONS, MANAGEMENT")
    role_code: str = Field(..., description="Target dynamic role code, e.g. SALES_MANAGER, TELECALLER")


class StaffUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[str] = Field(None, max_length=255)
    mobile: Optional[str] = Field(None, min_length=10, max_length=15)
    department_code: Optional[str] = None
    role_code: Optional[str] = None
    is_active: Optional[bool] = None


class StaffResponse(BaseModel):
    id: int
    employee_id: str
    name: str
    username: Optional[str] = None
    email: Optional[str] = None
    mobile: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    role_code: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Display name e.g. Senior Telecaller")
    code: Optional[str] = Field(None, max_length=50, description="Optional uppercase code e.g. SR_TELECALLER (auto-generated if omitted)")
    department_code: str = Field(..., description="Department code e.g. SALES, OPERATIONS, MANAGEMENT")
    permissions: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Initial module permissions")


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    department_code: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[Dict[str, Any]] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    code: str
    department_id: int
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    permissions: Dict[str, Any]
    is_active: bool
    employee_count: int = 0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UpdatePermissionsRequest(BaseModel):
    permissions: Dict[str, Any] = Field(..., description="Granular module permissions JSON")


# --- DEPARTMENTS ENDPOINT ---

@router.get(
    "/admin/departments",
    response_model=List[DepartmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List all active departments via DepartmentRepository",
)
async def list_departments(
    db: AsyncSession = Depends(get_db),
) -> List[DepartmentResponse]:
    depts = await department_repo.list_active(db)
    return [
        DepartmentResponse(
            id=d.id,
            name=d.name,
            code=d.code,
            is_active=d.is_active,
        )
        for d in depts
    ]


# --- DYNAMIC ROLES CRUD ENDPOINTS ---

@router.get(
    "/admin/roles",
    response_model=List[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="List all dynamic roles via RoleRepository",
)
async def list_roles(
    db: AsyncSession = Depends(get_db),
) -> List[RoleResponse]:
    role_items = await role_repo.list_active_with_counts(db)
    output = []
    for item in role_items:
        r = item["role"]
        output.append(
            RoleResponse(
                id=r.id,
                name=r.name,
                code=r.code,
                department_id=r.department_id,
                department_name=r.department.name if r.department else None,
                department_code=r.department.code if r.department else None,
                permissions=r.permissions or {},
                is_active=r.is_active,
                employee_count=item["employee_count"],
                created_at=r.created_at,
            )
        )
    return output


@router.post(
    "/admin/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new dynamic role via RoleRepository",
)
async def create_role(
    payload: RoleCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    # 1. Normalize code
    if payload.code and payload.code.strip():
        code = re.sub(r'[^A-Z0-9_]', '_', payload.code.strip().upper())
    else:
        code = re.sub(r'[^A-Z0-9_]', '_', payload.name.strip().upper())

    # 2. Check existing
    existing = await role_repo.get_by_code(db, code, include_deleted=True)
    if existing:
        if existing.deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role with code '{code}' already exists.",
            )
        else:
            # Revive previously soft-deleted role
            existing.deleted_at = None
            existing.is_active = True
            existing.name = payload.name.strip()
            existing.permissions = payload.permissions or {}
            await role_repo.update(db, existing)
            return RoleResponse(
                id=existing.id,
                name=existing.name,
                code=existing.code,
                department_id=existing.department_id,
                permissions=existing.permissions or {},
                is_active=existing.is_active,
                employee_count=0,
                created_at=existing.created_at,
            )

    # 3. Resolve department
    dept = await department_repo.get_by_code(db, payload.department_code)
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with code '{payload.department_code}' not found.",
        )

    # 4. Create new Role
    new_role = Role(
        name=payload.name.strip(),
        code=code,
        department_id=dept.id,
        permissions=payload.permissions or {},
        is_active=True,
        deleted_at=None,
    )
    saved_role = await role_repo.create(db, new_role)

    return RoleResponse(
        id=saved_role.id,
        name=saved_role.name,
        code=saved_role.code,
        department_id=dept.id,
        department_name=dept.name,
        department_code=dept.code,
        permissions=saved_role.permissions or {},
        is_active=saved_role.is_active,
        employee_count=0,
        created_at=saved_role.created_at,
    )


@router.put(
    "/admin/roles/{code}",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a dynamic role via RoleRepository",
)
async def update_role(
    code: str,
    payload: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    role = await role_repo.get_by_code(db, code)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with code '{code}' not found.",
        )

    if payload.name is not None and payload.name.strip():
        role.name = payload.name.strip()

    if payload.department_code is not None and payload.department_code.strip():
        dept = await department_repo.get_by_code(db, payload.department_code)
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department '{payload.department_code}' not found.",
            )
        role.department_id = dept.id

    if payload.is_active is not None:
        if code.strip().upper() in ("SUPER_ADMIN", "MD") and not payload.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System role (SUPER_ADMIN) cannot be deactivated.",
            )
        role.is_active = payload.is_active

    if payload.permissions is not None:
        role.permissions = payload.permissions

    updated = await role_repo.update(db, role)
    active_employees = await role_repo.get_assigned_active_employees(db, updated.id)

    return RoleResponse(
        id=updated.id,
        name=updated.name,
        code=updated.code,
        department_id=updated.department_id,
        department_name=updated.department.name if updated.department else None,
        department_code=updated.department.code if updated.department else None,
        permissions=updated.permissions or {},
        is_active=updated.is_active,
        employee_count=len(active_employees),
        created_at=updated.created_at,
    )


@router.delete(
    "/admin/roles/{code}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete a role via RoleRepository",
)
async def delete_role(
    code: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    norm_code = code.strip().upper()
    if norm_code in ("SUPER_ADMIN", "MD"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System roles (SUPER_ADMIN) cannot be deleted.",
        )

    role = await role_repo.get_by_code(db, norm_code)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with code '{code}' not found.",
        )

    active_assigned = await role_repo.get_assigned_active_employees(db, role.id)
    if active_assigned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role '{code}': {len(active_assigned)} active staff member(s) ({', '.join(active_assigned[:3])}) are assigned to it. Please reassign them first.",
        )

    await role_repo.soft_delete(db, role)

    return {
        "status": "success",
        "message": f"Role '{role.name}' ({role.code}) soft-deleted successfully.",
        "deleted_at": role.deleted_at.isoformat() if role.deleted_at else datetime.now(timezone.utc).isoformat(),
    }


@router.put(
    "/admin/roles/{code}/permissions",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update granular module permissions for a role",
)
async def update_role_permissions(
    code: str,
    payload: UpdatePermissionsRequest,
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    role = await role_repo.get_by_code(db, code)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with code '{code}' not found.",
        )

    role.permissions = payload.permissions
    updated = await role_repo.update(db, role)
    active_employees = await role_repo.get_assigned_active_employees(db, updated.id)

    return RoleResponse(
        id=updated.id,
        name=updated.name,
        code=updated.code,
        department_id=updated.department_id,
        department_name=updated.department.name if updated.department else None,
        department_code=updated.department.code if updated.department else None,
        permissions=updated.permissions or {},
        is_active=updated.is_active,
        employee_count=len(active_employees),
        created_at=updated.created_at,
    )


# --- STAFF CRUD ENDPOINTS ---

@router.get(
    "/admin/staff",
    response_model=List[StaffResponse],
    status_code=status.HTTP_200_OK,
    summary="List all active staff members via StaffRepository",
)
async def list_staff(
    db: AsyncSession = Depends(get_db),
) -> List[StaffResponse]:
    employees = await staff_repo.list_active(db)
    output = []
    for emp in employees:
        output.append(
            StaffResponse(
                id=emp.id,
                employee_id=emp.employee_id,
                name=emp.name,
                username=emp.username,
                email=emp.email,
                mobile=emp.mobile,
                department_id=emp.department_id,
                department_name=emp.department.name if emp.department else None,
                role_id=emp.role_id,
                role_name=emp.role.name if emp.role else None,
                role_code=emp.role.code if emp.role else None,
                is_active=emp.is_active,
                created_at=emp.created_at,
            )
        )
    return output


@router.post(
    "/admin/staff",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new staff member via StaffRepository",
)
async def create_staff(
    payload: StaffCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> StaffResponse:
    # 1. Duplicate check
    existing = await staff_repo.check_duplicate(
        db,
        username=payload.username,
        mobile=payload.mobile,
        email=payload.email,
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Staff member with username '{payload.username}', mobile, or email already exists.",
        )

    # 2. Resolve Department
    dept = await department_repo.get_by_code(db, payload.department_code)
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with code '{payload.department_code}' not found.",
        )

    # 3. Resolve Dynamic Role
    role = await role_repo.get_by_code(db, payload.role_code)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with code '{payload.role_code}' not found.",
        )

    # 4. Generate EMP-XXXX ID
    generated_emp_id = await staff_repo.generate_emp_id(db)

    # 5. Create employee
    new_employee = Employee(
        employee_id=generated_emp_id,
        name=payload.name.strip(),
        username=payload.username.strip().lower(),
        password_hash=hash_password(payload.password),
        mobile=payload.mobile.strip(),
        email=payload.email.strip().lower() if payload.email else None,
        department_id=dept.id,
        role_id=role.id,
        is_active=True,
        deleted_at=None,
    )
    saved_emp = await staff_repo.create(db, new_employee)
    if role.code == "FRANCHISEE_AGENT":
        await sync_franchisee_staff_to_partners(db)

    return StaffResponse(
        id=saved_emp.id,
        employee_id=saved_emp.employee_id,
        name=saved_emp.name,
        username=saved_emp.username,
        email=saved_emp.email,
        mobile=saved_emp.mobile,
        department_id=dept.id,
        department_name=dept.name,
        role_id=role.id,
        role_name=role.name,
        role_code=role.code,
        is_active=saved_emp.is_active,
        created_at=saved_emp.created_at,
    )


@router.put(
    "/admin/staff/{employee_id}",
    response_model=StaffResponse,
    status_code=status.HTTP_200_OK,
    summary="Update staff member via StaffRepository",
)
async def update_staff(
    employee_id: str,
    payload: StaffUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> StaffResponse:
    emp = await staff_repo.get_by_emp_id(db, employee_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member with ID '{employee_id}' not found.",
        )

    if payload.name is not None and payload.name.strip():
        emp.name = payload.name.strip()

    if payload.email is not None:
        emp.email = payload.email.strip().lower() if payload.email.strip() else None

    if payload.mobile is not None and payload.mobile.strip():
        emp.mobile = payload.mobile.strip()

    if payload.department_code is not None and payload.department_code.strip():
        dept = await department_repo.get_by_code(db, payload.department_code)
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department '{payload.department_code}' not found.",
            )
        emp.department_id = dept.id

    if payload.role_code is not None and payload.role_code.strip():
        role = await role_repo.get_by_code(db, payload.role_code)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{payload.role_code}' not found.",
            )
        emp.role_id = role.id

    if payload.is_active is not None:
        if (emp.employee_id == "EMP-0001" or (emp.username and emp.username.lower() == "admin")) and not payload.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Primary Administrator (EMP-0001) cannot be deactivated.",
            )
        emp.is_active = payload.is_active

    updated = await staff_repo.update(db, emp)
    await sync_franchisee_staff_to_partners(db)

    return StaffResponse(
        id=updated.id,
        employee_id=updated.employee_id,
        name=updated.name,
        username=updated.username,
        email=updated.email,
        mobile=updated.mobile,
        department_id=updated.department_id,
        department_name=updated.department.name if updated.department else None,
        role_id=updated.role_id,
        role_name=updated.role.name if updated.role else None,
        role_code=updated.role.code if updated.role else None,
        is_active=updated.is_active,
        created_at=updated.created_at,
    )


@router.delete(
    "/admin/staff/{employee_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete a staff member via StaffRepository",
)
async def delete_staff(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    norm_id = employee_id.strip()
    if norm_id in ("EMP-0001", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The root Super Administrator account (EMP-0001) cannot be deleted.",
        )

    emp = await staff_repo.get_by_emp_id(db, norm_id)
    if not emp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member with ID '{employee_id}' not found.",
        )

    if emp.username == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The Super Administrator account cannot be deleted.",
        )

    await staff_repo.soft_delete(db, emp)

    return {
        "status": "success",
        "message": f"Staff member '{emp.name}' ({emp.employee_id}) soft-deleted successfully.",
        "deleted_at": emp.deleted_at.isoformat() if emp.deleted_at else datetime.now(timezone.utc).isoformat(),
    }
