import pytest
from datetime import datetime, timezone, timedelta
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.models.ai_agents import AIAgentConfig, CustomerConsent, AIAgentExecutionLog, PropertyAlertHistory


@pytest.mark.asyncio
async def test_opt_out_blocks_messaging(db_session):
    guard = SafetyGuardrailsService(db_session)
    await guard.register_consent("919876543210", "WHATSAPP", is_opted_in=False, source="INCOMING_SMS", reason="STOP")
    allowed = await guard.verify_consent("919876543210", "WHATSAPP")
    assert allowed is False


@pytest.mark.asyncio
async def test_opt_in_allows_messaging(db_session):
    guard = SafetyGuardrailsService(db_session)
    await guard.register_consent("919876543210", "WHATSAPP", is_opted_in=True, source="META_FORM")
    allowed = await guard.verify_consent("919876543210", "WHATSAPP")
    assert allowed is True


@pytest.mark.asyncio
async def test_unregistered_consent_defaults_to_false(db_session):
    guard = SafetyGuardrailsService(db_session)
    allowed = await guard.verify_consent("919800000000", "WHATSAPP")
    assert allowed is False


@pytest.mark.asyncio
async def test_pii_masking():
    guard = SafetyGuardrailsService(None)
    masked = guard.mask_pii("919829012345")
    assert masked == "9198****2345"

    masked_text = guard.mask_pii("Contact user at 919829012345 or user@example.com for site visit")
    assert "9198****2345" in masked_text
    assert "u***@example.com" in masked_text


@pytest.mark.asyncio
async def test_agent_mode_defaults_and_override(db_session):
    guard = SafetyGuardrailsService(db_session)
    # Unconfigured agent defaults to SHADOW
    mode = await guard.get_agent_mode("unseeded_agent")
    assert mode == "SHADOW"

    # Set mode to LIVE
    await guard.set_agent_mode("lead_qualification", "LIVE")
    mode_live = await guard.get_agent_mode("lead_qualification")
    assert mode_live == "LIVE"

    # Change mode to DISABLED
    await guard.set_agent_mode("lead_qualification", "DISABLED")
    mode_disabled = await guard.get_agent_mode("lead_qualification")
    assert mode_disabled == "DISABLED"


@pytest.mark.asyncio
async def test_rate_limiting_sliding_window(db_session):
    guard = SafetyGuardrailsService(db_session)
    mobile = "919829123456"
    channel = "WHATSAPP"

    # Under rate limit
    can_send = await guard.check_rate_limit(mobile, channel, max_per_hour=3)
    assert can_send is True

    # Record 3 dispatches
    for i in range(3):
        await guard.record_execution_log(
            agent_name="test_agent",
            lead_id=mobile,
            channel=channel,
            mode="LIVE",
            status="SUCCESS",
            input_summary=f"Message {i}",
        )

    # Exceeding limit
    can_send_now = await guard.check_rate_limit(mobile, channel, max_per_hour=3)
    assert can_send_now is False

    # Higher threshold allows
    can_send_higher = await guard.check_rate_limit(mobile, channel, max_per_hour=5)
    assert can_send_higher is True


@pytest.mark.asyncio
async def test_duplicate_property_alert_cooldown(db_session):
    guard = SafetyGuardrailsService(db_session)
    lead_id = "OB-2026-TEST01"
    prop_id = "OP-2026-00099"

    # Not duplicate initially
    is_dup = await guard.is_duplicate_property_alert(lead_id, prop_id, cooldown_days=7)
    assert is_dup is False

    # Dispatch an alert
    alert = PropertyAlertHistory(
        lead_id=lead_id,
        property_id=prop_id,
        channel="WHATSAPP",
        status="SENT",
        sent_at=datetime.now(timezone.utc),
    )
    db_session.add(alert)
    await db_session.commit()

    # Now duplicate within cooldown
    is_dup_now = await guard.is_duplicate_property_alert(lead_id, prop_id, cooldown_days=7)
    assert is_dup_now is True


@pytest.mark.asyncio
async def test_record_execution_log(db_session):
    guard = SafetyGuardrailsService(db_session)
    log = await guard.record_execution_log(
        agent_name="lead_qualification",
        lead_id="OB-2026-000001",
        channel="WHATSAPP",
        mode="SHADOW",
        trigger_event="NEW_LEAD",
        input_summary="Lead looking for 3BHK in Vaishali Nagar with phone 919829012345",
        output_response="Hello, we have 2 matching villas",
        tools_called=[{"name": "search_properties", "args": {"bhk": 3}}],
        status="SHADOW_LOGGED",
    )
    assert log.id is not None
    assert log.agent_name == "lead_qualification"
    assert log.status == "SHADOW_LOGGED"
    # Verify PII masking applied in execution log
    assert "9198****2345" in log.input_summary
