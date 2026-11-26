import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.services.ai.agents.new_property_alert_agent import NewPropertyAlertAgent
from app.models.properties import Property
from app.models.leads import Lead
from app.models.ai_agents import (
    PropertyAlertHistory,
    CustomerConsent,
    AIAgentConfig,
    AIAgentExecutionLog,
)
from app.services.notifications.whatsapp_gateway import WhatsAppGateway


@pytest.mark.asyncio
async def test_duplicate_alert_suppressed(db_session):
    prop = Property(
        property_id="OP-2026-00005",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="2 BHK Flat",
        city="Alwar",
        pincode="301001",
        expected_price=3000000,
        owner_name="X",
        owner_mobile="9999999999",
        is_live=True,
    )
    lead = Lead(
        lead_id="OB-2026-000005",
        full_name="Prem",
        mobile="9829077777",
        preferred_city="Alwar",
        budget_max=3500000,
    )
    consent = CustomerConsent(
        mobile="9829077777",
        channel="WHATSAPP",
        is_opted_in=True,
    )
    history = PropertyAlertHistory(
        lead_id="OB-2026-000005",
        property_id="OP-2026-00005",
        channel="WHATSAPP",
        status="SENT",
        sent_at=datetime.now(timezone.utc),
    )
    db_session.add_all([prop, lead, consent, history])
    await db_session.commit()

    agent = NewPropertyAlertAgent(db_session)
    res = await agent.dispatch_alerts_for_property("OP-2026-00005")

    assert res["success"] is True
    assert res["eligible_leads_count"] == 1
    assert res["dispatched_count"] == 0
    assert res["suppressed_duplicate_count"] == 1


@pytest.mark.asyncio
async def test_cooldown_expired_allows_alert(db_session):
    prop = Property(
        property_id="OP-2026-00006",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="3 BHK Villa",
        city="Alwar",
        pincode="301001",
        expected_price=5000000,
        owner_name="Y",
        owner_mobile="9999999998",
        is_live=True,
    )
    lead = Lead(
        lead_id="OB-2026-000006",
        full_name="Rahul",
        mobile="9829077778",
        preferred_city="Alwar",
        budget_max=6000000,
    )
    consent = CustomerConsent(
        mobile="9829077778",
        channel="WHATSAPP",
        is_opted_in=True,
    )
    # Alert was sent 8 days ago (> 7-day cooldown)
    old_history = PropertyAlertHistory(
        lead_id="OB-2026-000006",
        property_id="OP-2026-00006",
        channel="WHATSAPP",
        status="SENT",
        sent_at=datetime.now(timezone.utc) - timedelta(days=8),
    )
    db_session.add_all([prop, lead, consent, old_history])
    await db_session.commit()

    agent = NewPropertyAlertAgent(db_session)
    res = await agent.dispatch_alerts_for_property("OP-2026-00006")

    assert res["success"] is True
    assert res["eligible_leads_count"] == 1
    assert res["suppressed_duplicate_count"] == 0
    # In default SHADOW mode
    assert res["shadow_count"] == 1
    assert res["dispatched_count"] == 0


@pytest.mark.asyncio
async def test_no_consent_suppresses_alert(db_session):
    prop = Property(
        property_id="OP-2026-00007",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Commercial Shop",
        city="Alwar",
        pincode="301001",
        expected_price=2500000,
        owner_name="Z",
        owner_mobile="9999999997",
        is_live=True,
    )
    # Lead has NOT opted in / no consent record
    lead = Lead(
        lead_id="OB-2026-000007",
        full_name="Vikas",
        mobile="9829077779",
        preferred_city="Alwar",
        budget_max=3000000,
    )
    db_session.add_all([prop, lead])
    await db_session.commit()

    agent = NewPropertyAlertAgent(db_session)
    res = await agent.dispatch_alerts_for_property("OP-2026-00007")

    assert res["success"] is True
    assert res["eligible_leads_count"] == 1
    assert res["suppressed_no_consent_count"] == 1
    assert res["dispatched_count"] == 0
    assert res["shadow_count"] == 0


@pytest.mark.asyncio
async def test_rate_limit_suppresses_alert(db_session):
    prop = Property(
        property_id="OP-2026-00008",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Plot in Scheme 8",
        city="Alwar",
        pincode="301001",
        expected_price=2000000,
        owner_name="W",
        owner_mobile="9999999996",
        is_live=True,
    )
    lead = Lead(
        lead_id="OB-2026-000008",
        full_name="Ankit",
        mobile="9829077780",
        preferred_city="Alwar",
        budget_max=2500000,
    )
    consent = CustomerConsent(
        mobile="9829077780",
        channel="WHATSAPP",
        is_opted_in=True,
    )
    db_session.add_all([prop, lead, consent])

    # Seed 10 recent alerts to hit max_per_hour = 10 limit
    now = datetime.now(timezone.utc)
    for i in range(10):
        db_session.add(
            PropertyAlertHistory(
                lead_id="OB-2026-000008",
                property_id=f"OP-PRIOR-{i}",
                channel="WHATSAPP",
                status="SENT",
                sent_at=now - timedelta(minutes=5),
            )
        )
    await db_session.commit()

    agent = NewPropertyAlertAgent(db_session)
    res = await agent.dispatch_alerts_for_property("OP-2026-00008")

    assert res["success"] is True
    assert res["eligible_leads_count"] == 1
    assert res["suppressed_rate_limit_count"] == 1
    assert res["dispatched_count"] == 0


@pytest.mark.asyncio
async def test_shadow_mode_records_history_and_logs(db_session):
    cfg = AIAgentConfig(agent_name="new_property_alert_agent", display_name="Property Alert", mode="SHADOW")
    prop = Property(
        property_id="OP-2026-00009",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="1 BHK Apartment",
        city="Alwar",
        pincode="301001",
        expected_price=1500000,
        owner_name="M",
        owner_mobile="9999999995",
        is_live=True,
    )
    lead = Lead(
        lead_id="OB-2026-000009",
        full_name="Deepak",
        mobile="9829077781",
        preferred_city="Alwar",
        budget_max=2000000,
    )
    consent = CustomerConsent(
        mobile="9829077781",
        channel="WHATSAPP",
        is_opted_in=True,
    )
    db_session.add_all([cfg, prop, lead, consent])
    await db_session.commit()

    agent = NewPropertyAlertAgent(db_session)
    res = await agent.dispatch_alerts_for_property("OP-2026-00009")

    assert res["success"] is True
    assert res["eligible_leads_count"] == 1
    assert res["shadow_count"] == 1
    assert res["dispatched_count"] == 0

    # Verify PropertyAlertHistory contains SHADOW record
    history_stmt = select(PropertyAlertHistory).where(
        PropertyAlertHistory.lead_id == "OB-2026-000009",
        PropertyAlertHistory.property_id == "OP-2026-00009",
    )
    history = (await db_session.execute(history_stmt)).scalar_one_or_none()
    assert history is not None
    assert history.status == "SHADOW"

    # Verify AIAgentExecutionLog contains SHADOW_LOGGED record
    log_stmt = select(AIAgentExecutionLog).where(
        AIAgentExecutionLog.agent_name == "new_property_alert_agent",
        AIAgentExecutionLog.lead_id == "OB-2026-000009",
    )
    log = (await db_session.execute(log_stmt)).scalar_one_or_none()
    assert log is not None
    assert log.status == "SHADOW_LOGGED"
    assert log.mode == "SHADOW"


@pytest.mark.asyncio
async def test_live_mode_dispatches_outbound(db_session):
    cfg = AIAgentConfig(agent_name="new_property_alert_agent", display_name="Property Alert", mode="LIVE")
    prop = Property(
        property_id="OP-2026-00010",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Luxury Villa",
        city="Alwar",
        pincode="301001",
        expected_price=7500000,
        owner_name="K",
        owner_mobile="9999999994",
        is_live=True,
    )
    lead = Lead(
        lead_id="OB-2026-000010",
        full_name="Kavita",
        mobile="9829077782",
        preferred_city="Alwar",
        budget_max=8000000,
    )
    consent = CustomerConsent(
        mobile="9829077782",
        channel="WHATSAPP",
        is_opted_in=True,
    )
    db_session.add_all([cfg, prop, lead, consent])
    await db_session.commit()

    mock_gateway = WhatsAppGateway()
    agent = NewPropertyAlertAgent(db_session, gateway=mock_gateway)
    res = await agent.dispatch_alerts_for_property("OP-2026-00010")

    assert res["success"] is True
    assert res["eligible_leads_count"] == 1
    assert res["dispatched_count"] == 1
    assert res["shadow_count"] == 0

    # Verify PropertyAlertHistory contains SENT record
    history_stmt = select(PropertyAlertHistory).where(
        PropertyAlertHistory.lead_id == "OB-2026-000010",
        PropertyAlertHistory.property_id == "OP-2026-00010",
    )
    history = (await db_session.execute(history_stmt)).scalar_one_or_none()
    assert history is not None
    assert history.status == "SENT"

    # Verify gateway dispatched message
    assert len(mock_gateway.sent_messages) == 1
    assert mock_gateway.sent_messages[0]["mobile"] == "9829077782"


@pytest.mark.asyncio
async def test_disabled_mode_blocks_dispatch(db_session):
    cfg = AIAgentConfig(agent_name="new_property_alert_agent", display_name="Property Alert", mode="DISABLED")
    prop = Property(
        property_id="OP-2026-00011",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Penthouse",
        city="Alwar",
        pincode="301001",
        expected_price=9000000,
        owner_name="L",
        owner_mobile="9999999993",
        is_live=True,
    )
    lead = Lead(
        lead_id="OB-2026-000011",
        full_name="Sanjay",
        mobile="9829077783",
        preferred_city="Alwar",
        budget_max=10000000,
    )
    db_session.add_all([cfg, prop, lead])
    await db_session.commit()

    agent = NewPropertyAlertAgent(db_session)
    res = await agent.dispatch_alerts_for_property("OP-2026-00011")

    assert res["success"] is False
    assert res.get("status") == "BLOCKED_FLAG"
    assert res["dispatched_count"] == 0


@pytest.mark.asyncio
async def test_property_not_live_or_missing(db_session):
    # Property not live (is_live=False)
    prop = Property(
        property_id="OP-2026-00012",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Unverified Flat",
        city="Alwar",
        pincode="301001",
        expected_price=3000000,
        owner_name="O",
        owner_mobile="9999999992",
        is_live=False,
    )
    db_session.add(prop)
    await db_session.commit()

    agent = NewPropertyAlertAgent(db_session)
    res_not_live = await agent.dispatch_alerts_for_property("OP-2026-00012")
    assert res_not_live["success"] is False
    assert "not live" in res_not_live.get("error", "").lower()

    # Missing property
    res_missing = await agent.dispatch_alerts_for_property("OP-NONEXISTENT")
    assert res_missing["success"] is False


@pytest.mark.asyncio
async def test_filtering_by_city_and_budget_and_deleted(db_session):
    prop = Property(
        property_id="OP-2026-00013",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Independent House",
        city="Alwar",
        pincode="301001",
        expected_price=4000000,
        owner_name="P",
        owner_mobile="9999999991",
        is_live=True,
    )
    # Lead 1: Matches city & budget >= 40L
    lead1 = Lead(
        lead_id="OB-MATCH-1",
        full_name="Match 1",
        mobile="9829077784",
        preferred_city="Alwar",
        budget_max=4500000,
    )
    consent1 = CustomerConsent(mobile="9829077784", channel="WHATSAPP", is_opted_in=True)

    # Lead 2: Different city (Jaipur != Alwar)
    lead2 = Lead(
        lead_id="OB-DIFF-CITY",
        full_name="Diff City",
        mobile="9829077785",
        preferred_city="Jaipur",
        budget_max=5000000,
    )

    # Lead 3: Lower budget (30L < 40L)
    lead3 = Lead(
        lead_id="OB-LOW-BUDGET",
        full_name="Low Budget",
        mobile="9829077786",
        preferred_city="Alwar",
        budget_max=3000000,
    )

    # Lead 4: Deleted lead (deleted_at is set)
    lead4 = Lead(
        lead_id="OB-DELETED",
        full_name="Deleted Lead",
        mobile="9829077787",
        preferred_city="Alwar",
        budget_max=5000000,
        deleted_at=datetime.now(timezone.utc),
    )

    db_session.add_all([prop, lead1, consent1, lead2, lead3, lead4])
    await db_session.commit()

    agent = NewPropertyAlertAgent(db_session)
    res = await agent.dispatch_alerts_for_property("OP-2026-00013")

    assert res["success"] is True
    assert res["eligible_leads_count"] == 1
    assert res["shadow_count"] == 1
