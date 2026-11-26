import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.services.ai.agents.voice_calling_agent import VoiceCallingAgent
from app.services.ai.telephony_client import ExotelTelephonyClient
from app.models.leads import Lead, LeadActivity
from app.models.ai_agents import AIAgentConfig, CustomerConsent
from tests.ai_mocks import MockTelephonyClient, MockAIClientService
from app.services.ai.agents.lead_qualification_agent import LeadQualificationAgent


@pytest.mark.asyncio
async def test_voice_call_blocked_without_consent(db_session):
    lead = Lead(lead_id="OB-2026-000004", full_name="Sunil Joshi", mobile="9829066666", stage="NEW")
    db_session.add(lead)
    await db_session.commit()

    mock_telephony = MockTelephonyClient()
    agent = VoiceCallingAgent(db_session, telephony_client=mock_telephony)
    ist = timezone(timedelta(hours=5, minutes=30))
    day_time = datetime(2026, 11, 26, 14, 0, tzinfo=ist)
    res = await agent.trigger_outbound_call("OB-2026-000004", check_time=day_time)

    assert res["status"] == "BLOCKED_NO_CONSENT"
    assert mock_telephony.calls_dispatched == 0


@pytest.mark.asyncio
async def test_voice_call_shadow_mode_logs_without_calling(db_session):
    cfg = AIAgentConfig(agent_name="voice_calling_agent", display_name="Voice Call", mode="SHADOW")
    lead = Lead(lead_id="OB-2026-000004b", full_name="Sunil Joshi", mobile="9829066667", stage="NEW")
    consent = CustomerConsent(mobile="9829066667", channel="VOICE", is_opted_in=True)
    db_session.add_all([cfg, lead, consent])
    await db_session.commit()

    mock_telephony = MockTelephonyClient()
    agent = VoiceCallingAgent(db_session, telephony_client=mock_telephony)
    ist = timezone(timedelta(hours=5, minutes=30))
    day_time = datetime(2026, 11, 26, 14, 0, tzinfo=ist)
    res = await agent.trigger_outbound_call("OB-2026-000004b", check_time=day_time)

    assert res["mode"] == "SHADOW"
    assert res["call_dispatched"] is False
    assert mock_telephony.calls_dispatched == 0


@pytest.mark.asyncio
async def test_voice_call_blocked_during_quiet_hours(db_session):
    lead = Lead(lead_id="OB-2026-000004c", full_name="Vikram Mehta", mobile="9829066668", stage="NEW")
    consent = CustomerConsent(mobile="9829066668", channel="VOICE", is_opted_in=True)
    db_session.add_all([lead, consent])
    await db_session.commit()

    mock_telephony = MockTelephonyClient()
    agent = VoiceCallingAgent(db_session, telephony_client=mock_telephony)
    
    # 22:30 IST is in quiet hours (21:00 - 09:00 IST)
    ist = timezone(timedelta(hours=5, minutes=30))
    quiet_time = datetime(2026, 11, 26, 22, 30, tzinfo=ist)

    res = await agent.trigger_outbound_call("OB-2026-000004c", check_time=quiet_time)

    assert res["status"] == "BLOCKED_QUIET_HOURS"
    assert res["call_dispatched"] is False
    assert mock_telephony.calls_dispatched == 0


@pytest.mark.asyncio
async def test_voice_call_live_mode_dispatches_call(db_session):
    cfg = AIAgentConfig(agent_name="voice_calling_agent", display_name="Voice Call", mode="LIVE")
    lead = Lead(lead_id="OB-2026-000004d", full_name="Asha Sharma", mobile="9829066669", stage="NEW")
    consent = CustomerConsent(mobile="9829066669", channel="VOICE", is_opted_in=True)
    db_session.add_all([cfg, lead, consent])
    await db_session.commit()

    mock_telephony = MockTelephonyClient()
    agent = VoiceCallingAgent(db_session, telephony_client=mock_telephony)

    # 14:00 IST is outside quiet hours
    ist = timezone(timedelta(hours=5, minutes=30))
    day_time = datetime(2026, 11, 26, 14, 0, tzinfo=ist)

    res = await agent.trigger_outbound_call("OB-2026-000004d", check_time=day_time)

    assert res["status"] == "SUCCESS"
    assert res["mode"] == "LIVE"
    assert res["call_dispatched"] is True
    assert mock_telephony.calls_dispatched == 1
    assert mock_telephony.dispatched_calls[0]["to_mobile"] == "9829066669"


@pytest.mark.asyncio
async def test_voice_call_blocked_when_agent_disabled(db_session):
    cfg = AIAgentConfig(agent_name="voice_calling_agent", display_name="Voice Call", mode="DISABLED")
    lead = Lead(lead_id="OB-2026-000004e", full_name="Ramesh Gupta", mobile="9829066670", stage="NEW")
    consent = CustomerConsent(mobile="9829066670", channel="VOICE", is_opted_in=True)
    db_session.add_all([cfg, lead, consent])
    await db_session.commit()

    mock_telephony = MockTelephonyClient()
    agent = VoiceCallingAgent(db_session, telephony_client=mock_telephony)

    ist = timezone(timedelta(hours=5, minutes=30))
    day_time = datetime(2026, 11, 26, 11, 0, tzinfo=ist)

    res = await agent.trigger_outbound_call("OB-2026-000004e", check_time=day_time)

    assert res["status"] == "BLOCKED_FLAG"
    assert res["call_dispatched"] is False
    assert mock_telephony.calls_dispatched == 0


@pytest.mark.asyncio
async def test_voice_call_transcript_processing(db_session):
    lead = Lead(
        lead_id="OB-2026-000004f",
        full_name="Pooja Verma",
        mobile="9829066671",
        stage="NEW",
        temperature="COLD",
    )
    db_session.add(lead)
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "temperature": "HOT",
        "qualification_score": 88,
        "budget_min": 4000000,
        "budget_max": 5000000,
        "preferred_city": "Alwar",
        "preferred_locality": "MIA",
        "timeline": "Immediate (within 30 days)",
        "bhk": "3 BHK",
        "summary": "Customer looking for 3 BHK flat near MIA within 50 lakhs",
        "recommended_next_action": "Schedule site visit",
        "should_disqualify": False,
    })

    lead_qual = LeadQualificationAgent(db_session, ai_client=mock_ai)
    agent = VoiceCallingAgent(db_session, lead_qualification_agent=lead_qual)

    transcript = "Namaste, mujhe MIA Alwar me 3 BHK flat dekhna hai, budget lagbhag 45 lakh hai. Jaldi chahiye."
    res = await agent.process_call_transcript(
        lead_id="OB-2026-000004f",
        transcript=transcript,
        call_duration=120,
        recording_url="https://s3.exotel.com/recordings/call_123.mp3",
    )

    assert res["success"] is True
    assert res["lead_id"] == "OB-2026-000004f"
    assert res["call_duration"] == 120

    await db_session.refresh(lead)
    assert lead.temperature == "HOT"
    assert lead.is_untouched is False

    # Verify LeadActivity logged
    activities = (await db_session.execute(
        select(LeadActivity).where(LeadActivity.lead_id == "OB-2026-000004f")
    )).scalars().all()
    assert len(activities) >= 1
    voice_act = next((a for a in activities if a.action_type == "VOICE_CALL"), None)
    assert voice_act is not None
    assert "https://s3.exotel.com/recordings/call_123.mp3" in voice_act.note


@pytest.mark.asyncio
async def test_exotel_telephony_client_mock_mode():
    client = ExotelTelephonyClient(mock=True)
    res = await client.dispatch_call(
        to_mobile="9829012345",
        custom_field="OB-2026-999",
        callback_url="https://api.omshiv.com/v1/ai/webhooks/voice/status",
    )
    assert res["status"] in ("QUEUED", "SUCCESS")
    assert "call_sid" in res


@pytest.mark.asyncio
async def test_webhook_voice_status(test_client, db_session):
    lead = Lead(lead_id="OB-2026-000004g", full_name="Rajesh Pilot", mobile="9829066672", stage="NEW")
    db_session.add(lead)
    await db_session.commit()

    payload = {
        "CallSid": "exotel-call-998877",
        "Status": "completed",
        "CustomField": "OB-2026-000004g",
        "Duration": 45,
        "RecordingUrl": "https://s3.exotel.com/rec/call99.mp3",
    }
    res = await test_client.post("/v1/ai/webhooks/voice/status", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "received"
    assert data["call_sid"] == "exotel-call-998877"
    assert data["call_status"] == "completed"

    activities = (await db_session.execute(
        select(LeadActivity).where(LeadActivity.lead_id == "OB-2026-000004g")
    )).scalars().all()
    status_act = next((a for a in activities if a.action_type == "VOICE_CALL_STATUS"), None)
    assert status_act is not None
    assert status_act.outcome == "completed"


@pytest.mark.asyncio
async def test_webhook_voice_transcript(test_client, db_session):
    lead = Lead(lead_id="OB-2026-000004h", full_name="Sunita Rao", mobile="9829066673", stage="NEW")
    db_session.add(lead)
    await db_session.commit()

    payload = {
        "lead_id": "OB-2026-000004h",
        "transcript": "Haanji, mujhe Alwar scheme 2 me 2 BHK flat chahiye. Budget 30 lakh hai.",
        "call_duration": 65,
        "recording_url": "https://s3.exotel.com/rec/call100.mp3",
    }
    res = await test_client.post("/v1/ai/webhooks/voice/transcript", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["lead_id"] == "OB-2026-000004h"


@pytest.mark.asyncio
async def test_webhook_voice_status_form_encoded(test_client, db_session):
    lead = Lead(lead_id="OB-2026-000004i", full_name="Sita Devi", mobile="9829066674", stage="NEW")
    db_session.add(lead)
    await db_session.commit()

    form_payload = {
        "CallSid": "exotel-call-form-123",
        "Status": "completed",
        "CustomField": "OB-2026-000004i",
        "Duration": "30",
        "RecordingUrl": "https://s3.exotel.com/rec/call_form.mp3",
    }
    res = await test_client.post("/v1/ai/webhooks/voice/status", data=form_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "received"
    assert data["call_sid"] == "exotel-call-form-123"

    activities = (await db_session.execute(
        select(LeadActivity).where(LeadActivity.lead_id == "OB-2026-000004i")
    )).scalars().all()
    assert len(activities) >= 1


@pytest.mark.asyncio
async def test_webhook_voice_status_unknown_lead_no_error(test_client, db_session):
    form_payload = {
        "CallSid": "exotel-call-unregistered",
        "Status": "completed",
        "CustomField": "OB-NONEXISTENT-9999",
        "Duration": "15",
    }
    res = await test_client.post("/v1/ai/webhooks/voice/status", data=form_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "received"
    assert data["call_sid"] == "exotel-call-unregistered"


@pytest.mark.asyncio
async def test_webhook_voice_transcript_form_encoded(test_client, db_session):
    lead = Lead(lead_id="OB-2026-000004j", full_name="Karan Johar", mobile="9829066675", stage="NEW")
    db_session.add(lead)
    await db_session.commit()

    form_payload = {
        "lead_id": "OB-2026-000004j",
        "transcript": "Hello, I want to inquire about plots near Delhi-Mumbai Expressway.",
        "call_duration": "40",
    }
    res = await test_client.post("/v1/ai/webhooks/voice/transcript", data=form_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["lead_id"] == "OB-2026-000004j"


@pytest.mark.asyncio
async def test_voice_call_live_mode_failed_dispatch(db_session):
    cfg = AIAgentConfig(agent_name="voice_calling_agent", display_name="Voice Call", mode="LIVE")
    lead = Lead(lead_id="OB-2026-000004k", full_name="Neeraj Sharma", mobile="9829066676", stage="NEW")
    consent = CustomerConsent(mobile="9829066676", channel="VOICE", is_opted_in=True)
    db_session.add_all([cfg, lead, consent])
    await db_session.commit()

    mock_telephony = MockTelephonyClient()
    mock_telephony.set_canned_call_result({"success": False, "error": "Gateway timeout", "status": "FAILED"})
    agent = VoiceCallingAgent(db_session, telephony_client=mock_telephony)

    ist = timezone(timedelta(hours=5, minutes=30))
    day_time = datetime(2026, 11, 26, 14, 0, tzinfo=ist)

    res = await agent.trigger_outbound_call("OB-2026-000004k", check_time=day_time)

    assert res["status"] == "FAILED"
    assert res["call_dispatched"] is False
    assert mock_telephony.calls_dispatched == 1

