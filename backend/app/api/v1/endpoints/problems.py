from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.callbacks import get_current_employee
from app.core.database import get_db
from app.models.identity import Employee
from app.services.problem_service import problem_service

router = APIRouter(prefix="/v1/problems", tags=["problems"])


# --- Pydantic Schemas ---


class ProblemCountsResponse(BaseModel):
    all: int
    new: int
    in_review: int
    resolved: int
    rejected: int


class ProblemListResponse(BaseModel):
    total: int
    counts: ProblemCountsResponse
    items: List[Dict[str, Any]]


class ProblemUpdateRequest(BaseModel):
    status: Optional[str] = Field(default=None, description="NEW, IN_REVIEW, RESOLVED, REJECTED")
    assigned_to: Optional[str] = Field(default=None, description="Target active employee_id")
    resolution_remark: Optional[str] = Field(default=None, description="Triage / resolution remark")


class ConvertProblemRequest(BaseModel):
    assigned_to: Optional[str] = Field(default=None, description="Employee ID for converted lead")
    lead_type: str = Field(default="BUYER", description="BUYER, SELLER, TENANT, OWNER")
    budget_min: Optional[float] = Field(default=None, description="Optional minimum budget")
    budget_max: Optional[float] = Field(default=None, description="Optional maximum budget")


class ProblemLeadResponse(BaseModel):
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


# --- Endpoints (static paths declared BEFORE /{inquiry_id}) ---


@router.get(
    "",
    response_model=ProblemListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Report A Problem inquiries with status counts",
)
async def list_problems(
    status: str = Query("ALL", description="ALL|NEW|IN_REVIEW|RESOLVED|REJECTED"),
    search: Optional[str] = Query(None, description="Search by reporter, mobile, email, property code, remark"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await problem_service.list_problems(
        db,
        actor,
        status_filter=status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export filtered problem reports as Excel .xls workbook",
)
async def export_problems(
    status: str = Query("ALL", description="ALL|NEW|IN_REVIEW|RESOLVED|REJECTED"),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Response:
    xls_html = await problem_service.export_problems_xls(
        db,
        actor,
        status_filter=status,
        search=search,
    )
    return Response(
        content=xls_html,
        media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": 'attachment; filename="problems_export.xls"'},
    )


@router.patch(
    "/{inquiry_id}",
    status_code=status.HTTP_200_OK,
    summary="Update Report A Problem triage status, assignee, or resolution remark",
)
async def update_problem(
    inquiry_id: int,
    payload: ProblemUpdateRequest,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
) -> Dict[str, Any]:
    return await problem_service.update_problem_triage(
        db,
        actor,
        inquiry_id,
        status_val=payload.status,
        assigned_to=payload.assigned_to,
        resolution_remark=payload.resolution_remark,
    )


@router.post(
    "/{inquiry_id}/convert-to-lead",
    response_model=ProblemLeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert a Report A Problem inquiry into an active CRM Lead",
)
async def convert_problem_to_lead(
    inquiry_id: int,
    payload: Optional[ConvertProblemRequest] = None,
    db: AsyncSession = Depends(get_db),
    actor: Employee = Depends(get_current_employee),
):
    return await problem_service.convert_problem_to_lead(
        db,
        actor,
        inquiry_id,
        assigned_to=payload.assigned_to if payload else None,
        lead_type=payload.lead_type if payload else "BUYER",
        budget_min=payload.budget_min if payload else None,
        budget_max=payload.budget_max if payload else None,
    )
