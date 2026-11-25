from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.verification_service import (
    assign_verifier,
    log_verification_call,
    upload_document,
    verify_and_approve,
)

router = APIRouter()


class AssignVerifierRequest(BaseModel):
    verifier_emp_id: str
    assigned_by: str = "EMP-0001"


class LogCallRequest(BaseModel):
    caller_emp_id: str
    call_outcome: str
    notes: Optional[str] = None
    confirmed_price: Optional[float] = None
    scheduled_visit_date: Optional[datetime] = None


class UploadDocumentRequest(BaseModel):
    doc_type: str
    file_url: str
    uploaded_by: str


class VerifyApproveRequest(BaseModel):
    area_confirmed: bool
    photos_genuine_confirmed: bool
    ownership_confirmed: bool
    approver_emp_id: str = "EMP-0001"


@router.post("/properties/{id}/assign-verifier", status_code=status.HTTP_200_OK)
async def endpoint_assign_verifier(
    id: str,
    payload: AssignVerifierRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    assignment = await assign_verifier(
        property_id_or_code=id,
        verifier_emp_id=payload.verifier_emp_id,
        assigned_by=payload.assigned_by,
        db=db,
    )
    return {
        "id": assignment.id,
        "property_id": assignment.property_id,
        "assigned_to": assignment.assigned_to,
        "status": assignment.status,
    }


@router.post("/properties/{id}/log-call", status_code=status.HTTP_200_OK)
async def endpoint_log_call(
    id: str,
    payload: LogCallRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    call = await log_verification_call(
        property_id_or_code=id,
        caller_emp_id=payload.caller_emp_id,
        call_outcome=payload.call_outcome,
        notes=payload.notes,
        confirmed_price=payload.confirmed_price,
        scheduled_visit_date=payload.scheduled_visit_date,
        db=db,
    )
    return {
        "id": call.id,
        "property_id": call.property_id,
        "caller_emp_id": call.caller_emp_id,
        "call_outcome": call.call_outcome,
        "confirmed_price": float(call.confirmed_price) if call.confirmed_price is not None else None,
        "scheduled_visit_date": call.scheduled_visit_date.isoformat() if call.scheduled_visit_date else None,
    }


@router.post("/properties/{id}/upload-document", status_code=status.HTTP_200_OK)
async def endpoint_upload_document(
    id: str,
    payload: UploadDocumentRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    doc = await upload_document(
        property_id_or_code=id,
        doc_type=payload.doc_type,
        file_url=payload.file_url,
        uploaded_by=payload.uploaded_by,
        db=db,
    )
    return {
        "id": doc.id,
        "property_id": doc.property_id,
        "doc_type": doc.doc_type,
        "file_url": doc.file_url,
        "is_verified": doc.is_verified,
    }


@router.post("/properties/{id}/verify-and-approve", status_code=status.HTTP_200_OK)
async def endpoint_verify_and_approve(
    id: str,
    payload: VerifyApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    prop = await verify_and_approve(
        property_id_or_code=id,
        area_confirmed=payload.area_confirmed,
        photos_genuine_confirmed=payload.photos_genuine_confirmed,
        ownership_confirmed=payload.ownership_confirmed,
        approver_emp_id=payload.approver_emp_id,
        db=db,
    )
    return {
        "id": prop.id,
        "property_id": prop.property_id,
        "verified_status": prop.verified_status,
        "is_live": prop.is_live,
        "expires_at": prop.expires_at.isoformat() if prop.expires_at else None,
    }
