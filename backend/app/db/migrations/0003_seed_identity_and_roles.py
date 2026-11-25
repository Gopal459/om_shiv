"""Migration 0003: Seed departments, default dynamic roles, and root Super Admin."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.identity_seed import seed_departments_and_roles, seed_admin_user

requires_session = True


async def upgrade(session: AsyncSession) -> None:
    await seed_departments_and_roles(session)
    await seed_admin_user(session)
