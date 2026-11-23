import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
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

class StaffCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    mobile: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = Field(None, max_length=255)
    department_code: str = Field(..., description="Target department code, e.g. SALES, MANAGEMENT")
    role_code: str = Field(..., description="Target role code, e.g. SALES_MANAGER, TELECALLER")


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


class RoleResponse(BaseModel):
    id: int
    name: str
    code: str
    department_id: int
    department_name: Optional[str] = None
    permissions: Dict[str, Any]
    is_active: bool

    model_config = {"from_attributes": True}


class UpdatePermissionsRequest(BaseModel):
    permissions: Dict[str, Any] = Field(..., description="Granular module permissions JSON")


# --- Endpoints ---

@router.get(
    "/admin/staff",
    response_model=List[StaffResponse],
    status_code=status.HTTP_200_OK,
    summary="List all staff members and their assigned roles",
)
async def list_staff(
    db: AsyncSession = Depends(get_db),
) -> List[StaffResponse]:
    stmt = (
        select(Employee)
        .options(selectinload(Employee.department), selectinload(Employee.role))
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
    summary="Create a new staff member with credentials and role assignment",
)
async def create_staff(
    payload: StaffCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> StaffResponse:
    # 1. Check for duplicates in username, email, or mobile
    conditions = [
        func.lower(Employee.username) == payload.username.strip().lower(),
        Employee.mobile == payload.mobile.strip(),
    ]
    if payload.email:
        conditions.append(func.lower(Employee.email) == payload.email.strip().lower())

    stmt_check = select(Employee).where(or_(*conditions))
    res_check = await db.execute(stmt_check)
    existing = res_check.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Staff member with username '{payload.username}', mobile, or email already exists.",
        )

    # 2. Resolve Department
    stmt_dept = select(Department).where(Department.code == payload.department_code.strip().upper())
    res_dept = await db.execute(stmt_dept)
    dept = res_dept.scalar_one_or_none()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with code '{payload.department_code}' not found.",
        )

    # 3. Resolve Role
    stmt_role = select(Role).where(Role.code == payload.role_code.strip().upper())
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


@router.get(
    "/admin/roles",
    response_model=List[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="List all roles and their configured permissions",
)
async def list_roles(
    db: AsyncSession = Depends(get_db),
) -> List[RoleResponse]:
    stmt = select(Role).options(selectinload(Role.department)).order_by(Role.id.asc())
    res = await db.execute(stmt)
    roles = res.scalars().all()

    return [
        RoleResponse(
            id=r.id,
            name=r.name,
            code=r.code,
            department_id=r.department_id,
            department_name=r.department.name if r.department else None,
            permissions=r.permissions or {},
            is_active=r.is_active,
        )
        for r in roles
    ]


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
    stmt = select(Role).options(selectinload(Role.department)).where(Role.code == code.strip().upper())
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

    return RoleResponse(
        id=role.id,
        name=role.name,
        code=role.code,
        department_id=role.department_id,
        department_name=role.department.name if role.department else None,
        permissions=role.permissions or {},
        is_active=role.is_active,
    )
