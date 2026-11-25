import pytest
import pytest_asyncio
import jwt
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.identity import Department, Role, Employee, AuthSession
from app.services.notifications.whatsapp_gateway import whatsapp_gateway
from app.services.notifications.sms_gateway import sms_gateway


@pytest_asyncio.fixture
async def seed_employee(db_session: AsyncSession):
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
        is_active=True,
    )
    db_session.add(emp)
    await db_session.commit()
    await db_session.refresh(emp)
    return emp


@pytest.fixture
def mock_whatsapp_fail(monkeypatch):
    """Simulates WhatsApp gateway failure to test automated SMS fallback."""
    async def mock_send_fail(mobile: str, otp: str) -> bool:
        return False

    monkeypatch.setattr(whatsapp_gateway, "send_otp", mock_send_fail)


@pytest.mark.asyncio
async def test_auth_request_otp_whatsapp_success(test_client: AsyncClient, seed_employee):
    # 1. Request OTP via primary WhatsApp channel
    response = await test_client.post("/v1/auth/request-otp", json={"mobile": "9829012345"})
    assert response.status_code == 200
    data = response.json()
    assert data["channel"] == "WHATSAPP"
    assert "session_id" in data
    assert data["expires_in_seconds"] == 300

    session_id = data["session_id"]

    # 2. Verify with valid OTP
    verify_resp = await test_client.post("/v1/auth/verify-otp", json={
        "session_id": session_id,
        "otp": "123456",
    })
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert "access_token" in verify_data
    assert verify_data["token_type"].lower() == "bearer"
    assert verify_data["user"]["employee_id"] == "EMP-0001"
    assert verify_data["user"]["role"] == "SALES_EXEC"
    assert verify_data["user"]["department"] == "SALES"
    assert verify_data["user"]["permissions"] == {"leads": ["read", "write"]}

    # Decode and verify JWT payload
    payload = jwt.decode(
        verify_data["access_token"],
        settings.SECRET_KEY,
        algorithms=["HS256"],
    )
    assert payload["sub"] == "EMP-0001"
    assert payload["role"] == "SALES_EXEC"
    assert payload["department"] == "SALES"
    assert payload["permissions"] == {"leads": ["read", "write"]}


@pytest.mark.asyncio
async def test_auth_request_otp_and_fallback(test_client: AsyncClient, seed_employee, mock_whatsapp_fail):
    # When WhatsApp fails, system falls back to SMS OTP seamlessly
    response = await test_client.post("/v1/auth/request-otp", json={"mobile": "9829012345"})
    assert response.status_code == 200
    data = response.json()
    assert data["channel"] == "SMS_FALLBACK"
    assert "session_id" in data

    # Verify 6-digit OTP
    verify_resp = await test_client.post("/v1/auth/verify-otp", json={
        "session_id": data["session_id"],
        "otp": "123456",
    })
    assert verify_resp.status_code == 200
    assert "access_token" in verify_resp.json()
    assert verify_resp.json()["user"]["employee_id"] == "EMP-0001"


@pytest.mark.asyncio
async def test_auth_manual_fallback_sms(test_client: AsyncClient, seed_employee):
    # User initiates WhatsApp login
    resp1 = await test_client.post("/v1/auth/request-otp", json={"mobile": "9829012345"})
    assert resp1.status_code == 200
    session_id = resp1.json()["session_id"]
    assert resp1.json()["channel"] == "WHATSAPP"

    # User does not receive WhatsApp OTP within 30s and clicks manual SMS fallback
    resp2 = await test_client.post("/v1/auth/fallback-sms", json={"session_id": session_id})
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["channel"] == "SMS_FALLBACK"
    assert data["session_id"] == session_id

    # Verify OTP
    verify_resp = await test_client.post("/v1/auth/verify-otp", json={
        "session_id": session_id,
        "otp": "123456",
    })
    assert verify_resp.status_code == 200
    assert "access_token" in verify_resp.json()


@pytest.mark.asyncio
async def test_auth_invalid_otp_and_max_attempts(test_client: AsyncClient, seed_employee):
    resp = await test_client.post("/v1/auth/request-otp", json={"mobile": "9829012345"})
    session_id = resp.json()["session_id"]

    # Attempt 1: wrong OTP
    resp_fail1 = await test_client.post("/v1/auth/verify-otp", json={
        "session_id": session_id,
        "otp": "000000",
    })
    assert resp_fail1.status_code == 400
    assert "invalid" in resp_fail1.json()["detail"].lower()

    # Attempt 2: wrong OTP
    resp_fail2 = await test_client.post("/v1/auth/verify-otp", json={
        "session_id": session_id,
        "otp": "999999",
    })
    assert resp_fail2.status_code == 400

    # Attempt 3: wrong OTP -> max attempts exceeded
    resp_fail3 = await test_client.post("/v1/auth/verify-otp", json={
        "session_id": session_id,
        "otp": "111111",
    })
    assert resp_fail3.status_code in (400, 429)
    assert "attempt" in resp_fail3.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_expired_session(test_client: AsyncClient, seed_employee, db_session: AsyncSession):
    resp = await test_client.post("/v1/auth/request-otp", json={"mobile": "9829012345"})
    session_id = resp.json()["session_id"]

    # Manually expire session in DB
    result = await db_session.execute(select(AuthSession).where(AuthSession.id == session_id))
    session = result.scalar_one()
    session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    # Try verifying expired session
    verify_resp = await test_client.post("/v1/auth/verify-otp", json={
        "session_id": session_id,
        "otp": "123456",
    })
    assert verify_resp.status_code == 400
    assert "expired" in verify_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_unregistered_mobile(test_client: AsyncClient):
    response = await test_client.post("/v1/auth/request-otp", json={"mobile": "9999999999"})
    assert response.status_code in (400, 404)
