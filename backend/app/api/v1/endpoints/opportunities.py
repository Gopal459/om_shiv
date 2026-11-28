from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.callbacks import get_current_employee
from app.core.database import get_db
from app.models.identity import Employee
from app.models.opportunities import OPPORTUNITY_STATUSES
from app.services.callback_service import validate_mobile_input, validate_non_blank_input
from app.services.opportunity_service import (
    ALLOWED_CUSTOMER_TYPES,
    ALLOWED_LOANABLE,
    ALLOWED_LOOKING_TYPES,
    ALLOWED_PROPERTY_TYPES,
    opportunity_service,
)

router = APIRouter()


class OpportunityLocationInput(BaseModel):
    locality_name: str = Field(..., max_length=255)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    radius_km: int = Field(default=10, ge=1, le=200)

    @field_validator("locality_name")
    @classmethod
    def validate_locality(cls, v: str) -> str:
        return validate_non_blank_input(v, "Locality name")


class OpportunityCreateRequest(BaseModel):
    source_lead_id: Optional[str] = Field(default=None, max_length=32)
    contact_name: str = Field(..., max_length=255)
    mobile: str = Field(..., max_length=32)
    alternate_mobile: Optional[str] = Field(default=None, max_length=32)
    email: Optional[str] = Field(default=None, max_length=255)
    address: Optional[str] = Field(default=None)
    customer_type: str = Field(default="END_USER", max_length=32)
    property_type: int = Field(default=2)
    looking_type: int = Field(default=1)
    looking_subcat_type: int = Field(default=1, ge=0)
    budget_from: float = Field(default=0, ge=0)
    budget_to: float = Field(default=0, ge=0)
    area_from: float = Field(default=0, ge=0)
    area_to: float = Field(default=0, ge=0)
    area_unit: str = Field(default="Sq.Ft", max_length=32)
    bhk: int = Field(default=0, ge=0)
    furnishing: Optional[str] = Field(default=None, max_length=32)
    property_age: Optional[str] = Field(default=None, max_length=64)
    loanable: str = Field(default="MAYBE", max_length=16)
    remark: Optional[str] = Field(default=None)
    assign_franch_id: int = Field(default=0, ge=0)
    assigned_to: Optional[str] = Field(default=None, max_length=32)
    followup_datetime: Optional[datetime] = Field(default=None)
    locations: List[OpportunityLocationInput] = Field(default_factory=list)

    @field_validator("contact_name")
    @classmethod
    def validate_contact_name(cls, v: str) -> str:
        return validate_non_blank_input(v, "Contact name")

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        return validate_mobile_input(v)

    @field_validator("customer_type")
    @classmethod
    def validate_customer_type(cls, v: str) -> str:
        norm = (v or "").strip().upper()
        if norm not in ALLOWED_CUSTOMER_TYPES:
            raise ValueError(f"customer_type must be one of {sorted(ALLOWED_CUSTOMER_TYPES)}")
        return norm

    @field_validator("loanable")
    @classmethod
    def validate_loanable(cls, v: str) -> str:
        norm = (v or "").strip().upper()
        if norm not in ALLOWED_LOANABLE:
            raise ValueError(f"loanable must be one of {sorted(ALLOWED_LOANABLE)}")
        return norm

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v: int) -> int:
        if v not in ALLOWED_PROPERTY_TYPES:
            raise ValueError("property_type must be 1 (Rent), 2 (Buy/Sell), or 3 (PG)")
        return v

    @field_validator("looking_type")
    @classmethod
    def validate_looking_type(cls, v: int) -> int:
        if v not in ALLOWED_LOOKING_TYPES:
            raise ValueError("looking_type must be 1..4")
        return v

    @model_validator(mode="after")
    def validate_ranges(self) -> "OpportunityCreateRequest":
        if self.budget_from > 0 and self.budget_to > 0 and self.budget_to < self.budget_from:
            raise ValueError("budget_to must be greater than or equal to budget_from")
        if self.area_from > 0 and self.area_to > 0 and self.area_to < self.area_from:
            raise ValueError("area_to must be greater than or equal to area_from")
        return self


class OpportunityUpdateRequest(BaseModel):
    contact_name: Optional[str] = Field(default=None, max_length=255)
    mobile: Optional[str] = Field(default=None, max_length=32)
    alternate_mobile: Optional[str] = Field(default=None, max_length=32)
    email: Optional[str] = Field(default=None, max_length=255)
    address: Optional[str] = Field(default=None)
    customer_type: Optional[str] = Field(default=None, max_length=32)
    property_type: Optional[int] = Field(default=None)
    looking_type: Optional[int] = Field(default=None)
    looking_subcat_type: Optional[int] = Field(default=None, ge=0)
    budget_from: Optional[float] = Field(default=None, ge=0)
    budget_to: Optional[float] = Field(default=None, ge=0)
    area_from: Optional[float] = Field(default=None, ge=0)
    area_to: Optional[float] = Field(default=None, ge=0)
    area_unit: Optional[str] = Field(default=None, max_length=32)
    bhk: Optional[int] = Field(default=None, ge=0)
    furnishing: Optional[str] = Field(default=None, max_length=32)
    property_age: Optional[str] = Field(default=None, max_length=64)
    loanable: Optional[str] = Field(default=None, max_length=16)
    remark: Optional[str] = Field(default=None)
    assign_franch_id: Optional[int] = Field(default=None, ge=0)
    locations: Optional[List[OpportunityLocationInput]] = Field(default=None)

    @field_validator("contact_name")
    @classmethod
    def validate_contact_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_non_blank_input(v, "Contact name")

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_mobile_input(v)

    @field_validator("customer_type")
    @classmethod
    def validate_customer_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        norm = v.strip().upper()
        if norm not in ALLOWED_CUSTOMER_TYPES:
            raise ValueError(f"customer_type must be one of {sorted(ALLOWED_CUSTOMER_TYPES)}")
        return norm

    @field_validator("loanable")
    @classmethod
    def validate_loanable(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        norm = v.strip().upper()
        if norm not in ALLOWED_LOANABLE:
            raise ValueError(f"loanable must be one of {sorted(ALLOWED_LOANABLE)}")
        return norm

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if v not in ALLOWED_PROPERTY_TYPES:
            raise ValueError("property_type must be 1 (Rent), 2 (Buy/Sell), or 3 (PG)")
        return v

    @field_validator("looking_type")
    @classmethod
    def validate_looking_type(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if v not in ALLOWED_LOOKING_TYPES:
            raise ValueError("looking_type must be 1..4")
        return v

    @model_validator(mode="after")
    def validate_ranges(self) -> "OpportunityUpdateRequest":
        if (
            self.budget_from is not None
            and self.budget_to is not None
            and self.budget_from > 0
            and self.budget_to > 0
            and self.budget_to < self.budget_from
        ):
            raise ValueError("budget_to must be greater than or equal to budget_from")
        if (
            self.area_from is not None
            and self.area_to is not None
            and self.area_from > 0
            and self.area_to > 0
            and self.area_to < self.area_from
        ):
            raise ValueError("area_to must be greater than or equal to area_from")
        return self


class OpportunityRescheduleRequest(BaseModel):
    followup_datetime: datetime
    remark: str = Field(...)
    current_update: Optional[str] = Field(default=None, max_length=120)

    @field_validator("remark")
    @classmethod
    def validate_remark(cls, v: str) -> str:
        return validate_non_blank_input(v, "Remark")


class OpportunityStatusChangeRequest(BaseModel):
    lead_status: int
    remark: Optional[str] = Field(default=None)
    disqualified_reason: Optional[int] = Field(default=None)
    deal_date: Optional[datetime] = Field(default=None)
    registry_date: Optional[datetime] = Field(default=None)
    is_propira_property: bool = Field(default=False)
    matched_property_id: Optional[int] = Field(default=None)
    deal_property_category: Optional[int] = Field(default=None)
    deal_property_subcategory: Optional[int] = Field(default=None)
    deal_property_address: Optional[str] = Field(default=None)
    deal_location_lat: Optional[str] = Field(default=None, max_length=64)
    deal_location_long: Optional[str] = Field(default=None, max_length=64)

    @field_validator("lead_status")
    @classmethod
    def validate_lead_status(cls, v: int) -> int:
        if v not in OPPORTUNITY_STATUSES:
            raise ValueError(f"lead_status must be one of {sorted(OPPORTUNITY_STATUSES)}")
        return v


class OpportunityTransferRequest(BaseModel):
    assigned_to: Optional[str] = Field(default=None, max_length=32)
    assign_franch_id: Optional[int] = Field(default=0, ge=0)
    remark: Optional[str] = Field(default=None)


class OpportunityReopenRequest(BaseModel):
    remark: Optional[str] = Field(default=None)


class OpportunityCallLogRequest(BaseModel):
    remark: Optional[str] = Field(default=None)


# --- Static endpoints MUST precede /{opportunity_id} ---


@router.get(
    "/dashboard",
    status_code=status.HTTP_200_OK,
    summary="Get role-scoped opportunity KPI counts and chart breakdown",
)
async def get_opportunities_dashboard(
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await opportunity_service.get_dashboard(db, actor)


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export filtered opportunities as downloadable Excel .xls workbook",
)
async def export_opportunities(
    tab: str = Query("all", description="new|today|open|missing|in_progress|closed|all"),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Response:
    xls_html = await opportunity_service.export_opportunities_xls(
        db, actor, tab=tab, search=search
    )
    return Response(
        content=xls_html,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": 'attachment; filename="opportunities_export.xls"'},
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List opportunities filtered by tab and search term",
)
async def list_opportunities(
    tab: str = Query("all", description="new|today|open|missing|in_progress|closed|all"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    total, items = await opportunity_service.list_opportunities(
        db, actor, tab=tab, search=search, limit=limit, offset=offset
    )
    return {"total": total, "items": items}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create an opportunity standalone or converted atomically from a lead",
)
async def create_opportunity(
    payload: OpportunityCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await opportunity_service.create_opportunity(
        db,
        actor,
        source_lead_id=payload.source_lead_id,
        contact_name=payload.contact_name,
        mobile=payload.mobile,
        alternate_mobile=payload.alternate_mobile,
        email=payload.email,
        address=payload.address,
        customer_type=payload.customer_type,
        property_type=payload.property_type,
        looking_type=payload.looking_type,
        looking_subcat_type=payload.looking_subcat_type,
        budget_from=payload.budget_from,
        budget_to=payload.budget_to,
        area_from=payload.area_from,
        area_to=payload.area_to,
        area_unit=payload.area_unit,
        bhk=payload.bhk,
        furnishing=payload.furnishing,
        property_age=payload.property_age,
        loanable=payload.loanable,
        remark=payload.remark,
        assign_franch_id=payload.assign_franch_id,
        assigned_to=payload.assigned_to,
        followup_datetime=payload.followup_datetime,
        locations=[loc.model_dump() for loc in payload.locations],
    )


@router.get(
    "/{opportunity_id}",
    status_code=status.HTTP_200_OK,
    summary="Get full 360-degree opportunity profile, locations, activities, and reschedules",
)
async def get_opportunity_detail(
    opportunity_id: int,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await opportunity_service.get_opportunity_detail(db, actor, opportunity_id)


@router.put(
    "/{opportunity_id}",
    status_code=status.HTTP_200_OK,
    summary="Update an open opportunity's requirements and preferred locations",
)
async def update_opportunity(
    opportunity_id: int,
    payload: OpportunityUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    raw_fields = payload.model_dump(exclude_unset=True)
    locations = raw_fields.pop("locations", None)
    return await opportunity_service.update_opportunity(
        db,
        actor,
        opportunity_id,
        fields=raw_fields,
        locations=locations,
    )


@router.get(
    "/{opportunity_id}/related-properties",
    status_code=status.HTTP_200_OK,
    summary="Run live inventory matching engine (getrelatedProperty) for an opportunity",
)
async def get_related_properties(
    opportunity_id: int,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await opportunity_service.get_related_properties(db, actor, opportunity_id)


@router.post(
    "/{opportunity_id}/reschedule",
    status_code=status.HTTP_200_OK,
    summary="Reschedule opportunity follow-up datetime with mandatory remark",
)
async def reschedule_opportunity(
    opportunity_id: int,
    payload: OpportunityRescheduleRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await opportunity_service.reschedule_opportunity(
        db,
        actor,
        opportunity_id,
        followup_datetime=payload.followup_datetime,
        remark=payload.remark,
        current_update=payload.current_update,
    )


@router.post(
    "/{opportunity_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Transition opportunity lifecycle status (In Progress, Disqualified, Deal Scheduled, Closed)",
)
async def change_opportunity_status(
    opportunity_id: int,
    payload: OpportunityStatusChangeRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await opportunity_service.change_opportunity_status(
        db,
        actor,
        opportunity_id,
        lead_status=payload.lead_status,
        remark=payload.remark,
        disqualified_reason=payload.disqualified_reason,
        deal_date=payload.deal_date,
        registry_date=payload.registry_date,
        is_propira_property=payload.is_propira_property,
        matched_property_id=payload.matched_property_id,
        deal_property_category=payload.deal_property_category,
        deal_property_subcategory=payload.deal_property_subcategory,
        deal_property_address=payload.deal_property_address,
        deal_location_lat=payload.deal_location_lat,
        deal_location_long=payload.deal_location_long,
    )


@router.post(
    "/{opportunity_id}/transfer",
    status_code=status.HTTP_200_OK,
    summary="Transfer an open opportunity to another active employee and/or franchise outlet",
)
async def transfer_opportunity(
    opportunity_id: int,
    payload: OpportunityTransferRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await opportunity_service.transfer_opportunity(
        db,
        actor,
        opportunity_id,
        assigned_to=payload.assigned_to,
        assign_franch_id=payload.assign_franch_id,
        remark=payload.remark,
    )


@router.post(
    "/{opportunity_id}/reopen",
    status_code=status.HTTP_200_OK,
    summary="Reopen a Disqualified opportunity back to In Progress",
)
async def reopen_opportunity(
    opportunity_id: int,
    payload: Optional[OpportunityReopenRequest] = None,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await opportunity_service.reopen_opportunity(
        db,
        actor,
        opportunity_id,
        remark=payload.remark if payload else None,
    )


@router.post(
    "/{opportunity_id}/call-log",
    status_code=status.HTTP_200_OK,
    summary="Log a connected call on an opportunity",
)
async def log_opportunity_call(
    opportunity_id: int,
    payload: Optional[OpportunityCallLogRequest] = None,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await opportunity_service.log_opportunity_call(
        db,
        actor,
        opportunity_id,
        remark=payload.remark if payload else None,
    )
