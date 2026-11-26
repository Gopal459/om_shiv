from __future__ import annotations
import re
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leads import Lead, LeadActivity, LeadSequence
from app.models.ai_agents import CustomerConsent
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.agents.lead_qualification_agent import LeadQualificationAgent
from app.services.intake_service import get_next_lead_id

logger = logging.getLogger(__name__)


def _clean_phone(phone: Optional[str]) -> str:
    """Clean phone number keeping only numeric digits without '+' prefix."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    return digits


def _extract_mobile_from_text(text: Any) -> Optional[str]:
    """Extract first 10-12 digit mobile number from freeform text or dictionary."""
    if isinstance(text, dict):
        text = text.get("text") or text.get("body") or ""
    if not text or not isinstance(text, str):
        return None
    match = re.search(r"\b(?:(?:\+?91)?[6-9]\d{9})\b", text)
    if match:
        return _clean_phone(match.group(0))
    return None


class MetaLeadAgent:
    """Agent 8 (Meta Ads) & Agent 9 (Instagram) Omnichannel Intake Agent.
    
    Processes webhook leads from Meta Lead Ads and Instagram Direct/Inquiries:
    - Enforces safety guardrail feature flags (meta_lead_agent / instagram_agent).
    - Normalizes and validates payload attributes (full_name, mobile, email, city, etc.).
    - Deduplicates against existing leads via idempotency_key or mobile.
    - Records explicit customer consent for TRAI/WhatsApp compliance.
    - Creates new Lead entities with atomic annual sequence numbering.
    - Triggers LeadQualificationAgent when custom form answers/questions exist.
    - Emits execution audit logs into AIAgentExecutionLog.
    """

    def __init__(
        self,
        db: AsyncSession,
        guardrails: Optional[SafetyGuardrailsService] = None,
        qualification_agent: Optional[LeadQualificationAgent] = None,
    ):
        self.db = db
        self.guardrails = guardrails or SafetyGuardrailsService(db)
        self.qualification_agent = qualification_agent

    async def process_meta_lead(
        self,
        payload: Dict[str, Any],
        channel: str = "META_LEAD_ADS",
    ) -> Dict[str, Any]:
        """Ingests a lead from Meta Ads or Instagram.
        
        Args:
            payload: Webhook or form payload dictionary.
            channel: Intake channel (e.g. 'META_LEAD_ADS' or 'INSTAGRAM').
        
        Returns:
            Dictionary with creation status, lead_id, consent, and qualification.
        """
        norm_channel = channel.upper()
        agent_flag = "instagram_agent" if "INSTAGRAM" in norm_channel else "meta_lead_agent"

        # 1. Feature Flag / Shadow Mode check
        mode = await self.guardrails.get_agent_mode(agent_flag)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=agent_flag,
                channel=norm_channel,
                mode=mode,
                trigger_event="LEAD_INTAKE",
                input_summary=str(payload)[:500],
                output_response=f"{agent_flag} is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message=f"Agent mode for {agent_flag} is DISABLED",
            )
            return {
                "created": False,
                "is_duplicate": False,
                "status": "blocked",
                "error": f"{agent_flag} is disabled by configuration.",
            }

        # 2. Extract and normalize fields from payload
        raw_mobile = (
            payload.get("mobile")
            or payload.get("phone")
            or payload.get("phone_number")
            or payload.get("contact_number")
        )
        if not raw_mobile and payload.get("message"):
            raw_mobile = _extract_mobile_from_text(payload["message"])

        mobile = _clean_phone(raw_mobile) if raw_mobile else ""
        if not mobile:
            await self.guardrails.record_execution_log(
                agent_name=agent_flag,
                channel=norm_channel,
                mode=mode,
                trigger_event="LEAD_INTAKE",
                input_summary=str(payload)[:500],
                output_response="Lead payload missing required mobile number.",
                status="ERROR",
                error_message="Missing mobile number in intake payload.",
            )
            return {
                "created": False,
                "is_duplicate": False,
                "status": "missing_mobile",
                "error": "Mobile number is required.",
            }

        full_name = (
            payload.get("full_name")
            or payload.get("name")
            or payload.get("sender_name")
            or payload.get("username")
            or ("Instagram Lead" if "INSTAGRAM" in norm_channel else "Meta Lead")
        )
        email = payload.get("email")
        city = payload.get("city") or payload.get("preferred_city") or "Jaipur"
        locality = payload.get("locality") or payload.get("preferred_locality")
        budget_min = payload.get("budget_min")
        budget_max = payload.get("budget_max")
        idempotency_key = (
            payload.get("idempotency_key")
            or payload.get("leadgen_id")
            or payload.get("sender_id")
            or payload.get("id")
        )
        if idempotency_key:
            idempotency_key = str(idempotency_key)

        # 3. Deduplication check: idempotency_key or mobile
        phone_variants = [mobile]
        if len(mobile) == 10:
            phone_variants.append(f"91{mobile}")
        elif len(mobile) == 12 and mobile.startswith("91"):
            phone_variants.append(mobile[2:])

        dedup_conditions = [Lead.mobile.in_(phone_variants)]
        if idempotency_key:
            dedup_conditions.append(Lead.idempotency_key == idempotency_key)

        stmt = (
            select(Lead)
            .where(or_(*dedup_conditions))
            .order_by(Lead.created_at.desc())
        )
        res = await self.db.execute(stmt)
        existing_lead = res.scalars().first()

        if existing_lead:
            activity = LeadActivity(
                lead_id=existing_lead.lead_id,
                action_type="REPEAT_INQUIRY",
                outcome="Duplicate Suppressed",
                note=f"Repeat intake inquiry via {norm_channel} (idempotency: {idempotency_key})",
                logged_by="SYSTEM",
            )
            self.db.add(activity)

            await self.guardrails.record_execution_log(
                agent_name=agent_flag,
                lead_id=existing_lead.lead_id,
                channel=norm_channel,
                mode=mode,
                trigger_event="LEAD_INTAKE_DEDUP",
                input_summary=f"Duplicate intake attempt for {mobile} / {idempotency_key}",
                output_response=f"Matched existing lead {existing_lead.lead_id}",
                status="DUPLICATE",
            )
            await self.db.commit()

            return {
                "created": False,
                "is_duplicate": True,
                "status": "duplicate",
                "lead_id": existing_lead.lead_id,
                "mobile": existing_lead.mobile,
                "full_name": existing_lead.full_name,
            }

        # 4. Record Customer Consent (WHATSAPP, is_opted_in=True)
        now = datetime.now(timezone.utc)
        consent_stmt = (
            select(CustomerConsent)
            .where(
                CustomerConsent.mobile.in_(phone_variants),
                func.upper(CustomerConsent.channel) == "WHATSAPP",
            )
            .order_by(CustomerConsent.id.desc())
            .limit(1)
        )
        c_res = await self.db.execute(consent_stmt)
        consent = c_res.scalar_one_or_none()

        if consent:
            consent.is_opted_in = True
            consent.consent_source = "META_LEAD_FORM"
            consent.opted_in_at = now
            consent.updated_at = now
        else:
            consent = CustomerConsent(
                mobile=mobile,
                channel="WHATSAPP",
                is_opted_in=True,
                consent_source="META_LEAD_FORM",
                opted_in_at=now,
                created_at=now,
                updated_at=now,
            )
            self.db.add(consent)

        # 5. Create new Lead
        lead_id = await get_next_lead_id(self.db)
        new_lead = Lead(
            lead_id=lead_id,
            idempotency_key=idempotency_key,
            full_name=full_name,
            mobile=mobile,
            email=email,
            lead_type="BUYER",
            source=norm_channel,
            stage="NEW",
            is_untouched=True,
            is_duplicate=False,
            is_test=False,
            preferred_city=city,
            preferred_locality=locality,
            budget_min=budget_min,
            budget_max=budget_max,
            created_at=now,
            updated_at=now,
        )
        self.db.add(new_lead)
        await self.db.flush()

        # Log intake activity
        activity = LeadActivity(
            lead_id=new_lead.lead_id,
            action_type="INTAKE",
            outcome="Lead Ingested",
            note=f"Inbound lead created via {norm_channel} form/message",
            logged_by="SYSTEM",
        )
        self.db.add(activity)

        # 6. Automatic Lead Qualification if questions/answers exist
        qualification_result = None
        transcript_lines = []

        questions = payload.get("questions") or payload.get("questions_and_answers")
        if isinstance(questions, list):
            for q in questions:
                if isinstance(q, dict):
                    q_text = q.get("question") or q.get("name") or q.get("title") or ""
                    a_text = q.get("answer") or q.get("value") or (", ".join(map(str, q.get("values", []))) if isinstance(q.get("values"), list) else "")
                    transcript_lines.append(f"Q: {q_text}\nA: {a_text}")
                elif isinstance(q, str):
                    transcript_lines.append(q)
        elif isinstance(questions, dict):
            for k, v in questions.items():
                transcript_lines.append(f"Q: {k}\nA: {v}")

        form_data = payload.get("form_data") or payload.get("field_data") or payload.get("custom_questions")
        if isinstance(form_data, list):
            for f in form_data:
                if isinstance(f, dict):
                    name = f.get("name", "")
                    vals = f.get("values", [])
                    transcript_lines.append(f"Field: {name} = {', '.join(map(str, vals)) if isinstance(vals, list) else vals}")
        elif isinstance(form_data, dict):
            for k, v in form_data.items():
                transcript_lines.append(f"{k}: {v}")

        msg_val = payload.get("message")
        if isinstance(msg_val, dict):
            msg_text = msg_val.get("text") or msg_val.get("body") or ""
            if msg_text:
                transcript_lines.append(f"Message: {msg_text}")
        elif msg_val:
            transcript_lines.append(f"Message: {msg_val}")

        if transcript_lines:
            transcript = "\n".join(transcript_lines)
            if self.qualification_agent is None:
                self.qualification_agent = LeadQualificationAgent(self.db, guardrails=self.guardrails)
            try:
                qualification_result = await self.qualification_agent.qualify_lead(
                    lead_id=new_lead.lead_id,
                    conversation_transcript=transcript,
                    channel=norm_channel,
                )
            except Exception as exc:
                logger.warning("LeadQualificationAgent failed for %s: %s", new_lead.lead_id, exc)

        # 7. Record execution log
        await self.guardrails.record_execution_log(
            agent_name=agent_flag,
            lead_id=new_lead.lead_id,
            channel=norm_channel,
            mode=mode,
            trigger_event="LEAD_INTAKE",
            input_summary=f"Intake for {full_name} ({mobile}) via {norm_channel}",
            output_response=f"Created Lead {new_lead.lead_id} successfully.",
            status="SUCCESS",
        )

        await self.db.commit()
        await self.db.refresh(new_lead)

        return {
            "created": True,
            "is_duplicate": False,
            "status": "created",
            "lead_id": new_lead.lead_id,
            "mobile": new_lead.mobile,
            "full_name": new_lead.full_name,
            "source": new_lead.source,
            "stage": new_lead.stage,
            "is_untouched": new_lead.is_untouched,
            "qualification": qualification_result,
        }
