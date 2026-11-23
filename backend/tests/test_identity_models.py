from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.core.database import get_db, AsyncSessionLocal
from app.models.identity import Department, Role, Employee, AuthSession


@pytest.mark.asyncio
async def test_get_db_generator():
    """Verify that get_db yields an active AsyncSession."""
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        assert session.is_active
        break


@pytest.mark.asyncio
async def test_create_employee_with_role(db_session: AsyncSession):
    dept = Department(name="Sales", code="SALES")
    db_session.add(dept)
    await db_session.flush()

    role = Role(
        department_id=dept.id,
        name="Sales Executive",
        code="SALES_EXEC",
        permissions={"leads": ["read", "write"]},
    )
    db_session.add(role)
    await db_session.flush()

    emp = Employee(
        employee_id="EMP-0001",
        name="Sunil Sharma",
        email="sunil@omshiv.com",
        mobile="9829012345",
        department_id=dept.id,
        role_id=role.id,
        level=1,
        handled_categories=["Residential", "Commercial"],
        budget_min_cr=0.1,
        budget_max_cr=2.0,
    )
    db_session.add(emp)
    await db_session.commit()

    # Query back and verify
    stmt = select(Employee).where(Employee.employee_id == "EMP-0001")
    result = await db_session.execute(stmt)
    saved_emp = result.scalar_one()

    assert saved_emp.employee_id == "EMP-0001"
    assert saved_emp.name == "Sunil Sharma"
    assert saved_emp.mobile == "9829012345"
    assert saved_emp.handled_categories == ["Residential", "Commercial"]
    assert float(saved_emp.budget_min_cr) == 0.1
    assert float(saved_emp.budget_max_cr) == 2.0
    assert saved_emp.is_active is True
    assert saved_emp.department_id == dept.id
    assert saved_emp.role_id == role.id

    # Verify relationships
    assert saved_emp.department is not None
    assert saved_emp.department.code == "SALES"
    assert saved_emp.role is not None
    assert saved_emp.role.code == "SALES_EXEC"


@pytest.mark.asyncio
async def test_employee_unique_constraints(db_session: AsyncSession):
    dept = Department(name="Operations", code="OPS")
    db_session.add(dept)
    await db_session.flush()

    role = Role(
        department_id=dept.id,
        name="Ops Manager",
        code="OPS_MGR",
        permissions={"all": ["read"]},
    )
    db_session.add(role)
    await db_session.flush()

    dept_id = dept.id
    role_id = role.id

    emp1 = Employee(
        employee_id="EMP-0002",
        name="Rajesh Verma",
        email="rajesh@omshiv.com",
        mobile="9829099999",
        department_id=dept_id,
        role_id=role_id,
    )
    db_session.add(emp1)
    await db_session.commit()

    # Duplicate employee_id must raise IntegrityError
    async with db_session.begin_nested():
        emp2 = Employee(
            employee_id="EMP-0002",
            name="Another Rajesh",
            email="rajesh2@omshiv.com",
            mobile="9829088888",
            department_id=dept_id,
            role_id=role_id,
        )
        db_session.add(emp2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # Duplicate mobile must raise IntegrityError
    async with db_session.begin_nested():
        emp3 = Employee(
            employee_id="EMP-0003",
            name="Third Rajesh",
            email="rajesh3@omshiv.com",
            mobile="9829099999",  # Same mobile as emp1
            department_id=dept_id,
            role_id=role_id,
        )
        db_session.add(emp3)
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
async def test_department_and_role_unique_codes(db_session: AsyncSession):
    dept1 = Department(name="Finance", code="FIN")
    db_session.add(dept1)
    await db_session.flush()

    # Duplicate department code
    async with db_session.begin_nested():
        dept2 = Department(name="Finance Two", code="FIN")
        db_session.add(dept2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    role1 = Role(
        department_id=dept1.id,
        name="Finance Head",
        code="FIN_HEAD",
        permissions={"accounts": ["read", "write"]},
    )
    db_session.add(role1)
    await db_session.flush()

    # Duplicate role code
    async with db_session.begin_nested():
        role2 = Role(
            department_id=dept1.id,
            name="Another Finance Head",
            code="FIN_HEAD",
            permissions={},
        )
        db_session.add(role2)
        with pytest.raises(IntegrityError):
            await db_session.flush()


@pytest.mark.asyncio
async def test_create_auth_session(db_session: AsyncSession):
    dept = Department(name="Tech", code="TECH")
    db_session.add(dept)
    await db_session.flush()

    role = Role(department_id=dept.id, name="Admin", code="TECH_ADMIN")
    db_session.add(role)
    await db_session.flush()

    emp = Employee(
        employee_id="EMP-0004",
        name="Admin User",
        email="admin@omshiv.com",
        mobile="9829077777",
        department_id=dept.id,
        role_id=role.id,
    )
    db_session.add(emp)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=5)
    auth_session = AuthSession(
        employee_id=emp.id,
        mobile="9829077777",
        otp_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        channel="WHATSAPP",
        attempts=0,
        is_verified=False,
        expires_at=expires,
    )
    db_session.add(auth_session)
    await db_session.commit()

    # Query back
    stmt = select(AuthSession).where(AuthSession.id == auth_session.id)
    result = await db_session.execute(stmt)
    saved_session = result.scalar_one()

    assert saved_session.id is not None
    assert saved_session.mobile == "9829077777"
    assert saved_session.channel == "WHATSAPP"
    assert saved_session.attempts == 0
    assert saved_session.is_verified is False
    assert saved_session.employee_id == emp.id

    # Verify relationship from employee to auth_sessions
    emp_stmt = select(Employee).where(Employee.id == emp.id)
    emp_res = await db_session.execute(emp_stmt)
    loaded_emp = emp_res.scalar_one()
    assert len(loaded_emp.auth_sessions) == 1
    assert loaded_emp.auth_sessions[0].id == saved_session.id
