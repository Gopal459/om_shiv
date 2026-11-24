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
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
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


class TblProperty(Base):
    """Legacy 124-column tbl_property model providing 100% database schema parity."""
    __tablename__ = "tbl_property"

    property_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assigned_user_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    if_update_user: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    update_date_time: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    update_by_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assigned_user_date_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    propertyid_no: Mapped[str] = mapped_column(String(264), nullable=False)
    property_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=>Rent, 2=>Sell, 3=>PG
    user_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    state_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    city_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    location_lat: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    location_long: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    sublocality_address: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    slug: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    nearby_area: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    pincode: Mapped[str] = mapped_column(String(264), default="0", nullable=False)
    looking_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=>Res, 2=>Comm, 3=>Agri, 4=>Ind
    looking_subcat_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    looking_subcat_type_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    whichpart_torent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=>Complete, 2=>Part
    floor_torent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # -1=>Basement, 0=>Ground
    street_no: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    property_ownership: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=>Leasehold, 2=>Freehold
    noof_bhk: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    possession_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=>Ready, 2=>Under construction
    constructed_floors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    area: Mapped[str] = mapped_column(String(264), default="0", nullable=False)
    area_unit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    constructed_area: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    constructed_areaunit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    boundary: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    super_area: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    superarea_unit: Mapped[str] = mapped_column(String(264), default="0", nullable=False)
    carpet_area: Mapped[str] = mapped_column(String(264), default="0", nullable=False)
    carpetarea_unit: Mapped[str] = mapped_column(String(264), default="0", nullable=False)
    noof_floors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    property_which_floors: Mapped[str] = mapped_column(String(264), default="0", nullable=False)
    office: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    room: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    kitchen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    toilet: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shade: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    machinery_plant: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    garage_parking: Mapped[str] = mapped_column(String(264), default="0", nullable=False)
    baathroom: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balcony: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    construction_age: Mapped[str] = mapped_column(String(264), default="0", nullable=False)
    transaction_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=>Resale, 2=>New
    want_tosell: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=>Part, 2=>Complete
    project_name: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    priceper_unitvalue: Mapped[float] = mapped_column(Numeric(18, 2), default=0.00, nullable=False)
    priceperunit_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expected_price: Mapped[float] = mapped_column(Numeric(18, 2), default=0.00, nullable=False)
    price_negociable: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=>Yes, 2=>No
    extra_charge_apply: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    width_facing_road: Mapped[str] = mapped_column(String(264), default="0", nullable=False)
    facing: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=East, 2=West, 3=North, etc.
    flooring: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rentalallow_forid: Mapped[str] = mapped_column(String(255), default="0", nullable=False)
    corner: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clu: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clu_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_furnished: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    furnished_type: Mapped[str] = mapped_column(String(264), default="0", nullable=False)
    featurepowerbackup: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_watersupply: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_lift: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_park: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_ownparking: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_visitparking: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_intercomfac: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_clubhosue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_swimming: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_fitness: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_gatedcomm: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_security: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    feature_electricityconnection: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nearby_atm: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nearby_childchehe: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nearby_shoppingmall: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nearby_hospital: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nearby_school: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nearby_multiplex: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nearby_departmental: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expiarydate: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
    modified_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
    verified_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0=>unverified, 1=>verified
    is_active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_owner_name: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    source_owner_email: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    source_owner_mobile: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    franchise_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    franchiseemember_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verification_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_submit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    document_approve_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_exclusive: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sold_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0=>Available, 1=>Sold, 2=>Expired
    sold_request_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delete_request_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recyclebin_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recyclebin_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    live_request_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_view: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    images: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    images_order: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amenities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class TblPayingGuest(Base):
    """Paying guest properties extension table tbl_payingguest."""
    __tablename__ = "tbl_payingguest"

    pg_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pg_name: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    available_category: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=>Pros, 2=>Students, 3=>Both
    gender: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=>Boys, 2=>Girls, 3=>Both
    room_type: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=>Private, 2=>Sharing, 3=>Both
    food_option: Mapped[int] = mapped_column(Integer, default=2, nullable=False)  # 1=>With Food, 2=>Without
    food_type: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=>Veg, 2=>Non-Veg, 3=>Both
    meal_type: Mapped[Optional[str]] = mapped_column(String(264), nullable=True)
    notice_period: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    electrical_charges: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    smoking: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    alcohol: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attached_bathroom: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attached_balcony: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    common_area: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amenities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
