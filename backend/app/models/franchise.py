"""SQLAlchemy models for Franchise Outlets, Channel Partners, and Partner Payouts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


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
    """Authorized real estate channel partner / broker linked to the franchise network."""

    __tablename__ = "channel_partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
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


class PartnerPayout(Base):
    """Commission payout tracking for channel partners."""

    __tablename__ = "partner_payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payout_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    partner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("channel_partners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    property_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deal_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0.0, nullable=False)
    commission_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)  # PENDING, APPROVED, SETTLED
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
