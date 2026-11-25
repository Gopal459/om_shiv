import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from app.models.ai_agents import (
    AIAgentConfig,
    CustomerConsent,
    AIApprovalQueue,
    AIAgentExecutionLog,
    PropertyAlertHistory,
)


@pytest.mark.asyncio
async def test_ai_agent_models_creation(db_session):
    config = AIAgentConfig(
        agent_name="property_search",
        display_name="AI Property Search Agent",
        mode="SHADOW",
        rate_limit_per_hour=10,
        requires_hitl=False,
        is_customer_facing=False,
        extra_config={"temperature": 0.2},
    )
    db_session.add(config)
    await db_session.commit()

    fetched = (
        await db_session.execute(
            select(AIAgentConfig).where(AIAgentConfig.agent_name == "property_search")
        )
    ).scalar_one_or_none()
    assert fetched is not None
    assert fetched.mode == "SHADOW"
    assert fetched.rate_limit_per_hour == 10
    assert fetched.extra_config == {"temperature": 0.2}


@pytest.mark.asyncio
async def test_customer_consent_model(db_session):
    consent = CustomerConsent(
        mobile="919829012345",
        channel="WHATSAPP",
        is_opted_in=True,
        consent_source="WEB_FORM",
        opted_in_at=datetime.now(timezone.utc),
    )
    db_session.add(consent)
    await db_session.commit()

    fetched = (
        await db_session.execute(
            select(CustomerConsent).where(CustomerConsent.mobile == "919829012345")
        )
    ).scalar_one_or_none()
    assert fetched is not None
    assert fetched.channel == "WHATSAPP"
    assert fetched.is_opted_in is True
    assert fetched.consent_source == "WEB_FORM"


@pytest.mark.asyncio
async def test_ai_approval_queue_model(db_session):
    item = AIApprovalQueue(
        agent_name="lead_qualification",
        lead_id="OB-2026-000001",
        action_type="STAGE_CHANGE_LOST",
        proposed_payload={"reason": "Customer budget too low"},
        status="PENDING",
    )
    db_session.add(item)
    await db_session.commit()

    assert item.id is not None
    fetched = await db_session.get(AIApprovalQueue, item.id)
    assert fetched is not None
    assert fetched.agent_name == "lead_qualification"
    assert fetched.status == "PENDING"
    assert fetched.proposed_payload["reason"] == "Customer budget too low"


@pytest.mark.asyncio
async def test_ai_agent_execution_log_model(db_session):
    log = AIAgentExecutionLog(
        agent_name="property_search",
        lead_id="OB-2026-000001",
        channel="WHATSAPP",
        mode="SHADOW",
        trigger_event="INCOMING_MESSAGE",
        input_summary="Looking for 3 BHK flat",
        output_response="Found 2 matching properties",
        tools_called=[{"name": "search_properties", "args": {"bhk": 3}}],
        status="SHADOW_LOGGED",
    )
    db_session.add(log)
    await db_session.commit()

    assert log.id is not None
    fetched = await db_session.get(AIAgentExecutionLog, log.id)
    assert fetched is not None
    assert fetched.status == "SHADOW_LOGGED"
    assert len(fetched.tools_called) == 1


@pytest.mark.asyncio
async def test_property_alert_history_model(db_session):
    alert = PropertyAlertHistory(
        lead_id="OB-2026-000001",
        property_id="OP-2026-00001",
        channel="WHATSAPP",
        status="SENT",
    )
    db_session.add(alert)
    await db_session.commit()

    assert alert.id is not None
    fetched = await db_session.get(PropertyAlertHistory, alert.id)
    assert fetched is not None
    assert fetched.lead_id == "OB-2026-000001"
    assert fetched.property_id == "OP-2026-00001"
    assert fetched.status == "SENT"
