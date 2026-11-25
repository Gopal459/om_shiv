import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.properties import Property, PropResidentialFlat
from app.models.ai_agents import AIAgentExecutionLog
from app.services.ai.agents.customer_support_agent import CustomerSupportAgent
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from tests.ai_mocks import MockAIClientService


@pytest.mark.asyncio
async def test_escalation_detected_on_dispute(db_session: AsyncSession):
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "response": "Connecting you immediately with our senior legal assistance desk.",
        "escalate_to_human": True,
        "escalation_reason": "LEGAL_DISPUTE",
        "urgency": "CRITICAL",
        "suggested_actions": ["Notify legal desk", "Flag customer profile"],
    })
    agent = CustomerSupportAgent(db_session, ai_client=mock_ai)
    res = await agent.answer_inquiry("I want to file a legal fraud complaint against your broker!")

    assert res["success"] is True
    assert res["escalate_to_human"] is True
    assert res["escalation_reason"] == "LEGAL_DISPUTE"
    assert "legal assistance" in res["response"]

    # Verify execution log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "customer_support",
    )
    log_res = await db_session.execute(log_stmt)
    logs = log_res.scalars().all()
    assert len(logs) >= 1
    assert logs[-1].status == "SUCCESS"


@pytest.mark.asyncio
async def test_customer_support_disabled_flag(db_session: AsyncSession):
    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("customer_support", "DISABLED")

    mock_ai = MockAIClientService()
    agent = CustomerSupportAgent(db_session, ai_client=mock_ai, guardrails=guardrails)

    res = await agent.answer_inquiry("What are your office hours?")
    assert res["success"] is False
    assert "disabled" in res["error"].lower()

    # Check blocked log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "customer_support",
        AIAgentExecutionLog.status == "BLOCKED_FLAG",
    )
    log_res = await db_session.execute(log_stmt)
    log = log_res.scalar_one_or_none()
    assert log is not None


@pytest.mark.asyncio
async def test_answer_inquiry_with_verified_property(db_session: AsyncSession):
    prop = Property(
        property_id="OP-2026-00050",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Verified 3 BHK Apartment in Jagatpura",
        city="Jaipur",
        locality="Jagatpura",
        pincode="302017",
        expected_price=6500000,
        owner_name="Ramesh Gupta",
        owner_mobile="9829055555",
        is_live=True,
        verified_status=1,
    )
    flat = PropResidentialFlat(
        property=prop,
        bhk=3,
        rooms=3,
        bathrooms=3,
        super_area=1400,
        carpet_area=1150,
    )
    db_session.add(prop)
    db_session.add(flat)
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "response": "The price for OP-2026-00050 in Jagatpura is ₹65 Lakh. It is a verified 3 BHK apartment.",
        "escalate_to_human": False,
        "escalation_reason": None,
        "urgency": "LOW",
        "suggested_actions": ["Offer site visit booking"],
    })

    agent = CustomerSupportAgent(db_session, ai_client=mock_ai)
    res = await agent.answer_inquiry(
        customer_query="What is the price of property OP-2026-00050 and is it verified?",
        property_id="OP-2026-00050",
        session_context={"lead_id": "OB-2026-000099", "channel": "WHATSAPP"},
    )

    assert res["success"] is True
    assert res["escalate_to_human"] is False
    assert res["property_context"] is not None
    assert res["property_context"]["property_id"] == "OP-2026-00050"
    assert res["property_context"]["bhk"] == 3
    assert res["property_context"]["verified_status"] == 1
    assert "₹65 Lakh" in res["response"] or "65" in res["response"]

    # Verify that AI was called with verified property context in the user prompt
    assert len(mock_ai.call_history) == 1
    user_prompt = mock_ai.call_history[0]["user_prompt"]
    assert "OP-2026-00050" in user_prompt
    assert "Jagatpura" in user_prompt


@pytest.mark.asyncio
async def test_anti_hallucination_on_unverified_missing_property(db_session: AsyncSession):
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "response": "I cannot verify listing OP-9999-99999 in our database. I can only provide details for verified live listings.",
        "escalate_to_human": False,
        "escalation_reason": None,
        "urgency": "LOW",
        "suggested_actions": [],
    })

    agent = CustomerSupportAgent(db_session, ai_client=mock_ai)
    res = await agent.answer_inquiry(
        customer_query="Give me details of OP-9999-99999",
        property_id="OP-9999-99999",
    )

    assert res["success"] is True
    assert res["property_context"] is None
    # User prompt must inform LLM that property was not found
    assert len(mock_ai.call_history) == 1
    assert "not found" in mock_ai.call_history[0]["user_prompt"].lower()


@pytest.mark.asyncio
async def test_deterministic_escalation_detection_safety_net(db_session: AsyncSession):
    # If the LLM mistakenly returns escalate_to_human=False on a severe complaint,
    # the agent's safety net triggers escalation.
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "response": "We have received your message regarding the police complaint.",
        "escalate_to_human": False,  # LLM failed to escalate
        "escalation_reason": None,
        "urgency": "LOW",
    })

    agent = CustomerSupportAgent(db_session, ai_client=mock_ai)
    res = await agent.answer_inquiry(
        "I am going to file a police FIR against your agent for cheating and fraud!"
    )

    assert res["success"] is True
    assert res["escalate_to_human"] is True
    assert res["escalation_reason"] in ["FRAUD_ALLEGATION", "LEGAL_DISPUTE"]


@pytest.mark.asyncio
async def test_multilingual_hindi_inquiry(db_session: AsyncSession):
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "response": "नमस्ते! हमारा ऑफिस सुबह 9:30 बजे से शाम 6:30 बजे तक खुला रहता है।",
        "escalate_to_human": False,
        "escalation_reason": None,
        "urgency": "LOW",
        "suggested_actions": [],
    })

    agent = CustomerSupportAgent(db_session, ai_client=mock_ai)
    res = await agent.answer_inquiry(
        customer_query="Aapka office timing kya hai?",
        language="hi",
        session_context={"channel": "WHATSAPP", "lead_id": "OB-2026-HINDI-01"}
    )

    assert res["success"] is True
    assert "नमस्ते" in res["response"]
    assert res["escalate_to_human"] is False

    # Check execution log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "customer_support",
        AIAgentExecutionLog.lead_id == "OB-2026-HINDI-01",
    )
    log_res = await db_session.execute(log_stmt)
    logs = log_res.scalars().all()
    assert len(logs) >= 1
    assert logs[-1].channel == "WHATSAPP"


@pytest.mark.asyncio
async def test_human_request_trigger(db_session: AsyncSession):
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "response": "Connecting you with our senior property manager right away.",
        "escalate_to_human": True,
        "escalation_reason": "HUMAN_REQUEST",
        "urgency": "MEDIUM",
        "suggested_actions": ["Notify lead manager"],
    })

    agent = CustomerSupportAgent(db_session, ai_client=mock_ai)
    res = await agent.answer_inquiry("Please connect me to human agent or manager immediately.")

    assert res["success"] is True
    assert res["escalate_to_human"] is True
    assert res["escalation_reason"] == "HUMAN_REQUEST"
