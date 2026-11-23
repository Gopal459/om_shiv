from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth_service import auth_service

router = APIRouter()


class RequestOTPRequest(BaseModel):
    mobile: str = Field(..., description="10-digit mobile number")


class RequestOTPResponse(BaseModel):
    session_id: str
    channel: str
    expires_in_seconds: int
    message: str


class VerifyOTPRequest(BaseModel):
    session_id: str = Field(..., description="UUID session id from request-otp")
    otp: str = Field(..., min_length=4, max_length=10, description="Numeric OTP")


class UserDetail(BaseModel):
    employee_id: str
    name: str
    mobile: str
    email: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    permissions: Dict[str, Any] = Field(default_factory=dict)


class VerifyOTPResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserDetail


class FallbackSMSRequest(BaseModel):
    session_id: str = Field(..., description="UUID session id from request-otp")


class FallbackSMSResponse(BaseModel):
    session_id: str
    channel: str
    message: str


@router.post(
    "/request-otp",
    response_model=RequestOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Request OTP login via WhatsApp with automated SMS fallback",
)
async def request_otp(
    payload: RequestOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> RequestOTPResponse:
    res = await auth_service.request_otp(payload.mobile, db)
    return RequestOTPResponse(**res)


@router.post(
    "/verify-otp",
    response_model=VerifyOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP and issue JWT access token",
)
async def verify_otp(
    payload: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyOTPResponse:
    res = await auth_service.verify_otp(payload.session_id, payload.otp, db)
    return VerifyOTPResponse(**res)


@router.post(
    "/fallback-sms",
    response_model=FallbackSMSResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger manual fallback to SMS channel",
)
async def fallback_sms(
    payload: FallbackSMSRequest,
    db: AsyncSession = Depends(get_db),
) -> FallbackSMSResponse:
    res = await auth_service.fallback_sms(payload.session_id, db)
    return FallbackSMSResponse(**res)
