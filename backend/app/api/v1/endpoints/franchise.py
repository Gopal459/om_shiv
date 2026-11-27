"""Dynamic Franchise & Channel Partner Network REST API.

Replaces static UI stats with live database-backed endpoints for:
  - Network overview KPIs (partners, outlets, partner-sourced leads, settled payouts)
  - Franchise Outlet CRUD & active/inactive toggle
  - Channel Partner CRUD, outlet linking, commission %, active/inactive toggle
  - Partner Commission Payouts tracking & settlement
  - Live listing of CRM Leads sourced from Franchise / Channel Partners
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.franchise import ChannelPartner, FranchiseOutlet, PartnerPayout
from app.models.leads import Lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/franchise", tags=["franchise"])

VALID_PAYOUT_STATUSES = {"PENDING", "APPROVED", "SETTLED"}


def _partner_source_filter():
    """SQLAlchemy filter matching CRM leads sourced via franchise or channel partners."""
    return or_(
        func.lower(Lead.source).contains("partner"),
        func.lower(Lead.source).contains("franchise"),
        func.lower(Lead.source).contains("broker"),
    )


async def _next_code(db: AsyncSession, model: Any, col: Any, prefix: str) -> str:
    """Generate sequential readable code like OUT-001, CP-001, PAY-001."""
    count = (await db.execute(select(func.count(model.id)))).scalar() or 0
    num = int(count) + 1
    while True:
        candidate = f"{prefix}-{num:03d}"
        exists = (await db.execute(select(model.id).where(col == candidate))).scalar_one_or_none()
        if not exists:
            return candidate
        num += 1


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
    full_name: str = Field(..., min_length=2, max_length=150)
    company_name: Optional[str] = Field(default=None, max_length=180)
    mobile: str = Field(..., min_length=8, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    city: str = Field(default="Jaipur", min_length=2, max_length=100)
    rera_number: Optional[str] = Field(default=None, max_length=64)
    outlet_id: Optional[int] = None
    commission_pct: float = Field(default=2.0, ge=0.0, le=50.0)


class PartnerUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    company_name: Optional[str] = Field(default=None, max_length=180)
    mobile: Optional[str] = Field(default=None, min_length=8, max_length=20)
    email: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, min_length=2, max_length=100)
    rera_number: Optional[str] = Field(default=None, max_length=64)
    outlet_id: Optional[int] = None
    commission_pct: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    is_active: Optional[bool] = None


class PayoutCreateRequest(BaseModel):
    partner_id: int
    lead_id: Optional[str] = Field(default=None, max_length=32)
    property_title: Optional[str] = Field(default=None, max_length=255)
    deal_amount: float = Field(..., ge=0.0)
    commission_amount: float = Field(..., ge=0.0)
    status: str = Field(default="PENDING")
    note: Optional[str] = None


class PayoutUpdateRequest(BaseModel):
    status: str
    note: Optional[str] = None


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


def _serialize_partner(p: ChannelPartner) -> Dict[str, Any]:
    settled_total = sum(
        float(pay.commission_amount or 0)
        for pay in (p.payouts or [])
        if (pay.status or "").upper() == "SETTLED"
    )
    return {
        "id": p.id,
        "partner_code": p.partner_code,
        "full_name": p.full_name,
        "company_name": p.company_name,
        "mobile": p.mobile,
        "email": p.email,
        "city": p.city,
        "rera_number": p.rera_number,
        "outlet_id": p.outlet_id,
        "outlet_name": p.outlet.name if p.outlet else None,
        "commission_pct": float(p.commission_pct or 0),
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
        "lead_id": pay.lead_id,
        "property_title": pay.property_title,
        "deal_amount": float(pay.deal_amount or 0),
        "commission_amount": float(pay.commission_amount or 0),
        "status": pay.status,
        "paid_at": pay.paid_at.isoformat() if pay.paid_at else None,
        "note": pay.note,
        "created_at": pay.created_at.isoformat() if pay.created_at else None,
    }


# ---------------------------------------------------------------------------
# Overview KPI Endpoint
# ---------------------------------------------------------------------------

@router.get("/overview", summary="Live Franchise & Channel Partner network KPIs")
async def get_franchise_overview(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Compute live network metrics directly from database tables."""
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
                func.upper(Lead.stage).in_(["WON", "CLOSED_WON", "CONVERTED", "BOOKED"]),
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

    return {
        "channel_partners": {
            "total": int(total_partners),
            "active": int(active_partners),
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
    code = await _next_code(db, FranchiseOutlet, FranchiseOutlet.outlet_code, "OUT")
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

    if payload.name is not None:
        outlet.name = payload.name.strip()
    if payload.city is not None:
        outlet.city = payload.city.strip()
    if payload.locality is not None:
        outlet.locality = payload.locality.strip() or None
    if payload.address is not None:
        outlet.address = payload.address.strip() or None
    if payload.manager_name is not None:
        outlet.manager_name = payload.manager_name.strip() or None
    if payload.manager_mobile is not None:
        outlet.manager_mobile = payload.manager_mobile.strip() or None
    if payload.is_active is not None:
        outlet.is_active = payload.is_active
    outlet.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(outlet)
    return _serialize_outlet(outlet)


# ---------------------------------------------------------------------------
# Channel Partners Endpoints
# ---------------------------------------------------------------------------

@router.get("/partners", summary="List channel partners")
async def list_partners(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    stmt = (
        select(ChannelPartner)
        .where(ChannelPartner.deleted_at.is_(None))
        .order_by(ChannelPartner.created_at.desc(), ChannelPartner.id.desc())
    )
    if status_filter == "ACTIVE":
        stmt = stmt.where(ChannelPartner.is_active.is_(True))
    elif status_filter == "INACTIVE":
        stmt = stmt.where(ChannelPartner.is_active.is_(False))

    rows = (await db.execute(stmt)).scalars().all()
    return {"partners": [_serialize_partner(p) for p in rows], "total": len(rows)}


@router.post("/partners", status_code=status.HTTP_201_CREATED, summary="Register new channel partner")
async def create_partner(payload: PartnerCreateRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
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

    code = await _next_code(db, ChannelPartner, ChannelPartner.partner_code, "CP")
    partner = ChannelPartner(
        partner_code=code,
        full_name=payload.full_name.strip(),
        company_name=payload.company_name.strip() if payload.company_name else None,
        mobile=payload.mobile.strip(),
        email=payload.email.strip() if payload.email else None,
        city=payload.city.strip(),
        rera_number=payload.rera_number.strip() if payload.rera_number else None,
        outlet_id=payload.outlet_id,
        commission_pct=payload.commission_pct,
        is_active=True,
    )
    db.add(partner)
    await db.commit()
    await db.refresh(partner)
    return _serialize_partner(partner)


@router.patch("/partners/{partner_id}", summary="Update or toggle channel partner")
async def update_partner(
    partner_id: int,
    payload: PartnerUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
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

    if payload.full_name is not None:
        partner.full_name = payload.full_name.strip()
    if payload.company_name is not None:
        partner.company_name = payload.company_name.strip() or None
    if payload.mobile is not None:
        partner.mobile = payload.mobile.strip()
    if payload.email is not None:
        partner.email = payload.email.strip() or None
    if payload.city is not None:
        partner.city = payload.city.strip()
    if payload.rera_number is not None:
        partner.rera_number = payload.rera_number.strip() or None
    if payload.outlet_id is not None:
        partner.outlet_id = payload.outlet_id
    if payload.commission_pct is not None:
        partner.commission_pct = payload.commission_pct
    if payload.is_active is not None:
        partner.is_active = payload.is_active
    partner.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(partner)
    return _serialize_partner(partner)


# ---------------------------------------------------------------------------
# Payouts & Partner Leads Endpoints
# ---------------------------------------------------------------------------

@router.get("/payouts", summary="List partner commission payouts")
async def list_payouts(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    stmt = select(PartnerPayout).order_by(PartnerPayout.created_at.desc(), PartnerPayout.id.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return {"payouts": [_serialize_payout(p) for p in rows], "total": len(rows)}


@router.post("/payouts", status_code=status.HTTP_201_CREATED, summary="Create partner commission payout")
async def create_payout(payload: PayoutCreateRequest, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    partner = (
        await db.execute(
            select(ChannelPartner).where(
                ChannelPartner.id == payload.partner_id,
                ChannelPartner.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel partner not found.")

    st = payload.status.strip().upper()
    if st not in VALID_PAYOUT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payout status '{payload.status}'. Allowed: {sorted(VALID_PAYOUT_STATUSES)}",
        )

    code = await _next_code(db, PartnerPayout, PartnerPayout.payout_code, "PAY")
    now = datetime.now(timezone.utc)
    payout = PartnerPayout(
        payout_code=code,
        partner_id=payload.partner_id,
        lead_id=payload.lead_id.strip() if payload.lead_id else None,
        property_title=payload.property_title.strip() if payload.property_title else None,
        deal_amount=payload.deal_amount,
        commission_amount=payload.commission_amount,
        status=st,
        paid_at=now if st == "SETTLED" else None,
        note=payload.note.strip() if payload.note else None,
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)
    return _serialize_payout(payout)


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
            "stage": l.stage,
            "temperature": l.temperature,
            "preferred_city": l.preferred_city,
            "budget_max": float(l.budget_max) if l.budget_max is not None else None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in rows
    ]
    return {"leads": items, "total": len(items)}
