import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def db_session():
    """Provides an isolated in-memory SQLite async database session for testing."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest_asyncio.fixture
async def test_client(db_session: AsyncSession):
    """Provides an AsyncClient bound to the FastAPI app with the test db session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client_md(db_session: AsyncSession):
    """Provides an AsyncClient authenticated as MD (EMP-0001) with seed data."""
    from app.models.identity import Department, Role, Employee
    from app.core.security import create_access_token
    from sqlalchemy import select

    # Ensure Managing Director employee exists
    res = await db_session.execute(select(Employee).where(Employee.employee_id == "EMP-0001"))
    emp = res.scalar_one_or_none()
    if not emp:
        dept = Department(name="Management", code="MGMT")
        db_session.add(dept)
        await db_session.flush()

        role = Role(
            department_id=dept.id,
            name="Managing Director",
            code="MD",
            permissions={"all": ["*"]},
        )
        db_session.add(role)
        await db_session.flush()

        emp = Employee(
            employee_id="EMP-0001",
            name="Managing Director",
            email="md@omshiv.com",
            mobile="9829000001",
            department_id=dept.id,
            role_id=role.id,
            is_active=True,
        )
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

    # Seed system settings if seeding function is available
    try:
        from app.services.settings_service import seed_system_settings
        await seed_system_settings(db_session)
    except ImportError:
        pass

    token = create_access_token({
        "sub": "EMP-0001",
        "employee_id": emp.id,
        "name": emp.name,
        "mobile": emp.mobile,
        "role": "MD",
        "department": "MGMT",
        "permissions": {"all": ["*"]},
    })

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client_sales(db_session: AsyncSession):
    """Provides an AsyncClient authenticated as Sales Executive (EMP-0002) with seed data."""
    from app.models.identity import Department, Role, Employee
    from app.core.security import create_access_token
    from sqlalchemy import select

    # Ensure Sales department & role exist
    res_dept = await db_session.execute(select(Department).where(Department.code == "SALES"))
    dept = res_dept.scalar_one_or_none()
    if not dept:
        dept = Department(name="Sales", code="SALES")
        db_session.add(dept)
        await db_session.flush()

    res_role = await db_session.execute(select(Role).where(Role.code == "SALES_EXEC"))
    role = res_role.scalar_one_or_none()
    if not role:
        role = Role(
            department_id=dept.id,
            name="Sales Executive",
            code="SALES_EXEC",
            permissions={"leads": ["read", "write"]},
        )
        db_session.add(role)
        await db_session.flush()

    res_emp = await db_session.execute(select(Employee).where(Employee.employee_id == "EMP-0002"))
    emp = res_emp.scalar_one_or_none()
    if not emp:
        emp = Employee(
            employee_id="EMP-0002",
            name="Sunil Sharma",
            email="sunil@omshiv.com",
            mobile="9829012345",
            department_id=dept.id,
            role_id=role.id,
            is_active=True,
        )
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

    token = create_access_token({
        "sub": "EMP-0002",
        "employee_id": emp.id,
        "name": emp.name,
        "mobile": emp.mobile,
        "role": "SALES_EXEC",
        "department": "SALES",
        "permissions": {"leads": ["read", "write"]},
    })

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        yield client
    app.dependency_overrides.clear()



