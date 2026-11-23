import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

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


async def ensure_soft_delete_columns(engine: AsyncEngine) -> None:
    """Safely adds `deleted_at` column to existing database tables if not already present."""
    try:
        is_sqlite = "sqlite" in str(engine.url)

        async with engine.begin() as conn:
            for table in TABLES_WITH_SOFT_DELETE:
                try:
                    if is_sqlite:
                        # Check table exists in sqlite
                        table_check = await conn.execute(
                            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:tbl"),
                            {"tbl": table},
                        )
                        if not table_check.scalar():
                            continue

                        # Check existing columns in sqlite
                        col_info = await conn.execute(text(f"PRAGMA table_info({table})"))
                        cols = [row[1] for row in col_info.fetchall()]
                        if "deleted_at" not in cols:
                            logger.info(f"Adding deleted_at column to SQLite table '{table}'")
                            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN deleted_at TIMESTAMP NULL"))
                    else:
                        # PostgreSQL / MySQL
                        await conn.execute(
                            text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE NULL")
                        )
                except Exception as table_err:
                    logger.debug(f"Notice during soft delete check on {table}: {table_err}")
    except Exception as exc:
        logger.warning(f"Soft delete column verification notice: {exc}")
