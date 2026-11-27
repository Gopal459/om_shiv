import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.models.callbacks import (
    TblCallback,
    CallbackRescheduleLog,
    CallbackActivity,
    CALLBACK_STATUSES,
    DISQUALIFIED_REASONS,
    PROBLEM_STATUSES,
    CURRENT_UPDATE_OPTIONS,
)
from app.models.inquiries import WebsiteInquiry


@pytest.mark.asyncio
async def test_callback_models_and_defaults(db_session):
    assert CALLBACK_STATUSES[0] == "New"
    assert CALLBACK_STATUSES[6] == "Converted Property"
    assert DISQUALIFIED_REASONS[1] == "Inaccurate Data"
    assert len(DISQUALIFIED_REASONS) == 7
    assert PROBLEM_STATUSES == ("NEW", "IN_REVIEW", "RESOLVED", "REJECTED")
    assert "Interested" in CURRENT_UPDATE_OPTIONS

    cb = TblCallback(name="Rohan", mobile_number="9829011223", phone_code="+91", message="Call me")
    db_session.add(cb)
    await db_session.flush()
    cb.lead_unique_id = f"WEB{cb.callback_id}"
    await db_session.commit()
    await db_session.refresh(cb)

    assert cb.lead_unique_id == f"WEB{cb.callback_id}"
    assert cb.lead_status == 0
    assert cb.calls_status == 0
    assert cb.lead_open == 1
    assert cb.disqualified_reason == 0
    assert cb.lead_converted == 0
    assert cb.opportunity_converted == 0

    # Verify child relationship persistence
    future_dt = datetime.now(timezone.utc) + timedelta(days=1)
    reschedule = CallbackRescheduleLog(
        callback_id=cb.callback_id,
        old_followup_datetime=None,
        new_followup_datetime=future_dt,
        current_update="Call Back Later",
        remark="Customer requested call tomorrow",
        rescheduled_by="EMP-0001",
    )
    activity = CallbackActivity(
        callback_id=cb.callback_id,
        action_type="RECEIVED",
        title="Received",
        status_before=None,
        status_after=0,
        remark="Inbound callback logged",
        performed_by="SYSTEM",
    )
    db_session.add_all([reschedule, activity])
    await db_session.commit()

    await db_session.refresh(cb, attribute_names=["reschedule_logs", "activities"])
    assert len(cb.reschedule_logs) == 1
    assert len(cb.activities) == 1
    assert cb.reschedule_logs[0].current_update == "Call Back Later"
    assert cb.activities[0].action_type == "RECEIVED"

    inq = WebsiteInquiry(inquiry_type="PROBLEM_REPORT", full_name="Amit", mobile="919829000111")
    db_session.add(inq)
    await db_session.commit()
    await db_session.refresh(inq)
    assert inq.status == "NEW"
    assert inq.assigned_to is None
    assert inq.related_property_code is None
    assert inq.resolution_remark is None
    assert inq.resolved_by is None
    assert inq.resolved_at is None
    assert inq.updated_at is not None


@pytest.mark.asyncio
async def test_migration_0013_idempotent_on_existing_website_inquiries():
    """Verify migration 0013 creates callback tables and adds inquiry triage columns idempotently."""
    import importlib

    migration_0013 = importlib.import_module("app.db.migrations.0013_website_forms_callback_schema")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    try:
        # Simulate pre-0013 database containing minimal employees + website_inquiries tables
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
            await conn.execute(
                text(
                    """
                    CREATE TABLE website_inquiries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        inquiry_type VARCHAR(32) NOT NULL,
                        full_name VARCHAR(255) NOT NULL,
                        mobile VARCHAR(15) NOT NULL,
                        email VARCHAR(255) NULL,
                        details TEXT NULL,
                        is_converted BOOLEAN NOT NULL DEFAULT 0,
                        converted_lead_id VARCHAR(32) NULL,
                        converted_by_emp_id VARCHAR(32) NULL,
                        converted_at TIMESTAMP NULL,
                        deleted_at TIMESTAMP NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )

        # First upgrade
        await migration_0013.upgrade(engine)
        # Second upgrade must be idempotent
        await migration_0013.upgrade(engine)

        async with engine.connect() as conn:
            tables_res = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            table_names = {row[0] for row in tables_res.fetchall()}
            assert "tbl_callback" in table_names
            assert "tbl_leadreschedule_followup" in table_names
            assert "tbl_callback_activities" in table_names

            cols_res = await conn.execute(text("PRAGMA table_info(website_inquiries)"))
            inquiry_cols = {row[1] for row in cols_res.fetchall()}
            expected_new_cols = {
                "status",
                "assigned_to",
                "related_property_code",
                "resolution_remark",
                "resolved_by",
                "resolved_at",
                "updated_at",
            }
            assert expected_new_cols.issubset(inquiry_cols)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_intake_callback_round_robin_and_zero_telecaller_fallback(test_client, db_session):
    from sqlalchemy import select
    from app.models.identity import Department, Role, Employee

    # 1. Zero TELECALLER fallback
    resp0 = await test_client.post(
        "/v1/intake/callback",
        json={
            "name": "Ravi Verma",
            "mobile_number": "9829010000",
            "phone_code": "+91",
            "message": "Call regarding plot",
        },
    )
    assert resp0.status_code == 201
    data0 = resp0.json()
    assert data0["lead_unique_id"].startswith("WEB")
    assert data0["assigned_user_id"] is None
    assert data0["lead_status"] == 0
    assert data0["lead_open"] == 1

    # Blank name / blank phone validation -> 422
    bad_name = await test_client.post(
        "/v1/intake/callback",
        json={"name": "   ", "mobile_number": "9829010000"},
    )
    assert bad_name.status_code == 422
    bad_phone = await test_client.post(
        "/v1/intake/callback",
        json={"name": "Valid Name", "phone": "   "},
    )
    assert bad_phone.status_code == 422

    # 2. Seed 2 active TELECALLERs and 1 inactive/on-leave TELECALLER
    dept = Department(name="Sales", code="SALES")
    db_session.add(dept)
    await db_session.flush()

    tc_role = Role(
        department_id=dept.id,
        name="Telecaller",
        code="TELECALLER",
        permissions={"leads": ["view_assigned", "create"]},
    )
    db_session.add(tc_role)
    await db_session.flush()

    emp1 = Employee(
        employee_id="EMP-T001",
        name="Telecaller One",
        email="t1@omshiv.in",
        mobile="9829090001",
        department_id=dept.id,
        role_id=tc_role.id,
        is_active=True,
        is_on_leave=False,
    )
    emp2 = Employee(
        employee_id="EMP-T002",
        name="Telecaller Two",
        email="t2@omshiv.in",
        mobile="9829090002",
        department_id=dept.id,
        role_id=tc_role.id,
        is_active=True,
        is_on_leave=False,
    )
    emp3 = Employee(
        employee_id="EMP-T003",
        name="Telecaller On Leave",
        email="t3@omshiv.in",
        mobile="9829090003",
        department_id=dept.id,
        role_id=tc_role.id,
        is_active=True,
        is_on_leave=True,
    )
    db_session.add_all([emp1, emp2, emp3])
    await db_session.commit()

    assigned = []
    for idx in range(4):
        resp = await test_client.post(
            "/v1/intake/callback",
            json={
                "name": f"Customer {idx + 1}",
                "phone": f"982901000{idx + 1}",
                "message": "Interested in 2BHK",
            },
        )
        assert resp.status_code == 201
        assigned.append(resp.json()["assigned_user_id"])

    assert assigned == ["EMP-T001", "EMP-T002", "EMP-T001", "EMP-T002"]
    assert "EMP-T003" not in assigned


@pytest.mark.asyncio
async def test_inquiry_callback_sync_and_dual_conversion_guard(test_client, db_session):
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.identity import Department, Role, Employee
    from app.models.leads import Lead, TblLead
    from app.services.callback_service import callback_service
    from app.services.intake_service import intake_service

    dept = Department(name="Management", code="MGMT")
    db_session.add(dept)
    await db_session.flush()
    role = Role(
        department_id=dept.id,
        name="Super Admin",
        code="SUPER_ADMIN",
        permissions={"leads": ["view_all"]},
    )
    db_session.add(role)
    await db_session.flush()
    admin = Employee(
        employee_id="EMP-0001",
        name="Admin User",
        email="admin@omshiv.in",
        mobile="9829000001",
        department_id=dept.id,
        role_id=role.id,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    # 1. Submit inquiry with inquiry_type="CALLBACK"
    resp_inq = await test_client.post(
        "/v1/intake/inquiry",
        json={
            "inquiry_type": "CALLBACK",
            "full_name": "Meena Gupta",
            "mobile": "9829022211",
            "email": "meena@example.com",
            "details": {"message": "Need callback", "property_code": "OP-2026-00001"},
        },
    )
    assert resp_inq.status_code == 201
    inquiry_id = resp_inq.json()["id"]

    cb_res = await db_session.execute(
        select(TblCallback).where(TblCallback.website_inquiry_id == inquiry_id)
    )
    cb = cb_res.scalar_one_or_none()
    assert cb is not None
    assert cb.lead_unique_id == f"WEB{cb.callback_id}"
    assert cb.website_inquiry_id == inquiry_id

    # 2. Convert via callback_service -> creates Lead + TblLead + updates TblCallback + WebsiteInquiry
    conv = await callback_service.convert_callback_to_lead(
        db_session,
        admin,
        cb.callback_id,
        customer_type="BUY",
        name="Meena Gupta",
        email="meena@example.com",
        mobile="9829022211",
        alternate_mobile=None,
        address="Alwar Sector 4",
        refer_by_relation=None,
        refer_by_name=None,
        refer_by_mobile=None,
        source="Website Callback",
        assigned_to="EMP-0001",
    )
    lead_id = conv["lead_id"]
    assert lead_id.startswith("OB-")

    lead_row = (await db_session.execute(select(Lead).where(Lead.lead_id == lead_id))).scalar_one()
    tbl_lead_row = (
        await db_session.execute(select(TblLead).where(TblLead.lead_unique_id == lead_id))
    ).scalar_one()
    assert tbl_lead_row.lead_source_id == 4
    assert lead_row.full_name == "Meena Gupta"

    await db_session.refresh(cb)
    assert cb.lead_status == 5
    assert cb.lead_open == 0
    assert cb.lead_converted == 1
    assert cb.converted_lead_id == lead_id

    inq_row = (
        await db_session.execute(select(WebsiteInquiry).where(WebsiteInquiry.id == inquiry_id))
    ).scalar_one()
    assert inq_row.is_converted is True
    assert inq_row.converted_lead_id == lead_id

    # 3. Subsequent intake_service.convert_inquiry_to_lead raises HTTPException(400)
    with pytest.raises(HTTPException) as exc_info:
        await intake_service.convert_inquiry_to_lead(
            db_session, inquiry_id=inquiry_id, assigned_to="EMP-0001"
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_reschedule_status_transfer_reopen_state_machine(db_session):
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.identity import Department, Role, Employee
    from app.services.callback_service import callback_service

    dept = Department(name="Sales", code="SALES")
    db_session.add(dept)
    await db_session.flush()
    mgr_role = Role(
        department_id=dept.id,
        name="Sales Manager",
        code="SALES_MANAGER",
        permissions={"leads": ["view_all"]},
    )
    tc_role = Role(
        department_id=dept.id,
        name="Telecaller",
        code="TELECALLER",
        permissions={"leads": ["view_assigned"]},
    )
    db_session.add_all([mgr_role, tc_role])
    await db_session.flush()

    mgr = Employee(
        employee_id="EMP-M001",
        name="Manager",
        email="mgr@omshiv.in",
        mobile="9829080001",
        department_id=dept.id,
        role_id=mgr_role.id,
        is_active=True,
    )
    tc1 = Employee(
        employee_id="EMP-T101",
        name="TC One",
        email="tc101@omshiv.in",
        mobile="9829080002",
        department_id=dept.id,
        role_id=tc_role.id,
        is_active=True,
    )
    tc2 = Employee(
        employee_id="EMP-T102",
        name="TC Two",
        email="tc102@omshiv.in",
        mobile="9829080003",
        department_id=dept.id,
        role_id=tc_role.id,
        is_active=True,
    )
    db_session.add_all([mgr, tc1, tc2])
    await db_session.commit()
    await db_session.refresh(mgr)

    cb = await callback_service.create_callback(
        db_session,
        name="Suresh",
        mobile_number="9829055555",
        assigned_user_id="EMP-T101",
    )

    # 1. Past datetime raises HTTPException(400)
    past_dt = datetime.now(timezone.utc) - timedelta(hours=1)
    with pytest.raises(HTTPException) as exc_past:
        await callback_service.reschedule_callback(
            db_session,
            mgr,
            cb.callback_id,
            current_update="Call Back Later",
            remark="Missed",
            followup_datetime=past_dt,
        )
    assert exc_past.value.status_code == 400
    assert (
        exc_past.value.detail
        == "Schedule Date and Time should be greater than the current date and time."
    )

    # 2. Naive future UTC datetime normalizes cleanly & creates CallbackRescheduleLog
    naive_future = (datetime.now(timezone.utc) + timedelta(days=2)).replace(tzinfo=None)
    resched = await callback_service.reschedule_callback(
        db_session,
        mgr,
        cb.callback_id,
        current_update="Interested",
        remark="Will visit weekend",
        followup_datetime=naive_future,
    )
    assert resched["followup_datetime"] is not None
    logs = (
        await db_session.execute(
            select(CallbackRescheduleLog).where(
                CallbackRescheduleLog.callback_id == cb.callback_id
            )
        )
    ).scalars().all()
    assert len(logs) == 1

    # 3. Disqualified without reason -> 400; with reason -> locks lead_open=0
    with pytest.raises(HTTPException) as exc_no_reason:
        await callback_service.change_callback_status(
            db_session, mgr, cb.callback_id, lead_status=2, remark="No answer"
        )
    assert exc_no_reason.value.status_code == 400

    disq = await callback_service.change_callback_status(
        db_session,
        mgr,
        cb.callback_id,
        lead_status=2,
        remark="Not responding after 3 tries",
        disqualified_reason=3,
    )
    assert disq["lead_status"] == 2
    assert disq["lead_open"] == 0

    # 4. While lead_open == 0, reschedule, transfer, change_status, convert all raise 400
    future_aware = datetime.now(timezone.utc) + timedelta(days=3)
    for coro in [
        callback_service.reschedule_callback(
            db_session,
            mgr,
            cb.callback_id,
            current_update="Interested",
            remark="Try again",
            followup_datetime=future_aware,
        ),
        callback_service.transfer_callback(
            db_session,
            mgr,
            cb.callback_id,
            assigned_user_id="EMP-T102",
            remark="Reassign",
        ),
        callback_service.change_callback_status(
            db_session, mgr, cb.callback_id, lead_status=1, remark="Try reopen via status"
        ),
        callback_service.convert_callback_to_lead(
            db_session,
            mgr,
            cb.callback_id,
            customer_type="BUY",
            name="Suresh",
            email=None,
            mobile="9829055555",
            alternate_mobile=None,
            address="Alwar",
            refer_by_relation=None,
            refer_by_name=None,
            refer_by_mobile=None,
            source="Website Callback",
            assigned_to="EMP-T101",
        ),
    ]:
        with pytest.raises(HTTPException) as exc_locked:
            await coro
        assert exc_locked.value.status_code == 400
        assert "This Callback is closed" in exc_locked.value.detail

    # 5. Reopen restores lead_open=1 and lead_status=1; transfer resets lead_status=0, calls_status=0
    reopened = await callback_service.reopen_callback(
        db_session, mgr, cb.callback_id, remark="Customer called back"
    )
    assert reopened["lead_open"] == 1
    assert reopened["lead_status"] == 1

    await callback_service.log_callback_call(
        db_session, mgr, cb.callback_id, remark="Connected call"
    )
    transferred = await callback_service.transfer_callback(
        db_session,
        mgr,
        cb.callback_id,
        assigned_user_id="EMP-T102",
        remark="Handoff to TC2",
    )
    assert transferred["assigned_user_id"] == "EMP-T102"
    assert transferred["lead_status"] == 0
    assert transferred["calls_status"] == 0

    # 6. Status 5 blocked in change_callback_status; status 6 locks lead_open=0 and blocks reopen
    with pytest.raises(HTTPException) as exc_status5:
        await callback_service.change_callback_status(
            db_session, mgr, cb.callback_id, lead_status=5, remark="Direct convert"
        )
    assert exc_status5.value.status_code == 400

    prop_conv = await callback_service.change_callback_status(
        db_session, mgr, cb.callback_id, lead_status=6, remark="Property converted"
    )
    assert prop_conv["lead_status"] == 6
    assert prop_conv["lead_open"] == 0
    assert prop_conv["lead_converted"] == 1

    with pytest.raises(HTTPException) as exc_reopen_terminal:
        await callback_service.reopen_callback(
            db_session, mgr, cb.callback_id, remark="Cannot reopen terminal"
        )
    assert exc_reopen_terminal.value.status_code == 400


@pytest.mark.asyncio
async def test_callback_dashboard_tabs_detail_export_and_reverse_sync(test_client, db_session):
    from sqlalchemy import select
    from app.models.identity import Department, Role, Employee
    from app.models.properties import Property
    from app.models.property_master import PincodeMaster
    from app.services.callback_service import callback_service
    from app.services.intake_service import intake_service

    dept = Department(name="Sales", code="SALES")
    db_session.add(dept)
    await db_session.flush()
    mgr_role = Role(
        department_id=dept.id,
        name="Sales Manager",
        code="SALES_MANAGER",
        permissions={"leads": ["view_all"]},
    )
    tc_role = Role(
        department_id=dept.id,
        name="Telecaller",
        code="TELECALLER",
        permissions={"leads": ["view_assigned"]},
    )
    db_session.add_all([mgr_role, tc_role])
    await db_session.flush()

    mgr = Employee(
        employee_id="EMP-M010",
        name="Manager Ten",
        email="mgr10@omshiv.in",
        mobile="9829070001",
        department_id=dept.id,
        role_id=mgr_role.id,
        is_active=True,
    )
    tc = Employee(
        employee_id="EMP-T010",
        name="Telecaller Ten",
        email="tc10@omshiv.in",
        mobile="9829070002",
        department_id=dept.id,
        role_id=tc_role.id,
        is_active=True,
    )
    db_session.add_all([mgr, tc])
    await db_session.flush()

    pincode = PincodeMaster(pincode="301001", city="Alwar", district="Alwar", state="Rajasthan")
    db_session.add(pincode)
    await db_session.flush()

    prop = Property(
        property_id="OP-2026-00077",
        listing_type=2,
        category_code=1,
        sub_category_code=2,
        title="3BHK Villa <Script>",
        pincode="301001",
        expected_price=7500000,
        owner_name="Owner",
        owner_mobile="919829077777",
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(mgr)
    await db_session.refresh(tc)

    assert callback_service.has_view_all(mgr) is True
    assert callback_service.has_view_all(tc) is False

    # Create callback for tc with property_code and XSS-like name to verify escaping in XLS
    cb = await callback_service.create_callback(
        db_session,
        name="<b>Anita</b>",
        mobile_number="9829066666",
        property_code="OP-2026-00077",
        assigned_user_id="EMP-T010",
    )
    # Schedule 10 minutes in future (counts as today_calls)
    await callback_service.reschedule_callback(
        db_session,
        tc,
        cb.callback_id,
        current_update="Site Visit Planned",
        remark="Confirming slot",
        followup_datetime=datetime.now(timezone.utc) + timedelta(minutes=10),
    )

    counts = await callback_service.get_dashboard_counts(db_session, tc)
    assert counts["new_calls"] == 1
    assert counts["today_calls"] == 1
    assert counts["open_calls"] == 1
    assert counts["all_calls"] == 1

    # Simulate an overdue followup for missing_calls check
    cb.followup_datetime = datetime.now(timezone.utc) - timedelta(minutes=30)
    await db_session.commit()
    counts_after = await callback_service.get_dashboard_counts(db_session, mgr)
    assert counts_after["missing_calls"] == 1

    detail = await callback_service.get_callback_detail(db_session, tc, cb.callback_id)
    assert detail["property_title"] == "3BHK Villa <Script>"
    assert len(detail["reschedule_history"]) == 1
    assert len(detail["activities"]) >= 2

    xls_html = await callback_service.export_callbacks_xls(db_session, tc, tab="all")
    assert "&lt;b&gt;Anita&lt;/b&gt;" in xls_html
    assert "<b>Anita</b>" not in xls_html

    # Reverse sync: inquiry -> convert_inquiry_to_lead updates paired TblCallback
    resp_inq = await test_client.post(
        "/v1/intake/inquiry",
        json={
            "inquiry_type": "CALLBACK",
            "full_name": "Karan Singh",
            "mobile": "9829066677",
            "details": {"message": "Call back ASAP"},
        },
    )
    assert resp_inq.status_code == 201
    inq_id = resp_inq.json()["id"]

    lead = await intake_service.convert_inquiry_to_lead(
        db_session, inquiry_id=inq_id, assigned_to="EMP-T010", converted_by_emp_id="EMP-M010"
    )
    paired_cb = (
        await db_session.execute(
            select(TblCallback).where(TblCallback.website_inquiry_id == inq_id)
        )
    ).scalar_one()
    assert paired_cb.lead_status == 5
    assert paired_cb.lead_converted == 1
    assert paired_cb.lead_open == 0
    assert paired_cb.converted_lead_id == lead.lead_id


@pytest.mark.asyncio
async def test_callback_conversion_truncates_preferred_locality_and_validates_assignees(db_session):
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.identity import Department, Role, Employee
    from app.models.leads import Lead, TblLead
    from app.services.callback_service import callback_service

    dept = Department(name="Sales", code="SALES")
    db_session.add(dept)
    await db_session.flush()
    mgr_role = Role(
        department_id=dept.id,
        name="Sales Manager",
        code="SALES_MANAGER",
        permissions={"leads": ["view_all"]},
    )
    db_session.add(mgr_role)
    await db_session.flush()

    mgr = Employee(
        employee_id="EMP-M020",
        name="Manager Twenty",
        email="mgr20@omshiv.in",
        mobile="9829071001",
        department_id=dept.id,
        role_id=mgr_role.id,
        is_active=True,
    )
    inactive_emp = Employee(
        employee_id="EMP-INACT",
        name="Inactive Staff",
        email="inact@omshiv.in",
        mobile="9829071002",
        department_id=dept.id,
        role_id=mgr_role.id,
        is_active=False,
    )
    db_session.add_all([mgr, inactive_emp])
    await db_session.commit()
    await db_session.refresh(mgr)

    # 1. create_callback rejects non-existent or inactive explicit assigned_user_id
    for bad_emp_id in ("EMP-NOPE", "EMP-INACT"):
        with pytest.raises(HTTPException) as exc_create:
            await callback_service.create_callback(
                db_session,
                name="Bad Assignee Test",
                mobile_number="9829071111",
                assigned_user_id=bad_emp_id,
            )
        assert exc_create.value.status_code in (400, 404)

    cb = await callback_service.create_callback(
        db_session,
        name="Long Address Customer",
        mobile_number="9829071112",
        assigned_user_id="EMP-M020",
    )

    # 2. convert_callback_to_lead rejects non-existent or inactive explicit assigned_to
    for bad_emp_id in ("EMP-NOPE", "EMP-INACT"):
        with pytest.raises(HTTPException) as exc_conv_bad:
            await callback_service.convert_callback_to_lead(
                db_session,
                mgr,
                cb.callback_id,
                customer_type="BUY",
                name="Long Address Customer",
                email=None,
                mobile="9829071112",
                alternate_mobile=None,
                address="Short Address",
                refer_by_relation=None,
                refer_by_name=None,
                refer_by_mobile=None,
                source="Website Callback",
                assigned_to=bad_emp_id,
            )
        assert exc_conv_bad.value.status_code in (400, 404)

    # 3. Long address (>100 chars) truncates Lead.preferred_locality to 100 while preserving full TblLead.address
    long_address = "Plot No 42, Near Main Circle, Opposite Central Park, Sector 7 Extension, Alwar, Rajasthan - 301001, India"
    assert len(long_address) > 100

    conv = await callback_service.convert_callback_to_lead(
        db_session,
        mgr,
        cb.callback_id,
        customer_type="BUY",
        name="Long Address Customer",
        email=None,
        mobile="9829071112",
        alternate_mobile=None,
        address=long_address,
        refer_by_relation=None,
        refer_by_name=None,
        refer_by_mobile=None,
        source="Website Callback",
        assigned_to="EMP-M020",
    )
    lead_id = conv["lead_id"]
    lead_row = (await db_session.execute(select(Lead).where(Lead.lead_id == lead_id))).scalar_one()
    tbl_lead_row = (
        await db_session.execute(select(TblLead).where(TblLead.lead_unique_id == lead_id))
    ).scalar_one()

    assert lead_row.preferred_locality == long_address[:100]
    assert len(lead_row.preferred_locality) == 100
    assert tbl_lead_row.address == long_address
    assert tbl_lead_row.indv_property_address == long_address


@pytest.mark.asyncio
async def test_convert_inquiry_blocked_when_paired_callback_closed_or_terminal(test_client, db_session):
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.identity import Department, Role, Employee
    from app.models.leads import Lead
    from app.services.callback_service import callback_service
    from app.services.intake_service import intake_service

    dept = Department(name="Sales", code="SALES")
    db_session.add(dept)
    await db_session.flush()
    mgr_role = Role(
        department_id=dept.id,
        name="Sales Manager",
        code="SALES_MANAGER",
        permissions={"leads": ["view_all"]},
    )
    db_session.add(mgr_role)
    await db_session.flush()
    mgr = Employee(
        employee_id="EMP-M030",
        name="Manager Thirty",
        email="mgr30@omshiv.in",
        mobile="9829072001",
        department_id=dept.id,
        role_id=mgr_role.id,
        is_active=True,
    )
    db_session.add(mgr)
    await db_session.commit()
    await db_session.refresh(mgr)

    # Case A: Paired callback closed via Disqualified (status 2, lead_open=0)
    resp_a = await test_client.post(
        "/v1/intake/inquiry",
        json={
            "inquiry_type": "CALLBACK",
            "full_name": "Disqualified User",
            "mobile": "9829072011",
            "details": {"message": "Test"},
        },
    )
    assert resp_a.status_code == 201
    inq_a_id = resp_a.json()["id"]
    cb_a = (
        await db_session.execute(select(TblCallback).where(TblCallback.website_inquiry_id == inq_a_id))
    ).scalar_one()
    await callback_service.change_callback_status(
        db_session, mgr, cb_a.callback_id, lead_status=2, remark="Not interested", disqualified_reason=2
    )

    leads_before = len((await db_session.execute(select(Lead))).scalars().all())
    with pytest.raises(HTTPException) as exc_a:
        await intake_service.convert_inquiry_to_lead(db_session, inquiry_id=inq_a_id, assigned_to="EMP-M030")
    assert exc_a.value.status_code == 400
    assert len((await db_session.execute(select(Lead))).scalars().all()) == leads_before

    # Case B: Paired callback closed via Converted Property (status 6, lead_open=0)
    resp_b = await test_client.post(
        "/v1/intake/inquiry",
        json={
            "inquiry_type": "CALLBACK",
            "full_name": "Converted Property User",
            "mobile": "9829072012",
            "details": {"message": "Test"},
        },
    )
    assert resp_b.status_code == 201
    inq_b_id = resp_b.json()["id"]
    cb_b = (
        await db_session.execute(select(TblCallback).where(TblCallback.website_inquiry_id == inq_b_id))
    ).scalar_one()
    await callback_service.change_callback_status(
        db_session, mgr, cb_b.callback_id, lead_status=6, remark="Property deal done"
    )

    with pytest.raises(HTTPException) as exc_b:
        await intake_service.convert_inquiry_to_lead(db_session, inquiry_id=inq_b_id, assigned_to="EMP-M030")
    assert exc_b.value.status_code == 400
    assert len((await db_session.execute(select(Lead))).scalars().all()) == leads_before
