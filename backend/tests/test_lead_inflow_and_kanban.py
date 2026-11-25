import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_manual_create_and_kanban_grouping(test_client: AsyncClient):
    # 1. Test manual creation
    resp = await test_client.post("/v1/leads/create", json={
        "contact_name": "Vikram Rathore",
        "mobile": "9829012345",
        "lead_type": "BUY",
        "lead_source_id": 1,
        "rating": 1,
        "indv_property_address": "Vaishali Nagar, Jaipur",
        "lead_remark": "Interested in 3 BHK Villa"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["contact_name"] == "Vikram Rathore"
    assert "lead_unique_id" in data
    lead_id = data["lead_unique_id"]

    # 2. Test kanban grouping
    kb_resp = await test_client.get("/v1/leads/kanban?type=buy")
    assert kb_resp.status_code == 200
    kb_data = kb_resp.json()
    assert "new" in kb_data
    assert "in_progress" in kb_data
    assert "site_visit" in kb_data
    assert "qualified" in kb_data
    assert "converted" in kb_data
    assert "disqualified" in kb_data
    assert any(l["contact_name"] == "Vikram Rathore" for l in kb_data["new"])

    # 3. Test stage transition
    patch_resp = await test_client.patch(f"/v1/leads/{lead_id}/stage", json={
        "lead_status": 1,
        "stage": 2,
        "remark": "Site visit planned for tomorrow"
    })
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["lead_status"] == 1
    assert updated["stage"] == 2

    # Verify moved to site_visit in kanban
    kb_resp2 = await test_client.get("/v1/leads/kanban?type=buy")
    kb_data2 = kb_resp2.json()
    assert any(l["contact_name"] == "Vikram Rathore" for l in kb_data2["site_visit"])


@pytest.mark.asyncio
async def test_bulk_csv_import(test_client: AsyncClient):
    csv_rows = [
        {"contact_name": "Anita Meena", "mobile": "9829011111", "lead_type": "RENT", "rating": 2},
        {"contact_name": "Sunil Sharma", "mobile": "9829022222", "lead_type": "PG", "rating": 3},
    ]
    resp = await test_client.post("/v1/leads/import-bulk", json={"leads": csv_rows})
    assert resp.status_code == 201
    res_data = resp.json()
    assert res_data["imported_count"] == 2
