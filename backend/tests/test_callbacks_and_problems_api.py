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
