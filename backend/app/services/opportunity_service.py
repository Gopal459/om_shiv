from __future__ import annotations

import html
import math
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.franchise import ChannelPartner, FranchiseOutlet
from app.models.identity import Employee
from app.models.leads import Lead, LeadActivity, TblLead
from app.models.opportunities import (
    DISQUALIFIED_REASONS,
    OPPORTUNITY_STATUSES,
    OpportunityActivity,
    OpportunityLocation,
    OpportunityRescheduleLog,
    OpportunitySequence,
    TblOpportunity,
)
from app.models.properties import TblProperty
from app.services.callback_service import (
    VIEW_ALL_ROLES,
    _ensure_utc,
    _iso_utc,
    _ist_today_bounds_utc,
    normalize_phone,
)

ALLOWED_CUSTOMER_TYPES = {"END_USER", "INVESTOR"}
ALLOWED_LOANABLE = {"YES", "NO", "MAYBE"}
ALLOWED_PROPERTY_TYPES = {1, 2, 3}
ALLOWED_LOOKING_TYPES = {1, 2, 3, 4}

PROPERTY_TYPE_LABELS = {1: "Rent", 2: "Buy/Sell", 3: "PG"}
LOOKING_TYPE_LABELS = {1: "Residential", 2: "Commercial", 3: "Agricultural", 4: "Industrial"}


def _to_float(val: Any) -> float:
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


def _to_opt_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _parse_coord_pair(lat_raw: Any, lng_raw: Any) -> Optional[Tuple[float, float]]:
    """Parse lat/lng strings or numbers; return None if missing, invalid, or zeroed."""
    if lat_raw is None or lng_raw is None:
        return None
    try:
        lat = float(str(lat_raw).strip())
        lng = float(str(lng_raw).strip())
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lng)):
        return None
    if lat == 0.0 and lng == 0.0:
        return None
    return lat, lng


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points in kilometers."""
    radius_earth_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * radius_earth_km * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


async def generate_opportunity_code(db: AsyncSession, year: Optional[int] = None) -> str:
    """Atomically increment OpportunitySequence for the UTC year and format OPP-YYYY-NNNNNN."""
    current_year = year or datetime.now(timezone.utc).year
    try:
        stmt = (
            select(OpportunitySequence)
            .where(OpportunitySequence.year == current_year)
            .with_for_update()
        )
        seq_row = (await db.execute(stmt)).scalar_one_or_none()
    except Exception:
        stmt = select(OpportunitySequence).where(OpportunitySequence.year == current_year)
        seq_row = (await db.execute(stmt)).scalar_one_or_none()

    if not seq_row:
        seq_row = OpportunitySequence(year=current_year, last_sequence=1)
        db.add(seq_row)
        await db.flush()
        next_val = 1
    else:
        seq_row.last_sequence += 1
        await db.flush()
        next_val = seq_row.last_sequence

    return f"OPP-{current_year}-{next_val:06d}"


class OpportunityService:
    """Core service for Opportunity CRUD, lead conversion, matching engine, and export."""

    def has_view_all(self, emp: Optional[Employee]) -> bool:
        """Return True for SUPER_ADMIN, MD, SALES_MANAGER, or explicit view-all permissions."""
        if not emp or not emp.role:
            return False
        role_code = (emp.role.code or "").upper()
        if role_code in VIEW_ALL_ROLES:
            return True

        perms = emp.role.permissions or {}
        if isinstance(perms, dict):
            all_perms = perms.get("all") or []
            opp_perms = perms.get("opportunities") or []
            if "*" in all_perms or "all.*" in all_perms:
                return True
            if "view_all" in opp_perms or "*" in opp_perms or "opportunities.view_all" in opp_perms:
                return True
            if perms.get("opportunities.view_all") is True or perms.get("all.*") is True:
                return True
        elif isinstance(perms, (list, tuple, set)):
            if "opportunities.view_all" in perms or "all.*" in perms or "*" in perms:
                return True
        return False

    def _scope_filters(self, actor: Employee) -> List[Any]:
        filters: List[Any] = [TblOpportunity.deleted_at.is_(None)]
        if not self.has_view_all(actor):
            filters.append(TblOpportunity.assigned_to == actor.employee_id)
        return filters

    def _tab_filters(self, tab: str, now_utc: datetime) -> List[Any]:
        today_start_utc, today_end_utc = _ist_today_bounds_utc(now_utc)
        norm = (tab or "all").strip().lower()
        if norm == "new":
            return [
                TblOpportunity.lead_open == 1,
                TblOpportunity.lead_status == 1,
                TblOpportunity.calls_status == 0,
            ]
        if norm == "today":
            return [
                TblOpportunity.lead_open == 1,
                TblOpportunity.followup_datetime.is_not(None),
                TblOpportunity.followup_datetime >= today_start_utc,
                TblOpportunity.followup_datetime <= today_end_utc,
            ]
        if norm == "open":
            return [TblOpportunity.lead_open == 1]
        if norm == "missing":
            return [
                TblOpportunity.lead_open == 1,
                TblOpportunity.followup_datetime.is_not(None),
                TblOpportunity.followup_datetime < now_utc,
            ]
        if norm == "in_progress":
            return [
                TblOpportunity.lead_open == 1,
                TblOpportunity.lead_status == 1,
            ]
        if norm == "closed":
            return [TblOpportunity.lead_open == 0]
        return []

    async def _get_scoped_opportunity(
        self,
        db: AsyncSession,
        actor: Employee,
        opportunity_id: int,
        *,
        with_relations: bool = False,
    ) -> TblOpportunity:
        stmt = select(TblOpportunity).where(
            TblOpportunity.opportunity_id == opportunity_id,
            TblOpportunity.deleted_at.is_(None),
        )
        if with_relations:
            stmt = stmt.options(
                selectinload(TblOpportunity.locations),
                selectinload(TblOpportunity.activities),
                selectinload(TblOpportunity.reschedules),
            ).execution_options(populate_existing=True)
        opp = (await db.execute(stmt)).scalar_one_or_none()
        if not opp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Opportunity #{opportunity_id} not found",
            )
        if not self.has_view_all(actor) and opp.assigned_to != actor.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this opportunity.",
            )
        return opp

    async def _get_active_employee(
        self, db: AsyncSession, employee_id: str, *, label: str = "Assignee"
    ) -> Employee:
        clean_id = (employee_id or "").strip()
        emp = (
            await db.execute(
                select(Employee).where(
                    Employee.employee_id == clean_id,
                    Employee.is_active.is_(True),
                    Employee.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{label} '{clean_id}' not found or inactive.",
            )
        return emp

    async def _get_active_franchise(
        self, db: AsyncSession, franchise_id: int
    ) -> FranchiseOutlet:
        outlet = (
            await db.execute(
                select(FranchiseOutlet).where(
                    FranchiseOutlet.id == franchise_id,
                    FranchiseOutlet.is_active.is_(True),
                    FranchiseOutlet.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not outlet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Franchise outlet #{franchise_id} not found or inactive.",
            )
        return outlet

    async def _resolve_lead_pair(
        self, db: AsyncSession, identifier: str
    ) -> Tuple[Optional[Lead], Optional[TblLead]]:
        """Resolve paired (Lead, TblLead) by lead_id, lead_unique_id, LEAD-<pk>, PR<pk>, or PK."""
        ident = (identifier or "").strip()
        if not ident:
            return None, None

        lead = (
            await db.execute(
                select(Lead).where(Lead.lead_id == ident, Lead.deleted_at.is_(None))
            )
        ).scalar_one_or_none()

        tbl_lead = (
            await db.execute(
                select(TblLead).where(
                    TblLead.lead_unique_id == ident,
                    TblLead.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()

        if not lead and not tbl_lead:
            pref = re.match(r"^(?:LEAD-|PR)(\d+)$", ident, flags=re.IGNORECASE)
            if pref:
                pk = int(pref.group(1))
                tbl_lead = (
                    await db.execute(
                        select(TblLead).where(TblLead.leads_id == pk, TblLead.deleted_at.is_(None))
                    )
                ).scalar_one_or_none()
            elif ident.isdigit():
                pk = int(ident)
                tbl_lead = (
                    await db.execute(
                        select(TblLead).where(TblLead.leads_id == pk, TblLead.deleted_at.is_(None))
                    )
                ).scalar_one_or_none()
                if not tbl_lead:
                    lead = (
                        await db.execute(
                            select(Lead).where(Lead.id == pk, Lead.deleted_at.is_(None))
                        )
                    ).scalar_one_or_none()

        if not lead and tbl_lead and tbl_lead.lead_unique_id:
            lead = (
                await db.execute(
                    select(Lead).where(
                        Lead.lead_id == tbl_lead.lead_unique_id,
                        Lead.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
        if not tbl_lead and lead and lead.lead_id:
            tbl_lead = (
                await db.execute(
                    select(TblLead).where(
                        TblLead.lead_unique_id == lead.lead_id,
                        TblLead.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()

        return lead, tbl_lead

    async def _employee_name_map(
        self, db: AsyncSession, employee_ids: List[Optional[str]]
    ) -> Dict[str, str]:
        clean_ids = sorted({eid for eid in employee_ids if eid})
        if not clean_ids:
            return {}
        rows = (
            await db.execute(
                select(Employee.employee_id, Employee.name).where(
                    Employee.employee_id.in_(clean_ids)
                )
            )
        ).all()
        return {emp_id: emp_name for emp_id, emp_name in rows}

    async def _franchise_name_map(
        self, db: AsyncSession, franchise_ids: List[Optional[int]]
    ) -> Dict[int, str]:
        clean_ids = sorted({fid for fid in franchise_ids if fid and fid > 0})
        if not clean_ids:
            return {}
        rows = (
            await db.execute(
                select(FranchiseOutlet.id, FranchiseOutlet.name).where(
                    FranchiseOutlet.id.in_(clean_ids)
                )
            )
        ).all()
        return {fid: fname for fid, fname in rows}

    def _serialize_locations(self, opp: TblOpportunity) -> List[Dict[str, Any]]:
        return [
            {
                "id": loc.id,
                "locality_name": loc.locality_name,
                "latitude": _to_opt_float(loc.latitude),
                "longitude": _to_opt_float(loc.longitude),
                "radius_km": loc.radius_km,
            }
            for loc in (opp.locations or [])
        ]

    def _serialize_summary(
        self,
        opp: TblOpportunity,
        *,
        assigned_to_name: Optional[str] = None,
        matching_properties_count: int = 0,
    ) -> Dict[str, Any]:
        return {
            "opportunity_id": opp.opportunity_id,
            "opportunity_code": opp.opportunity_code,
            "source_lead_id": opp.source_lead_id,
            "contact_name": opp.contact_name,
            "mobile": opp.mobile,
            "customer_type": opp.customer_type,
            "property_type": opp.property_type,
            "looking_type": opp.looking_type,
            "looking_subcat_type": opp.looking_subcat_type,
            "budget_from": _to_float(opp.budget_from),
            "budget_to": _to_float(opp.budget_to),
            "area_from": _to_float(opp.area_from),
            "area_to": _to_float(opp.area_to),
            "area_unit": opp.area_unit,
            "bhk": opp.bhk,
            "lead_status": opp.lead_status,
            "status_label": OPPORTUNITY_STATUSES.get(opp.lead_status, "Unknown"),
            "lead_open": opp.lead_open,
            "calls_status": opp.calls_status,
            "assigned_to": opp.assigned_to,
            "assigned_to_name": assigned_to_name,
            "assign_franch_id": opp.assign_franch_id,
            "followup_datetime": _iso_utc(opp.followup_datetime),
            "deal_date": _iso_utc(opp.deal_date),
            "registry_date": _iso_utc(opp.registry_date),
            "is_propira_property": bool(opp.is_propira_property),
            "matched_property_code": opp.matched_property_code,
            "locations": self._serialize_locations(opp),
            "matching_properties_count": matching_properties_count,
            "created_at": _iso_utc(opp.created_at),
        }

    def _serialize_detail(
        self,
        opp: TblOpportunity,
        *,
        name_map: Dict[str, str],
        franchise_name: Optional[str],
        matching_properties_count: int,
    ) -> Dict[str, Any]:
        summary = self._serialize_summary(
            opp,
            assigned_to_name=name_map.get(opp.assigned_to or ""),
            matching_properties_count=matching_properties_count,
        )
        sorted_acts = sorted(
            opp.activities or [],
            key=lambda a: (_ensure_utc(a.created_at) if a.created_at else datetime.min.replace(tzinfo=timezone.utc), a.id or 0),
            reverse=True,
        )
        sorted_rescheds = sorted(
            opp.reschedules or [],
            key=lambda r: (_ensure_utc(r.created_at) if r.created_at else datetime.min.replace(tzinfo=timezone.utc), r.id or 0),
            reverse=True,
        )
        summary.update(
            {
                "alternate_mobile": opp.alternate_mobile,
                "email": opp.email,
                "address": opp.address,
                "furnishing": opp.furnishing,
                "property_age": opp.property_age,
                "loanable": opp.loanable,
                "remark": opp.remark,
                "assign_franchstaff_id": opp.assign_franchstaff_id,
                "franchise_name": franchise_name,
                "disqualified_reason": opp.disqualified_reason,
                "disqualified_reason_label": DISQUALIFIED_REASONS.get(opp.disqualified_reason),
                "current_update": opp.current_update,
                "last_remark": opp.last_remark,
                "matched_property_id": opp.matched_property_id,
                "deal_property_category": opp.deal_property_category,
                "deal_property_subcategory": opp.deal_property_subcategory,
                "deal_property_address": opp.deal_property_address,
                "deal_location_lat": opp.deal_location_lat,
                "deal_location_long": opp.deal_location_long,
                "closed_at": _iso_utc(opp.closed_at),
                "created_by": opp.created_by,
                "updated_at": _iso_utc(opp.updated_at),
                "activities": [
                    {
                        "id": a.id,
                        "opportunity_id": a.opportunity_id,
                        "action_type": a.action_type,
                        "note": a.note,
                        "status_before": a.status_before,
                        "status_after": a.status_after,
                        "performed_by": a.performed_by,
                        "performed_by_name": name_map.get(a.performed_by or "") or a.performed_by,
                        "created_at": _iso_utc(a.created_at),
                    }
                    for a in sorted_acts
                ],
                "reschedules": [
                    {
                        "id": r.id,
                        "opportunity_id": r.opportunity_id,
                        "old_followup_datetime": _iso_utc(r.old_followup_datetime),
                        "new_followup_datetime": _iso_utc(r.new_followup_datetime),
                        "current_update": r.current_update,
                        "remark": r.remark,
                        "rescheduled_by": r.rescheduled_by,
                        "rescheduled_by_name": name_map.get(r.rescheduled_by or "") or r.rescheduled_by,
                        "created_at": _iso_utc(r.created_at),
                    }
                    for r in sorted_rescheds
                ],
            }
        )
        return summary

    async def _resolve_actor_cp_policy(
        self, db: AsyncSession, actor: Employee, *, raise_on_inactive: bool = True
    ) -> Tuple[bool, Optional[str], bool]:
        """Return (is_restricted_empty, restricted_reason, owner_masked) for actor."""
        partner = (
            await db.execute(
                select(ChannelPartner).where(
                    ChannelPartner.employee_id == actor.employee_id,
                    ChannelPartner.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        role_code = (actor.role.code or "").upper() if actor.role else ""

        if partner is not None:
            if not partner.is_active:
                if raise_on_inactive:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access revoked: partner {partner.partner_code} is inactive/suspended.",
                    )
                return True, "Partner account is inactive", True
            cp_type = (partner.cp_type or "").upper()
            level = (partner.active_level or "L1").upper()
            if cp_type == "REFERRAL_PARTNER" or (cp_type == "ACTIVE_CP" and level == "L1"):
                return True, "LP/L1 partners cannot browse direct inventory", True
            return False, None, True

        if role_code == "FRANCHISEE_AGENT":
            return False, None, True

        return False, None, False

    def _live_property_base_conditions(self, ref_now: datetime) -> List[Any]:
        """Shared SQL predicates for live, verified, unsold, non-recycled, non-expired inventory."""
        return [
            TblProperty.is_active == 1,
            TblProperty.verified_status == 1,
            TblProperty.sold_status == 0,
            TblProperty.recyclebin_status == 0,
            TblProperty.deleted_at.is_(None),
            or_(TblProperty.expiarydate.is_(None), TblProperty.expiarydate >= ref_now),
        ]

    async def _match_properties_for_opportunity(
        self,
        db: AsyncSession,
        actor: Employee,
        opp: TblOpportunity,
        *,
        now_utc: Optional[datetime] = None,
        raise_on_inactive_cp: bool = True,
        cp_policy: Optional[Tuple[bool, Optional[str], bool]] = None,
        candidate_properties: Optional[Sequence[TblProperty]] = None,
    ) -> Dict[str, Any]:
        ref_now = _ensure_utc(now_utc or datetime.now(timezone.utc))
        is_restricted, restricted_reason, owner_masked = (
            cp_policy
            if cp_policy is not None
            else await self._resolve_actor_cp_policy(
                db, actor, raise_on_inactive=raise_on_inactive_cp
            )
        )
        if is_restricted:
            return {
                "opportunity_id": opp.opportunity_id,
                "count": 0,
                "owner_masked": True,
                "restricted_reason": restricted_reason,
                "items": [],
            }

        budget_from = _to_float(opp.budget_from)
        budget_to = _to_float(opp.budget_to)

        if candidate_properties is None:
            conditions: List[Any] = self._live_property_base_conditions(ref_now) + [
                TblProperty.property_type == opp.property_type,
                TblProperty.looking_type == opp.looking_type,
            ]
            if opp.looking_subcat_type and opp.looking_subcat_type > 0:
                conditions.append(TblProperty.looking_subcat_type == opp.looking_subcat_type)
            if opp.bhk and opp.bhk > 0:
                conditions.append(TblProperty.noof_bhk == opp.bhk)
            if budget_from > 0:
                conditions.append(TblProperty.expected_price >= Decimal(str(budget_from)))
            if budget_to > 0:
                conditions.append(TblProperty.expected_price <= Decimal(str(budget_to)))

            stmt = select(TblProperty).where(and_(*conditions))
            candidates: Sequence[TblProperty] = list((await db.execute(stmt)).scalars().all())
        else:
            candidates = candidate_properties

        opp_locs = opp.locations or []
        scored: List[Tuple[int, float, float, int, Dict[str, Any]]] = []

        for prop in candidates:
            if (
                prop.is_active != 1
                or prop.verified_status != 1
                or prop.sold_status != 0
                or prop.recyclebin_status != 0
                or prop.deleted_at is not None
            ):
                continue
            if prop.expiarydate is not None and _ensure_utc(prop.expiarydate) < ref_now:
                continue
            if prop.property_type != opp.property_type or prop.looking_type != opp.looking_type:
                continue
            if (
                opp.looking_subcat_type
                and opp.looking_subcat_type > 0
                and prop.looking_subcat_type != opp.looking_subcat_type
            ):
                continue
            if opp.bhk and opp.bhk > 0 and prop.noof_bhk != opp.bhk:
                continue
            prop_price = _to_float(prop.expected_price)
            if budget_from > 0 and prop_price < budget_from:
                continue
            if budget_to > 0 and prop_price > budget_to:
                continue

            min_dist: Optional[float] = None
            matched_reasons: List[str] = ["Type & Category"]
            if budget_from > 0 or budget_to > 0:
                matched_reasons.append("Budget")
            if opp.bhk and opp.bhk > 0:
                matched_reasons.append(f"{opp.bhk} BHK")

            if opp_locs:
                prop_coords = _parse_coord_pair(prop.location_lat, prop.location_long)
                prop_texts = [
                    (prop.location or "").lower(),
                    (prop.sublocality_address or "").lower(),
                    (prop.nearby_area or "").lower(),
                ]
                loc_matched = False
                matched_localities: List[str] = []

                for loc in opp_locs:
                    radius = loc.radius_km or 10
                    opp_coords = _parse_coord_pair(loc.latitude, loc.longitude)
                    geo_hit = False
                    if opp_coords and prop_coords:
                        dist = _haversine_km(
                            opp_coords[0], opp_coords[1], prop_coords[0], prop_coords[1]
                        )
                        if dist <= radius:
                            geo_hit = True
                            loc_matched = True
                            if min_dist is None or dist < min_dist:
                                min_dist = dist

                    loc_name = (loc.locality_name or "").strip().lower()
                    text_hit = bool(loc_name and any(loc_name in txt for txt in prop_texts))
                    if text_hit:
                        loc_matched = True

                    if geo_hit or text_hit:
                        matched_localities.append(loc.locality_name)

                if not loc_matched:
                    continue

                if min_dist is not None:
                    matched_reasons.append(f"Geo {round(min_dist, 2)} km")
                elif matched_localities:
                    matched_reasons.append(f"Locality: {matched_localities[0]}")

            distance_val = round(min_dist, 2) if min_dist is not None else None
            created_dt = _ensure_utc(prop.created_date) if prop.created_date else datetime.min.replace(tzinfo=timezone.utc)

            item = {
                "property_id": prop.property_id,
                "propertyid_no": prop.propertyid_no,
                "property_type": prop.property_type,
                "looking_type": prop.looking_type,
                "looking_subcat_type": prop.looking_subcat_type,
                "project_name": prop.project_name,
                "location": prop.location,
                "sublocality_address": prop.sublocality_address,
                "nearby_area": prop.nearby_area,
                "pincode": prop.pincode,
                "location_lat": prop.location_lat,
                "location_long": prop.location_long,
                "noof_bhk": prop.noof_bhk,
                "area": prop.area,
                "area_unit": prop.area_unit,
                "expected_price": _to_float(prop.expected_price),
                "price_negociable": prop.price_negociable,
                "description": prop.description,
                "images": prop.images,
                "is_exclusive": prop.is_exclusive,
                "distance_km": distance_val,
                "match_reasons": matched_reasons,
                "owner_masked": owner_masked,
                "source_owner_name": "Omshiv Managed" if owner_masked else prop.source_owner_name,
                "source_owner_mobile": None if owner_masked else prop.source_owner_mobile,
                "source_owner_email": None if owner_masked else prop.source_owner_email,
                "created_date": _iso_utc(prop.created_date),
            }
            scored.append(
                (
                    0 if distance_val is not None else 1,
                    distance_val if distance_val is not None else float("inf"),
                    -created_dt.timestamp(),
                    -prop.property_id,
                    item,
                )
            )

        scored.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
        items = [row[4] for row in scored]
        return {
            "opportunity_id": opp.opportunity_id,
            "count": len(items),
            "owner_masked": owner_masked,
            "restricted_reason": None,
            "items": items,
        }

    async def get_dashboard(self, db: AsyncSession, actor: Employee) -> Dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        base = self._scope_filters(actor)

        async def _count(extra: List[Any]) -> int:
            stmt = select(func.count(TblOpportunity.opportunity_id)).where(and_(*base, *extra))
            return int((await db.execute(stmt)).scalar() or 0)

        all_count = await _count([])
        in_progress_count = await _count(self._tab_filters("in_progress", now_utc))

        counts = {
            "new": await _count(self._tab_filters("new", now_utc)),
            "today": await _count(self._tab_filters("today", now_utc)),
            "open": await _count(self._tab_filters("open", now_utc)),
            "missing": await _count(self._tab_filters("missing", now_utc)),
            "in_progress": in_progress_count,
            "closed": await _count(self._tab_filters("closed", now_utc)),
            "all": all_count,
        }
        chart_breakdown = {
            "total": all_count,
            "open": in_progress_count,
            "disqualified": await _count([TblOpportunity.lead_status == 2]),
            "qualified_propira": await _count(
                [TblOpportunity.lead_status == 4, TblOpportunity.is_propira_property.is_(True)]
            ),
            "qualified_other": await _count(
                [TblOpportunity.lead_status == 4, TblOpportunity.is_propira_property.is_(False)]
            ),
            "closed": await _count([TblOpportunity.lead_status == 5]),
        }
        return {"counts": counts, "chart_breakdown": chart_breakdown}

    async def list_opportunities(
        self,
        db: AsyncSession,
        actor: Employee,
        *,
        tab: str = "all",
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_match_counts: bool = True,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        now_utc = datetime.now(timezone.utc)
        conditions = self._scope_filters(actor) + self._tab_filters(tab, now_utc)

        if search and search.strip():
            term = f"%{search.strip()}%"
            loc_exists = (
                select(OpportunityLocation.id)
                .where(
                    OpportunityLocation.opportunity_id == TblOpportunity.opportunity_id,
                    OpportunityLocation.locality_name.ilike(term),
                )
                .exists()
            )
            conditions.append(
                or_(
                    TblOpportunity.contact_name.ilike(term),
                    TblOpportunity.mobile.ilike(term),
                    TblOpportunity.email.ilike(term),
                    TblOpportunity.opportunity_code.ilike(term),
                    TblOpportunity.remark.ilike(term),
                    loc_exists,
                )
            )

        where_clause = and_(*conditions)
        total = int(
            (
                await db.execute(
                    select(func.count(TblOpportunity.opportunity_id)).where(where_clause)
                )
            ).scalar()
            or 0
        )

        stmt = (
            select(TblOpportunity)
            .options(selectinload(TblOpportunity.locations))
            .where(where_clause)
            .order_by(desc(TblOpportunity.created_at), desc(TblOpportunity.opportunity_id))
            .offset(offset)
            .limit(limit)
        )
        rows = list((await db.execute(stmt)).scalars().all())
        name_map = await self._employee_name_map(db, [r.assigned_to for r in rows])

        cp_policy: Optional[Tuple[bool, Optional[str], bool]] = None
        batch_properties: Optional[List[TblProperty]] = None
        if include_match_counts and rows:
            cp_policy = await self._resolve_actor_cp_policy(
                db, actor, raise_on_inactive=False
            )
            if not cp_policy[0]:
                prop_types = sorted({r.property_type for r in rows})
                look_types = sorted({r.looking_type for r in rows})
                prop_stmt = select(TblProperty).where(
                    and_(
                        *self._live_property_base_conditions(now_utc),
                        TblProperty.property_type.in_(prop_types),
                        TblProperty.looking_type.in_(look_types),
                    )
                )
                batch_properties = list((await db.execute(prop_stmt)).scalars().all())

        items: List[Dict[str, Any]] = []
        for opp in rows:
            if not include_match_counts or (cp_policy is not None and cp_policy[0]):
                match_count = 0
            else:
                match_res = await self._match_properties_for_opportunity(
                    db,
                    actor,
                    opp,
                    now_utc=now_utc,
                    raise_on_inactive_cp=False,
                    cp_policy=cp_policy,
                    candidate_properties=batch_properties,
                )
                match_count = match_res["count"]
            items.append(
                self._serialize_summary(
                    opp,
                    assigned_to_name=name_map.get(opp.assigned_to or ""),
                    matching_properties_count=match_count,
                )
            )
        return total, items

    async def create_opportunity(
        self,
        db: AsyncSession,
        actor: Employee,
        *,
        source_lead_id: Optional[str] = None,
        contact_name: str,
        mobile: str,
        alternate_mobile: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        customer_type: str = "END_USER",
        property_type: int = 2,
        looking_type: int = 1,
        looking_subcat_type: int = 1,
        budget_from: float = 0,
        budget_to: float = 0,
        area_from: float = 0,
        area_to: float = 0,
        area_unit: str = "Sq.Ft",
        bhk: int = 0,
        furnishing: Optional[str] = None,
        property_age: Optional[str] = None,
        loanable: str = "MAYBE",
        remark: Optional[str] = None,
        assign_franch_id: int = 0,
        assigned_to: Optional[str] = None,
        followup_datetime: Optional[datetime] = None,
        locations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        # 1. Validate assignee & franchise outlet before sequence/writes
        target_assigned = (
            assigned_to.strip()
            if isinstance(assigned_to, str) and assigned_to.strip()
            else actor.employee_id
        )
        if not self.has_view_all(actor):
            target_assigned = actor.employee_id

        assignee_emp = await self._get_active_employee(db, target_assigned, label="Assignee")

        if assign_franch_id and assign_franch_id > 0:
            await self._get_active_franchise(db, assign_franch_id)

        # 2. Validate source_lead_id & atomic conversion guards BEFORE sequence/writes
        lead: Optional[Lead] = None
        tbl_lead: Optional[TblLead] = None
        canonical_lead_id: Optional[str] = None

        if source_lead_id and source_lead_id.strip():
            raw_lead_ident = source_lead_id.strip()
            lead, tbl_lead = await self._resolve_lead_pair(db, raw_lead_ident)
            if not lead and not tbl_lead:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Source lead '{raw_lead_ident}' not found.",
                )

            canonical_lead_id = (
                lead.lead_id
                if lead
                else (
                    tbl_lead.lead_unique_id
                    if tbl_lead and tbl_lead.lead_unique_id
                    else f"LEAD-{tbl_lead.leads_id}"
                )
            )

            if tbl_lead:
                if tbl_lead.opportunity_converted == 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Lead '{canonical_lead_id}' is already converted to an Opportunity.",
                    )
                if tbl_lead.lead_status == 2:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Disqualified lead '{canonical_lead_id}' cannot be converted to an Opportunity.",
                    )
                if tbl_lead.lead_status == 5 or (tbl_lead.property_id or 0) > 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Closed/property-converted lead '{canonical_lead_id}' cannot be converted to an Opportunity.",
                    )

            if lead and (lead.stage or "").upper() in ("LOST", "WON"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Lead '{canonical_lead_id}' in stage '{lead.stage}' cannot be converted to an Opportunity.",
                )

            existing_opp = (
                await db.execute(
                    select(TblOpportunity.opportunity_id).where(
                        TblOpportunity.deleted_at.is_(None),
                        TblOpportunity.source_lead_id.in_(
                            list({raw_lead_ident, canonical_lead_id})
                        ),
                    )
                )
            ).scalar_one_or_none()
            if existing_opp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Lead '{canonical_lead_id}' is already linked to an existing Opportunity.",
                )

        # 3. All validations passed -> allocate sequence & write atomically
        now_utc = datetime.now(timezone.utc)
        opp_code = await generate_opportunity_code(db, year=now_utc.year)
        digits = re.sub(r"\D", "", mobile or "")
        norm_mobile = normalize_phone(digits)[:15]

        opp = TblOpportunity(
            opportunity_code=opp_code,
            source_lead_id=canonical_lead_id,
            contact_name=contact_name.strip(),
            mobile=norm_mobile,
            alternate_mobile=alternate_mobile.strip() if isinstance(alternate_mobile, str) and alternate_mobile.strip() else None,
            email=email.strip() if isinstance(email, str) and email.strip() else None,
            address=address.strip() if isinstance(address, str) and address.strip() else None,
            customer_type=customer_type,
            property_type=property_type,
            looking_type=looking_type,
            looking_subcat_type=looking_subcat_type,
            budget_from=Decimal(str(budget_from or 0)),
            budget_to=Decimal(str(budget_to or 0)),
            area_from=Decimal(str(area_from or 0)),
            area_to=Decimal(str(area_to or 0)),
            area_unit=(area_unit or "Sq.Ft").strip() or "Sq.Ft",
            bhk=bhk or 0,
            furnishing=furnishing.strip() if isinstance(furnishing, str) and furnishing.strip() else None,
            property_age=property_age.strip() if isinstance(property_age, str) and property_age.strip() else None,
            loanable=loanable,
            remark=remark.strip() if isinstance(remark, str) and remark.strip() else None,
            assign_franch_id=assign_franch_id or 0,
            assign_franchstaff_id=assignee_emp.id,
            assigned_to=assignee_emp.employee_id,
            followup_datetime=_ensure_utc(followup_datetime) if followup_datetime else None,
            created_by=actor.employee_id,
        )
        db.add(opp)
        await db.flush()

        for loc in locations or []:
            db.add(
                OpportunityLocation(
                    opportunity_id=opp.opportunity_id,
                    locality_name=loc["locality_name"].strip(),
                    latitude=(
                        Decimal(str(loc["latitude"]))
                        if loc.get("latitude") is not None
                        else None
                    ),
                    longitude=(
                        Decimal(str(loc["longitude"]))
                        if loc.get("longitude") is not None
                        else None
                    ),
                    radius_km=int(loc.get("radius_km") or 10),
                )
            )

        db.add(
            OpportunityActivity(
                opportunity_id=opp.opportunity_id,
                action_type="CREATED",
                note=(
                    f"Converted from Lead {canonical_lead_id}"
                    if canonical_lead_id
                    else (opp.remark or "Opportunity created")
                ),
                status_before=None,
                status_after=1,
                performed_by=actor.employee_id,
            )
        )

        if tbl_lead:
            tbl_lead.opportunity_converted = 1
            tbl_lead.opportunity_id = opp.opportunity_id
            tbl_lead.opportunity_datetime = now_utc.replace(tzinfo=None)
            tbl_lead.lead_status = 4

        if lead:
            prev_stage = lead.stage
            lead.stage = "QUALIFIED"
            lead.is_untouched = False
            db.add(
                LeadActivity(
                    lead_id=lead.lead_id,
                    action_type="CONVERTED_TO_OPPORTUNITY",
                    outcome=f"Opportunity {opp.opportunity_code}",
                    note=f"Converted to Opportunity {opp.opportunity_code}",
                    stage_before=prev_stage,
                    stage_after="QUALIFIED",
                    logged_by=actor.employee_id,
                    performed_by=actor.employee_id,
                )
            )

        await db.commit()
        return await self.get_opportunity_detail(db, actor, opp.opportunity_id)

    async def get_opportunity_detail(
        self, db: AsyncSession, actor: Employee, opportunity_id: int
    ) -> Dict[str, Any]:
        opp = await self._get_scoped_opportunity(
            db, actor, opportunity_id, with_relations=True
        )
        emp_ids = (
            [opp.assigned_to, opp.created_by]
            + [a.performed_by for a in (opp.activities or [])]
            + [r.rescheduled_by for r in (opp.reschedules or [])]
        )
        name_map = await self._employee_name_map(db, emp_ids)
        franchise_map = await self._franchise_name_map(db, [opp.assign_franch_id])
        match_res = await self._match_properties_for_opportunity(
            db, actor, opp, raise_on_inactive_cp=False
        )
        return self._serialize_detail(
            opp,
            name_map=name_map,
            franchise_name=franchise_map.get(opp.assign_franch_id),
            matching_properties_count=match_res["count"],
        )

    async def update_opportunity(
        self,
        db: AsyncSession,
        actor: Employee,
        opportunity_id: int,
        *,
        fields: Dict[str, Any],
        locations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        opp = await self._get_scoped_opportunity(
            db, actor, opportunity_id, with_relations=True
        )
        if opp.lead_open == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This Opportunity is closed/locked and cannot be edited.",
            )

        eff_budget_from = (
            float(fields["budget_from"])
            if fields.get("budget_from") is not None
            else _to_float(opp.budget_from)
        )
        eff_budget_to = (
            float(fields["budget_to"])
            if fields.get("budget_to") is not None
            else _to_float(opp.budget_to)
        )
        if eff_budget_from > 0 and eff_budget_to > 0 and eff_budget_to < eff_budget_from:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="budget_to must be greater than or equal to budget_from.",
            )

        eff_area_from = (
            float(fields["area_from"])
            if fields.get("area_from") is not None
            else _to_float(opp.area_from)
        )
        eff_area_to = (
            float(fields["area_to"])
            if fields.get("area_to") is not None
            else _to_float(opp.area_to)
        )
        if eff_area_from > 0 and eff_area_to > 0 and eff_area_to < eff_area_from:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="area_to must be greater than or equal to area_from.",
            )

        if fields.get("assign_franch_id") is not None and int(fields["assign_franch_id"]) > 0:
            await self._get_active_franchise(db, int(fields["assign_franch_id"]))

        if "contact_name" in fields and fields["contact_name"] is not None:
            opp.contact_name = fields["contact_name"].strip()
        if "mobile" in fields and fields["mobile"] is not None:
            digits = re.sub(r"\D", "", fields["mobile"])
            opp.mobile = normalize_phone(digits)[:15]
        for str_field in ("alternate_mobile", "email", "address", "furnishing", "property_age", "remark"):
            if str_field in fields:
                val = fields[str_field]
                setattr(
                    opp,
                    str_field,
                    val.strip() if isinstance(val, str) and val.strip() else None,
                )
        for direct_field in (
            "customer_type",
            "property_type",
            "looking_type",
            "looking_subcat_type",
            "bhk",
            "loanable",
            "assign_franch_id",
        ):
            if direct_field in fields and fields[direct_field] is not None:
                setattr(opp, direct_field, fields[direct_field])

        if "area_unit" in fields and fields["area_unit"] is not None:
            opp.area_unit = fields["area_unit"].strip() or "Sq.Ft"

        for dec_field in ("budget_from", "budget_to", "area_from", "area_to"):
            if dec_field in fields and fields[dec_field] is not None:
                setattr(opp, dec_field, Decimal(str(fields[dec_field])))

        if locations is not None:
            opp.locations.clear()
            await db.flush()
            for loc in locations:
                opp.locations.append(
                    OpportunityLocation(
                        opportunity_id=opp.opportunity_id,
                        locality_name=loc["locality_name"].strip(),
                        latitude=(
                            Decimal(str(loc["latitude"]))
                            if loc.get("latitude") is not None
                            else None
                        ),
                        longitude=(
                            Decimal(str(loc["longitude"]))
                            if loc.get("longitude") is not None
                            else None
                        ),
                        radius_km=int(loc.get("radius_km") or 10),
                    )
                )

        db.add(
            OpportunityActivity(
                opportunity_id=opp.opportunity_id,
                action_type="UPDATED",
                note="Opportunity details and requirements updated",
                status_before=opp.lead_status,
                status_after=opp.lead_status,
                performed_by=actor.employee_id,
            )
        )
        await db.commit()
        return await self.get_opportunity_detail(db, actor, opp.opportunity_id)

    async def get_related_properties(
        self, db: AsyncSession, actor: Employee, opportunity_id: int
    ) -> Dict[str, Any]:
        opp = await self._get_scoped_opportunity(
            db, actor, opportunity_id, with_relations=True
        )
        return await self._match_properties_for_opportunity(
            db, actor, opp, raise_on_inactive_cp=True
        )

    async def export_opportunities_xls(
        self,
        db: AsyncSession,
        actor: Employee,
        *,
        tab: str = "all",
        search: Optional[str] = None,
    ) -> str:
        _, items = await self.list_opportunities(
            db,
            actor,
            tab=tab,
            search=search,
            limit=5000,
            offset=0,
            include_match_counts=False,
        )
        headers = [
            "Opportunity Code",
            "Source Lead ID",
            "Customer Name",
            "Mobile",
            "Customer Type",
            "Transaction Type",
            "Category",
            "Budget From",
            "Budget To",
            "Area From",
            "Area To",
            "Area Unit",
            "BHK",
            "Preferred Localities",
            "Status",
            "Open State",
            "Assigned To",
            "Follow-up Datetime",
            "Deal Date",
            "Registry Date",
            "Matched Property Code",
            "Created At",
        ]
        header_cells = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
        rows_html: List[str] = []
        for item in items:
            locs = ", ".join(loc["locality_name"] for loc in (item.get("locations") or []))
            vals = [
                item.get("opportunity_code") or "",
                item.get("source_lead_id") or "",
                item.get("contact_name") or "",
                item.get("mobile") or "",
                item.get("customer_type") or "",
                PROPERTY_TYPE_LABELS.get(item.get("property_type"), ""),
                LOOKING_TYPE_LABELS.get(item.get("looking_type"), ""),
                item.get("budget_from") or 0,
                item.get("budget_to") or 0,
                item.get("area_from") or 0,
                item.get("area_to") or 0,
                item.get("area_unit") or "",
                item.get("bhk") or 0,
                locs,
                item.get("status_label") or "",
                "Open" if item.get("lead_open") == 1 else "Closed",
                item.get("assigned_to_name") or item.get("assigned_to") or "Unassigned",
                item.get("followup_datetime") or "",
                item.get("deal_date") or "",
                item.get("registry_date") or "",
                item.get("matched_property_code") or "",
                item.get("created_at") or "",
            ]
            cells = "".join(f"<td>{html.escape(str(v))}</td>" for v in vals)
            rows_html.append(f"<tr>{cells}</tr>")

        return (
            "<html><head><meta charset='UTF-8'></head><body>"
            "<table border='1'>"
            f"<thead><tr>{header_cells}</tr></thead>"
            f"<tbody>{''.join(rows_html)}</tbody>"
            "</table></body></html>"
        )


opportunity_service = OpportunityService()
