"""Governance engine for the 4-Tier Channel Partner (CP) system.

Implements server-side enforcement for:
  1. Broker CP        : Office setup & Co-Broking split rules.
  2. Active CP        : Strict L1 -> L2 -> L3 progression ladder, owner masking,
                        Omshiv-mediated meetings, and Instant Kill-Switch suspension.
  3. Referral Partner : Registry-only fixed rewards gated by annual FY limits.
  4. Creator Partner  : Tracking code/link lead attribution & monthly top-creator retainers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.franchise import (
    CPMediatedMeeting,
    ChannelPartner,
    PartnerPayout,
    PAYOUT_TYPES,
    current_fiscal_year,
)
from app.models.leads import Lead
from app.models.properties import Property
from app.models.settings import AuditLog

REGISTERED_LEAD_STAGES = {"CONVERTED", "WON", "CLOSED_WON", "REGISTERED"}
L2_MIN_DAYS = 30
L3_MIN_DAYS = 60


def _ensure_tz(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def tenure_days(partner: ChannelPartner, now: Optional[datetime] = None) -> int:
    ref = now or datetime.now(timezone.utc)
    joined = _ensure_tz(partner.joined_at or partner.created_at)
    return max(0, (ref - joined).days)


async def next_franchise_code(db: AsyncSession, model: Any, col: Any, prefix: str) -> str:
    """Generate sequential readable code like OUT-001, CP-001, PAY-001, MTG-001."""
    count = (await db.execute(select(func.count(model.id)))).scalar() or 0
    num = int(count) + 1
    while True:
        candidate = f"{prefix}-{num:03d}"
        exists = (await db.execute(select(model.id).where(col == candidate))).scalar_one_or_none()
        if not exists:
            return candidate
        num += 1


async def count_referral_rewards_for_fy(
    db: AsyncSession,
    partner_id: int,
    fiscal_year: Optional[str] = None,
) -> int:
    """Count REFERRAL_FIXED payouts for a partner in the given Indian Fiscal Year."""
    fy = fiscal_year or current_fiscal_year()
    count = (
        await db.execute(
            select(func.count(PartnerPayout.id)).where(
                PartnerPayout.partner_id == partner_id,
                PartnerPayout.payout_type == "REFERRAL_FIXED",
                PartnerPayout.fiscal_year == fy,
            )
        )
    ).scalar() or 0
    return int(count)


async def certify_active_cp(
    db: AsyncSession,
    partner: ChannelPartner,
    actor: str = "ADMIN_SYSTEM",
) -> ChannelPartner:
    """Mark an Active CP as training-certified."""
    if partner.cp_type != "ACTIVE_CP":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Certification applies only to ACTIVE_CP partners.",
        )
    now = datetime.now(timezone.utc)
    partner.is_certified = True
    partner.certified_at = now
    partner.updated_at = now

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            entity_name="ChannelPartner",
            entity_id=partner.partner_code,
            action="CP_CERTIFIED",
            old_state={"is_certified": False},
            new_state={"is_certified": True},
            performed_by=actor,
            timestamp=now,
        )
    )
    await db.commit()
    await db.refresh(partner)
    return partner


async def promote_active_cp(
    db: AsyncSession,
    partner: ChannelPartner,
    target_level: str,
    manager_emp_id: str,
    notes: Optional[str] = None,
) -> ChannelPartner:
    """Promote an Active CP strictly enforcing L1 -> L2 -> L3 rules."""
    if partner.cp_type != "ACTIVE_CP":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Level ladder promotion applies only to ACTIVE_CP partners.",
        )
    if not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended or inactive partner cannot be promoted.",
        )

    level = target_level.strip().upper()
    if level not in {"L2", "L3"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Target promotion level must be L2 or L3.",
        )

    days = tenure_days(partner)
    now = datetime.now(timezone.utc)
    old_level = partner.active_level

    if level == "L2":
        if days < L2_MIN_DAYS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"L2 requires at least {L2_MIN_DAYS} days tenure (current: {days} days).",
            )
        if not partner.is_certified:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="L2 promotion requires training certification to be completed first.",
            )
        if not manager_emp_id or not manager_emp_id.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Manager recommendation (employee ID) is mandatory for L2 promotion.",
            )
        partner.active_level = "L2"
        partner.recommended_by = manager_emp_id.strip()
        partner.recommended_at = now

    elif level == "L3":
        if partner.active_level != "L2":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Partner must complete L2 before promotion to L3.",
            )
        if days < L3_MIN_DAYS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"L3 requires at least {L3_MIN_DAYS} days tenure (1-2 months after onboarding; current: {days} days).",
            )
        if not partner.clean_record:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="L3 promotion blocked: partner does not have a clean compliance record.",
            )
        partner.active_level = "L3"
        partner.l3_approved_by = manager_emp_id.strip() or "MANAGER"
        partner.l3_approved_at = now

    partner.updated_at = now
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            entity_name="ChannelPartner",
            entity_id=partner.partner_code,
            action=f"CP_PROMOTED_{level}",
            old_state={"active_level": old_level},
            new_state={"active_level": level, "manager": manager_emp_id, "notes": notes},
            performed_by=manager_emp_id or "ADMIN_SYSTEM",
            timestamp=now,
        )
    )
    await db.commit()
    await db.refresh(partner)
    return partner


async def suspend_partner(
    db: AsyncSession,
    partner: ChannelPartner,
    reason: str,
    actor: str = "ADMIN_SYSTEM",
) -> ChannelPartner:
    """Zero-tolerance instant kill switch disabling all access and marking record unclean."""
    now = datetime.now(timezone.utc)
    old_active = partner.is_active
    partner.is_active = False
    partner.clean_record = False
    partner.suspended_at = now
    partner.suspended_by = actor
    partner.suspension_reason = reason.strip()
    partner.violation_notes = reason.strip()
    partner.updated_at = now

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            entity_name="ChannelPartner",
            entity_id=partner.partner_code,
            action="CP_INSTANT_SUSPEND",
            old_state={"is_active": old_active, "active_level": partner.active_level},
            new_state={"is_active": False, "clean_record": False, "reason": reason.strip()},
            performed_by=actor,
            timestamp=now,
        )
    )
    await db.commit()
    await db.refresh(partner)
    return partner


async def reinstate_partner(
    db: AsyncSession,
    partner: ChannelPartner,
    actor: str = "ADMIN_SYSTEM",
    note: Optional[str] = None,
) -> ChannelPartner:
    """Reinstate a previously suspended partner after admin review."""
    now = datetime.now(timezone.utc)
    partner.is_active = True
    partner.clean_record = True
    partner.suspended_at = None
    partner.suspension_reason = None
    partner.updated_at = now

    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            entity_name="ChannelPartner",
            entity_id=partner.partner_code,
            action="CP_REINSTATED",
            old_state={"is_active": False},
            new_state={"is_active": True, "note": note},
            performed_by=actor,
            timestamp=now,
        )
    )
    await db.commit()
    await db.refresh(partner)
    return partner


async def get_cp_scoped_inventory(
    db: AsyncSession,
    partner: ChannelPartner,
    limit: int = 30,
) -> Dict[str, Any]:
    """Return property inventory strictly scoped by CP type, Active CP level, and status.

    Enforces server-side owner privacy:
      - Inactive/Suspended CP -> 403 Forbidden
      - Active CP L1          -> Empty inventory (Omshiv-accompanied visits only)
      - Active CP L2 & L3     -> Address/locality/price visible; owner_name & owner_mobile masked
      - Broker CP             -> Co-broking inventory; direct owner contact masked
      - Referral Partner      -> Lead-submission only (no inventory browsing)
      - Creator Partner       -> Public promo catalog + tracking share links
    """
    if not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access revoked: partner {partner.partner_code} is suspended/inactive.",
        )

    cp_type = (partner.cp_type or "BROKER_CP").upper()
    level = (partner.active_level or "L1").upper()

    if cp_type == "ACTIVE_CP" and level == "L1":
        return {
            "partner_code": partner.partner_code,
            "cp_type": cp_type,
            "active_level": level,
            "access_level": "LOCKED_L1",
            "can_browse_inventory": False,
            "can_view_address": False,
            "can_view_owner_contact": False,
            "can_request_mediated_meeting": False,
            "requires_accompanied_visit": True,
            "message": "L1 Active CP (0-30 days): Inventory access locked. Site visits only accompanied by Omshiv team.",
            "items": [],
        }

    if cp_type == "REFERRAL_PARTNER":
        return {
            "partner_code": partner.partner_code,
            "cp_type": cp_type,
            "access_level": "LEAD_ONLY",
            "can_browse_inventory": False,
            "can_view_address": False,
            "can_view_owner_contact": False,
            "can_request_mediated_meeting": False,
            "requires_accompanied_visit": True,
            "message": "Referral Partners submit leads only and earn fixed registry rewards.",
            "items": [],
        }

    stmt = (
        select(Property)
        .where(
            Property.deleted_at.is_(None),
            Property.is_live.is_(True),
        )
        .order_by(Property.created_at.desc())
        .limit(limit)
    )
    props = (await db.execute(stmt)).scalars().all()

    items: List[Dict[str, Any]] = []
    for prop in props:
        item: Dict[str, Any] = {
            "property_id": prop.property_id,
            "title": prop.title,
            "city": prop.city,
            "locality": prop.locality,
            "expected_price": float(prop.expected_price or 0),
            "price_negotiable": bool(prop.price_negotiable),
            "owner_name": "Omshiv Managed",
            "owner_mobile": None,  # Never leaked directly to Active CPs, Creators, or Referrers
            "owner_masked": True,
        }
        if cp_type == "CREATOR_PARTNER" and partner.tracking_code:
            item["share_url"] = f"/?ref={partner.tracking_code}&property={prop.property_id}"
        items.append(item)

    can_meeting = cp_type == "ACTIVE_CP" and level == "L3"
    return {
        "partner_code": partner.partner_code,
        "cp_type": cp_type,
        "active_level": level if cp_type == "ACTIVE_CP" else None,
        "access_level": (
            f"ACTIVE_{level}" if cp_type == "ACTIVE_CP" else cp_type
        ),
        "can_browse_inventory": True,
        "can_view_address": True,
        "can_view_owner_contact": False,
        "can_request_mediated_meeting": can_meeting,
        "requires_accompanied_visit": False,
        "message": (
            "L3 Active CP: Address visible, owner details masked. Eligible for Omshiv-mediated direct meetings."
            if can_meeting
            else "L2 Active CP: Verified address & locality visible. Owner name/phone strictly masked."
            if cp_type == "ACTIVE_CP"
            else "Co-broking inventory access enabled."
            if cp_type == "BROKER_CP"
            else "Promotional creator catalog with tracking links."
        ),
        "items": items,
    }


async def validate_and_create_payout(
    db: AsyncSession,
    partner: ChannelPartner,
    payout_type: str,
    deal_amount: float,
    commission_amount: float,
    lead_id: Optional[str] = None,
    property_title: Optional[str] = None,
    payout_status: str = "PENDING",
    note: Optional[str] = None,
) -> PartnerPayout:
    """Validate CP type rules (registry-only & annual cap for Referral Partner) and create payout."""
    if not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create payout for a suspended/inactive partner.",
        )

    norm_type = (payout_type or "COMMISSION").strip().upper()
    if norm_type not in PAYOUT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payout_type '{payout_type}'. Allowed: {sorted(PAYOUT_TYPES)}",
        )

    fy = current_fiscal_year()
    final_commission = commission_amount

    # Referral Partner strict rules: Registry-only + Annual cap
    if partner.cp_type == "REFERRAL_PARTNER" or norm_type == "REFERRAL_FIXED":
        norm_type = "REFERRAL_FIXED"
        if not lead_id or not lead_id.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Referral Partner fixed reward requires a linked Lead ID.",
            )
        lead = (
            await db.execute(
                select(Lead).where(
                    Lead.lead_id == lead_id.strip(),
                    Lead.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Linked lead '{lead_id}' not found.",
            )
        if (lead.stage or "").upper() not in REGISTERED_LEAD_STAGES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Referral reward is unlocked ONLY after property registry (lead stage must be CONVERTED/WON/REGISTERED; current: {lead.stage}).",
            )

        used = await count_referral_rewards_for_fy(db, partner.id, fy)
        limit = int(partner.annual_reward_limit or 0)
        if limit > 0 and used >= limit:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Annual referral reward limit reached for FY {fy} ({used}/{limit}).",
            )

        if final_commission <= 0:
            final_commission = float(partner.fixed_reward_amount or 0)

    # Broker CP default co-broking split calculation if 0 provided
    elif partner.cp_type == "BROKER_CP" and norm_type in {"CO_BROKING", "COMMISSION"}:
        norm_type = "CO_BROKING"

    code = await next_franchise_code(db, PartnerPayout, PartnerPayout.payout_code, "PAY")
    now = datetime.now(timezone.utc)
    payout = PartnerPayout(
        payout_code=code,
        partner_id=partner.id,
        payout_type=norm_type,
        fiscal_year=fy,
        lead_id=lead_id.strip() if lead_id else None,
        property_title=property_title.strip() if property_title else None,
        deal_amount=deal_amount,
        commission_amount=final_commission,
        status=payout_status,
        paid_at=now if payout_status == "SETTLED" else None,
        note=note.strip() if note else None,
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)
    return payout


async def generate_creator_retainers(db: AsyncSession) -> Dict[str, Any]:
    """Generate monthly retainer payouts for active Top Creator Partners (idempotent per month)."""
    now = datetime.now(timezone.utc)
    month_tag = now.strftime("%Y-%m")
    fy = current_fiscal_year(now)

    stmt = select(ChannelPartner).where(
        ChannelPartner.deleted_at.is_(None),
        ChannelPartner.is_active.is_(True),
        ChannelPartner.cp_type == "CREATOR_PARTNER",
        ChannelPartner.is_top_creator.is_(True),
        ChannelPartner.monthly_retainer_amount > 0,
    )
    creators = (await db.execute(stmt)).scalars().all()

    created_codes: List[str] = []
    skipped = 0
    for creator in creators:
        existing_stmt = select(PartnerPayout.id).where(
            PartnerPayout.partner_id == creator.id,
            PartnerPayout.payout_type == "CREATOR_RETAINER",
            PartnerPayout.property_title == f"Retainer {month_tag}",
        )
        if (await db.execute(existing_stmt)).scalar_one_or_none():
            skipped += 1
            continue

        code = await next_franchise_code(db, PartnerPayout, PartnerPayout.payout_code, "PAY")
        payout = PartnerPayout(
            payout_code=code,
            partner_id=creator.id,
            payout_type="CREATOR_RETAINER",
            fiscal_year=fy,
            property_title=f"Retainer {month_tag}",
            deal_amount=0.0,
            commission_amount=float(creator.monthly_retainer_amount),
            status="PENDING",
            note=f"Monthly Top Creator Retainer ({creator.tracking_code or creator.partner_code})",
        )
        db.add(payout)
        await db.flush()
        created_codes.append(code)

    if created_codes:
        await db.commit()

    return {
        "month": month_tag,
        "generated_count": len(created_codes),
        "skipped_existing": skipped,
        "payout_codes": created_codes,
    }
