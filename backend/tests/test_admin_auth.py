import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.passwords import hash_password, verify_password
from app.models.identity import Employee, Role, Department
from app.services.identity_seed import seed_admin_user, seed_departments_and_roles


def test_password_hashing():
    raw_pwd = "Admin@123"
    hashed = hash_password(raw_pwd)
    assert hashed != raw_pwd
    assert hashed.startswith("pbkdf2_sha256$")
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password(raw_pwd, "invalid$format") is False


@pytest.mark.asyncio
async def test_seed_admin_user_idempotency(db_session: AsyncSession):
    # Seed depts and roles first
    await seed_departments_and_roles(db_session)
    # Seed admin user
    admin_emp = await seed_admin_user(db_session)
    assert admin_emp is not None
    assert admin_emp.username == "admin"
    assert admin_emp.email == "admin@omshiv.in"
    assert verify_password("Admin@123", admin_emp.password_hash) is True

    # Check role
    stmt = select(Role).where(Role.id == admin_emp.role_id)
    res = await db_session.execute(stmt)
    role = res.scalar_one_or_none()
    assert role is not None
    assert role.code == "SUPER_ADMIN"

    # Idempotent re-run
    second_run = await seed_admin_user(db_session)
    assert second_run.id == admin_emp.id
