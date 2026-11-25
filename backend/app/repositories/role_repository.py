from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func
from app.models.identity import Role, Employee
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self):
        super().__init__(Role)

    async def get_by_code(self, db: AsyncSession, code: str, include_deleted: bool = False) -> Optional[Role]:
        stmt = (
            select(Role)
            .options(selectinload(Role.department), selectinload(Role.employees))
            .where(Role.code == code.strip().upper())
        )
        if not include_deleted:
            stmt = stmt.where(Role.deleted_at.is_(None))
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_active_with_counts(self, db: AsyncSession) -> List[Dict[str, Any]]:
        # Query non-deleted roles
        stmt = (
            select(Role)
            .options(selectinload(Role.department))
            .where(Role.deleted_at.is_(None))
            .order_by(Role.id.asc())
        )
        res = await db.execute(stmt)
        roles = res.scalars().all()

        # Query active counts
        count_stmt = (
            select(Employee.role_id, func.count(Employee.id))
            .where(Employee.deleted_at.is_(None), Employee.is_active.is_(True))
            .group_by(Employee.role_id)
        )
        count_res = await db.execute(count_stmt)
        count_map = {row[0]: row[1] for row in count_res.all()}

        output = []
        for r in roles:
            output.append({
                "role": r,
                "employee_count": count_map.get(r.id, 0),
            })
        return output

    async def get_assigned_active_employees(self, db: AsyncSession, role_id: int) -> List[str]:
        stmt = select(Employee.employee_id).where(
            Employee.role_id == role_id,
            Employee.deleted_at.is_(None),
            Employee.is_active.is_(True),
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


role_repo = RoleRepository()
