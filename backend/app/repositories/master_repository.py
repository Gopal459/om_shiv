from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.property_master import PropertyMasterGroup, PropertyMasterOption, PincodeMaster
from app.repositories.base import BaseRepository


class MasterRepository(BaseRepository[PropertyMasterGroup]):
    def __init__(self):
        super().__init__(PropertyMasterGroup)

    async def get_pincode(self, db: AsyncSession, pincode: str) -> Optional[PincodeMaster]:
        stmt = select(PincodeMaster).where(
            PincodeMaster.pincode == pincode.strip(),
            PincodeMaster.deleted_at.is_(None),
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_group_by_code(self, db: AsyncSession, group_code: str) -> Optional[PropertyMasterGroup]:
        stmt = select(PropertyMasterGroup).where(
            PropertyMasterGroup.code == group_code.strip().upper(),
            PropertyMasterGroup.deleted_at.is_(None),
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()


master_repo = MasterRepository()
