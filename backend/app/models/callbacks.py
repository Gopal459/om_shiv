from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

CALLBACK_STATUSES: Dict[int, str] = {
    0: "New",
    1: "In Progress",
    2: "Disqualified",
    3: "Solved",
    4: "Qualified",
    5: "Converted to Lead",
    6: "Converted Property",
}

DISQUALIFIED_REASONS: Dict[int, str] = {
    1: "Inaccurate Data",
    2: "Not Interested",
    3: "Not Response",
    4: "Call Me Later",
    5: "Disconnecting Call",
    6: "Rejected",
    7: "Other",
}

CURRENT_UPDATE_OPTIONS: List[str] = [
    "Interested",
    "Call Back Later",
    "Site Visit Planned",
    "Price Discussion",
    "Shared Details on WhatsApp",
    "Ringing / Follow-Up",
]

PROBLEM_STATUSES: Tuple[str, ...] = (
    "NEW",
    "IN_REVIEW",
    "RESOLVED",
    "REJECTED",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TblCallback(Base):
    """Inbound Request A Callback CRM entity mapped to tbl_callback."""

    __tablename__ = "tbl_callback"

    callback_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_unique_id: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile_number: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    phone_code: Mapped[str] = mapped_column(String(16), default="+91", nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    property_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    property_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    assigned_user_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lead_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    calls_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lead_open: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    disqualified_reason: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_update: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    last_remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    followup_datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    opportunity_converted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lead_converted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    converted_lead_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    website_inquiry_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("website_inquiries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False, index=True
    )
    modified_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    reschedule_logs: Mapped[List["CallbackRescheduleLog"]] = relationship(
        "CallbackRescheduleLog",
        back_populates="callback",
        cascade="all, delete-orphan",
    )
    activities: Mapped[List["CallbackActivity"]] = relationship(
        "CallbackActivity",
        back_populates="callback",
        cascade="all, delete-orphan",
    )


class CallbackRescheduleLog(Base):
    """Audit trail of callback follow-up schedule changes."""

    __tablename__ = "tbl_leadreschedule_followup"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    callback_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tbl_callback.callback_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_followup_datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_followup_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    current_update: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    remark: Mapped[str] = mapped_column(Text, nullable=False)
    rescheduled_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )

    callback: Mapped["TblCallback"] = relationship(
        "TblCallback", back_populates="reschedule_logs"
    )


class CallbackActivity(Base):
    """Lifecycle activity timeline events for a callback record."""

    __tablename__ = "tbl_callback_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    callback_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tbl_callback.callback_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    status_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status_after: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    performed_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )

    callback: Mapped["TblCallback"] = relationship(
        "TblCallback", back_populates="activities"
    )
