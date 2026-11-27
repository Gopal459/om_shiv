import logging
import importlib
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

MIGRATION_STEPS = [
    "app.db.migrations.0001_initial_schema",
    "app.db.migrations.0002_soft_delete_columns",
    "app.db.migrations.0003_seed_identity_and_roles",
    "app.db.migrations.0004_seed_property_masters",
    "app.db.migrations.0005_tbl_leads_schema",
    "app.db.migrations.0006_tbl_property_schema",
    "app.db.migrations.0007_tbl_property_amenities_column",
    "app.db.migrations.0008_tbl_blog_schema",
    "app.db.migrations.0009_ai_agents_safety_schema",
    "app.db.migrations.0010_franchise_network_schema",
]


async def run_all_migrations(engine: AsyncEngine) -> None:
    """Executes all pending database migrations in sequence, recording applied migrations."""
    # 1. Ensure schema_migrations ledger table exists
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(100) PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL
                )
                """
            )
        )

    # 2. Get list of already applied migrations
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT version FROM schema_migrations"))
        applied_versions = {row[0] for row in res.fetchall()}

    # 3. Apply pending migrations
    for module_path in MIGRATION_STEPS:
        version_name = module_path.split(".")[-1]
        if version_name in applied_versions:
            continue

        logger.info(f"Applying database migration: {version_name}")
        mod = importlib.import_module(module_path)

        # Run migration upgrade function
        if hasattr(mod, "upgrade"):
            if hasattr(mod, "requires_session") and mod.requires_session:
                async with AsyncSessionLocal() as session:
                    await mod.upgrade(session)
            else:
                await mod.upgrade(engine)

        # Record as applied
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO schema_migrations (version, applied_at) VALUES (:ver, :at)"),
                {"ver": version_name, "at": datetime.now(timezone.utc)},
            )
        logger.info(f"Migration {version_name} applied successfully.")
