from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid

from sqlalchemy import (
    String,
    Integer,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Lead(Base):
    """Core Lead entity in Omshiv CRM."""
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile: Mapped[str] = mapped_column(String(15), index=True, nullable=False)  # Normalized 91XXXXXXXXXX
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lead_type: Mapped[str] = mapped_column(String(32), default="BUYER", nullable=False)  # BUYER, SELLER, TENANT, OWNER
    customer_type: Mapped[str] = mapped_column(String(32), default="USER", nullable=False)  # USER, INVESTOR, BROKER
    source: Mapped[str] = mapped_column(String(64), default="MANUAL", nullable=False)

    related_listing_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    related_project_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("builder_projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    partner_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("channel_partners.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    referral_code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    accompanied_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    stage: Mapped[str] = mapped_column(String(32), default="NEW", nullable=False, index=True)
    temperature: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # HOT, WARM, COLD
    follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lost_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    budget_min: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    budget_max: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    preferred_city: Mapped[Optional[str]] = mapped_column(String(100), default="Alwar", nullable=True)
    preferred_locality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    untouched_timer_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_untouched: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    activities: Mapped[List[LeadActivity]] = relationship(
        "LeadActivity",
        back_populates="lead",
        cascade="all, delete-orphan",
    )

    @classmethod
    def select(cls):
        return select(cls)


class LeadSequence(Base):
    """Annual atomic counter for unbounded 6-digit Lead IDs (OB-YYYY-NNNNNN)."""
    __tablename__ = "lead_sequences"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class LeadActivity(Base):
    """Activity and interaction log for a lead."""
    __tablename__ = "lead_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("leads.lead_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_action: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stage_before: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    stage_after: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    temperature: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    logged_by: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
    )
    performed_by: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    lead: Mapped[Lead] = relationship("Lead", back_populates="activities")


# Alias for LeadActivity representing action logs
LeadActionLog = LeadActivity


class TblLead(Base):
    """Full 54-field legacy & modern leads entity mapped to tbl_leads."""
    __tablename__ = "tbl_leads"

    leads_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assign_franch_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assign_franchstaff_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assignfranchisee_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    assignfranchiseestaff_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    property_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lead_table_name: Mapped[Optional[str]] = mapped_column(String(264), default="BUY", nullable=True)
    customer_type: Mapped[str] = mapped_column(String(32), default="USER", nullable=False)  # USER, INVESTOR, BROKER
    dealer_have: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lead_status_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lead_source_id: Mapped[Optional[int]] = mapped_column(Integer, default=1, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mobile: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    permission: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nextfollowup_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deal_final_price: Mapped[float] = mapped_column(Numeric(18, 2), default=0.00, nullable=False)
    registry_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    property_idno: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    indv_property_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approve_lead_remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approve_by: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approve_lead_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deal_close_by: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dealclose_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deal_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    lead_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lead_close_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reference_relation_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refer_by_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refer_by_mobile: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    alternate_contact_mobile: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    create_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lead_unique_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    lastfollowup_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lastcallstatus_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calls_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lead_open: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    lead_remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stage: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    location_lat: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_long: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rating: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    current_update: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    update_userid: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    disqualified_reason: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_admin: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    call_status_qulified: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_callstatus_updatetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sold_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opportunity_converted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opportunity_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opportunity_datetime: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    modified_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


