import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.properties import Property
from app.models.owner_requests import OwnerAdRequest

logger = logging.getLogger(__name__)


async def get_property_by_id_or_code(property_id_or_code: str, db: AsyncSession) -> Property:
    stmt = select(Property).where(
        or_(
            Property.property_id == property_id_or_code,
            Property.id == (int(property_id_or_code) if property_id_or_code.isdigit() else -1),
        )
    )
    res = await db.execute(stmt)
    prop = res.scalar_one_or_none()
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id_or_code} not found.",
        )
    return prop


async def submit_owner_request(
    property_id_or_code: str,
    request_type: str,
    reason: str,
    mobile: str,
    db: AsyncSession,
) -> OwnerAdRequest:
    prop = await get_property_by_id_or_code(property_id_or_code, db)

    # Check for existing pending request (only 1 allowed at a time)
    pending_stmt = select(OwnerAdRequest).where(
        and_(
            OwnerAdRequest.property_id == prop.id,
            OwnerAdRequest.status == "PENDING",
        )
    )
    pending_res = await db.execute(pending_stmt)
    if pending_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending request already exists for this property.",
        )

    req = OwnerAdRequest(
        property_id=prop.id,
        request_type=request_type.upper(),
        reason=reason,
        status="PENDING",
        requested_by_mobile=mobile,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


async def approve_delete(property_id_or_code: str, db: AsyncSession) -> Property:
    prop = await get_property_by_id_or_code(property_id_or_code, db)
    now = datetime.now(timezone.utc)

    prop.is_recycled = True
    prop.recycled_at = now
    prop.deleted_at = now
    prop.is_live = False

    # Mark any pending delete request as approved
    stmt = select(OwnerAdRequest).where(
        and_(
            OwnerAdRequest.property_id == prop.id,
            OwnerAdRequest.request_type == "DELETE",
            OwnerAdRequest.status == "PENDING",
        )
    )
    res = await db.execute(stmt)
    req = res.scalar_one_or_none()
    if req:
        req.status = "APPROVED"
        req.reviewed_at = now

    await db.commit()
    await db.refresh(prop)
    return prop


async def recycle_bin_restore(property_id_or_code: str, db: AsyncSession) -> Property:
    prop = await get_property_by_id_or_code(property_id_or_code, db)

    prop.is_recycled = False
    prop.recycled_at = None
    prop.deleted_at = None
    prop.is_live = True

    await db.commit()
    await db.refresh(prop)
    return prop
