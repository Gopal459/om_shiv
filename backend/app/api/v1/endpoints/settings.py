from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Request, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.services.settings_service import settings_service

router = APIRouter()
security = HTTPBearer(auto_error=False)


# --- Pydantic Schemas ---

class SettingResponse(BaseModel):
    key: str
    value: Any
    data_type: str
    category: str
    description: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpdateSettingRequest(BaseModel):
    value: Any = Field(..., description="New setting value conforming to its data_type")
    reason: Optional[str] = Field(None, description="Operational justification for changing the setting")
    performed_by: Optional[str] = Field(None, description="Optional override of actor employee_id")


class AuditLogResponse(BaseModel):
    id: str
    entity_name: str
    entity_id: str
    action: str
    old_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    performed_by: str
    ip_address: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}


class AuditLogPageResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    limit: int
    offset: int


def get_actor_from_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Extract authenticated employee_id from Bearer token, or fallback to SYSTEM."""
    if credentials and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            sub = payload.get("sub")
            if sub:
                return str(sub)
        except Exception:
            pass
    return "SYSTEM"


# --- Settings Endpoints ---

@router.get(
    "/settings",
    response_model=List[SettingResponse],
    status_code=status.HTTP_200_OK,
    summary="List all dynamic system settings",
)
async def list_settings(
    category: Optional[str] = Query(None, description="Filter settings by category (e.g. SLA, NOTIFICATION, ROUTING)"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all configurable system settings, optionally filtered by category."""
    settings = await settings_service.get_all_settings(db, category=category)
    return settings


@router.get(
    "/settings/{key}",
    response_model=SettingResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve single setting by key",
)
async def get_setting_by_key(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details and value for a specific setting key."""
    setting = await settings_service.get_setting_model(db, key=key)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )
    return setting


@router.patch(
    "/settings/{key}",
    response_model=SettingResponse,
    status_code=status.HTTP_200_OK,
    summary="Update system setting value",
)
async def update_setting(
    key: str,
    payload: UpdateSettingRequest,
    request: Request,
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
):
    """Update a dynamic setting value, automatically appending to immutable audit log."""
    performed_by = payload.performed_by or actor
    client_ip = request.client.host if request.client else None

    updated = await settings_service.update_setting(
        db=db,
        key=key,
        value=payload.value,
        performed_by=performed_by,
        reason=payload.reason,
        ip_address=client_ip,
    )
    return updated


# --- Audit Log Endpoints ---

@router.get(
    "/audit-logs",
    response_model=AuditLogPageResponse,
    status_code=status.HTTP_200_OK,
    summary="Query immutable audit log ledger",
)
async def get_audit_logs(
    entity_name: Optional[str] = Query(None, description="Filter by entity name (e.g. system_settings, leads)"),
    entity_id: Optional[str] = Query(None, description="Filter by entity identifier"),
    performed_by: Optional[str] = Query(None, description="Filter by employee_id or actor"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve audit history filtered by entity, entity_id, or actor."""
    items, total = await settings_service.get_audit_logs(
        db=db,
        entity_name=entity_name,
        entity_id=entity_id,
        performed_by=performed_by,
        limit=limit,
        offset=offset,
    )
    return AuditLogPageResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
