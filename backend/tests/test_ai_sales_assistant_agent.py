import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leads import Lead, LeadActivity
from app.models.ai_agents import AIAgentExecutionLog, AIApprovalQueue
from app.services.ai.agents.sales_assistant_agent import SalesAssistantAgent
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from tests.ai_mocks import MockAIClientService


@pytest.mark.asyncio
async def test_sales_assistant_summary_generation(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000003",
        full_name="Sanjay Gupta",
        mobile="9829033333",
        stage="CONTACTED",
        temperature="WARM",
        budget_min=2000000,
        budget_max=4000000,
        preferred_city="Alwar",
        preferred_locality="Alwar Bypass",
    )
    act = LeadActivity(
        lead_id="OB-2026-000003",
        action_type="CALL",
        outcome="DISCUSSED",
        note="Looking for plot near Alwar bypass",
    )
    db_session.add_all([lead, act])
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "full_name": "Sanjay Gupta",
        "summary": "Customer is interested in residential plots near Alwar bypass.",
        "recommended_action": "Share approved township layout on WhatsApp.",
        "draft_message": "Namaste Sanjay ji, Alwar bypass township layout share kar rahe hain.",
        "recommended_stage": "SITE_VISIT_SCHEDULED",
        "requires_hitl": False,
        "talking_points": ["Highlight 90A approval", "Mention wide road access"],
    })

    agent = SalesAssistantAgent(db_session, ai_client=mock_ai)
    summary = await agent.generate_lead_summary("OB-2026-000003")

    assert summary["success"] is True
    assert summary["full_name"] == "Sanjay Gupta"
    assert "plot" in summary["summary"].lower()
    assert summary["recommended_action"] == "Share approved township layout on WhatsApp."

    # Verify execution log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "sales_assistant",
        AIAgentExecutionLog.lead_id == "OB-2026-000003",
    )
    log_res = await db_session.execute(log_stmt)
    logs = log_res.scalars().all()
    assert len(logs) >= 1
    assert logs[-1].status == "SUCCESS"


@pytest.mark.asyncio
async def test_sales_assistant_disabled_flag(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000004",
        full_name="Anita Meena",
        mobile="9829044444",
        stage="NEW",
    )
    db_session.add(lead)
    await db_session.commit()

    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("sales_assistant", "DISABLED")

    mock_ai = MockAIClientService()
    agent = SalesAssistantAgent(db_session, ai_client=mock_ai, guardrails=guardrails)

    res = await agent.generate_lead_summary("OB-2026-000004")
    assert res["success"] is False
    assert "disabled" in res["error"].lower()

    # Verify blocked execution log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "sales_assistant",
        AIAgentExecutionLog.lead_id == "OB-2026-000004",
        AIAgentExecutionLog.status == "BLOCKED_FLAG",
    )
    log_res = await db_session.execute(log_stmt)
    log = log_res.scalar_one_or_none()
    assert log is not None


@pytest.mark.asyncio
async def test_sales_assistant_lead_not_found(db_session: AsyncSession):
    mock_ai = MockAIClientService()
    agent = SalesAssistantAgent(db_session, ai_client=mock_ai)

    res = await agent.generate_lead_summary("OB-NON-EXISTENT")
    assert res["success"] is False
    assert "not found" in res["error"].lower()


@pytest.mark.asyncio
async def test_sales_assistant_recommend_followup_message(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000005",
        full_name="Vikram Singh",
        mobile="9829055555",
        stage="SITE_VISIT_SCHEDULED",
        temperature="HOT",
        preferred_locality="Vaishali Nagar",
    )
    act = LeadActivity(
        lead_id="OB-2026-000005",
        action_type="SITE_VISIT",
        outcome="COMPLETED",
        note="Customer visited 3 BHK sample flat, liked ventilation, negotiating on floor preference",
    )
    db_session.add_all([lead, act])
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "full_name": "Vikram Singh",
        "draft_message": "Hello Vikram ji, thank you for visiting our Vaishali Nagar property today. We have reserved the top floor unit for your consideration.",
        "recommended_action": "Follow up with payment schedule options.",
        "channel": "WHATSAPP",
        "talking_points": ["Special payment plan available this week", "Only 2 park-facing units left"],
    })

    agent = SalesAssistantAgent(db_session, ai_client=mock_ai)
    res = await agent.recommend_followup_message("OB-2026-000005", channel="WHATSAPP", language="en")

    assert res["success"] is True
    assert "draft_message" in res
    assert "Vaishali Nagar" in res["draft_message"]
    assert res["channel"] == "WHATSAPP"

    # Verify execution log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "sales_assistant",
        AIAgentExecutionLog.lead_id == "OB-2026-000005",
    )
    log_res = await db_session.execute(log_stmt)
    logs = log_res.scalars().all()
    assert len(logs) >= 1
    assert logs[-1].status == "SUCCESS"


@pytest.mark.asyncio
async def test_request_stage_update_stages_hitl(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000006",
        full_name="Ramesh Sharma",
        mobile="9829066666",
        stage="NEGOTIATION",
    )
    db_session.add(lead)
    await db_session.commit()

    agent = SalesAssistantAgent(db_session)
    approval_id = await agent.request_stage_update(
        lead_id="OB-2026-000006",
        new_stage="WON",
        reason="Customer paid booking advance token",
    )

    assert approval_id is not None
    assert len(approval_id) > 10

    # Ensure lead.stage is NOT mutated directly
    await db_session.refresh(lead)
    assert lead.stage == "NEGOTIATION"

    # Verify staged item in AIApprovalQueue
    queue_stmt = select(AIApprovalQueue).where(AIApprovalQueue.id == approval_id)
    queue_res = await db_session.execute(queue_stmt)
    staged = queue_res.scalar_one_or_none()
    assert staged is not None
    assert staged.agent_name == "sales_assistant"
    assert staged.lead_id == "OB-2026-000006"
    assert staged.action_type == "STAGE_CHANGE_WON"
    assert staged.status == "PENDING"
    assert staged.proposed_payload["new_stage"] == "WON"
    assert "booking advance" in staged.proposed_payload["reason"]

    # Now verify that executing the approved action through tools actually applies it
    approved = await agent.tools.execute_approved_action(
        approval_id=approval_id,
        reviewer_id="EMP-MGR-01",
        review_note="Verified payment receipt in bank statement",
        db=db_session,
    )
    assert approved is True

    await db_session.refresh(lead)
    assert lead.stage == "WON"


@pytest.mark.asyncio
async def test_request_stage_update_disabled_flag(db_session: AsyncSession):
    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("sales_assistant", "DISABLED")

    agent = SalesAssistantAgent(db_session, guardrails=guardrails)
    with pytest.raises(ValueError) as excinfo:
        await agent.request_stage_update(
            lead_id="OB-2026-000007",
            new_stage="WON",
            reason="Customer agreed",
        )
    assert "disabled" in str(excinfo.value).lower()
