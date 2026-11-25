import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import hash_otp, verify_otp_hash, create_access_token
from app.models.identity import Employee, AuthSession
from app.services.notifications.whatsapp_gateway import whatsapp_gateway
from app.services.notifications.sms_gateway import sms_gateway


def normalize_mobile(mobile: str) -> str:
    """Normalize mobile number by stripping whitespace, hyphens, and +91 prefix."""
    clean = mobile.strip().replace(" ", "").replace("-", "")
    if clean.startswith("+91"):
        clean = clean[3:]
    elif clean.startswith("0") and len(clean) == 11:
        clean = clean[1:]
    return clean


def generate_otp() -> str:
    """Generate 6-digit numeric OTP. Supports mock OTP in test environments."""
    mock_otp = os.environ.get("MOCK_OTP")
    if mock_otp:
        return mock_otp
    if (
        os.environ.get("PYTEST_CURRENT_TEST")
        or os.environ.get("TESTING", "").lower() in ("true", "1")
    ):
        return "123456"
    return f"{secrets.randbelow(900000) + 100000}"


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone for cross-dialect compatibility."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AuthService:
    """Dual-channel OTP authentication service."""

    @staticmethod
    async def request_otp(mobile: str, db: AsyncSession) -> Dict[str, Any]:
        normalized_mobile = normalize_mobile(mobile)

        # Check if mobile belongs to an active Employee
        stmt = (
            select(Employee)
            .options(selectinload(Employee.department), selectinload(Employee.role))
            .where(Employee.mobile == normalized_mobile, Employee.is_active == True)
        )
        result = await db.execute(stmt)
        employee = result.scalar_one_or_none()

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mobile number not registered or account inactive",
            )

        otp = generate_otp()
        otp_hashed = hash_otp(otp)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=settings.OTP_EXPIRE_SECONDS
        )

        # Attempt primary delivery via WhatsApp
        wa_success = await whatsapp_gateway.send_otp(normalized_mobile, otp)
        channel = "WHATSAPP"

        if not wa_success:
            # Fall back to SMS gateway seamlessly
            sms_success = await sms_gateway.send_otp(normalized_mobile, otp)
            channel = "SMS_FALLBACK"
            if not sms_success:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to dispatch OTP across both WhatsApp and SMS channels",
                )

        session = AuthSession(
            employee_id=employee.id,
            mobile=normalized_mobile,
            otp_hash=otp_hashed,
            channel=channel,
            attempts=0,
            is_verified=False,
            expires_at=expires_at,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return {
            "session_id": session.id,
            "channel": session.channel,
            "expires_in_seconds": settings.OTP_EXPIRE_SECONDS,
            "message": f"OTP dispatched successfully via {session.channel}",
        }

    @staticmethod
    async def fallback_sms(session_id: str, db: AsyncSession) -> Dict[str, Any]:
        stmt = select(AuthSession).where(AuthSession.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authentication session not found",
            )

        if session.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session already verified",
            )

        now = datetime.now(timezone.utc)
        if ensure_utc(session.expires_at) < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP session expired",
            )

        # Regenerate fresh OTP for SMS fallback
        otp = generate_otp()
        session.otp_hash = hash_otp(otp)
        session.channel = "SMS_FALLBACK"

        sms_success = await sms_gateway.send_otp(session.mobile, otp)
        if not sms_success:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to dispatch SMS fallback OTP",
            )

        await db.commit()
        await db.refresh(session)

        return {
            "session_id": session.id,
            "channel": session.channel,
            "message": "OTP resent via SMS fallback successfully",
        }

    @staticmethod
    async def verify_otp(
        session_id: str, otp: str, db: AsyncSession
    ) -> Dict[str, Any]:
        stmt = (
            select(AuthSession)
            .options(
                selectinload(AuthSession.employee).selectinload(Employee.department),
                selectinload(AuthSession.employee).selectinload(Employee.role),
            )
            .where(AuthSession.id == session_id)
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Authentication session not found",
            )

        if session.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session already verified",
            )

        now = datetime.now(timezone.utc)
        if ensure_utc(session.expires_at) < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP session expired",
            )

        if session.attempts >= settings.OTP_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum verification attempts exceeded",
            )

        # Verify hash
        is_valid = verify_otp_hash(otp, session.otp_hash)
        if not is_valid:
            session.attempts += 1
            await db.commit()
            if session.attempts >= settings.OTP_MAX_ATTEMPTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Maximum verification attempts exceeded",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP",
            )

        # Valid OTP: Mark verified
        session.is_verified = True
        employee = session.employee

        role_code = employee.role.code if employee and employee.role else None
        role_permissions = (
            employee.role.permissions if employee and employee.role else {}
        )
        dept_code = (
            employee.department.code if employee and employee.department else None
        )
        emp_id = employee.employee_id if employee else session.mobile

        jwt_claims = {
            "sub": emp_id,
            "employee_id": employee.id if employee else None,
            "name": employee.name if employee else "",
            "mobile": session.mobile,
            "role": role_code,
            "department": dept_code,
            "permissions": role_permissions,
        }

        access_token = create_access_token(jwt_claims)
        session.session_token = access_token
        await db.commit()

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "employee_id": emp_id,
                "name": employee.name if employee else "",
                "mobile": session.mobile,
                "email": employee.email if employee else None,
                "role": role_code,
                "department": dept_code,
                "permissions": role_permissions,
            },
        }


auth_service = AuthService()
