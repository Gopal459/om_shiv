from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.properties import Property
from app.repositories.base import BaseRepository


class PropertyRepository(BaseRepository[Property]):
    def __init__(self):
        super().__init__(Property)

    async def get_by_id_or_code(self, db: AsyncSession, identifier: str) -> Optional[Property]:
        stmt = select(Property).where(
            or_(
                Property.property_id == identifier,
                Property.id == (int(identifier) if identifier.isdigit() else -1),
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_recycled(self, db: AsyncSession) -> List[Property]:
        stmt = (
            select(Property)
            .where(Property.is_recycled.is_(True))
            .order_by(Property.recycled_at.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


property_repo = PropertyRepository()
