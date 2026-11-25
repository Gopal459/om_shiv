from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, or_, func
from app.models.identity import Employee
from app.repositories.base import BaseRepository


class StaffRepository(BaseRepository[Employee]):
    def __init__(self):
        super().__init__(Employee)

    async def get_by_emp_id(self, db: AsyncSession, emp_id: str) -> Optional[Employee]:
        stmt = (
            select(Employee)
            .options(selectinload(Employee.department), selectinload(Employee.role))
            .where(Employee.employee_id == emp_id.strip(), Employee.deleted_at.is_(None))
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_username_or_email(self, db: AsyncSession, identifier: str) -> Optional[Employee]:
        query_lower = identifier.strip().lower()
        stmt = (
            select(Employee)
            .options(selectinload(Employee.department), selectinload(Employee.role))
            .where(
                Employee.deleted_at.is_(None),
                or_(
                    func.lower(Employee.username) == query_lower,
                    func.lower(Employee.email) == query_lower,
                    Employee.employee_id == identifier.strip().upper(),
                ),
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def check_duplicate(
        self,
        db: AsyncSession,
        username: str,
        mobile: str,
        email: Optional[str] = None,
    ) -> Optional[Employee]:
        conditions = [
            func.lower(Employee.username) == username.strip().lower(),
            Employee.mobile == mobile.strip(),
        ]
        if email and email.strip():
            conditions.append(func.lower(Employee.email) == email.strip().lower())

        stmt = select(Employee).where(Employee.deleted_at.is_(None), or_(*conditions))
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_active(self, db: AsyncSession) -> List[Employee]:
        stmt = (
            select(Employee)
            .options(selectinload(Employee.department), selectinload(Employee.role))
            .where(Employee.deleted_at.is_(None))
            .order_by(Employee.id.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def generate_emp_id(self, db: AsyncSession) -> str:
        stmt = select(func.count(Employee.id))
        res = await db.execute(stmt)
        count = res.scalar() or 0
        return f"EMP-{count + 1:04d}"


staff_repo = StaffRepository()
