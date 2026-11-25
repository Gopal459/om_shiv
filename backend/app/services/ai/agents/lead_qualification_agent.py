from __future__ import annotations
import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.llm_client import AIClientService
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.tools import AIToolRegistry
from app.services.ai.prompts import LEAD_QUALIFICATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LeadQualificationAgent:
    """Agent 2: AI Lead Qualification Agent.
    
    Analyzes customer conversations (WhatsApp chats, web inquiries, call transcripts)
    in English, Hindi, or Hinglish to qualify prospects:
    - Extracts budget range, target locality, timeline, BHK requirements.
    - Computes qualification score (0-100) and temperature (HOT / WARM / COLD / FUTURE_PROSPECT).
    - Safely updates lead requirements (budget, locality, temperature) via AIToolRegistry.
    - If disqualification is proposed, stages a sensitive action in AIApprovalQueue for human review
      WITHOUT directly mutating lead.stage.
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
        self.agent_name = "lead_qualification"

    async def qualify_lead(
        self,
        lead_id: str,
        conversation_transcript: str,
        channel: str = "CRM",
    ) -> Dict[str, Any]:
        """Analyzes conversation transcript and qualifies the lead.
        
        1. Checks feature flag & safety guardrail mode.
        2. Verifies lead exists in database.
        3. Calls AIClientService with LEAD_QUALIFICATION_SYSTEM_PROMPT.
        4. Applies safe non-destructive updates to lead requirements.
        5. If disqualification / stage LOST is proposed, stages sensitive action in approval queue.
        6. Logs execution audit record.
        """
        # 1. Feature Flag Verification
        mode = await self.guardrails.get_agent_mode(self.agent_name)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="LEAD_QUALIFICATION",
                input_summary=conversation_transcript[:500] if conversation_transcript else None,
                output_response="Lead qualification agent is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message="Agent mode is configured to DISABLED",
            )
            return {
                "success": False,
                "error": "Lead qualification agent is disabled by configuration.",
                "lead_id": lead_id,
                "temperature": None,
                "qualification_score": None,
                "budget_min": None,
                "budget_max": None,
                "preferred_city": None,
                "preferred_locality": None,
                "timeline": None,
                "bhk": None,
                "summary": None,
                "recommended_next_action": None,
                "should_disqualify": False,
                "approval_id": None,
            }

        # 2. Verify lead exists
        lead_data = await self.tools.get_lead_details(lead_id=lead_id, db=self.db)
        if not lead_data:
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="LEAD_QUALIFICATION",
                input_summary=conversation_transcript[:500] if conversation_transcript else None,
                output_response=f"Lead {lead_id} not found.",
                status="ERROR",
                error_message=f"Lead {lead_id} not found in database.",
            )
            return {
                "success": False,
                "error": f"Lead {lead_id} not found in database.",
                "lead_id": lead_id,
                "temperature": None,
                "qualification_score": None,
                "budget_min": None,
                "budget_max": None,
                "preferred_city": None,
                "preferred_locality": None,
                "timeline": None,
                "bhk": None,
                "summary": None,
                "recommended_next_action": None,
                "should_disqualify": False,
                "approval_id": None,
            }

        try:
            # 3. Parse conversation transcript via LLM
            lead_name = lead_data.get("full_name") or "Unknown"
            user_prompt = (
                f"Lead ID: {lead_id}\n"
                f"Customer Name: {lead_name}\n"
                f"Current Stage: {lead_data.get('stage')}\n"
                f"Conversation Transcript:\n{conversation_transcript}"
            )

            fallback = {
                "full_name": lead_name,
                "temperature": "WARM",
                "qualification_score": 50,
                "budget_min": None,
                "budget_max": None,
                "preferred_city": None,
                "preferred_localities": [],
                "preferred_locality": None,
                "property_types": [],
                "bhk_preference": None,
                "bhk": None,
                "timeline": "1_TO_3_MONTHS",
                "financing_mode": "UNDECIDED",
                "key_factors": [],
                "summary": "Lead requirements parsed from inquiry.",
                "recommended_next_action": None,
                "should_disqualify": False,
            }

            parsed = await self.ai_client.chat_completion_json(
                system_prompt=LEAD_QUALIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                fallback_data=fallback,
            )

            # Extract fields with type safety
            budget_min = None
            if parsed.get("budget_min") is not None:
                try:
                    budget_min = float(parsed["budget_min"])
                except (ValueError, TypeError):
                    pass

            budget_max = None
            if parsed.get("budget_max") is not None:
                try:
                    budget_max = float(parsed["budget_max"])
                except (ValueError, TypeError):
                    pass

            preferred_city = str(parsed["preferred_city"]).strip() if parsed.get("preferred_city") else None

            preferred_locality = None
            if parsed.get("preferred_locality"):
                preferred_locality = str(parsed["preferred_locality"]).strip()
            elif parsed.get("preferred_localities") and isinstance(parsed["preferred_localities"], list) and len(parsed["preferred_localities"]) > 0:
                preferred_locality = str(parsed["preferred_localities"][0]).strip()

            timeline = str(parsed["timeline"]).strip() if parsed.get("timeline") else None

            bhk = None
            if parsed.get("bhk") is not None:
                try:
                    bhk = int(parsed["bhk"])
                except (ValueError, TypeError):
                    pass
            elif parsed.get("bhk_preference") is not None:
                try:
                    bhk = int(parsed["bhk_preference"])
                except (ValueError, TypeError):
                    pass

            qualification_score = 50
            if parsed.get("qualification_score") is not None:
                try:
                    qualification_score = max(0, min(100, int(parsed["qualification_score"])))
                except (ValueError, TypeError):
                    pass

            temperature = "WARM"
            if parsed.get("temperature"):
                temp_str = str(parsed["temperature"]).strip().upper()
                if temp_str in ("HOT", "WARM", "COLD", "FUTURE_PROSPECT"):
                    temperature = temp_str

            summary = parsed.get("summary") or "Lead profile qualified by AI specialist."
            recommended_next_action = parsed.get("recommended_next_action") or parsed.get("next_action")

            # Determine disqualification flag
            should_disqualify = bool(
                parsed.get("should_disqualify")
                or parsed.get("stage") == "LOST"
                or parsed.get("recommended_stage") == "LOST"
                or str(parsed.get("temperature")).upper() in ("DISQUALIFIED", "INVALID")
            )

            # 4. Safe Non-Destructive Update to Lead Requirements
            updates: Dict[str, Any] = {}
            if budget_min is not None:
                updates["budget_min"] = budget_min
            if budget_max is not None:
                updates["budget_max"] = budget_max
            if preferred_city:
                updates["preferred_city"] = preferred_city
            if preferred_locality:
                updates["preferred_locality"] = preferred_locality
            if temperature:
                updates["temperature"] = temperature

            if updates:
                await self.tools.update_lead_requirements(
                    lead_id=lead_id,
                    updates=updates,
                    db=self.db,
                )

            # 5. Stage sensitive action if disqualification is proposed
            # Note: lead.stage is NOT mutated directly to LOST; it is staged for human supervisor review
            approval_id = None
            if should_disqualify:
                approval_id = await self.tools.stage_sensitive_action(
                    agent_name=self.agent_name,
                    lead_id=lead_id,
                    action_type="STAGE_CHANGE_LOST",
                    payload={
                        "reason": summary or "Disqualified by AI lead qualification agent",
                        "qualification_score": qualification_score,
                        "temperature": temperature,
                        "recommended_next_action": recommended_next_action,
                        "transcript_snippet": conversation_transcript[:300] if conversation_transcript else "",
                    },
                    db=self.db,
                )

            # 6. Record Execution Log
            tools_called: List[Dict[str, Any]] = []
            if updates:
                tools_called.append({
                    "tool": "update_lead_requirements",
                    "updates": updates,
                })
            if approval_id:
                tools_called.append({
                    "tool": "stage_sensitive_action",
                    "action_type": "STAGE_CHANGE_LOST",
                    "approval_id": approval_id,
                })

            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="LEAD_QUALIFICATION",
                input_summary=conversation_transcript[:500] if conversation_transcript else None,
                output_response=summary,
                tools_called=tools_called,
                status="SUCCESS",
                approval_id=approval_id,
            )

            return {
                "success": True,
                "lead_id": lead_id,
                "temperature": temperature,
                "qualification_score": qualification_score,
                "budget_min": budget_min,
                "budget_max": budget_max,
                "preferred_city": preferred_city,
                "preferred_locality": preferred_locality,
                "timeline": timeline,
                "bhk": bhk,
                "summary": summary,
                "recommended_next_action": recommended_next_action,
                "should_disqualify": should_disqualify,
                "approval_id": approval_id,
                "updates_applied": updates,
            }

        except Exception as exc:
            logger.exception("Error executing lead qualification for %s: %s", lead_id, exc)
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="LEAD_QUALIFICATION",
                input_summary=conversation_transcript[:500] if conversation_transcript else None,
                output_response=None,
                status="ERROR",
                error_message=str(exc),
            )
            return {
                "success": False,
                "error": str(exc),
                "lead_id": lead_id,
                "temperature": None,
                "qualification_score": None,
                "budget_min": None,
                "budget_max": None,
                "preferred_city": None,
                "preferred_locality": None,
                "timeline": None,
                "bhk": None,
                "summary": None,
                "recommended_next_action": None,
                "should_disqualify": False,
                "approval_id": None,
            }
