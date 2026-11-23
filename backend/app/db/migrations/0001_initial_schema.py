"""Migration 0001: Initial schema creation registering all SQLAlchemy models."""
from sqlalchemy.ext.asyncio import AsyncEngine
from app.db.base import Base

requires_session = False


async def upgrade(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
