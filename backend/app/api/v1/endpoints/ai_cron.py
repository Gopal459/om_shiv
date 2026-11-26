"""Cron-webhook endpoints for triggering AI scheduler runners.

Each endpoint is a lightweight POST webhook intended to be called by an external
scheduler (e.g., cron, Celery beat, GitHub Actions, or APScheduler).  Endpoints
are secured via the ``CRON_SECRET_KEY`` environment variable so they cannot be
triggered by arbitrary HTTP clients.

Routes:
  POST /v1/ai/cron/nurturing-runner       -- Run the nurturing cadence cycle.
  POST /v1/ai/cron/property-alerts-runner -- Retry failed property-alert dispatches.
  POST /v1/ai/cron/call-retry-runner      -- Retry failed outbound voice calls.
  POST /v1/ai/cron/retention-purge        -- Purge PII from logs older than N days.

Security:
  Pass the ``X-Cron-Secret`` header matching the ``CRON_SECRET_KEY`` env var.
  Defaults to a development-only placeholder; set a strong secret in production.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.workers.ai_scheduler import (
    run_nurturing_cycle,
    run_property_alert_queue,
    run_call_retry_cycle,
    run_pii_retention_purge,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ai/cron", tags=["ai-cron"])

_DEFAULT_DEV_SECRET = "dev-cron-secret-change-in-production"


# ---------------------------------------------------------------------------
# Security dependency
# ---------------------------------------------------------------------------

def _get_cron_secret() -> str:
    return os.environ.get("CRON_SECRET_KEY", _DEFAULT_DEV_SECRET)


async def verify_cron_secret(
    x_cron_secret: Optional[str] = Header(default=None, alias="X-Cron-Secret"),
) -> None:
    """Validate the X-Cron-Secret header against CRON_SECRET_KEY env var."""
    expected = _get_cron_secret()
    if not x_cron_secret or x_cron_secret != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Cron-Secret header.",
        )


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------

class RetentionPurgeRequest(BaseModel):
    retention_days: int = 90


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/nurturing-runner",
    summary="Trigger the AI nurturing cadence cycle",
    response_model=None,
    dependencies=[Depends(verify_cron_secret)],
)
async def nurturing_runner(db: AsyncSession = Depends(get_db)):
    """Run the Day-0/1/3/7/15/30 nurturing evaluation for all eligible leads.

    Safe to call repeatedly; the agent enforces 24-hour cooldowns and feature-flag
    modes (SHADOW / LIVE / DISABLED) internally.
    """
    try:
        async with db.begin():
            result = await run_nurturing_cycle(db)
        logger.info("[ai_cron] nurturing-runner completed: %s", result)
        return {"status": "ok", "detail": result}
    except Exception as exc:
        logger.error("[ai_cron] nurturing-runner error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Nurturing runner failed: {exc}",
        )


@router.post(
    "/property-alerts-runner",
    summary="Retry failed property-alert dispatches",
    response_model=None,
    dependencies=[Depends(verify_cron_secret)],
)
async def property_alerts_runner(db: AsyncSession = Depends(get_db)):
    """Retry PropertyAlertHistory entries with status=FAILED (created < 24 h ago).

    Anti-spam deduplication and consent checks are enforced by the agent.
    """
    try:
        async with db.begin():
            result = await run_property_alert_queue(db)
        logger.info("[ai_cron] property-alerts-runner completed: %s", result)
        return {"status": "ok", "detail": result}
    except Exception as exc:
        logger.error("[ai_cron] property-alerts-runner error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Property alerts runner failed: {exc}",
        )


@router.post(
    "/call-retry-runner",
    summary="Retry failed outbound voice calls (quiet-hours aware)",
    response_model=None,
    dependencies=[Depends(verify_cron_secret)],
)
async def call_retry_runner(db: AsyncSession = Depends(get_db)):
    """Retry voice call logs with status ERROR/FAILED from the last 24 hours.

    The runner self-cancels if the current IST time falls in quiet hours (21:00-09:00).
    TRAI consent is re-verified before each retry.
    """
    try:
        async with db.begin():
            result = await run_call_retry_cycle(db)
        logger.info("[ai_cron] call-retry-runner completed: %s", result)
        return {"status": "ok", "detail": result}
    except Exception as exc:
        logger.error("[ai_cron] call-retry-runner error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Call retry runner failed: {exc}",
        )


@router.post(
    "/retention-purge",
    summary="Purge PII from AI execution logs older than N days",
    response_model=None,
    dependencies=[Depends(verify_cron_secret)],
)
async def retention_purge(
    body: RetentionPurgeRequest = RetentionPurgeRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Scrub ``input_summary`` and ``output_response`` for logs older than ``retention_days``.

    Defaults to 90 days. Pass ``{"retention_days": N}`` in the request body to override.
    Idempotent: already-purged rows are skipped automatically.
    """
    try:
        async with db.begin():
            result = await run_pii_retention_purge(db, retention_days=body.retention_days)
        logger.info("[ai_cron] retention-purge completed: %s", result)
        return {"status": "ok", "detail": result}
    except Exception as exc:
        logger.error("[ai_cron] retention-purge error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retention purge failed: {exc}",
        )
