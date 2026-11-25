from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leads import Lead, LeadActivity
from app.services.ai.llm_client import AIClientService
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.tools import AIToolRegistry
from app.services.ai.prompts import SALES_ASSISTANT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class SalesAssistantAgent:
    """Agent 5: AI Sales Assistant Agent & Human-In-The-Loop (HITL) Copilot.
    
    Acts as an intelligent sales strategy copilot for Propira Omshiv property advisors:
    - Analyzes lead profile and complete chronological interaction history.
    - Generates concise executive sales briefings and actionable next steps.
    - Drafts warm, personalized follow-up messages across channels (WhatsApp, SMS, Call)
      in English, Hindi, or Hinglish.
    - Stages sensitive pipeline stage modifications (e.g. WON, LOST, pricing overrides)
      into the AIApprovalQueue for human supervisor review without mutating live lead stage.
    - Records comprehensive execution audit logs.
    """

    def __init__(
        self,
        db: AsyncSession,
        ai_client: Optional[AIClientService] = None,
        guardrails: Optional[SafetyGuardrailsService] = None,
        tools: Optional[AIToolRegistry] = None,
    ):
        self.db = db
        self.ai_client = ai_client or AIClientService()
        self.guardrails = guardrails or SafetyGuardrailsService(db)
        self.tools = tools or AIToolRegistry(db)
        self.agent_name = "sales_assistant"

    async def _fetch_lead_with_activities(self, lead_id: str) -> Optional[Lead]:
        """Fetch lead and eager-load historical activities."""
        cleaned_id = str(lead_id).strip()
        if not cleaned_id:
            return None

        stmt = (
            select(Lead)
            .options(selectinload(Lead.activities))
            .where(
                Lead.lead_id == cleaned_id,
                Lead.deleted_at.is_(None),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def generate_lead_summary(self, lead_id: str) -> Dict[str, Any]:
        """Generates executive sales briefing and recommended actions for a lead.
        
        1. Checks feature flag ('sales_assistant').
        2. Queries Lead and its LeadActivity interaction history.
        3. Calls AIClientService with SALES_ASSISTANT_SYSTEM_PROMPT.
        4. Records execution audit log.
        """
        # 1. Feature Flag Verification
        mode = await self.guardrails.get_agent_mode(self.agent_name)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="CRM",
                mode=mode,
                trigger_event="GENERATE_SUMMARY",
                output_response="Sales assistant agent is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message="Agent mode is configured to DISABLED",
            )
            return {
                "success": False,
                "error": "Sales assistant agent is disabled by configuration.",
                "lead_id": lead_id,
                "full_name": None,
                "summary": None,
                "recommended_action": None,
            }

        # 2. Query Lead and chronological activity history
        lead = await self._fetch_lead_with_activities(lead_id)
        if not lead:
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="CRM",
                mode=mode,
                trigger_event="GENERATE_SUMMARY",
                output_response=f"Lead {lead_id} not found.",
                status="ERROR",
                error_message=f"Lead {lead_id} not found in database.",
            )
            return {
                "success": False,
                "error": f"Lead {lead_id} not found in database.",
                "lead_id": lead_id,
                "full_name": None,
                "summary": None,
                "recommended_action": None,
            }

        try:
            # Format chronological interaction history
            activities = sorted(lead.activities or [], key=lambda a: a.created_at or datetime.min.replace(tzinfo=timezone.utc))
            timeline_items = []
            for act in activities:
                ts = act.created_at.strftime("%Y-%m-%d %H:%M") if act.created_at else "Unknown date"
                outcome = f" [{act.outcome}]" if act.outcome else ""
                note = f" - {act.note}" if act.note else ""
                timeline_items.append(f"- [{ts}] {act.action_type}{outcome}{note}")

            timeline_str = "\n".join(timeline_items) if timeline_items else "No previous interactions recorded."

            user_prompt = (
                f"Lead ID: {lead.lead_id}\n"
                f"Full Name: {lead.full_name}\n"
                f"Mobile: {lead.mobile}\n"
                f"Current Stage: {lead.stage}\n"
                f"Temperature: {lead.temperature or 'UNKNOWN'}\n"
                f"Budget Range: INR {lead.budget_min} to {lead.budget_max}\n"
                f"Preferred Location: {lead.preferred_city or ''} {lead.preferred_locality or ''}\n\n"
                f"Chronological Interaction History:\n{timeline_str}\n\n"
                f"Produce an executive sales briefing, recommended concrete action, draft message, and talking points."
            )

            fallback = {
                "full_name": lead.full_name,
                "summary": f"Lead {lead.full_name} is in {lead.stage} stage.",
                "recommended_action": "Follow up with customer regarding property preferences.",
                "draft_message": f"Hello {lead.full_name}, thank you for contacting Propira Omshiv.",
                "recommended_stage": lead.stage,
                "requires_hitl": False,
                "talking_points": [],
            }

            parsed = await self.ai_client.chat_completion_json(
                system_prompt=SALES_ASSISTANT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                fallback_data=fallback,
            )

            full_name = parsed.get("full_name") or lead.full_name
            summary = parsed.get("summary") or fallback["summary"]
            recommended_action = parsed.get("recommended_action") or fallback["recommended_action"]
            draft_message = parsed.get("draft_message") or fallback["draft_message"]
            recommended_stage = parsed.get("recommended_stage") or lead.stage
            requires_hitl = bool(parsed.get("requires_hitl", False))
            talking_points = parsed.get("talking_points", [])

            # Record execution log
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="CRM",
                mode=mode,
                trigger_event="GENERATE_SUMMARY",
                input_summary=user_prompt[:500],
                output_response=summary[:500] if summary else None,
                status="SUCCESS",
            )

            return {
                "success": True,
                "lead_id": lead.lead_id,
                "full_name": full_name,
                "summary": summary,
                "recommended_action": recommended_action,
                "draft_message": draft_message,
                "recommended_stage": recommended_stage,
                "requires_hitl": requires_hitl,
                "talking_points": talking_points,
                "current_stage": lead.stage,
                "temperature": lead.temperature,
                "activities_count": len(activities),
            }

        except Exception as exc:
            logger.exception("Error generating sales summary for %s: %s", lead_id, exc)
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="CRM",
                mode=mode,
                trigger_event="GENERATE_SUMMARY",
                output_response=None,
                status="ERROR",
                error_message=str(exc),
            )
            return {
                "success": False,
                "error": str(exc),
                "lead_id": lead_id,
                "full_name": None,
                "summary": None,
                "recommended_action": None,
            }

    async def recommend_followup_message(
        self,
        lead_id: str,
        channel: str = "WHATSAPP",
        language: str = "en",
    ) -> Dict[str, Any]:
        """Drafts personalized follow-up message based on current requirements and past touchpoints."""
        # 1. Feature Flag Verification
        mode = await self.guardrails.get_agent_mode(self.agent_name)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="RECOMMEND_FOLLOWUP",
                output_response="Sales assistant agent is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message="Agent mode is configured to DISABLED",
            )
            return {
                "success": False,
                "error": "Sales assistant agent is disabled by configuration.",
                "lead_id": lead_id,
                "draft_message": None,
            }

        # 2. Query Lead and activities
        lead = await self._fetch_lead_with_activities(lead_id)
        if not lead:
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="RECOMMEND_FOLLOWUP",
                output_response=f"Lead {lead_id} not found.",
                status="ERROR",
                error_message=f"Lead {lead_id} not found in database.",
            )
            return {
                "success": False,
                "error": f"Lead {lead_id} not found in database.",
                "lead_id": lead_id,
                "draft_message": None,
            }

        try:
            activities = sorted(lead.activities or [], key=lambda a: a.created_at or datetime.min.replace(tzinfo=timezone.utc))
            last_activity = activities[-1] if activities else None
            last_activity_str = (
                f"Last Touchpoint: {last_activity.action_type} - {last_activity.outcome}: {last_activity.note}"
                if last_activity else "No prior touchpoints."
            )

            user_prompt = (
                f"Lead ID: {lead.lead_id}\n"
                f"Full Name: {lead.full_name}\n"
                f"Current Stage: {lead.stage}\n"
                f"Temperature: {lead.temperature or 'UNKNOWN'}\n"
                f"Preferred Location: {lead.preferred_city or ''} {lead.preferred_locality or ''}\n"
                f"Budget: INR {lead.budget_min} to {lead.budget_max}\n"
                f"{last_activity_str}\n\n"
                f"Target Outreach Channel: {channel}\n"
                f"Preferred Language: {language}\n\n"
                f"Draft a warm, polite, and persuasive follow-up message for {channel} in {language}."
            )

            fallback = {
                "full_name": lead.full_name,
                "summary": f"Follow-up for {lead.full_name}.",
                "draft_message": f"Hello {lead.full_name}, thank you for your interest with Propira Omshiv Real Estate.",
                "recommended_action": f"Send follow-up message via {channel}.",
                "channel": channel,
                "talking_points": [],
            }

            parsed = await self.ai_client.chat_completion_json(
                system_prompt=SALES_ASSISTANT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                fallback_data=fallback,
            )

            draft_message = parsed.get("draft_message") or fallback["draft_message"]
            recommended_action = parsed.get("recommended_action") or fallback["recommended_action"]
            talking_points = parsed.get("talking_points", [])

            # Record execution log
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="RECOMMEND_FOLLOWUP",
                input_summary=user_prompt[:500],
                output_response=draft_message[:500] if draft_message else None,
                status="SUCCESS",
            )

            return {
                "success": True,
                "lead_id": lead.lead_id,
                "full_name": parsed.get("full_name") or lead.full_name,
                "channel": channel,
                "language": language,
                "draft_message": draft_message,
                "recommended_action": recommended_action,
                "talking_points": talking_points,
            }

        except Exception as exc:
            logger.exception("Error recommending follow-up message for %s: %s", lead_id, exc)
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="RECOMMEND_FOLLOWUP",
                output_response=None,
                status="ERROR",
                error_message=str(exc),
            )
            return {
                "success": False,
                "error": str(exc),
                "lead_id": lead_id,
                "draft_message": None,
            }

    async def request_stage_update(
        self,
        lead_id: str,
        new_stage: str,
        reason: str,
    ) -> str:
        """Stages a sensitive lead pipeline stage change into AIApprovalQueue.
        
        Does NOT modify lead.stage directly! Human supervisor must approve the action.
        Returns the unique approval_id.
        """
        # 1. Feature Flag Verification
        mode = await self.guardrails.get_agent_mode(self.agent_name)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="CRM",
                mode=mode,
                trigger_event="REQUEST_STAGE_UPDATE",
                output_response="Sales assistant agent is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message="Agent mode is configured to DISABLED",
            )
            raise ValueError("Sales assistant agent is disabled by configuration.")

        # 2. Stage sensitive action into approval queue
        clean_stage = str(new_stage).strip()
        action_type = f"STAGE_CHANGE_{clean_stage.upper()}"
        payload = {
            "new_stage": clean_stage,
            "reason": reason,
        }

        approval_id = await self.tools.stage_sensitive_action(
            agent_name=self.agent_name,
            lead_id=lead_id,
            action_type=action_type,
            payload=payload,
            db=self.db,
        )

        # 3. Record execution audit log
        await self.guardrails.record_execution_log(
            agent_name=self.agent_name,
            lead_id=lead_id,
            channel="CRM",
            mode=mode,
            trigger_event="REQUEST_STAGE_UPDATE",
            input_summary=f"Request stage update to {clean_stage}: {reason}",
            output_response=f"Staged sensitive action with approval_id={approval_id}",
            status="PENDING_APPROVAL",
            approval_id=approval_id,
            tools_called=[{
                "tool": "stage_sensitive_action",
                "action_type": action_type,
                "approval_id": approval_id,
            }],
        )

        return approval_id
