"""Migration 0002: Universal soft-delete columns (deleted_at) across all core tables."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

requires_session = False

TABLES_WITH_SOFT_DELETE = [
    "departments",
    "roles",
    "employees",
    "leads",
    "properties",
    "property_master_groups",
    "property_master_options",
    "pincode_master",
    "website_inquiries",
    "builder_projects",
    "owner_ad_requests",
    "system_settings",
]


async def upgrade(engine: AsyncEngine) -> None:
    is_sqlite = "sqlite" in str(engine.url)

    async with engine.begin() as conn:
        for table in TABLES_WITH_SOFT_DELETE:
            try:
                if is_sqlite:
                    # Check table exists in SQLite
                    res = await conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
                        {"t": table},
                    )
                    if not res.scalar():
                        continue

                    # Check columns
                    col_info = await conn.execute(text(f"PRAGMA table_info({table})"))
                    cols = [row[1] for row in col_info.fetchall()]
                    if "deleted_at" not in cols:
                        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN deleted_at TIMESTAMP NULL"))
                else:
                    await conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE NULL")
                    )
            except Exception:
                pass
