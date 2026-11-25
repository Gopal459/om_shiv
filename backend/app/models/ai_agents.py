from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    JSON,
    Text,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class AIAgentConfig(Base):
    """Configuration and operating mode flags for AI Agents in Omshiv CRM."""
    __tablename__ = "ai_agent_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="SHADOW", nullable=False)  # DISABLED, SHADOW, LIVE
    rate_limit_per_hour: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    requires_hitl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_customer_facing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, default=dict, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @classmethod
    def select(cls):
        return select(cls)


class CustomerConsent(Base):
    """Permanent customer consent registry for TRAI/DND and multi-channel communication."""
    __tablename__ = "customer_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mobile: Mapped[str] = mapped_column(String(15), index=True, nullable=False)  # Normalized E.164 or 10/12-digit
    channel: Mapped[str] = mapped_column(String(32), default="WHATSAPP", nullable=False)  # WHATSAPP, VOICE, SMS
    is_opted_in: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    consent_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # META_FORM, INCOMING_SMS, MANUAL
    opted_in_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
    opted_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opt_out_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @classmethod
    def select(cls):
        return select(cls)


class AIApprovalQueue(Base):
    """Human-in-the-loop (HITL) approval queue for sensitive agent actions."""
    __tablename__ = "ai_approval_queue"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    agent_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    lead_id: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g., STAGE_CHANGE_LOST
    proposed_payload: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)  # PENDING, APPROVED, REJECTED
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # employee_id
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @classmethod
    def select(cls):
        return select(cls)


class AIAgentExecutionLog(Base):
    """Audit log tracking every AI agent trigger, decision, shadow execution, and tool call."""
    __tablename__ = "ai_agent_execution_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    lead_id: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    channel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # WHATSAPP, VOICE, WEB, INTERNAL
    mode: Mapped[str] = mapped_column(String(32), default="SHADOW", nullable=False)  # DISABLED, SHADOW, LIVE
    trigger_event: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tools_called: Mapped[Optional[Any]] = mapped_column(JSON_TYPE, default=list, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
    )  # SUCCESS, SHADOW_LOGGED, BLOCKED_CONSENT, BLOCKED_RATE_LIMIT, BLOCKED_FLAG, PENDING_APPROVAL, ERROR
    approval_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    @classmethod
    def select(cls):
        return select(cls)


class PropertyAlertHistory(Base):
    """History of property recommendations dispatched to leads to prevent spamming."""
    __tablename__ = "property_alert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    property_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(32), default="WHATSAPP", nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), default="SENT", nullable=False)  # SENT, DELIVERED, FAILED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @classmethod
    def select(cls):
        return select(cls)
