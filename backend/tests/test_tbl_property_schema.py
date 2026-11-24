import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.db.migrations.runner import run_all_migrations


@pytest.mark.asyncio
async def test_tbl_property_and_tbl_payingguest_tables_exist(db_session: AsyncSession):
    """Verify that tbl_property (124 columns) and tbl_payingguest exist in the database."""
    # Check tbl_property exists
    result = await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='tbl_property'")
    )
    row = result.fetchone()
    assert row is not None, "tbl_property table should exist"

    # Check tbl_payingguest exists
    result_pg = await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='tbl_payingguest'")
    )
    row_pg = result_pg.fetchone()
    assert row_pg is not None, "tbl_payingguest table should exist"

    # Verify columns in tbl_property
    cols_res = await db_session.execute(text("PRAGMA table_info(tbl_property)"))
    cols = {r[1] for r in cols_res.fetchall()}
    required_cols = [
        "property_id",
        "propertyid_no",
        "property_type",
        "looking_type",
        "looking_subcat_type",
        "state_id",
        "city_id",
        "location_lat",
        "location_long",
        "expected_price",
        "price_negociable",
        "carpet_area",
        "super_area",
        "noof_bhk",
        "verified_status",
        "is_active",
        "sold_status",
        "recyclebin_status",
        "assigned_user_id",
        "live_request_sent",
        "source_owner_name",
        "source_owner_mobile",
    ]
    for col in required_cols:
        assert col in cols, f"Column '{col}' must exist in tbl_property"


@pytest.mark.asyncio
async def test_migration_0006_applies_cleanly():
    """Verify that migration 0006 runs cleanly on an engine and creates tbl_property and tbl_payingguest."""
    import importlib
    mig_0006 = importlib.import_module("app.db.migrations.0006_tbl_property_schema")
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    await mig_0006.upgrade(test_engine)

    async with test_engine.connect() as conn:
        # Verify tbl_property exists
        t_res = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='tbl_property'"))
        assert t_res.scalar_one_or_none() == "tbl_property"

        # Verify tbl_payingguest exists
        pg_res = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='tbl_payingguest'"))
        assert pg_res.scalar_one_or_none() == "tbl_payingguest"

    await test_engine.dispose()
