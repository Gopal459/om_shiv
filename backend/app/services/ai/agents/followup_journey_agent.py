from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leads import Lead, LeadActivity
from app.models.ai_agents import AIAgentConfig
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.llm_client import AIClientService

logger = logging.getLogger(__name__)

TERMINAL_LEAD_STAGES = {"WON", "CLOSED_WON", "LOST", "CLOSED_LOST", "BOOKED", "JUNK", "DROPPED"}

STEP_TEMPLATES: Dict[str, str] = {
    "DAY_0": (
        "Namaste {name}! Welcome to Omshiv Buildcon. Thank you for expressing interest "
        "in our properties. How can we assist you with your property search today?"
    ),
    "DAY_1": (
        "Hello {name}, based on your preferences, we have curated some top property listings "
        "in {city}. Would you like to explore them or schedule a visit?"
    ),
    "DAY_3": (
        "Hi {name}, checking in to see if you had a chance to review the property options "
        "we shared for {city}. Would you like to schedule an on-site visit this week?"
    ),
    "DAY_7": (
        "Dear {name}, we have newly released residential plots and villas in {city}. "
        "Let us know if you'd like more details or assistance from our dedicated property advisor."
    ),
    "DAY_15": (
        "Hello {name}, are you still actively exploring properties in {city}? "
        "We are here to help whenever you are ready with fresh inventory and attractive terms."
    ),
    "DAY_30": (
        "Namaste {name}, exciting new real estate developments and exclusive offers are live "
        "in {city}. Feel free to reach out anytime to get updated brochures and price sheets."
    ),
}


class FollowupJourneyAgent:
    """Agent 10 & 11: AI Follow-Up & Post-Site Visit Nurturing Engine.

    Automates customer lifecycle engagement and post-site visit feedback processing:
    - Agent 10: Lifecycle Nurturing Engine across Day 0, Day 1, Day 3, Day 7, Day 15, Day 30.
      Enforces terminal stage skip, TRAI/DND consent checks, and 24-hour anti-spam cooldown.
    - Agent 11: Post-Site Visit Feedback Analyzer classifying responses into actionable
      intents (FUTURE_PROSPECT, INTERESTED, BUDGET_MISMATCH, NOT_INTERESTED, ESCALATE)
      with automated temperature adjustment, follow-up scheduling, and opt-out execution.
    - Operates safely under feature flags: DISABLED, SHADOW (audit-only), and LIVE.
    """

    def __init__(
        self,
        db: AsyncSession,
        guardrails: Optional[SafetyGuardrailsService] = None,
        ai_client: Optional[AIClientService] = None,
        whatsapp_agent: Optional[Any] = None,
        default_mode: str = "LIVE",
    ):
        self.db = db
        self.guardrails = guardrails or SafetyGuardrailsService(db)
        self.ai_client = ai_client or AIClientService()
        self.whatsapp_agent = whatsapp_agent
        self.agent_name = "followup_journey_agent"
        self.default_mode = default_mode

    async def _get_mode(self) -> str:
        """Resolves agent operating mode from AIAgentConfig or falls back to default."""
        stmt = select(AIAgentConfig).where(AIAgentConfig.agent_name == self.agent_name)
        res = await self.db.execute(stmt)
        config = res.scalar_one_or_none()
        if config and config.mode:
            return config.mode.upper()
        return self.default_mode.upper()

    async def evaluate_nurturing_step(self, lead_id: str) -> Dict[str, Any]:
        """Evaluates and dispatches the appropriate lifecycle nurturing step for a lead.

        Enforces:
        1. Lead existence and active status.
        2. Terminal stage suppression (WON, LOST, etc.).
        3. Feature flag governance (DISABLED, SHADOW, LIVE).
        4. Customer communication consent verification (TRAI/DND).
        5. 24-hour anti-spam activity cooldown.
        6. Lifecycle timing based on lead creation age.

        Args:
            lead_id: Unique lead identifier (e.g., OB-2026-000010).

        Returns:
            Dictionary indicating execution status, determined step, and action metadata.
        """
        # 1. Fetch Lead
        stmt = select(Lead).where(Lead.lead_id == lead_id, Lead.deleted_at.is_(None))
        lead = (await self.db.execute(stmt)).scalar_one_or_none()
        if not lead:
            return {"success": False, "reason": "LEAD_NOT_FOUND"}

        # 2. Check Terminal Stage
        if lead.stage and lead.stage.upper() in TERMINAL_LEAD_STAGES:
            return {"success": True, "action": "SKIPPED_TERMINAL_STAGE"}

        # 3. Check Agent Mode
        mode = await self._get_mode()
        if mode == "DISABLED":
            return {"success": False, "reason": "AGENT_DISABLED"}

        # 4. Check Consent
        has_consent = await self.guardrails.verify_consent(lead.mobile, channel="WHATSAPP")
        if not has_consent:
            return {"success": False, "reason": "NO_CONSENT"}

        # 5. Anti-spam & Cooldown Check (Outreach/Nurture within last 24 hours)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_act_stmt = (
            select(LeadActivity)
            .where(
                LeadActivity.lead_id == lead.lead_id,
                LeadActivity.created_at >= cutoff,
            )
            .order_by(LeadActivity.created_at.desc())
            .limit(1)
        )
        recent_act = (await self.db.execute(recent_act_stmt)).scalar_one_or_none()
        if recent_act:
            return {"success": True, "action": "COOLDOWN_ACTIVE"}

        # 6. Calculate Days Since Lead Creation & Determine Step
        now = datetime.now(timezone.utc)
        created_dt = lead.created_at or now
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        days_since = max(0, (now - created_dt).days)

        if days_since == 0:
            step_name = "DAY_0"
        elif days_since <= 2:
            step_name = "DAY_1"
        elif days_since <= 6:
            step_name = "DAY_3"
        elif days_since <= 14:
            step_name = "DAY_7"
        elif days_since <= 29:
            step_name = "DAY_15"
        else:
            step_name = "DAY_30"

        client_name = (lead.full_name or "Valued Client").strip()
        city_name = (lead.preferred_city or "Alwar").strip()
        template = STEP_TEMPLATES.get(step_name, STEP_TEMPLATES["DAY_0"])
        message_text = template.format(name=client_name, city=city_name)

        # 7. SHADOW Mode Execution
        if mode == "SHADOW":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead.lead_id,
                channel="WHATSAPP",
                mode="SHADOW",
                trigger_event="EVALUATE_NURTURING_STEP",
                input_summary=f"Evaluated nurturing for lead {lead.lead_id} (days={days_since})",
                output_response=f"Shadow nurture {step_name}: {message_text}",
                status="SHADOW_LOGGED",
            )
            return {
                "success": True,
                "mode": "SHADOW",
                "step": step_name,
                "message": message_text,
            }

        # 8. LIVE Mode Execution
        if self.whatsapp_agent and hasattr(self.whatsapp_agent, "dispatch_outbound_message"):
            try:
                await self.whatsapp_agent.dispatch_outbound_message(
                    mobile=lead.mobile,
                    text=message_text,
                    lead_id=lead.lead_id,
                )
            except Exception as exc:
                logger.warning(f"Error dispatching via injected whatsapp_agent: {exc}")

        activity = LeadActivity(
            lead_id=lead.lead_id,
            action_type="FOLLOW_UP_NURTURE",
            outcome="SENT",
            note=f"Nurturing step {step_name} sent: {message_text}",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(activity)
        await self.db.commit()

        await self.guardrails.record_execution_log(
            agent_name=self.agent_name,
            lead_id=lead.lead_id,
            channel="WHATSAPP",
            mode="LIVE",
            trigger_event="EVALUATE_NURTURING_STEP",
            input_summary=f"Evaluated nurturing for lead {lead.lead_id} (days={days_since})",
            output_response=f"Live nurture {step_name}: {message_text}",
            status="SUCCESS",
        )

        return {
            "success": True,
            "mode": "LIVE",
            "step": step_name,
            "message": message_text,
        }

    async def process_post_visit_feedback(
        self,
        lead_id: str,
        visit_id: str,
        feedback_text: str,
    ) -> Dict[str, Any]:
        """Analyzes post-site visit customer feedback, adjusting lead state and scheduling follow-ups.

        Args:
            lead_id: CRM lead identifier.
            visit_id: Unique site visit identifier (e.g. SV-1).
            feedback_text: Natural language customer feedback.

        Returns:
            Dictionary containing processed intent, summary, scheduled follow-up days, and mode.
        """
        # 1. Fetch Lead
        stmt = select(Lead).where(Lead.lead_id == lead_id, Lead.deleted_at.is_(None))
        lead = (await self.db.execute(stmt)).scalar_one_or_none()
        if not lead:
            return {"success": False, "reason": "LEAD_NOT_FOUND"}

        # 2. Check Agent Mode
        mode = await self._get_mode()
        if mode == "DISABLED":
            return {"success": False, "reason": "AGENT_DISABLED"}

        # 3. Rule-based Fallback Heuristics
        lower_text = (feedback_text or "").lower().strip()
        fallback_intent = "INTERESTED"
        fallback_months = 0
        fallback_days = 7
        fallback_summary = (feedback_text or "").strip()

        if any(w in lower_text for w in ["stop", "unsubscribe", "mat karo", "not interested", "nahi chahiye", "don't call", "never call", "nahi lena"]):
            fallback_intent = "NOT_INTERESTED"
            fallback_days = 0
            fallback_summary = "Customer requested to stop / not interested"
        elif any(w in lower_text for w in ["3 mahine", "3 months", "months", "baad", "future", "baad me", "agle saal", "later", "planning"]):
            fallback_intent = "FUTURE_PROSPECT"
            fallback_months = 3
            fallback_days = 60
            fallback_summary = "Liked property but planning purchase in future / 3 months"
        elif any(w in lower_text for w in ["budget", "expensive", "costly", "mehenga", "price high", "jyada"]):
            fallback_intent = "BUDGET_MISMATCH"
            fallback_days = 14
            fallback_summary = "Budget mismatch or price concerns"
        elif any(w in lower_text for w in ["token", "book", "finalize", "deal", "kharidna", "pasand", "acchi lagi"]):
            fallback_intent = "INTERESTED"
            fallback_days = 2
            fallback_summary = "Customer expressed high interest to proceed or book"

        fallback_data = {
            "intent": fallback_intent,
            "timeline_months": fallback_months,
            "feedback_summary": fallback_summary,
            "scheduled_follow_up_days": fallback_days,
        }

        # 4. LLM Classification via AI Client
        system_prompt = (
            "You are an AI post-site-visit feedback classifier for Omshiv Buildcon (Indian real estate). "
            "Analyze customer feedback and classify into JSON: "
            "intent (FUTURE_PROSPECT, INTERESTED, BUDGET_MISMATCH, NOT_INTERESTED, ESCALATE), "
            "timeline_months (integer), "
            "feedback_summary (concise English summary), "
            "scheduled_follow_up_days (integer days to wait before next contact)."
        )
        user_prompt = f"Customer post-visit feedback for visit {visit_id}: \"{feedback_text}\""

        parsed: Optional[Dict[str, Any]] = None
        if hasattr(self.ai_client, "chat_completion_json"):
            try:
                parsed = await self.ai_client.chat_completion_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    fallback_data=fallback_data,
                )
            except Exception as exc:
                logger.warning(f"AIClient chat_completion_json failed: {exc}")
                parsed = fallback_data
        elif hasattr(self.ai_client, "generate_response"):
            try:
                resp = await self.ai_client.generate_response(system_prompt, user_prompt)
                if isinstance(resp, dict):
                    parsed = resp
            except Exception as exc:
                logger.warning(f"AIClient generate_response failed: {exc}")
                parsed = fallback_data

        if not parsed or not isinstance(parsed, dict) or "intent" not in parsed:
            parsed = fallback_data

        intent = str(parsed.get("intent") or fallback_intent).upper()
        timeline_months = int(parsed.get("timeline_months") or fallback_months)
        feedback_summary = str(parsed.get("feedback_summary") or fallback_summary)
        scheduled_follow_up_days = int(parsed.get("scheduled_follow_up_days") or fallback_days)

        if intent == "FUTURE_PROSPECT" and scheduled_follow_up_days < 60:
            scheduled_follow_up_days = 60
        elif intent == "INTERESTED" and scheduled_follow_up_days <= 0:
            scheduled_follow_up_days = 2

        # 5. Determine Temperature and Follow-up Date
        now = datetime.now(timezone.utc)
        follow_up_date = now + timedelta(days=scheduled_follow_up_days) if scheduled_follow_up_days > 0 else None

        new_temp = lead.temperature
        if intent == "FUTURE_PROSPECT":
            new_temp = "FUTURE_PROSPECT"
        elif intent == "INTERESTED":
            new_temp = "HOT"
        elif intent == "NOT_INTERESTED":
            new_temp = "COLD"
        elif intent == "BUDGET_MISMATCH":
            new_temp = "WARM"
        elif intent == "ESCALATE":
            new_temp = "HOT"

        # Check for explicit opt-out
        is_opt_out = (
            intent == "NOT_INTERESTED"
            or any(w in lower_text for w in ["stop", "unsubscribe", "mat karo", "don't call", "never call"])
        )

        # 6. SHADOW Mode Execution
        if mode == "SHADOW":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead.lead_id,
                channel="WHATSAPP",
                mode="SHADOW",
                trigger_event="POST_VISIT_FEEDBACK",
                input_summary=f"Visit {visit_id} feedback: {feedback_text}",
                output_response=f"Intent: {intent}, FollowUp: {scheduled_follow_up_days}d, Summary: {feedback_summary}",
                status="SHADOW_LOGGED",
            )
            return {
                "success": True,
                "lead_id": lead_id,
                "visit_id": visit_id,
                "intent": intent,
                "feedback_summary": feedback_summary,
                "scheduled_follow_up_days": scheduled_follow_up_days,
                "mode": "SHADOW",
            }

        # 7. LIVE Mode Execution
        if is_opt_out:
            if hasattr(self.guardrails, "record_opt_out"):
                await self.guardrails.record_opt_out(lead.mobile, channel="WHATSAPP")
            else:
                await self.guardrails.register_consent(
                    lead.mobile, channel="WHATSAPP", is_opted_in=False, reason="Customer requested STOP"
                )

        lead.temperature = new_temp

        activity = LeadActivity(
            lead_id=lead.lead_id,
            action_type="POST_VISIT_FEEDBACK",
            outcome=intent,
            note=feedback_summary,
            follow_up_date=follow_up_date,
            stage_before=lead.stage,
            stage_after=lead.stage,
            temperature=new_temp,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(lead)

        await self.guardrails.record_execution_log(
            agent_name=self.agent_name,
            lead_id=lead.lead_id,
            channel="WHATSAPP",
            mode="LIVE",
            trigger_event="POST_VISIT_FEEDBACK",
            input_summary=f"Visit {visit_id} feedback: {feedback_text}",
            output_response=f"Intent: {intent}, FollowUp: {scheduled_follow_up_days}d, Summary: {feedback_summary}",
            status="SUCCESS",
        )

        return {
            "success": True,
            "lead_id": lead_id,
            "visit_id": visit_id,
            "intent": intent,
            "feedback_summary": feedback_summary,
            "scheduled_follow_up_days": scheduled_follow_up_days,
            "mode": "LIVE",
        }
