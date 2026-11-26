import pytest
from app.services.ai.agents.meta_lead_agent import MetaLeadAgent
from app.models.leads import Lead
from app.models.ai_agents import CustomerConsent
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.services.ai.agents.lead_qualification_agent import LeadQualificationAgent
from tests.ai_mocks import MockAIClientService


@pytest.mark.asyncio
async def test_meta_lead_intake_creates_lead_and_consent(db_session):
    agent = MetaLeadAgent(db_session)
    payload = {
        "leadgen_id": "meta_123456",
        "full_name": "Anita Roy",
        "mobile": "9829044444",
        "city": "Jaipur",
        "ad_name": "Vaishali Nagar Project Launch",
    }
    res = await agent.process_meta_lead(payload)
    assert res["created"] is True

    lead = (await db_session.execute(Lead.select().where(Lead.mobile == "9829044444"))).scalar_one_or_none()
    assert lead is not None
    assert lead.source == "META_LEAD_ADS"

    consent = (await db_session.execute(CustomerConsent.select().where(CustomerConsent.mobile == "9829044444"))).scalar_one_or_none()
    assert consent is not None
    assert consent.is_opted_in is True


@pytest.mark.asyncio
async def test_meta_lead_deduplication(db_session):
    agent = MetaLeadAgent(db_session)
    payload = {
        "leadgen_id": "meta_repeat_1",
        "full_name": "Rohan Mehra",
        "mobile": "9829055555",
        "city": "Jaipur",
    }
    res1 = await agent.process_meta_lead(payload)
    assert res1["created"] is True

    # Repeat with same leadgen_id / idempotency
    res2 = await agent.process_meta_lead(payload)
    assert res2["created"] is False
    assert res2["is_duplicate"] is True
    assert res2["lead_id"] == res1["lead_id"]

    # Another payload with different leadgen_id but same mobile
    payload3 = {
        "leadgen_id": "meta_diff_id",
        "full_name": "Rohan Mehra",
        "mobile": "9829055555",
        "city": "Jaipur",
    }
    res3 = await agent.process_meta_lead(payload3)
    assert res3["created"] is False
    assert res3["is_duplicate"] is True
    assert res3["lead_id"] == res1["lead_id"]


@pytest.mark.asyncio
async def test_meta_lead_agent_disabled_flag(db_session):
    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("meta_lead_agent", "DISABLED")

    agent = MetaLeadAgent(db_session, guardrails=guardrails)
    payload = {
        "leadgen_id": "meta_dis_1",
        "full_name": "Dev Sharma",
        "mobile": "9829066666",
        "city": "Jaipur",
    }
    res = await agent.process_meta_lead(payload)
    assert res["created"] is False
    assert "disabled" in res["error"].lower()

    lead = (await db_session.execute(Lead.select().where(Lead.mobile == "9829066666"))).scalar_one_or_none()
    assert lead is None


@pytest.mark.asyncio
async def test_instagram_lead_intake(db_session):
    agent = MetaLeadAgent(db_session)
    payload = {
        "sender_id": "ig_987654",
        "full_name": "Pooja Verma",
        "mobile": "9829077777",
        "city": "Jaipur",
        "message": "Interested in 2 BHK flat near Mansarovar",
    }
    res = await agent.process_meta_lead(payload, channel="INSTAGRAM")
    assert res["created"] is True

    lead = (await db_session.execute(Lead.select().where(Lead.mobile == "9829077777"))).scalar_one_or_none()
    assert lead is not None
    assert lead.source == "INSTAGRAM"


@pytest.mark.asyncio
async def test_meta_lead_triggers_qualification(db_session):
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "budget_max": 9000000,
        "temperature": "HOT",
        "qualification_score": 95,
        "summary": "High budget buyer looking for 3 BHK flat",
    })
    qual_agent = LeadQualificationAgent(db_session, ai_client=mock_ai)
    agent = MetaLeadAgent(db_session, qualification_agent=qual_agent)
    payload = {
        "leadgen_id": "meta_qual_1",
        "full_name": "Suresh Gupta",
        "mobile": "9829088888",
        "city": "Jaipur",
        "questions": [
            {"question": "What is your budget?", "answer": "90 Lakhs"},
            {"question": "Preferred property type?", "answer": "3 BHK Apartment"},
        ],
    }
    res = await agent.process_meta_lead(payload)
    assert res["created"] is True
    assert res["qualification"] is not None
    assert res["qualification"]["temperature"] == "HOT"

    lead = (await db_session.execute(Lead.select().where(Lead.mobile == "9829088888"))).scalar_one_or_none()
    assert lead.temperature == "HOT"


@pytest.mark.asyncio
async def test_meta_webhook_challenge(test_client):
    res = await test_client.get(
        "/v1/ai/webhooks/meta",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "1158201444",
            "hub.verify_token": "omshiv_meta_secret_token",
        },
    )
    assert res.status_code == 200
    assert int(res.text) == 1158201444


@pytest.mark.asyncio
async def test_meta_webhook_post_lead(test_client, db_session):
    payload = {
        "leadgen_id": "meta_post_123",
        "full_name": "Kiran Rathore",
        "mobile": "9829099999",
        "city": "Jaipur",
    }
    res = await test_client.post("/v1/ai/webhooks/meta", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["created"] is True
    assert data["lead_id"] is not None


@pytest.mark.asyncio
async def test_instagram_webhook_challenge(test_client):
    res = await test_client.get(
        "/v1/ai/webhooks/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "99887766",
            "hub.verify_token": "omshiv_meta_secret_token",
        },
    )
    assert res.status_code == 200
    assert int(res.text) == 99887766


@pytest.mark.asyncio
async def test_instagram_webhook_post_lead(test_client, db_session):
    payload = {
        "sender_id": "ig_post_999",
        "full_name": "Vikram Singh",
        "mobile": "9829011112",
        "city": "Jaipur",
    }
    res = await test_client.post("/v1/ai/webhooks/instagram", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["created"] is True


@pytest.mark.asyncio
async def test_instagram_lead_intake_with_dict_message(db_session):
    agent = MetaLeadAgent(db_session)
    payload = {
        "sender_id": "ig_dict_1",
        "username": "ananya_realty",
        "city": "Jaipur",
        "message": {
            "mid": "mid_1234567890",
            "text": "Hi, please WhatsApp me property brochures on 9829011223",
        },
    }
    res = await agent.process_meta_lead(payload, channel="INSTAGRAM")
    assert res["created"] is True
    assert res["mobile"] == "9829011223"

    lead = (await db_session.execute(Lead.select().where(Lead.mobile == "9829011223"))).scalar_one_or_none()
    assert lead is not None
    assert lead.source == "INSTAGRAM"

    consent = (await db_session.execute(CustomerConsent.select().where(CustomerConsent.mobile == "9829011223"))).scalar_one_or_none()
    assert consent is not None
    assert consent.is_opted_in is True


@pytest.mark.asyncio
async def test_meta_webhook_challenge_rejected_on_missing_or_invalid_token(test_client):
    # Missing verify_token
    res_missing = await test_client.get(
        "/v1/ai/webhooks/meta",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "1158201444",
        },
    )
    assert res_missing.status_code == 403
    assert res_missing.json()["detail"] == "Verification token mismatch"

    # Invalid verify_token
    res_invalid = await test_client.get(
        "/v1/ai/webhooks/meta",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "1158201444",
            "hub.verify_token": "wrong_secret_token",
        },
    )
    assert res_invalid.status_code == 403
    assert res_invalid.json()["detail"] == "Verification token mismatch"


@pytest.mark.asyncio
async def test_instagram_webhook_challenge_rejected_on_missing_token(test_client):
    res = await test_client.get(
        "/v1/ai/webhooks/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "99887766",
        },
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "Verification token mismatch"

