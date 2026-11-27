"""Migration 0011: Extend franchise & lead tables for 4-Tier Channel Partner governance."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from app.models.franchise import CPMediatedMeeting

requires_session = False

# (table_name, column_name, sqlite_ddl, pg_ddl)
COLUMN_ADDITIONS = [
    ("channel_partners", "cp_type", "VARCHAR(32) NOT NULL DEFAULT 'BROKER_CP'", "VARCHAR(32) NOT NULL DEFAULT 'BROKER_CP'"),
    ("channel_partners", "has_office_setup", "BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("channel_partners", "office_address", "TEXT NULL", "TEXT NULL"),
    ("channel_partners", "co_broking_split_pct", "NUMERIC(5,2) NOT NULL DEFAULT 50.0", "NUMERIC(5,2) NOT NULL DEFAULT 50.0"),
    ("channel_partners", "active_level", "VARCHAR(16) NOT NULL DEFAULT 'L1'", "VARCHAR(16) NOT NULL DEFAULT 'L1'"),
    ("channel_partners", "joined_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP", "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"),
    ("channel_partners", "is_certified", "BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("channel_partners", "certified_at", "TIMESTAMP NULL", "TIMESTAMP WITH TIME ZONE NULL"),
    ("channel_partners", "recommended_by", "VARCHAR(32) NULL", "VARCHAR(32) NULL"),
    ("channel_partners", "recommended_at", "TIMESTAMP NULL", "TIMESTAMP WITH TIME ZONE NULL"),
    ("channel_partners", "l3_approved_by", "VARCHAR(32) NULL", "VARCHAR(32) NULL"),
    ("channel_partners", "l3_approved_at", "TIMESTAMP NULL", "TIMESTAMP WITH TIME ZONE NULL"),
    ("channel_partners", "clean_record", "BOOLEAN NOT NULL DEFAULT 1", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("channel_partners", "violation_notes", "TEXT NULL", "TEXT NULL"),
    ("channel_partners", "suspended_at", "TIMESTAMP NULL", "TIMESTAMP WITH TIME ZONE NULL"),
    ("channel_partners", "suspended_by", "VARCHAR(32) NULL", "VARCHAR(32) NULL"),
    ("channel_partners", "suspension_reason", "TEXT NULL", "TEXT NULL"),
    ("channel_partners", "fixed_reward_amount", "NUMERIC(12,2) NOT NULL DEFAULT 5000.0", "NUMERIC(12,2) NOT NULL DEFAULT 5000.0"),
    ("channel_partners", "annual_reward_limit", "INTEGER NOT NULL DEFAULT 5", "INTEGER NOT NULL DEFAULT 5"),
    ("channel_partners", "tracking_code", "VARCHAR(40) NULL", "VARCHAR(40) NULL"),
    ("channel_partners", "social_handle", "VARCHAR(150) NULL", "VARCHAR(150) NULL"),
    ("channel_partners", "is_top_creator", "BOOLEAN NOT NULL DEFAULT 0", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("channel_partners", "monthly_retainer_amount", "NUMERIC(12,2) NOT NULL DEFAULT 0.0", "NUMERIC(12,2) NOT NULL DEFAULT 0.0"),
    ("partner_payouts", "payout_type", "VARCHAR(32) NOT NULL DEFAULT 'COMMISSION'", "VARCHAR(32) NOT NULL DEFAULT 'COMMISSION'"),
    ("partner_payouts", "fiscal_year", "VARCHAR(16) NOT NULL DEFAULT '2026-27'", "VARCHAR(16) NOT NULL DEFAULT '2026-27'"),
    ("leads", "partner_id", "INTEGER NULL", "INTEGER NULL"),
    ("leads", "referral_code", "VARCHAR(40) NULL", "VARCHAR(40) NULL"),
    ("leads", "accompanied_by", "VARCHAR(32) NULL", "VARCHAR(32) NULL"),
]


async def upgrade(engine: AsyncEngine) -> None:
    """Create cp_mediated_meetings table and add 4-tier CP columns idempotently."""
    is_sqlite = "sqlite" in str(engine.url)

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: CPMediatedMeeting.metadata.create_all(
                sync_conn,
                tables=[CPMediatedMeeting.__table__],
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

        # Ensure unique index on channel_partners.tracking_code if missing
        try:
            await conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS ix_channel_partners_tracking_code ON channel_partners (tracking_code)")
            )
        except Exception:
            pass
