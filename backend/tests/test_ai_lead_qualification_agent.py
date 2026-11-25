import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leads import Lead, LeadActivity
from app.models.ai_agents import AIAgentExecutionLog, AIApprovalQueue
from app.services.ai.agents.lead_qualification_agent import LeadQualificationAgent
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from tests.ai_mocks import MockAIClientService


@pytest.mark.asyncio
async def test_qualify_hot_lead_deterministic(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000002",
        full_name="Vijay Verma",
        mobile="9829022222",
        stage="NEW",
    )
    db_session.add(lead)
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "budget_max": 8000000,
        "timeline": "IMMEDIATE",
        "temperature": "HOT",
        "qualification_score": 90,
        "summary": "Ready buyer for 3 BHK in Mansarovar",
    })

    agent = LeadQualificationAgent(db_session, ai_client=mock_ai)
    transcript = "Customer: I need 3 BHK in Mansarovar within 80 lakh, planning to purchase next week."
    res = await agent.qualify_lead("OB-2026-000002", transcript)

    assert res["temperature"] == "HOT"
    assert res["budget_max"] == 8000000

    await db_session.refresh(lead)
    assert lead.temperature == "HOT"
    assert lead.budget_max == 8000000
    assert lead.stage == "NEW"

    # Verify execution log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "lead_qualification",
        AIAgentExecutionLog.lead_id == "OB-2026-000002",
    )
    log_res = await db_session.execute(log_stmt)
    logs = log_res.scalars().all()
    assert len(logs) >= 1
    assert logs[-1].status == "SUCCESS"


@pytest.mark.asyncio
async def test_qualify_lead_disabled_guardrail(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000003",
        full_name="Rajesh Sharma",
        mobile="9829033333",
        stage="NEW",
    )
    db_session.add(lead)
    await db_session.commit()

    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("lead_qualification", "DISABLED")

    mock_ai = MockAIClientService()
    agent = LeadQualificationAgent(db_session, ai_client=mock_ai, guardrails=guardrails)

    res = await agent.qualify_lead("OB-2026-000003", "Looking for property")
    assert res["success"] is False
    assert "disabled" in res["error"].lower()

    # Check lead stage and temperature remain untouched
    await db_session.refresh(lead)
    assert lead.temperature is None
    assert lead.stage == "NEW"

    # Verify blocked execution log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "lead_qualification",
        AIAgentExecutionLog.lead_id == "OB-2026-000003",
        AIAgentExecutionLog.status == "BLOCKED_FLAG",
    )
    log_res = await db_session.execute(log_stmt)
    log = log_res.scalar_one_or_none()
    assert log is not None


@pytest.mark.asyncio
async def test_qualify_lead_disqualification_stages_hitl(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000004",
        full_name="Sunil Kumar",
        mobile="9829044444",
        stage="NEW",
    )
    db_session.add(lead)
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "temperature": "COLD",
        "qualification_score": 5,
        "summary": "Customer says wrong number and not looking to buy property.",
        "should_disqualify": True,
        "recommended_next_action": "Mark as lost and suppress calls",
    })

    agent = LeadQualificationAgent(db_session, ai_client=mock_ai)
    transcript = "Customer: Wrong number, I never inquired about any property, please do not call."
    res = await agent.qualify_lead("OB-2026-000004", transcript)

    assert res["success"] is True
    assert res["should_disqualify"] is True
    assert res["approval_id"] is not None

    # Crucial Safety Rule: lead.stage MUST NOT be mutated to LOST directly!
    await db_session.refresh(lead)
    assert lead.stage == "NEW"
    assert lead.temperature == "COLD"

    # Verify staged item in AIApprovalQueue
    approval_stmt = select(AIApprovalQueue).where(
        AIApprovalQueue.id == res["approval_id"]
    )
    app_res = await db_session.execute(approval_stmt)
    staged_item = app_res.scalar_one_or_none()
    assert staged_item is not None
    assert staged_item.status == "PENDING"
    assert staged_item.action_type == "STAGE_CHANGE_LOST"
    assert staged_item.lead_id == "OB-2026-000004"


@pytest.mark.asyncio
async def test_qualify_warm_lead_with_full_details(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000005",
        full_name="Pooja Mehta",
        mobile="9829055555",
        stage="NEW",
    )
    db_session.add(lead)
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "budget_min": 5000000,
        "budget_max": 7500000,
        "preferred_city": "Jaipur",
        "preferred_locality": "Jagatpura",
        "timeline": "1_TO_3_MONTHS",
        "bhk": 3,
        "temperature": "WARM",
        "qualification_score": 75,
        "summary": "Looking for 3 BHK flat in Jagatpura within 3 months, budget 50-75 Lakh.",
        "recommended_next_action": "Share Jagatpura project options and arrange site visit.",
        "should_disqualify": False,
    })

    agent = LeadQualificationAgent(db_session, ai_client=mock_ai)
    transcript = "Hello, I am looking for a 3 BHK apartment in Jagatpura, Jaipur. Budget is around 50 to 75 lakh. Plan to purchase within 2 months."
    res = await agent.qualify_lead("OB-2026-000005", transcript)

    assert res["success"] is True
    assert res["temperature"] == "WARM"
    assert res["budget_min"] == 5000000
    assert res["budget_max"] == 7500000
    assert res["preferred_city"] == "Jaipur"
    assert res["preferred_locality"] == "Jagatpura"
    assert res["timeline"] == "1_TO_3_MONTHS"
    assert res["bhk"] == 3
    assert res["qualification_score"] == 75

    await db_session.refresh(lead)
    assert lead.temperature == "WARM"
    assert lead.budget_min == 5000000
    assert lead.budget_max == 7500000
    assert lead.preferred_city == "Jaipur"
    assert lead.preferred_locality == "Jagatpura"
    assert lead.stage == "NEW"

    # Verify LeadActivity log
    act_stmt = select(LeadActivity).where(LeadActivity.lead_id == "OB-2026-000005")
    act_res = await db_session.execute(act_stmt)
    activities = act_res.scalars().all()
    assert len(activities) >= 1
    assert any("REQUIREMENTS_UPDATE" in a.action_type for a in activities)


@pytest.mark.asyncio
async def test_qualify_nonexistent_lead(db_session: AsyncSession):
    mock_ai = MockAIClientService()
    agent = LeadQualificationAgent(db_session, ai_client=mock_ai)

    res = await agent.qualify_lead("OB-2026-999999", "Customer query")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


@pytest.mark.asyncio
async def test_lead_qualification_agent_default_initialization(db_session: AsyncSession):
    agent = LeadQualificationAgent(db_session)
    assert agent.db is db_session
    assert agent.ai_client is not None
    assert agent.guardrails is not None
    assert agent.tools is not None
    assert agent.agent_name == "lead_qualification"
