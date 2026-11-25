from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.settings import SystemSetting, AuditLog
from app.repositories.base import BaseRepository


class SettingRepository(BaseRepository[SystemSetting]):
    def __init__(self):
        super().__init__(SystemSetting)

    async def get_by_key(self, db: AsyncSession, key: str) -> Optional[SystemSetting]:
        stmt = select(SystemSetting).where(
            SystemSetting.key == key,
            SystemSetting.deleted_at.is_(None),
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(self, db: AsyncSession) -> List[SystemSetting]:
        stmt = (
            select(SystemSetting)
            .where(SystemSetting.deleted_at.is_(None))
            .order_by(SystemSetting.category.asc(), SystemSetting.key.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def list_audit_logs(self, db: AsyncSession, limit: int = 50) -> List[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())


setting_repo = SettingRepository()
