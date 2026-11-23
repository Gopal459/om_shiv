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

    stage: Mapped[str] = mapped_column(String(32), default="NEW", nullable=False, index=True)
    temperature: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # HOT, WARM, COLD
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
    logged_by: Mapped[Optional[str]] = mapped_column(
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
