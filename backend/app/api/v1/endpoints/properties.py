from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.models.properties import Property
from app.schemas.property_schemas import PropertyPostRequest, QuickListingRequest
from app.services.property_service import create_property, create_quick_listing

router = APIRouter()


@router.post("/properties/post", status_code=status.HTTP_201_CREATED)
async def post_property(
    payload: PropertyPostRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Posts a new property listing with strict validation and 5-digit OP-YYYY-NNNNN sequence."""
    prop = await create_property(payload, db=db, source="PORTAL")
    return {
        "id": prop.id,
        "property_id": prop.property_id,
        "title": prop.title,
        "listing_type": prop.listing_type,
        "category_code": prop.category_code,
        "sub_category_code": prop.sub_category_code,
        "pincode": prop.pincode,
        "city": prop.city,
        "expected_price": float(prop.expected_price),
        "verified_status": prop.verified_status,
        "is_live": prop.is_live,
        "created_at": prop.created_at.isoformat(),
    }


@router.post("/properties/quick-listing", status_code=status.HTTP_201_CREATED)
async def post_quick_listing(
    payload: QuickListingRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Unauthenticated quick listing endpoint creating a pending property."""
    prop = await create_quick_listing(payload, db=db)
    return {
        "id": prop.id,
        "property_id": prop.property_id,
        "title": prop.title,
        "listing_type": prop.listing_type,
        "category_code": prop.category_code,
        "sub_category_code": prop.sub_category_code,
        "pincode": prop.pincode,
        "city": prop.city,
        "expected_price": float(prop.expected_price),
        "source": prop.source,
        "verified_status": prop.verified_status,
        "is_live": prop.is_live,
        "created_at": prop.created_at.isoformat(),
    }


@router.get("/properties/{id}", status_code=status.HTTP_200_OK)
async def get_property(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves property details by alphanumeric OP-YYYY-NNNNN or numeric id."""
    stmt = select(Property).where(
        or_(Property.property_id == id, Property.id == (int(id) if id.isdigit() else -1))
    )
    res = await db.execute(stmt)
    prop = res.scalar_one_or_none()
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {id} not found.",
        )
    return {
        "id": prop.id,
        "property_id": prop.property_id,
        "title": prop.title,
        "description": prop.description,
        "listing_type": prop.listing_type,
        "category_code": prop.category_code,
        "sub_category_code": prop.sub_category_code,
        "pincode": prop.pincode,
        "city": prop.city,
        "locality": prop.locality,
        "expected_price": float(prop.expected_price),
        "owner_name": prop.owner_name,
        # Mask owner mobile for privacy if public viewer
        "owner_mobile": prop.owner_mobile[:2] + "XXXXXX" + prop.owner_mobile[-2:],
        "verified_status": prop.verified_status,
        "is_live": prop.is_live,
        "is_recycled": prop.is_recycled,
        "created_at": prop.created_at.isoformat(),
    }
