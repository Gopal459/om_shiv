from __future__ import annotations
import logging
import re
from typing import Optional, Dict, Any, List

from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.properties import Property, PropResidentialFlat, PropHouseVilla
from app.services.ai.llm_client import AIClientService
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.tools import AIToolRegistry
from app.services.ai.prompts import CUSTOMER_SUPPORT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _detect_escalation_triggers(text: str) -> tuple[bool, Optional[str]]:
    """Deterministic safety net detecting high-risk customer complaints or escalation triggers."""
    if not text:
        return False, None

    lower = text.lower()

    # 1. Fraud / Cheating / Criminal Allegations
    if re.search(r"\b(fraud|cheat|cheating|cheated|scam|scammer|scammed|forgery|extortion|stolen|loot|bribe)\b", lower):
        return True, "FRAUD_ALLEGATION"

    # 2. Legal / Police / Regulatory Dispute
    if re.search(r"\b(legal|lawyer|advocate|court|police|fir|litigation|notice|dispute|tribunal|rera\s*complaint|file\s*a\s*case|sue)\b", lower):
        return True, "LEGAL_DISPUTE"

    # 3. Explicit Human / Manager Requests
    if re.search(r"\b(talk\s*to\s*(?:a\s*|an\s*)?(?:human|person|agent|executive|manager|director|owner|boss|supervisor)|speak\s*with|call\s*me\s*back|connect\s*(?:me\s*)?to\s*human)\b", lower):
        return True, "HUMAN_REQUEST"

    # 4. Severe Customer Dissatisfaction / Harassment / Financial Forfeiture
    if re.search(r"\b(harassment|harass|terrible\s*service|worst\s*(?:agency|broker|service)|unacceptable|forfeit|deposit\s*refund|illegal\s*fee|money\s*back)\b", lower):
        return True, "CUSTOMER_COMPLAINT"

    # 5. Complex Legal Negotiation
    if re.search(r"\b(contract\s*amendment|title\s*verification|patta\s*dispute|non-standard\s*agreement)\b", lower):
        return True, "COMPLEX_NEGOTIATION"

    return False, None


class CustomerSupportAgent:
    """Agent 3: AI Customer Support Agent & Escalation Router.
    
    Provides accurate, polite customer support regarding verified property listings, office hours,
    site visit procedures, documentation requirements, and company policies.
    Guards against hallucinations by strictly citing verified database listings.
    Detects complaints, legal disputes, fraud allegations, and complex negotiations, escalating
    immediately to human managers with structured routing reasons.
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
        self.agent_name = "customer_support"

    async def _fetch_property_context(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Safely fetch verified property details by property_id or ID."""
        pid_clean = str(property_id).strip()
        if not pid_clean:
            return None

        is_numeric = pid_clean.isdigit()
        stmt = (
            select(Property)
            .outerjoin(PropResidentialFlat, Property.id == PropResidentialFlat.property_id)
            .outerjoin(PropHouseVilla, Property.id == PropHouseVilla.property_id)
            .options(
                selectinload(Property.flat_details),
                selectinload(Property.house_details),
            )
            .where(
                or_(
                    Property.property_id == pid_clean,
                    Property.id == int(pid_clean) if is_numeric else False,
                ),
                Property.deleted_at.is_(None),
            )
        )
        res = await self.db.execute(stmt)
        prop = res.scalar_one_or_none()
        if not prop:
            return None

        bhk = None
        if prop.flat_details and prop.flat_details.bhk is not None:
            bhk = prop.flat_details.bhk
        elif prop.house_details and prop.house_details.bhk is not None:
            bhk = prop.house_details.bhk
        else:
            match = re.search(r"(\d+)\s*bhk", prop.title or "", re.IGNORECASE)
            if match:
                bhk = int(match.group(1))

        return {
            "property_id": prop.property_id,
            "title": prop.title,
            "city": prop.city,
            "locality": prop.locality,
            "expected_price": float(prop.expected_price) if prop.expected_price is not None else 0.0,
            "price_negotiable": bool(prop.price_negotiable),
            "category_code": prop.category_code,
            "sub_category_code": prop.sub_category_code,
            "listing_type": prop.listing_type,
            "bhk": bhk,
            "pincode": prop.pincode,
            "description": prop.description,
            "verified_status": prop.verified_status,
            "is_live": bool(prop.is_live),
        }

    async def answer_inquiry(
        self,
        customer_query: str,
        property_id: Optional[str] = None,
        session_context: Optional[Dict[str, Any]] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Answers customer questions and routes escalations.
        
        1. Checks feature flag ('customer_support').
        2. Evaluates deterministic escalation rules.
        3. Retrieves verified property context if property_id provided.
        4. Calls LLM with CUSTOMER_SUPPORT_SYSTEM_PROMPT and anti-hallucination constraints.
        5. Combines LLM & deterministic escalation flags.
        6. Logs execution audit record.
        """
        session_context = session_context or {}
        lead_id = session_context.get("lead_id")
        channel = session_context.get("channel", "SUPPORT")

        # 1. Feature Flag Verification
        mode = await self.guardrails.get_agent_mode(self.agent_name)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="CUSTOMER_INQUIRY",
                input_summary=customer_query[:500] if customer_query else None,
                output_response="Customer support agent is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message="Agent mode is configured to DISABLED",
            )
            return {
                "success": False,
                "response": "Customer support assistant is currently unavailable.",
                "escalate_to_human": False,
                "escalation_reason": None,
                "property_context": None,
                "error": "Customer support agent is disabled by configuration.",
            }

        # 2. Deterministic Escalation Safety Net
        det_escalate, det_reason = _detect_escalation_triggers(customer_query)

        # 3. Retrieve Property Context (Anti-hallucination ground truth)
        property_context = None
        if property_id:
            property_context = await self._fetch_property_context(property_id)

        try:
            # 4. Construct LLM Prompts
            user_prompt_sections = [
                f"Customer Query: {customer_query}",
                f"Target Language: {language}",
            ]

            if property_id:
                if property_context:
                    user_prompt_sections.append(
                        f"Verified Property Listing Ground Truth (Database Verified):\n{property_context}\n"
                        "CRITICAL ANTI-HALLUCINATION GUARD: Adhere strictly to the verified facts above. "
                        "Do NOT invent unverified prices, amenities, or ownership details."
                    )
                else:
                    user_prompt_sections.append(
                        f"Verified Property Listing Ground Truth: Property listing '{property_id}' was NOT FOUND "
                        "in our verified database.\n"
                        "CRITICAL ANTI-HALLUCINATION GUARD: Clearly inform the customer that listing "
                        f"'{property_id}' could not be verified or found in our active database."
                    )

            if session_context:
                clean_context = {k: v for k, v in session_context.items() if k not in ("lead_id", "channel")}
                if clean_context:
                    user_prompt_sections.append(f"Session Context: {clean_context}")

            user_prompt = "\n\n".join(user_prompt_sections)

            schema = {
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                    "escalate_to_human": {"type": "boolean"},
                    "escalation_reason": {"type": "string"},
                    "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                    "suggested_actions": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["response", "escalate_to_human"],
            }

            fallback = {
                "response": "Thank you for reaching out to Propira Omshiv Real Estate. Our team is reviewing your inquiry.",
                "escalate_to_human": det_escalate,
                "escalation_reason": det_reason,
                "urgency": "CRITICAL" if det_escalate else "LOW",
                "suggested_actions": ["Human agent follow-up required" if det_escalate else "Provide catalog details"],
            }

            parsed = await self.ai_client.chat_completion_json(
                system_prompt=CUSTOMER_SUPPORT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema=schema,
                fallback_data=fallback,
            )

            # 5. Combine LLM output with deterministic safety net
            llm_escalate = bool(parsed.get("escalate_to_human", False))
            llm_reason = parsed.get("escalation_reason")

            final_escalate = llm_escalate or det_escalate
            final_reason = llm_reason or det_reason
            if det_escalate and not final_reason:
                final_reason = det_reason

            response_text = parsed.get("response") or fallback["response"]
            urgency = parsed.get("urgency", "HIGH" if final_escalate else "LOW")
            suggested_actions = parsed.get("suggested_actions", [])

            # 6. Audit Execution Log
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="CUSTOMER_INQUIRY",
                input_summary=customer_query[:500] if customer_query else None,
                output_response=response_text[:1000] if response_text else None,
                status="SUCCESS",
            )

            return {
                "success": True,
                "response": response_text,
                "escalate_to_human": final_escalate,
                "escalation_reason": final_reason,
                "property_context": property_context,
                "urgency": urgency,
                "suggested_actions": suggested_actions,
            }

        except Exception as e:
            logger.exception("Error in CustomerSupportAgent.answer_inquiry: %s", e)
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel=channel,
                mode=mode,
                trigger_event="CUSTOMER_INQUIRY",
                input_summary=customer_query[:500] if customer_query else None,
                output_response="Internal support processing error occurred.",
                status="ERROR",
                error_message=str(e),
            )
            return {
                "success": False,
                "response": "We are currently experiencing a brief delay. A senior support representative has been alerted to assist you.",
                "escalate_to_human": True,
                "escalation_reason": "SYSTEM_ERROR",
                "property_context": property_context,
                "error": str(e),
            }
