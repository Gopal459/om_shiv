from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class WebsiteInquiry(Base):
    """Inbound public website inquiry form submissions."""
    __tablename__ = "website_inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inquiry_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )  # CALLBACK, PROBLEM_REPORT, SERVICE_LOAN, SERVICE_LEGAL, SERVICE_INTERIOR, CONTACT_US
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mobile: Mapped[str] = mapped_column(String(15), index=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=True)

    is_converted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    converted_lead_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("leads.lead_id", ondelete="SET NULL"),
        nullable=True,
    )
    converted_by_emp_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
    )
    converted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BuilderProject(Base):
    """Builder Projects and Township developments for project-level inquiries."""
    __tablename__ = "builder_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    developer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), default="Alwar", nullable=False)
    locality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
