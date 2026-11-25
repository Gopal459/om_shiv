import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.agents.property_search_agent import PropertySearchAgent
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.models.properties import Property, PropResidentialFlat
from app.models.ai_agents import AIAgentExecutionLog
from tests.ai_mocks import MockAIClientService


@pytest.mark.asyncio
async def test_conversational_property_search_deterministic(db_session: AsyncSession):
    prop = Property(
        property_id="OP-2026-00001",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Luxury 3 BHK Flat in Vaishali Nagar",
        city="Jaipur",
        locality="Vaishali Nagar",
        pincode="302021",
        expected_price=8500000,
        owner_name="Sharma Ji",
        owner_mobile="9829011111",
        is_live=True,
    )
    flat = PropResidentialFlat(
        property=prop,
        bhk=3,
        rooms=3,
        bathrooms=2,
        super_area=1500,
        carpet_area=1250,
    )
    db_session.add(prop)
    db_session.add(flat)
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "city": "Jaipur",
        "locality": "Vaishali Nagar",
        "bhk": 3,
        "max_price": 8500000,
    })

    agent = PropertySearchAgent(db_session, ai_client=mock_ai)
    result = await agent.search_properties_conversational(
        "Mujhe Jaipur Vaishali Nagar me 85 lakh tak flat chahiye"
    )

    assert result["success"] is True
    assert len(result["properties"]) > 0
    assert result["properties"][0]["property_id"] == "OP-2026-00001"
    assert result["total_found"] == 1
    assert "Jaipur" in result["response_text"] or "Vaishali Nagar" in result["response_text"] or "85" in result["response_text"]

    # Verify execution log entry was created
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "property_search"
    )
    log_res = await db_session.execute(log_stmt)
    logs = log_res.scalars().all()
    assert len(logs) >= 1
    assert logs[-1].status == "SUCCESS"
    assert logs[-1].input_summary is not None


@pytest.mark.asyncio
async def test_conversational_search_disabled_flag(db_session: AsyncSession):
    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("property_search", "DISABLED")

    mock_ai = MockAIClientService()
    agent = PropertySearchAgent(db_session, ai_client=mock_ai, guardrails=guardrails)

    result = await agent.search_properties_conversational("Show 2 BHK in Alwar")
    assert result["success"] is False
    assert result["total_found"] == 0
    assert "disabled" in result["error"].lower()

    # Verify execution log was recorded as blocked
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "property_search",
        AIAgentExecutionLog.status == "BLOCKED_FLAG",
    )
    log_res = await db_session.execute(log_stmt)
    log = log_res.scalar_one_or_none()
    assert log is not None


@pytest.mark.asyncio
async def test_conversational_search_no_results(db_session: AsyncSession):
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "city": "NonExistentCity",
        "locality": "Nowhere",
        "bhk": 5,
        "max_price": 1000000,
    })

    agent = PropertySearchAgent(db_session, ai_client=mock_ai)
    result = await agent.search_properties_conversational("5 BHK in NonExistentCity under 10 lakh")

    assert result["success"] is True
    assert result["total_found"] == 0
    assert len(result["properties"]) == 0
    assert isinstance(result["response_text"], str)
    assert len(result["response_text"]) > 0


@pytest.mark.asyncio
async def test_conversational_search_hindi_response(db_session: AsyncSession):
    prop = Property(
        property_id="OP-2026-00002",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="2 BHK Apartment in Alwar",
        city="Alwar",
        locality="MIA",
        pincode="301001",
        expected_price=3500000,
        owner_name="Verma Ji",
        owner_mobile="9829022222",
        is_live=True,
    )
    db_session.add(prop)
    await db_session.commit()

    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "city": "Alwar",
        "locality": "MIA",
        "bhk": 2,
        "max_price": 4000000,
    })

    agent = PropertySearchAgent(db_session, ai_client=mock_ai)
    result = await agent.search_properties_conversational(
        "Alwar me 2 BHK flat dikhao",
        language="hi",
        session_context={"lead_id": "LD-2026-001", "channel": "WHATSAPP"}
    )

    assert result["success"] is True
    assert result["total_found"] == 1
    assert result["properties"][0]["property_id"] == "OP-2026-00002"
    assert "प्रॉपर्टी" in result["response_text"] or "प्रॉपर्टीज" in result["response_text"] or "Alwar" in result["response_text"]


@pytest.mark.asyncio
async def test_property_search_agent_default_initialization(db_session: AsyncSession):
    agent = PropertySearchAgent(db_session)
    assert agent.db is db_session
    assert agent.ai_client is not None
    assert agent.guardrails is not None
    assert agent.tools is not None
