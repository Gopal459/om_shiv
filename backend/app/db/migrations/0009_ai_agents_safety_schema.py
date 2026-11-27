"""Migration 0009: Create AI Agents safety, consent, HITL approval, execution log, and property alert tables."""

from sqlalchemy.ext.asyncio import AsyncEngine
from app.models.ai_agents import (
    AIAgentConfig,
    CustomerConsent,
    AIApprovalQueue,
    AIAgentExecutionLog,
    PropertyAlertHistory,
)

requires_session = False

AI_TABLES = [
    AIAgentConfig.__table__,
    CustomerConsent.__table__,
    AIApprovalQueue.__table__,
    AIAgentExecutionLog.__table__,
    PropertyAlertHistory.__table__,
]


async def upgrade(engine: AsyncEngine) -> None:
    """Create the 5 AI agent governance tables idempotently (SQLite & PostgreSQL)."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: AIAgentConfig.metadata.create_all(
                sync_conn,
                tables=AI_TABLES,
                checkfirst=True,
            )
        )
