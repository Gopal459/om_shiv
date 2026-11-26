from __future__ import annotations
import re
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_agents import CustomerConsent, AIAgentExecutionLog
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.llm_client import AIClientService
from app.services.ai.prompts import WHATSAPP_AGENT_SYSTEM_PROMPT
from app.services.ai.agents.property_search_agent import PropertySearchAgent
from app.services.notifications.whatsapp_gateway import WhatsAppGateway, whatsapp_gateway

logger = logging.getLogger(__name__)

OPT_OUT_KEYWORDS = {
    "STOP",
    "UNSUBSCRIBE",
    "OPT OUT",
    "OPTOUT",
    "BAND KARO",
    "ROKO",
    "HATAO",
    "CANCEL",
    "END",
    "QUIT",
    "DO NOT MESSAGE",
    "NO MORE MESSAGES",
}

RE_OPT_IN_KEYWORDS = {
    "START",
    "SUBSCRIBE",
    "YES",
    "HAAN",
    "SHURU KARO",
    "RESUME",
}


def _detect_opt_out(text: str) -> bool:
    """Detects whether text indicates an opt-out intent."""
    if not text:
        return False
    clean = text.strip().upper()
    if clean in OPT_OUT_KEYWORDS:
        return True
    if re.search(r"\b(stop|unsubscribe|opt\s*out|optout|band\s*karo|roko|hatao)\b", text, re.IGNORECASE):
        return True
    return False


class WhatsAppAgent:
    """Agent 7: AI WhatsApp Agent (Shadow Mode & Instant Opt-Out).
    
    Provides 24x7 intelligent WhatsApp assistance for Propira Omshiv Real Estate:
    - Instant opt-out detection ("STOP", "UNSUBSCRIBE", "BAND KARO") registering TRAI compliance.
    - Safety guardrails and operating mode enforcement (DISABLED, SHADOW, LIVE).
    - In SHADOW mode: generates responses and records audit logs without live dispatch.
    - In LIVE mode: checks rate limits and dispatches via DoubleTick WhatsApp Gateway.
    - Connects with PropertySearchAgent for conversational real estate queries.
    - Handles proactive outbound messaging with TRAI consent and rate limit verification.
    """

    def __init__(
        self,
        db: AsyncSession,
        ai_client: Optional[AIClientService] = None,
        guardrails: Optional[SafetyGuardrailsService] = None,
        tools: Optional[Any] = None,
        search_agent: Optional[PropertySearchAgent] = None,
        gateway: Optional[WhatsAppGateway] = None,
        whatsapp_gateway: Optional[WhatsAppGateway] = None,
    ):
        self.db = db
        self.ai_client = ai_client or AIClientService()
        self.guardrails = guardrails or SafetyGuardrailsService(db)
        self.tools = tools
        self.search_agent = search_agent or PropertySearchAgent(db, ai_client=self.ai_client, guardrails=self.guardrails)
        self.gateway = gateway or whatsapp_gateway or globals()["whatsapp_gateway"]
        self.agent_name = "whatsapp_agent"

    async def handle_incoming_message(
        self,
        mobile: str,
        text: str,
        lead_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Processes an incoming WhatsApp message.
        
        Args:
            mobile: Customer phone number.
            text: Inbound message content.
            lead_id: Optional CRM lead identifier.
            
        Returns:
            Dictionary with execution status, mode, live dispatch state, and reply text.
        """
        clean_mobile = str(mobile).strip()
        clean_text = (text or "").strip()

        # 1. Instant Opt-Out Detection
        if _detect_opt_out(clean_text):
            mode = await self.guardrails.get_agent_mode(self.agent_name)
            await self.guardrails.register_consent(
                mobile=clean_mobile,
                channel="WHATSAPP",
                is_opted_in=False,
                source="WHATSAPP_INCOMING",
                reason=clean_text,
            )
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="WHATSAPP",
                mode=mode,
                trigger_event="OPT_OUT",
                input_summary=clean_text,
                output_response="User opted out from WhatsApp messaging.",
                status="SUCCESS",
            )
            return {
                "status": "OPTED_OUT",
                "opt_out": True,
                "dispatched_live": False,
                "mode": mode,
                "reply_text": "You have been unsubscribed from WhatsApp notifications. Reply START to resubscribe.",
            }

        # 2. Feature Flag Check
        mode = await self.guardrails.get_agent_mode(self.agent_name)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="WHATSAPP",
                mode=mode,
                trigger_event="INCOMING_MESSAGE",
                input_summary=clean_text,
                output_response="WhatsApp agent is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message="whatsapp_agent is DISABLED",
            )
            return {
                "status": "BLOCKED_FLAG",
                "mode": "DISABLED",
                "dispatched_live": False,
                "reply_text": None,
                "error": "WhatsApp agent is disabled by configuration.",
            }

        # 3. Consent Management (Prevent silent re-opt-in for previously opted-out users)
        phone_variants = [clean_mobile]
        if len(clean_mobile) == 10:
            phone_variants.append(f"91{clean_mobile}")
        elif len(clean_mobile) == 12 and clean_mobile.startswith("91"):
            phone_variants.append(clean_mobile[2:])

        consent_stmt = (
            select(CustomerConsent)
            .where(
                CustomerConsent.mobile.in_(phone_variants),
                func.upper(CustomerConsent.channel) == "WHATSAPP",
            )
            .order_by(CustomerConsent.updated_at.desc(), CustomerConsent.id.desc())
            .limit(1)
        )
        c_res = await self.db.execute(consent_stmt)
        existing_consent = c_res.scalar_one_or_none()

        is_explicit_reopt = clean_text.upper() in RE_OPT_IN_KEYWORDS

        if existing_consent is not None:
            if existing_consent.is_opted_in is False:
                # User previously opted out: ONLY re-opt-in if they send explicit re-subscribe keyword
                if is_explicit_reopt:
                    await self.guardrails.register_consent(
                        mobile=clean_mobile,
                        channel="WHATSAPP",
                        is_opted_in=True,
                        source="WHATSAPP_INCOMING",
                        reason=clean_text,
                    )
            elif is_explicit_reopt:
                await self.guardrails.register_consent(
                    mobile=clean_mobile,
                    channel="WHATSAPP",
                    is_opted_in=True,
                    source="WHATSAPP_INCOMING",
                    reason=clean_text,
                )
        else:
            # First-time inbound inquiry: auto-register consent
            await self.guardrails.register_consent(
                mobile=clean_mobile,
                channel="WHATSAPP",
                is_opted_in=True,
                source="WHATSAPP_INCOMING",
            )

        # 4. Sliding-window Rate Limit Check in LIVE mode
        if mode == "LIVE":
            within_limit = await self.guardrails.check_rate_limit(
                clean_mobile,
                channel="WHATSAPP",
                max_per_hour=10,
            )
            if not within_limit:
                await self.guardrails.record_execution_log(
                    agent_name=self.agent_name,
                    lead_id=lead_id,
                    channel="WHATSAPP",
                    mode=mode,
                    trigger_event="INCOMING_MESSAGE",
                    input_summary=clean_text,
                    output_response="Rate limit exceeded.",
                    status="RATE_LIMITED",
                    error_message="Rate limit exceeded (max 10/hour)",
                )
                return {
                    "status": "RATE_LIMITED",
                    "mode": mode,
                    "dispatched_live": False,
                    "error": "Rate limit exceeded for this mobile number.",
                }

        # 5. Property Search & Catalog Context
        is_property_query = bool(
            re.search(
                r"\b(bhk|flat|apartment|villa|plot|house|budget|price|lakh|cr|crore|alwar|jaipur|neemrana|bhiwadi|buy|rent|sale|kothi|farmhouse|commercial|shop|office)\b",
                clean_text,
                re.IGNORECASE,
            )
        )
        recommended_properties: List[Dict[str, Any]] = []
        property_context = ""

        if is_property_query and self.search_agent:
            try:
                search_res = await self.search_agent.search_properties_conversational(
                    query=clean_text,
                    session_context={"lead_id": lead_id, "channel": "WHATSAPP"},
                )
                if search_res.get("success"):
                    recommended_properties = search_res.get("properties", [])
                    property_context = search_res.get("response_text", "")
            except Exception as exc:
                logger.warning("PropertySearchAgent execution notice: %s", exc)

        # 6. LLM Conversational Reply Generation
        user_prompt = f"Customer message from {clean_mobile}: '{clean_text}'"
        if property_context:
            user_prompt += f"\n\nProperty Catalog Results:\n{property_context}"

        fallback_reply = (
            property_context
            or "Namaste! Thank you for reaching out to Propira Omshiv Real Estate. How can we assist you with properties in Rajasthan & NCR today? 😊"
        )
        rec_catalog_ids = [
            str(p.get("property_id") or p.get("id"))
            for p in recommended_properties
            if isinstance(p, dict) and (p.get("property_id") or p.get("id"))
        ]

        parsed = await self.ai_client.chat_completion_json(
            system_prompt=WHATSAPP_AGENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            fallback_data={
                "reply_text": fallback_reply,
                "intent": "PROPERTY_SEARCH" if is_property_query else "GENERAL_FAQ",
                "opt_out_detected": False,
                "recommended_property_ids": rec_catalog_ids,
                "requires_agent_followup": False,
            },
        )

        # In case the LLM itself detected opt-out from colloquial phrasing
        if parsed.get("opt_out_detected") or parsed.get("intent") == "OPT_OUT":
            await self.guardrails.register_consent(
                mobile=clean_mobile,
                channel="WHATSAPP",
                is_opted_in=False,
                source="WHATSAPP_INCOMING",
                reason=clean_text,
            )
            return {
                "status": "OPTED_OUT",
                "opt_out": True,
                "dispatched_live": False,
                "mode": mode,
                "reply_text": "You have been unsubscribed from WhatsApp notifications. Reply START to resubscribe.",
            }

        reply_text = parsed.get("reply_text") or fallback_reply
        llm_rec_ids = [str(pid) for pid in (parsed.get("recommended_property_ids") or [])]
        recommended_property_ids = list(dict.fromkeys(llm_rec_ids + rec_catalog_ids))
        intent = parsed.get("intent", "GENERAL_FAQ")
        requires_agent_followup = bool(parsed.get("requires_agent_followup", False))

        # 7. Operating Mode Handling (SHADOW vs LIVE)
        if mode == "SHADOW":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="WHATSAPP",
                mode="SHADOW",
                trigger_event="INCOMING_MESSAGE",
                input_summary=clean_text,
                output_response=reply_text,
                tools_called=[{
                    "tool": "whatsapp_incoming_shadow",
                    "intent": intent,
                    "recommended_count": len(recommended_property_ids),
                }],
                status="SHADOW_LOGGED",
            )
            return {
                "status": "SUCCESS",
                "mode": "SHADOW",
                "dispatched_live": False,
                "reply_text": reply_text,
                "intent": intent,
                "recommended_property_ids": recommended_property_ids,
                "requires_agent_followup": requires_agent_followup,
            }

        # LIVE Mode: Dispatch via WhatsApp Gateway
        gateway_success = await self.gateway.send_message(mobile=clean_mobile, text=reply_text)
        await self.guardrails.record_execution_log(
            agent_name=self.agent_name,
            lead_id=lead_id,
            channel="WHATSAPP",
            mode="LIVE",
            trigger_event="INCOMING_MESSAGE",
            input_summary=clean_text,
            output_response=reply_text,
            tools_called=[{
                "tool": "whatsapp_send_message",
                "intent": intent,
                "gateway_success": gateway_success,
            }],
            status="SUCCESS" if gateway_success else "DELIVERY_FAILED",
        )

        return {
            "status": "SUCCESS" if gateway_success else "DELIVERY_FAILED",
            "mode": "LIVE",
            "dispatched_live": True,
            "reply_text": reply_text,
            "intent": intent,
            "recommended_property_ids": recommended_property_ids,
            "requires_agent_followup": requires_agent_followup,
        }

    async def dispatch_outbound_message(
        self,
        mobile: str,
        text: str,
        lead_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dispatches proactive outbound message with TRAI consent and rate limit verification.
        
        Args:
            mobile: Destination mobile number.
            text: Message text to send.
            lead_id: Optional CRM lead identifier.
            
        Returns:
            Dictionary with dispatch status, mode, and live dispatch state.
        """
        clean_mobile = str(mobile).strip()
        clean_text = (text or "").strip()

        # 1. Feature Flag Check
        mode = await self.guardrails.get_agent_mode(self.agent_name)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="WHATSAPP",
                mode=mode,
                trigger_event="OUTBOUND_DISPATCH",
                input_summary=clean_text,
                output_response="WhatsApp agent disabled.",
                status="BLOCKED_FLAG",
                error_message="whatsapp_agent is DISABLED",
            )
            return {
                "status": "BLOCKED_FLAG",
                "mode": "DISABLED",
                "dispatched_live": False,
                "error": "WhatsApp agent is disabled by configuration.",
            }

        # 2. TRAI Consent Check (Outbound marketing REQUIRES prior explicit opt-in)
        is_opted_in = await self.guardrails.verify_consent(clean_mobile, "WHATSAPP")
        if not is_opted_in:
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="WHATSAPP",
                mode=mode,
                trigger_event="OUTBOUND_DISPATCH",
                input_summary=clean_text,
                output_response="Blocked: Customer has not consented to WhatsApp communication.",
                status="BLOCKED_CONSENT",
                error_message="No explicit opt-in found for recipient",
            )
            return {
                "status": "BLOCKED_CONSENT",
                "dispatched_live": False,
                "error": "Customer has not consented to WhatsApp communication.",
            }

        # 3. Rate Limit Check
        within_limit = await self.guardrails.check_rate_limit(
            clean_mobile,
            channel="WHATSAPP",
            max_per_hour=10,
        )
        if not within_limit:
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="WHATSAPP",
                mode=mode,
                trigger_event="OUTBOUND_DISPATCH",
                input_summary=clean_text,
                output_response="Blocked: Rate limit reached.",
                status="RATE_LIMITED",
                error_message="Rate limit exceeded (max 10/hour)",
            )
            return {
                "status": "RATE_LIMITED",
                "dispatched_live": False,
                "error": "Rate limit exceeded for this mobile number.",
            }

        # 4. Mode Handling
        if mode == "SHADOW":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                lead_id=lead_id,
                channel="WHATSAPP",
                mode="SHADOW",
                trigger_event="OUTBOUND_DISPATCH",
                input_summary=clean_text,
                output_response=clean_text,
                status="SHADOW_LOGGED",
            )
            return {
                "status": "SUCCESS",
                "mode": "SHADOW",
                "dispatched_live": False,
                "text": clean_text,
            }

        # LIVE Mode
        gateway_success = await self.gateway.send_message(mobile=clean_mobile, text=clean_text)
        await self.guardrails.record_execution_log(
            agent_name=self.agent_name,
            lead_id=lead_id,
            channel="WHATSAPP",
            mode="LIVE",
            trigger_event="OUTBOUND_DISPATCH",
            input_summary=clean_text,
            output_response=clean_text,
            status="SUCCESS" if gateway_success else "DELIVERY_FAILED",
        )
        return {
            "status": "SUCCESS" if gateway_success else "DELIVERY_FAILED",
            "mode": "LIVE",
            "dispatched_live": True,
            "text": clean_text,
        }
