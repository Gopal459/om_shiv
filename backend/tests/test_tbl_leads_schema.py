import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_tbl_leads_table_has_all_54_columns(db_session: AsyncSession):
    res = await db_session.execute(text("PRAGMA table_info(tbl_leads)"))
    cols = {row[1] for row in res.fetchall()}
    assert "leads_id" in cols
    assert "contact_name" in cols
    assert "mobile" in cols
    assert "dealer_have" in cols
    assert "lead_status" in cols
    assert "stage" in cols
    assert "rating" in cols
    assert "lead_table_name" in cols
    assert "deleted_at" in cols
