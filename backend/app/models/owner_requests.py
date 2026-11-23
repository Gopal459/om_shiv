from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OwnerAdRequest(Base):
    """Owner self-service listing requests (SOLD, DELETE, RE_LIVE).
    Enforces that only one pending request exists per property.
    """
    __tablename__ = "owner_ad_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    request_type: Mapped[str] = mapped_column(String(32), nullable=False)  # SOLD, DELETE, RE_LIVE
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False, index=True)  # PENDING, APPROVED, REJECTED
    requested_by_mobile: Mapped[str] = mapped_column(String(15), nullable=False)

    reviewed_by: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
