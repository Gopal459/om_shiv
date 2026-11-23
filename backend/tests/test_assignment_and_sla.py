import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.identity import Department, Role, Employee
from app.models.leads import Lead, LeadActivity
from app.models.settings import SystemSetting
from app.services.settings_service import seed_system_settings
from app.services.assignment_service import assign_lead
from app.workers.sla_worker import process_sla_escalations


@pytest.mark.asyncio
async def test_assignment_round_robin_matching(db_session: AsyncSession):
    await seed_system_settings(db_session)

    dept = Department(name="Sales Dept", code="SALES_DEPT")
    db_session.add(dept)
    await db_session.flush()

    role = Role(department_id=dept.id, name="Sales Rep", code="SALES_REP_TEST", permissions={})
    db_session.add(role)
    await db_session.flush()

    emp1 = Employee(
        employee_id="EMP-1001",
        name="Amit Verma",
        mobile="9829011111",
        department_id=dept.id,
        role_id=role.id,
        handled_categories=["RESIDENTIAL"],
        budget_min_cr=0.1,
        budget_max_cr=2.0,
        is_active=True,
    )
    emp2 = Employee(
        employee_id="EMP-1002",
        name="Rohit Sharma",
        mobile="9829022222",
        department_id=dept.id,
        role_id=role.id,
        handled_categories=["RESIDENTIAL"],
        budget_min_cr=0.1,
        budget_max_cr=2.0,
        is_active=True,
    )
    db_session.add_all([emp1, emp2])
    await db_session.commit()

    lead1 = Lead(
        lead_id="OB-2026-000101",
        full_name="Client One",
        mobile="919829033333",
        source="PROPERTY_INQUIRY",
        lead_type="BUYER",
        budget_min=5000000,  # 0.5 Cr
        budget_max=8000000,
        preferred_locality="Alwar",
        stage="NEW",
        is_untouched=True,
    )
    lead2 = Lead(
        lead_id="OB-2026-000102",
        full_name="Client Two",
        mobile="919829044444",
        source="PROPERTY_INQUIRY",
        lead_type="BUYER",
        budget_min=5000000,
        budget_max=8000000,
        preferred_locality="Alwar",
        stage="NEW",
        is_untouched=True,
    )
    db_session.add_all([lead1, lead2])
    await db_session.commit()

    # Assign lead 1
    assigned1 = await assign_lead(lead1, db=db_session, category="RESIDENTIAL")
    assert assigned1 is not None
    assert assigned1.employee_id in ["EMP-1001", "EMP-1002"]
    assert lead1.assigned_to == assigned1.employee_id

    # Assign lead 2 -> round robin selects the other rep
    assigned2 = await assign_lead(lead2, db=db_session, category="RESIDENTIAL")
    assert assigned2 is not None
    assert assigned2.employee_id in ["EMP-1001", "EMP-1002"]
    assert assigned2.employee_id != assigned1.employee_id
    assert lead2.assigned_to == assigned2.employee_id


@pytest.mark.asyncio
async def test_assignment_leave_cover_rerouting(db_session: AsyncSession):
    await seed_system_settings(db_session)

    dept = Department(name="Commercial Sales", code="COMM_SALES")
    db_session.add(dept)
    await db_session.flush()

    role = Role(department_id=dept.id, name="Commercial Executive", code="COMM_EXEC", permissions={})
    db_session.add(role)
    await db_session.flush()

    manager = Employee(
        employee_id="EMP-1099",
        name="Deepak Manager",
        mobile="9829099900",
        department_id=dept.id,
        role_id=role.id,
        handled_categories=["COMMERCIAL"],
        budget_min_cr=1.0,
        budget_max_cr=10.0,
        is_active=True,
    )
    db_session.add(manager)
    await db_session.flush()

    rep_on_leave = Employee(
        employee_id="EMP-1050",
        name="Vikram OnLeave",
        mobile="9829055555",
        department_id=dept.id,
        role_id=role.id,
        reporting_to="EMP-1099",
        leave_approver="EMP-1099",
        handled_categories=["COMMERCIAL"],
        budget_min_cr=1.0,
        budget_max_cr=10.0,
        is_active=True,
        is_on_leave=True,
    )
    db_session.add(rep_on_leave)
    await db_session.commit()

    lead = Lead(
        lead_id="OB-2026-000103",
        full_name="Commercial Client",
        mobile="919829055501",
        source="WEBSITE_FORM",
        lead_type="BUYER",
        budget_min=20000000,  # 2 Cr
        budget_max=30000000,
        stage="NEW",
        is_untouched=True,
    )
    db_session.add(lead)
    await db_session.commit()

    assigned = await assign_lead(lead, db=db_session, category="COMMERCIAL")
    # Rep is on leave, so assignment reroutes to leave_approver (manager)
    assert assigned.employee_id == "EMP-1099"
    assert lead.assigned_to == "EMP-1099"


@pytest.mark.asyncio
async def test_sla_escalations_untouched_reminders_and_escalations(db_session: AsyncSession):
    await seed_system_settings(db_session)
    now = datetime.now(timezone.utc)

    # Lead 1: untouched for 4 hours (> 3h untouched SLA)
    lead_3h = Lead(
        lead_id="OB-2026-000201",
        full_name="Untouched 4h Lead",
        mobile="919829066601",
        stage="NEW",
        is_untouched=True,
        assigned_to="EMP-1001",
        untouched_timer_start=now - timedelta(hours=4),
    )
    # Lead 2: untouched for 25 hours (> 24h escalation SLA)
    lead_24h = Lead(
        lead_id="OB-2026-000202",
        full_name="Untouched 25h Lead",
        mobile="919829066602",
        stage="NEW",
        is_untouched=True,
        assigned_to="EMP-1050",
        untouched_timer_start=now - timedelta(hours=25),
    )
    # Lead 3: HOT lead untouched for 4 hours
    lead_hot = Lead(
        lead_id="OB-2026-000203",
        full_name="Hot Untouched Lead",
        mobile="919829066603",
        stage="NEW",
        temperature="HOT",
        is_untouched=True,
        assigned_to="EMP-1002",
        untouched_timer_start=now - timedelta(hours=4),
    )
    # Lead 4: Fresh untouched lead (30 mins old -> no action)
    lead_fresh = Lead(
        lead_id="OB-2026-000204",
        full_name="Fresh Lead",
        mobile="919829066604",
        stage="NEW",
        is_untouched=True,
        assigned_to="EMP-1001",
        untouched_timer_start=now - timedelta(minutes=30),
    )
    db_session.add_all([lead_3h, lead_24h, lead_hot, lead_fresh])
    await db_session.commit()

    # Run SLA worker bypassing quiet hours
    results = await process_sla_escalations(db=db_session, bypass_quiet_hours=True)

    assert results["reminders_sent"] >= 1
    assert results["escalations_sent"] >= 1
    assert results["hot_escalations_sent"] >= 1


@pytest.mark.asyncio
async def test_sla_escalation_respects_quiet_hours(db_session: AsyncSession):
    from app.services.settings_service import settings_service

    await seed_system_settings(db_session)
    settings_service.clear_cache()

    # Force quiet hours active window covering all 24 hours
    setting = await db_session.get(SystemSetting, "quiet_hours_start")
    if setting:
        setting.value = "00:00"
    end_setting = await db_session.get(SystemSetting, "quiet_hours_end")
    if end_setting:
        end_setting.value = "23:59"
    await db_session.commit()
    settings_service.clear_cache()

    # Process without bypass -> returns quiet hours suppression
    results = await process_sla_escalations(db=db_session, bypass_quiet_hours=False)
    assert results.get("quiet_hours_active") is True
    assert results.get("notifications_suppressed") is True
