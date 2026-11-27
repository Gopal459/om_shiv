"""SQLAlchemy models for 4-Tier Channel Partners, Franchise Outlets, Payouts, and Mediated Meetings."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

CP_TYPES = {"BROKER_CP", "ACTIVE_CP", "REFERRAL_PARTNER", "CREATOR_PARTNER"}
ACTIVE_LEVELS = {"L1", "L2", "L3"}
PAYOUT_TYPES = {
    "CO_BROKING",
    "COMMISSION",
    "REFERRAL_FIXED",
    "CREATOR_COMMISSION",
    "CREATOR_RETAINER",
}


def current_fiscal_year(dt: Optional[datetime] = None) -> str:
    """Return Indian Financial Year string like '2026-27' (Apr-Mar)."""
    now = dt or datetime.now(timezone.utc)
    start_year = now.year if now.month >= 4 else now.year - 1
    end_short = (start_year + 1) % 100
    return f"{start_year}-{end_short:02d}"


class FranchiseOutlet(Base):
    """Physical franchise branch or regional office."""

    __tablename__ = "franchise_outlets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    outlet_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(100), default="Jaipur", nullable=False)
    locality: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manager_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    manager_mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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

    partners: Mapped[list["ChannelPartner"]] = relationship(
        "ChannelPartner",
        back_populates="outlet",
        lazy="selectin",
    )


class ChannelPartner(Base):
    """4-Tier Channel Partner entity (Broker CP, Active CP, Referral Partner, Creator Partner)."""

    __tablename__ = "channel_partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    cp_type: Mapped[str] = mapped_column(
        String(32), default="BROKER_CP", index=True, nullable=False
    )  # BROKER_CP, ACTIVE_CP, REFERRAL_PARTNER, CREATOR_PARTNER

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(180), nullable=True)
    mobile: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), default="Jaipur", nullable=False)
    rera_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    outlet_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("franchise_outlets.id", ondelete="SET NULL"),
        nullable=True,
    )
    commission_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=2.0, nullable=False)

    # 1. Broker CP fields
    has_office_setup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    office_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    co_broking_split_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=50.0, nullable=False)

    # 2. Active CP Ladder & Instant Kill-Switch fields
    active_level: Mapped[str] = mapped_column(String(16), default="L1", nullable=False)  # L1, L2, L3
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_certified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    certified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    recommended_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    recommended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    l3_approved_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    l3_approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    clean_record: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    violation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    suspension_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 3. Referral Partner fields
    fixed_reward_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=5000.0, nullable=False)
    annual_reward_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # 4. Creator Partner fields
    tracking_code: Mapped[Optional[str]] = mapped_column(String(40), unique=True, index=True, nullable=True)
    social_handle: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    is_top_creator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    monthly_retainer_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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

    outlet: Mapped[Optional["FranchiseOutlet"]] = relationship(
        "FranchiseOutlet",
        back_populates="partners",
        lazy="selectin",
    )
    payouts: Mapped[list["PartnerPayout"]] = relationship(
        "PartnerPayout",
        back_populates="partner",
        lazy="selectin",
    )
    meetings: Mapped[list["CPMediatedMeeting"]] = relationship(
        "CPMediatedMeeting",
        back_populates="partner",
        lazy="selectin",
    )


class PartnerPayout(Base):
    """Commission, fixed referral reward, and creator retainer payouts."""

    __tablename__ = "partner_payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payout_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    partner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("channel_partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payout_type: Mapped[str] = mapped_column(
        String(32), default="COMMISSION", nullable=False, index=True
    )  # CO_BROKING, COMMISSION, REFERRAL_FIXED, CREATOR_COMMISSION, CREATOR_RETAINER
    fiscal_year: Mapped[str] = mapped_column(
        String(16), default=current_fiscal_year, nullable=False, index=True
    )
    lead_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    property_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deal_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0.0, nullable=False)
    commission_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False, index=True
    )  # PENDING, APPROVED, SETTLED
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    partner: Mapped["ChannelPartner"] = relationship(
        "ChannelPartner",
        back_populates="payouts",
        lazy="selectin",
    )


class CPMediatedMeeting(Base):
    """Omshiv-mediated owner-buyer meetings for L3 Active CPs."""

    __tablename__ = "cp_mediated_meetings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    partner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("channel_partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[str] = mapped_column(String(32), nullable=False)
    lead_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    requested_slot: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supervisor_emp_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="REQUESTED", nullable=False, index=True
    )  # REQUESTED, APPROVED, COMPLETED, REJECTED
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    partner: Mapped["ChannelPartner"] = relationship(
        "ChannelPartner",
        back_populates="meetings",
        lazy="selectin",
    )

