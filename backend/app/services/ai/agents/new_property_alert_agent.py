from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.properties import Property
from app.models.leads import Lead
from app.models.ai_agents import PropertyAlertHistory
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.agents.whatsapp_agent import WhatsAppAgent
from app.services.notifications.whatsapp_gateway import WhatsAppGateway, whatsapp_gateway

logger = logging.getLogger(__name__)


class NewPropertyAlertAgent:
    """Agent 12: AI New Property Alert Agent (Anti-Spam & Deduplication).

    Automates targeted proactive alerts to prospective buyers/tenants when new properties
    are listed and verified live, applying strict anti-spam governance:
    1. Feature flag control (DISABLED, SHADOW, LIVE).
    2. Active lead matching by location and budget criteria.
    3. 7-day cooldown deduplication via PropertyAlertHistory.
    4. Prior explicit opt-in customer consent verification (TRAI/DND).
    5. Sliding-window hourly rate limit enforcement.
    6. Shadow mode logging vs live outbound dispatch.
    """

    def __init__(
        self,
        db: AsyncSession,
        guardrails: Optional[SafetyGuardrailsService] = None,
        whatsapp_agent: Optional[WhatsAppAgent] = None,
        gateway: Optional[WhatsAppGateway] = None,
    ):
        self.db = db
        self.guardrails = guardrails or SafetyGuardrailsService(db)
        self.whatsapp_agent = whatsapp_agent
        self.gateway = (
            gateway
            or (whatsapp_agent.gateway if whatsapp_agent and hasattr(whatsapp_agent, "gateway") else None)
            or whatsapp_gateway
        )
        self.agent_name = "new_property_alert_agent"

    async def dispatch_alerts_for_property(
        self,
        property_id: str,
        channel: str = "WHATSAPP",
    ) -> Dict[str, Any]:
        """Dispatches proactive alerts to matching leads for a newly listed property.

        Args:
            property_id: Unique property listing identifier (e.g., OP-2026-00005).
            channel: Communication channel, defaults to WHATSAPP.

        Returns:
            Dictionary containing execution status, counts of eligible, dispatched,
            suppressed (duplicate, no-consent, rate-limit), and shadow alerts.
        """
        norm_channel = (channel or "WHATSAPP").upper()

        # 1. Feature Flag Check
        mode = await self.guardrails.get_agent_mode(self.agent_name)
        if mode == "DISABLED":
            await self.guardrails.record_execution_log(
                agent_name=self.agent_name,
                channel=norm_channel,
                mode=mode,
                trigger_event="NEW_PROPERTY_ALERT",
                input_summary=f"Alert dispatch requested for property {property_id}",
                output_response="Agent is disabled by configuration.",
                status="BLOCKED_FLAG",
                error_message="new_property_alert_agent is DISABLED",
            )
            return {
                "success": False,
                "status": "BLOCKED_FLAG",
                "mode": "DISABLED",
                "property_id": property_id,
                "eligible_leads_count": 0,
                "dispatched_count": 0,
                "suppressed_duplicate_count": 0,
                "suppressed_no_consent_count": 0,
                "suppressed_rate_limit_count": 0,
                "shadow_count": 0,
                "error": "new_property_alert_agent is DISABLED",
            }

        # 2. Query Property Listing
        prop_stmt = select(Property).where(
            Property.property_id == property_id,
            Property.deleted_at.is_(None),
        )
        prop_res = await self.db.execute(prop_stmt)
        prop = prop_res.scalar_one_or_none()

        if not prop:
            return {
                "success": False,
                "error": f"Property '{property_id}' not found.",
                "property_id": property_id,
                "eligible_leads_count": 0,
                "dispatched_count": 0,
                "suppressed_duplicate_count": 0,
                "suppressed_no_consent_count": 0,
                "suppressed_rate_limit_count": 0,
                "shadow_count": 0,
            }

        if not prop.is_live:
            return {
                "success": False,
                "error": f"Property '{property_id}' is not live.",
                "property_id": property_id,
                "eligible_leads_count": 0,
                "dispatched_count": 0,
                "suppressed_duplicate_count": 0,
                "suppressed_no_consent_count": 0,
                "suppressed_rate_limit_count": 0,
                "shadow_count": 0,
            }

        # 3. Match Active Leads (city, budget_max >= expected_price, not deleted)
        leads_stmt = select(Lead).where(
            Lead.deleted_at.is_(None),
            (Lead.stage != "LOST") | (Lead.stage.is_(None)),
            func.lower(func.trim(Lead.preferred_city)) == func.lower(func.trim(prop.city)),
            Lead.budget_max >= prop.expected_price,
        )
        leads_res = await self.db.execute(leads_stmt)
        matching_leads = leads_res.scalars().all()
        eligible_leads_count = len(matching_leads)

        dispatched_count = 0
        suppressed_duplicate_count = 0
        suppressed_no_consent_count = 0
        suppressed_rate_limit_count = 0
        shadow_count = 0

        # Format price for alert notification
        price_num = float(prop.expected_price or 0)
        if price_num >= 10000000:
            formatted_price = f"₹{price_num / 10000000:.2f} Cr"
        elif price_num >= 100000:
            formatted_price = f"₹{price_num / 100000:.2f} Lakhs"
        else:
            formatted_price = f"₹{price_num:,.0f}"

        locality = prop.locality or prop.city

        # 4. Anti-Spam Pipeline per matching lead
        for lead in matching_leads:
            # (a) 7-day cooldown duplicate alert check
            is_dup = await self.guardrails.is_duplicate_property_alert(
                lead.lead_id,
                prop.property_id,
                cooldown_days=7,
            )
            if is_dup:
                suppressed_duplicate_count += 1
                continue

            # (b) Consent verification
            has_consent = await self.guardrails.verify_consent(lead.mobile, norm_channel)
            if not has_consent:
                suppressed_no_consent_count += 1
                await self.guardrails.record_execution_log(
                    agent_name=self.agent_name,
                    lead_id=lead.lead_id,
                    channel=norm_channel,
                    mode=mode,
                    trigger_event="NEW_PROPERTY_ALERT",
                    input_summary=f"Alert candidate {prop.property_id} ({prop.title}) for lead {lead.lead_id}",
                    output_response="Blocked: Customer has not consented to communication",
                    status="BLOCKED_CONSENT",
                    error_message=f"No consent for {lead.mobile} on {norm_channel}",
                )
                continue

            # (c) Rate limiting check
            within_limit = await self.guardrails.check_rate_limit(lead.mobile, norm_channel)
            if not within_limit:
                suppressed_rate_limit_count += 1
                await self.guardrails.record_execution_log(
                    agent_name=self.agent_name,
                    lead_id=lead.lead_id,
                    channel=norm_channel,
                    mode=mode,
                    trigger_event="NEW_PROPERTY_ALERT",
                    input_summary=f"Alert candidate {prop.property_id} ({prop.title}) for lead {lead.lead_id}",
                    output_response="Blocked: Rate limit reached",
                    status="BLOCKED_RATE_LIMIT",
                    error_message=f"Rate limit exceeded for {lead.mobile}",
                )
                continue

            # Construct alert notification message
            message_text = (
                f"Namaste {lead.full_name}! 🏠 A new property matching your preferences is now available in {prop.city}:\n\n"
                f"*{prop.title}*\n"
                f"Price: {formatted_price}\n"
                f"Location: {locality}\n"
                f"Listing ID: {prop.property_id}\n\n"
                f"Reply YES or call us to schedule a site visit! Reply STOP to opt out."
            )

            # (d) Mode Handling (SHADOW vs LIVE)
            if mode == "SHADOW":
                alert = PropertyAlertHistory(
                    lead_id=lead.lead_id,
                    property_id=prop.property_id,
                    channel=norm_channel,
                    status="SHADOW",
                    sent_at=datetime.now(timezone.utc),
                )
                self.db.add(alert)
                await self.db.commit()

                await self.guardrails.record_execution_log(
                    agent_name=self.agent_name,
                    lead_id=lead.lead_id,
                    channel=norm_channel,
                    mode="SHADOW",
                    trigger_event="NEW_PROPERTY_ALERT",
                    input_summary=f"Property alert candidate {prop.property_id} ({prop.title}) for lead {lead.lead_id}",
                    output_response=message_text,
                    tools_called=[{
                        "tool": "property_alert_shadow",
                        "property_id": prop.property_id,
                        "lead_id": lead.lead_id,
                    }],
                    status="SHADOW_LOGGED",
                )
                shadow_count += 1
            else:
                # LIVE Mode
                sent_successfully = False
                if self.whatsapp_agent:
                    try:
                        res = await self.whatsapp_agent.dispatch_outbound_message(
                            mobile=lead.mobile,
                            text=message_text,
                            lead_id=lead.lead_id,
                        )
                        if res.get("dispatched_live") is True or res.get("status") == "SUCCESS":
                            sent_successfully = True
                        elif hasattr(self.gateway, "send_message"):
                            sent_successfully = await self.gateway.send_message(
                                mobile=lead.mobile,
                                text=message_text,
                            )
                    except Exception as exc:
                        logger.warning("whatsapp_agent dispatch exception: %s", exc)
                        if hasattr(self.gateway, "send_message"):
                            sent_successfully = await self.gateway.send_message(
                                mobile=lead.mobile,
                                text=message_text,
                            )
                else:
                    sent_successfully = await self.gateway.send_message(
                        mobile=lead.mobile,
                        text=message_text,
                    )

                alert = PropertyAlertHistory(
                    lead_id=lead.lead_id,
                    property_id=prop.property_id,
                    channel=norm_channel,
                    status="SENT" if sent_successfully else "FAILED",
                    sent_at=datetime.now(timezone.utc),
                )
                self.db.add(alert)
                await self.db.commit()

                await self.guardrails.record_execution_log(
                    agent_name=self.agent_name,
                    lead_id=lead.lead_id,
                    channel=norm_channel,
                    mode="LIVE",
                    trigger_event="NEW_PROPERTY_ALERT",
                    input_summary=f"Property alert for {prop.property_id} ({prop.title}) dispatched to lead {lead.lead_id}",
                    output_response=message_text,
                    tools_called=[{
                        "tool": "property_alert_live_dispatch",
                        "property_id": prop.property_id,
                        "lead_id": lead.lead_id,
                        "channel": norm_channel,
                        "dispatched": sent_successfully,
                    }],
                    status="SUCCESS" if sent_successfully else "DELIVERY_FAILED",
                )
                if sent_successfully:
                    dispatched_count += 1

        return {
            "success": True,
            "property_id": property_id,
            "eligible_leads_count": eligible_leads_count,
            "dispatched_count": dispatched_count,
            "suppressed_duplicate_count": suppressed_duplicate_count,
            "suppressed_no_consent_count": suppressed_no_consent_count,
            "suppressed_rate_limit_count": suppressed_rate_limit_count,
            "shadow_count": shadow_count,
        }
