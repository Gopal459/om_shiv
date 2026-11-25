from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.properties import Property
from app.repositories import property_repo
from app.services.owner_service import (
    submit_owner_request,
    approve_delete,
    recycle_bin_restore,
)

router = APIRouter()


class OwnerRequestPayload(BaseModel):
    mobile: str = Field(..., min_length=10, max_length=15)
    reason: str = Field(..., min_length=3)


@router.post("/owner/properties/{id}/request-sold", status_code=status.HTTP_200_OK)
async def endpoint_request_sold(
    id: str,
    payload: OwnerRequestPayload,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    req = await submit_owner_request(
        property_id_or_code=id,
        request_type="SOLD",
        reason=payload.reason,
        mobile=payload.mobile,
        db=db,
    )
    return {"id": req.id, "request_type": req.request_type, "status": req.status}


@router.post("/owner/properties/{id}/request-delete", status_code=status.HTTP_200_OK)
async def endpoint_request_delete(
    id: str,
    payload: OwnerRequestPayload,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    req = await submit_owner_request(
        property_id_or_code=id,
        request_type="DELETE",
        reason=payload.reason,
        mobile=payload.mobile,
        db=db,
    )
    return {"id": req.id, "request_type": req.request_type, "status": req.status}


@router.post("/owner/properties/{id}/request-relive", status_code=status.HTTP_200_OK)
async def endpoint_request_relive(
    id: str,
    payload: OwnerRequestPayload,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    req = await submit_owner_request(
        property_id_or_code=id,
        request_type="RE_LIVE",
        reason=payload.reason,
        mobile=payload.mobile,
        db=db,
    )
    return {"id": req.id, "request_type": req.request_type, "status": req.status}


@router.post("/admin/properties/{id}/approve-delete", status_code=status.HTTP_200_OK)
async def endpoint_approve_delete(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    prop = await approve_delete(property_id_or_code=id, db=db)
    return {
        "id": prop.id,
        "property_id": prop.property_id,
        "is_recycled": prop.is_recycled,
        "is_live": prop.is_live,
    }


@router.post("/admin/properties/{id}/recycle-bin-restore", status_code=status.HTTP_200_OK)
async def endpoint_recycle_bin_restore(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    prop = await recycle_bin_restore(property_id_or_code=id, db=db)
    return {
        "id": prop.id,
        "property_id": prop.property_id,
        "is_recycled": prop.is_recycled,
        "is_live": prop.is_live,
    }


@router.get("/admin/recycle-bin", status_code=status.HTTP_200_OK)
async def endpoint_list_recycle_bin(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    properties = await property_repo.list_recycled(db)
    return [
        {
            "id": p.id,
            "property_id": p.property_id,
            "title": p.title,
            "recycled_at": p.recycled_at.isoformat() if p.recycled_at else None,
        }
        for p in properties
    ]
