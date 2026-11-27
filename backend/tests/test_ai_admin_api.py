"""Unit & API tests for AI Agent Admin Control Center & HITL API (Task 17)."""

from __future__ import annotations

import os
import pytest
from sqlalchemy import select

os.environ.setdefault("PYTEST_CURRENT_TEST", "true")
os.environ.setdefault("TESTING", "true")

from app.models.ai_agents import AIAgentConfig, AIAgentExecutionLog, AIApprovalQueue
from app.models.leads import Lead


class TestAIAdminAgentsAPI:
    """Tests for GET /v1/ai/agents and PATCH /v1/ai/agents/{agent_name}."""

    @pytest.mark.asyncio
    async def test_get_ai_agents_auto_seeds_all_13(self, test_client):
        res = await test_client.get("/v1/ai/agents")
        assert res.status_code == 200
        data = res.json()
        assert "agents" in data
        assert len(data["agents"]) >= 13
        assert data["summary"]["total"] >= 13
        # Default safe trial mode is SHADOW (so is_active=True, mode=SHADOW)
        names = {a["agent_name"] for a in data["agents"]}
        assert "whatsapp_agent" in names
        assert "voice_calling_agent" in names
        assert "ai_scheduler" in names

    @pytest.mark.asyncio
    async def test_toggle_agent_active_inactive_and_mode(self, test_client, db_session):
        # First ensure seeded
        await test_client.get("/v1/ai/agents")

        # 1. Disable (Inactive) via is_active=False
        res_off = await test_client.patch(
            "/v1/ai/agents/whatsapp_agent",
            json={"is_active": False, "reason": "Maintenance pause"},
        )
        assert res_off.status_code == 200
        d_off = res_off.json()
        assert d_off["mode"] == "DISABLED"
        assert d_off["is_active"] is False

        # 2. Activate to LIVE via is_active=True
        res_on = await test_client.patch(
            "/v1/ai/agents/whatsapp_agent",
            json={"is_active": True, "active_mode": "LIVE", "rate_limit_per_hour": 25},
        )
        assert res_on.status_code == 200
        d_on = res_on.json()
        assert d_on["mode"] == "LIVE"
        assert d_on["is_active"] is True
        assert d_on["rate_limit_per_hour"] == 25

        # 3. Direct mode switch to SHADOW
        res_shadow = await test_client.patch(
            "/v1/ai/agents/whatsapp_agent",
            json={"mode": "SHADOW"},
        )
        assert res_shadow.status_code == 200
        assert res_shadow.json()["mode"] == "SHADOW"

        # Verify persisted in DB
        cfg = (
            await db_session.execute(
                select(AIAgentConfig).where(AIAgentConfig.agent_name == "whatsapp_agent")
            )
        ).scalar_one()
        assert cfg.mode == "SHADOW"
        assert cfg.rate_limit_per_hour == 25

    @pytest.mark.asyncio
    async def test_invalid_mode_returns_422(self, test_client):
        await test_client.get("/v1/ai/agents")
        res = await test_client.patch(
            "/v1/ai/agents/whatsapp_agent",
            json={"mode": "TURBO_MODE"},
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_unknown_agent_returns_404(self, test_client):
        res = await test_client.patch(
            "/v1/ai/agents/non_existent_agent",
            json={"is_active": False},
        )
        assert res.status_code == 404


class TestAIApprovalsAndLogsAPI:
    """Tests for HITL approvals, PII-masked logs, and consent endpoints."""

    @pytest.mark.asyncio
    async def test_hitl_approve_and_reject_flow(self, auth_client_md, db_session):
        lead1 = Lead(
            lead_id="OB-2026-HITL1",
            full_name="Test Buyer 1",
            mobile="919829011111",
            stage="CONNECTED",
        )
        lead2 = Lead(
            lead_id="OB-2026-HITL2",
            full_name="Test Buyer 2",
            mobile="919829022222",
            stage="CONNECTED",
        )
        db_session.add_all([lead1, lead2])
        await db_session.flush()

        q1 = AIApprovalQueue(
            id="appr-test-1",
            agent_name="sales_assistant",
            lead_id="OB-2026-HITL1",
            action_type="STAGE_CHANGE_LOST",
            proposed_payload={"reason": "Bought elsewhere"},
            status="PENDING",
        )
        q2 = AIApprovalQueue(
            id="appr-test-2",
            agent_name="lead_qualification",
            lead_id="OB-2026-HITL2",
            action_type="STAGE_CHANGE_LOST",
            proposed_payload={"reason": "Unreachable"},
            status="PENDING",
        )
        db_session.add_all([q1, q2])
        await db_session.commit()

        # List pending
        list_res = await auth_client_md.get("/v1/ai/approvals?status=PENDING")
        assert list_res.status_code == 200
        assert len(list_res.json()["approvals"]) == 2

        # Approve q1 -> updates lead1.stage to LOST
        appr_res = await auth_client_md.post(
            "/v1/ai/approvals/appr-test-1/approve",
            json={"review_note": "Confirmed with buyer"},
        )
        assert appr_res.status_code == 200
        assert appr_res.json()["status"] == "APPROVED"

        await db_session.refresh(lead1)
        assert lead1.stage == "LOST"

        # Reject q2 -> lead2.stage stays CONNECTED
        rej_res = await auth_client_md.post(
            "/v1/ai/approvals/appr-test-2/reject",
            json={"review_note": "Retry call once more"},
        )
        assert rej_res.status_code == 200
        assert rej_res.json()["status"] == "REJECTED"

        await db_session.refresh(lead2)
        assert lead2.stage == "CONNECTED"

    @pytest.mark.asyncio
    async def test_logs_mask_pii_and_consent_toggle(self, test_client, db_session):
        log_row = AIAgentExecutionLog(
            agent_name="whatsapp_agent",
            lead_id="OB-2026-LOG1",
            channel="WHATSAPP",
            mode="SHADOW",
            trigger_event="INCOMING_MESSAGE",
            input_summary="Call me on 9829012345 or email raj@example.com",
            output_response="Sent reply to 919829012345",
            status="SHADOW_LOGGED",
        )
        db_session.add(log_row)
        await db_session.commit()

        logs_res = await test_client.get("/v1/ai/logs?agent_name=whatsapp_agent")
        assert logs_res.status_code == 200
        logs = logs_res.json()["logs"]
        assert len(logs) == 1
        assert "9829012345" not in logs[0]["input_summary"]
        assert "raj@example.com" not in logs[0]["input_summary"]
        assert "****" in logs[0]["input_summary"]

        # Consent opt-out & opt-in
        out_res = await test_client.post(
            "/v1/ai/consent/opt-out",
            json={"mobile": "9829012345", "channel": "WHATSAPP", "reason": "Client requested"},
        )
        assert out_res.status_code == 200
        assert out_res.json()["is_opted_in"] is False

        check_res = await test_client.get("/v1/ai/consent/9829012345")
        assert check_res.status_code == 200
        assert check_res.json()["channels"]["WHATSAPP"]["is_opted_in"] is False

        in_res = await test_client.post(
            "/v1/ai/consent/opt-in",
            json={"mobile": "9829012345", "channel": "WHATSAPP"},
        )
        assert in_res.status_code == 200
        assert in_res.json()["is_opted_in"] is True
