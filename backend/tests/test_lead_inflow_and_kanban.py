import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_manual_create_and_kanban_grouping(test_client: AsyncClient):
    # 1. Test manual creation
    resp = await test_client.post("/v1/leads/create", json={
        "contact_name": "Vikram Rathore",
        "mobile": "9829012345",
        "lead_type": "BUY",
        "lead_source_id": 1,
        "rating": 1,
        "indv_property_address": "Vaishali Nagar, Jaipur",
        "lead_remark": "Interested in 3 BHK Villa"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["contact_name"] == "Vikram Rathore"
    assert "lead_unique_id" in data
    lead_id = data["lead_unique_id"]

    # 2. Test kanban grouping
    kb_resp = await test_client.get("/v1/leads/kanban?type=buy")
    assert kb_resp.status_code == 200
    kb_data = kb_resp.json()
    assert "new" in kb_data
    assert "in_progress" in kb_data
    assert "site_visit" in kb_data
    assert "qualified" in kb_data
    assert "converted" in kb_data
    assert "disqualified" in kb_data
    assert any(l["contact_name"] == "Vikram Rathore" for l in kb_data["new"])

    # 3. Test stage transition
    patch_resp = await test_client.patch(f"/v1/leads/{lead_id}/stage", json={
        "lead_status": 1,
        "stage": 2,
        "remark": "Site visit planned for tomorrow"
    })
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["lead_status"] == 1
    assert updated["stage"] == 2

    # Verify moved to site_visit in kanban
    kb_resp2 = await test_client.get("/v1/leads/kanban?type=buy")
    kb_data2 = kb_resp2.json()
    assert any(l["contact_name"] == "Vikram Rathore" for l in kb_data2["site_visit"])


@pytest.mark.asyncio
async def test_bulk_csv_import(test_client: AsyncClient):
    csv_rows = [
        {"contact_name": "Anita Meena", "mobile": "9829011111", "lead_type": "RENT", "rating": 2},
        {"contact_name": "Sunil Sharma", "mobile": "9829022222", "lead_type": "PG", "rating": 3},
    ]
    resp = await test_client.post("/v1/leads/import-bulk", json={"leads": csv_rows})
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["imported_count"] == 2


@pytest.mark.asyncio
async def test_kanban_card_enrichment_fields_and_utc_dates(auth_client_md: AsyncClient, db_session):
    from datetime import datetime, timezone, timedelta
    from app.models.leads import Lead, TblLead, LeadActivity

    # 1. Create a TblLead-only manual lead (no paired Lead / Employee row)
    manual_resp = await auth_client_md.post("/v1/leads/create", json={
        "contact_name": "Karan Singh",
        "mobile": "9829099887",
        "lead_type": "BUY",
        "lead_source_id": 4,
        "rating": 3,
        "indv_property_address": "Bhagat Singh Circle, Sector 7, Alwar",
        "lead_remark": "Interested For 2 BHK Flat",
        "deal_final_price": 0,
    })
    assert manual_resp.status_code == 201
    manual_uid = manual_resp.json()["lead_unique_id"]

    # 2. Create a paired Lead + TblLead assigned to EMP-0001 with follow_up_date & activity
    followup_dt = datetime.now(timezone.utc) + timedelta(days=1)
    paired_lead = Lead(
        lead_id="OB-2026-990001",
        full_name="Priya Sharma",
        mobile="919829077665",
        lead_type="BUY",
        source="Website Callback",
        assigned_to="EMP-0001",
        stage="NEW",
        temperature="HOT",
        follow_up_date=followup_dt,
        preferred_locality="Tijara Road, Alwar",
    )
    db_session.add(paired_lead)
    await db_session.flush()
    db_session.add(LeadActivity(
        lead_id="OB-2026-990001",
        action_type="CALL",
        outcome="Site Visit Planned",
        note="Customer wants morning visit",
        logged_by="EMP-0001",
    ))
    db_session.add(TblLead(
        lead_unique_id="OB-2026-990001",
        contact_name="Priya Sharma",
        mobile="919829077665",
        lead_table_name="BUY",
        lead_source_id=4,
        rating=1,
        lead_status=0,
        stage=1,
        indv_property_address="Tijara Road, Alwar",
        nextfollowup_datetime=followup_dt,
        lead_remark="2 BHK Ready Flat",
    ))
    await db_session.commit()

    kb_resp = await auth_client_md.get("/v1/leads/kanban")
    assert kb_resp.status_code == 200
    cards = kb_resp.json()["new"]

    manual_card = next(c for c in cards if c["lead_unique_id"] == manual_uid)
    assert manual_card["requirement_title"] == "Interested For 2 BHK Flat"
    assert manual_card["source_name"] == "Request a Callback Form"
    assert manual_card["assigned_to_name"] == "Om Shiv Properties"
    assert manual_card["current_update"] == "General Follow-Up"
    assert manual_card["status_label"] == "New"
    assert manual_card["created_date"].endswith("+00:00") or manual_card["created_date"].endswith("Z")

    paired_card = next(c for c in cards if c["lead_unique_id"] == "OB-2026-990001")
    assert paired_card["assigned_to"] == "EMP-0001"
    assert paired_card["assigned_to_name"] == "Managing Director"
    assert paired_card["current_update"] == "Site Visit Planned"
    assert paired_card["followup_datetime"] is not None
    assert paired_card["followup_datetime"].endswith("+00:00") or paired_card["followup_datetime"].endswith("Z")

