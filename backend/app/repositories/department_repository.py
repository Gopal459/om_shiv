from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.identity import Department
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    def __init__(self):
        super().__init__(Department)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Department]:
        stmt = select(Department).where(
            Department.code == code.strip().upper(),
            Department.deleted_at.is_(None),
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_active(self, db: AsyncSession) -> List[Department]:
        stmt = (
            select(Department)
            .where(Department.deleted_at.is_(None))
            .order_by(Department.name.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


department_repo = DepartmentRepository()
