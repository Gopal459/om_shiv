import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leads import Lead, LeadActivity
from app.models.properties import Property
from app.models.ai_agents import AIAgentConfig, AIAgentExecutionLog
from app.services.ai.agents.site_visit_agent import SiteVisitAgent
from app.services.ai.safety_guardrails import SafetyGuardrailsService


@pytest.mark.asyncio
async def test_book_site_visit_workflow(db_session: AsyncSession):
    """Test standard booking workflow in LIVE mode creates activity and updates lead stage."""
    lead = Lead(
        lead_id="OB-2026-000006",
        full_name="Geeta Sharma",
        mobile="9829088888",
        stage="CONTACTED",
    )
    prop = Property(
        property_id="OP-2026-00006",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Residential Plot in Alwar Bypass",
        city="Alwar",
        locality="Alwar Bypass",
        pincode="301001",
        expected_price=2000000,
        owner_name="Yashwant Singh",
        owner_mobile="9829077777",
        is_live=True,
    )
    db_session.add_all([lead, prop])
    await db_session.commit()

    agent = SiteVisitAgent(db_session)
    booking = await agent.book_site_visit(
        lead_id="OB-2026-000006",
        property_id="OP-2026-00006",
        slot="2026-12-01 11:00",
        visitor_notes="Customer coming by car with family",
    )

    assert booking["success"] is True
    assert booking["booking_id"] is not None
    assert booking["mode"] == "LIVE"
    assert booking["lead_id"] == "OB-2026-000006"
    assert booking["property_id"] == "OP-2026-00006"
    assert "Alwar" in booking["confirmation_message"]

    # Verify LeadActivity created
    act_stmt = select(LeadActivity).where(
        LeadActivity.lead_id == "OB-2026-000006",
        LeadActivity.action_type == "SITE_VISIT",
    )
    act_res = await db_session.execute(act_stmt)
    act = act_res.scalar_one_or_none()
    assert act is not None
    assert act.outcome == "SCHEDULED"
    assert "OP-2026-00006" in act.note
    assert act.stage_after == "SITE_VISIT_SCHEDULED"
    assert act.follow_up_date is not None

    # Verify lead stage updated
    await db_session.refresh(lead)
    assert lead.stage == "SITE_VISIT_SCHEDULED"

    # Verify execution log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "site_visit_agent",
        AIAgentExecutionLog.lead_id == "OB-2026-000006",
    )
    log_res = await db_session.execute(log_stmt)
    log = log_res.scalar_one_or_none()
    assert log is not None
    assert log.status == "SUCCESS"
    assert log.mode == "LIVE"


@pytest.mark.asyncio
async def test_prevent_double_booking(db_session: AsyncSession):
    """Test that booking the same property at the same slot fails with SLOT_UNAVAILABLE."""
    lead1 = Lead(lead_id="OB-2026-000007", full_name="Rahul Verma", mobile="9829011111", stage="NEW")
    lead2 = Lead(lead_id="OB-2026-000008", full_name="Pooja Sharma", mobile="9829022222", stage="NEW")
    prop = Property(
        property_id="OP-2026-00007",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Luxury Villa",
        city="Jaipur",
        pincode="302001",
        expected_price=9500000,
        owner_name="Owner",
        owner_mobile="9829033333",
        is_live=True,
    )
    db_session.add_all([lead1, lead2, prop])
    await db_session.commit()

    agent = SiteVisitAgent(db_session)

    # First booking succeeds
    res1 = await agent.book_site_visit("OB-2026-000007", "OP-2026-00007", "2026-12-05 14:00")
    assert res1["success"] is True
    assert res1["booking_id"] is not None

    # Second booking for the same property and slot fails
    res2 = await agent.book_site_visit("OB-2026-000008", "OP-2026-00007", "2026-12-05 14:00")
    assert res2["success"] is False
    assert res2["reason"] == "SLOT_UNAVAILABLE"
    assert "already booked" in res2["message"].lower()


@pytest.mark.asyncio
async def test_check_available_slots_excludes_booked(db_session: AsyncSession):
    """Test that check_available_slots filters out booked times for the property."""
    lead = Lead(lead_id="OB-2026-000009", full_name="Aman Gupta", mobile="9829044444")
    prop = Property(
        property_id="OP-2026-00008",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Commercial Shop",
        city="Kota",
        pincode="324001",
        expected_price=3500000,
        owner_name="Owner",
        owner_mobile="9829055555",
        is_live=True,
    )
    db_session.add_all([lead, prop])
    await db_session.commit()

    agent = SiteVisitAgent(db_session)

    # Initially all standard slots are available
    initial_slots = await agent.check_available_slots("OP-2026-00008", "2026-12-10")
    assert "11:30" in initial_slots
    assert "14:00" in initial_slots
    assert len(initial_slots) == 5

    # Book 11:30 slot
    res = await agent.book_site_visit("OB-2026-000009", "OP-2026-00008", "2026-12-10 11:30")
    assert res["success"] is True

    # Now 11:30 should be excluded from available slots
    updated_slots = await agent.check_available_slots("OP-2026-00008", "2026-12-10")
    assert "11:30" not in updated_slots
    assert "14:00" in updated_slots
    assert len(updated_slots) == 4

    # Different date should still have all slots
    other_date_slots = await agent.check_available_slots("OP-2026-00008", "2026-12-11")
    assert "11:30" in other_date_slots
    assert len(other_date_slots) == 5


@pytest.mark.asyncio
async def test_shadow_mode_records_log_without_activity(db_session: AsyncSession):
    """Test that in SHADOW mode no LeadActivity is created and lead stage is unchanged."""
    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("site_visit_agent", "SHADOW")

    lead = Lead(lead_id="OB-2026-000010", full_name="Ramesh Kumar", mobile="9829066666", stage="NEW")
    prop = Property(
        property_id="OP-2026-00009",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Farmhouse Plot",
        city="Jaipur",
        pincode="302001",
        expected_price=12000000,
        owner_name="Owner",
        owner_mobile="9829077777",
        is_live=True,
    )
    db_session.add_all([lead, prop])
    await db_session.commit()

    agent = SiteVisitAgent(db_session, guardrails=guardrails)
    res = await agent.book_site_visit("OB-2026-000010", "OP-2026-00009", "2026-12-08 15:30")

    assert res["success"] is True
    assert res["mode"] == "SHADOW"
    assert res["booking_id"] is None
    assert "confirmation_message" in res

    # Verify no LeadActivity was written to DB
    act_stmt = select(LeadActivity).where(LeadActivity.lead_id == "OB-2026-000010")
    act_res = await db_session.execute(act_stmt)
    assert act_res.scalar_one_or_none() is None

    # Verify lead stage was NOT modified
    await db_session.refresh(lead)
    assert lead.stage == "NEW"

    # Verify SHADOW_LOGGED execution log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "site_visit_agent",
        AIAgentExecutionLog.lead_id == "OB-2026-000010",
        AIAgentExecutionLog.status == "SHADOW_LOGGED",
    )
    log_res = await db_session.execute(log_stmt)
    log = log_res.scalar_one_or_none()
    assert log is not None
    assert log.mode == "SHADOW"


@pytest.mark.asyncio
async def test_disabled_mode_rejected(db_session: AsyncSession):
    """Test that DISABLED mode rejects booking and logs BLOCKED_FLAG."""
    guardrails = SafetyGuardrailsService(db_session)
    await guardrails.set_agent_mode("site_visit_agent", "DISABLED")

    lead = Lead(lead_id="OB-2026-000011", full_name="Sita Devi", mobile="9829088889")
    prop = Property(
        property_id="OP-2026-00010",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="2 BHK Apartment",
        city="Ajmer",
        pincode="305001",
        expected_price=4500000,
        owner_name="Owner",
        owner_mobile="9829099999",
        is_live=True,
    )
    db_session.add_all([lead, prop])
    await db_session.commit()

    agent = SiteVisitAgent(db_session, guardrails=guardrails)
    res = await agent.book_site_visit("OB-2026-000011", "OP-2026-00010", "2026-12-09 10:00")

    assert res["success"] is False
    assert res["reason"] == "AGENT_DISABLED"

    # Verify BLOCKED_FLAG execution log
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "site_visit_agent",
        AIAgentExecutionLog.status == "BLOCKED_FLAG",
    )
    log_res = await db_session.execute(log_stmt)
    log = log_res.scalar_one_or_none()
    assert log is not None


@pytest.mark.asyncio
async def test_missing_lead_or_property_handled(db_session: AsyncSession):
    """Test graceful handling when lead or property does not exist."""
    agent = SiteVisitAgent(db_session)

    # Lead missing
    res_no_lead = await agent.book_site_visit("OB-NON-EXISTENT", "OP-2026-00006", "2026-12-01 10:00")
    assert res_no_lead["success"] is False
    assert res_no_lead["reason"] == "NOT_FOUND"
    assert "lead" in res_no_lead["message"].lower()

    # Lead exists, property missing
    lead = Lead(lead_id="OB-2026-000012", full_name="Kavita", mobile="9829012345")
    db_session.add(lead)
    await db_session.commit()

    res_no_prop = await agent.book_site_visit("OB-2026-000012", "OP-NON-EXISTENT", "2026-12-01 10:00")
    assert res_no_prop["success"] is False
    assert res_no_prop["reason"] == "NOT_FOUND"
    assert "property" in res_no_prop["message"].lower()


@pytest.mark.asyncio
async def test_lead_stage_not_overwritten_if_won_or_lost(db_session: AsyncSession):
    """Test that terminal stages like WON or LOST are not downgraded to SITE_VISIT_SCHEDULED."""
    lead = Lead(lead_id="OB-2026-000013", full_name="Dinesh", mobile="9829023456", stage="WON")
    prop = Property(
        property_id="OP-2026-00011",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Penthouse",
        city="Jaipur",
        pincode="302001",
        expected_price=15000000,
        owner_name="Owner",
        owner_mobile="9829034567",
        is_live=True,
    )
    db_session.add_all([lead, prop])
    await db_session.commit()

    agent = SiteVisitAgent(db_session)
    res = await agent.book_site_visit("OB-2026-000013", "OP-2026-00011", "2026-12-15 17:00")
    assert res["success"] is True

    await db_session.refresh(lead)
    assert lead.stage == "WON"
