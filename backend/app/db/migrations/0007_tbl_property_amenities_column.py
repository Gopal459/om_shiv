import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def upgrade(engine: AsyncEngine) -> None:
    """Adds missing 'amenities' column to tbl_property table if not already present."""
    async with engine.begin() as conn:
        try:
            # Check SQLite table info
            res = await conn.execute(text("PRAGMA table_info(tbl_property)"))
            cols = [row[1] for row in res.fetchall()]
            if cols and "amenities" not in cols:
                await conn.execute(text("ALTER TABLE tbl_property ADD COLUMN amenities TEXT NULL"))
                logger.info("Added 'amenities' column to tbl_property in SQLite successfully.")
        except Exception:
            # PostgreSQL fallback
            try:
                await conn.execute(text("ALTER TABLE tbl_property ADD COLUMN IF NOT EXISTS amenities TEXT NULL"))
                logger.info("Added 'amenities' column to tbl_property in PostgreSQL successfully.")
            except Exception as e:
                logger.warning(f"Notice applying amenities column migration: {e}")
