import logging
from typing import Dict, Any, Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.models.identity import Employee, Role, Department
from app.core.passwords import verify_password
from app.core.security import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100, description="Username, Email, or Employee ID")
    password: str = Field(..., min_length=1, description="Account password")


class AdminUserDetail(BaseModel):
    employee_id: str
    name: str
    username: Optional[str] = None
    email: Optional[str] = None
    mobile: str
    department: Optional[str] = None
    role: Optional[str] = None
    permissions: Dict[str, Any] = Field(default_factory=dict)


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AdminUserDetail


@router.post(
    "/admin/login",
    response_model=AdminLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin/Staff Login via Username & Password",
)
async def admin_login(
    payload: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AdminLoginResponse:
    query_str = payload.username.strip()
    query_lower = query_str.lower()

    # Query Employee by username (case-insensitive), email, or employee_id
    stmt = (
        select(Employee)
        .options(selectinload(Employee.role), selectinload(Employee.department))
        .where(
            or_(
                func.lower(Employee.username) == query_lower,
                func.lower(Employee.email) == query_lower,
                Employee.employee_id == query_str.upper(),
            )
        )
    )
    res = await db.execute(stmt)
    employee = res.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact system administrator.",
        )

    if not employee.password_hash or not verify_password(payload.password, employee.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    role_code = employee.role.code if employee.role else "STAFF"
    permissions = employee.role.permissions if employee.role else {}
    department_name = employee.department.name if employee.department else None

    # Issue JWT valid for 24 hours
    token = create_access_token(
        data={
            "sub": employee.employee_id,
            "role": role_code,
            "permissions": permissions,
            "department": department_name,
        },
        expires_delta=timedelta(hours=24),
    )

    return AdminLoginResponse(
        access_token=token,
        token_type="bearer",
        user=AdminUserDetail(
            employee_id=employee.employee_id,
            name=employee.name,
            username=employee.username,
            email=employee.email,
            mobile=employee.mobile,
            department=department_name,
            role=role_code,
            permissions=permissions,
        ),
    )
