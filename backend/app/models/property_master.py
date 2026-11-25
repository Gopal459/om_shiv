from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class PropertyMasterGroup(Base):
    """Dynamic property attribute groups (Facing, Flooring, Amenities, Units, etc.)."""
    __tablename__ = "property_master_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    options: Mapped[List["PropertyMasterOption"]] = relationship(
        "PropertyMasterOption",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PropertyMasterOption.display_order",
    )


class PropertyMasterOption(Base):
    """Dynamic options inside a master group. Zero hardcoding in forms."""
    __tablename__ = "property_master_options"
    __table_args__ = (
        UniqueConstraint("group_id", "code", name="uq_master_group_option_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("property_master_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    applicable_categories: Mapped[List[int]] = mapped_column(
        JSON_TYPE,
        default=list,
        nullable=False,
    )  # e.g. [3] for Bigha in Agriculture, [] for universal
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    group: Mapped[PropertyMasterGroup] = relationship("PropertyMasterGroup", back_populates="options")


class PincodeMaster(Base):
    """Master registry of serviceable Indian postal pincodes."""
    __tablename__ = "pincode_master"

    pincode: Mapped[str] = mapped_column(String(6), primary_key=True, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    is_serviceable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
