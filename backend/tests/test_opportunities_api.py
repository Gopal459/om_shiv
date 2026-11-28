import importlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
from app.db.migrations.runner import MIGRATION_STEPS
from app.models.opportunities import (
    DISQUALIFIED_REASONS,
    OPPORTUNITY_STATUSES,
    OpportunityActivity,
    OpportunityLocation,
    OpportunityRescheduleLog,
    OpportunitySequence,
    TblOpportunity,
)


def test_opportunities_models_registered_in_metadata():
    expected_tables = {
        "opportunity_sequences",
        "tbl_opportunities",
        "tbl_opportunity_locations",
        "tbl_opportunity_reschedules",
        "tbl_opportunity_activities",
    }
    assert expected_tables.issubset(set(Base.metadata.tables.keys()))
    assert "app.db.migrations.0015_opportunities_schema" in MIGRATION_STEPS

    assert OPPORTUNITY_STATUSES == {
        1: "In Progress",
        2: "Disqualified",
        4: "Qualified (Deal Scheduled)",
        5: "Closed",
    }
    assert DISQUALIFIED_REASONS == {
        1: "Inaccurate Data",
        2: "Not Interested",
        3: "Not Responding",
        4: "Disconnecting Call",
        5: "Rejected",
        6: "Other",
        7: "Not Available Property",
    }


@pytest.mark.asyncio
async def test_opportunities_models_defaults_and_relationships(db_session):
    seq = OpportunitySequence(year=2026)
    db_session.add(seq)
    await db_session.flush()
    assert seq.last_sequence == 0

    opp = TblOpportunity(
        contact_name="Aarav Sharma",
        mobile="9829011223",
    )
    db_session.add(opp)
    await db_session.flush()
    opp.opportunity_code = f"OPP-2026-{opp.opportunity_id:06d}"
    await db_session.commit()
    await db_session.refresh(opp)

    assert opp.opportunity_code == f"OPP-2026-{opp.opportunity_id:06d}"
    assert opp.customer_type == "END_USER"
    assert opp.property_type == 2
    assert opp.looking_type == 1
    assert opp.looking_subcat_type == 1
    assert opp.budget_from == Decimal("0")
    assert opp.budget_to == Decimal("0")
    assert opp.area_from == Decimal("0")
    assert opp.area_to == Decimal("0")
    assert opp.area_unit == "Sq.Ft"
    assert opp.bhk == 0
    assert opp.loanable == "MAYBE"
    assert opp.assign_franch_id == 0
    assert opp.assign_franchstaff_id == 0
    assert opp.lead_status == 1
    assert opp.lead_open == 1
    assert opp.calls_status == 0
    assert opp.disqualified_reason == 0
    assert opp.is_propira_property is False
    assert opp.created_at is not None
    assert opp.updated_at is not None

    loc = OpportunityLocation(
        opportunity_id=opp.opportunity_id,
        locality_name="Vaishali Nagar",
        latitude=Decimal("26.912400"),
        longitude=Decimal("75.787300"),
    )
    reschedule = OpportunityRescheduleLog(
        opportunity_id=opp.opportunity_id,
        old_followup_datetime=None,
        new_followup_datetime=datetime.now(timezone.utc) + timedelta(days=1),
        current_update="Call Back Later",
        remark="Client asked to call tomorrow",
        rescheduled_by="EMP-0001",
    )
    activity = OpportunityActivity(
        opportunity_id=opp.opportunity_id,
        action_type="CREATED",
        note="Opportunity created",
        status_before=None,
        status_after=1,
        performed_by="EMP-0001",
    )
    db_session.add_all([loc, reschedule, activity])
    await db_session.commit()

    await db_session.refresh(opp, attribute_names=["locations", "reschedules", "activities"])
    assert len(opp.locations) == 1
    assert opp.locations[0].radius_km == 10
    assert len(opp.reschedules) == 1
    assert len(opp.activities) == 1


@pytest.mark.asyncio
async def test_migration_0015_idempotent():
    migration_0015 = importlib.import_module("app.db.migrations.0015_opportunities_schema")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    CREATE TABLE employees (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id VARCHAR(32) UNIQUE NOT NULL
                    )
                    """
                )
            )

        # First upgrade
        await migration_0015.upgrade(engine)
        # Second upgrade must succeed idempotently
        await migration_0015.upgrade(engine)

        async with engine.connect() as conn:
            res = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            table_names = {row[0] for row in res.fetchall()}
            assert {
                "opportunity_sequences",
                "tbl_opportunities",
                "tbl_opportunity_locations",
                "tbl_opportunity_reschedules",
                "tbl_opportunity_activities",
            }.issubset(table_names)
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Task 2 API & Service Tests (TDD)
# ---------------------------------------------------------------------------


async def _create_employee_with_token(
    db_session,
    *,
    employee_id: str,
    name: str,
    mobile: str,
    role_code: str,
    role_name: str,
    dept_code: str = "SALES",
    permissions: dict | None = None,
):
    from sqlalchemy import select
    from app.core.security import create_access_token
    from app.models.identity import Department, Employee, Role

    dept = (
        await db_session.execute(select(Department).where(Department.code == dept_code))
    ).scalar_one_or_none()
    if not dept:
        dept = Department(name=dept_code.title(), code=dept_code)
        db_session.add(dept)
        await db_session.flush()

    role = (
        await db_session.execute(select(Role).where(Role.code == role_code))
    ).scalar_one_or_none()
    if not role:
        role = Role(
            department_id=dept.id,
            name=role_name,
            code=role_code,
            permissions=permissions or {"leads": ["read", "write"]},
        )
        db_session.add(role)
        await db_session.flush()

    emp = (
        await db_session.execute(select(Employee).where(Employee.employee_id == employee_id))
    ).scalar_one_or_none()
    if not emp:
        emp = Employee(
            employee_id=employee_id,
            name=name,
            email=f"{employee_id.lower()}@omshiv.com",
            mobile=mobile,
            department_id=dept.id,
            role_id=role.id,
            is_active=True,
        )
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

    token = create_access_token(
        {
            "sub": employee_id,
            "employee_id": emp.id,
            "name": emp.name,
            "mobile": emp.mobile,
            "role": role_code,
            "department": dept_code,
            "permissions": permissions or {"leads": ["read", "write"]},
        }
    )
    return emp, {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_opportunities_auth_and_role_scoping(test_client, auth_client_md, auth_client_sales, db_session):
    # Unauthenticated calls must fail with 401
    for path in (
        "/v1/opportunities",
        "/v1/opportunities/dashboard",
        "/v1/opportunities/export",
        "/v1/opportunities/1",
        "/v1/opportunities/1/related-properties",
    ):
        resp = await test_client.get(path)
        assert resp.status_code == 401, f"Expected 401 on {path}, got {resp.status_code}"

    # Create another sales rep EMP-0003
    emp3, emp3_headers = await _create_employee_with_token(
        db_session,
        employee_id="EMP-0003",
        name="Priya Verma",
        mobile="9829099903",
        role_code="SALES_EXEC",
        role_name="Sales Executive",
    )

    # EMP-0002 creates an opportunity (assigned to self)
    create_resp2 = await auth_client_sales.post(
        "/v1/opportunities",
        json={
            "contact_name": "Rep Two Buyer",
            "mobile": "9829011102",
            "customer_type": "END_USER",
            "property_type": 2,
            "looking_type": 1,
            "looking_subcat_type": 1,
            "budget_from": 3000000,
            "budget_to": 5000000,
        },
    )
    assert create_resp2.status_code == 201
    opp2_id = create_resp2.json()["opportunity_id"]
    assert create_resp2.json()["assigned_to"] == "EMP-0002"

    # MD creates an opportunity assigned to EMP-0003
    create_resp3 = await auth_client_md.post(
        "/v1/opportunities",
        json={
            "contact_name": "Rep Three Buyer",
            "mobile": "9829011103",
            "assigned_to": emp3.employee_id,
        },
    )
    assert create_resp3.status_code == 201
    opp3_id = create_resp3.json()["opportunity_id"]
    assert create_resp3.json()["assigned_to"] == "EMP-0003"

    # EMP-0002 sees only own in list & dashboard, and gets 403 on EMP-0003's opp
    list_sales = await auth_client_sales.get("/v1/opportunities?tab=all")
    assert list_sales.status_code == 200
    assert list_sales.json()["total"] == 1
    assert list_sales.json()["items"][0]["opportunity_id"] == opp2_id

    dash_sales = await auth_client_sales.get("/v1/opportunities/dashboard")
    assert dash_sales.status_code == 200
    assert dash_sales.json()["counts"]["all"] == 1

    forbidden_detail = await auth_client_sales.get(f"/v1/opportunities/{opp3_id}")
    assert forbidden_detail.status_code == 403
    forbidden_rel = await auth_client_sales.get(f"/v1/opportunities/{opp3_id}/related-properties")
    assert forbidden_rel.status_code == 403

    # EMP-0003 sees own opp
    list_emp3 = await test_client.get("/v1/opportunities?tab=all", headers=emp3_headers)
    assert list_emp3.status_code == 200
    assert list_emp3.json()["total"] == 1
    assert list_emp3.json()["items"][0]["opportunity_id"] == opp3_id

    # MD sees both
    list_md = await auth_client_md.get("/v1/opportunities?tab=all")
    assert list_md.status_code == 200
    assert list_md.json()["total"] == 2
    dash_md = await auth_client_md.get("/v1/opportunities/dashboard")
    assert dash_md.status_code == 200
    assert dash_md.json()["counts"]["all"] == 2

    # 404 on missing and soft-deleted
    missing_resp = await auth_client_md.get("/v1/opportunities/999999")
    assert missing_resp.status_code == 404

    from sqlalchemy import select
    opp_row = (
        await db_session.execute(select(TblOpportunity).where(TblOpportunity.opportunity_id == opp3_id))
    ).scalar_one()
    opp_row.deleted_at = datetime.now(timezone.utc)
    await db_session.commit()

    deleted_resp = await auth_client_md.get(f"/v1/opportunities/{opp3_id}")
    assert deleted_resp.status_code == 404


@pytest.mark.asyncio
async def test_opportunities_create_dashboard_tabs_and_search(auth_client_md, db_session):
    from app.services.callback_service import _ist_today_bounds_utc

    # Validation checks
    bad_name = await auth_client_md.post("/v1/opportunities", json={"contact_name": "   ", "mobile": "9829011223"})
    assert bad_name.status_code == 422

    bad_mobile = await auth_client_md.post("/v1/opportunities", json={"contact_name": "Test", "mobile": "123"})
    assert bad_mobile.status_code == 422

    bad_budget = await auth_client_md.post(
        "/v1/opportunities",
        json={"contact_name": "Test", "mobile": "9829011223", "budget_from": 5000000, "budget_to": 2000000},
    )
    assert bad_budget.status_code == 422

    bad_area = await auth_client_md.post(
        "/v1/opportunities",
        json={"contact_name": "Test", "mobile": "9829011223", "area_from": 2000, "area_to": 1000},
    )
    assert bad_area.status_code == 422

    # 1. New (open, status=1, calls_status=0) with locations
    r1 = await auth_client_md.post(
        "/v1/opportunities",
        json={
            "contact_name": "Karan Malhotra",
            "mobile": "9829055501",
            "email": "karan@example.com",
            "customer_type": "INVESTOR",
            "property_type": 2,
            "looking_type": 1,
            "looking_subcat_type": 1,
            "budget_from": 4000000,
            "budget_to": 7000000,
            "area_from": 1200,
            "area_to": 1800,
            "area_unit": "Sq.Ft",
            "bhk": 3,
            "loanable": "YES",
            "remark": "Needs corner park facing flat",
            "locations": [
                {"locality_name": "Vaishali Nagar", "latitude": 26.9124, "longitude": 75.7873, "radius_km": 5},
                {"locality_name": "Mansarovar", "latitude": 26.8686, "longitude": 75.7640, "radius_km": 8},
            ],
        },
    )
    assert r1.status_code == 201
    d1 = r1.json()
    year = datetime.now(timezone.utc).year
    assert d1["opportunity_code"] == f"OPP-{year}-000001"
    assert d1["lead_status"] == 1
    assert d1["lead_open"] == 1
    assert d1["calls_status"] == 0
    assert len(d1["locations"]) == 2
    assert len(d1["activities"]) == 1
    assert d1["activities"][0]["action_type"] == "CREATED"

    # Create additional opportunities for today, missing, qualified_propira, disqualified, closed
    now_utc = datetime.now(timezone.utc)
    ist_start, ist_end = _ist_today_bounds_utc(now_utc)
    today_dt = ist_start + timedelta(hours=23, minutes=0)  # 11 PM IST – always future today

    opp_today = TblOpportunity(
        opportunity_code=f"OPP-{year}-000090",
        contact_name="Today Followup Client",
        mobile="919829055502",
        lead_status=1,
        lead_open=1,
        calls_status=1,
        followup_datetime=today_dt,
        assigned_to="EMP-0001",
    )
    opp_missing = TblOpportunity(
        opportunity_code=f"OPP-{year}-000091",
        contact_name="Overdue Missing Client",
        mobile="919829055503",
        lead_status=1,
        lead_open=1,
        calls_status=1,
        followup_datetime=now_utc - timedelta(days=2),
        assigned_to="EMP-0001",
    )
    opp_qual_propira = TblOpportunity(
        opportunity_code=f"OPP-{year}-000092",
        contact_name="Qualified Propira Client",
        mobile="919829055504",
        lead_status=4,
        lead_open=1,
        calls_status=1,
        is_propira_property=True,
        matched_property_id=101,
        matched_property_code="PR101",
        followup_datetime=now_utc + timedelta(days=5),
        assigned_to="EMP-0001",
    )
    opp_disq = TblOpportunity(
        opportunity_code=f"OPP-{year}-000093",
        contact_name="Disqualified Client",
        mobile="919829055505",
        lead_status=2,
        lead_open=0,
        calls_status=1,
        disqualified_reason=2,
        assigned_to="EMP-0001",
    )
    opp_closed = TblOpportunity(
        opportunity_code=f"OPP-{year}-000094",
        contact_name="Closed Deal Client",
        mobile="919829055506",
        lead_status=5,
        lead_open=0,
        calls_status=1,
        assigned_to="EMP-0001",
    )
    db_session.add_all([opp_today, opp_missing, opp_qual_propira, opp_disq, opp_closed])
    await db_session.commit()

    # Verify dashboard KPIs & chart_breakdown
    dash = await auth_client_md.get("/v1/opportunities/dashboard")
    assert dash.status_code == 200
    body = dash.json()
    assert body["counts"] == {
        "new": 1,
        "today": 1,
        "open": 4,
        "missing": 1,
        "in_progress": 3,
        "closed": 2,
        "all": 6,
    }
    assert body["chart_breakdown"] == {
        "total": 6,
        "open": 3,
        "disqualified": 1,
        "qualified_propira": 1,
        "qualified_other": 0,
        "closed": 1,
    }

    # Verify all 7 tabs
    tab_expected = {
        "new": 1,
        "today": 1,
        "open": 4,
        "missing": 1,
        "in_progress": 3,
        "closed": 2,
        "all": 6,
    }
    for tab, expected_total in tab_expected.items():
        res = await auth_client_md.get(f"/v1/opportunities?tab={tab}")
        assert res.status_code == 200
        assert res.json()["total"] == expected_total, f"Tab {tab} expected {expected_total}, got {res.json()['total']}"

    # Search by locality_name, opportunity_code, remark, email
    for term in ("vaishali", f"OPP-{year}-000001", "corner park", "karan@example.com"):
        s_res = await auth_client_md.get(f"/v1/opportunities?tab=all&search={term}")
        assert s_res.status_code == 200
        assert s_res.json()["total"] == 1
        assert s_res.json()["items"][0]["contact_name"] == "Karan Malhotra"


@pytest.mark.asyncio
async def test_lead_to_opportunity_conversion_and_guards(auth_client_md, db_session):
    from sqlalchemy import select
    from app.models.leads import Lead, LeadActivity, TblLead

    # 1. Missing source_lead_id -> 404
    r_missing = await auth_client_md.post(
        "/v1/opportunities",
        json={"source_lead_id": "OB-2026-999999", "contact_name": "Ghost", "mobile": "9829011111"},
    )
    assert r_missing.status_code == 404

    # 2. Disqualified TblLead (lead_status == 2) -> 400 with zero partial mutations
    t_disq = TblLead(
        lead_unique_id="OB-2026-000101",
        contact_name="Disq Lead",
        mobile="919829010101",
        lead_status=2,
        lead_open=0,
    )
    # 3. Property-converted TblLead (property_id > 0) -> 400
    t_prop = TblLead(
        lead_unique_id="OB-2026-000102",
        contact_name="Prop Lead",
        mobile="919829010102",
        property_id=55,
        lead_status=5,
        lead_open=0,
    )
    # 4. Closed WON Lead -> 400
    l_won = Lead(
        lead_id="OB-2026-000103",
        full_name="Won Lead",
        mobile="919829010103",
        stage="WON",
    )
    t_won = TblLead(
        lead_unique_id="OB-2026-000103",
        contact_name="Won Lead",
        mobile="919829010103",
        lead_status=1,
    )
    # 5. Valid open Lead + TblLead pair
    l_valid = Lead(
        lead_id="OB-2026-000104",
        full_name="Valid Buyer Lead",
        mobile="919829010104",
        email="buyer@example.com",
        stage="CONNECTED",
    )
    t_valid = TblLead(
        lead_unique_id="OB-2026-000104",
        contact_name="Valid Buyer Lead",
        mobile="919829010104",
        email="buyer@example.com",
        lead_status=1,
        lead_open=1,
    )
    db_session.add_all([t_disq, t_prop, l_won, t_won, l_valid, t_valid])
    await db_session.commit()

    for bad_uid in ("OB-2026-000101", "OB-2026-000102", "OB-2026-000103"):
        bad_resp = await auth_client_md.post(
            "/v1/opportunities",
            json={"source_lead_id": bad_uid, "contact_name": "Blocked", "mobile": "9829010101"},
        )
        assert bad_resp.status_code == 400

    # Assert zero partial DB mutations (no OpportunitySequence or TblOpportunity created)
    assert (await db_session.execute(select(OpportunitySequence))).scalars().all() == []
    assert (await db_session.execute(select(TblOpportunity))).scalars().all() == []

    # Now convert the valid lead
    ok_resp = await auth_client_md.post(
        "/v1/opportunities",
        json={
            "source_lead_id": "OB-2026-000104",
            "contact_name": "Valid Buyer Lead",
            "mobile": "9829010104",
            "customer_type": "END_USER",
            "property_type": 2,
            "looking_type": 1,
            "looking_subcat_type": 2,
            "budget_from": 4500000,
            "budget_to": 6500000,
            "locations": [{"locality_name": "Jagatpura"}],
        },
    )
    assert ok_resp.status_code == 201
    opp_data = ok_resp.json()
    assert opp_data["source_lead_id"] == "OB-2026-000104"

    await db_session.refresh(t_valid)
    await db_session.refresh(l_valid)
    assert t_valid.opportunity_converted == 1
    assert t_valid.opportunity_id == opp_data["opportunity_id"]
    assert t_valid.opportunity_datetime is not None
    assert t_valid.lead_status == 4
    assert l_valid.stage == "QUALIFIED"

    act = (
        await db_session.execute(
            select(LeadActivity).where(
                LeadActivity.lead_id == "OB-2026-000104",
                LeadActivity.action_type == "CONVERTED_TO_OPPORTUNITY",
            )
        )
    ).scalar_one_or_none()
    assert act is not None

    # Duplicate conversion attempt must fail with 400 and leave sequence untouched
    dup_resp = await auth_client_md.post(
        "/v1/opportunities",
        json={"source_lead_id": "OB-2026-000104", "contact_name": "Dup", "mobile": "9829010104"},
    )
    assert dup_resp.status_code == 400
    seqs = (await db_session.execute(select(OpportunitySequence))).scalars().all()
    assert len(seqs) == 1 and seqs[0].last_sequence == 1


@pytest.mark.asyncio
async def test_opportunity_put_update_and_locked_guard(auth_client_md, auth_client_sales, db_session):
    create_resp = await auth_client_sales.post(
        "/v1/opportunities",
        json={
            "contact_name": "Editable Client",
            "mobile": "9829022201",
            "budget_from": 2000000,
            "budget_to": 3000000,
            "locations": [{"locality_name": "C-Scheme"}],
        },
    )
    assert create_resp.status_code == 201
    opp_id = create_resp.json()["opportunity_id"]

    # Update specs + replace locations
    put_resp = await auth_client_sales.put(
        f"/v1/opportunities/{opp_id}",
        json={
            "contact_name": "Edited Client Name",
            "mobile": "9829022201",
            "budget_from": 3500000,
            "budget_to": 5500000,
            "bhk": 3,
            "loanable": "YES",
            "locations": [
                {"locality_name": "Vaishali Nagar", "radius_km": 12},
                {"locality_name": "Bapu Nagar", "radius_km": 6},
            ],
        },
    )
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["contact_name"] == "Edited Client Name"
    assert float(updated["budget_to"]) == 5500000.0
    assert updated["bhk"] == 3
    assert [loc["locality_name"] for loc in updated["locations"]] == ["Vaishali Nagar", "Bapu Nagar"]
    assert updated["activities"][0]["action_type"] == "UPDATED"

    # Lock the opportunity (lead_open = 0) and confirm PUT is blocked with 400
    from sqlalchemy import select
    opp_row = (
        await db_session.execute(select(TblOpportunity).where(TblOpportunity.opportunity_id == opp_id))
    ).scalar_one()
    opp_row.lead_open = 0
    opp_row.lead_status = 2
    await db_session.commit()

    locked_resp = await auth_client_md.put(
        f"/v1/opportunities/{opp_id}",
        json={"contact_name": "Should Fail"},
    )
    assert locked_resp.status_code == 400


@pytest.mark.asyncio
async def test_related_properties_matching_and_cp_masking(test_client, auth_client_md, db_session):
    from app.models.franchise import ChannelPartner
    from app.models.properties import TblProperty

    now_utc = datetime.now(timezone.utc)

    # Create properties: 2 matching (1 closer geo, 1 further text fallback), and several excluded
    p_near = TblProperty(
        propertyid_no="PR-NEAR",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        noof_bhk=3,
        expected_price=5000000,
        location="Vaishali Nagar",
        location_lat="26.9150",
        location_long="75.7890",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
        source_owner_name="Owner Near",
        source_owner_mobile="9829090001",
        source_owner_email="near@owner.com",
        expiarydate=now_utc + timedelta(days=30),
    )
    p_far_geo = TblProperty(
        propertyid_no="PR-FAR-GEO",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        noof_bhk=3,
        expected_price=5500000,
        location="Ajmer Road",
        location_lat="26.9000",
        location_long="75.7400",  # ~4.9 km from 26.9124, 75.7873 (within 10 km)
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
        source_owner_name="Owner Far Geo",
        source_owner_mobile="9829090002",
        source_owner_email="fargeo@owner.com",
        expiarydate=None,
    )
    p_text_fallback = TblProperty(
        propertyid_no="PR-TEXT",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        noof_bhk=3,
        expected_price=4800000,
        sublocality_address="Sector 4, Vaishali Nagar Extension",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
        source_owner_name="Owner Text",
        source_owner_mobile="9829090003",
    )
    # Excluded properties
    p_sold = TblProperty(
        propertyid_no="PR-SOLD",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        noof_bhk=3,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=1,
        sold_status=1,
        recyclebin_status=0,
    )
    p_unverified = TblProperty(
        propertyid_no="PR-UNVER",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        noof_bhk=3,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=0,
        sold_status=0,
        recyclebin_status=0,
    )
    p_inactive = TblProperty(
        propertyid_no="PR-INACT",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        noof_bhk=3,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=0,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
    )
    p_recycled = TblProperty(
        propertyid_no="PR-RECYC",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        noof_bhk=3,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=1,
    )
    p_expired = TblProperty(
        propertyid_no="PR-EXP",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        noof_bhk=3,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
        expiarydate=now_utc - timedelta(days=1),
    )
    p_overbudget = TblProperty(
        propertyid_no="PR-EXPENSIVE",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        noof_bhk=3,
        expected_price=9500000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
    )
    p_wrong_subcat = TblProperty(
        propertyid_no="PR-PLOT",
        property_type=2,
        looking_type=1,
        looking_subcat_type=3,
        noof_bhk=3,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
    )
    p_out_of_radius = TblProperty(
        propertyid_no="PR-TOOFAR",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        noof_bhk=3,
        expected_price=5000000,
        location="Tonk Road",
        location_lat="26.7500",
        location_long="75.8500",  # > 18 km away
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
    )
    db_session.add_all(
        [
            p_near,
            p_far_geo,
            p_text_fallback,
            p_sold,
            p_unverified,
            p_inactive,
            p_recycled,
            p_expired,
            p_overbudget,
            p_wrong_subcat,
            p_out_of_radius,
        ]
    )
    await db_session.commit()

    # Create employees for TELECALLER, FRANCHISEE_AGENT, CP L2, CP L1, CP inactive
    _, tc_headers = await _create_employee_with_token(
        db_session,
        employee_id="EMP-TC01",
        name="Telecaller One",
        mobile="9829088801",
        role_code="TELECALLER",
        role_name="Telecaller",
    )
    _, fa_headers = await _create_employee_with_token(
        db_session,
        employee_id="EMP-FA01",
        name="Franchise Agent",
        mobile="9829088802",
        role_code="FRANCHISEE_AGENT",
        role_name="Franchisee Agent",
    )
    _, cp_l2_headers = await _create_employee_with_token(
        db_session,
        employee_id="EMP-CP02",
        name="Active CP L2",
        mobile="9829088803",
        role_code="CHANNEL_PARTNER",
        role_name="Channel Partner",
    )
    _, cp_l1_headers = await _create_employee_with_token(
        db_session,
        employee_id="EMP-CP01",
        name="Active CP L1",
        mobile="9829088804",
        role_code="CHANNEL_PARTNER",
        role_name="Channel Partner",
    )
    _, cp_inact_headers = await _create_employee_with_token(
        db_session,
        employee_id="EMP-CP00",
        name="Inactive CP",
        mobile="9829088805",
        role_code="CHANNEL_PARTNER",
        role_name="Channel Partner",
    )

    db_session.add_all(
        [
            ChannelPartner(
                partner_code="CP-T02",
                employee_id="EMP-CP02",
                cp_type="ACTIVE_CP",
                active_level="L2",
                full_name="Active CP L2",
                mobile="9829088803",
                is_active=True,
            ),
            ChannelPartner(
                partner_code="CP-T01",
                employee_id="EMP-CP01",
                cp_type="ACTIVE_CP",
                active_level="L1",
                full_name="Active CP L1",
                mobile="9829088804",
                is_active=True,
            ),
            ChannelPartner(
                partner_code="CP-T00",
                employee_id="EMP-CP00",
                cp_type="BROKER_CP",
                full_name="Inactive CP",
                mobile="9829088805",
                is_active=False,
            ),
        ]
    )
    await db_session.commit()

    # Helper to create identical opp assigned to each actor
    async def _make_opp(assigned_to: str) -> int:
        res = await auth_client_md.post(
            "/v1/opportunities",
            json={
                "contact_name": f"Buyer for {assigned_to}",
                "mobile": "9829077777",
                "property_type": 2,
                "looking_type": 1,
                "looking_subcat_type": 1,
                "bhk": 3,
                "budget_from": 4000000,
                "budget_to": 6000000,
                "assigned_to": assigned_to,
                "locations": [
                    {
                        "locality_name": "Vaishali Nagar",
                        "latitude": 26.9124,
                        "longitude": 75.7873,
                        "radius_km": 10,
                    }
                ],
            },
        )
        assert res.status_code == 201
        return res.json()["opportunity_id"]

    opp_tc = await _make_opp("EMP-TC01")
    opp_fa = await _make_opp("EMP-FA01")
    opp_l2 = await _make_opp("EMP-CP02")
    opp_l1 = await _make_opp("EMP-CP01")
    opp_inact = await _make_opp("EMP-CP00")

    # 1. MD & TELECALLER see 3 matches sorted nearest-first and unmasked owner info
    tc_res = await test_client.get(f"/v1/opportunities/{opp_tc}/related-properties", headers=tc_headers)
    assert tc_res.status_code == 200
    tc_data = tc_res.json()
    assert tc_data["count"] == 3
    assert tc_data["owner_masked"] is False
    codes = [i["propertyid_no"] for i in tc_data["items"]]
    assert codes == ["PR-NEAR", "PR-FAR-GEO", "PR-TEXT"]
    assert tc_data["items"][0]["source_owner_mobile"] == "9829090001"
    assert tc_data["items"][0]["distance_km"] < tc_data["items"][1]["distance_km"]
    assert tc_data["items"][2]["distance_km"] is None

    # 2. FRANCHISEE_AGENT & ACTIVE_CP L2 see 3 matches but owner contact is masked
    for hdrs, oid in ((fa_headers, opp_fa), (cp_l2_headers, opp_l2)):
        res = await test_client.get(f"/v1/opportunities/{oid}/related-properties", headers=hdrs)
        assert res.status_code == 200
        d = res.json()
        assert d["count"] == 3
        assert d["owner_masked"] is True
        for item in d["items"]:
            assert item["source_owner_mobile"] is None
            assert item["source_owner_email"] is None
            assert item["source_owner_name"] == "Omshiv Managed"

    # 3. ACTIVE_CP L1 returns restricted empty list
    l1_res = await test_client.get(f"/v1/opportunities/{opp_l1}/related-properties", headers=cp_l1_headers)
    assert l1_res.status_code == 200
    l1_data = l1_res.json()
    assert l1_data["count"] == 0
    assert l1_data["owner_masked"] is True
    assert l1_data["items"] == []
    assert "restricted_reason" in l1_data and l1_data["restricted_reason"]

    # 4. Inactive ChannelPartner -> 403
    inact_res = await test_client.get(
        f"/v1/opportunities/{opp_inact}/related-properties", headers=cp_inact_headers
    )
    assert inact_res.status_code == 403


@pytest.mark.asyncio
async def test_opportunities_excel_export_not_shadowed(auth_client_md):
    r1 = await auth_client_md.post(
        "/v1/opportunities",
        json={
            "contact_name": "Export <Safe> Buyer",
            "mobile": "9829033301",
            "locations": [{"locality_name": "Malviya Nagar"}],
        },
    )
    assert r1.status_code == 201
    code = r1.json()["opportunity_code"]

    exp = await auth_client_md.get("/v1/opportunities/export?tab=all&search=Export")
    assert exp.status_code == 200
    assert exp.headers["content-type"].startswith("application/vnd.ms-excel")
    assert 'filename="opportunities_export.xls"' in exp.headers.get("content-disposition", "")
    assert code in exp.text
    assert "Export &lt;Safe&gt; Buyer" in exp.text
    assert "Malviya Nagar" in exp.text


@pytest.mark.asyncio
async def test_list_and_export_avoid_n_plus_one_cp_and_property_queries(
    test_client, auth_client_md, db_session
):
    from sqlalchemy import event
    from app.models.franchise import ChannelPartner
    from app.models.properties import TblProperty

    _, cp_l1_headers = await _create_employee_with_token(
        db_session,
        employee_id="EMP-NPLUS1",
        name="L1 Partner",
        mobile="9829088899",
        role_code="CHANNEL_PARTNER",
        role_name="Channel Partner",
    )
    db_session.add(
        ChannelPartner(
            partner_code="CP-N1",
            employee_id="EMP-NPLUS1",
            cp_type="ACTIVE_CP",
            active_level="L1",
            full_name="L1 Partner",
            mobile="9829088899",
            is_active=True,
        )
    )
    db_session.add(
        TblProperty(
            propertyid_no="PR-BATCH-1",
            property_type=2,
            looking_type=1,
            looking_subcat_type=1,
            expected_price=4500000,
            location="Vaishali Nagar",
            is_active=1,
            verified_status=1,
            sold_status=0,
            recyclebin_status=0,
        )
    )
    await db_session.commit()

    for idx in range(3):
        res = await auth_client_md.post(
            "/v1/opportunities",
            json={
                "contact_name": f"Batch Buyer {idx}",
                "mobile": f"982906660{idx}",
                "property_type": 2,
                "looking_type": 1,
                "looking_subcat_type": 1,
                "assigned_to": "EMP-NPLUS1",
            },
        )
        assert res.status_code == 201

    recorded_sql: list[str] = []

    def _capture_sql(conn, cursor, statement, parameters, context, executemany):
        recorded_sql.append(statement.lower())

    sync_engine = db_session.get_bind()
    event.listen(sync_engine, "before_cursor_execute", _capture_sql)
    try:
        # 1. List for MD (non-restricted): ChannelPartner resolved once, tbl_property queried <= 1 time total
        recorded_sql.clear()
        list_md = await auth_client_md.get("/v1/opportunities?tab=all")
        assert list_md.status_code == 200
        assert list_md.json()["total"] == 3
        assert all(item["matching_properties_count"] == 1 for item in list_md.json()["items"])
        cp_queries_md = [s for s in recorded_sql if "from channel_partners" in s]
        prop_queries_md = [s for s in recorded_sql if "from tbl_property" in s]
        assert len(cp_queries_md) == 1
        assert len(prop_queries_md) <= 1

        # 2. List for L1 Active CP: ChannelPartner resolved once, zero tbl_property queries
        recorded_sql.clear()
        list_l1 = await test_client.get("/v1/opportunities?tab=all", headers=cp_l1_headers)
        assert list_l1.status_code == 200
        assert list_l1.json()["total"] == 3
        assert all(item["matching_properties_count"] == 0 for item in list_l1.json()["items"])
        assert len([s for s in recorded_sql if "from channel_partners" in s]) == 1
        assert len([s for s in recorded_sql if "from tbl_property" in s]) == 0

        # 3. Export for MD: zero channel_partners and zero tbl_property queries
        recorded_sql.clear()
        exp = await auth_client_md.get("/v1/opportunities/export?tab=all")
        assert exp.status_code == 200
        assert "Batch Buyer 0" in exp.text
        assert "Batch Buyer 2" in exp.text
        assert len([s for s in recorded_sql if "from channel_partners" in s]) == 0
        assert len([s for s in recorded_sql if "from tbl_property" in s]) == 0
    finally:
        event.remove(sync_engine, "before_cursor_execute", _capture_sql)


# ---------------------------------------------------------------------------
# Task 3 Deal Pipeline, Reschedule, Transfer, Reopen & Call Log Tests (TDD)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_opportunity_status_direct_close_blocked_and_deal_registry_validation(
    auth_client_md,
):
    now_utc = datetime.now(timezone.utc)

    # 1. Create a Buy/Sell (property_type=2) opportunity
    buy_resp = await auth_client_md.post(
        "/v1/opportunities",
        json={
            "contact_name": "Direct Close Guard Buyer",
            "mobile": "9829044401",
            "property_type": 2,
            "looking_type": 1,
            "looking_subcat_type": 1,
            "budget_from": 4000000,
            "budget_to": 6000000,
        },
    )
    assert buy_resp.status_code == 201
    buy_id = buy_resp.json()["opportunity_id"]

    # Direct close (status=5) without Option 1 deal_date must fail with exact HTTP 400 detail
    direct_close = await auth_client_md.post(
        f"/v1/opportunities/{buy_id}/status",
        json={"lead_status": 5, "remark": "Try direct close"},
    )
    assert direct_close.status_code == 400
    assert (
        direct_close.json()["detail"]
        == "You cannot close this lead because the client has not yet Buy any property."
    )

    # Confirm opportunity was NOT locked
    check_open = await auth_client_md.get(f"/v1/opportunities/{buy_id}")
    assert check_open.status_code == 200
    assert check_open.json()["lead_status"] == 1
    assert check_open.json()["lead_open"] == 1

    # Disqualified without valid reason (1..7) -> 422
    bad_disq_missing = await auth_client_md.post(
        f"/v1/opportunities/{buy_id}/status",
        json={"lead_status": 2, "remark": "No reason"},
    )
    assert bad_disq_missing.status_code == 422
    bad_disq_range = await auth_client_md.post(
        f"/v1/opportunities/{buy_id}/status",
        json={"lead_status": 2, "disqualified_reason": 9, "remark": "Invalid reason"},
    )
    assert bad_disq_range.status_code == 422

    # Buy Option 1 validations: missing deal_date, future deal_date, missing registry_date, past registry_date -> 422
    no_deal_dt = await auth_client_md.post(
        f"/v1/opportunities/{buy_id}/status",
        json={
            "lead_status": 4,
            "registry_date": (now_utc + timedelta(days=5)).isoformat(),
        },
    )
    assert no_deal_dt.status_code == 422

    future_deal_dt = await auth_client_md.post(
        f"/v1/opportunities/{buy_id}/status",
        json={
            "lead_status": 4,
            "deal_date": (now_utc + timedelta(hours=2)).isoformat(),
            "registry_date": (now_utc + timedelta(days=5)).isoformat(),
        },
    )
    assert future_deal_dt.status_code == 422

    no_reg_dt = await auth_client_md.post(
        f"/v1/opportunities/{buy_id}/status",
        json={
            "lead_status": 4,
            "deal_date": (now_utc - timedelta(hours=2)).isoformat(),
        },
    )
    assert no_reg_dt.status_code == 422

    past_reg_dt = await auth_client_md.post(
        f"/v1/opportunities/{buy_id}/status",
        json={
            "lead_status": 4,
            "deal_date": (now_utc - timedelta(days=2)).isoformat(),
            "registry_date": (now_utc - timedelta(hours=1)).isoformat(),
        },
    )
    assert past_reg_dt.status_code == 422

    # Valid Buy Option 1 with External property & registry_date +5d -> auto followup ~ +3d
    deal_dt = now_utc - timedelta(days=1)
    reg_dt = now_utc + timedelta(days=5)
    ok_buy_opt1 = await auth_client_md.post(
        f"/v1/opportunities/{buy_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_dt.isoformat(),
            "registry_date": reg_dt.isoformat(),
            "is_propira_property": False,
            "deal_property_category": 1,
            "deal_property_subcategory": 1,
            "deal_property_address": "Plot 12, Jagatpura",
            "deal_location_lat": "26.8200",
            "deal_location_long": "75.8600",
            "remark": "Token paid on external flat",
        },
    )
    assert ok_buy_opt1.status_code == 200
    buy_data = ok_buy_opt1.json()
    assert buy_data["lead_status"] == 4
    assert buy_data["lead_open"] == 1
    assert buy_data["is_propira_property"] is False
    assert buy_data["matched_property_id"] is None
    assert buy_data["deal_property_address"] == "Plot 12, Jagatpura"
    assert buy_data["activities"][0]["action_type"] == "DEAL_SCHEDULED"

    auto_fu = datetime.fromisoformat(buy_data["followup_datetime"])
    expected_fu = reg_dt - timedelta(days=2)
    assert abs((auto_fu - expected_fu).total_seconds()) < 10
    assert (
        buy_data["reschedules"][0]["remark"]
        == "Auto-scheduled pre-registry follow-up (registry - 2 days)"
    )

    dash = await auth_client_md.get("/v1/opportunities/dashboard")
    assert dash.status_code == 200
    assert dash.json()["chart_breakdown"]["qualified_other"] == 1

    # Clamped auto-followup when registry_date is only 6 hours in the future -> >= now + 1h
    near_reg = now_utc + timedelta(hours=6)
    clamped_resp = await auth_client_md.post(
        f"/v1/opportunities/{buy_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_dt.isoformat(),
            "registry_date": near_reg.isoformat(),
            "is_propira_property": False,
        },
    )
    assert clamped_resp.status_code == 200
    clamped_fu = datetime.fromisoformat(clamped_resp.json()["followup_datetime"])
    assert clamped_fu >= now_utc + timedelta(minutes=59)
    assert clamped_fu <= datetime.now(timezone.utc) + timedelta(hours=1, minutes=2)

    # 2. Rent (property_type=1): registry_date (Agreement Date) is optional
    rent_resp = await auth_client_md.post(
        "/v1/opportunities",
        json={
            "contact_name": "Rent Tenant",
            "mobile": "9829044402",
            "property_type": 1,
        },
    )
    assert rent_resp.status_code == 201
    rent_id = rent_resp.json()["opportunity_id"]

    rent_opt1 = await auth_client_md.post(
        f"/v1/opportunities/{rent_id}/status",
        json={
            "lead_status": 4,
            "deal_date": (now_utc - timedelta(hours=3)).isoformat(),
            "is_propira_property": False,
            "deal_property_address": "Flat 4B, Malviya Nagar",
        },
    )
    assert rent_opt1.status_code == 200
    assert rent_opt1.json()["lead_status"] == 4
    assert rent_opt1.json()["registry_date"] is None
    assert rent_opt1.json()["reschedules"] == []

    # 3. PG (property_type=3): Agreement Date < deal_date rejected; future Agreement Date schedules auto-followup
    pg_resp = await auth_client_md.post(
        "/v1/opportunities",
        json={
            "contact_name": "PG Student",
            "mobile": "9829044403",
            "property_type": 3,
        },
    )
    assert pg_resp.status_code == 201
    pg_id = pg_resp.json()["opportunity_id"]

    pg_deal = now_utc - timedelta(days=1)
    bad_pg = await auth_client_md.post(
        f"/v1/opportunities/{pg_id}/status",
        json={
            "lead_status": 4,
            "deal_date": pg_deal.isoformat(),
            "registry_date": (pg_deal - timedelta(days=1)).isoformat(),
        },
    )
    assert bad_pg.status_code == 422

    pg_future_agr = now_utc + timedelta(days=4)
    ok_pg = await auth_client_md.post(
        f"/v1/opportunities/{pg_id}/status",
        json={
            "lead_status": 4,
            "deal_date": pg_deal.isoformat(),
            "registry_date": pg_future_agr.isoformat(),
        },
    )
    assert ok_pg.status_code == 200
    pg_fu = datetime.fromisoformat(ok_pg.json()["followup_datetime"])
    assert abs((pg_fu - (pg_future_agr - timedelta(days=2))).total_seconds()) < 10


@pytest.mark.asyncio
async def test_opportunity_propira_sold_lock_switch_and_cancellation_rollback(
    auth_client_md, db_session
):
    from app.models.properties import TblProperty

    now_utc = datetime.now(timezone.utc)
    p1 = TblProperty(
        propertyid_no="PR-DEAL-1",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
    )
    p2 = TblProperty(
        propertyid_no="PR-DEAL-2",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        expected_price=5500000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
    )
    p_sold = TblProperty(
        propertyid_no="PR-ALREADY-SOLD",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=1,
        sold_status=1,
        recyclebin_status=0,
    )
    p_unverified = TblProperty(
        propertyid_no="PR-NOT-VERIFIED",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=0,
        sold_status=0,
        recyclebin_status=0,
    )
    p_inactive = TblProperty(
        propertyid_no="PR-INACTIVE",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=0,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
    )
    p_recycled = TblProperty(
        propertyid_no="PR-RECYCLED",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=1,
    )
    p_expired = TblProperty(
        propertyid_no="PR-EXPIRED",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        expected_price=5000000,
        location="Vaishali Nagar",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
        expiarydate=now_utc - timedelta(days=1),
    )
    db_session.add_all([p1, p2, p_sold, p_unverified, p_inactive, p_recycled, p_expired])
    await db_session.commit()
    for p in (p1, p2, p_sold, p_unverified, p_inactive, p_recycled, p_expired):
        await db_session.refresh(p)

    r1 = await auth_client_md.post(
        "/v1/opportunities",
        json={"contact_name": "Propira Buyer 1", "mobile": "9829044501", "property_type": 2},
    )
    r2 = await auth_client_md.post(
        "/v1/opportunities",
        json={"contact_name": "Propira Buyer 2", "mobile": "9829044502", "property_type": 2},
    )
    opp1_id = r1.json()["opportunity_id"]
    opp2_id = r2.json()["opportunity_id"]

    deal_iso = (now_utc - timedelta(hours=4)).isoformat()
    reg_iso = (now_utc + timedelta(days=6)).isoformat()

    # Missing matched_property_id when is_propira_property=True -> 422
    missing_pid = await auth_client_md.post(
        f"/v1/opportunities/{opp1_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_iso,
            "registry_date": reg_iso,
            "is_propira_property": True,
        },
    )
    assert missing_pid.status_code == 422

    # Non-existent property -> 404
    not_found_pid = await auth_client_md.post(
        f"/v1/opportunities/{opp1_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_iso,
            "registry_date": reg_iso,
            "is_propira_property": True,
            "matched_property_id": 999999,
        },
    )
    assert not_found_pid.status_code == 404

    # Unavailable/unverified/inactive/recycled/expired properties -> 400
    for bad_prop in (p_sold, p_unverified, p_inactive, p_recycled, p_expired):
        bad_res = await auth_client_md.post(
            f"/v1/opportunities/{opp1_id}/status",
            json={
                "lead_status": 4,
                "deal_date": deal_iso,
                "registry_date": reg_iso,
                "is_propira_property": True,
                "matched_property_id": bad_prop.property_id,
            },
        )
        assert bad_res.status_code == 400, f"Expected 400 for {bad_prop.propertyid_no}"

    # Link P1 to opp1 -> P1.sold_status becomes 1
    link_p1 = await auth_client_md.post(
        f"/v1/opportunities/{opp1_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_iso,
            "registry_date": reg_iso,
            "is_propira_property": True,
            "matched_property_id": p1.property_id,
            "remark": "Matched PR-DEAL-1",
        },
    )
    assert link_p1.status_code == 200
    assert link_p1.json()["is_propira_property"] is True
    assert link_p1.json()["matched_property_id"] == p1.property_id
    assert link_p1.json()["matched_property_code"] == "PR-DEAL-1"

    await db_session.refresh(p1)
    assert p1.sold_status == 1

    # P1 is now excluded from opp2's related-properties and cannot be double-sold
    rel_while_sold = await auth_client_md.get(f"/v1/opportunities/{opp2_id}/related-properties")
    assert rel_while_sold.status_code == 200
    assert "PR-DEAL-1" not in [i["propertyid_no"] for i in rel_while_sold.json()["items"]]

    # opp2 cannot double-sell P1 -> 400
    double_sell = await auth_client_md.post(
        f"/v1/opportunities/{opp2_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_iso,
            "registry_date": reg_iso,
            "is_propira_property": True,
            "matched_property_id": p1.property_id,
        },
    )
    assert double_sell.status_code == 400

    # Switch opp1 from P1 -> P2: P1 rolls back to 0, P2 becomes 1
    switch_p2 = await auth_client_md.post(
        f"/v1/opportunities/{opp1_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_iso,
            "registry_date": reg_iso,
            "is_propira_property": True,
            "matched_property_id": p2.property_id,
            "remark": "Switched to PR-DEAL-2",
        },
    )
    assert switch_p2.status_code == 200
    assert switch_p2.json()["matched_property_id"] == p2.property_id
    assert switch_p2.json()["matched_property_code"] == "PR-DEAL-2"

    await db_session.refresh(p1)
    await db_session.refresh(p2)
    assert p1.sold_status == 0
    assert p2.sold_status == 1

    rel_after_switch = await auth_client_md.get(f"/v1/opportunities/{opp2_id}/related-properties")
    assert rel_after_switch.status_code == 200
    switched_codes = [i["propertyid_no"] for i in rel_after_switch.json()["items"]]
    assert "PR-DEAL-1" in switched_codes
    assert "PR-DEAL-2" not in switched_codes

    # Switch opp1 from P2 -> External (is_propira_property=False): P2 rolls back to 0
    switch_ext = await auth_client_md.post(
        f"/v1/opportunities/{opp1_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_iso,
            "registry_date": reg_iso,
            "is_propira_property": False,
            "deal_property_address": "External Villa",
        },
    )
    assert switch_ext.status_code == 200
    assert switch_ext.json()["is_propira_property"] is False
    assert switch_ext.json()["matched_property_id"] is None
    await db_session.refresh(p2)
    assert p2.sold_status == 0

    # Re-link P1 then cancel 4 -> 1 (In Progress): P1 rolls back to 0 & deal fields cleared
    await auth_client_md.post(
        f"/v1/opportunities/{opp1_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_iso,
            "registry_date": reg_iso,
            "is_propira_property": True,
            "matched_property_id": p1.property_id,
        },
    )
    await db_session.refresh(p1)
    assert p1.sold_status == 1

    cancel_to_1 = await auth_client_md.post(
        f"/v1/opportunities/{opp1_id}/status",
        json={"lead_status": 1, "remark": "Client postponed deal"},
    )
    assert cancel_to_1.status_code == 200
    c1 = cancel_to_1.json()
    assert c1["lead_status"] == 1
    assert c1["lead_open"] == 1
    assert c1["deal_date"] is None
    assert c1["registry_date"] is None
    assert c1["is_propira_property"] is False
    assert c1["matched_property_id"] is None
    assert c1["matched_property_code"] is None
    assert c1["deal_property_address"] is None
    await db_session.refresh(p1)
    assert p1.sold_status == 0

    # After cancellation 4 -> 1, closing directly must again be blocked
    close_after_cancel = await auth_client_md.post(
        f"/v1/opportunities/{opp1_id}/status",
        json={"lead_status": 5},
    )
    assert close_after_cancel.status_code == 400
    assert (
        close_after_cancel.json()["detail"]
        == "You cannot close this lead because the client has not yet Buy any property."
    )

    # Re-link P1 then disqualify 4 -> 2: P1 rolls back to 0, deal fields cleared, opp locked
    await auth_client_md.post(
        f"/v1/opportunities/{opp1_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_iso,
            "registry_date": reg_iso,
            "is_propira_property": True,
            "matched_property_id": p1.property_id,
        },
    )
    disq_from_4 = await auth_client_md.post(
        f"/v1/opportunities/{opp1_id}/status",
        json={"lead_status": 2, "disqualified_reason": 5, "remark": "Backed out"},
    )
    assert disq_from_4.status_code == 200
    d4 = disq_from_4.json()
    assert d4["lead_status"] == 2
    assert d4["lead_open"] == 0
    assert d4["disqualified_reason"] == 5
    assert d4["deal_date"] is None
    assert d4["matched_property_id"] is None
    assert d4["activities"][0]["action_type"] == "DISQUALIFIED"
    await db_session.refresh(p1)
    assert p1.sold_status == 0


@pytest.mark.asyncio
async def test_opportunity_close_and_parent_lead_won_lost_reopen_sync(
    auth_client_md, db_session
):
    from sqlalchemy import select
    from app.models.leads import Lead, LeadActivity, TblLead
    from app.models.properties import TblProperty

    now_utc = datetime.now(timezone.utc)
    lead = Lead(
        lead_id="OB-2026-000501",
        full_name="Synced Buyer",
        mobile="919829055510",
        stage="CONNECTED",
    )
    tbl_lead = TblLead(
        lead_unique_id="OB-2026-000501",
        contact_name="Synced Buyer",
        mobile="919829055510",
        lead_status=1,
        lead_open=1,
    )
    prop = TblProperty(
        propertyid_no="PR-SYNC-1",
        property_type=2,
        looking_type=1,
        looking_subcat_type=1,
        expected_price=6000000,
        location="Mansarovar",
        is_active=1,
        verified_status=1,
        sold_status=0,
        recyclebin_status=0,
    )
    db_session.add_all([lead, tbl_lead, prop])
    await db_session.commit()
    await db_session.refresh(prop)

    conv = await auth_client_md.post(
        "/v1/opportunities",
        json={
            "source_lead_id": "OB-2026-000501",
            "contact_name": "Synced Buyer",
            "mobile": "9829055510",
            "property_type": 2,
        },
    )
    assert conv.status_code == 201
    opp_id = conv.json()["opportunity_id"]

    # 1. Disqualify -> parent Lead.stage = LOST, TblLead.lead_status = 2, lead_open = 0
    disq = await auth_client_md.post(
        f"/v1/opportunities/{opp_id}/status",
        json={"lead_status": 2, "disqualified_reason": 3, "remark": "Not picking calls"},
    )
    assert disq.status_code == 200
    await db_session.refresh(lead)
    await db_session.refresh(tbl_lead)
    assert lead.stage == "LOST"
    assert tbl_lead.lead_status == 2
    assert tbl_lead.lead_open == 0

    # Locked Disqualified blocks /status, /reschedule, /transfer
    for path, body in (
        (f"/v1/opportunities/{opp_id}/status", {"lead_status": 1}),
        (f"/v1/opportunities/{opp_id}/status", {"lead_status": 4, "deal_date": now_utc.isoformat(), "registry_date": (now_utc + timedelta(days=3)).isoformat()}),
        (
            f"/v1/opportunities/{opp_id}/reschedule",
            {"followup_datetime": (now_utc + timedelta(days=1)).isoformat(), "remark": "Locked"},
        ),
        (f"/v1/opportunities/{opp_id}/transfer", {"assigned_to": "EMP-0001", "remark": "Locked"}),
    ):
        blocked = await auth_client_md.post(path, json=body)
        assert blocked.status_code == 400, f"Expected 400 when locked on {path}"

    # 2. Reopen Disqualified -> status=1, lead_open=1, Lead.stage=QUALIFIED, TblLead.lead_status=4, lead_open=1
    reopen = await auth_client_md.post(
        f"/v1/opportunities/{opp_id}/reopen",
        json={"remark": "Client returned call"},
    )
    assert reopen.status_code == 200
    r_data = reopen.json()
    assert r_data["lead_status"] == 1
    assert r_data["lead_open"] == 1
    assert r_data["disqualified_reason"] == 0
    assert r_data["activities"][0]["action_type"] == "REOPEN"

    await db_session.refresh(lead)
    await db_session.refresh(tbl_lead)
    assert lead.stage == "QUALIFIED"
    assert tbl_lead.lead_status == 4
    assert tbl_lead.lead_open == 1

    # Reopening an already-open opportunity -> 400
    reopen_open = await auth_client_md.post(f"/v1/opportunities/{opp_id}/reopen")
    assert reopen_open.status_code == 400

    # 3. Schedule Option 1 then Close Option 2 -> Lead.stage = WON, TblLead.lead_status = 5, lead_open = 0
    deal_dt = now_utc - timedelta(days=1)
    reg_dt = now_utc + timedelta(days=5)
    opt1 = await auth_client_md.post(
        f"/v1/opportunities/{opp_id}/status",
        json={
            "lead_status": 4,
            "deal_date": deal_dt.isoformat(),
            "registry_date": reg_dt.isoformat(),
            "is_propira_property": True,
            "matched_property_id": prop.property_id,
        },
    )
    assert opt1.status_code == 200

    closed = await auth_client_md.post(
        f"/v1/opportunities/{opp_id}/status",
        json={"lead_status": 5, "remark": "Registry completed successfully"},
    )
    assert closed.status_code == 200
    c_data = closed.json()
    assert c_data["lead_status"] == 5
    assert c_data["lead_open"] == 0
    assert c_data["closed_at"] is not None
    assert c_data["calls_status"] == 1
    assert c_data["activities"][0]["action_type"] == "CLOSED"

    await db_session.refresh(prop)
    await db_session.refresh(lead)
    await db_session.refresh(tbl_lead)
    assert prop.sold_status == 1
    assert lead.stage == "WON"
    assert tbl_lead.lead_status == 5
    assert tbl_lead.lead_open == 0
    assert tbl_lead.deal_date is not None
    assert tbl_lead.registry_date is not None
    assert tbl_lead.dealclose_date is not None

    won_act = (
        await db_session.execute(
            select(LeadActivity).where(
                LeadActivity.lead_id == "OB-2026-000501",
                LeadActivity.action_type == "OPPORTUNITY_WON",
            )
        )
    ).scalar_one_or_none()
    assert won_act is not None

    # Closed opportunity is permanently terminal (blocks reopen, status, reschedule, transfer)
    assert (await auth_client_md.post(f"/v1/opportunities/{opp_id}/reopen")).status_code == 400
    assert (
        await auth_client_md.post(f"/v1/opportunities/{opp_id}/status", json={"lead_status": 1})
    ).status_code == 400
    assert (
        await auth_client_md.post(
            f"/v1/opportunities/{opp_id}/reschedule",
            json={"followup_datetime": (now_utc + timedelta(days=1)).isoformat(), "remark": "Try"},
        )
    ).status_code == 400
    assert (
        await auth_client_md.post(
            f"/v1/opportunities/{opp_id}/transfer",
            json={"assigned_to": "EMP-0001"},
        )
    ).status_code == 400


@pytest.mark.asyncio
async def test_opportunity_reschedule_transfer_call_log_and_scoping(
    test_client, auth_client_md, auth_client_sales, db_session
):
    from app.models.franchise import FranchiseOutlet

    now_utc = datetime.now(timezone.utc)
    emp3, emp3_headers = await _create_employee_with_token(
        db_session,
        employee_id="EMP-0003",
        name="Priya Verma",
        mobile="9829099903",
        role_code="SALES_EXEC",
        role_name="Sales Executive",
    )
    outlet = FranchiseOutlet(
        outlet_code="OUT-JPR-01",
        name="Jaipur Vaishali Desk",
        city="Jaipur",
        is_active=True,
    )
    db_session.add(outlet)
    await db_session.commit()
    await db_session.refresh(outlet)

    # Create opportunity owned by EMP-0002 (auth_client_sales)
    create_resp = await auth_client_sales.post(
        "/v1/opportunities",
        json={"contact_name": "Scoped Pipeline Buyer", "mobile": "9829066701"},
    )
    assert create_resp.status_code == 201
    opp_id = create_resp.json()["opportunity_id"]

    # Unauthenticated calls -> 401; out-of-scope actor (EMP-0003) -> 403
    for endpoint, payload in (
        ("call-log", {"remark": "Unauth"}),
        ("reschedule", {"followup_datetime": (now_utc + timedelta(days=1)).isoformat(), "remark": "Unauth"}),
        ("status", {"lead_status": 2, "disqualified_reason": 2}),
        ("transfer", {"assigned_to": "EMP-0001"}),
        ("reopen", {"remark": "Unauth"}),
    ):
        assert (await test_client.post(f"/v1/opportunities/{opp_id}/{endpoint}", json=payload)).status_code == 401
        assert (
            await test_client.post(
                f"/v1/opportunities/{opp_id}/{endpoint}",
                json=payload,
                headers=emp3_headers,
            )
        ).status_code == 403

    # Call log updates calls_status = 1 and appends CALL activity
    call_res = await auth_client_sales.post(
        f"/v1/opportunities/{opp_id}/call-log",
        json={"remark": "Client wants 3BHK near metro"},
    )
    assert call_res.status_code == 200
    call_data = call_res.json()
    assert call_data["calls_status"] == 1
    assert call_data["last_remark"] == "Client wants 3BHK near metro"
    assert call_data["activities"][0]["action_type"] == "CALL"

    # Reschedule rejects past datetime and blank remark (422)
    assert (
        await auth_client_sales.post(
            f"/v1/opportunities/{opp_id}/reschedule",
            json={
                "followup_datetime": (now_utc - timedelta(hours=1)).isoformat(),
                "remark": "Past",
            },
        )
    ).status_code == 422
    assert (
        await auth_client_sales.post(
            f"/v1/opportunities/{opp_id}/reschedule",
            json={
                "followup_datetime": (now_utc + timedelta(days=2)).isoformat(),
                "remark": "   ",
            },
        )
    ).status_code == 422

    next_fu = now_utc + timedelta(days=2)
    resched_res = await auth_client_sales.post(
        f"/v1/opportunities/{opp_id}/reschedule",
        json={
            "followup_datetime": next_fu.isoformat(),
            "current_update": "Site Visit Scheduled",
            "remark": "Visit Saturday 11 AM",
        },
    )
    assert resched_res.status_code == 200
    rs_data = resched_res.json()
    assert rs_data["current_update"] == "Site Visit Scheduled"
    assert rs_data["last_remark"] == "Visit Saturday 11 AM"
    assert rs_data["calls_status"] == 1
    assert rs_data["activities"][0]["action_type"] == "RESCHEDULE"
    assert len(rs_data["reschedules"]) == 1
    assert rs_data["reschedules"][0]["remark"] == "Visit Saturday 11 AM"

    # Transfer validates Employee / FranchiseOutlet (404 for unknown)
    assert (
        await auth_client_sales.post(
            f"/v1/opportunities/{opp_id}/transfer",
            json={"assigned_to": "EMP-NOPE", "remark": "Bad emp"},
        )
    ).status_code == 404
    assert (
        await auth_client_sales.post(
            f"/v1/opportunities/{opp_id}/transfer",
            json={"assigned_to": "EMP-0003", "assign_franch_id": 999999, "remark": "Bad branch"},
        )
    ).status_code == 404

    # EMP-0002 transfers own opportunity to EMP-0003 + Jaipur Vaishali Desk -> 200 (even though ownership changed!)
    xfer_res = await auth_client_sales.post(
        f"/v1/opportunities/{opp_id}/transfer",
        json={
            "assigned_to": "EMP-0003",
            "assign_franch_id": outlet.id,
            "remark": "Handover to Vaishali specialist",
        },
    )
    assert xfer_res.status_code == 200
    xf_data = xfer_res.json()
    assert xf_data["assigned_to"] == "EMP-0003"
    assert xf_data["assign_franchstaff_id"] == emp3.id
    assert xf_data["assign_franch_id"] == outlet.id
    assert xf_data["franchise_name"] == "Jaipur Vaishali Desk"
    assert xf_data["activities"][0]["action_type"] == "TRANSFER"

    # Ownership transferred: EMP-0002 now gets 403, EMP-0003 gets 200
    assert (await auth_client_sales.get(f"/v1/opportunities/{opp_id}")).status_code == 403
    assert (await test_client.get(f"/v1/opportunities/{opp_id}", headers=emp3_headers)).status_code == 200

    # Fix Round 1 regressions:
    # (a) Employee-only transfer on a franchised opportunity preserves assign_franch_id > 0
    partial_staff_xfer = await test_client.post(
        f"/v1/opportunities/{opp_id}/transfer",
        json={"assigned_to": "EMP-0001", "remark": "Escalate to MD within branch"},
        headers=emp3_headers,
    )
    assert partial_staff_xfer.status_code == 200
    ps_data = partial_staff_xfer.json()
    assert ps_data["assigned_to"] == "EMP-0001"
    assert ps_data["assign_franch_id"] == outlet.id
    assert ps_data["franchise_name"] == "Jaipur Vaishali Desk"
    assert ps_data["activities"][0]["action_type"] == "TRANSFER"
    assert "Central Desk" not in ps_data["activities"][0]["note"]
    acts_before_noop = len(ps_data["activities"])

    # (b) Explicit nulls / empty transfer on a franchised opportunity -> 422 with zero new TRANSFER activity
    for noop_payload in (
        {"assigned_to": None, "assign_franch_id": None},
        {},
    ):
        noop_res = await auth_client_md.post(
            f"/v1/opportunities/{opp_id}/transfer",
            json=noop_payload,
        )
        assert noop_res.status_code == 422
    after_noop = await auth_client_md.get(f"/v1/opportunities/{opp_id}")
    assert after_noop.status_code == 200
    assert len(after_noop.json()["activities"]) == acts_before_noop

    # (c) Explicit assign_franch_id=0 cleanly transfers back to Central Desk
    central_xfer = await auth_client_md.post(
        f"/v1/opportunities/{opp_id}/transfer",
        json={"assign_franch_id": 0, "remark": "Return to central desk"},
    )
    assert central_xfer.status_code == 200
    c_xf = central_xfer.json()
    assert c_xf["assigned_to"] == "EMP-0001"
    assert c_xf["assign_franch_id"] == 0
    assert c_xf["franchise_name"] is None
    assert c_xf["activities"][0]["action_type"] == "TRANSFER"
    assert "Central Desk" in c_xf["activities"][0]["note"]
