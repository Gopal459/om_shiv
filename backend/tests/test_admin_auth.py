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


@pytest.mark.asyncio
async def test_admin_login_success_and_case_insensitivity(test_client, db_session: AsyncSession):
    await seed_departments_and_roles(db_session)
    await seed_admin_user(db_session)

    # 1. Login with lowercase 'admin'
    resp = await test_client.post("/v1/auth/admin/login", json={"username": "admin", "password": "Admin@123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "SUPER_ADMIN"
    assert "leads" in data["user"]["permissions"]

    # 2. Login with uppercase 'ADMIN'
    resp_upper = await test_client.post("/v1/auth/admin/login", json={"username": "ADMIN", "password": "Admin@123"})
    assert resp_upper.status_code == 200

    # 3. Login with email
    resp_email = await test_client.post("/v1/auth/admin/login", json={"username": "admin@omshiv.in", "password": "Admin@123"})
    assert resp_email.status_code == 200


@pytest.mark.asyncio
async def test_admin_login_invalid_password(test_client, db_session: AsyncSession):
    await seed_departments_and_roles(db_session)
    await seed_admin_user(db_session)

    resp = await test_client.post("/v1/auth/admin/login", json={"username": "admin", "password": "WrongPassword"})
    assert resp.status_code == 401
    assert "Invalid" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_login_non_existent_user(test_client, db_session: AsyncSession):
    await seed_departments_and_roles(db_session)

    resp = await test_client.post("/v1/auth/admin/login", json={"username": "non_existent_user", "password": "AnyPassword"})
    assert resp.status_code == 401
    assert "Invalid" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_login_inactive_user(test_client, db_session: AsyncSession):
    await seed_departments_and_roles(db_session)
    admin_emp = await seed_admin_user(db_session)
    admin_emp.is_active = False
    await db_session.commit()

    resp = await test_client.post("/v1/auth/admin/login", json={"username": "admin", "password": "Admin@123"})
    assert resp.status_code == 403
    assert "deactivated" in resp.json()["detail"].lower()

