from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.session import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic Base Repository providing foundational CRUD and soft-delete operations."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """Fetch active record by primary key (soft-deleted records excluded)."""
        stmt = select(self.model).where(self.model.id == id)
        if hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_all(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> List[ModelType]:
        """Fetch list of records with pagination."""
        stmt = select(self.model)
        if hasattr(self.model, "deleted_at") and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        stmt = stmt.offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def create(self, db: AsyncSession, obj_in: ModelType) -> ModelType:
        """Persist a new entity instance to the database."""
        db.add(obj_in)
        await db.commit()
        await db.refresh(obj_in)
        return obj_in

    async def update(self, db: AsyncSession, db_obj: ModelType) -> ModelType:
        """Commit modified entity instance."""
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def soft_delete(self, db: AsyncSession, db_obj: ModelType) -> ModelType:
        """Apply soft delete timestamp and deactivate entity."""
        if hasattr(db_obj, "deleted_at"):
            setattr(db_obj, "deleted_at", datetime.now(timezone.utc))
        if hasattr(db_obj, "is_active"):
            setattr(db_obj, "is_active", False)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def restore(self, db: AsyncSession, db_obj: ModelType) -> ModelType:
        """Clear soft delete timestamp and reactivate entity."""
        if hasattr(db_obj, "deleted_at"):
            setattr(db_obj, "deleted_at", None)
        if hasattr(db_obj, "is_active"):
            setattr(db_obj, "is_active", True)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def count(self, db: AsyncSession, include_deleted: bool = False) -> int:
        """Count total records."""
        stmt = select(func.count(self.model.id))
        if hasattr(self.model, "deleted_at") and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        res = await db.execute(stmt)
        return res.scalar() or 0
