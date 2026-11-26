from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leads import Lead, LeadActivity
from app.models.properties import Property
from app.models.ai_agents import AIAgentConfig, AIAgentExecutionLog
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.llm_client import AIClientService

logger = logging.getLogger(__name__)

DEFAULT_DAILY_SLOTS: List[str] = ["10:00", "11:30", "14:00", "15:30", "17:00"]
TERMINAL_LEAD_STAGES = {"WON", "CLOSED_WON", "LOST", "CLOSED_LOST", "BOOKED", "JUNK", "DROPPED"}


def _parse_slot_datetime(slot: str) -> Tuple[Optional[datetime], str, str]:
    """Parses slot string into a datetime object, date string, and time string.
    
    Handles formats such as:
    - YYYY-MM-DD HH:MM
    - YYYY-MM-DDTHH:MM
    - YYYY-MM-DD HH:MM:SS
    - DD-MM-YYYY HH:MM
    - HH:MM
    """
    if not slot:
        return None, "", ""
    clean = slot.strip()

    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(clean, fmt)
            return dt, dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
        except ValueError:
            continue

    # Try parsing time only
    try:
        dt_time = datetime.strptime(clean, "%H:%M")
        return None, "", dt_time.strftime("%H:%M")
    except ValueError:
        pass

    return None, "", clean


def _normalize_date_str(date_input: str) -> str:
    """Normalizes input date string to YYYY-MM-DD format."""
    if not date_input:
        return ""
    clean = date_input.strip()
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return clean


class SiteVisitAgent:
    """Agent 4: AI Site Visit Booking Agent.
    
    Coordinates property site visits between leads and listing advisors:
    - Checks daily slot availability for listings.
    - Prevents double-booking conflicts.
    - Enforces safety guardrails (DISABLED, SHADOW, LIVE).
    - In LIVE mode: logs LeadActivity, advances lead stage to SITE_VISIT_SCHEDULED,
      and produces customer confirmation details.
    - In SHADOW mode: records audit execution without creating CRM activity.
    """

    def __init__(
        self,
        db: AsyncSession,
        guardrails: Optional[SafetyGuardrailsService] = None,
        ai_client: Optional[AIClientService] = None,
        default_mode: str = "LIVE",
    ):
        self.db = db
        self.guardrails = guardrails or SafetyGuardrailsService(db)
        self.ai_client = ai_client or AIClientService()
        self.agent_name = "site_visit_agent"
        self.default_mode = default_mode

    async def _get_mode(self) -> str:
        """Resolves agent operating mode from AIAgentConfig or falls back to default."""
        stmt = select(AIAgentConfig).where(AIAgentConfig.agent_name == self.agent_name)
        res = await self.db.execute(stmt)
        config = res.scalar_one_or_none()
        if config and config.mode:
            return config.mode.upper()
        return self.default_mode.upper()

    async def check_available_slots(
        self,
        property_id: str,
        visit_date: str,
        daily_slots: Optional[List[str]] = None,
    ) -> List[str]:
        """Returns list of open daily slots for a property on a given date.
        
        Args:
            property_id: Unique property ID (e.g. OP-2026-00006).
            visit_date: Target date string (e.g. '2026-12-01').
            daily_slots: Optional custom slot schedule, defaults to DEFAULT_DAILY_SLOTS.
        
        Returns:
            List of available slot time strings (e.g. ['10:00', '14:00', ...]).
        """
        all_slots = list(daily_slots or DEFAULT_DAILY_SLOTS)
        norm_date = _normalize_date_str(visit_date)

        # Query existing scheduled visits
        stmt = select(LeadActivity).where(
            LeadActivity.action_type == "SITE_VISIT",
            LeadActivity.outcome == "SCHEDULED",
        )
        res = await self.db.execute(stmt)
        activities = res.scalars().all()

        booked_slots = set()
        for act in activities:
            note_text = act.note or ""
            if property_id not in note_text:
                continue

            # Check if visit matches visit_date
            date_matches = False
            slot_time = None

            if act.follow_up_date:
                act_date = act.follow_up_date.strftime("%Y-%m-%d")
                if act_date == norm_date:
                    date_matches = True
                    slot_time = act.follow_up_date.strftime("%H:%M")

            if not date_matches and (norm_date in note_text or visit_date in note_text):
                date_matches = True

            if date_matches:
                if slot_time:
                    booked_slots.add(slot_time)
                # Also check if any known slot string is in the note
                for s in all_slots:
                    if s in note_text:
                        booked_slots.add(s)

        return [s for s in all_slots if s not in booked_slots]

    async def book_site_visit(
        self,
        lead_id: str,
        property_id: str,
        slot: str,
        visitor_notes: str = "",
    ) -> Dict[str, Any]:
        """Books a site visit for a lead on a property at the specified slot.
        
        Args:
            lead_id: Unique lead identifier.
            property_id: Unique property listing identifier.
            slot: Datetime or time slot string (e.g. '2026-12-01 11:00').
            visitor_notes: Optional special instructions or visitor notes.
            
        Returns:
            Dict containing success boolean, booking_id, mode, and confirmation message.
        """
        # 1. Validate lead existence
        lead_res = await self.db.execute(select(Lead).where(Lead.lead_id == lead_id))
        lead = lead_res.scalar_one_or_none()
        if not lead:
            return {
                "success": False,
                "reason": "NOT_FOUND",
                "message": f"Lead '{lead_id}' not found.",
                "error": f"Lead '{lead_id}' not found.",
            }

        # 2. Validate property existence
        prop_res = await self.db.execute(select(Property).where(Property.property_id == property_id))
        prop = prop_res.scalar_one_or_none()
        if not prop:
            return {
                "success": False,
                "reason": "NOT_FOUND",
                "message": f"Property '{property_id}' not found.",
                "error": f"Property '{property_id}' not found.",
            }

        # 3. Check agent mode
        mode = await self._get_mode()
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="CRM",
                mode="DISABLED",
                trigger_event="BOOK_SITE_VISIT",
                input_summary=f"Booking request for property {property_id} at {slot}",
                output_response="Site visit booking agent is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message="Agent mode is configured to DISABLED",
            )
            return {
                "success": False,
                "reason": "AGENT_DISABLED",
                "message": "Site visit booking agent is disabled by configuration.",
                "error": "Site visit booking agent is disabled by configuration.",
                "mode": "DISABLED",
            }

        # 4. Double-booking check
        parsed_dt, slot_date, slot_time = _parse_slot_datetime(slot)

        stmt = select(LeadActivity).where(
            LeadActivity.action_type == "SITE_VISIT",
            LeadActivity.outcome == "SCHEDULED",
        )
        res = await self.db.execute(stmt)
        existing_activities = res.scalars().all()

        is_already_booked = False
        for act in existing_activities:
            note_text = act.note or ""
            if property_id not in note_text:
                continue

            if parsed_dt and act.follow_up_date:
                if act.follow_up_date.strftime("%Y-%m-%d %H:%M") == parsed_dt.strftime("%Y-%m-%d %H:%M"):
                    is_already_booked = True
                    break

            if slot.strip() in note_text:
                is_already_booked = True
                break

        if is_already_booked:
            return {
                "success": False,
                "reason": "SLOT_UNAVAILABLE",
                "message": f"Slot '{slot}' already booked for property {property_id}",
            }

        # 5. Format human-readable confirmation message
        prop_title = prop.title or f"Property {property_id}"
        loc = prop.locality or prop.city or "Rajasthan"
        visitor_name = lead.full_name or "Client"
        clean_notes = visitor_notes.strip() if visitor_notes else ""
        notes_str = f" Notes: {clean_notes}" if clean_notes else ""

        confirmation_message = (
            f"Site visit confirmed for {visitor_name} to visit '{prop_title}' "
            f"[{property_id}] in {loc} at {slot}.{notes_str}"
        ).strip()

        # 6. SHADOW Mode Handling
        if mode == "SHADOW":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="CRM",
                mode="SHADOW",
                trigger_event="BOOK_SITE_VISIT",
                input_summary=f"Booking request for property {property_id} at {slot}. Notes: {clean_notes}".strip(),
                output_response=confirmation_message,
                tools_called=[{
                    "tool": "book_site_visit",
                    "property_id": property_id,
                    "slot": slot,
                    "mode": "SHADOW",
                }],
                status="SHADOW_LOGGED",
            )
            return {
                "success": True,
                "booking_id": None,
                "mode": "SHADOW",
                "lead_id": lead_id,
                "property_id": property_id,
                "slot": slot,
                "confirmation_message": confirmation_message,
            }

        # 7. LIVE Mode Handling
        note_content = f"Site visit scheduled for {property_id} at {slot}."
        if clean_notes:
            note_content += f" Notes: {clean_notes}"

        activity = LeadActivity(
            lead_id=lead.lead_id,
            action_type="SITE_VISIT",
            outcome="SCHEDULED",
            note=note_content,
            follow_up_date=parsed_dt,
            stage_before=lead.stage,
            stage_after="SITE_VISIT_SCHEDULED",
        )
        self.db.add(activity)

        # Update lead stage if not already in terminal stage
        if not lead.stage or lead.stage.upper() not in TERMINAL_LEAD_STAGES:
            lead.stage = "SITE_VISIT_SCHEDULED"

        await self.db.commit()
        await self.db.refresh(activity)

        await self.guardrails.record_execution_log(
            agent_name=self.agent_name,
            lead_id=lead_id,
            channel="CRM",
            mode="LIVE",
            trigger_event="BOOK_SITE_VISIT",
            input_summary=f"Booking request for property {property_id} at {slot}. Notes: {clean_notes}".strip(),
            output_response=confirmation_message,
            tools_called=[{
                "tool": "book_site_visit",
                "booking_id": activity.id,
                "property_id": property_id,
                "slot": slot,
                "mode": "LIVE",
            }],
            status="SUCCESS",
        )

        return {
            "success": True,
            "booking_id": activity.id,
            "mode": "LIVE",
            "lead_id": lead_id,
            "property_id": property_id,
            "slot": slot,
            "confirmation_message": confirmation_message,
        }
