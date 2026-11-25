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
from app.models.leads import Lead, LeadActivity, LeadActionLog, TblLead, LeadSequence
from app.repositories import lead_repo
from app.services.pipeline_service import pipeline_service

router = APIRouter()
security = HTTPBearer(auto_error=False)


LEAD_SOURCES_MAP = {
    1: "Website Inbound Inquiry",
    2: "Builder Project Landing",
    3: "Franchisee / Agent Direct",
    4: "Request a Callback Form",
    5: "Report a Problem Form",
    6: "Bulk CSV / Portal Import",
    7: "Newspaper Advertisement",
    8: "Facebook Ad Campaign",
    9: "Google Search Ad",
    10: "Poster & Hoarding",
    11: "Direct Incoming Call",
    12: "Office Walk-in",
    13: "YouTube Channel",
    14: "Instagram Reel / Post",
    15: "WhatsApp Business",
    16: "Referral / Channel Partner",
    17: "MagicBricks Sync",
    18: "99acres Sync",
    19: "Housing.com Sync",
    20: "SMS Marketing Blast",
    21: "Email Newsletter",
    22: "Property Expo / Exhibition",
    23: "Telecaller Cold Outreach",
    24: "Other Inbound Source",
}


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
    is_untouched: bool = False
    is_duplicate: bool = False
    is_test: bool = False
    created_at: datetime
    updated_at: datetime
    activities: List[LeadActivityResponse] = []

    # Dynamic & tbl_leads integrated fields
    property_idno: Optional[str] = None
    indv_property_address: Optional[str] = None
    deal_final_price: Optional[float] = 0.0
    dealer_have: Optional[int] = 0
    lead_status_num: Optional[int] = 0
    stage_num: Optional[int] = 1
    rating_num: Optional[int] = 3
    lead_source_id: Optional[int] = 1
    lead_source_name: Optional[str] = None
    alternate_contact_mobile: Optional[str] = None
    refer_by_name: Optional[str] = None
    refer_by_mobile: Optional[str] = None
    assign_franch_id: Optional[int] = 0
    assign_franchstaff_id: Optional[int] = 0
    lead_remark: Optional[str] = None
    registry_date: Optional[datetime] = None
    deal_date: Optional[datetime] = None
    opportunity_converted: Optional[int] = 0
    opportunity_id: Optional[int] = 0

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


class LeadCreateManual(BaseModel):
    contact_name: str = Field(..., description="Lead contact name")
    mobile: str = Field(..., description="Mobile number")
    email: Optional[str] = None
    address: Optional[str] = None
    lead_type: Optional[str] = "BUY"
    lead_source_id: Optional[int] = 1
    rating: Optional[int] = 3
    indv_property_address: Optional[str] = None
    lead_remark: Optional[str] = None
    deal_final_price: Optional[float] = 0.0


class LeadImportBulk(BaseModel):
    leads: List[Dict[str, Any]]


class LeadStagePatch(BaseModel):
    lead_status: int
    stage: Optional[int] = None
    remark: Optional[str] = None


class LeadAssignPatch(BaseModel):
    assigned_to: Optional[str] = None
    assign_franch_id: Optional[int] = 0
    assign_franchstaff_id: Optional[int] = 0
    remark: Optional[str] = None


def normalize_phone(phone: str) -> str:
    cleaned = "".join(filter(str.isdigit, str(phone)))
    if cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    if len(cleaned) == 10:
        return f"91{cleaned}"
    if cleaned.startswith("91") and len(cleaned) == 12:
        return cleaned
    return cleaned or "919999999999"


async def generate_lead_id(db: AsyncSession) -> str:
    year = datetime.now(timezone.utc).year
    res = await db.execute(select(LeadSequence).where(LeadSequence.year == year))
    seq = res.scalar_one_or_none()
    if not seq:
        seq = LeadSequence(year=year, last_sequence=1)
        db.add(seq)
    else:
        seq.last_sequence += 1
    await db.flush()
    return f"OB-{year}-{seq.last_sequence:06d}"


async def find_tbl_lead_by_id_or_unique_id(db: AsyncSession, identifier: str) -> Optional[TblLead]:
    stmt = select(TblLead).where(TblLead.lead_unique_id == identifier, TblLead.deleted_at.is_(None))
    res = await db.execute(stmt)
    lead = res.scalar_one_or_none()
    if lead:
        return lead
    if str(identifier).isdigit():
        stmt_pk = select(TblLead).where(TblLead.leads_id == int(identifier), TblLead.deleted_at.is_(None))
        res_pk = await db.execute(stmt_pk)
        return res_pk.scalar_one_or_none()
    return None


# --- Lead Inflows, Kanban & Stage Endpoints ---

@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    summary="Manual lead creation with 24 sources and property type",
)
async def create_manual_lead(
    payload: LeadCreateManual,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(get_actor_from_token),
) -> Dict[str, Any]:
    norm_mobile = normalize_phone(payload.mobile)
    lead_uid = await generate_lead_id(db)
    lead_type = (payload.lead_type or "BUY").upper()

    tbl_lead = TblLead(
        lead_unique_id=lead_uid,
        contact_name=payload.contact_name,
        mobile=norm_mobile,
        email=payload.email,
        address=payload.address,
        lead_table_name=lead_type,
        lead_source_id=payload.lead_source_id or 1,
        rating=payload.rating or 3,
        indv_property_address=payload.indv_property_address,
        lead_remark=payload.lead_remark,
        deal_final_price=payload.deal_final_price or 0.0,
        lead_status=0,
        stage=1,
        lead_open=1,
        create_by=actor_id,
    )
    db.add(tbl_lead)

    # Sync modern Lead entity so standard queries & activities work
    lead_entity = Lead(
        lead_id=lead_uid,
        full_name=payload.contact_name,
        mobile=norm_mobile,
        email=payload.email,
        lead_type=lead_type,
        source=f"SOURCE_{payload.lead_source_id or 1}",
        stage="NEW",
        temperature="HOT" if payload.rating == 1 else "WARM" if payload.rating == 2 else "COLD",
        preferred_locality=payload.indv_property_address,
    )
    db.add(lead_entity)
    await db.commit()
    await db.refresh(tbl_lead)

    return {
        "status": "success",
        "leads_id": tbl_lead.leads_id,
        "lead_unique_id": tbl_lead.lead_unique_id,
        "contact_name": tbl_lead.contact_name,
        "mobile": tbl_lead.mobile,
        "lead_type": tbl_lead.lead_table_name,
        "lead_status": tbl_lead.lead_status,
        "stage": tbl_lead.stage,
        "rating": tbl_lead.rating,
    }


@router.post(
    "/import-bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk CSV / Excel lead import",
)
async def import_bulk_leads(
    payload: LeadImportBulk,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(get_actor_from_token),
) -> Dict[str, Any]:
    imported = []
    for item in payload.leads:
        name = item.get("contact_name") or item.get("name") or "Imported Lead"
        raw_phone = item.get("mobile") or item.get("phone") or "9999999999"
        norm_phone = normalize_phone(raw_phone)
        lead_type = (item.get("lead_type") or item.get("type") or "BUY").upper()
        lead_uid = await generate_lead_id(db)

        tbl = TblLead(
            lead_unique_id=lead_uid,
            contact_name=name,
            mobile=norm_phone,
            email=item.get("email"),
            address=item.get("address"),
            lead_table_name=lead_type,
            lead_source_id=int(item.get("lead_source_id") or 6),
            rating=int(item.get("rating") or 3),
            indv_property_address=item.get("indv_property_address") or item.get("location"),
            lead_remark=item.get("lead_remark") or item.get("remarks"),
            lead_status=0,
            stage=1,
            lead_open=1,
            create_by=actor_id,
        )
        db.add(tbl)

        lead_ent = Lead(
            lead_id=lead_uid,
            full_name=name,
            mobile=norm_phone,
            email=item.get("email"),
            lead_type=lead_type,
            source="BULK_IMPORT",
            stage="NEW",
            temperature="HOT" if tbl.rating == 1 else "WARM" if tbl.rating == 2 else "COLD",
        )
        db.add(lead_ent)
        imported.append(lead_uid)

    await db.commit()
    return {
        "status": "success",
        "imported_count": len(imported),
        "lead_ids": imported,
    }


@router.get(
    "/kanban",
    status_code=status.HTTP_200_OK,
    summary="Fetch leads grouped into Kanban pipeline columns",
)
async def get_kanban_board(
    type: Optional[str] = Query(None, description="Optional property type filter: buy, rent, pg, all"),
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(get_actor_from_token),
) -> Dict[str, List[Dict[str, Any]]]:
    stmt = select(TblLead).where(TblLead.deleted_at.is_(None))
    if type and type.lower() != "all":
        stmt = stmt.where(TblLead.lead_table_name.ilike(f"%{type}%"))

    res = await db.execute(stmt.order_by(TblLead.leads_id.desc()))
    all_leads = res.scalars().all()

    board: Dict[str, List[Dict[str, Any]]] = {
        "new": [],
        "in_progress": [],
        "site_visit": [],
        "qualified": [],
        "converted": [],
        "disqualified": [],
    }

    for l in all_leads:
        card = {
            "leads_id": l.leads_id,
            "lead_unique_id": l.lead_unique_id or f"PR{l.leads_id}",
            "contact_name": l.contact_name,
            "mobile": l.mobile,
            "email": l.email,
            "address": l.address,
            "lead_type": l.lead_table_name or "BUY",
            "rating": l.rating,
            "lead_status": l.lead_status,
            "stage": l.stage,
            "property_address": l.indv_property_address or "Alwar, Rajasthan",
            "deal_final_price": float(l.deal_final_price or 0.0),
            "lead_remark": l.lead_remark or "N/A",
            "created_date": l.created_date.isoformat() if l.created_date else None,
        }

        # Deterministic column grouping:
        # 1. Disqualified (lead_status == 2)
        if l.lead_status == 2:
            board["disqualified"].append(card)
        # 2. Converted (lead_status == 5)
        elif l.lead_status == 5:
            board["converted"].append(card)
        # 3. Qualified (lead_status == 4)
        elif l.lead_status == 4:
            board["qualified"].append(card)
        # 4. Site Visit / Inspection (stage in [2, 3])
        elif l.stage in [2, 3]:
            board["site_visit"].append(card)
        # 5. In Progress (lead_status == 1)
        elif l.lead_status == 1:
            board["in_progress"].append(card)
        # 6. Default to New (lead_status == 0)
        else:
            board["new"].append(card)

    return board


@router.patch(
    "/{id}/stage",
    status_code=status.HTTP_200_OK,
    summary="1-click stage and lead_status transition for Kanban moves",
)
async def update_lead_stage(
    id: str,
    payload: LeadStagePatch,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(get_actor_from_token),
) -> Dict[str, Any]:
    tbl_lead = await find_tbl_lead_by_id_or_unique_id(db, id)
    if not tbl_lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{id}' not found in tbl_leads",
        )

    tbl_lead.lead_status = payload.lead_status
    if payload.stage is not None:
        tbl_lead.stage = payload.stage
    if payload.remark:
        tbl_lead.lead_remark = payload.remark
    tbl_lead.last_callstatus_updatetime = datetime.now(timezone.utc)

    # Sync modern Lead entity if exists
    modern_lead = await find_lead_by_id_or_lead_id(db, tbl_lead.lead_unique_id or str(tbl_lead.leads_id))
    if modern_lead:
        stage_map = {0: "NEW", 1: "CONNECTED", 2: "LOST", 3: "SOLVED", 4: "QUALIFIED", 5: "WON"}
        if payload.stage in [2, 3]:
            modern_lead.stage = "SITE_VISIT"
        else:
            modern_lead.stage = stage_map.get(payload.lead_status, modern_lead.stage)

    await db.commit()
    await db.refresh(tbl_lead)

    return {
        "status": "success",
        "leads_id": tbl_lead.leads_id,
        "lead_unique_id": tbl_lead.lead_unique_id,
        "lead_status": tbl_lead.lead_status,
        "stage": tbl_lead.stage,
        "lead_remark": tbl_lead.lead_remark,
    }


@router.patch(
    "/{id}/assign",
    status_code=status.HTTP_200_OK,
    summary="Reassign lead to a sales rep or franchisee desk",
)
async def reassign_lead(
    id: str,
    payload: LeadAssignPatch,
    db: AsyncSession = Depends(get_db),
    actor_id: str = Depends(get_actor_from_token),
) -> Dict[str, Any]:
    tbl_lead = await find_tbl_lead_by_id_or_unique_id(db, id)
    modern_lead = await find_lead_by_id_or_lead_id(db, id)

    if not tbl_lead and not modern_lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{id}' not found",
        )

    now = datetime.now(timezone.utc)
    if tbl_lead:
        if payload.assign_franch_id is not None:
            tbl_lead.assign_franch_id = payload.assign_franch_id
            tbl_lead.assignfranchisee_date = now
        if payload.assign_franchstaff_id is not None:
            tbl_lead.assign_franchstaff_id = payload.assign_franchstaff_id
            tbl_lead.assignfranchiseestaff_date = now
        if payload.remark:
            tbl_lead.lead_remark = payload.remark

    if modern_lead:
        modern_lead.assigned_to = payload.assigned_to
        modern_lead.updated_at = now
        transfer_act = LeadActivity(
            lead_id=modern_lead.lead_id,
            action_type="TRANSFER",
            outcome="Reassigned",
            note=payload.remark or f"Reassigned to {payload.assigned_to or 'Om Shiv Central Desk'}",
            logged_by=actor_id,
            performed_by=actor_id,
            created_at=now,
        )
        db.add(transfer_act)

    await db.commit()
    return {
        "status": "success",
        "assigned_to": payload.assigned_to,
        "assign_franch_id": payload.assign_franch_id,
        "assign_franchstaff_id": payload.assign_franchstaff_id,
    }


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
        # Sort activities descending by created_at and id
        l.activities.sort(key=lambda a: (a.created_at, a.id or 0), reverse=True)

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
        l.activities.sort(key=lambda a: (a.created_at, a.id or 0), reverse=True)
    return leads


def build_lead_detail_dict(lead: Optional[Lead], tbl_lead: Optional[TblLead]) -> Dict[str, Any]:
    lead_uid = lead.lead_id if lead else (tbl_lead.lead_unique_id if tbl_lead and tbl_lead.lead_unique_id else f"LEAD-{tbl_lead.leads_id if tbl_lead else 0}")
    source_id = tbl_lead.lead_source_id if (tbl_lead and tbl_lead.lead_source_id) else 1
    source_name = LEAD_SOURCES_MAP.get(source_id, "Website Inbound Inquiry")
    
    if tbl_lead and tbl_lead.rating:
        rating_num = tbl_lead.rating
        temp = "HOT" if rating_num == 1 else "WARM" if rating_num == 2 else "COLD"
    elif lead and lead.temperature:
        temp = lead.temperature
        rating_num = 1 if temp == "HOT" else 2 if temp == "WARM" else 3
    else:
        temp = "WARM"
        rating_num = 2

    stage_str = lead.stage if (lead and lead.stage) else ("NEW" if not tbl_lead else ("CONNECTED" if tbl_lead.lead_status == 1 else "NEW"))
    stage_num = tbl_lead.stage if (tbl_lead and tbl_lead.stage) else 1

    acts = []
    if lead and lead.activities:
        for a in lead.activities:
            acts.append({
                "id": a.id,
                "lead_id": a.lead_id,
                "action_type": a.action_type,
                "outcome": a.outcome,
                "note": a.note,
                "next_action": a.next_action,
                "follow_up_date": a.follow_up_date,
                "stage_before": a.stage_before,
                "stage_after": a.stage_after,
                "temperature": a.temperature,
                "logged_by": a.logged_by,
                "performed_by": a.performed_by,
                "created_at": a.created_at,
            })

    created_at = lead.created_at if lead else (tbl_lead.created_date if tbl_lead else datetime.now(timezone.utc))
    updated_at = lead.updated_at if lead else (tbl_lead.modified_date if tbl_lead else datetime.now(timezone.utc))

    return {
        "id": lead.id if lead else (tbl_lead.leads_id if tbl_lead else 0),
        "lead_id": lead_uid,
        "full_name": (lead.full_name if lead else tbl_lead.contact_name) if (lead or tbl_lead) else "Valued Client",
        "mobile": (lead.mobile if lead else tbl_lead.mobile) if (lead or tbl_lead) else "",
        "email": (lead.email if lead else tbl_lead.email) if (lead or tbl_lead) else None,
        "lead_type": (tbl_lead.lead_table_name if (tbl_lead and tbl_lead.lead_table_name) else (lead.lead_type if lead else "BUY")).upper(),
        "source": lead.source if (lead and lead.source) else f"SOURCE_{source_id}",
        "assigned_to": lead.assigned_to if (lead and lead.assigned_to) else (f"Staff #{tbl_lead.assign_franchstaff_id}" if (tbl_lead and tbl_lead.assign_franchstaff_id) else None),
        "stage": stage_str,
        "temperature": temp,
        "follow_up_date": lead.follow_up_date if (lead and lead.follow_up_date) else (tbl_lead.nextfollowup_datetime if tbl_lead else None),
        "last_contacted_at": lead.last_contacted_at if lead else (tbl_lead.last_callstatus_updatetime if tbl_lead else None),
        "lost_reason": lead.lost_reason if lead else None,
        "budget_min": lead.budget_min if lead else None,
        "budget_max": lead.budget_max if lead else None,
        "preferred_city": lead.preferred_city if (lead and lead.preferred_city) else (tbl_lead.address if tbl_lead else None),
        "preferred_locality": lead.preferred_locality if (lead and lead.preferred_locality) else (tbl_lead.indv_property_address if tbl_lead else None),
        "is_untouched": lead.is_untouched if lead else False,
        "is_duplicate": lead.is_duplicate if lead else False,
        "is_test": lead.is_test if lead else False,
        "created_at": created_at,
        "updated_at": updated_at,
        "activities": acts,
        "property_idno": tbl_lead.property_idno if tbl_lead else None,
        "indv_property_address": tbl_lead.indv_property_address if (tbl_lead and tbl_lead.indv_property_address) else (lead.preferred_locality if lead else None),
        "deal_final_price": float(tbl_lead.deal_final_price) if (tbl_lead and tbl_lead.deal_final_price) else 0.0,
        "dealer_have": tbl_lead.dealer_have if tbl_lead else 0,
        "lead_status_num": tbl_lead.lead_status if tbl_lead else 0,
        "stage_num": stage_num,
        "rating_num": rating_num,
        "lead_source_id": source_id,
        "lead_source_name": source_name,
        "alternate_contact_mobile": tbl_lead.alternate_contact_mobile if tbl_lead else None,
        "refer_by_name": tbl_lead.refer_by_name if tbl_lead else None,
        "refer_by_mobile": tbl_lead.refer_by_mobile if tbl_lead else None,
        "assign_franch_id": tbl_lead.assign_franch_id if tbl_lead else 0,
        "assign_franchstaff_id": tbl_lead.assign_franchstaff_id if tbl_lead else 0,
        "lead_remark": (tbl_lead.lead_remark if tbl_lead else None) or (acts[0]["note"] if acts else None),
        "registry_date": tbl_lead.registry_date if tbl_lead else None,
        "deal_date": tbl_lead.deal_date if tbl_lead else None,
        "opportunity_converted": tbl_lead.opportunity_converted if tbl_lead else 0,
        "opportunity_id": tbl_lead.opportunity_id if tbl_lead else 0,
    }


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
    """Retrieve complete lead details by ID or lead_id, along with full interaction history and tbl_leads data."""
    lead = await find_lead_by_id_or_lead_id(db, id)
    tbl_lead = await find_tbl_lead_by_id_or_unique_id(db, id)

    if not lead and tbl_lead and tbl_lead.lead_unique_id:
        lead = await find_lead_by_id_or_lead_id(db, tbl_lead.lead_unique_id)
    if not tbl_lead and lead and lead.lead_id:
        tbl_lead = await find_tbl_lead_by_id_or_unique_id(db, lead.lead_id)

    if not lead and not tbl_lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{id}' not found",
        )

    if lead:
        lead.activities.sort(key=lambda a: (a.created_at, a.id or 0), reverse=True)

    return build_lead_detail_dict(lead, tbl_lead)


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

    # Sync tbl_leads if exists
    tbl_lead = await find_tbl_lead_by_id_or_unique_id(db, lead.lead_id)
    if tbl_lead:
        if payload.follow_up_date:
            tbl_lead.nextfollowup_datetime = payload.follow_up_date
        if payload.note:
            tbl_lead.lead_remark = payload.note
        if payload.temperature:
            tbl_lead.rating = 1 if payload.temperature == "HOT" else 2 if payload.temperature == "WARM" else 3
        tbl_lead.last_callstatus_updatetime = datetime.now(timezone.utc)
        await db.commit()

    # Re-query lead with activities to ensure response serialization
    fresh_lead = await find_lead_by_id_or_lead_id(db, lead.lead_id)
    target_lead = fresh_lead or updated_lead
    if target_lead:
        target_lead.activities.sort(key=lambda a: (a.created_at, a.id or 0), reverse=True)
    return build_lead_detail_dict(target_lead, tbl_lead)


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
