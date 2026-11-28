from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AliasChoices, BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.identity import Employee
from app.services.callback_service import (
    callback_service,
    validate_mobile_input,
    validate_non_blank_input,
)

router = APIRouter(prefix="/v1/callbacks", tags=["callbacks"])
security = HTTPBearer(auto_error=False)


async def get_current_employee(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    """Resolve authenticated, active, non-deleted Employee + Role from Bearer JWT."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    sub = payload.get("sub")
    emp_claim = payload.get("employee_id")

    stmt = (
        select(Employee)
        .options(selectinload(Employee.role))
        .where(
            Employee.is_active.is_(True),
            Employee.deleted_at.is_(None),
        )
    )
    if sub:
        stmt = stmt.where(Employee.employee_id == str(sub))
    elif emp_claim is not None:
        if isinstance(emp_claim, int) or (isinstance(emp_claim, str) and emp_claim.isdigit()):
            stmt = stmt.where(Employee.id == int(emp_claim))
        else:
            stmt = stmt.where(Employee.employee_id == str(emp_claim))
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    employee = (await db.execute(stmt)).scalar_one_or_none()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return employee


# --- Pydantic Schemas ---


class CallbackCreateRequest(BaseModel):
    name: str = Field(..., max_length=255, description="Customer name")
    mobile_number: str = Field(
        ...,
        max_length=32,
        validation_alias=AliasChoices("mobile_number", "phone"),
        description="Customer mobile number",
    )
    phone_code: str = Field(default="+91", max_length=16, description="Country calling code")
    message: Optional[str] = Field(default=None, description="Optional callback note")
    property_id: Optional[int] = Field(default=None, description="Optional numeric property ID")
    property_code: Optional[str] = Field(default=None, max_length=32, description="Optional property code")
    assigned_user_id: Optional[str] = Field(default=None, max_length=32, description="Optional target employee_id")

    @field_validator("name")
    @classmethod
    def validate_name_non_blank(cls, v: str) -> str:
        return validate_non_blank_input(v, "Name")

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_digits(cls, v: str) -> str:
        return validate_mobile_input(v)


class LogCallRequest(BaseModel):
    remark: Optional[str] = Field(default=None, description="Optional call remark")


class RescheduleCallbackRequest(BaseModel):
    current_update: str = Field(..., max_length=120, description="Current follow-up status/category")
    remark: str = Field(..., description="Mandatory reschedule remark")
    followup_datetime: datetime = Field(..., description="Strictly future follow-up datetime")

    @field_validator("current_update")
    @classmethod
    def validate_current_update_non_blank(cls, v: str) -> str:
        return validate_non_blank_input(v, "Current update")


class ChangeStatusRequest(BaseModel):
    lead_status: int = Field(..., ge=0, le=6, description="Callback status code 0..4 or 6")
    remark: str = Field(..., description="Mandatory status change remark")
    disqualified_reason: Optional[int] = Field(default=None, description="Required (1..7) when status=2")
    calls_status: Optional[int] = Field(default=None, ge=0, le=1, description="Optional calls_status flag (0 or 1)")


class TransferCallbackRequest(BaseModel):
    assigned_user_id: str = Field(..., description="Target active employee_id")
    remark: str = Field(..., description="Mandatory transfer remark")


class ReopenCallbackRequest(BaseModel):
    remark: Optional[str] = Field(default=None, description="Optional reopen remark")


class ConvertCallbackRequest(BaseModel):
    customer_type: str = Field(default="BUY", max_length=32, description="Customer type e.g. BUY, RENT, PG")
    name: str = Field(..., max_length=255, description="Customer name")
    email: Optional[str] = Field(default=None, max_length=255, description="Customer email")
    mobile: str = Field(..., max_length=32, description="Primary mobile number")
    alternate_mobile: Optional[str] = Field(default=None, max_length=255, description="Alternate mobile number")
    address: str = Field(default="", description="Customer address / preferred locality")
    refer_by_relation: Optional[str] = Field(default=None, max_length=255, description="Referral relation")
    refer_by_name: Optional[str] = Field(default=None, max_length=255, description="Referral name")
    refer_by_mobile: Optional[str] = Field(default=None, max_length=255, description="Referral mobile")
    source: str = Field(default="Website Callback", max_length=64, description="Lead source")
    assigned_to: Optional[str] = Field(default=None, max_length=32, description="Assignee employee_id")

    @field_validator("name")
    @classmethod
    def validate_name_non_blank(cls, v: str) -> str:
        return validate_non_blank_input(v, "Name")

    @field_validator("address")
    @classmethod
    def validate_address_non_blank(cls, v: str) -> str:
        return validate_non_blank_input(v, "Address")

    @field_validator("mobile")
    @classmethod
    def validate_mobile_digits(cls, v: str) -> str:
        return validate_mobile_input(v)


class AssigneeResponse(BaseModel):
    employee_id: str
    name: str
    role_name: Optional[str] = None
    role_code: Optional[str] = None
    is_active: bool


class DashboardCountsResponse(BaseModel):
    new_calls: int
    today_calls: int
    open_calls: int
    missing_calls: int
    converted_leads: int
    all_calls: int
    converted_property: int


class CallbackListResponse(BaseModel):
    total: int
    items: List[Dict[str, Any]]


# --- Endpoints (static paths declared BEFORE /{callback_id}) ---


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual callback entry",
)
async def create_manual_callback(
    payload: CallbackCreateRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    cb = await callback_service.create_callback(
        db,
        name=payload.name,
        mobile_number=payload.mobile_number,
        phone_code=payload.phone_code,
        message=payload.message,
        property_id=payload.property_id,
        property_code=payload.property_code,
        assigned_user_id=payload.assigned_user_id,
        actor_emp_id=actor.employee_id,
        enforce_caller_scope=True,
    )
    return await callback_service.get_callback_detail(db, actor, cb.callback_id)


@router.get(
    "/dashboard",
    response_model=DashboardCountsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get role-scoped callback dashboard counts",
)
async def get_callback_dashboard(
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, int]:
    return await callback_service.get_dashboard_counts(db, actor)


@router.get(
    "",
    response_model=CallbackListResponse,
    status_code=status.HTTP_200_OK,
    summary="List callbacks filtered by tab, search, and sort order",
)
async def list_callbacks(
    tab: str = Query("new", description="new|today|open|missing|converted|all|converted_property"),
    search: Optional[str] = Query(None, description="Search by name, mobile, WEB ID, property, message"),
    sort_by: str = Query("created_date", description="created_date|followup_datetime|name|callback_id"),
    order_by: str = Query("desc", description="asc|desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    total, items = await callback_service.list_callbacks(
        db,
        actor,
        tab=tab,
        search=search,
        sort_by=sort_by,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )
    return {"total": total, "items": items}


@router.get(
    "/assignees",
    response_model=List[AssigneeResponse],
    status_code=status.HTTP_200_OK,
    summary="List active staff available for callback assignment/transfer",
)
async def list_callback_assignees(
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> List[Dict[str, Any]]:
    stmt = (
        select(Employee)
        .options(selectinload(Employee.role))
        .where(
            Employee.is_active.is_(True),
            Employee.deleted_at.is_(None),
        )
        .order_by(Employee.name.asc())
    )
    employees = list((await db.execute(stmt)).scalars().all())
    return [
        {
            "employee_id": emp.employee_id,
            "name": emp.name,
            "role_name": emp.role.name if emp.role else None,
            "role_code": emp.role.code if emp.role else None,
            "is_active": emp.is_active,
        }
        for emp in employees
    ]


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export filtered callbacks as Excel .xls workbook",
)
async def export_callbacks(
    tab: str = Query("all", description="new|today|open|missing|converted|all|converted_property"),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_date"),
    order_by: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Response:
    xls_html = await callback_service.export_callbacks_xls(
        db,
        actor,
        tab=tab,
        search=search,
        sort_by=sort_by,
        order_by=order_by,
    )
    return Response(
        content=xls_html,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": 'attachment; filename="callbacks_export.xls"'},
    )


@router.get(
    "/{callback_id}",
    status_code=status.HTTP_200_OK,
    summary="Get detailed callback record with reschedule & activity history",
)
async def get_callback_detail(
    callback_id: int,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await callback_service.get_callback_detail(db, actor, callback_id)


@router.post(
    "/{callback_id}/log-call",
    status_code=status.HTTP_200_OK,
    summary="Log a call attempt/connection on a callback",
)
async def log_callback_call(
    callback_id: int,
    payload: Optional[LogCallRequest] = None,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await callback_service.log_callback_call(
        db,
        actor,
        callback_id,
        remark=payload.remark if payload else None,
    )


@router.post(
    "/{callback_id}/reschedule",
    status_code=status.HTTP_200_OK,
    summary="Reschedule a callback follow-up datetime",
)
async def reschedule_callback(
    callback_id: int,
    payload: RescheduleCallbackRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await callback_service.reschedule_callback(
        db,
        actor,
        callback_id,
        current_update=payload.current_update,
        remark=payload.remark,
        followup_datetime=payload.followup_datetime,
    )


@router.post(
    "/{callback_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Change callback lifecycle status",
)
async def change_callback_status(
    callback_id: int,
    payload: ChangeStatusRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await callback_service.change_callback_status(
        db,
        actor,
        callback_id,
        lead_status=payload.lead_status,
        remark=payload.remark,
        disqualified_reason=payload.disqualified_reason,
        calls_status=payload.calls_status,
    )


@router.post(
    "/{callback_id}/transfer",
    status_code=status.HTTP_200_OK,
    summary="Transfer callback to another active staff member",
)
async def transfer_callback(
    callback_id: int,
    payload: TransferCallbackRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await callback_service.transfer_callback(
        db,
        actor,
        callback_id,
        assigned_user_id=payload.assigned_user_id,
        remark=payload.remark,
    )


@router.post(
    "/{callback_id}/reopen",
    status_code=status.HTTP_200_OK,
    summary="Reopen a closed Disqualified or Solved callback",
)
async def reopen_callback(
    callback_id: int,
    payload: Optional[ReopenCallbackRequest] = None,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await callback_service.reopen_callback(
        db,
        actor,
        callback_id,
        remark=payload.remark if payload else None,
    )


@router.post(
    "/{callback_id}/convert-to-lead",
    status_code=status.HTTP_200_OK,
    summary="Convert an open callback into Lead + TblLead",
)
async def convert_callback_to_lead(
    callback_id: int,
    payload: ConvertCallbackRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await callback_service.convert_callback_to_lead(
        db,
        actor,
        callback_id,
        customer_type=payload.customer_type,
        name=payload.name,
        email=payload.email,
        mobile=payload.mobile,
        alternate_mobile=payload.alternate_mobile,
        address=payload.address,
        refer_by_relation=payload.refer_by_relation,
        refer_by_name=payload.refer_by_name,
        refer_by_mobile=payload.refer_by_mobile,
        source=payload.source,
        assigned_to=payload.assigned_to,
    )
