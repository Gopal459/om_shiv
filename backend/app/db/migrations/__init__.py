"""Database migrations package executing sequential schema evolutions."""
from app.db.migrations.runner import run_all_migrations

__all__ = ["run_all_migrations"]
