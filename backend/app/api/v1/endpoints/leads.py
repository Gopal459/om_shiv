from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Request, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, or_, desc, asc

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.leads import Lead, LeadActivity, LeadActionLog
from app.repositories import lead_repo
from app.services.pipeline_service import pipeline_service

router = APIRouter()
security = HTTPBearer(auto_error=False)


# --- Pydantic Schemas ---

class LeadActionCreate(BaseModel):
    action_type: str = Field(..., description="CALL, WHATSAPP, VISIT, MEETING, NOTE, TRANSFER, REQUIREMENT")
    outcome: Optional[str] = Field(None, description="Action outcome (e.g. Connected, Ringing, Visited)")
    note: Optional[str] = Field(None, description="Notes on the action")
    next_action: Optional[str] = Field(None, description="Recommended next step")
    stage: Optional[str] = Field(None, description="Target stage (e.g. CONNECTED, QUALIFIED, LOST)")
    temperature: Optional[str] = Field(None, description="Lead temperature: HOT, WARM, COLD")
    follow_up_date: Optional[datetime] = Field(None, description="Follow-up scheduled datetime (UTC)")
    lost_reason: Optional[str] = Field(None, description="Mandatory reason if transitioning to LOST")


class LeadActivityResponse(BaseModel):
    id: int
    lead_id: str
    action_type: str
    outcome: Optional[str] = None
    note: Optional[str] = None
    next_action: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    stage_before: Optional[str] = None
    stage_after: Optional[str] = None
    temperature: Optional[str] = None
    logged_by: Optional[str] = None
    performed_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


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
    follow_up_date: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None
    lost_reason: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    preferred_city: Optional[str] = None
    preferred_locality: Optional[str] = None
    is_untouched: bool
    is_duplicate: bool
    is_test: bool
    created_at: datetime
    updated_at: datetime
    activities: List[LeadActivityResponse] = []

    model_config = {"from_attributes": True}


def get_actor_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Extract authenticated employee_id from Bearer token, or fallback to SYSTEM."""
    if credentials and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            sub = payload.get("sub")
            if sub:
                return str(sub)
        except Exception:
            pass
    return "SYSTEM"


async def find_lead_by_id_or_lead_id(db: AsyncSession, lead_identifier: str) -> Optional[Lead]:
    """Helper delegating to LeadRepository."""
    return await lead_repo.get_by_id_or_lead_id(db, lead_identifier)


# --- Sales Rep Queue & Leads Endpoints ---

@router.get(
    "/my-work",
    response_model=List[LeadDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Prioritized sales rep work queue",
)
async def get_my_work_queue(
    rep_id: Optional[str] = Query(None, description="Optional override for managerial views"),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(get_actor_from_token),
):
    """
    Returns prioritized sales work queue:
    1. Overdue follow-ups (follow_up_date < now)
    2. Untouched leads (is_untouched == True)
    3. Today's calls/visits/follow-ups
    4. Upcoming future follow-ups
    5. Other active leads
    """
    target_rep = rep_id or actor_id
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Fetch all active open leads assigned to this rep via Repository
    leads = await lead_repo.get_work_queue(db, target_rep)

    overdue: List[Lead] = []
    untouched: List[Lead] = []
    today: List[Lead] = []
    upcoming: List[Lead] = []
    other: List[Lead] = []

    for l in leads:
        # Sort activities descending
        l.activities.sort(key=lambda a: a.created_at, reverse=True)

        if l.follow_up_date and l.follow_up_date < now:
            overdue.append(l)
        elif l.is_untouched:
            untouched.append(l)
        elif l.follow_up_date and today_start <= l.follow_up_date <= today_end:
            today.append(l)
        elif l.follow_up_date and l.follow_up_date > today_end:
            upcoming.append(l)
        else:
            other.append(l)

    # Sort each bucket appropriately
    overdue.sort(key=lambda x: x.follow_up_date or now)
    untouched.sort(key=lambda x: x.untouched_timer_start or now)
    today.sort(key=lambda x: x.follow_up_date or now)
    upcoming.sort(key=lambda x: x.follow_up_date or now)
    other.sort(key=lambda x: x.created_at, reverse=True)

    prioritized = overdue + untouched + today + upcoming + other
    return prioritized


@router.get(
    "/my-leads",
    response_model=List[LeadDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Filterable list of leads assigned to rep",
)
async def get_my_leads(
    stage: Optional[str] = Query(None, description="Filter by stage"),
    temperature: Optional[str] = Query(None, description="Filter by temperature: HOT, WARM, COLD"),
    date_from: Optional[datetime] = Query(None, description="Filter created on or after date"),
    date_to: Optional[datetime] = Query(None, description="Filter created on or before date"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    rep_id: Optional[str] = Query(None, description="Optional override for managerial views"),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(get_actor_from_token),
):
    """Query leads assigned to the sales rep with filtering by stage, temperature, and date range."""
    target_rep = rep_id or actor_id

    conditions = [Lead.assigned_to == target_rep]
    if stage:
        conditions.append(Lead.stage == stage.strip().upper())
    if temperature:
        conditions.append(Lead.temperature == temperature.strip().upper())
    if date_from:
        conditions.append(Lead.created_at >= date_from)
    if date_to:
        conditions.append(Lead.created_at <= date_to)

    stmt = (
        select(Lead)
        .options(selectinload(Lead.activities))
        .where(and_(*conditions))
        .order_by(desc(Lead.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    leads = res.scalars().all()
    for l in leads:
        l.activities.sort(key=lambda a: a.created_at, reverse=True)
    return leads


@router.get(
    "/{id}",
    response_model=LeadDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full lead details and activity history",
)
async def get_lead_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(get_actor_from_token),
):
    """Retrieve complete lead details by ID or lead_id, along with full interaction history."""
    lead = await find_lead_by_id_or_lead_id(db, id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{id}' not found",
        )
    lead.activities.sort(key=lambda a: a.created_at, reverse=True)
    return lead


@router.post(
    "/{id}/log-action",
    response_model=LeadDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Log sales action, validate stage transitions and record activity",
)
async def log_sales_action(
    id: str,
    payload: LeadActionCreate,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(get_actor_from_token),
):
    """
    Log a call, WhatsApp, meeting, or visit action.
    Validates stage transition rules and compulsory fields:
    - Transitions to CONNECTED, REQ_CAPTURED, QUALIFIED, MEETING, SITE_VISIT, NEGOTIATION require temperature & follow_up_date.
    - Transitions to LOST require lost_reason.
    Resets untouched status and records a LeadActivity log.
    """
    lead = await find_lead_by_id_or_lead_id(db, id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{id}' not found",
        )

    updated_lead, activity = await pipeline_service.log_sales_action(
        db=db,
        lead=lead,
        action_type=payload.action_type,
        outcome=payload.outcome,
        note=payload.note,
        next_action=payload.next_action,
        stage=payload.stage,
        temperature=payload.temperature,
        follow_up_date=payload.follow_up_date,
        lost_reason=payload.lost_reason,
        actor_id=actor_id,
    )

    # Re-query lead with activities to ensure response serialization
    fresh_lead = await find_lead_by_id_or_lead_id(db, lead.lead_id)
    if fresh_lead:
        fresh_lead.activities.sort(key=lambda a: a.created_at, reverse=True)
        return fresh_lead
    return updated_lead


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete a lead",
)
async def delete_lead(
    id: str,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(get_actor_from_token),
) -> Dict[str, Any]:
    lead = await find_lead_by_id_or_lead_id(db, id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{id}' not found",
        )
    lead.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "status": "success",
        "message": f"Lead '{lead.lead_id}' soft-deleted successfully.",
        "deleted_at": lead.deleted_at.isoformat(),
    }
    return updated_lead
