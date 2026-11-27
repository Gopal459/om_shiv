"""Migration 0012: Link channel_partners.employee_id to employees.employee_id."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

requires_session = False


async def upgrade(engine: AsyncEngine) -> None:
    """Add employee_id column and unique index on channel_partners idempotently."""
    is_sqlite = "sqlite" in str(engine.url)

    async with engine.begin() as conn:
        if is_sqlite:
            res = await conn.execute(text("PRAGMA table_info(channel_partners)"))
            existing_cols = {row[1] for row in res.fetchall()}
            if "employee_id" not in existing_cols:
                await conn.execute(
                    text("ALTER TABLE channel_partners ADD COLUMN employee_id VARCHAR(32) NULL")
                )
        else:
            await conn.execute(
                text("ALTER TABLE channel_partners ADD COLUMN IF NOT EXISTS employee_id VARCHAR(32) NULL")
            )

        try:
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_channel_partners_employee_id "
                    "ON channel_partners (employee_id)"
                )
            )
        except Exception:
            pass
