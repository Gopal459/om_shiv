"""Unit tests for the AI background scheduler runners (Task 16).

All tests use an in-memory SQLite database (via conftest.py ``db_session``
fixture) and mock external agent calls so the suite is fully deterministic
and incurs zero live API cost.

Coverage:
  - run_nurturing_cycle: Eligible lead triggers agent; terminal leads skipped;
    SHADOW mode logs without calling live dispatch; DISABLED mode skips all.
  - run_property_alert_queue: Failed alert retried in LIVE mode; shadow-logged in SHADOW.
  - run_call_retry_cycle: Failed voice log retried; quiet-hours defers entire run.
  - run_pii_retention_purge: Old logs scrubbed; recent logs untouched; idempotent.
"""

from __future__ import annotations

import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

os.environ.setdefault("PYTEST_CURRENT_TEST", "true")
os.environ.setdefault("TESTING", "true")

from app.workers.ai_scheduler import (
    run_nurturing_cycle,
    run_property_alert_queue,
    run_call_retry_cycle,
    run_pii_retention_purge,
    _PII_PURGE_PLACEHOLDER,
)
from app.models.ai_agents import AIAgentConfig, AIAgentExecutionLog, PropertyAlertHistory
from app.models.leads import Lead


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_lead(
    lead_id: str,
    stage: str = "CONTACTED",
    days_ago: float = 3.5,
    mobile: str = "919829000001",
) -> Lead:
    """Create a Lead fixture with created_at set to `days_ago` days in the past."""
    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return Lead(
        lead_id=lead_id,
        full_name="Test Lead",
        mobile=mobile,
        stage=stage,
        created_at=created,
        updated_at=created,
        untouched_timer_start=created,
    )


def _make_config(agent_name: str, mode: str) -> AIAgentConfig:
    return AIAgentConfig(
        agent_name=agent_name,
        display_name=f"{agent_name} (test)",
        mode=mode,
    )


def _make_execution_log(
    agent_name: str,
    lead_id: str,
    status: str,
    days_ago: float = 0,
) -> AIAgentExecutionLog:
    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return AIAgentExecutionLog(
        agent_name=agent_name,
        lead_id=lead_id,
        channel="INTERNAL",
        mode="LIVE",
        trigger_event="TEST",
        input_summary="test input",
        output_response="test output",
        tools_called=[],
        status=status,
        created_at=created,
    )


# ===========================================================================
# Tests: run_nurturing_cycle
# ===========================================================================

class TestRunNurturingCycle:
    """Tests for run_nurturing_cycle."""

    @pytest.mark.asyncio
    async def test_disabled_mode_skips_all(self, db_session):
        """DISABLED mode should return immediately without processing any leads."""
        db_session.add(_make_config("ai_scheduler", "DISABLED"))
        await db_session.commit()

        result = await run_nurturing_cycle(db_session)

        assert result["status"] == "DISABLED"
        assert result["processed_leads"] == 0

    @pytest.mark.asyncio
    async def test_no_leads_returns_zero(self, db_session):
        """With no leads in DB, processed_leads should be 0."""
        db_session.add(_make_config("ai_scheduler", "SHADOW"))
        await db_session.commit()

        with patch(
            "app.workers.ai_scheduler.FollowupJourneyAgent.evaluate_nurturing_step",
            new_callable=AsyncMock,
            return_value={"success": True, "action": "SHADOW_LOGGED"},
        ):
            result = await run_nurturing_cycle(db_session)

        assert result["status"] == "COMPLETED"
        assert result["processed_leads"] == 0

    @pytest.mark.asyncio
    async def test_eligible_lead_triggers_agent(self, db_session):
        """A lead created exactly 3 days ago should be evaluated."""
        db_session.add(_make_config("ai_scheduler", "SHADOW"))
        lead = _make_lead("OB-SCHED-001", days_ago=3.1)  # ~3 days → DAY_3 window
        db_session.add(lead)
        await db_session.commit()

        mock_result = {"success": True, "action": "SHADOW_LOGGED"}
        with patch(
            "app.workers.ai_scheduler.FollowupJourneyAgent.evaluate_nurturing_step",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_eval:
            result = await run_nurturing_cycle(db_session)

        assert result["processed_leads"] >= 1
        mock_eval.assert_called()

    @pytest.mark.asyncio
    async def test_terminal_stage_lead_skipped(self, db_session):
        """Leads in LOST/WON/BOOKED stages must be skipped by the scheduler query."""
        db_session.add(_make_config("ai_scheduler", "SHADOW"))
        for stage in ("LOST", "WON", "BOOKED"):
            db_session.add(_make_lead(f"OB-TERM-{stage}", stage=stage, days_ago=3.0))
        await db_session.commit()

        result = await run_nurturing_cycle(db_session)

        # Terminal leads are filtered out by SQL `notin_` — none should be processed
        assert result["processed_leads"] == 0

    @pytest.mark.asyncio
    async def test_shadow_mode_does_not_mutate_crm(self, db_session):
        """In SHADOW mode the agent is called but no live CRM write occurs."""
        db_session.add(_make_config("ai_scheduler", "SHADOW"))
        lead = _make_lead("OB-SHADOW-001", days_ago=1.1)
        db_session.add(lead)
        await db_session.commit()

        # Simulate agent returning SHADOW_LOGGED action
        with patch(
            "app.workers.ai_scheduler.FollowupJourneyAgent.evaluate_nurturing_step",
            new_callable=AsyncMock,
            return_value={"success": True, "action": "SHADOW_LOGGED"},
        ):
            result = await run_nurturing_cycle(db_session)

        assert result["succeeded"] == 0  # No live dispatch in SHADOW


# ===========================================================================
# Tests: run_property_alert_queue
# ===========================================================================

class TestRunPropertyAlertQueue:
    """Tests for run_property_alert_queue."""

    @pytest.mark.asyncio
    async def test_disabled_mode_skips(self, db_session):
        db_session.add(_make_config("ai_scheduler", "DISABLED"))
        await db_session.commit()

        result = await run_property_alert_queue(db_session)
        assert result["status"] == "DISABLED"

    @pytest.mark.asyncio
    async def test_failed_alert_retried_in_live_mode(self, db_session):
        """LIVE mode should attempt to dispatch the failed alert via the agent."""
        db_session.add(_make_config("ai_scheduler", "LIVE"))
        alert = PropertyAlertHistory(
            lead_id="OB-ALERT-001",
            property_id="PROP-001",
            channel="WHATSAPP",
            status="FAILED",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db_session.add(alert)
        await db_session.commit()

        with patch(
            "app.workers.ai_scheduler.NewPropertyAlertAgent.dispatch_alerts_for_property",
            new_callable=AsyncMock,
            return_value={"dispatched": 1},
        ):
            result = await run_property_alert_queue(db_session)

        assert result["succeeded"] >= 1
        assert result["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_failed_alert_shadow_logged_in_shadow_mode(self, db_session):
        """SHADOW mode must log but not dispatch."""
        db_session.add(_make_config("ai_scheduler", "SHADOW"))
        alert = PropertyAlertHistory(
            lead_id="OB-SHADOW-002",
            property_id="PROP-002",
            channel="WHATSAPP",
            status="FAILED",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db_session.add(alert)
        await db_session.commit()

        with patch(
            "app.workers.ai_scheduler.NewPropertyAlertAgent.dispatch_alerts_for_property",
            new_callable=AsyncMock,
        ) as mock_dispatch:
            result = await run_property_alert_queue(db_session)

        mock_dispatch.assert_not_called()
        assert result["shadow_logged"] >= 1


# ===========================================================================
# Tests: run_call_retry_cycle
# ===========================================================================

class TestRunCallRetryCycle:
    """Tests for run_call_retry_cycle."""

    @pytest.mark.asyncio
    async def test_disabled_mode_skips(self, db_session):
        db_session.add(_make_config("ai_scheduler", "DISABLED"))
        await db_session.commit()

        result = await run_call_retry_cycle(db_session)
        assert result["status"] == "DISABLED"

    @pytest.mark.asyncio
    async def test_quiet_hours_defers_entire_run(self, db_session):
        """When is_quiet_hours() returns True the entire retry run is deferred."""
        db_session.add(_make_config("ai_scheduler", "LIVE"))
        await db_session.commit()

        with patch("app.workers.ai_scheduler.is_quiet_hours", return_value=True):
            result = await run_call_retry_cycle(db_session)

        assert result["status"] == "DEFERRED_QUIET_HOURS"
        assert result["attempted"] == 0

    @pytest.mark.asyncio
    async def test_failed_call_retried_in_live_mode(self, db_session):
        """Failed voice call log should be retried during active hours."""
        db_session.add(_make_config("ai_scheduler", "LIVE"))
        lead = _make_lead("OB-VOICE-001", days_ago=0.5)
        db_session.add(lead)
        await db_session.flush()

        log = _make_execution_log("voice_calling_agent", "OB-VOICE-001", "ERROR", days_ago=0.3)
        db_session.add(log)
        await db_session.commit()

        with patch("app.workers.ai_scheduler.is_quiet_hours", return_value=False), \
             patch(
                 "app.workers.ai_scheduler.VoiceCallingAgent.trigger_outbound_call",
                 new_callable=AsyncMock,
                 return_value={"status": "INITIATED"},
             ):
            result = await run_call_retry_cycle(db_session)

        assert result["attempted"] >= 1
        assert result["succeeded"] >= 1

    @pytest.mark.asyncio
    async def test_already_succeeded_lead_not_retried(self, db_session):
        """Leads with a SUCCESS log in the window must not be retried."""
        db_session.add(_make_config("ai_scheduler", "LIVE"))
        lead = _make_lead("OB-VOICE-002", days_ago=0.5)
        db_session.add(lead)
        await db_session.flush()

        # Both failed and succeeded log in window
        db_session.add(_make_execution_log("voice_calling_agent", "OB-VOICE-002", "ERROR", 0.3))
        db_session.add(_make_execution_log("voice_calling_agent", "OB-VOICE-002", "SUCCESS", 0.1))
        await db_session.commit()

        with patch("app.workers.ai_scheduler.is_quiet_hours", return_value=False), \
             patch(
                 "app.workers.ai_scheduler.VoiceCallingAgent.trigger_outbound_call",
                 new_callable=AsyncMock,
             ) as mock_call:
            await run_call_retry_cycle(db_session)

        mock_call.assert_not_called()


# ===========================================================================
# Tests: run_pii_retention_purge
# ===========================================================================

class TestRunPiiRetentionPurge:
    """Tests for run_pii_retention_purge."""

    @pytest.mark.asyncio
    async def test_old_log_input_summary_purged(self, db_session):
        """Logs older than retention_days must have input_summary replaced."""
        old_log = _make_execution_log(
            "whatsapp_agent", "OB-OLD-001", "SUCCESS", days_ago=95
        )
        old_log.input_summary = "Customer phone: 9829012345 secret info"
        db_session.add(old_log)
        await db_session.commit()

        result = await run_pii_retention_purge(db_session, retention_days=90)

        assert result["purged_count"] >= 1
        await db_session.refresh(old_log)
        assert old_log.input_summary == _PII_PURGE_PLACEHOLDER
        assert old_log.output_response == _PII_PURGE_PLACEHOLDER

    @pytest.mark.asyncio
    async def test_recent_log_not_purged(self, db_session):
        """Logs within the retention window must NOT be touched."""
        recent_log = _make_execution_log(
            "whatsapp_agent", "OB-RECENT-001", "SUCCESS", days_ago=10
        )
        recent_log.input_summary = "Recent conversation"
        db_session.add(recent_log)
        await db_session.commit()

        result = await run_pii_retention_purge(db_session, retention_days=90)

        assert result["purged_count"] == 0
        await db_session.refresh(recent_log)
        assert recent_log.input_summary == "Recent conversation"

    @pytest.mark.asyncio
    async def test_purge_is_idempotent(self, db_session):
        """Running purge twice should not increase purged_count on second run."""
        old_log = _make_execution_log(
            "whatsapp_agent", "OB-IDEM-001", "SUCCESS", days_ago=100
        )
        old_log.input_summary = "Sensitive data"
        db_session.add(old_log)
        await db_session.commit()

        await run_pii_retention_purge(db_session, retention_days=90)
        result2 = await run_pii_retention_purge(db_session, retention_days=90)

        # On second run the placeholder IS the input_summary, so it's filtered out
        assert result2["purged_count"] == 0

    @pytest.mark.asyncio
    async def test_purge_returns_correct_summary_keys(self, db_session):
        result = await run_pii_retention_purge(db_session, retention_days=90)

        assert "purged_count" in result
        assert "retention_days" in result
        assert "cutoff_date" in result
        assert "status" in result
        assert result["retention_days"] == 90
        assert result["status"] == "COMPLETED"
