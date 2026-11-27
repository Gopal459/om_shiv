"""Migration 0013: Create callback CRM tables and extend website_inquiries for Report A Problem."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.callbacks import (
    CallbackActivity,
    CallbackRescheduleLog,
    TblCallback,
)

requires_session = False

CALLBACK_TABLES = [
    TblCallback.__table__,
    CallbackRescheduleLog.__table__,
    CallbackActivity.__table__,
]

# (table_name, column_name, sqlite_ddl, pg_ddl)
COLUMN_ADDITIONS = [
    ("website_inquiries", "status", "VARCHAR(32) NOT NULL DEFAULT 'NEW'", "VARCHAR(32) NOT NULL DEFAULT 'NEW'"),
    ("website_inquiries", "assigned_to", "VARCHAR(32) NULL", "VARCHAR(32) NULL"),
    ("website_inquiries", "related_property_code", "VARCHAR(32) NULL", "VARCHAR(32) NULL"),
    ("website_inquiries", "resolution_remark", "TEXT NULL", "TEXT NULL"),
    ("website_inquiries", "resolved_by", "VARCHAR(32) NULL", "VARCHAR(32) NULL"),
    ("website_inquiries", "resolved_at", "TIMESTAMP NULL", "TIMESTAMP WITH TIME ZONE NULL"),
    ("website_inquiries", "updated_at", "TIMESTAMP NULL", "TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW()"),
]


async def upgrade(engine: AsyncEngine) -> None:
    """Create tbl_callback, reschedule log, activity tables and add inquiry triage columns idempotently."""
    is_sqlite = "sqlite" in str(engine.url)

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: TblCallback.metadata.create_all(
                sync_conn,
                tables=CALLBACK_TABLES,
                checkfirst=True,
            )
        )

        for table_name, col_name, sqlite_ddl, pg_ddl in COLUMN_ADDITIONS:
            if is_sqlite:
                res = await conn.execute(text(f"PRAGMA table_info({table_name})"))
                existing_cols = {row[1] for row in res.fetchall()}
                if col_name not in existing_cols:
                    await conn.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {sqlite_ddl}")
                    )
            else:
                await conn.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {pg_ddl}")
                )
