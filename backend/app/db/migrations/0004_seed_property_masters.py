"""Migration 0004: Seed dynamic property master attribute groups, options, and postal pincodes."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.property_master_service import seed_property_masters

requires_session = True


async def upgrade(session: AsyncSession) -> None:
    await seed_property_masters(session)
