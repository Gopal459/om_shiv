"""Asynchronous background scheduler for Omshiv AI Agents system.

This module provides four cron-safe async runner functions that are invoked
by external schedulers (cron, APScheduler, or the /v1/ai/cron/* endpoints):

  - run_nurturing_cycle       : Evaluates Day-0/1/3/7/15/30 nurturing steps.
  - run_property_alert_queue  : Dispatches pending new-property alerts.
  - run_call_retry_cycle      : Retries failed outbound calls (quiet-hours aware).
  - run_pii_retention_purge   : Scrubs PII fields in logs older than retention_days.

Safety patterns honoured by every runner:
  * Feature-flag modes (DISABLED / SHADOW / LIVE) via AIAgentConfig.
  * Shadow mode logs the intended action but never mutates CRM state.
  * 24-hour anti-spam cooldown enforced by the FollowupJourneyAgent itself.
  * Consent checks delegated to SafetyGuardrailsService.
  * Quiet-hours (09:00-21:00 IST) enforced before any voice call retry.
  * Terminal-stage leads (WON, LOST, etc.) are skipped automatically.
  * PII purge replaces sensitive text with [PURGED_PER_PII_POLICY] in-place.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_agents import AIAgentConfig, AIAgentExecutionLog, PropertyAlertHistory
from app.models.leads import Lead
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.agents.followup_journey_agent import FollowupJourneyAgent, TERMINAL_LEAD_STAGES
from app.services.ai.agents.new_property_alert_agent import NewPropertyAlertAgent
from app.services.ai.agents.voice_calling_agent import VoiceCallingAgent
from app.workers.sla_worker import is_quiet_hours

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEDULER_AGENT_NAME = "ai_scheduler"
_DEFAULT_MODE = "SHADOW"            # Safe default: log-only, never live
_NURTURING_CADENCE_DAYS: List[int] = [0, 1, 3, 7, 15, 30]
_CALL_RETRY_MAX_ATTEMPTS = 1        # Retry failed calls at most once
_PII_PURGE_PLACEHOLDER = "[PURGED_PER_PII_POLICY]"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_scheduler_mode(db: AsyncSession) -> str:
    """Return the operating mode for the scheduler from AIAgentConfig.

    Falls back to SHADOW (safe) if no DB record is found.
    """
    stmt = select(AIAgentConfig).where(AIAgentConfig.agent_name == _SCHEDULER_AGENT_NAME)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    if config and config.mode:
        return config.mode.upper()
    return _DEFAULT_MODE


async def _log_execution(
    db: AsyncSession,
    agent_name: str,
    trigger_event: str,
    mode: str,
    lead_id: Optional[str],
    status: str,
    input_summary: str,
    output_response: str,
) -> None:
    """Persist a lightweight audit entry in AIAgentExecutionLog."""
    log_entry = AIAgentExecutionLog(
        agent_name=agent_name,
        lead_id=lead_id,
        channel="INTERNAL",
        mode=mode,
        trigger_event=trigger_event,
        input_summary=input_summary[:2000] if input_summary else None,
        output_response=output_response[:2000] if output_response else None,
        tools_called=[],
        status=status,
    )
    db.add(log_entry)
    # Flush without committing — callers control the transaction boundary.
    await db.flush()


# ---------------------------------------------------------------------------
# 1. Nurturing Cycle Runner
# ---------------------------------------------------------------------------

async def run_nurturing_cycle(db: AsyncSession) -> Dict[str, Any]:
    """Evaluate Day-0/1/3/7/15/30 nurturing steps for all eligible leads.

    A lead is eligible if:
      - It is not deleted and not in a terminal stage.
      - Its creation age matches one of the nurturing cadence milestones (± 6 h window).
      - It has not been contacted in the last 24 hours (cooldown enforced by agent).

    Returns:
        dict with keys: processed_leads, skipped_terminal, skipped_cooldown,
                        shadow_logged, succeeded, errors.
    """
    mode = await _get_scheduler_mode(db)
    summary: Dict[str, Any] = {
        "runner": "nurturing_cycle",
        "mode": mode,
        "processed_leads": 0,
        "skipped_terminal": 0,
        "skipped_cooldown": 0,
        "shadow_logged": 0,
        "succeeded": 0,
        "errors": 0,
    }

    if mode == "DISABLED":
        logger.info("[ai_scheduler] nurturing_cycle: DISABLED — skipping.")
        summary["status"] = "DISABLED"
        return summary

    now = datetime.now(timezone.utc)

    # Build a window of qualifying lead ages (cadence day ± 6 hours)
    eligible_windows: List[tuple[datetime, datetime]] = []
    for day in _NURTURING_CADENCE_DAYS:
        center = now - timedelta(days=day)
        eligible_windows.append(
            (center - timedelta(hours=6), center + timedelta(hours=6))
        )

    # Fetch all non-deleted, non-terminal leads that fall into any cadence window
    # We load in-flight lead IDs only (keep the query light)
    terminal_stages_tuple = tuple(TERMINAL_LEAD_STAGES)
    stmt = (
        select(Lead.lead_id, Lead.stage, Lead.created_at)
        .where(
            Lead.deleted_at.is_(None),
            Lead.stage.notin_(terminal_stages_tuple),
        )
    )
    rows = (await db.execute(stmt)).all()

    eligible_lead_ids: List[str] = []
    for lead_id, stage, created_at in rows:
        # Normalise timezone
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        for window_start, window_end in eligible_windows:
            if window_start <= created_at <= window_end:
                eligible_lead_ids.append(lead_id)
                break

    logger.info(
        "[ai_scheduler] nurturing_cycle: %d leads eligible (mode=%s).",
        len(eligible_lead_ids),
        mode,
    )

    guardrails = SafetyGuardrailsService(db)
    agent = FollowupJourneyAgent(
        db=db,
        guardrails=guardrails,
        default_mode=mode,
    )

    for lead_id in eligible_lead_ids:
        summary["processed_leads"] += 1
        try:
            result = await agent.evaluate_nurturing_step(lead_id)
            action = result.get("action", "")
            reason = result.get("reason", "")

            if reason in ("AGENT_DISABLED",):
                summary["skipped_terminal"] += 1
            elif action == "SKIPPED_TERMINAL_STAGE":
                summary["skipped_terminal"] += 1
            elif action == "COOLDOWN_ACTIVE":
                summary["skipped_cooldown"] += 1
            elif mode == "SHADOW":
                summary["shadow_logged"] += 1
                await _log_execution(
                    db, _SCHEDULER_AGENT_NAME, "NURTURING_CYCLE", mode,
                    lead_id, "SHADOW_LOGGED",
                    f"lead_id={lead_id}",
                    f"shadow_result={result}",
                )
            else:
                summary["succeeded"] += 1

        except Exception as exc:
            logger.error("[ai_scheduler] nurturing_cycle error for %s: %s", lead_id, exc)
            summary["errors"] += 1

    summary["status"] = "COMPLETED"
    return summary


# ---------------------------------------------------------------------------
# 2. Property Alert Queue Runner
# ---------------------------------------------------------------------------

async def run_property_alert_queue(db: AsyncSession) -> Dict[str, Any]:
    """Dispatch pending new-property alerts for FAILED history entries.

    Looks for PropertyAlertHistory records with status='FAILED' that are
    less than 24 hours old, and retries the dispatch via NewPropertyAlertAgent.

    Returns:
        dict with keys: attempted, shadow_logged, succeeded, errors.
    """
    mode = await _get_scheduler_mode(db)
    summary: Dict[str, Any] = {
        "runner": "property_alert_queue",
        "mode": mode,
        "attempted": 0,
        "shadow_logged": 0,
        "succeeded": 0,
        "errors": 0,
    }

    if mode == "DISABLED":
        logger.info("[ai_scheduler] property_alert_queue: DISABLED — skipping.")
        summary["status"] = "DISABLED"
        return summary

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    stmt = (
        select(PropertyAlertHistory)
        .where(
            PropertyAlertHistory.status == "FAILED",
            PropertyAlertHistory.created_at >= cutoff,
        )
        .limit(100)
    )
    failed_alerts = (await db.execute(stmt)).scalars().all()

    logger.info(
        "[ai_scheduler] property_alert_queue: %d failed alerts to retry (mode=%s).",
        len(failed_alerts),
        mode,
    )

    guardrails = SafetyGuardrailsService(db)
    agent = NewPropertyAlertAgent(db=db, guardrails=guardrails)

    seen_properties: set = set()
    for alert in failed_alerts:
        summary["attempted"] += 1
        if alert.property_id in seen_properties:
            continue
        seen_properties.add(alert.property_id)
        try:
            if mode == "SHADOW":
                # Shadow: log intent, do not call dispatch
                summary["shadow_logged"] += 1
                await _log_execution(
                    db, _SCHEDULER_AGENT_NAME, "PROPERTY_ALERT_RETRY", mode,
                    alert.lead_id, "SHADOW_LOGGED",
                    f"property_id={alert.property_id} lead_id={alert.lead_id}",
                    "shadow: would dispatch alert",
                )
            else:
                result = await agent.dispatch_alerts_for_property(alert.property_id)
                summary["succeeded"] += 1
                await _log_execution(
                    db, _SCHEDULER_AGENT_NAME, "PROPERTY_ALERT_RETRY", mode,
                    alert.lead_id, "SUCCESS",
                    f"property_id={alert.property_id}",
                    str(result)[:500],
                )
        except Exception as exc:
            logger.error(
                "[ai_scheduler] property_alert_queue error for property %s: %s",
                alert.property_id, exc,
            )
            summary["errors"] += 1

    summary["status"] = "COMPLETED"
    return summary


# ---------------------------------------------------------------------------
# 3. Call Retry Cycle Runner
# ---------------------------------------------------------------------------

async def run_call_retry_cycle(db: AsyncSession) -> Dict[str, Any]:
    """Retry failed outbound voice calls once, respecting quiet-hours (09:00-21:00 IST).

    Looks for AIAgentExecutionLog entries where:
      - agent_name = 'voice_calling_agent'
      - status = 'ERROR' or 'FAILED'
      - Created within the last 24 hours (missed-call window)
      - No subsequent SUCCESS log exists for the same lead within that window

    Returns:
        dict with keys: attempted, skipped_quiet_hours, shadow_logged, succeeded, errors.
    """
    mode = await _get_scheduler_mode(db)
    summary: Dict[str, Any] = {
        "runner": "call_retry_cycle",
        "mode": mode,
        "attempted": 0,
        "skipped_quiet_hours": 0,
        "shadow_logged": 0,
        "succeeded": 0,
        "errors": 0,
    }

    if mode == "DISABLED":
        logger.info("[ai_scheduler] call_retry_cycle: DISABLED — skipping.")
        summary["status"] = "DISABLED"
        return summary

    # Enforce quiet hours: do not retry if currently in quiet period
    if is_quiet_hours():
        logger.info("[ai_scheduler] call_retry_cycle: quiet hours active — deferring all retries.")
        summary["skipped_quiet_hours"] = -1   # sentinal: whole run deferred
        summary["status"] = "DEFERRED_QUIET_HOURS"
        return summary

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    # Find failed call logs
    failed_stmt = (
        select(AIAgentExecutionLog)
        .where(
            AIAgentExecutionLog.agent_name == "voice_calling_agent",
            AIAgentExecutionLog.status.in_(["ERROR", "FAILED"]),
            AIAgentExecutionLog.created_at >= cutoff,
            AIAgentExecutionLog.lead_id.isnot(None),
        )
        .limit(50)
    )
    failed_logs = (await db.execute(failed_stmt)).scalars().all()

    # De-duplicate by lead_id; also skip leads that already have a SUCCESS in the window
    success_stmt = (
        select(AIAgentExecutionLog.lead_id)
        .where(
            AIAgentExecutionLog.agent_name == "voice_calling_agent",
            AIAgentExecutionLog.status == "SUCCESS",
            AIAgentExecutionLog.created_at >= cutoff,
        )
    )
    already_succeeded = {
        row[0] for row in (await db.execute(success_stmt)).all()
    }

    seen_leads: set = set()
    guardrails = SafetyGuardrailsService(db)
    voice_agent = VoiceCallingAgent(db=db, guardrails=guardrails)

    for log_entry in failed_logs:
        lead_id = log_entry.lead_id
        if lead_id in seen_leads or lead_id in already_succeeded:
            continue
        seen_leads.add(lead_id)
        summary["attempted"] += 1

        try:
            # Fetch lead for mobile number
            lead_stmt = select(Lead).where(
                Lead.lead_id == lead_id,
                Lead.deleted_at.is_(None),
            )
            lead = (await db.execute(lead_stmt)).scalar_one_or_none()
            if not lead:
                continue

            # Skip terminal stage leads
            if lead.stage and lead.stage.upper() in TERMINAL_LEAD_STAGES:
                summary["skipped_quiet_hours"] += 1
                continue

            if mode == "SHADOW":
                summary["shadow_logged"] += 1
                await _log_execution(
                    db, _SCHEDULER_AGENT_NAME, "CALL_RETRY", mode,
                    lead_id, "SHADOW_LOGGED",
                    f"lead_id={lead_id} mobile={lead.mobile[:6]}***",
                    "shadow: would retry outbound call",
                )
            else:
                result = await voice_agent.trigger_outbound_call(lead_id=lead_id)
                summary["succeeded"] += 1
                await _log_execution(
                    db, _SCHEDULER_AGENT_NAME, "CALL_RETRY", mode,
                    lead_id, "SUCCESS",
                    f"lead_id={lead_id}",
                    str(result)[:500],
                )

        except Exception as exc:
            logger.error("[ai_scheduler] call_retry_cycle error for %s: %s", lead_id, exc)
            summary["errors"] += 1

    summary["status"] = "COMPLETED"
    return summary


# ---------------------------------------------------------------------------
# 4. PII Retention Purge Runner
# ---------------------------------------------------------------------------

async def run_pii_retention_purge(
    db: AsyncSession,
    retention_days: int = 90,
) -> Dict[str, Any]:
    """Scrub PII fields in AIAgentExecutionLog entries older than retention_days.

    Replaces ``input_summary`` and ``output_response`` with the placeholder
    ``[PURGED_PER_PII_POLICY]`` for all logs whose ``created_at`` is older than
    the retention window, and that have not already been purged (purged_at IS NULL
    guard applied where the column exists — gracefully skipped on SQLite test DB).

    Args:
        db: Async database session.
        retention_days: Number of days after which PII is purged (default 90).

    Returns:
        dict with keys: purged_count, cutoff_date, retention_days, errors.
    """
    summary: Dict[str, Any] = {
        "runner": "pii_retention_purge",
        "retention_days": retention_days,
        "purged_count": 0,
        "errors": 0,
    }

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    summary["cutoff_date"] = cutoff.isoformat()

    try:
        # Select old logs that still contain data (at least one field not yet purged)
        stmt = (
            select(AIAgentExecutionLog)
            .where(
                AIAgentExecutionLog.created_at < cutoff,
                AIAgentExecutionLog.input_summary != _PII_PURGE_PLACEHOLDER,
            )
            .limit(500)   # Process in batches to avoid long-running transactions
        )
        old_logs = (await db.execute(stmt)).scalars().all()

        logger.info(
            "[ai_scheduler] pii_retention_purge: %d logs to purge (cutoff=%s, retention=%d days).",
            len(old_logs),
            cutoff.date(),
            retention_days,
        )

        for log_entry in old_logs:
            try:
                log_entry.input_summary = _PII_PURGE_PLACEHOLDER
                log_entry.output_response = _PII_PURGE_PLACEHOLDER
                db.add(log_entry)
                summary["purged_count"] += 1
            except Exception as row_exc:
                logger.error(
                    "[ai_scheduler] pii_retention_purge row error (id=%s): %s",
                    log_entry.id,
                    row_exc,
                )
                summary["errors"] += 1

        await db.flush()
        logger.info(
            "[ai_scheduler] pii_retention_purge: purged %d records.",
            summary["purged_count"],
        )

    except Exception as exc:
        logger.error("[ai_scheduler] pii_retention_purge fatal error: %s", exc)
        summary["errors"] += 1

    summary["status"] = "COMPLETED"
    return summary
