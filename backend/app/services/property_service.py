import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.properties import (
    Property,
    PropertySequence,
    PropResidentialFlat,
)
from app.models.property_master import PincodeMaster
from app.schemas.property_schemas import PropertyPostRequest, QuickListingRequest

logger = logging.getLogger(__name__)


async def generate_property_id(db: AsyncSession) -> str:
    """Atomically allocates the next 5-digit sequence ID for OP-YYYY-NNNNN."""
    current_year = datetime.now(timezone.utc).year

    # Check for existing sequence row
    stmt = (
        select(PropertySequence)
        .where(PropertySequence.year == current_year)
        .with_for_update()
    )
    result = await db.execute(stmt)
    seq_record = result.scalar_one_or_none()

    if not seq_record:
        # Create sequence record for new year
        seq_record = PropertySequence(year=current_year, last_sequence=1)
        db.add(seq_record)
        await db.flush()
        seq_num = 1
    else:
        seq_record.last_sequence += 1
        seq_num = seq_record.last_sequence

    # Format: OP-YYYY-NNNNN (5 digits zero-padded, unbounded)
    return f"OP-{current_year}-{seq_num:05d}"


async def validate_pincode_serviceable(pincode: str, db: AsyncSession) -> None:
    """Ensures pincode exists in pincode_master and is serviceable."""
    stmt = select(PincodeMaster).where(
        PincodeMaster.pincode == pincode.strip(),
        PincodeMaster.is_serviceable == True,
    )
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Pincode {pincode} does not exist in master registry or is not serviceable.",
        )


async def create_property(
    payload: PropertyPostRequest,
    db: AsyncSession,
    source: str = "PORTAL",
) -> Property:
    """Creates a validated property listing with 5-digit sequence."""
    await validate_pincode_serviceable(payload.pincode, db)
    prop_id = await generate_property_id(db)

    property_obj = Property(
        property_id=prop_id,
        listing_type=payload.listing_type,
        category_code=payload.category_code,
        sub_category_code=payload.sub_category_code,
        title=payload.title,
        description=payload.description,
        pincode=payload.pincode,
        city=payload.city,
        locality=payload.locality,
        latitude=payload.latitude,
        longitude=payload.longitude,
        expected_price=payload.expected_price,
        price_negotiable=payload.price_negotiable,
        owner_name=payload.owner_name,
        owner_mobile=payload.owner_mobile,
        posted_by_role=payload.posted_by_role,
        source=source,
        verified_status=0,
        is_live=False,
    )
    db.add(property_obj)
    await db.flush()

    # If flat details provided, add child flat record
    if payload.flat_details:
        flat = PropResidentialFlat(
            property_id=property_obj.id,
            bhk=payload.flat_details.bhk,
            rooms=payload.flat_details.rooms,
            bathrooms=payload.flat_details.bathrooms,
            balconies=payload.flat_details.balconies,
            super_area=payload.flat_details.super_area,
            carpet_area=payload.flat_details.carpet_area,
            total_floors=payload.flat_details.total_floors,
            property_floor=payload.flat_details.property_floor,
        )
        db.add(flat)

    await db.commit()
    await db.refresh(property_obj)
    return property_obj


async def create_quick_listing(
    payload: QuickListingRequest,
    db: AsyncSession,
) -> Property:
    """Creates an unauthenticated quick listing."""
    await validate_pincode_serviceable(payload.pincode, db)
    prop_id = await generate_property_id(db)

    property_obj = Property(
        property_id=prop_id,
        listing_type=payload.listing_type,
        category_code=payload.category_code,
        sub_category_code=payload.sub_category_code,
        title=payload.title,
        pincode=payload.pincode,
        city=payload.city,
        expected_price=payload.expected_price,
        owner_name=payload.owner_name,
        owner_mobile=payload.owner_mobile,
        source="QUICK_LISTING",
        verified_status=0,
        is_live=False,
    )
    db.add(property_obj)
    await db.commit()
    await db.refresh(property_obj)
    return property_obj
