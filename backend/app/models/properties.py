from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

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


class PropertySequence(Base):
    """Atomic annual sequence counter for OP-YYYY-NNNNN (5-digit unbounded sequence)."""
    __tablename__ = "property_sequences"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Property(Base):
    """Core master property listing table."""
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)  # OP-YYYY-NNNNN
    listing_type: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Rent, 2=Sale, 3=PG
    category_code: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Res, 2=Comm, 3=Agri, 4=Ind
    sub_category_code: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Flat, 2=House, 3=Plot, etc.

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pincode: Mapped[str] = mapped_column(String(6), ForeignKey("pincode_master.pincode"), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), default="Alwar", nullable=False)
    locality: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 6), nullable=True)

    expected_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    price_negotiable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    owner_name: Mapped[str] = mapped_column(String(150), nullable=False)
    owner_mobile: Mapped[str] = mapped_column(String(15), nullable=False)
    posted_by_role: Mapped[str] = mapped_column(String(32), default="OWNER", nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="PORTAL", nullable=False)

    verified_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0=Unverified, 1=Verified, 2=Rejected
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_recycled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recycled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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

    flat_details: Mapped[Optional["PropResidentialFlat"]] = relationship(
        "PropResidentialFlat", back_populates="property", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )
    house_details: Mapped[Optional["PropHouseVilla"]] = relationship(
        "PropHouseVilla", back_populates="property", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )
    pg_details: Mapped[Optional["PropPG"]] = relationship(
        "PropPG", back_populates="property", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )


class PropResidentialFlat(Base):
    __tablename__ = "prop_residential_flats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), unique=True, nullable=False)
    bhk: Mapped[int] = mapped_column(Integer, nullable=False)
    rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    bathrooms: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    balconies: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    super_area: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    carpet_area: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total_floors: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    property_floor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    property: Mapped[Property] = relationship("Property", back_populates="flat_details")


class PropHouseVilla(Base):
    __tablename__ = "prop_houses_villas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), unique=True, nullable=False)
    bhk: Mapped[int] = mapped_column(Integer, nullable=False)
    rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    bathrooms: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_floors: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sell_part_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Entire house vs floor
    plot_area: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    built_up_area: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    property: Mapped[Property] = relationship("Property", back_populates="house_details")


class PropPG(Base):
    __tablename__ = "prop_pg"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), unique=True, nullable=False)
    pg_name: Mapped[str] = mapped_column(String(150), nullable=False)
    available_for: Mapped[str] = mapped_column(String(50), default="BOYS", nullable=False)  # BOYS, GIRLS, ANY
    room_type: Mapped[str] = mapped_column(String(50), default="SINGLE", nullable=False)  # SINGLE, DOUBLE, TRIPLE
    food_included: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attached_bathroom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attached_balcony: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    common_area: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    smoking_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alcohol_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rent_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    rent_negotiable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra_charges: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    min_stay_months: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notice_period_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    property: Mapped[Property] = relationship("Property", back_populates="pg_details")
