from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union

from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_agents import AIApprovalQueue
from app.models.leads import Lead, LeadActivity
from app.models.properties import Property, PropResidentialFlat, PropHouseVilla
from app.models.settings import AuditLog


class AIToolRegistry:
    """
    Controlled Backend Tool Registry & Human-in-the-Loop (HITL) Action Stager.
    Provides safe, controlled database access primitives for AI agents:
    - Read-only property catalog querying with verified/live filters
    - Safe non-destructive lead requirement updates
    - Sensitive action staging requiring supervisor signoff
    - Approval execution and rejection with immutable audit and lead activity logs
    """

    ALLOWED_LEAD_UPDATE_FIELDS = {
        "budget_min",
        "budget_max",
        "preferred_city",
        "preferred_locality",
        "temperature",
    }

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    def _resolve_session(self, explicit_db: Optional[AsyncSession] = None) -> AsyncSession:
        session = explicit_db or self.db
        if session is None:
            raise ValueError("No database session provided to AIToolRegistry")
        return session

    async def search_properties(
        self,
        filters: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
        *args,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Read-only query on Property table with filters:
        - city, locality, min_price, max_price, category_code, sub_category_code, bhk, listing_type
        - Enforces is_live=True and deleted_at is None
        Returns clean JSON-serializable property summaries.
        """
        if isinstance(filters, AsyncSession):
            session = filters
            query_filters = db if isinstance(db, dict) else (args[0] if args else {})
        else:
            session = self._resolve_session(db)
            query_filters = filters or {}

        stmt = (
            select(Property)
            .outerjoin(PropResidentialFlat, Property.id == PropResidentialFlat.property_id)
            .outerjoin(PropHouseVilla, Property.id == PropHouseVilla.property_id)
            .options(
                selectinload(Property.flat_details),
                selectinload(Property.house_details),
            )
            .where(Property.is_live.is_(True))
            .where(Property.deleted_at.is_(None))
        )

        # 1. City filter
        if query_filters.get("city"):
            city_str = str(query_filters["city"]).strip()
            stmt = stmt.where(Property.city.ilike(f"%{city_str}%"))

        # 2. Locality filter
        if query_filters.get("locality"):
            loc_str = str(query_filters["locality"]).strip()
            stmt = stmt.where(Property.locality.ilike(f"%{loc_str}%"))

        # 3. Minimum price
        if query_filters.get("min_price") is not None:
            try:
                min_p = float(query_filters["min_price"])
                stmt = stmt.where(Property.expected_price >= min_p)
            except (ValueError, TypeError):
                pass

        # 4. Maximum price
        if query_filters.get("max_price") is not None:
            try:
                max_p = float(query_filters["max_price"])
                stmt = stmt.where(Property.expected_price <= max_p)
            except (ValueError, TypeError):
                pass

        # 5. Category code
        if query_filters.get("category_code") is not None:
            try:
                cat = int(query_filters["category_code"])
                stmt = stmt.where(Property.category_code == cat)
            except (ValueError, TypeError):
                pass

        # 6. Sub category code
        if query_filters.get("sub_category_code") is not None:
            try:
                sub_cat = int(query_filters["sub_category_code"])
                stmt = stmt.where(Property.sub_category_code == sub_cat)
            except (ValueError, TypeError):
                pass

        # 7. Listing type (1=Rent, 2=Sale, 3=PG)
        if query_filters.get("listing_type") is not None:
            try:
                ltype = int(query_filters["listing_type"])
                stmt = stmt.where(Property.listing_type == ltype)
            except (ValueError, TypeError):
                pass

        # 8. BHK filter
        if query_filters.get("bhk") is not None:
            try:
                bhk_val = int(query_filters["bhk"])
                stmt = stmt.where(
                    or_(
                        PropResidentialFlat.bhk == bhk_val,
                        PropHouseVilla.bhk == bhk_val,
                        Property.title.ilike(f"%{bhk_val}%bhk%"),
                        Property.title.ilike(f"%{bhk_val} bhk%"),
                        Property.description.ilike(f"%{bhk_val}%bhk%"),
                    )
                )
            except (ValueError, TypeError):
                pass

        limit = min(int(query_filters.get("limit", 20)), 50)
        stmt = stmt.distinct().limit(limit)

        result = await session.execute(stmt)
        properties = result.scalars().all()

        summaries = []
        for p in properties:
            bhk = None
            if p.flat_details and p.flat_details.bhk is not None:
                bhk = p.flat_details.bhk
            elif p.house_details and p.house_details.bhk is not None:
                bhk = p.house_details.bhk
            else:
                match = re.search(r"(\d+)\s*bhk", p.title or "", re.IGNORECASE)
                if match:
                    bhk = int(match.group(1))

            summaries.append({
                "property_id": p.property_id,
                "title": p.title,
                "city": p.city,
                "locality": p.locality,
                "expected_price": float(p.expected_price) if p.expected_price is not None else 0.0,
                "price_negotiable": bool(p.price_negotiable),
                "category_code": p.category_code,
                "sub_category_code": p.sub_category_code,
                "listing_type": p.listing_type,
                "bhk": bhk,
                "pincode": p.pincode,
                "description": p.description,
                "owner_name": p.owner_name,
                "owner_mobile": p.owner_mobile,
                "is_live": bool(p.is_live),
            })

        return summaries

    async def get_lead_details(
        self,
        lead_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        *args,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch lead details safely by lead_id.
        Returns a clean dictionary or None if not found.
        """
        if isinstance(lead_id, AsyncSession):
            session = lead_id
            target_lead_id = db if isinstance(db, str) else (args[0] if args else None)
        else:
            session = self._resolve_session(db)
            target_lead_id = lead_id

        if not target_lead_id:
            return None

        stmt = select(Lead).where(
            Lead.lead_id == str(target_lead_id).strip(),
            Lead.deleted_at.is_(None),
        )
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            return None

        return {
            "lead_id": lead.lead_id,
            "full_name": lead.full_name,
            "mobile": lead.mobile,
            "email": lead.email,
            "stage": lead.stage,
            "temperature": lead.temperature,
            "budget_min": float(lead.budget_min) if lead.budget_min is not None else None,
            "budget_max": float(lead.budget_max) if lead.budget_max is not None else None,
            "preferred_city": lead.preferred_city,
            "preferred_locality": lead.preferred_locality,
            "source": lead.source,
            "lead_type": lead.lead_type,
            "assigned_to": lead.assigned_to,
            "lost_reason": lead.lost_reason,
            "follow_up_date": lead.follow_up_date.isoformat() if lead.follow_up_date else None,
            "last_contacted_at": lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
        }

    async def update_lead_requirements(
        self,
        lead_id: Optional[str] = None,
        updates: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
        *args,
        **kwargs,
    ) -> bool:
        """
        Safely update non-destructive lead attributes:
        budget_min, budget_max, preferred_city, preferred_locality, temperature.
        Destructive or sensitive fields (e.g., stage) are strictly ignored.
        Logs LeadActivity upon successful update.
        """
        if isinstance(lead_id, AsyncSession):
            session = lead_id
            target_lead_id = str(updates).strip()
            data_updates = db if isinstance(db, dict) else (args[0] if args else {})
        else:
            session = self._resolve_session(db)
            target_lead_id = str(lead_id).strip() if lead_id else ""
            data_updates = updates or {}

        if not target_lead_id:
            return False

        stmt = select(Lead).where(
            Lead.lead_id == target_lead_id,
            Lead.deleted_at.is_(None),
        )
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            return False

        applied_fields = {}
        for key, value in data_updates.items():
            if key in self.ALLOWED_LEAD_UPDATE_FIELDS:
                if key in {"budget_min", "budget_max"}:
                    val = float(value) if value is not None else None
                else:
                    val = value
                setattr(lead, key, val)
                applied_fields[key] = val

        lead.updated_at = datetime.now(timezone.utc)

        activity = LeadActivity(
            lead_id=lead.lead_id,
            action_type="REQUIREMENTS_UPDATE",
            outcome="UPDATED",
            note=f"Lead requirements updated: {list(applied_fields.keys())}",
            temperature=lead.temperature,
            stage_before=lead.stage,
            stage_after=lead.stage,
            performed_by="AI_AGENT",
            created_at=datetime.now(timezone.utc),
        )
        session.add(activity)

        await session.commit()
        await session.refresh(lead)
        return True

    async def stage_sensitive_action(
        self,
        agent_name: Optional[str] = None,
        lead_id: Optional[str] = None,
        action_type: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
        *args,
        **kwargs,
    ) -> str:
        """
        Stages a sensitive action in AIApprovalQueue with status='PENDING'.
        Does NOT mutate lead.stage or any other live records.
        Returns the unique approval_id (UUID string).
        """
        if isinstance(agent_name, AsyncSession):
            session = agent_name
            actual_agent_name = str(lead_id)
            target_lead_id = str(action_type)
            act_type = str(payload)
            action_payload = db if isinstance(db, dict) else (args[0] if args else {})
        else:
            session = self._resolve_session(db)
            actual_agent_name = str(agent_name)
            target_lead_id = str(lead_id)
            act_type = str(action_type)
            action_payload = payload or {}

        queue_item = AIApprovalQueue(
            id=str(uuid.uuid4()),
            agent_name=actual_agent_name,
            lead_id=target_lead_id,
            action_type=act_type,
            proposed_payload=action_payload,
            status="PENDING",
            requested_at=datetime.now(timezone.utc),
        )
        session.add(queue_item)
        await session.commit()
        await session.refresh(queue_item)
        return queue_item.id

    async def execute_approved_action(
        self,
        approval_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        review_note: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        *args,
        **kwargs,
    ) -> bool:
        """
        Applies a staged change when a human supervisor approves it.
        Updates AIApprovalQueue to 'APPROVED', mutates the lead according to payload,
        and logs both LeadActivity and AuditLog.
        Returns False if the approval item does not exist or is not in 'PENDING' status.
        """
        if isinstance(approval_id, AsyncSession):
            session = approval_id
            target_approval_id = str(reviewer_id)
            reviewer = str(review_note) if review_note else None
            note = db if isinstance(db, str) else (args[0] if args else None)
        else:
            session = self._resolve_session(db)
            target_approval_id = str(approval_id)
            reviewer = str(reviewer_id) if reviewer_id else None
            note = review_note

        queue_item = await session.get(AIApprovalQueue, target_approval_id)
        if not queue_item or queue_item.status != "PENDING":
            return False

        # Mark approval queue item as approved
        now = datetime.now(timezone.utc)
        queue_item.status = "APPROVED"
        queue_item.reviewed_by = reviewer
        queue_item.reviewed_at = now
        queue_item.review_note = note

        lead = None
        if queue_item.lead_id:
            res = await session.execute(
                select(Lead).where(
                    Lead.lead_id == queue_item.lead_id,
                    Lead.deleted_at.is_(None),
                )
            )
            lead = res.scalar_one_or_none()

        if lead:
            stage_before = lead.stage
            old_state = {"stage": lead.stage, "lost_reason": lead.lost_reason}

            # Apply stage or status changes
            payload = queue_item.proposed_payload or {}
            if queue_item.action_type == "STAGE_CHANGE_LOST":
                lead.stage = "LOST"
                reason = payload.get("reason") or payload.get("lost_reason")
                if reason:
                    lead.lost_reason = str(reason)
            elif queue_item.action_type.startswith("STAGE_CHANGE_"):
                new_st = queue_item.action_type.replace("STAGE_CHANGE_", "")
                lead.stage = payload.get("new_stage") or payload.get("stage") or new_st
            elif "stage" in payload:
                lead.stage = payload["stage"]
            elif "new_stage" in payload:
                lead.stage = payload["new_stage"]

            if "temperature" in payload:
                lead.temperature = payload["temperature"]
            if "lost_reason" in payload and not lead.lost_reason:
                lead.lost_reason = payload["lost_reason"]

            lead.updated_at = now
            new_state = {"stage": lead.stage, "lost_reason": lead.lost_reason, "payload": payload}

            # Log LeadActivity
            activity = LeadActivity(
                lead_id=lead.lead_id,
                action_type=queue_item.action_type,
                outcome="APPROVED",
                note=note or f"Approved {queue_item.action_type} by {reviewer}",
                stage_before=stage_before,
                stage_after=lead.stage,
                temperature=lead.temperature,
                performed_by=reviewer,
                logged_by=reviewer,
                created_at=now,
            )
            session.add(activity)

            # Log AuditLog
            audit = AuditLog(
                id=str(uuid.uuid4()),
                entity_name="Lead",
                entity_id=lead.lead_id,
                action=f"AI_APPROVAL_{queue_item.action_type}",
                old_state=old_state,
                new_state=new_state,
                performed_by=reviewer or "SYSTEM",
                timestamp=now,
            )
            session.add(audit)

        await session.commit()
        return True

    async def reject_staged_action(
        self,
        approval_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        review_note: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        *args,
        **kwargs,
    ) -> bool:
        """
        Marks an AIApprovalQueue entry as 'REJECTED' without modifying the lead entity.
        Logs LeadActivity and AuditLog for full audit trail.
        Returns False if the approval item does not exist or is not in 'PENDING' status.
        """
        if isinstance(approval_id, AsyncSession):
            session = approval_id
            target_approval_id = str(reviewer_id)
            reviewer = str(review_note) if review_note else None
            note = db if isinstance(db, str) else (args[0] if args else None)
        else:
            session = self._resolve_session(db)
            target_approval_id = str(approval_id)
            reviewer = str(reviewer_id) if reviewer_id else None
            note = review_note

        queue_item = await session.get(AIApprovalQueue, target_approval_id)
        if not queue_item or queue_item.status != "PENDING":
            return False

        now = datetime.now(timezone.utc)
        queue_item.status = "REJECTED"
        queue_item.reviewed_by = reviewer
        queue_item.reviewed_at = now
        queue_item.review_note = note

        lead = None
        if queue_item.lead_id:
            res = await session.execute(
                select(Lead).where(
                    Lead.lead_id == queue_item.lead_id,
                    Lead.deleted_at.is_(None),
                )
            )
            lead = res.scalar_one_or_none()

        if lead:
            activity = LeadActivity(
                lead_id=lead.lead_id,
                action_type=f"{queue_item.action_type}_REJECTED",
                outcome="REJECTED",
                note=note or f"Rejected {queue_item.action_type} by {reviewer}",
                stage_before=lead.stage,
                stage_after=lead.stage,
                temperature=lead.temperature,
                performed_by=reviewer,
                logged_by=reviewer,
                created_at=now,
            )
            session.add(activity)

        audit = AuditLog(
            id=str(uuid.uuid4()),
            entity_name="AIApprovalQueue",
            entity_id=queue_item.id,
            action="REJECT_ACTION",
            old_state={"status": "PENDING"},
            new_state={
                "status": "REJECTED",
                "reviewer_id": reviewer,
                "review_note": note,
            },
            performed_by=reviewer or "SYSTEM",
            timestamp=now,
        )
        session.add(audit)

        await session.commit()
        return True

    @classmethod
    def get_tool_definitions(cls) -> List[Dict[str, Any]]:
        """
        Return OpenAPI / OpenAI function calling schemas for LLM tool binding.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_properties",
                    "description": "Search verified live properties matching criteria such as city, locality, budget, and BHK.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string", "description": "City name, e.g. Alwar, Jaipur"},
                            "locality": {"type": "string", "description": "Locality or neighborhood name"},
                            "min_price": {"type": "number", "description": "Minimum budget in INR"},
                            "max_price": {"type": "number", "description": "Maximum budget in INR"},
                            "bhk": {"type": "integer", "description": "Number of bedrooms (e.g. 1, 2, 3)"},
                            "category_code": {"type": "integer", "description": "1=Residential, 2=Commercial, 3=Agricultural, 4=Industrial"},
                            "sub_category_code": {"type": "integer", "description": "1=Flat, 2=House/Villa, 3=Plot, etc."},
                            "listing_type": {"type": "integer", "description": "1=Rent, 2=Sale, 3=PG"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_lead_details",
                    "description": "Fetch current profile and preferences of a lead safely.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lead_id": {"type": "string", "description": "Unique Lead ID (e.g. OB-2026-000001)"},
                        },
                        "required": ["lead_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_lead_requirements",
                    "description": "Safely update non-destructive lead attributes such as budget, city, locality, and temperature.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "lead_id": {"type": "string", "description": "Unique Lead ID"},
                            "updates": {
                                "type": "object",
                                "properties": {
                                    "budget_min": {"type": "number"},
                                    "budget_max": {"type": "number"},
                                    "preferred_city": {"type": "string"},
                                    "preferred_locality": {"type": "string"},
                                    "temperature": {"type": "string", "enum": ["HOT", "WARM", "COLD"]},
                                },
                            },
                        },
                        "required": ["lead_id", "updates"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "stage_sensitive_action",
                    "description": "Stage a sensitive action (e.g. stage change to LOST) into the supervisor approval queue.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_name": {"type": "string", "description": "Name of the calling agent"},
                            "lead_id": {"type": "string", "description": "Target Lead ID"},
                            "action_type": {"type": "string", "description": "Action type (e.g. STAGE_CHANGE_LOST)"},
                            "payload": {"type": "object", "description": "Proposed action payload or reason"},
                        },
                        "required": ["agent_name", "lead_id", "action_type", "payload"],
                    },
                },
            },
        ]
