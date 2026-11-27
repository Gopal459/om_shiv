"""Dynamic 4-Tier Franchise & Channel Partner Network REST API.

Supports Omshiv's 4 finalized CP tiers:
  1. BROKER_CP        : Own office setup & customizable co-broking split %
  2. ACTIVE_CP        : L1 (0-30d, no inventory, accompanied visits) ->
                        L2 (30d + certified + manager rec, address only, NO owner info) ->
                        L3 (clean record, Omshiv-mediated direct meetings) + Instant Kill Switch
  3. REFERRAL_PARTNER : Fixed reward ONLY on Registry, gated by custom annual limit
  4. CREATOR_PARTNER  : Link/code deal attribution + monthly retainer for top creators
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.franchise import (
    CP_TYPES,
    CPMediatedMeeting,
    ChannelPartner,
    FranchiseOutlet,
    PartnerPayout,
    current_fiscal_year,
)
from app.models.leads import Lead
from app.services.cp_governance_service import (
    certify_active_cp,
    count_referral_rewards_for_fy,
    generate_creator_retainers,
    get_cp_scoped_inventory,
    next_franchise_code,
    promote_active_cp,
    reinstate_partner,
    suspend_partner,
    sync_franchisee_staff_to_partners,
    tenure_days,
    validate_and_create_payout,
)
from app.core.passwords import hash_password
from app.models.identity import Employee
from app.repositories import department_repo, role_repo, staff_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/franchise", tags=["franchise"])
security = HTTPBearer(auto_error=False)

VALID_PAYOUT_STATUSES = {"PENDING", "APPROVED", "SETTLED"}
VALID_MEETING_STATUSES = {"REQUESTED", "APPROVED", "COMPLETED", "REJECTED"}


def get_actor_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    if credentials and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            if payload.get("sub"):
                return str(payload["sub"])
        except Exception:
            pass
    return "ADMIN_MANAGER"


def _partner_source_filter():
    """SQLAlchemy filter matching CRM leads sourced via franchise, partners, or referral codes."""
    return or_(
        Lead.partner_id.isnot(None),
        Lead.referral_code.isnot(None),
        func.lower(Lead.source).contains("partner"),
        func.lower(Lead.source).contains("franchise"),
        func.lower(Lead.source).contains("broker"),
        func.lower(Lead.source).contains("creator"),
    )


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class OutletCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    city: str = Field(default="Jaipur", min_length=2, max_length=100)
    locality: Optional[str] = Field(default=None, max_length=120)
    address: Optional[str] = None
    manager_name: Optional[str] = Field(default=None, max_length=150)
    manager_mobile: Optional[str] = Field(default=None, max_length=20)


class OutletUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    city: Optional[str] = Field(default=None, min_length=2, max_length=100)
    locality: Optional[str] = Field(default=None, max_length=120)
    address: Optional[str] = None
    manager_name: Optional[str] = Field(default=None, max_length=150)
    manager_mobile: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = None


class PartnerCreateRequest(BaseModel):
    cp_type: str = Field(
        default="BROKER_CP",
        description="BROKER_CP, ACTIVE_CP, REFERRAL_PARTNER, CREATOR_PARTNER",
    )
    full_name: str = Field(..., min_length=2, max_length=150)
    company_name: Optional[str] = Field(default=None, max_length=180)
    mobile: str = Field(..., min_length=8, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    city: str = Field(default="Jaipur", min_length=2, max_length=100)
    rera_number: Optional[str] = Field(default=None, max_length=64)
    outlet_id: Optional[int] = None
    commission_pct: float = Field(default=2.0, ge=0.0, le=50.0)
    # Broker CP
    has_office_setup: bool = False
    office_address: Optional[str] = None
    co_broking_split_pct: float = Field(default=50.0, ge=0.0, le=100.0)
    # Active CP
    active_level: str = Field(default="L1")
    joined_at: Optional[datetime] = None
    # Referral Partner
    fixed_reward_amount: float = Field(default=5000.0, ge=0.0)
    annual_reward_limit: int = Field(default=5, ge=1, le=100)
    # Creator Partner
    tracking_code: Optional[str] = Field(default=None, max_length=40)
    social_handle: Optional[str] = Field(default=None, max_length=150)
    is_top_creator: bool = False
    monthly_retainer_amount: float = Field(default=0.0, ge=0.0)
    # Optional Staff Login linkage (unifies Staff Directory & Franchise CP)
    employee_id: Optional[str] = Field(default=None, max_length=32)
    username: Optional[str] = Field(default=None, max_length=50)
    password: Optional[str] = Field(default=None, min_length=6, max_length=100)


class PartnerUpdateRequest(BaseModel):
    cp_type: Optional[str] = None
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    company_name: Optional[str] = Field(default=None, max_length=180)
    mobile: Optional[str] = Field(default=None, min_length=8, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, min_length=2, max_length=100)
    rera_number: Optional[str] = Field(default=None, max_length=64)
    outlet_id: Optional[int] = None
    commission_pct: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    has_office_setup: Optional[bool] = None
    office_address: Optional[str] = None
    co_broking_split_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    fixed_reward_amount: Optional[float] = Field(default=None, ge=0.0)
    annual_reward_limit: Optional[int] = Field(default=None, ge=1, le=100)
    tracking_code: Optional[str] = Field(default=None, max_length=40)
    social_handle: Optional[str] = Field(default=None, max_length=150)
    is_top_creator: Optional[bool] = None
    monthly_retainer_amount: Optional[float] = Field(default=None, ge=0.0)
    is_active: Optional[bool] = None


class PromotePartnerRequest(BaseModel):
    target_level: str = Field(..., description="L2 or L3")
    manager_emp_id: Optional[str] = None
    notes: Optional[str] = None


class SuspendPartnerRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class ReinstatePartnerRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=500)


class PayoutCreateRequest(BaseModel):
    partner_id: int
    payout_type: Optional[str] = None
    lead_id: Optional[str] = Field(default=None, max_length=32)
    property_title: Optional[str] = Field(default=None, max_length=255)
    deal_amount: float = Field(default=0.0, ge=0.0)
    commission_amount: float = Field(default=0.0, ge=0.0)
    status: str = Field(default="PENDING")
    note: Optional[str] = None


class PayoutUpdateRequest(BaseModel):
    status: str
    note: Optional[str] = None


class MeetingCreateRequest(BaseModel):
    partner_id: int
    property_id: str = Field(..., min_length=2, max_length=32)
    lead_id: Optional[str] = Field(default=None, max_length=32)
    requested_slot: datetime
    supervisor_emp_id: Optional[str] = None
    notes: Optional[str] = None


class MeetingUpdateRequest(BaseModel):
    status: str
    supervisor_emp_id: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _serialize_outlet(o: FranchiseOutlet) -> Dict[str, Any]:
    active_partners = sum(1 for p in (o.partners or []) if p.deleted_at is None and p.is_active)
    total_partners = sum(1 for p in (o.partners or []) if p.deleted_at is None)
    return {
        "id": o.id,
        "outlet_code": o.outlet_code,
        "name": o.name,
        "city": o.city,
        "locality": o.locality,
        "address": o.address,
        "manager_name": o.manager_name,
        "manager_mobile": o.manager_mobile,
        "is_active": bool(o.is_active),
        "partner_count": total_partners,
        "active_partner_count": active_partners,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


def _serialize_partner(
    p: ChannelPartner,
    fy_rewards_used: int = 0,
    tracked_leads_count: int = 0,
) -> Dict[str, Any]:
    settled_total = sum(
        float(pay.commission_amount or 0)
        for pay in (p.payouts or [])
        if (pay.status or "").upper() == "SETTLED"
    )
    return {
        "id": p.id,
        "partner_code": p.partner_code,
        "employee_id": p.employee_id,
        "cp_type": p.cp_type or "BROKER_CP",
        "full_name": p.full_name,
        "company_name": p.company_name,
        "mobile": p.mobile,
        "email": p.email,
        "city": p.city,
        "rera_number": p.rera_number,
        "outlet_id": p.outlet_id,
        "outlet_name": p.outlet.name if p.outlet else None,
        "commission_pct": float(p.commission_pct or 0),
        # Broker CP
        "has_office_setup": bool(p.has_office_setup),
        "office_address": p.office_address,
        "co_broking_split_pct": float(p.co_broking_split_pct or 50.0),
        # Active CP
        "active_level": p.active_level or "L1",
        "tenure_days": tenure_days(p),
        "joined_at": p.joined_at.isoformat() if p.joined_at else None,
        "is_certified": bool(p.is_certified),
        "recommended_by": p.recommended_by,
        "l3_approved_by": p.l3_approved_by,
        "clean_record": bool(p.clean_record),
        "suspended_at": p.suspended_at.isoformat() if p.suspended_at else None,
        "suspension_reason": p.suspension_reason,
        # Referral Partner
        "fixed_reward_amount": float(p.fixed_reward_amount or 0),
        "annual_reward_limit": int(p.annual_reward_limit or 5),
        "fy_rewards_used": fy_rewards_used,
        "current_fy": current_fiscal_year(),
        # Creator Partner
        "tracking_code": p.tracking_code,
        "social_handle": p.social_handle,
        "is_top_creator": bool(p.is_top_creator),
        "monthly_retainer_amount": float(p.monthly_retainer_amount or 0),
        "tracked_leads_count": tracked_leads_count,
        "is_active": bool(p.is_active),
        "settled_commission_total": settled_total,
        "payout_count": len(p.payouts or []),
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _serialize_payout(pay: PartnerPayout) -> Dict[str, Any]:
    return {
        "id": pay.id,
        "payout_code": pay.payout_code,
        "partner_id": pay.partner_id,
        "partner_name": pay.partner.full_name if pay.partner else None,
        "partner_code": pay.partner.partner_code if pay.partner else None,
        "cp_type": pay.partner.cp_type if pay.partner else None,
        "payout_type": pay.payout_type,
        "fiscal_year": pay.fiscal_year,
        "lead_id": pay.lead_id,
        "property_title": pay.property_title,
        "deal_amount": float(pay.deal_amount or 0),
        "commission_amount": float(pay.commission_amount or 0),
        "status": pay.status,
        "paid_at": pay.paid_at.isoformat() if pay.paid_at else None,
        "note": pay.note,
        "created_at": pay.created_at.isoformat() if pay.created_at else None,
    }


def _serialize_meeting(m: CPMediatedMeeting) -> Dict[str, Any]:
    return {
        "id": m.id,
        "meeting_code": m.meeting_code,
        "partner_id": m.partner_id,
        "partner_name": m.partner.full_name if m.partner else None,
        "partner_code": m.partner.partner_code if m.partner else None,
        "property_id": m.property_id,
        "lead_id": m.lead_id,
        "requested_slot": m.requested_slot.isoformat() if m.requested_slot else None,
        "supervisor_emp_id": m.supervisor_emp_id,
        "status": m.status,
        "notes": m.notes,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


async def _get_partner_or_404(db: AsyncSession, partner_id: int) -> ChannelPartner:
    partner = (
        await db.execute(
            select(ChannelPartner).where(
                ChannelPartner.id == partner_id,
                ChannelPartner.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel partner not found.")
    return partner


# ---------------------------------------------------------------------------
# Overview KPI Endpoint
# ---------------------------------------------------------------------------

@router.get("/overview", summary="Live 4-Tier Franchise & Channel Partner network KPIs")
async def get_franchise_overview(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Compute live network metrics & tier breakdown directly from DB tables."""
    await sync_franchisee_staff_to_partners(db)
    total_partners = (
        await db.execute(
            select(func.count(ChannelPartner.id)).where(ChannelPartner.deleted_at.is_(None))
        )
    ).scalar() or 0

    active_partners = (
        await db.execute(
            select(func.count(ChannelPartner.id)).where(
                ChannelPartner.deleted_at.is_(None),
                ChannelPartner.is_active.is_(True),
            )
        )
    ).scalar() or 0

    tier_rows = (
        await db.execute(
            select(ChannelPartner.cp_type, func.count(ChannelPartner.id))
            .where(ChannelPartner.deleted_at.is_(None))
            .group_by(ChannelPartner.cp_type)
        )
    ).all()
    by_tier = {t: int(c) for t, c in tier_rows if t}

    total_outlets = (
        await db.execute(
            select(func.count(FranchiseOutlet.id)).where(FranchiseOutlet.deleted_at.is_(None))
        )
    ).scalar() or 0

    active_outlets = (
        await db.execute(
            select(func.count(FranchiseOutlet.id)).where(
                FranchiseOutlet.deleted_at.is_(None),
                FranchiseOutlet.is_active.is_(True),
            )
        )
    ).scalar() or 0

    cities_rows = (
        await db.execute(
            select(func.distinct(FranchiseOutlet.city)).where(
                FranchiseOutlet.deleted_at.is_(None),
                FranchiseOutlet.is_active.is_(True),
            )
        )
    ).scalars().all()

    partner_leads_total = (
        await db.execute(
            select(func.count(Lead.id)).where(
                Lead.deleted_at.is_(None),
                _partner_source_filter(),
            )
        )
    ).scalar() or 0

    partner_leads_converted = (
        await db.execute(
            select(func.count(Lead.id)).where(
                Lead.deleted_at.is_(None),
                _partner_source_filter(),
                func.upper(Lead.stage).in_(["WON", "CLOSED_WON", "CONVERTED", "BOOKED", "REGISTERED"]),
            )
        )
    ).scalar() or 0

    settled_payouts_count = (
        await db.execute(
            select(func.count(PartnerPayout.id)).where(PartnerPayout.status == "SETTLED")
        )
    ).scalar() or 0

    settled_payouts_amount = (
        await db.execute(
            select(func.coalesce(func.sum(PartnerPayout.commission_amount), 0)).where(
                PartnerPayout.status == "SETTLED"
            )
        )
    ).scalar() or 0

    pending_payouts_count = (
        await db.execute(
            select(func.count(PartnerPayout.id)).where(PartnerPayout.status != "SETTLED")
        )
    ).scalar() or 0

    pending_meetings_count = (
        await db.execute(
            select(func.count(CPMediatedMeeting.id)).where(CPMediatedMeeting.status == "REQUESTED")
        )
    ).scalar() or 0

    return {
        "channel_partners": {
            "total": int(total_partners),
            "active": int(active_partners),
            "by_tier": by_tier,
        },
        "franchise_outlets": {
            "total": int(total_outlets),
            "active": int(active_outlets),
            "cities": [c for c in cities_rows if c],
        },
        "partner_sourced_leads": {
            "total": int(partner_leads_total),
            "converted": int(partner_leads_converted),
        },
        "settled_payouts": {
            "count": int(settled_payouts_count),
            "pending_count": int(pending_payouts_count),
            "total_amount": float(settled_payouts_amount or 0),
        },
        "pending_meetings": int(pending_meetings_count),
    }


# ---------------------------------------------------------------------------
# Outlets Endpoints
# ---------------------------------------------------------------------------

@router.get("/outlets", summary="List franchise outlets")
async def list_outlets(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    stmt = (
        select(FranchiseOutlet)
        .where(FranchiseOutlet.deleted_at.is_(None))
        .order_by(FranchiseOutlet.created_at.desc(), FranchiseOutlet.id.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {"outlets": [_serialize_outlet(o) for o in rows], "total": len(rows)}


@router.post("/outlets", status_code=status.HTTP_201_CREATED, summary="Create franchise outlet")
async def create_outlet(payload: OutletCreateRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    code = await next_franchise_code(db, FranchiseOutlet, FranchiseOutlet.outlet_code, "OUT")
    outlet = FranchiseOutlet(
        outlet_code=code,
        name=payload.name.strip(),
        city=payload.city.strip(),
        locality=payload.locality.strip() if payload.locality else None,
        address=payload.address.strip() if payload.address else None,
        manager_name=payload.manager_name.strip() if payload.manager_name else None,
        manager_mobile=payload.manager_mobile.strip() if payload.manager_mobile else None,
        is_active=True,
    )
    db.add(outlet)
    await db.commit()
    await db.refresh(outlet)
    return _serialize_outlet(outlet)


@router.patch("/outlets/{outlet_id}", summary="Update or toggle franchise outlet")
async def update_outlet(
    outlet_id: int,
    payload: OutletUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    outlet = (
        await db.execute(
            select(FranchiseOutlet).where(
                FranchiseOutlet.id == outlet_id,
                FranchiseOutlet.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not outlet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Franchise outlet not found.")

    for field in ("name", "city", "locality", "address", "manager_name", "manager_mobile"):
        val = getattr(payload, field)
        if val is not None:
            setattr(outlet, field, val.strip() or None)
    if payload.is_active is not None:
        outlet.is_active = payload.is_active
    outlet.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(outlet)
    return _serialize_outlet(outlet)


# ---------------------------------------------------------------------------
# Channel Partners Endpoints
# ---------------------------------------------------------------------------

@router.get("/partners", summary="List 4-tier channel partners")
async def list_partners(
    cp_type: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await sync_franchisee_staff_to_partners(db)
    stmt = (
        select(ChannelPartner)
        .where(ChannelPartner.deleted_at.is_(None))
        .order_by(ChannelPartner.created_at.desc(), ChannelPartner.id.desc())
    )
    if cp_type and cp_type.upper() != "ALL":
        stmt = stmt.where(ChannelPartner.cp_type == cp_type.upper())
    if status_filter == "ACTIVE":
        stmt = stmt.where(ChannelPartner.is_active.is_(True))
    elif status_filter == "INACTIVE":
        stmt = stmt.where(ChannelPartner.is_active.is_(False))

    rows = (await db.execute(stmt)).scalars().all()

    fy = current_fiscal_year()
    fy_counts_rows = (
        await db.execute(
            select(PartnerPayout.partner_id, func.count(PartnerPayout.id))
            .where(
                PartnerPayout.payout_type == "REFERRAL_FIXED",
                PartnerPayout.fiscal_year == fy,
            )
            .group_by(PartnerPayout.partner_id)
        )
    ).all()
    fy_map = {pid: int(cnt) for pid, cnt in fy_counts_rows}

    lead_counts_rows = (
        await db.execute(
            select(Lead.partner_id, func.count(Lead.id))
            .where(Lead.deleted_at.is_(None), Lead.partner_id.isnot(None))
            .group_by(Lead.partner_id)
        )
    ).all()
    lead_map = {pid: int(cnt) for pid, cnt in lead_counts_rows}

    return {
        "partners": [
            _serialize_partner(p, fy_rewards_used=fy_map.get(p.id, 0), tracked_leads_count=lead_map.get(p.id, 0))
            for p in rows
        ],
        "total": len(rows),
    }


@router.post("/partners", status_code=status.HTTP_201_CREATED, summary="Register 4-tier channel partner")
async def create_partner(payload: PartnerCreateRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    norm_type = payload.cp_type.strip().upper()
    if norm_type not in CP_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid cp_type '{payload.cp_type}'. Allowed: {sorted(CP_TYPES)}",
        )

    if payload.outlet_id is not None:
        outlet_exists = (
            await db.execute(
                select(FranchiseOutlet.id).where(
                    FranchiseOutlet.id == payload.outlet_id,
                    FranchiseOutlet.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not outlet_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned franchise outlet not found.")

    code = await next_franchise_code(db, ChannelPartner, ChannelPartner.partner_code, "CP")
    tracking_code = payload.tracking_code.strip().upper() if payload.tracking_code else None
    if norm_type == "CREATOR_PARTNER" and not tracking_code:
        tracking_code = f"CR{code.replace('-', '')}"

    if tracking_code:
        dup = (
            await db.execute(
                select(ChannelPartner.id).where(ChannelPartner.tracking_code == tracking_code)
            )
        ).scalar_one_or_none()
        if dup:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Tracking code '{tracking_code}' is already in use.",
            )

    linked_emp_id = payload.employee_id.strip() if payload.employee_id else None
    if not linked_emp_id and payload.username and payload.password:
        clean_uname = payload.username.strip().lower()
        existing_emp = await staff_repo.check_duplicate(
            db, username=clean_uname, mobile=payload.mobile.strip(), email=payload.email
        )
        if existing_emp:
            linked_emp_id = existing_emp.employee_id
        else:
            dept = await department_repo.get_by_code(db, "SALES")
            role = await role_repo.get_by_code(db, "FRANCHISEE_AGENT")
            if dept and role:
                linked_emp_id = await staff_repo.generate_emp_id(db)
                new_emp = Employee(
                    employee_id=linked_emp_id,
                    name=payload.full_name.strip(),
                    username=clean_uname,
                    password_hash=hash_password(payload.password),
                    mobile=payload.mobile.strip(),
                    email=payload.email.strip().lower() if payload.email else None,
                    department_id=dept.id,
                    role_id=role.id,
                    is_active=True,
                )
                await staff_repo.create(db, new_emp)

    partner = ChannelPartner(
        partner_code=code,
        employee_id=linked_emp_id,
        cp_type=norm_type,
        full_name=payload.full_name.strip(),
        company_name=payload.company_name.strip() if payload.company_name else None,
        mobile=payload.mobile.strip(),
        email=payload.email.strip() if payload.email else None,
        city=payload.city.strip(),
        rera_number=payload.rera_number.strip() if payload.rera_number else None,
        outlet_id=payload.outlet_id,
        commission_pct=payload.commission_pct,
        has_office_setup=payload.has_office_setup,
        office_address=payload.office_address.strip() if payload.office_address else None,
        co_broking_split_pct=payload.co_broking_split_pct,
        active_level="L1",  # Active CPs always onboard at L1 (0-30 days)
        joined_at=payload.joined_at or datetime.now(timezone.utc),
        fixed_reward_amount=payload.fixed_reward_amount,
        annual_reward_limit=payload.annual_reward_limit,
        tracking_code=tracking_code,
        social_handle=payload.social_handle.strip() if payload.social_handle else None,
        is_top_creator=payload.is_top_creator,
        monthly_retainer_amount=payload.monthly_retainer_amount,
        is_active=True,
    )
    db.add(partner)
    await db.commit()
    await db.refresh(partner)
    return _serialize_partner(partner)


@router.patch("/partners/{partner_id}", summary="Update channel partner fields")
async def update_partner(
    partner_id: int,
    payload: PartnerUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    partner = await _get_partner_or_404(db, partner_id)

    if payload.cp_type is not None:
        nt = payload.cp_type.strip().upper()
        if nt not in CP_TYPES:
            raise HTTPException(status_code=422, detail=f"Invalid cp_type '{payload.cp_type}'")
        partner.cp_type = nt

    for field in ("full_name", "company_name", "mobile", "email", "city", "rera_number", "office_address", "social_handle"):
        val = getattr(payload, field)
        if val is not None:
            setattr(partner, field, val.strip() or None)

    for num_field in (
        "outlet_id",
        "commission_pct",
        "has_office_setup",
        "co_broking_split_pct",
        "fixed_reward_amount",
        "annual_reward_limit",
        "is_top_creator",
        "monthly_retainer_amount",
        "is_active",
    ):
        val = getattr(payload, num_field)
        if val is not None:
            setattr(partner, num_field, val)

    if payload.tracking_code is not None:
        partner.tracking_code = payload.tracking_code.strip().upper() or None

    partner.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(partner)
    used = await count_referral_rewards_for_fy(db, partner.id)
    return _serialize_partner(partner, fy_rewards_used=used)


# ---------------------------------------------------------------------------
# Active CP Ladder, Instant Kill Switch & Scoped Inventory
# ---------------------------------------------------------------------------

@router.post("/partners/{partner_id}/certify", summary="Mark Active CP training certification completed")
async def certify_partner_endpoint(
    partner_id: int,
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    partner = await _get_partner_or_404(db, partner_id)
    updated = await certify_active_cp(db, partner, actor=actor)
    return _serialize_partner(updated)


@router.patch("/partners/{partner_id}/promote", summary="Promote Active CP (L1->L2 or L2->L3)")
async def promote_partner_endpoint(
    partner_id: int,
    payload: PromotePartnerRequest,
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    partner = await _get_partner_or_404(db, partner_id)
    mgr = payload.manager_emp_id or actor
    updated = await promote_active_cp(
        db,
        partner=partner,
        target_level=payload.target_level,
        manager_emp_id=mgr,
        notes=payload.notes,
    )
    return _serialize_partner(updated)


@router.post("/partners/{partner_id}/suspend", summary="Instant kill-switch suspension on compliance issue")
async def suspend_partner_endpoint(
    partner_id: int,
    payload: SuspendPartnerRequest,
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    partner = await _get_partner_or_404(db, partner_id)
    updated = await suspend_partner(db, partner, reason=payload.reason, actor=actor)
    return _serialize_partner(updated)


@router.post("/partners/{partner_id}/reinstate", summary="Reinstate suspended partner after review")
async def reinstate_partner_endpoint(
    partner_id: int,
    payload: ReinstatePartnerRequest = ReinstatePartnerRequest(),
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    partner = await _get_partner_or_404(db, partner_id)
    updated = await reinstate_partner(db, partner, actor=actor, note=payload.note)
    return _serialize_partner(updated)


@router.get("/partners/{partner_id}/inventory", summary="Server-scoped property inventory access for CP")
async def get_partner_inventory_endpoint(
    partner_id: int,
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    partner = await _get_partner_or_404(db, partner_id)
    return await get_cp_scoped_inventory(db, partner, limit=limit)


# ---------------------------------------------------------------------------
# L3 Omshiv-Mediated Meetings Endpoints
# ---------------------------------------------------------------------------

@router.get("/meetings", summary="List L3 Active CP mediated owner-buyer meetings")
async def list_mediated_meetings(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    stmt = select(CPMediatedMeeting).order_by(CPMediatedMeeting.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return {"meetings": [_serialize_meeting(m) for m in rows], "total": len(rows)}


@router.post("/meetings", status_code=status.HTTP_201_CREATED, summary="Request Omshiv-mediated direct meeting (L3 Active CP only)")
async def create_mediated_meeting(
    payload: MeetingCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    partner = await _get_partner_or_404(db, payload.partner_id)
    if not partner.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Partner is suspended/inactive.")
    if partner.cp_type != "ACTIVE_CP" or partner.active_level != "L3":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Omshiv-mediated direct meetings are unlocked only for L3 Active CPs.",
        )

    code = await next_franchise_code(db, CPMediatedMeeting, CPMediatedMeeting.meeting_code, "MTG")
    meeting = CPMediatedMeeting(
        meeting_code=code,
        partner_id=partner.id,
        property_id=payload.property_id.strip(),
        lead_id=payload.lead_id.strip() if payload.lead_id else None,
        requested_slot=payload.requested_slot,
        supervisor_emp_id=payload.supervisor_emp_id.strip() if payload.supervisor_emp_id else None,
        status="REQUESTED",
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return _serialize_meeting(meeting)


@router.patch("/meetings/{meeting_id}", summary="Approve, complete, or reject L3 mediated meeting")
async def update_mediated_meeting(
    meeting_id: int,
    payload: MeetingUpdateRequest,
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    meeting = await db.get(CPMediatedMeeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mediated meeting not found.")
    st = payload.status.strip().upper()
    if st not in VALID_MEETING_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status '{payload.status}'")
    meeting.status = st
    meeting.supervisor_emp_id = payload.supervisor_emp_id or meeting.supervisor_emp_id or actor
    if payload.notes is not None:
        meeting.notes = payload.notes.strip() or None
    meeting.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(meeting)
    return _serialize_meeting(meeting)


# ---------------------------------------------------------------------------
# Payouts & Partner Leads Endpoints
# ---------------------------------------------------------------------------

@router.get("/payouts", summary="List partner commission, referral, and retainer payouts")
async def list_payouts(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    stmt = select(PartnerPayout).order_by(PartnerPayout.created_at.desc(), PartnerPayout.id.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return {"payouts": [_serialize_payout(p) for p in rows], "total": len(rows)}


@router.post("/payouts", status_code=status.HTTP_201_CREATED, summary="Create payout respecting CP type rules")
async def create_payout(payload: PayoutCreateRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    partner = await _get_partner_or_404(db, payload.partner_id)
    st = payload.status.strip().upper()
    if st not in VALID_PAYOUT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payout status '{payload.status}'. Allowed: {sorted(VALID_PAYOUT_STATUSES)}",
        )

    default_type = (
        "CO_BROKING"
        if partner.cp_type == "BROKER_CP"
        else "REFERRAL_FIXED"
        if partner.cp_type == "REFERRAL_PARTNER"
        else "CREATOR_COMMISSION"
        if partner.cp_type == "CREATOR_PARTNER"
        else "COMMISSION"
    )
    payout = await validate_and_create_payout(
        db=db,
        partner=partner,
        payout_type=payload.payout_type or default_type,
        deal_amount=payload.deal_amount,
        commission_amount=payload.commission_amount,
        lead_id=payload.lead_id,
        property_title=payload.property_title,
        payout_status=st,
        note=payload.note,
    )
    return _serialize_payout(payout)


@router.post("/payouts/generate-retainers", summary="Generate monthly retainers for Top Creator Partners")
async def generate_retainers_endpoint(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    return await generate_creator_retainers(db)


@router.patch("/payouts/{payout_id}", summary="Update commission payout status (Approve / Settle)")
async def update_payout(
    payout_id: int,
    payload: PayoutUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    payout = await db.get(PartnerPayout, payout_id)
    if not payout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout record not found.")

    st = payload.status.strip().upper()
    if st not in VALID_PAYOUT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payout status '{payload.status}'. Allowed: {sorted(VALID_PAYOUT_STATUSES)}",
        )

    now = datetime.now(timezone.utc)
    payout.status = st
    if st == "SETTLED" and not payout.paid_at:
        payout.paid_at = now
    if payload.note is not None:
        payout.note = payload.note.strip() or None
    payout.updated_at = now

    await db.commit()
    await db.refresh(payout)
    return _serialize_payout(payout)


@router.get("/leads", summary="List real CRM leads sourced via franchise/channel partners")
async def list_partner_sourced_leads(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    stmt = (
        select(Lead)
        .where(
            Lead.deleted_at.is_(None),
            _partner_source_filter(),
        )
        .order_by(Lead.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    items = [
        {
            "lead_id": l.lead_id,
            "full_name": l.full_name,
            "mobile": l.mobile,
            "source": l.source,
            "referral_code": l.referral_code,
            "partner_id": l.partner_id,
            "accompanied_by": l.accompanied_by,
            "stage": l.stage,
            "temperature": l.temperature,
            "preferred_city": l.preferred_city,
            "budget_max": float(l.budget_max) if l.budget_max is not None else None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in rows
    ]
    return {"leads": items, "total": len(items)}

