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
