"""Agent 13: AI Voice Calling Agent (Exotel Contract & TRAI Pre-Dial Gate).

Responsible for:
- Pre-Dial Gate 1: TRAI Quiet Hours enforcement (21:00 - 09:00 IST).
- Pre-Dial Gate 2: Customer Consent verification (channel: VOICE).
- Pre-Dial Gate 3: Feature flag mode enforcement (DISABLED, SHADOW, LIVE).
- Outbound Call Dispatch via Exotel Telephony.
- Speech-to-Text transcript ingestion and lead qualification parsing via LeadQualificationAgent.
- Audit logging (AIAgentExecutionLog) and CRM LeadActivity tracking.
"""

from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leads import Lead, LeadActivity
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.telephony_client import ExotelTelephonyClient
from app.services.ai.agents.lead_qualification_agent import LeadQualificationAgent
from app.workers.sla_worker import is_quiet_hours

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))


class VoiceCallingAgent:
    """Agent 13: AI Voice Calling Agent."""

    def __init__(
        self,
        db: AsyncSession,
        telephony_client: Optional[Any] = None,
        guardrails: Optional[SafetyGuardrailsService] = None,
        lead_qualification_agent: Optional[LeadQualificationAgent] = None,
    ):
        self.db = db
        self.guardrails = guardrails or SafetyGuardrailsService(db)
        self.telephony_client = telephony_client or ExotelTelephonyClient()
        self.lead_qualification_agent = (
            lead_qualification_agent
            or LeadQualificationAgent(db, guardrails=self.guardrails)
        )
        self.agent_name = "voice_calling_agent"

    async def trigger_outbound_call(
        self,
        lead_id: str,
        caller_reason: str = "NEW_LEAD_QUALIFICATION",
        bypass_quiet_hours: bool = False,
        check_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Evaluates 3 pre-dial gates and triggers outbound call if permitted.

        Gate 1: Check quiet hours (21:00 - 09:00 IST). Returns status="BLOCKED_QUIET_HOURS" if active.
        Gate 2: Check consent (guardrails.verify_consent(mobile, "VOICE")). Returns status="BLOCKED_NO_CONSENT" if False.
        Gate 3: Check feature flag mode:
          - DISABLED: Returns status="BLOCKED_FLAG", call_dispatched=False.
          - SHADOW: Logs intent with status="SHADOW_LOGGED", call_dispatched=False, no network call.
          - LIVE: Dispatches via telephony_client and logs status="SUCCESS", call_dispatched=True.

        Args:
            lead_id: Target lead identifier.
            caller_reason: Business justification for outbound call.
            bypass_quiet_hours: Explicit bypass for internal testing/urgent overrides.
            check_time: Optional explicit timestamp for quiet-hours evaluation.

        Returns:
            Dictionary with status, mode, call_dispatched, and execution details.
        """
        # Fetch target lead
        stmt = select(Lead).where(Lead.lead_id == lead_id)
        res = await self.db.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            logger.warning("VoiceCallingAgent: Lead %s not found", lead_id)
            return {
                "status": "ERROR",
                "lead_id": lead_id,
                "error": f"Lead {lead_id} not found in database.",
                "call_dispatched": False,
            }

        # Pre-Dial Gate 1: TRAI Quiet Hours (21:00 - 09:00 IST)
        now_ist = check_time or datetime.now(IST)
        in_quiet = is_quiet_hours("21:00", "09:00", check_time=now_ist)
        if in_quiet and not bypass_quiet_hours:
            mode = await self.guardrails.get_agent_mode(self.agent_name)
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="VOICE",
                mode=mode,
                trigger_event=caller_reason,
                input_summary=f"Mobile: {lead.mobile}, Reason: {caller_reason}",
                output_response="Call suppressed by TRAI quiet hours (21:00 to 09:00 IST).",
                status="BLOCKED_QUIET_HOURS",
                error_message="Quiet hours active (21:00 - 09:00 IST)",
            )
            return {
                "status": "BLOCKED_QUIET_HOURS",
                "lead_id": lead_id,
                "call_dispatched": False,
                "reason": "Quiet hours active (21:00 - 09:00 IST)",
            }

        # Pre-Dial Gate 2: TRAI Consent Verification
        has_consent = await self.guardrails.verify_consent(lead.mobile, channel="VOICE")
        if not has_consent:
            mode = await self.guardrails.get_agent_mode(self.agent_name)
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="VOICE",
                mode=mode,
                trigger_event=caller_reason,
                input_summary=f"Mobile: {lead.mobile}, Reason: {caller_reason}",
                output_response="Call suppressed: customer has not provided opt-in consent for voice.",
                status="BLOCKED_NO_CONSENT",
                error_message="Missing or opted-out customer consent for channel VOICE",
            )
            return {
                "status": "BLOCKED_NO_CONSENT",
                "lead_id": lead_id,
                "call_dispatched": False,
                "reason": "Customer consent not found or opted-out for channel VOICE",
            }

        # Pre-Dial Gate 3: Feature Flag Operating Mode
        mode = await self.guardrails.get_agent_mode(self.agent_name)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="VOICE",
                mode=mode,
                trigger_event=caller_reason,
                input_summary=f"Mobile: {lead.mobile}, Reason: {caller_reason}",
                output_response="Voice calling agent is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message="Agent mode is configured to DISABLED",
            )
            return {
                "status": "BLOCKED_FLAG",
                "mode": "DISABLED",
                "lead_id": lead_id,
                "call_dispatched": False,
                "reason": "Voice calling agent is disabled by configuration",
            }

        if mode == "SHADOW":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="VOICE",
                mode="SHADOW",
                trigger_event=caller_reason,
                input_summary=f"Mobile: {lead.mobile}, Reason: {caller_reason}",
                output_response=f"[SHADOW] Outbound voice call simulation logged for lead {lead_id} ({lead.mobile}). Telephony gateway not invoked.",
                status="SHADOW_LOGGED",
            )
            return {
                "status": "SHADOW_LOGGED",
                "mode": "SHADOW",
                "lead_id": lead_id,
                "call_dispatched": False,
                "reason": "Agent operating in SHADOW mode",
            }

        # LIVE mode: check sliding-window rate limit before dispatch
        rate_ok = await self.guardrails.check_rate_limit(lead.mobile, channel="VOICE", max_per_hour=5)
        if not rate_ok:
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="VOICE",
                mode=mode,
                trigger_event=caller_reason,
                input_summary=f"Mobile: {lead.mobile}, Reason: {caller_reason}",
                output_response="Outbound voice call blocked by rate limit.",
                status="RATE_LIMITED",
                error_message="Hourly rate limit exceeded for mobile",
            )
            return {
                "status": "RATE_LIMITED",
                "mode": mode,
                "lead_id": lead_id,
                "call_dispatched": False,
                "reason": "Rate limit exceeded",
            }

        # Dispatch call via telephony client
        call_res = await self.telephony_client.dispatch_call(
            to_mobile=lead.mobile,
            custom_field=lead_id,
            lead_id=lead_id,
        )

        await self.guardrails.record_execution_log(
            agent_name=self.agent_name,
            lead_id=lead_id,
            channel="VOICE",
            mode="LIVE",
            trigger_event=caller_reason,
            input_summary=f"Mobile: {lead.mobile}, Reason: {caller_reason}",
            output_response=f"Outbound call dispatched: {call_res.get('call_sid')}",
            tools_called=[{"tool": "telephony_client.dispatch_call", "result": call_res}],
            status="SUCCESS",
        )

        return {
            "status": "SUCCESS",
            "mode": "LIVE",
            "lead_id": lead_id,
            "call_dispatched": True,
            "call_details": call_res,
        }

    async def process_call_transcript(
        self,
        lead_id: str,
        transcript: str,
        call_duration: int = 0,
        recording_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Parses speech-to-text call conversation, updates lead requirements, and logs activity.

        Args:
            lead_id: Lead identifier.
            transcript: Full transcript of the call.
            call_duration: Call duration in seconds.
            recording_url: Optional audio recording URL.

        Returns:
            Dictionary with qualification summary and execution status.
        """
        stmt = select(Lead).where(Lead.lead_id == lead_id)
        res = await self.db.execute(stmt)
        lead = res.scalar_one_or_none()
        if not lead:
            return {
                "success": False,
                "error": f"Lead {lead_id} not found",
                "lead_id": lead_id,
            }

        # Delegate parsing & qualification to LeadQualificationAgent
        qual_res = await self.lead_qualification_agent.qualify_lead(
            lead_id=lead_id,
            conversation_transcript=transcript,
            channel="VOICE",
        )

        lead.last_contacted_at = datetime.now(timezone.utc)
        lead.is_untouched = False

        note_parts = [f"Voice Call Transcript processed ({call_duration}s)"]
        if recording_url:
            note_parts.append(f"Recording: {recording_url}")
        if transcript:
            note_parts.append(f"Transcript: {transcript[:300]}")
        activity_note = " | ".join(note_parts)

        activity = LeadActivity(
            lead_id=lead_id,
            action_type="VOICE_CALL",
            outcome="TRANSCRIPT_PROCESSED" if qual_res.get("success") else "COMPLETED",
            note=activity_note,
            temperature=lead.temperature,
            stage_before=lead.stage,
            stage_after=lead.stage,
            performed_by="AI_VOICE_AGENT",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(lead)

        return {
            "success": True,
            "lead_id": lead_id,
            "call_duration": call_duration,
            "recording_url": recording_url,
            "qualification": qual_res,
        }
