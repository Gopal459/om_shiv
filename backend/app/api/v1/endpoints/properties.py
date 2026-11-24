from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.models.properties import Property
from app.repositories import property_repo
from app.schemas.property_schemas import PropertyPostRequest, QuickListingRequest
from app.schemas.tbl_property_schemas import (
    TblPropertyCreateRequest,
    TblPropertyUpdateRequest,
    TblPropertyStatusUpdateRequest,
    TblPropertyHubListResponse,
)
from app.services.property_service import (
    create_property,
    create_quick_listing,
    create_tbl_property,
    get_tbl_properties_hub,
    get_tbl_property_by_id,
    update_tbl_property,
    update_tbl_property_status,
)

router = APIRouter()


@router.get("/properties/hub", response_model=TblPropertyHubListResponse, status_code=status.HTTP_200_OK)
async def get_properties_hub(
    tab: str = Query("new_assign", description="Sidebar tab filter"),
    search: Optional[str] = Query(None, description="Search term for ID, name, mobile, location"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves paginated property listings mapped to the 7 admin sidebar tabs."""
    return await get_tbl_properties_hub(tab=tab, search=search, page=page, limit=limit, db=db)


@router.post("/properties/create", status_code=status.HTTP_201_CREATED)
async def post_tbl_property(
    payload: TblPropertyCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Creates a validated property in tbl_property and optional tbl_payingguest."""
    prop = await create_tbl_property(payload, db=db)
    return {
        "property_id": prop.property_id,
        "propertyid_no": prop.propertyid_no,
        "property_type": prop.property_type,
        "looking_type": prop.looking_type,
        "looking_subcat_type": prop.looking_subcat_type,
        "expected_price": float(prop.expected_price),
        "source_owner_name": prop.source_owner_name,
        "source_owner_mobile": prop.source_owner_mobile,
        "verified_status": prop.verified_status,
        "is_active": prop.is_active,
        "slug": prop.slug,
        "created_date": prop.created_date.isoformat() if prop.created_date else None,
    }


@router.get("/properties/tbl/{id}", status_code=status.HTTP_200_OK)
async def get_tbl_property(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves full 124-column details + PG details for a property."""
    prop = await get_tbl_property_by_id(id, db=db)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {id} not found.",
        )
    return prop


@router.put("/properties/tbl/{id}", status_code=status.HTTP_200_OK)
async def put_tbl_property(
    id: int,
    payload: TblPropertyUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Updates property fields in tbl_property."""
    prop = await update_tbl_property(id, payload, db=db)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {id} not found.",
        )
    return prop


@router.patch("/properties/tbl/{id}/status", status_code=status.HTTP_200_OK)
async def patch_tbl_property_status(
    id: int,
    payload: TblPropertyStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Updates status flags (assigned user, verified, live, sold, recycle)."""
    prop = await update_tbl_property_status(id, payload, db=db)
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {id} not found.",
        )
    return prop


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
    prop = await property_repo.get_by_id_or_code(db, id)
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
