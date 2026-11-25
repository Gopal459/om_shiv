from __future__ import annotations
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_agents import (
    AIAgentConfig,
    CustomerConsent,
    AIAgentExecutionLog,
    PropertyAlertHistory,
)
from app.models.leads import Lead


def _normalize_phone(phone: Optional[str]) -> str:
    """Normalize phone number to standard Indian 12-digit format: 91XXXXXXXXXX."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    if len(digits) > 10 and digits.startswith("91"):
        return digits[:12]
    return digits


def _get_phone_variants(phone: str) -> list[str]:
    """Generate symmetric phone variants (10-digit, 12-digit, raw) for resilient lookups."""
    if not phone:
        return []
    raw = str(phone).strip()
    norm = _normalize_phone(raw)
    variants = {raw, norm}
    if len(norm) == 12 and norm.startswith("91"):
        variants.add(norm[2:])
    elif len(norm) == 10:
        variants.add(f"91{norm}")
    return list(variants - {""})


class SafetyGuardrailsService:
    """
    Core safety and governance engine for Omshiv AI agents.
    Provides feature flags/shadow mode, TRAI consent verification,
    sliding-window rate limiting, duplicate alert suppression, and PII masking.
    """

    VALID_MODES = {"DISABLED", "SHADOW", "LIVE"}

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    def mask_pii(self, text_or_mobile: Optional[str]) -> str:
        """
        Masks Personally Identifiable Information (PII) including phone numbers and emails.
        E.g. 919829012345 -> 9198****2345
             9829012345   -> 98****2345
             user@domain  -> u***@domain
        """
        if text_or_mobile is None:
            return ""
        text = str(text_or_mobile)

        # 1. Mask 12-digit Indian numbers (with optional +): +919829012345 or 919829012345 -> 9198****2345
        text = re.sub(r"(?:\+)?(91\d{2})\d{4}(\d{4})\b", r"\1****\2", text)

        # 2. Mask 10-digit Indian numbers: 9829012345 -> 98****2345
        text = re.sub(r"\b([6-9]\d{1})\d{4}(\d{4})\b", r"\1****\2", text)

        # 3. Mask email addresses: user@domain.com -> u***@domain.com
        text = re.sub(
            r"\b([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b",
            r"\1***@\2",
            text,
        )

        return text

    async def get_agent_mode(self, agent_name: str) -> str:
        """
        Checks operational mode for an agent (DISABLED, SHADOW, LIVE).
        Defaults to 'SHADOW' if not found or if the flag table is unseeded.
        """
        if self.db is None:
            return "SHADOW"

        stmt = select(AIAgentConfig).where(AIAgentConfig.agent_name == agent_name)
        res = await self.db.execute(stmt)
        config = res.scalar_one_or_none()
        if not config or not config.mode:
            return "SHADOW"
        return config.mode.upper()

    async def set_agent_mode(self, agent_name: str, mode: str) -> AIAgentConfig:
        """
        Updates or seeds an agent's operating mode flag.
        Valid modes: DISABLED, SHADOW, LIVE.
        """
        if self.db is None:
            raise ValueError("Database session required to set agent mode")

        valid_mode = mode.upper()
        if valid_mode not in self.VALID_MODES:
            raise ValueError(
                f"Invalid mode '{mode}'. Allowed modes are: {', '.join(sorted(self.VALID_MODES))}"
            )

        stmt = select(AIAgentConfig).where(AIAgentConfig.agent_name == agent_name)
        res = await self.db.execute(stmt)
        config = res.scalar_one_or_none()

        if config:
            config.mode = valid_mode
            config.updated_at = datetime.now(timezone.utc)
        else:
            config = AIAgentConfig(
                agent_name=agent_name,
                display_name=agent_name.replace("_", " ").title(),
                mode=valid_mode,
            )
            self.db.add(config)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def verify_consent(self, mobile: str, channel: str = "WHATSAPP") -> bool:
        """
        Verifies customer consent for automated communication.
        Requires is_opted_in=True; defaults to False for proactive marketing.
        """
        if self.db is None:
            return False

        phone_variants = _get_phone_variants(mobile)
        norm_channel = channel.upper()

        stmt = (
            select(CustomerConsent)
            .where(
                CustomerConsent.mobile.in_(phone_variants),
                func.upper(CustomerConsent.channel) == norm_channel,
            )
            .order_by(CustomerConsent.updated_at.desc(), CustomerConsent.id.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            return False

        return bool(record.is_opted_in)

    async def register_consent(
        self,
        mobile: str,
        channel: str,
        is_opted_in: bool,
        source: str = "MANUAL",
        reason: Optional[str] = None,
    ) -> CustomerConsent:
        """
        Records or updates customer communication consent.
        Always stores canonical normalized mobile for consistent lookup.
        """
        if self.db is None:
            raise ValueError("Database session required to register consent")

        phone_variants = _get_phone_variants(mobile)
        norm_mobile = _normalize_phone(mobile)
        canonical_mobile = norm_mobile or str(mobile).strip()
        norm_channel = channel.upper()

        stmt = (
            select(CustomerConsent)
            .where(
                CustomerConsent.mobile.in_(phone_variants),
                func.upper(CustomerConsent.channel) == norm_channel,
            )
            .order_by(CustomerConsent.updated_at.desc(), CustomerConsent.id.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        consent = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if consent:
            consent.mobile = canonical_mobile
            consent.is_opted_in = is_opted_in
            consent.consent_source = source
            if is_opted_in:
                consent.opted_in_at = now
                consent.opt_out_reason = None
            else:
                consent.opted_out_at = now
                consent.opt_out_reason = reason
            consent.updated_at = now
        else:
            consent = CustomerConsent(
                mobile=canonical_mobile,
                channel=norm_channel,
                is_opted_in=is_opted_in,
                consent_source=source,
                opted_in_at=now if is_opted_in else None,
                opted_out_at=now if not is_opted_in else None,
                opt_out_reason=reason if not is_opted_in else None,
                created_at=now,
                updated_at=now,
            )
            self.db.add(consent)

        await self.db.commit()
        await self.db.refresh(consent)
        return consent

    async def check_rate_limit(
        self,
        mobile: str,
        channel: str = "WHATSAPP",
        max_per_hour: int = 10,
    ) -> bool:
        """
        Sliding-window rate limiter counting dispatches to a mobile in the last 1 hour.
        Combines execution log dispatches and property alert notifications.
        Returns True if within rate limit (allowed), False if limit reached (blocked).
        """
        if self.db is None:
            return True

        phone_variants = _get_phone_variants(mobile)
        norm_channel = channel.upper()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

        # Check corresponding lead_ids if any
        target_ids = list(phone_variants)
        lead_stmt = select(Lead.lead_id).where(Lead.mobile.in_(phone_variants))
        lead_res = await self.db.execute(lead_stmt)
        for lid in lead_res.scalars().all():
            if lid:
                target_ids.append(lid)

        # Count successful / active dispatches in AIAgentExecutionLog
        exec_stmt = select(func.count(AIAgentExecutionLog.id)).where(
            AIAgentExecutionLog.lead_id.in_(target_ids),
            func.upper(AIAgentExecutionLog.channel) == norm_channel,
            AIAgentExecutionLog.created_at >= cutoff,
            AIAgentExecutionLog.status.in_(["SUCCESS", "SHADOW_LOGGED", "SENT"]),
        )
        exec_count = (await self.db.execute(exec_stmt)).scalar() or 0

        # Also count dispatches in PropertyAlertHistory
        alert_stmt = select(func.count(PropertyAlertHistory.id)).where(
            PropertyAlertHistory.lead_id.in_(target_ids),
            func.upper(PropertyAlertHistory.channel) == norm_channel,
            PropertyAlertHistory.sent_at >= cutoff,
            PropertyAlertHistory.status.in_(["SENT", "DELIVERED"]),
        )
        alert_count = (await self.db.execute(alert_stmt)).scalar() or 0

        total_dispatches = exec_count + alert_count
        return total_dispatches < max_per_hour

    async def is_duplicate_property_alert(
        self,
        lead_id: str,
        property_id: str,
        cooldown_days: int = 7,
    ) -> bool:
        """
        Anti-spam deduplication: checks if this property was recommended to the lead within cooldown_days.
        Returns True if duplicate (suppress), False if allowed.
        """
        if self.db is None:
            return False

        cutoff = datetime.now(timezone.utc) - timedelta(days=cooldown_days)
        stmt = (
            select(PropertyAlertHistory)
            .where(
                PropertyAlertHistory.lead_id == lead_id,
                PropertyAlertHistory.property_id == property_id,
                PropertyAlertHistory.sent_at >= cutoff,
                PropertyAlertHistory.status.in_(["SENT", "DELIVERED"]),
            )
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def record_execution_log(
        self,
        agent_name: str,
        lead_id: Optional[str] = None,
        channel: Optional[str] = None,
        mode: str = "SHADOW",
        trigger_event: Optional[str] = None,
        input_summary: Optional[str] = None,
        output_response: Optional[str] = None,
        tools_called: Optional[Any] = None,
        status: str = "SUCCESS",
        approval_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> AIAgentExecutionLog:
        """
        Audit log tracking for every agent decision, tool invocation, and shadow execution.
        Automatically applies PII masking to input, output text, and error messages.
        """
        if self.db is None:
            raise ValueError("Database session required to record execution log")

        masked_input = self.mask_pii(input_summary) if input_summary else None
        masked_output = self.mask_pii(output_response) if output_response else None
        masked_error = self.mask_pii(error_message) if error_message else None

        log = AIAgentExecutionLog(
            agent_name=agent_name,
            lead_id=lead_id,
            channel=channel.upper() if channel else None,
            mode=mode.upper(),
            trigger_event=trigger_event,
            input_summary=masked_input,
            output_response=masked_output,
            tools_called=tools_called,
            status=status.upper(),
            approval_id=approval_id,
            error_message=masked_error,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log
