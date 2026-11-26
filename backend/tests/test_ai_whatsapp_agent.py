import pytest
from app.services.ai.agents.whatsapp_agent import WhatsAppAgent
from app.models.ai_agents import AIAgentConfig, AIAgentExecutionLog, CustomerConsent
from app.models.properties import Property, PropResidentialFlat
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.notifications.whatsapp_gateway import WhatsAppGateway
from tests.ai_mocks import MockAIClientService


@pytest.mark.asyncio
async def test_whatsapp_stop_unsubscribes_instantly(db_session):
    agent = WhatsAppAgent(db_session)
    res = await agent.handle_incoming_message("9829055555", "STOP")
    assert res["status"] == "OPTED_OUT"
    assert res["dispatched_live"] is False

    consent = (await db_session.execute(CustomerConsent.select().where(CustomerConsent.mobile == "9829055555"))).scalar_one_or_none()
    assert consent is not None
    assert consent.is_opted_in is False


@pytest.mark.asyncio
async def test_whatsapp_various_opt_out_phrases(db_session):
    agent = WhatsAppAgent(db_session)
    for phrase in ["UNSUBSCRIBE", "BAND KARO", "ROKO", "OPT OUT", "optout"]:
        mobile = f"98290{hash(phrase) % 100000:05d}"
        res = await agent.handle_incoming_message(mobile, phrase)
        assert res["status"] == "OPTED_OUT"
        assert res["dispatched_live"] is False

        consent = (await db_session.execute(CustomerConsent.select().where(CustomerConsent.mobile == mobile))).scalar_one_or_none()
        assert consent is not None
        assert consent.is_opted_in is False


@pytest.mark.asyncio
async def test_whatsapp_inbound_does_not_silently_reopt_in_after_stop(db_session):
    agent = WhatsAppAgent(db_session)
    mobile = "9829033333"

    # 1. User unsubscribes
    res1 = await agent.handle_incoming_message(mobile, "STOP")
    assert res1["status"] == "OPTED_OUT"

    consent1 = (await db_session.execute(CustomerConsent.select().where(CustomerConsent.mobile == mobile))).scalar_one_or_none()
    assert consent1 is not None
    assert consent1.is_opted_in is False

    # 2. User texts a regular message - must NOT silently re-opt in
    res2 = await agent.handle_incoming_message(mobile, "Why did you send this message?")
    assert res2["status"] == "SUCCESS"

    consent2 = (await db_session.execute(CustomerConsent.select().where(CustomerConsent.mobile == mobile))).scalar_one_or_none()
    assert consent2 is not None
    assert consent2.is_opted_in is False  # Must remain False!

    # 3. User texts explicit re-subscribe keyword - NOW re-opts in
    res3 = await agent.handle_incoming_message(mobile, "START")
    assert res3["status"] == "SUCCESS"

    consent3 = (await db_session.execute(CustomerConsent.select().where(CustomerConsent.mobile == mobile))).scalar_one_or_none()
    assert consent3 is not None
    assert consent3.is_opted_in is True


@pytest.mark.asyncio
async def test_whatsapp_shadow_mode_does_not_send_live_message(db_session):
    cfg = AIAgentConfig(agent_name="whatsapp_agent", display_name="WhatsApp", mode="SHADOW")
    db_session.add(cfg)
    await db_session.commit()

    agent = WhatsAppAgent(db_session)
    res = await agent.handle_incoming_message("9829055555", "Hello, do you have flats in Alwar?")
    assert res["mode"] == "SHADOW"
    assert res["dispatched_live"] is False
    assert res["status"] == "SUCCESS"
    assert "reply_text" in res


@pytest.mark.asyncio
async def test_whatsapp_live_mode_sends_live_message(db_session):
    cfg = AIAgentConfig(agent_name="whatsapp_agent", display_name="WhatsApp", mode="LIVE")
    db_session.add(cfg)
    await db_session.commit()

    mock_gateway = WhatsAppGateway()
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "reply_text": "Namaste! Yes, we have 2 BHK and 3 BHK flats in Alwar.",
        "intent": "PROPERTY_SEARCH",
        "opt_out_detected": False,
        "recommended_property_ids": [],
        "requires_agent_followup": False,
    })

    agent = WhatsAppAgent(db_session, ai_client=mock_ai, gateway=mock_gateway)
    res = await agent.handle_incoming_message("9829055555", "Hello, do you have flats in Alwar?")
    assert res["mode"] == "LIVE"
    assert res["dispatched_live"] is True
    assert res["status"] == "SUCCESS"
    assert len(mock_gateway.sent_messages) > 0
    assert mock_gateway.sent_messages[-1]["mobile"] in ("9829055555", "919829055555")


@pytest.mark.asyncio
async def test_whatsapp_disabled_mode_blocks_execution(db_session):
    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("whatsapp_agent", "DISABLED")

    agent = WhatsAppAgent(db_session, guardrails=guardrails)
    res = await agent.handle_incoming_message("9829055555", "Hello")
    assert res["status"] == "BLOCKED_FLAG"
    assert res["dispatched_live"] is False


@pytest.mark.asyncio
async def test_whatsapp_outbound_requires_consent(db_session):
    cfg = AIAgentConfig(agent_name="whatsapp_agent", display_name="WhatsApp", mode="LIVE")
    db_session.add(cfg)
    await db_session.commit()

    agent = WhatsAppAgent(db_session)
    # Proactive outbound without prior consent
    res = await agent.dispatch_outbound_message("9829011111", "Exclusive new villa launch in Jaipur!")
    assert res["status"] == "BLOCKED_CONSENT"
    assert res["dispatched_live"] is False

    # Grant consent
    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.register_consent("9829011111", "WHATSAPP", is_opted_in=True, source="WEB_FORM")

    # Now outbound should succeed
    res2 = await agent.dispatch_outbound_message("9829011111", "Exclusive new villa launch in Jaipur!")
    assert res2["status"] == "SUCCESS"
    assert res2["dispatched_live"] is True


@pytest.mark.asyncio
async def test_whatsapp_property_search_integration(db_session):
    # Seed matching property in database
    prop = Property(
        property_id="OP-2026-00001",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="2 BHK Flat in Alwar",
        city="Alwar",
        locality="Alwar Bypass",
        pincode="301001",
        expected_price=2800000,
        owner_name="Verma Ji",
        owner_mobile="9829022222",
        is_live=True,
    )
    flat = PropResidentialFlat(
        property=prop,
        bhk=2,
        rooms=2,
        bathrooms=2,
        super_area=1000,
        carpet_area=850,
    )
    db_session.add(prop)
    db_session.add(flat)
    await db_session.commit()

    mock_ai = MockAIClientService()
    # First response: parsed search filters for PropertySearchAgent
    # Second response: WhatsApp conversational reply
    mock_ai.set_canned_responses([
        {
            "city": "Alwar",
            "bhk": 2,
            "max_price": 3000000,
            "property_type": "FLAT",
        },
        {
            "reply_text": "Here are some verified 2 BHK flats in Alwar matching your search: OP-2026-00001",
            "intent": "PROPERTY_SEARCH",
            "opt_out_detected": False,
            "recommended_property_ids": ["OP-2026-00001"],
            "requires_agent_followup": False,
        },
    ])

    agent = WhatsAppAgent(db_session, ai_client=mock_ai)
    res = await agent.handle_incoming_message("9829055555", "Show me 2 BHK flats in Alwar under 30 Lakh")
    assert res["status"] == "SUCCESS"
    assert "reply_text" in res
    assert "recommended_property_ids" in res
    assert "OP-2026-00001" in res["recommended_property_ids"]


@pytest.mark.asyncio
async def test_whatsapp_webhook_get_challenge(test_client):
    res = await test_client.get(
        "/v1/ai/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "12345678",
            "hub.verify_token": "omshiv_meta_secret_token",
        },
    )
    assert res.status_code == 200
    assert int(res.text) == 12345678


@pytest.mark.asyncio
async def test_whatsapp_webhook_post_incoming(test_client, db_session):
    payload = {
        "mobile": "9829022222",
        "text": "Hello, need details about plots in Neemrana",
    }
    res = await test_client.post("/v1/ai/webhooks/whatsapp", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("SUCCESS", "SHADOW_LOGGED")
    assert data["dispatched_live"] is False  # Default mode is SHADOW
