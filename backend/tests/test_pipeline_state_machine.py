import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.leads import Lead


@pytest.mark.asyncio
async def test_stage_transition_requires_compulsory_fields(auth_client_sales: AsyncClient):
    """Verify transitions to CONNECTED, REQ_CAPTURED, QUALIFIED, MEETING, SITE_VISIT, NEGOTIATION require temperature and follow_up_date."""
    # 1. Create a fresh lead in NEW stage
    create_resp = await auth_client_sales.post("/v1/intake/lead", json={
        "source": "WEBSITE",
        "full_name": "Rajesh Gupta",
        "mobile": "9829070001",
        "lead_type": "BUYER",
    })
    assert create_resp.status_code == 201
    lead_id = create_resp.json()["lead_id"]

    # 2. Attempt transition to CONNECTED without temperature and follow_up_date -> 422
    resp_missing_all = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Connected",
        "note": "Client looking for 3BHK flat",
        "stage": "CONNECTED",
    })
    assert resp_missing_all.status_code == 422

    # 3. Attempt transition with temperature but missing follow_up_date -> 422
    resp_missing_date = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Connected",
        "note": "Client looking for 3BHK flat",
        "stage": "CONNECTED",
        "temperature": "HOT",
    })
    assert resp_missing_date.status_code == 422

    # 4. Attempt transition with past follow_up_date -> 422
    past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    resp_past_date = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Connected",
        "note": "Client looking for 3BHK flat",
        "stage": "CONNECTED",
        "temperature": "HOT",
        "follow_up_date": past_date,
    })
    assert resp_past_date.status_code == 422

    # 5. Attempt HOT lead with follow_up_date > 30 days -> 422
    far_date_hot = (datetime.now(timezone.utc) + timedelta(days=35)).isoformat()
    resp_far_hot = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Connected",
        "note": "Client looking for 3BHK flat",
        "stage": "CONNECTED",
        "temperature": "HOT",
        "follow_up_date": far_date_hot,
    })
    assert resp_far_hot.status_code == 422

    # 6. Attempt COLD lead with follow_up_date > 100 days -> 422
    far_date_cold = (datetime.now(timezone.utc) + timedelta(days=105)).isoformat()
    resp_far_cold = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Connected",
        "note": "Client not ready soon",
        "stage": "CONNECTED",
        "temperature": "COLD",
        "follow_up_date": far_date_cold,
    })
    assert resp_far_cold.status_code == 422

    # 7. Success with valid compulsory fields (HOT, within 30 days)
    valid_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    resp_valid = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Connected",
        "note": "Client looking for 3BHK flat in Alwar",
        "temperature": "HOT",
        "follow_up_date": valid_date,
        "stage": "CONNECTED",
    })
    assert resp_valid.status_code == 200
    data = resp_valid.json()
    assert data["stage"] == "CONNECTED"
    assert data["temperature"] == "HOT"
    assert data["is_untouched"] is False


@pytest.mark.asyncio
async def test_transition_to_lost_requires_reason(auth_client_sales: AsyncClient):
    """Verify transitioning to LOST requires lost_reason."""
    create_resp = await auth_client_sales.post("/v1/intake/lead", json={
        "source": "WEBSITE",
        "full_name": "Kavita Rao",
        "mobile": "9829070002",
        "lead_type": "BUYER",
    })
    lead_id = create_resp.json()["lead_id"]

    # Missing lost_reason -> 422
    resp_no_reason = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Lost Deal",
        "stage": "LOST",
    })
    assert resp_no_reason.status_code == 422

    # With lost_reason -> 200
    resp_with_reason = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Lost Deal",
        "stage": "LOST",
        "lost_reason": "Bought property from direct builder in Bhiwadi",
    })
    assert resp_with_reason.status_code == 200
    assert resp_with_reason.json()["stage"] == "LOST"
    assert resp_with_reason.json()["lost_reason"] == "Bought property from direct builder in Bhiwadi"


@pytest.mark.asyncio
async def test_action_logging_resets_untouched_and_creates_activity_log(
    auth_client_sales: AsyncClient, db_session: AsyncSession
):
    """Verify logging an action sets is_untouched=False, sets last_contacted_at, and creates LeadActivity."""
    create_resp = await auth_client_sales.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "Vikram Singh",
        "mobile": "9829070003",
        "lead_type": "BUYER",
    })
    lead_id = create_resp.json()["lead_id"]
    assert create_resp.json()["is_untouched"] is True

    # Log an action while moving to ATTEMPTING
    resp_action = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Ringing No Answer",
        "note": "Tried first contact, no pickup",
        "stage": "ATTEMPTING",
    })
    assert resp_action.status_code == 200
    lead_data = resp_action.json()
    assert lead_data["is_untouched"] is False
    assert lead_data["stage"] == "ATTEMPTING"
    assert lead_data["last_contacted_at"] is not None

    # Fetch detailed lead view with activities
    resp_detail = await auth_client_sales.get(f"/v1/leads/{lead_id}")
    assert resp_detail.status_code == 200
    detail_data = resp_detail.json()
    assert len(detail_data["activities"]) >= 2
    # Latest activity should be the CALL action
    act = detail_data["activities"][0]
    assert act["action_type"] == "CALL"
    assert act["outcome"] == "Ringing No Answer"
    assert act["stage_before"] == "NEW"
    assert act["stage_after"] == "ATTEMPTING"
    assert act["performed_by"] == "EMP-0002"
    # Initial activity was INTAKE
    assert detail_data["activities"][1]["action_type"] == "INTAKE"


@pytest.mark.asyncio
async def test_my_work_prioritization_ordering(
    auth_client_sales: AsyncClient, db_session: AsyncSession
):
    """Verify /v1/leads/my-work prioritizes: 1. Overdue follow-ups, 2. Untouched leads, 3. Today's calls/visits."""
    now = datetime.now(timezone.utc)

    # Lead 1: Overdue follow-up (yesterday)
    overdue_lead = Lead(
        lead_id="OB-2026-900001",
        full_name="Overdue Lead",
        mobile="919829070011",
        lead_type="BUYER",
        source="WEBSITE",
        assigned_to="EMP-0002",
        stage="CONNECTED",
        temperature="HOT",
        follow_up_date=now - timedelta(hours=5),
        is_untouched=False,
        untouched_timer_start=now - timedelta(days=2),
        created_at=now - timedelta(days=2),
    )

    # Lead 2: Untouched lead
    untouched_lead = Lead(
        lead_id="OB-2026-900002",
        full_name="Untouched Lead",
        mobile="919829070012",
        lead_type="BUYER",
        source="WEBSITE",
        assigned_to="EMP-0002",
        stage="NEW",
        is_untouched=True,
        untouched_timer_start=now - timedelta(hours=1),
        created_at=now - timedelta(hours=1),
    )

    # Lead 3: Today's follow-up (in 3 hours)
    today_lead = Lead(
        lead_id="OB-2026-900003",
        full_name="Today Followup Lead",
        mobile="919829070013",
        lead_type="BUYER",
        source="WEBSITE",
        assigned_to="EMP-0002",
        stage="CONNECTED",
        temperature="WARM",
        follow_up_date=now + timedelta(hours=3),
        is_untouched=False,
        untouched_timer_start=now - timedelta(days=1),
        created_at=now - timedelta(days=1),
    )

    # Lead 4: Future follow-up (in 5 days)
    future_lead = Lead(
        lead_id="OB-2026-900004",
        full_name="Future Followup Lead",
        mobile="919829070014",
        lead_type="BUYER",
        source="WEBSITE",
        assigned_to="EMP-0002",
        stage="CONNECTED",
        temperature="COLD",
        follow_up_date=now + timedelta(days=5),
        is_untouched=False,
        untouched_timer_start=now - timedelta(days=1),
        created_at=now - timedelta(days=1),
    )

    db_session.add_all([overdue_lead, untouched_lead, today_lead, future_lead])
    await db_session.commit()

    # Query /v1/leads/my-work
    resp = await auth_client_sales.get("/v1/leads/my-work")
    assert resp.status_code == 200
    work_items = resp.json()
    assert len(work_items) >= 4

    work_ids = [item["lead_id"] for item in work_items]
    # Check prioritization ordering:
    # 1. Overdue lead MUST be first
    assert work_ids[0] == "OB-2026-900001"
    # 2. Untouched lead should come before today's / future
    assert work_ids[1] == "OB-2026-900002"
    # 3. Today's follow-up lead
    assert work_ids[2] == "OB-2026-900003"
    # 4. Future lead
    assert work_ids[3] == "OB-2026-900004"


@pytest.mark.asyncio
async def test_my_leads_filtering(auth_client_sales: AsyncClient, db_session: AsyncSession):
    """Verify /v1/leads/my-leads filters by stage, temperature, and date range."""
    now = datetime.now(timezone.utc)

    lead1 = Lead(
        lead_id="OB-2026-900021",
        full_name="Hot Lead",
        mobile="919829070021",
        assigned_to="EMP-0002",
        stage="QUALIFIED",
        temperature="HOT",
        created_at=now - timedelta(days=5),
    )
    lead2 = Lead(
        lead_id="OB-2026-900022",
        full_name="Cold Lead",
        mobile="919829070022",
        assigned_to="EMP-0002",
        stage="ATTEMPTING",
        temperature="COLD",
        created_at=now - timedelta(days=2),
    )
    db_session.add_all([lead1, lead2])
    await db_session.commit()

    # Filter by stage=QUALIFIED
    resp_stage = await auth_client_sales.get("/v1/leads/my-leads?stage=QUALIFIED")
    assert resp_stage.status_code == 200
    leads = resp_stage.json()
    assert all(l["stage"] == "QUALIFIED" for l in leads)
    assert any(l["lead_id"] == "OB-2026-900021" for l in leads)
    assert not any(l["lead_id"] == "OB-2026-900022" for l in leads)

    # Filter by temperature=COLD
    resp_temp = await auth_client_sales.get("/v1/leads/my-leads?temperature=COLD")
    assert resp_temp.status_code == 200
    leads_cold = resp_temp.json()
    assert all(l["temperature"] == "COLD" for l in leads_cold)
    assert any(l["lead_id"] == "OB-2026-900022" for l in leads_cold)


@pytest.mark.asyncio
async def test_lead_not_found_returns_404(auth_client_sales: AsyncClient):
    """Verify requesting or updating a non-existent lead returns 404."""
    resp_get = await auth_client_sales.get("/v1/leads/OB-2026-999999")
    assert resp_get.status_code == 404

    resp_log = await auth_client_sales.post("/v1/leads/OB-2026-999999/log-action", json={
        "action_type": "CALL",
        "outcome": "Attempted",
        "stage": "ATTEMPTING",
    })
    assert resp_log.status_code == 404


@pytest.mark.asyncio
async def test_full_buyer_pipeline_progression(auth_client_sales: AsyncClient):
    """Verify end-to-end buyer pipeline progression:
    NEW -> ATTEMPTING -> CONNECTED -> REQ_CAPTURED -> QUALIFIED -> MEETING -> SITE_VISIT -> NEGOTIATION -> WON."""
    now = datetime.now(timezone.utc)

    # 1. New Lead
    create_resp = await auth_client_sales.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "Pipeline Journey Lead",
        "mobile": "9829080001",
        "lead_type": "BUYER",
    })
    lead_id = create_resp.json()["lead_id"]
    lead_pk = create_resp.json().get("id")

    # 2. Transition to ATTEMPTING (no follow up or temp strictly required)
    r1 = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Ringing",
        "stage": "ATTEMPTING",
    })
    assert r1.status_code == 200
    assert r1.json()["stage"] == "ATTEMPTING"

    # 3. Transition to CONNECTED (requires temp & follow_up_date)
    f_date = (now + timedelta(days=2)).isoformat()
    r2 = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Connected",
        "stage": "CONNECTED",
        "temperature": "WARM",
        "follow_up_date": f_date,
    })
    assert r2.status_code == 200
    assert r2.json()["stage"] == "CONNECTED"
    assert r2.json()["temperature"] == "WARM"

    # 4. Transition to REQ_CAPTURED
    r3 = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "REQUIREMENT",
        "outcome": "Requirements Recorded",
        "note": "Looking for 3BHK Apartment under 80 Lakhs in Alwar",
        "stage": "REQ_CAPTURED",
        "temperature": "HOT",
        "follow_up_date": (now + timedelta(days=3)).isoformat(),
    })
    assert r3.status_code == 200
    assert r3.json()["stage"] == "REQ_CAPTURED"

    # 5. Transition to QUALIFIED
    r4 = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Pre-qualified",
        "stage": "QUALIFIED",
        "temperature": "HOT",
        "follow_up_date": (now + timedelta(days=4)).isoformat(),
    })
    assert r4.status_code == 200
    assert r4.json()["stage"] == "QUALIFIED"

    # 6. Transition to MEETING
    r5 = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "MEETING",
        "outcome": "Meeting Scheduled",
        "stage": "MEETING",
        "temperature": "HOT",
        "follow_up_date": (now + timedelta(days=5)).isoformat(),
    })
    assert r5.status_code == 200
    assert r5.json()["stage"] == "MEETING"

    # 7. Transition to SITE_VISIT
    r6 = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "VISIT",
        "outcome": "Site Visit Completed",
        "stage": "SITE_VISIT",
        "temperature": "HOT",
        "follow_up_date": (now + timedelta(days=6)).isoformat(),
    })
    assert r6.status_code == 200
    assert r6.json()["stage"] == "SITE_VISIT"

    # 8. Transition to NEGOTIATION
    r7 = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Price Negotiation",
        "stage": "NEGOTIATION",
        "temperature": "HOT",
        "follow_up_date": (now + timedelta(days=7)).isoformat(),
    })
    assert r7.status_code == 200
    assert r7.json()["stage"] == "NEGOTIATION"

    # 9. Transition to WON (deal closed)
    r8 = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "MEETING",
        "outcome": "Registry Signed & Token Received",
        "note": "Deal closed for 3BHK flat",
        "stage": "WON",
    })
    assert r8.status_code == 200
    assert r8.json()["stage"] == "WON"

    # 10. Moving backwards from WON is disallowed
    r_won_back = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "stage": "ATTEMPTING",
    })
    assert r_won_back.status_code == 422

    # 11. Verify lead details and full activity timeline
    r_detail = await auth_client_sales.get(f"/v1/leads/{lead_id}")
    assert r_detail.status_code == 200
    lead_info = r_detail.json()
    assert lead_info["stage"] == "WON"
    # Activities should have at least 9 records (intake + 8 transitions)
    assert len(lead_info["activities"]) >= 9

    # 12. Also verify lookup by numeric ID
    numeric_id = str(lead_info["id"])
    r_num = await auth_client_sales.get(f"/v1/leads/{numeric_id}")
    assert r_num.status_code == 200
    assert r_num.json()["lead_id"] == lead_id


@pytest.mark.asyncio
async def test_invalid_terminal_stage_transitions(auth_client_sales: AsyncClient):
    """Verify illegal transitions (e.g., NEW directly to WON) are rejected with 422."""
    create_resp = await auth_client_sales.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "Direct Won Attempt",
        "mobile": "9829080002",
        "lead_type": "BUYER",
    })
    lead_id = create_resp.json()["lead_id"]

    # Direct jump to WON from NEW
    resp = await auth_client_sales.post(f"/v1/leads/{lead_id}/log-action", json={
        "action_type": "CALL",
        "outcome": "Closed",
        "stage": "WON",
    })
    assert resp.status_code == 422

