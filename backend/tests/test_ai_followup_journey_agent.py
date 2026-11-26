import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leads import Lead, LeadActivity
from app.models.ai_agents import CustomerConsent, AIAgentExecutionLog
from app.services.ai.agents.followup_journey_agent import FollowupJourneyAgent
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from tests.ai_mocks import MockAIClientService


@pytest.mark.asyncio
async def test_post_visit_future_prospect_handled(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000007",
        full_name="Manish",
        mobile="9829099999",
        stage="SITE_VISIT_DONE",
        temperature="WARM",
    )
    db_session.add(lead)
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "intent": "FUTURE_PROSPECT",
        "timeline_months": 3,
        "feedback_summary": "Liked property but planning purchase in 3 months",
        "scheduled_follow_up_days": 60,
    })

    agent = FollowupJourneyAgent(db_session, ai_client=mock_ai)
    res = await agent.process_post_visit_feedback(
        "OB-2026-000007", "SV-1", "Property acchi lagi lekin abhi 3 mahine baad lenge."
    )
    assert res["success"] is True
    assert res["intent"] == "FUTURE_PROSPECT"
    assert res["scheduled_follow_up_days"] >= 60

    await db_session.refresh(lead)
    assert lead.temperature == "FUTURE_PROSPECT"

    # Verify LeadActivity was created
    act_stmt = select(LeadActivity).where(
        LeadActivity.lead_id == "OB-2026-000007",
        LeadActivity.action_type == "POST_VISIT_FEEDBACK",
    )
    act = (await db_session.execute(act_stmt)).scalar_one_or_none()
    assert act is not None
    assert act.outcome == "FUTURE_PROSPECT"
    assert "3 months" in act.note
    assert act.follow_up_date is not None


@pytest.mark.asyncio
async def test_post_visit_interested_hot(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000008",
        full_name="Pooja Sharma",
        mobile="9829088888",
        stage="SITE_VISIT_DONE",
        temperature="WARM",
    )
    db_session.add(lead)
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "intent": "INTERESTED",
        "timeline_months": 0,
        "feedback_summary": "Ready to book, liked the location and floor plan",
        "scheduled_follow_up_days": 2,
    })

    agent = FollowupJourneyAgent(db_session, ai_client=mock_ai)
    res = await agent.process_post_visit_feedback(
        "OB-2026-000008", "SV-2", "Location bohot acchi hai, booking token kab dena hai?"
    )
    assert res["success"] is True
    assert res["intent"] == "INTERESTED"

    await db_session.refresh(lead)
    assert lead.temperature == "HOT"

    act_stmt = select(LeadActivity).where(
        LeadActivity.lead_id == "OB-2026-000008",
        LeadActivity.action_type == "POST_VISIT_FEEDBACK",
    )
    act = (await db_session.execute(act_stmt)).scalar_one_or_none()
    assert act is not None
    assert act.outcome == "INTERESTED"


@pytest.mark.asyncio
async def test_post_visit_opt_out(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000009",
        full_name="Vikram Singh",
        mobile="9829077777",
        stage="SITE_VISIT_DONE",
    )
    consent = CustomerConsent(
        mobile="9829077777",
        channel="WHATSAPP",
        is_opted_in=True,
    )
    db_session.add_all([lead, consent])
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "intent": "NOT_INTERESTED",
        "timeline_months": 0,
        "feedback_summary": "Customer explicitly requested STOP messaging and calls",
        "scheduled_follow_up_days": 0,
    })

    agent = FollowupJourneyAgent(db_session, ai_client=mock_ai)
    res = await agent.process_post_visit_feedback(
        "OB-2026-000009", "SV-3", "STOP calling me, I am not interested at all."
    )
    assert res["success"] is True
    assert res["intent"] == "NOT_INTERESTED"

    # Verify CustomerConsent updated to opted out
    guardrails = SafetyGuardrailsService(db_session)
    has_consent = await guardrails.verify_consent("9829077777", channel="WHATSAPP")
    assert has_consent is False


@pytest.mark.asyncio
async def test_evaluate_nurturing_step_lifecycle(db_session: AsyncSession):
    now = datetime.now(timezone.utc)
    leads_data = [
        ("OB-2026-000010", "Lead0", "9829000000", now, "DAY_0"),
        ("OB-2026-000011", "Lead1", "9829000001", now - timedelta(days=1), "DAY_1"),
        ("OB-2026-000012", "Lead3", "9829000002", now - timedelta(days=4), "DAY_3"),
        ("OB-2026-000013", "Lead7", "9829000003", now - timedelta(days=8), "DAY_7"),
        ("OB-2026-000014", "Lead15", "9829000004", now - timedelta(days=18), "DAY_15"),
        ("OB-2026-000015", "Lead30", "9829000005", now - timedelta(days=35), "DAY_30"),
    ]

    for lid, name, mobile, created, _ in leads_data:
        lead = Lead(
            lead_id=lid,
            full_name=name,
            mobile=mobile,
            stage="CONNECTED",
            preferred_city="Jaipur",
            created_at=created,
        )
        consent = CustomerConsent(
            mobile=mobile,
            channel="WHATSAPP",
            is_opted_in=True,
        )
        db_session.add_all([lead, consent])
    await db_session.commit()

    agent = FollowupJourneyAgent(db_session)

    for lid, _, _, _, expected_step in leads_data:
        res = await agent.evaluate_nurturing_step(lid)
        assert res["success"] is True, f"Failed for {lid}"
        assert res["step"] == expected_step, f"Expected {expected_step} for {lid}, got {res['step']}"
        assert res["message"] is not None
        assert len(res["message"]) > 0
        assert res["mode"] == "LIVE"


@pytest.mark.asyncio
async def test_evaluate_nurturing_cooldown_within_24h(db_session: AsyncSession):
    now = datetime.now(timezone.utc)
    lead = Lead(
        lead_id="OB-2026-000016",
        full_name="Anjali",
        mobile="9829011112",
        stage="CONNECTED",
        created_at=now - timedelta(days=5),
    )
    consent = CustomerConsent(
        mobile="9829011112",
        channel="WHATSAPP",
        is_opted_in=True,
    )
    recent_activity = LeadActivity(
        lead_id="OB-2026-000016",
        action_type="FOLLOW_UP_NURTURE",
        outcome="SENT",
        note="Nurturing step Day 3 sent",
        created_at=now - timedelta(hours=6),
    )
    db_session.add_all([lead, consent, recent_activity])
    await db_session.commit()

    agent = FollowupJourneyAgent(db_session)
    res = await agent.evaluate_nurturing_step("OB-2026-000016")
    assert res["success"] is True
    assert res["action"] == "COOLDOWN_ACTIVE"


@pytest.mark.asyncio
async def test_evaluate_nurturing_skipped_terminal_stage(db_session: AsyncSession):
    terminal_stages = ["WON", "CLOSED_WON", "LOST", "CLOSED_LOST", "BOOKED", "JUNK", "DROPPED"]
    for i, stage in enumerate(terminal_stages):
        lid = f"OB-2026-00002{i}"
        mobile = f"982902222{i}"
        lead = Lead(
            lead_id=lid,
            full_name=f"Terminal {stage}",
            mobile=mobile,
            stage=stage,
        )
        consent = CustomerConsent(
            mobile=mobile,
            channel="WHATSAPP",
            is_opted_in=True,
        )
        db_session.add_all([lead, consent])
    await db_session.commit()

    agent = FollowupJourneyAgent(db_session)
    for i, stage in enumerate(terminal_stages):
        lid = f"OB-2026-00002{i}"
        res = await agent.evaluate_nurturing_step(lid)
        assert res["success"] is True
        assert res["action"] == "SKIPPED_TERMINAL_STAGE"


@pytest.mark.asyncio
async def test_evaluate_nurturing_no_consent(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000030",
        full_name="No Consent Lead",
        mobile="9829033330",
        stage="CONNECTED",
    )
    db_session.add(lead)
    await db_session.commit()

    agent = FollowupJourneyAgent(db_session)
    res = await agent.evaluate_nurturing_step("OB-2026-000030")
    assert res["success"] is False
    assert res["reason"] == "NO_CONSENT"


@pytest.mark.asyncio
async def test_shadow_mode_no_crm_mutation(db_session: AsyncSession):
    now = datetime.now(timezone.utc)
    lead = Lead(
        lead_id="OB-2026-000040",
        full_name="Shadow Test Lead",
        mobile="9829044440",
        stage="CONNECTED",
        temperature="WARM",
        created_at=now - timedelta(days=2),
    )
    consent = CustomerConsent(
        mobile="9829044440",
        channel="WHATSAPP",
        is_opted_in=True,
    )
    db_session.add_all([lead, consent])
    await db_session.commit()

    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("followup_journey_agent", "SHADOW")

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "intent": "FUTURE_PROSPECT",
        "timeline_months": 3,
        "feedback_summary": "Looking to buy after 3 months",
        "scheduled_follow_up_days": 60,
    })

    agent = FollowupJourneyAgent(db_session, guardrails=guardrails, ai_client=mock_ai)

    # 1. Test evaluate_nurturing_step in SHADOW mode
    eval_res = await agent.evaluate_nurturing_step("OB-2026-000040")
    assert eval_res["success"] is True
    assert eval_res["mode"] == "SHADOW"
    assert eval_res["step"] == "DAY_1"

    # Verify no LeadActivity created for nurture
    act_stmt = select(LeadActivity).where(
        LeadActivity.lead_id == "OB-2026-000040",
        LeadActivity.action_type == "FOLLOW_UP_NURTURE",
    )
    assert (await db_session.execute(act_stmt)).scalar_one_or_none() is None

    # 2. Test process_post_visit_feedback in SHADOW mode
    fb_res = await agent.process_post_visit_feedback(
        "OB-2026-000040", "SV-10", "3 mahine baad lenge"
    )
    assert fb_res["success"] is True
    assert fb_res["mode"] == "SHADOW"
    assert fb_res["intent"] == "FUTURE_PROSPECT"

    # Verify lead.temperature was NOT mutated in database
    await db_session.refresh(lead)
    assert lead.temperature == "WARM"

    # Verify audit log in AIAgentExecutionLog
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "followup_journey_agent",
        AIAgentExecutionLog.lead_id == "OB-2026-000040",
        AIAgentExecutionLog.status == "SHADOW_LOGGED",
    )
    logs = (await db_session.execute(log_stmt)).scalars().all()
    assert len(logs) >= 2


@pytest.mark.asyncio
async def test_disabled_mode_rejected(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000050",
        full_name="Disabled Test Lead",
        mobile="9829055550",
        stage="CONNECTED",
    )
    db_session.add(lead)
    await db_session.commit()

    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("followup_journey_agent", "DISABLED")

    agent = FollowupJourneyAgent(db_session, guardrails=guardrails)

    res1 = await agent.evaluate_nurturing_step("OB-2026-000050")
    assert res1["success"] is False
    assert res1["reason"] == "AGENT_DISABLED"

    res2 = await agent.process_post_visit_feedback("OB-2026-000050", "SV-50", "Some feedback")
    assert res2["success"] is False
    assert res2["reason"] == "AGENT_DISABLED"


@pytest.mark.asyncio
async def test_lead_not_found(db_session: AsyncSession):
    agent = FollowupJourneyAgent(db_session)
    res1 = await agent.evaluate_nurturing_step("OB-NON-EXISTENT")
    assert res1["success"] is False
    assert res1["reason"] == "LEAD_NOT_FOUND"

    res2 = await agent.process_post_visit_feedback("OB-NON-EXISTENT", "SV-0", "Feedback")
    assert res2["success"] is False
    assert res2["reason"] == "LEAD_NOT_FOUND"
