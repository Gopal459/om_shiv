from __future__ import annotations
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Request, Response, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import AliasChoices, BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.services.callback_service import callback_service
from app.services.intake_service import intake_service

router = APIRouter()
security = HTTPBearer(auto_error=False)


# --- Pydantic Schemas ---

class LeadIntakeRequest(BaseModel):
    source: str = Field(default="PROPERTY_INQUIRY", description="Lead source channel")
    full_name: str = Field(..., description="Customer full name")
    mobile: str = Field(..., description="10 or 12-digit mobile number")
    email: Optional[str] = Field(None, description="Customer email address")
    lead_type: str = Field(default="BUYER", description="BUYER, SELLER, TENANT, OWNER")
    related_listing_id: Optional[str] = Field(None, description="Related property listing ID (OP-YYYY-NNNNN)")
    related_project_id: Optional[int] = Field(None, description="Related builder project ID")
    budget_min: Optional[float] = Field(None, description="Minimum budget in INR")
    budget_max: Optional[float] = Field(None, description="Maximum budget in INR")
    preferred_city: Optional[str] = Field("Alwar", description="Preferred city")
    preferred_locality: Optional[str] = Field(None, description="Preferred locality / sector")
    idempotency_key: Optional[str] = Field(None, description="Unique idempotency token")
    referral_code: Optional[str] = Field(None, description="Creator tracking code or CP code")
    partner_id: Optional[int] = Field(None, description="Explicit ChannelPartner ID")
    accompanied_by: Optional[str] = Field(None, description="Omshiv employee ID for L1 accompanied visit")


class LeadIntakeResponse(BaseModel):
    lead_id: Optional[str] = Field(None, description="Assigned sequence ID (OB-YYYY-NNNNNN)")
    is_duplicate: bool = Field(False, description="True if deduplicated against recent lead")
    is_test: bool = Field(False, description="True if suppressed as test lead")
    status: str = Field(..., description="created, duplicate, idempotent, suppressed")
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    stage: Optional[str] = None
    is_untouched: Optional[bool] = None


class WebsiteInquiryCreateRequest(BaseModel):
    inquiry_type: str = Field(
        ...,
        description="CALLBACK, PROBLEM_REPORT, SERVICE_LOAN, SERVICE_LEGAL, SERVICE_INTERIOR, CONTACT_US",
    )
    full_name: str = Field(..., description="Full name of requester")
    mobile: str = Field(..., description="Mobile number")
    email: Optional[str] = Field(None, description="Email address")
    details: Optional[Dict[str, Any]] = Field(None, description="Custom form payload/specifications")


class CallbackIntakeRequest(BaseModel):
    name: str = Field(..., description="Customer name")
    mobile_number: str = Field(
        ...,
        validation_alias=AliasChoices("mobile_number", "phone"),
        description="Customer mobile number",
    )
    phone_code: str = Field(default="+91", description="Country calling code")
    message: Optional[str] = Field(default=None, description="Optional callback note")
    property_id: Optional[int] = Field(default=None, description="Optional numeric property ID")
    property_code: Optional[str] = Field(default=None, description="Optional property code OP-YYYY-NNNNN")

    @field_validator("name")
    @classmethod
    def validate_name_non_blank(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned:
            raise ValueError("Name must not be blank")
        return cleaned

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_non_blank(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned or not re.search(r"\d", cleaned):
            raise ValueError("Valid mobile number is required")
        return cleaned


class CallbackIntakeResponse(BaseModel):
    callback_id: int
    lead_unique_id: Optional[str] = None
    name: str
    mobile_number: str
    phone_code: str
    message: Optional[str] = None
    property_id: Optional[int] = None
    property_code: Optional[str] = None
    assigned_user_id: Optional[str] = None
    lead_status: int
    calls_status: int
    lead_open: int
    created_date: datetime

    model_config = {"from_attributes": True}


class WebsiteInquiryResponse(BaseModel):
    id: int
    inquiry_type: str
    full_name: str
    mobile: str
    email: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    is_converted: bool
    converted_lead_id: Optional[str] = None
    converted_by_emp_id: Optional[str] = None
    converted_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConvertInquiryRequest(BaseModel):
    assigned_to: Optional[str] = Field(None, description="Employee ID to assign the converted lead")
    lead_type: str = Field(default="BUYER", description="BUYER, SELLER, TENANT, OWNER")
    budget_min: Optional[float] = Field(None, description="Optional minimum budget")
    budget_max: Optional[float] = Field(None, description="Optional maximum budget")


class LeadDetailResponse(BaseModel):
    id: int
    lead_id: str
    full_name: str
    mobile: str
    email: Optional[str] = None
    lead_type: str
    source: str
    assigned_to: Optional[str] = None
    stage: str
    temperature: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    preferred_city: Optional[str] = None
    preferred_locality: Optional[str] = None
    is_untouched: bool
    is_duplicate: bool
    is_test: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def get_actor_employee_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """Extract authenticated employee_id from Bearer token if present."""
    if credentials and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            sub = payload.get("sub")
            if sub:
                return str(sub)
        except Exception:
            pass
    return None


# --- Endpoints ---

@router.post(
    "/intake/lead",
    response_model=LeadIntakeResponse,
    summary="Inbound Lead Intake API (Unified 6-way ingestion)",
)
async def intake_lead(
    payload: LeadIntakeRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Ingest inbound leads with phone normalization, test suppression, and 24h deduplication."""
    result = await intake_service.create_or_dedup_lead(
        db=db,
        source=payload.source,
        full_name=payload.full_name,
        mobile=payload.mobile,
        email=payload.email,
        lead_type=payload.lead_type,
        related_listing_id=payload.related_listing_id,
        related_project_id=payload.related_project_id,
        budget_min=payload.budget_min,
        budget_max=payload.budget_max,
        preferred_city=payload.preferred_city,
        preferred_locality=payload.preferred_locality,
        idempotency_key=payload.idempotency_key,
        referral_code=payload.referral_code,
        partner_id=payload.partner_id,
        accompanied_by=payload.accompanied_by,
    )
    if result.get("status") == "created":
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK

    return result


@router.post(
    "/intake/callback",
    response_model=CallbackIntakeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Public Request A Callback Form Intake",
)
async def submit_callback_request(
    payload: CallbackIntakeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a public Request A Callback form with automatic TELECALLER round-robin."""
    callback = await callback_service.create_callback(
        db,
        name=payload.name,
        mobile_number=payload.mobile_number,
        phone_code=payload.phone_code,
        message=payload.message,
        property_id=payload.property_id,
        property_code=payload.property_code,
    )
    return callback


@router.post(
    "/intake/inquiry",
    response_model=WebsiteInquiryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Public Website Inquiry Form Intake",
)
async def submit_website_inquiry(
    payload: WebsiteInquiryCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a public inquiry (Callback, Problem Report, Services, Help Center)."""
    inquiry = await intake_service.create_website_inquiry(
        db=db,
        inquiry_type=payload.inquiry_type,
        full_name=payload.full_name,
        mobile=payload.mobile,
        email=payload.email,
        details=payload.details,
    )
    return inquiry


@router.get(
    "/crm/inquiries",
    response_model=List[WebsiteInquiryResponse],
    status_code=status.HTTP_200_OK,
    summary="List Website Inquiries for CRM staff review",
)
async def list_crm_inquiries(
    is_converted: Optional[bool] = Query(False, description="Filter by conversion status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve website inquiries, defaulting to unconverted requests for staff triage."""
    inquiries = await intake_service.list_unconverted_inquiries(
        db=db,
        is_converted=is_converted,
        limit=limit,
        offset=offset,
    )
    return inquiries


@router.post(
    "/crm/inquiries/{id}/convert-to-lead",
    response_model=LeadDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="1-Click Conversion: Convert Website Inquiry into an active Lead",
)
async def convert_inquiry_to_lead(
    id: int,
    payload: ConvertInquiryRequest,
    db: AsyncSession = Depends(get_db),
    actor_id: Optional[str] = Depends(get_actor_employee_id),
):
    """1-Click convert a website inquiry into an official pipeline lead."""
    lead = await intake_service.convert_inquiry_to_lead(
        db=db,
        inquiry_id=id,
        assigned_to=payload.assigned_to,
        lead_type=payload.lead_type,
        budget_min=payload.budget_min,
        budget_max=payload.budget_max,
        converted_by_emp_id=actor_id,
    )
    return lead
