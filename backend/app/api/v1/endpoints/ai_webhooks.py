from __future__ import annotations
import os
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ai.agents.meta_lead_agent import MetaLeadAgent

logger = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_VERIFY_TOKEN = "omshiv_meta_secret_token"


def _verify_meta_challenge(
    hub_mode: Optional[str],
    hub_verify_token: Optional[str],
    hub_challenge: Optional[str],
) -> Response:
    """Verifies standard Meta/Instagram webhook subscription challenge."""
    expected_token = os.environ.get("META_VERIFY_TOKEN", DEFAULT_VERIFY_TOKEN)
    if hub_mode == "subscribe":
        if hub_verify_token and expected_token and hub_verify_token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verification token mismatch",
            )
        if hub_challenge is not None:
            try:
                challenge_int = int(hub_challenge)
                return Response(content=str(challenge_int), media_type="text/plain")
            except (ValueError, TypeError):
                return Response(content=str(hub_challenge), media_type="text/plain")

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid verification request: hub.mode must be 'subscribe'",
    )


@router.get("/meta", summary="Meta Ads Webhook Subscription Verification")
async def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """GET verification challenge for Meta Ads leadgen webhook."""
    return _verify_meta_challenge(hub_mode, hub_verify_token, hub_challenge)


@router.post("/meta", summary="Meta Ads LeadGen Ingestion Endpoint")
async def post_meta_lead(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """POST endpoint for Meta Ads inbound lead webhook payload."""
    lead_payload = dict(payload)

    # Check for Meta nested webhook entry structure
    if "entry" in payload and isinstance(payload["entry"], list) and len(payload["entry"]) > 0:
        entry = payload["entry"][0]
        changes = entry.get("changes", [])
        if changes and isinstance(changes, list) and len(changes) > 0:
            val = changes[0].get("value", {})
            if isinstance(val, dict):
                lead_payload = {**val, **payload}

    agent = MetaLeadAgent(db)
    result = await agent.process_meta_lead(lead_payload, channel="META_LEAD_ADS")
    return result


@router.get("/instagram", summary="Instagram Webhook Subscription Verification")
async def verify_instagram_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """GET verification challenge for Instagram webhook."""
    return _verify_meta_challenge(hub_mode, hub_verify_token, hub_challenge)


@router.post("/instagram", summary="Instagram Lead/Direct Ingestion Endpoint")
async def post_instagram_lead(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """POST endpoint for Instagram lead messages and inquiries."""
    lead_payload = dict(payload)

    # Check for Instagram messaging structure
    if "entry" in payload and isinstance(payload["entry"], list) and len(payload["entry"]) > 0:
        entry = payload["entry"][0]
        messaging = entry.get("messaging", [])
        if messaging and isinstance(messaging, list) and len(messaging) > 0:
            msg = messaging[0]
            if isinstance(msg, dict):
                lead_payload = {**msg, **payload}

    agent = MetaLeadAgent(db)
    result = await agent.process_meta_lead(lead_payload, channel="INSTAGRAM")
    return result
