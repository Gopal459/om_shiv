from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.property_master_service import (
    get_property_schema,
    add_master_option,
    get_pincode_details,
)

router = APIRouter()


class MasterOptionCreate(BaseModel):
    group_code: str = Field(..., description="Target group code, e.g. FACING, AREA_UNITS")
    code: str = Field(..., description="Unique alphanumeric code inside group")
    label: str = Field(..., description="Human readable label")
    display_order: int = Field(0, description="Display sorting order")
    applicable_categories: List[int] = Field(default_factory=list, description="Category scoping list (empty = all)")


@router.get("/public/property-schema", status_code=status.HTTP_200_OK)
async def public_property_schema(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieves all dynamic property attributes and options for frontend forms."""
    return await get_property_schema(db)


@router.post("/admin/property-master/options", status_code=status.HTTP_201_CREATED)
async def create_property_master_option(
    payload: MasterOptionCreate,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Admin endpoint to dynamically add new property options without hardcoded changes."""
    option = await add_master_option(
        db=db,
        group_code=payload.group_code,
        code=payload.code,
        label=payload.label,
        display_order=payload.display_order,
        applicable_categories=payload.applicable_categories,
    )
    return {
        "id": option.id,
        "group_id": option.group_id,
        "code": option.code,
        "label": option.label,
        "display_order": option.display_order,
        "applicable_categories": option.applicable_categories,
    }


@router.get("/public/pincodes/{pincode}", status_code=status.HTTP_200_OK)
async def lookup_pincode(
    pincode: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Validates and retrieves postal pincode details."""
    pin_record = await get_pincode_details(db, pincode)
    if not pin_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pincode {pincode} is not found or currently unserviceable.",
        )
    return {
        "pincode": pin_record.pincode,
        "city": pin_record.city,
        "district": pin_record.district,
        "state": pin_record.state,
        "is_serviceable": pin_record.is_serviceable,
    }
