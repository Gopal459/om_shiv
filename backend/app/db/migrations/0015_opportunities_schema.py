"""Migration 0015: Create opportunities CRM relational tables and sequence counter."""

from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.opportunities import (
    OpportunityActivity,
    OpportunityLocation,
    OpportunityRescheduleLog,
    OpportunitySequence,
    TblOpportunity,
)

requires_session = False

OPPORTUNITY_TABLES = [
    OpportunitySequence.__table__,
    TblOpportunity.__table__,
    OpportunityLocation.__table__,
    OpportunityRescheduleLog.__table__,
    OpportunityActivity.__table__,
]


async def upgrade(engine: AsyncEngine) -> None:
    """Create opportunity_sequences, tbl_opportunities, locations, reschedules, and activities idempotently."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: TblOpportunity.metadata.create_all(
                sync_conn,
                tables=OPPORTUNITY_TABLES,
                checkfirst=True,
            )
        )
