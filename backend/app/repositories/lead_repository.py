from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_
from app.models.leads import Lead, LeadActivity, LeadActionLog
from app.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    def __init__(self):
        super().__init__(Lead)

    async def get_by_id_or_lead_id(self, db: AsyncSession, identifier: str) -> Optional[Lead]:
        # Try by sequence code (OB-YYYY-NNNNNN)
        stmt = (
            select(Lead)
            .options(selectinload(Lead.activities))
            .where(Lead.lead_id == identifier, Lead.deleted_at.is_(None))
        )
        res = await db.execute(stmt)
        lead = res.scalar_one_or_none()
        if lead:
            return lead

        # Fallback to numeric primary key
        if identifier.isdigit():
            stmt_pk = (
                select(Lead)
                .options(selectinload(Lead.activities))
                .where(Lead.id == int(identifier), Lead.deleted_at.is_(None))
            )
            res_pk = await db.execute(stmt_pk)
            return res_pk.scalar_one_or_none()

        return None

    async def get_work_queue(self, db: AsyncSession, target_rep: str) -> List[Lead]:
        stmt = (
            select(Lead)
            .options(selectinload(Lead.activities))
            .where(
                and_(
                    Lead.deleted_at.is_(None),
                    Lead.assigned_to == target_rep,
                    Lead.stage.not_in(["WON", "LOST", "NURTURE"]),
                )
            )
        )
        res = await db.execute(stmt)
        leads = list(res.scalars().all())
        for l in leads:
            l.activities.sort(key=lambda a: a.created_at, reverse=True)
        return leads


lead_repo = LeadRepository()
