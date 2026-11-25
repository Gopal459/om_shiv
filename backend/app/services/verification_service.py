import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models.properties import Property
from app.models.property_verification import (
    PropertyVerificationAssignment,
    PropertyVerificationCall,
    PropertyDocument,
)

logger = logging.getLogger(__name__)


async def get_property_by_id_or_code(property_id_or_code: str, db: AsyncSession) -> Property:
    """Finds a property by string OP-YYYY-NNNNN or integer PK."""
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


async def assign_verifier(
    property_id_or_code: str,
    verifier_emp_id: str,
    assigned_by: str,
    db: AsyncSession,
) -> PropertyVerificationAssignment:
    prop = await get_property_by_id_or_code(property_id_or_code, db)
    assignment = PropertyVerificationAssignment(
        property_id=prop.id,
        assigned_to=verifier_emp_id,
        assigned_by=assigned_by,
        status="ASSIGNED",
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def log_verification_call(
    property_id_or_code: str,
    caller_emp_id: str,
    call_outcome: str,
    notes: Optional[str],
    confirmed_price: Optional[float],
    scheduled_visit_date: Optional[datetime],
    db: AsyncSession,
) -> PropertyVerificationCall:
    prop = await get_property_by_id_or_code(property_id_or_code, db)
    call = PropertyVerificationCall(
        property_id=prop.id,
        caller_emp_id=caller_emp_id,
        call_outcome=call_outcome,
        notes=notes,
        confirmed_price=confirmed_price,
        scheduled_visit_date=scheduled_visit_date,
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call


async def upload_document(
    property_id_or_code: str,
    doc_type: str,
    file_url: str,
    uploaded_by: str,
    db: AsyncSession,
) -> PropertyDocument:
    prop = await get_property_by_id_or_code(property_id_or_code, db)
    doc = PropertyDocument(
        property_id=prop.id,
        doc_type=doc_type,
        file_url=file_url,
        uploaded_by=uploaded_by,
        is_verified=True,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def verify_and_approve(
    property_id_or_code: str,
    area_confirmed: bool,
    photos_genuine_confirmed: bool,
    ownership_confirmed: bool,
    approver_emp_id: str,
    db: AsyncSession,
) -> Property:
    if not (area_confirmed and photos_genuine_confirmed and ownership_confirmed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve listing: all verification checklist items must be confirmed.",
        )

    prop = await get_property_by_id_or_code(property_id_or_code, db)
    now = datetime.now(timezone.utc)

    prop.verified_status = 1  # 1=Verified
    prop.is_live = True

    # 90 days validity for Sale, 30 days for Rent
    validity_days = 30 if prop.listing_type == 1 else 90
    prop.expires_at = now + timedelta(days=validity_days)

    await db.commit()
    await db.refresh(prop)
    return prop
