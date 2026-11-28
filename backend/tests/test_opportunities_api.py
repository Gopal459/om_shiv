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
    today_dt = ist_start + timedelta(hours=12)

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
