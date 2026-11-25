import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.identity import Department, Role, Employee
from app.core.passwords import hash_password

logger = logging.getLogger(__name__)

DEFAULT_DEPARTMENTS = [
    ("MANAGEMENT", "Executive Management"),
    ("SALES", "Sales & Business Development"),
    ("OPERATIONS", "Operations & Verification"),
]

DEFAULT_ROLES: List[Dict[str, Any]] = [
    {
        "code": "SUPER_ADMIN",
        "name": "Super Administrator",
        "dept": "MANAGEMENT",
        "permissions": {
            "leads": ["view_all", "create", "edit_stage", "delete", "reassign", "convert_inquiries"],
            "properties": ["view_all", "post_listing", "verify", "approve_reject", "recycle_bin"],
            "masters": ["view", "manage_options", "manage_pincodes"],
            "staff": ["view_staff", "create_staff", "edit_permissions"],
            "settings": ["view_settings", "edit_settings", "view_audit"],
        },
    },
    {
        "code": "SALES_MANAGER",
        "name": "Sales Manager",
        "dept": "SALES",
        "permissions": {
            "leads": ["view_all", "create", "edit_stage", "reassign", "convert_inquiries"],
            "properties": ["view_all"],
            "masters": ["view"],
            "staff": ["view_staff"],
            "settings": ["view_settings"],
        },
    },
    {
        "code": "TELECALLER",
        "name": "Telecaller",
        "dept": "SALES",
        "permissions": {
            "leads": ["view_assigned", "create", "edit_stage", "convert_inquiries"],
            "properties": ["view_all"],
            "masters": ["view"],
        },
    },
    {
        "code": "VERIFICATION_OFFICER",
        "name": "Verification Officer",
        "dept": "OPERATIONS",
        "permissions": {
            "properties": ["view_all", "verify", "approve_reject", "recycle_bin"],
            "masters": ["view"],
        },
    },
    {
        "code": "FIELD_EXECUTIVE",
        "name": "Field Executive",
        "dept": "SALES",
        "permissions": {
            "leads": ["view_assigned", "edit_stage"],
            "properties": ["view_all"],
        },
    },
    {
        "code": "FRANCHISEE_AGENT",
        "name": "Franchisee / Channel Partner",
        "dept": "SALES",
        "permissions": {
            "leads": ["view_assigned", "create"],
            "properties": ["view_all", "post_listing"],
        },
    },
]


async def seed_departments_and_roles(db: AsyncSession) -> None:
    """Seeds default departments and core roles idempotently."""
    dept_map = {}
    for code, name in DEFAULT_DEPARTMENTS:
        stmt = select(Department).where(Department.code == code)
        res = await db.execute(stmt)
        dept = res.scalar_one_or_none()
        if not dept:
            dept = Department(code=code, name=name, is_active=True)
            db.add(dept)
            await db.flush()
        dept_map[code] = dept

    for r in DEFAULT_ROLES:
        stmt = select(Role).where(Role.code == r["code"])
        res = await db.execute(stmt)
        role = res.scalar_one_or_none()
        dept = dept_map.get(r["dept"])
        dept_id = dept.id if dept else None
        if not role and dept_id:
            role = Role(
                department_id=dept_id,
                name=r["name"],
                code=r["code"],
                permissions=r["permissions"],
                is_active=True,
            )
            db.add(role)
            await db.flush()
        elif role:
            # Refresh default permissions if empty
            if not role.permissions:
                role.permissions = r["permissions"]
                await db.flush()

    await db.commit()


async def seed_admin_user(db: AsyncSession) -> Employee:
    """Seeds the default Super Administrator employee if not already existing."""
    stmt = select(Employee).where(Employee.username == "admin")
    res = await db.execute(stmt)
    admin_emp = res.scalar_one_or_none()

    if not admin_emp:
        # Check by email or employee_id
        stmt2 = select(Employee).where((Employee.email == "admin@omshiv.in") | (Employee.employee_id == "EMP-0001"))
        res2 = await db.execute(stmt2)
        admin_emp = res2.scalar_one_or_none()

    # Get SUPER_ADMIN role & MANAGEMENT dept
    stmt_role = select(Role).where(Role.code == "SUPER_ADMIN")
    res_role = await db.execute(stmt_role)
    super_admin_role = res_role.scalar_one_or_none()

    stmt_dept = select(Department).where(Department.code == "MANAGEMENT")
    res_dept = await db.execute(stmt_dept)
    mgmt_dept = res_dept.scalar_one_or_none()

    default_pwd_hash = hash_password("Admin@123")

    if not admin_emp:
        admin_emp = Employee(
            employee_id="EMP-0001",
            name="Super Administrator",
            username="admin",
            password_hash=default_pwd_hash,
            email="admin@omshiv.in",
            mobile="9876543210",
            department_id=mgmt_dept.id if mgmt_dept else None,
            role_id=super_admin_role.id if super_admin_role else None,
            is_active=True,
        )
        db.add(admin_emp)
        await db.commit()
        await db.refresh(admin_emp)
    else:
        # Update credentials and role if missing
        updated = False
        if not admin_emp.username:
            admin_emp.username = "admin"
            updated = True
        if not admin_emp.password_hash:
            admin_emp.password_hash = default_pwd_hash
            updated = True
        if super_admin_role and admin_emp.role_id != super_admin_role.id:
            admin_emp.role_id = super_admin_role.id
            updated = True
        if updated:
            await db.commit()
            await db.refresh(admin_emp)

    return admin_emp
