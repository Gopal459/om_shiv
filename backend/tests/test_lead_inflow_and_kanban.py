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


@pytest.mark.asyncio
async def test_convert_lead_to_property_atomic_and_duplicate_guard(auth_client_md: AsyncClient, db_session):
    from sqlalchemy import select, func
    from app.models.properties import TblProperty

    prop_payload = {
        "property_type": 2,
        "looking_type": 1,
        "looking_subcat_type": 1,
        "transaction_type": 1,
        "source_type": 2,
        "source_owner_name": "Ramesh Seller",
        "source_owner_mobile": "9829055443",
        "sublocality_address": "Sector 7, Alwar",
        "location": "Bhagat Singh Circle, Alwar",
        "pincode": "301001",
        "expected_price": 5200000,
    }

    # 1. Missing lead -> 404 and zero TblProperty created
    missing_resp = await auth_client_md.post("/v1/leads/OB-9999-999999/convert-to-property", json=prop_payload)
    assert missing_resp.status_code == 404
    prop_count = (await db_session.execute(select(func.count()).select_from(TblProperty))).scalar_one()
    assert prop_count == 0

    # 2. Create active lead and convert to property
    create_resp = await auth_client_md.post("/v1/leads/create", json={
        "contact_name": "Ramesh Seller",
        "mobile": "9829055443",
        "lead_type": "BUY",
        "lead_source_id": 4,
        "rating": 2,
        "indv_property_address": "Sector 7, Alwar",
    })
    assert create_resp.status_code == 201
    lead_id = create_resp.json()["lead_unique_id"]

    conv_resp = await auth_client_md.post(f"/v1/leads/{lead_id}/convert-to-property", json=prop_payload)
    assert conv_resp.status_code == 201
    conv_data = conv_resp.json()
    assert conv_data["lead_id"] == lead_id
    assert conv_data["property_id"] > 0
    assert conv_data["propertyid_no"].startswith("PROP-") or conv_data["propertyid_no"].startswith("OM-") or len(conv_data["propertyid_no"]) > 3
    assert conv_data["stage"] == "WON"
    assert conv_data["lead_status"] == 5

    # 3. Duplicate conversion must be blocked (400) and leave TblProperty count at 1
    dup_resp = await auth_client_md.post(f"/v1/leads/{lead_id}/convert-to-property", json=prop_payload)
    assert dup_resp.status_code == 400
    prop_count_after = (await db_session.execute(select(func.count()).select_from(TblProperty))).scalar_one()
    assert prop_count_after == 1

    # 4. Lead detail exposes linked property metadata & CONVERTED_TO_PROPERTY activity
    detail_resp = await auth_client_md.get(f"/v1/leads/{lead_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["property_id"] == conv_data["property_id"]
    assert detail["property_idno"] == conv_data["propertyid_no"]
    assert detail["related_listing_id"] == conv_data["propertyid_no"]
    assert detail["stage"] == "WON"
    assert any(a["action_type"] == "CONVERTED_TO_PROPERTY" for a in detail["activities"])


@pytest.mark.asyncio
async def test_convert_single_table_leads_synthetic_prefix_and_no_pk_collision(auth_client_md: AsyncClient, db_session):
    from sqlalchemy import select
    from app.models.leads import Lead, TblLead

    prop_payload = {
        "property_type": 2,
        "looking_type": 1,
        "looking_subcat_type": 1,
        "transaction_type": 1,
        "source_type": 2,
        "source_owner_name": "Legacy Owner",
        "source_owner_mobile": "9829011223",
        "sublocality_address": "Moti Doongri, Alwar",
        "location": "Alwar",
        "pincode": "301001",
        "expected_price": 3800000,
    }

    # 1. TblLead-only with lead_unique_id=None + unrelated Lead sharing same numeric PK (999)
    tbl_only = TblLead(
        leads_id=999,
        lead_unique_id=None,
        contact_name="Legacy TblOnly",
        mobile="9829011223",
        lead_table_name="BUY",
        rating=2,
        lead_status=0,
        stage=1,
    )
    unrelated_lead = Lead(
        id=999,
        lead_id="OB-2026-888999",
        full_name="Unrelated Modern Lead",
        mobile="919999888777",
        lead_type="BUY",
        source="MANUAL",
        stage="NEW",
    )
    db_session.add_all([tbl_only, unrelated_lead])
    await db_session.commit()

    # Access & convert via synthetic LEAD-999 identifier
    get_resp = await auth_client_md.get("/v1/leads/LEAD-999")
    assert get_resp.status_code == 200
    assert get_resp.json()["full_name"] == "Legacy TblOnly"

    conv_resp = await auth_client_md.post("/v1/leads/LEAD-999/convert-to-property", json=prop_payload)
    assert conv_resp.status_code == 201
    await db_session.refresh(unrelated_lead)
    # Unrelated modern Lead#999 must NOT be mutated by converting TblLead#999
    assert unrelated_lead.related_listing_id is None
    assert unrelated_lead.stage == "NEW"

    # 2. Lead-only (no TblLead row) conversion with actor attribution
    lead_only = Lead(
        lead_id="OB-2026-777001",
        full_name="Modern Only Seller",
        mobile="919829066554",
        lead_type="RENT",
        source="PROPERTY_INQUIRY",
        stage="NEW",
    )
    db_session.add(lead_only)
    await db_session.commit()

    rent_payload = {
        "property_type": 1,
        "looking_type": 1,
        "looking_subcat_type": 1,
        "rentalallow_forid": "Family",
        "source_type": 2,
        "source_owner_name": "Modern Only Seller",
        "source_owner_mobile": "9829066554",
        "sublocality_address": "Tijara Road, Alwar",
        "location": "Tijara Road, Alwar",
        "pincode": "301001",
        "expected_price": 18000,
    }
    conv_modern = await auth_client_md.post("/v1/leads/OB-2026-777001/convert-to-property", json=rent_payload)
    assert conv_modern.status_code == 201
    detail_modern = (await auth_client_md.get("/v1/leads/OB-2026-777001")).json()
    assert detail_modern["stage"] == "WON"
    assert detail_modern["related_listing_id"] == conv_modern.json()["propertyid_no"]
    act = next(a for a in detail_modern["activities"] if a["action_type"] == "CONVERTED_TO_PROPERTY")
    assert act["logged_by"] == "EMP-0001"


@pytest.mark.asyncio
async def test_convert_lead_to_property_rollback_on_midflight_error(auth_client_md: AsyncClient, db_session, monkeypatch):
    from sqlalchemy import select, func
    from app.models.leads import Lead
    from app.models.properties import TblProperty
    import app.api.v1.endpoints.leads as leads_ep

    lead_row = Lead(
        lead_id="OB-2026-777002",
        full_name="Rollback Seller",
        mobile="919829033221",
        lead_type="BUY",
        source="MANUAL",
        stage="NEW",
    )
    db_session.add(lead_row)
    await db_session.commit()

    def boom_activity(*args, **kwargs):
        raise RuntimeError("Simulated activity failure")

    monkeypatch.setattr(leads_ep, "LeadActivity", boom_activity)

    prop_payload = {
        "property_type": 2,
        "looking_type": 1,
        "looking_subcat_type": 1,
        "transaction_type": 1,
        "source_type": 2,
        "source_owner_name": "Rollback Seller",
        "source_owner_mobile": "9829033221",
        "sublocality_address": "Alwar",
        "location": "Alwar",
        "pincode": "301001",
        "expected_price": 4500000,
    }
    with pytest.raises(RuntimeError, match="Simulated activity failure"):
        await auth_client_md.post("/v1/leads/OB-2026-777002/convert-to-property", json=prop_payload)

    prop_count = (await db_session.execute(select(func.count()).select_from(TblProperty))).scalar_one()
    assert prop_count == 0


@pytest.mark.asyncio
async def test_lead_assignees_endpoint_and_route_ordering(auth_client_md: AsyncClient, test_client: AsyncClient, db_session):
    from app.models.identity import Employee, Role, Department
    from sqlalchemy import select

    unauth = await test_client.get("/v1/leads/assignees")
    assert unauth.status_code == 401

    dept_id = (await db_session.execute(select(Department.id))).scalars().first()
    role_id = (await db_session.execute(select(Role.id))).scalars().first()

    inactive_emp = Employee(
        employee_id="EMP-9999",
        name="Inactive Staff",
        email="inactive@omshiv.com",
        mobile="9829099999",
        department_id=dept_id,
        role_id=role_id,
        is_active=False,
    )
    db_session.add(inactive_emp)
    await db_session.commit()

    resp = await auth_client_md.get("/v1/leads/assignees")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    ids = [i["employee_id"] for i in items]
    assert "EMP-0001" in ids
    assert "EMP-9999" not in ids


@pytest.mark.asyncio
async def test_manual_lead_create_with_staff_customer_type_and_reference(auth_client_md: AsyncClient, db_session):
    from sqlalchemy import select
    from app.models.leads import Lead, TblLead

    # 1. Broker lead assigned to EMP-0001 with Relative reference (and whitespace/hyphenated mobile)
    resp = await auth_client_md.post("/v1/leads/create", json={
        "contact_name": "Ramesh Broker",
        "mobile": "9829012345",
        "lead_type": "BUY",
        "lead_source_id": 12,
        "rating": 1,
        "assigned_to": "EMP-0001",
        "customer_type": "broker",
        "reference_type": "relative",
        "refer_by_name": "  Suresh Sharma  ",
        "refer_by_mobile": "+91 98290-55555",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["customer_type"] == "BROKER"
    assert data["assigned_to"] == "EMP-0001"
    assert data["reference_relation_by"] == "Relative"
    assert data["refer_by_name"] == "Suresh Sharma"
    assert data["refer_by_mobile"] == "+91 98290-55555"

    uid = data["lead_unique_id"]
    lead_row = (await db_session.execute(select(Lead).where(Lead.lead_id == uid))).scalar_one()
    tbl_row = (await db_session.execute(select(TblLead).where(TblLead.lead_unique_id == uid))).scalar_one()
    assert lead_row.assigned_to == "EMP-0001"
    assert lead_row.customer_type == "BROKER"
    assert tbl_row.customer_type == "BROKER"
    assert tbl_row.dealer_have == 1
    assert tbl_row.assign_franchstaff_id > 0
    assert tbl_row.assignfranchiseestaff_date is not None
    assert tbl_row.assignfranchiseestaff_date.tzinfo is None
    assert tbl_row.reference_relation_by == "Relative"
    assert tbl_row.refer_by_name == "Suresh Sharma"

    # Detail endpoint exposes customer_type + reference_relation_by
    detail = (await auth_client_md.get(f"/v1/leads/{uid}")).json()
    assert detail["customer_type"] == "BROKER"
    assert detail["reference_relation_by"] == "Relative"
    assert detail["refer_by_name"] == "Suresh Sharma"

    # 2. Optional empty assigned_to creates unassigned Investor lead cleanly
    resp2 = await auth_client_md.post("/v1/leads/create", json={
        "contact_name": "Anita Investor",
        "mobile": "9829022334",
        "lead_type": "BUY",
        "assigned_to": "",
        "customer_type": "INVESTOR",
        "reference_type": "  ",
        "refer_by_name": "   ",
    })
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert data2["assigned_to"] is None
    assert data2["customer_type"] == "INVESTOR"
    assert data2["reference_relation_by"] is None
    uid2 = data2["lead_unique_id"]
    tbl_row2 = (await db_session.execute(select(TblLead).where(TblLead.lead_unique_id == uid2))).scalar_one()
    assert tbl_row2.dealer_have == 2
    assert tbl_row2.assign_franchstaff_id == 0


@pytest.mark.asyncio
async def test_manual_lead_create_validation_and_invalid_assignee(auth_client_md: AsyncClient, db_session):
    from sqlalchemy import select, func
    from app.models.leads import Lead, TblLead
    from app.models.identity import Employee, Role, Department

    dept_id = (await db_session.execute(select(Department.id))).scalars().first()
    role_id = (await db_session.execute(select(Role.id))).scalars().first()
    db_session.add(Employee(
        employee_id="EMP-8888",
        name="Inactive Assignee",
        email="inactive8888@omshiv.com",
        mobile="9829088888",
        department_id=dept_id,
        role_id=role_id,
        is_active=False,
    ))
    await db_session.commit()

    # Unknown assignee returns 400 and inserts zero rows
    bad_assign = await auth_client_md.post("/v1/leads/create", json={
        "contact_name": "Bad Assignee Lead",
        "mobile": "9829088776",
        "assigned_to": "EMP-DOES-NOT-EXIST",
    })
    assert bad_assign.status_code == 400
    inactive_assign = await auth_client_md.post("/v1/leads/create", json={
        "contact_name": "Inactive Assignee Lead",
        "mobile": "9829088779",
        "assigned_to": "EMP-8888",
    })
    assert inactive_assign.status_code == 400
    assert (await db_session.execute(select(func.count()).select_from(Lead))).scalar_one() == 0
    assert (await db_session.execute(select(func.count()).select_from(TblLead))).scalar_one() == 0

    # Invalid customer_type returns 422
    bad_cust = await auth_client_md.post("/v1/leads/create", json={
        "contact_name": "Bad Cust Type",
        "mobile": "9829088777",
        "customer_type": "ALIEN",
    })
    assert bad_cust.status_code == 422

    # Invalid reference_type returns 422
    bad_ref = await auth_client_md.post("/v1/leads/create", json={
        "contact_name": "Bad Ref Type",
        "mobile": "9829088778",
        "reference_type": "STRANGER",
    })
    assert bad_ref.status_code == 422



