"""Backward-compatibility wrapper for database session and engine."""
from app.db.session import (
    engine,
    Base,
    AsyncSessionLocal,
    get_db,
    DATABASE_URL,
)

__all__ = [
    "engine",
    "Base",
    "AsyncSessionLocal",
    "get_db",
    "DATABASE_URL",
]
