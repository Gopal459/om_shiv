import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.models.identity import Employee, Role, Department
from app.core.passwords import hash_password

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
    summary="List all active departments",
)
async def list_departments(
    db: AsyncSession = Depends(get_db),
) -> List[DepartmentResponse]:
    stmt = (
        select(Department)
        .where(Department.deleted_at.is_(None))
        .order_by(Department.name.asc())
    )
    res = await db.execute(stmt)
    depts = res.scalars().all()
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
    summary="List all dynamic roles and active employee counts",
)
async def list_roles(
    db: AsyncSession = Depends(get_db),
) -> List[RoleResponse]:
    # Query non-deleted roles
    stmt = (
        select(Role)
        .options(selectinload(Role.department), selectinload(Role.employees))
        .where(Role.deleted_at.is_(None))
        .order_by(Role.id.asc())
    )
    res = await db.execute(stmt)
    roles = res.scalars().all()

    # Query active counts per role
    count_stmt = (
        select(Employee.role_id, func.count(Employee.id))
        .where(Employee.deleted_at.is_(None), Employee.is_active.is_(True))
        .group_by(Employee.role_id)
    )
    count_res = await db.execute(count_stmt)
    count_map = {row[0]: row[1] for row in count_res.all()}

    output = []
    for r in roles:
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
                employee_count=count_map.get(r.id, 0),
                created_at=r.created_at,
            )
        )
    return output


@router.post(
    "/admin/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new dynamic role with custom permissions",
)
async def create_role(
    payload: RoleCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    # 1. Generate or normalize code
    if payload.code and payload.code.strip():
        code = re.sub(r'[^A-Z0-9_]', '_', payload.code.strip().upper())
    else:
        code = re.sub(r'[^A-Z0-9_]', '_', payload.name.strip().upper())

    # 2. Check if code already exists and is not deleted
    stmt_check = select(Role).where(Role.code == code)
    res_check = await db.execute(stmt_check)
    existing = res_check.scalar_one_or_none()
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
            await db.commit()
            await db.refresh(existing)
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
    stmt_dept = select(Department).where(
        Department.code == payload.department_code.strip().upper(),
        Department.deleted_at.is_(None),
    )
    res_dept = await db.execute(stmt_dept)
    dept = res_dept.scalar_one_or_none()
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
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)

    return RoleResponse(
        id=new_role.id,
        name=new_role.name,
        code=new_role.code,
        department_id=dept.id,
        department_name=dept.name,
        department_code=dept.code,
        permissions=new_role.permissions or {},
        is_active=new_role.is_active,
        employee_count=0,
        created_at=new_role.created_at,
    )


@router.put(
    "/admin/roles/{code}",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a dynamic role's details, department, or active state",
)
async def update_role(
    code: str,
    payload: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    stmt = (
        select(Role)
        .options(selectinload(Role.department), selectinload(Role.employees))
        .where(Role.code == code.strip().upper(), Role.deleted_at.is_(None))
    )
    res = await db.execute(stmt)
    role = res.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with code '{code}' not found.",
        )

    if payload.name is not None and payload.name.strip():
        role.name = payload.name.strip()

    if payload.department_code is not None and payload.department_code.strip():
        stmt_dept = select(Department).where(
            Department.code == payload.department_code.strip().upper(),
            Department.deleted_at.is_(None),
        )
        res_dept = await db.execute(stmt_dept)
        dept = res_dept.scalar_one_or_none()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department '{payload.department_code}' not found.",
            )
        role.department_id = dept.id

    if payload.is_active is not None:
        role.is_active = payload.is_active

    if payload.permissions is not None:
        role.permissions = payload.permissions

    await db.commit()
    await db.refresh(role)

    active_staff = [e for e in (role.employees or []) if e.deleted_at is None and e.is_active]
    return RoleResponse(
        id=role.id,
        name=role.name,
        code=role.code,
        department_id=role.department_id,
        department_name=role.department.name if role.department else None,
        department_code=role.department.code if role.department else None,
        permissions=role.permissions or {},
        is_active=role.is_active,
        employee_count=len(active_staff),
        created_at=role.created_at,
    )


@router.delete(
    "/admin/roles/{code}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete a role (with safety protection for Super Admin and assigned staff)",
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

    stmt = (
        select(Role)
        .options(selectinload(Role.employees))
        .where(Role.code == norm_code, Role.deleted_at.is_(None))
    )
    res = await db.execute(stmt)
    role = res.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with code '{code}' not found.",
        )

    # Check for active employees assigned to this role
    stmt_emp = select(Employee).where(
        Employee.role_id == role.id,
        Employee.deleted_at.is_(None),
        Employee.is_active.is_(True),
    )
    res_emp = await db.execute(stmt_emp)
    active_assigned = [e.employee_id for e in res_emp.scalars().all()]
    if active_assigned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role '{code}': {len(active_assigned)} active staff member(s) ({', '.join(active_assigned[:3])}) are assigned to it. Please reassign them first.",
        )

    # Soft delete role
    role.deleted_at = datetime.now(timezone.utc)
    role.is_active = False
    await db.commit()

    return {
        "status": "success",
        "message": f"Role '{role.name}' ({role.code}) soft-deleted successfully.",
        "deleted_at": role.deleted_at.isoformat(),
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
    stmt = (
        select(Role)
        .options(selectinload(Role.department), selectinload(Role.employees))
        .where(Role.code == code.strip().upper(), Role.deleted_at.is_(None))
    )
    res = await db.execute(stmt)
    role = res.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with code '{code}' not found.",
        )

    role.permissions = payload.permissions
    await db.commit()
    await db.refresh(role)

    active_staff = [e for e in (role.employees or []) if e.deleted_at is None and e.is_active]
    return RoleResponse(
        id=role.id,
        name=role.name,
        code=role.code,
        department_id=role.department_id,
        department_name=role.department.name if role.department else None,
        department_code=role.department.code if role.department else None,
        permissions=role.permissions or {},
        is_active=role.is_active,
        employee_count=len(active_staff),
        created_at=role.created_at,
    )


# --- STAFF CRUD ENDPOINTS ---

@router.get(
    "/admin/staff",
    response_model=List[StaffResponse],
    status_code=status.HTTP_200_OK,
    summary="List all active staff members and their assigned roles (soft-deleted excluded)",
)
async def list_staff(
    db: AsyncSession = Depends(get_db),
) -> List[StaffResponse]:
    stmt = (
        select(Employee)
        .options(selectinload(Employee.department), selectinload(Employee.role))
        .where(Employee.deleted_at.is_(None))
        .order_by(Employee.id.asc())
    )
    res = await db.execute(stmt)
    employees = res.scalars().all()

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
    summary="Create a new staff member with credentials and dynamic role assignment",
)
async def create_staff(
    payload: StaffCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> StaffResponse:
    # 1. Check for duplicates in username, email, or mobile among non-deleted staff
    conditions = [
        func.lower(Employee.username) == payload.username.strip().lower(),
        Employee.mobile == payload.mobile.strip(),
    ]
    if payload.email:
        conditions.append(func.lower(Employee.email) == payload.email.strip().lower())

    stmt_check = select(Employee).where(Employee.deleted_at.is_(None), or_(*conditions))
    res_check = await db.execute(stmt_check)
    existing = res_check.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Staff member with username '{payload.username}', mobile, or email already exists.",
        )

    # 2. Resolve Department
    stmt_dept = select(Department).where(
        Department.code == payload.department_code.strip().upper(),
        Department.deleted_at.is_(None),
    )
    res_dept = await db.execute(stmt_dept)
    dept = res_dept.scalar_one_or_none()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with code '{payload.department_code}' not found.",
        )

    # 3. Resolve Dynamic Role
    stmt_role = select(Role).where(
        Role.code == payload.role_code.strip().upper(),
        Role.deleted_at.is_(None),
    )
    res_role = await db.execute(stmt_role)
    role = res_role.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with code '{payload.role_code}' not found.",
        )

    # 4. Generate EMP-XXXX sequence
    stmt_count = select(func.count(Employee.id))
    res_count = await db.execute(stmt_count)
    count = res_count.scalar() or 0
    generated_emp_id = f"EMP-{count + 1:04d}"

    # 5. Create employee with hashed password
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
    db.add(new_employee)
    await db.commit()
    await db.refresh(new_employee)

    return StaffResponse(
        id=new_employee.id,
        employee_id=new_employee.employee_id,
        name=new_employee.name,
        username=new_employee.username,
        email=new_employee.email,
        mobile=new_employee.mobile,
        department_id=dept.id,
        department_name=dept.name,
        role_id=role.id,
        role_name=role.name,
        role_code=role.code,
        is_active=new_employee.is_active,
        created_at=new_employee.created_at,
    )


@router.put(
    "/admin/staff/{employee_id}",
    response_model=StaffResponse,
    status_code=status.HTTP_200_OK,
    summary="Update staff member details, department, role, or active status",
)
async def update_staff(
    employee_id: str,
    payload: StaffUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> StaffResponse:
    stmt = (
        select(Employee)
        .options(selectinload(Employee.department), selectinload(Employee.role))
        .where(Employee.employee_id == employee_id.strip(), Employee.deleted_at.is_(None))
    )
    res = await db.execute(stmt)
    emp = res.scalar_one_or_none()
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
        stmt_dept = select(Department).where(
            Department.code == payload.department_code.strip().upper(),
            Department.deleted_at.is_(None),
        )
        res_dept = await db.execute(stmt_dept)
        dept = res_dept.scalar_one_or_none()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department '{payload.department_code}' not found.",
            )
        emp.department_id = dept.id

    if payload.role_code is not None and payload.role_code.strip():
        stmt_role = select(Role).where(
            Role.code == payload.role_code.strip().upper(),
            Role.deleted_at.is_(None),
        )
        res_role = await db.execute(stmt_role)
        role = res_role.scalar_one_or_none()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{payload.role_code}' not found.",
            )
        emp.role_id = role.id

    if payload.is_active is not None:
        emp.is_active = payload.is_active

    await db.commit()
    await db.refresh(emp)

    return StaffResponse(
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


@router.delete(
    "/admin/staff/{employee_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete a staff member (safeguards Super Admin from deletion)",
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

    stmt = select(Employee).where(Employee.employee_id == norm_id, Employee.deleted_at.is_(None))
    res = await db.execute(stmt)
    emp = res.scalar_one_or_none()
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

    # Soft delete
    emp.deleted_at = datetime.now(timezone.utc)
    emp.is_active = False
    await db.commit()

    return {
        "status": "success",
        "message": f"Staff member '{emp.name}' ({emp.employee_id}) soft-deleted successfully.",
        "deleted_at": emp.deleted_at.isoformat(),
    }
