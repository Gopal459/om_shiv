from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

OPPORTUNITY_STATUSES: Dict[int, str] = {
    1: "In Progress",
    2: "Disqualified",
    4: "Qualified (Deal Scheduled)",
    5: "Closed",
}

DISQUALIFIED_REASONS: Dict[int, str] = {
    1: "Inaccurate Data",
    2: "Not Interested",
    3: "Not Responding",
    4: "Disconnecting Call",
    5: "Rejected",
    6: "Other",
    7: "Not Available Property",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OpportunitySequence(Base):
    """Annual atomic counter for unbounded 6-digit Opportunity codes (OPP-YYYY-NNNNNN)."""

    __tablename__ = "opportunity_sequences"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class TblOpportunity(Base):
    """Core Opportunity CRM entity mapped to tbl_opportunities."""

    __tablename__ = "tbl_opportunities"

    opportunity_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    opportunity_code: Mapped[Optional[str]] = mapped_column(
        String(32), unique=True, index=True, nullable=True
    )
    source_lead_id: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, index=True
    )

    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    alternate_mobile: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_type: Mapped[str] = mapped_column(
        String(32), default="END_USER", nullable=False
    )

    property_type: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    looking_type: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    looking_subcat_type: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    budget_from: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=0, nullable=False
    )
    budget_to: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=0, nullable=False
    )
    area_from: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    area_to: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    area_unit: Mapped[str] = mapped_column(String(32), default="Sq.Ft", nullable=False)
    bhk: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    furnishing: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    property_age: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    loanable: Mapped[str] = mapped_column(String(16), default="MAYBE", nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    assign_franch_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assign_franchstaff_id: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    lead_status: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, index=True
    )
    lead_open: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, index=True
    )
    calls_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    disqualified_reason: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_update: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    last_remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    followup_datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    deal_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registry_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_propira_property: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    matched_property_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    matched_property_code: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    deal_property_category: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    deal_property_subcategory: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    deal_property_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deal_location_lat: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    deal_location_long: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    locations: Mapped[List["OpportunityLocation"]] = relationship(
        "OpportunityLocation",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )
    reschedules: Mapped[List["OpportunityRescheduleLog"]] = relationship(
        "OpportunityRescheduleLog",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )
    activities: Mapped[List["OpportunityActivity"]] = relationship(
        "OpportunityActivity",
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )


class OpportunityLocation(Base):
    """Preferred localities and geo-radius filters for an opportunity."""

    __tablename__ = "tbl_opportunity_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tbl_opportunities.opportunity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    locality_name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    radius_km: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    opportunity: Mapped["TblOpportunity"] = relationship(
        "TblOpportunity", back_populates="locations"
    )


class OpportunityRescheduleLog(Base):
    """Audit trail of opportunity follow-up schedule changes."""

    __tablename__ = "tbl_opportunity_reschedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tbl_opportunities.opportunity_id", ondelete="CASCADE"),
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

    opportunity: Mapped["TblOpportunity"] = relationship(
        "TblOpportunity", back_populates="reschedules"
    )


class OpportunityActivity(Base):
    """Lifecycle activity timeline events for an opportunity record."""

    __tablename__ = "tbl_opportunity_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tbl_opportunities.opportunity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status_after: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    performed_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )

    opportunity: Mapped["TblOpportunity"] = relationship(
        "TblOpportunity", back_populates="activities"
    )
