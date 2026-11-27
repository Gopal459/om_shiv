"""Migration 0010: Create Franchise Outlets, Channel Partners, and Partner Payouts tables."""

from sqlalchemy.ext.asyncio import AsyncEngine
from app.models.franchise import ChannelPartner, FranchiseOutlet, PartnerPayout

requires_session = False

FRANCHISE_TABLES = [
    FranchiseOutlet.__table__,
    ChannelPartner.__table__,
    PartnerPayout.__table__,
]


async def upgrade(engine: AsyncEngine) -> None:
    """Create franchise network tables idempotently (SQLite & PostgreSQL)."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: FranchiseOutlet.metadata.create_all(
                sync_conn,
                tables=FRANCHISE_TABLES,
                checkfirst=True,
            )
        )
