"""Migration 0014: Add customer_type column to leads and tbl_leads."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

requires_session = False

# (table_name, column_name, sqlite_ddl, pg_ddl)
COLUMN_ADDITIONS = [
    ("leads", "customer_type", "VARCHAR(32) NOT NULL DEFAULT 'USER'", "VARCHAR(32) NOT NULL DEFAULT 'USER'"),
    ("tbl_leads", "customer_type", "VARCHAR(32) NOT NULL DEFAULT 'USER'", "VARCHAR(32) NOT NULL DEFAULT 'USER'"),
]


async def upgrade(engine: AsyncEngine) -> None:
    """Add customer_type column to leads and tbl_leads idempotently."""
    is_sqlite = "sqlite" in str(engine.url)

    async with engine.begin() as conn:
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
