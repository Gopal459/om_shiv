import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


@pytest.mark.asyncio
async def test_intake_sequence_and_24h_deduplication(test_client: AsyncClient):
    """Verify first lead creates 6-digit zero-padded sequence, repeat within 24h dedupes."""
    # First lead submission
    resp1 = await test_client.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "Ramesh Kumar",
        "mobile": "9829099999",
        "lead_type": "BUYER",
    })
    assert resp1.status_code == 201
    data1 = resp1.json()
    lead_id = data1["lead_id"]
    assert lead_id.startswith("OB-2026-")
    # Verify 6-digit zero-padded sequence
    seq_str = lead_id.split("-")[2]
    assert len(seq_str) == 6
    assert seq_str == "000001"
    assert data1["is_duplicate"] is False
    assert data1["mobile"] == "919829099999"

    # Repeat submission within 24h with same mobile -> deduplicated
    resp2 = await test_client.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "Ramesh Kumar",
        "mobile": "9829099999",
        "lead_type": "BUYER",
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["lead_id"] == lead_id
    assert data2["is_duplicate"] is True


@pytest.mark.asyncio
async def test_mobile_normalization_variants_trigger_dedup(test_client: AsyncClient):
    """Verify different phone formats (+91, leading 0, 10 digits) normalize and deduplicate."""
    resp1 = await test_client.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "Suresh Sharma",
        "mobile": "+91 98291 11111",
        "lead_type": "BUYER",
    })
    assert resp1.status_code == 201
    lead_id = resp1.json()["lead_id"]
    assert resp1.json()["mobile"] == "919829111111"

    # Repeat submission with leading zero: 09829111111
    resp2 = await test_client.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "Suresh Sharma",
        "mobile": "09829111111",
        "lead_type": "BUYER",
    })
    assert resp2.status_code == 200
    assert resp2.json()["lead_id"] == lead_id
    assert resp2.json()["is_duplicate"] is True


@pytest.mark.asyncio
async def test_test_number_suppression(test_client: AsyncClient, db_session: AsyncSession):
    """Verify numbers configured in test_numbers setting skip CRM lead creation."""
    from app.models.settings import SystemSetting

    # Seed test_numbers setting
    setting = SystemSetting(
        key="test_numbers",
        value=["919999999999", "910000000000"],
        data_type="JSON",
        category="ROUTING",
        description="Test mobile numbers suppressed from CRM",
    )
    db_session.add(setting)
    await db_session.commit()

    resp = await test_client.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "Test Account",
        "mobile": "9999999999",
        "lead_type": "BUYER",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["lead_id"] is None
    assert data["is_test"] is True
    assert data["status"] == "suppressed"


@pytest.mark.asyncio
async def test_website_inquiry_and_1_click_conversion(test_client: AsyncClient, db_session: AsyncSession):
    """Verify website inquiry submission, listing unconverted, and 1-click lead conversion."""
    # 1. Public website inquiry submission
    resp_inq = await test_client.post("/v1/intake/inquiry", json={
        "inquiry_type": "CALLBACK",
        "full_name": "Pooja Verma",
        "mobile": "9829022222",
        "email": "pooja@example.com",
        "details": {"preferred_time": "18:00 - 19:00", "property_interest": "3BHK Flat"},
    })
    assert resp_inq.status_code == 201
    inquiry_id = resp_inq.json()["id"]
    assert resp_inq.json()["is_converted"] is False

    # 2. List un-converted inquiries
    resp_list = await test_client.get("/v1/crm/inquiries")
    assert resp_list.status_code == 200
    inquiries = resp_list.json()
    assert any(inq["id"] == inquiry_id for inq in inquiries)

    # 3. 1-Click Conversion to Lead
    resp_convert = await test_client.post(
        f"/v1/crm/inquiries/{inquiry_id}/convert-to-lead",
        json={"assigned_to": "EMP-0001", "lead_type": "BUYER"}
    )
    assert resp_convert.status_code == 200
    converted_data = resp_convert.json()
    lead_id = converted_data["lead_id"]
    assert lead_id.startswith("OB-2026-")
    assert converted_data["full_name"] == "Pooja Verma"
    assert converted_data["mobile"] == "919829022222"
    assert converted_data["assigned_to"] == "EMP-0001"
    assert converted_data["is_untouched"] is True

    # 4. Verify inquiry is now marked as converted
    resp_list_after = await test_client.get("/v1/crm/inquiries")
    assert resp_list_after.status_code == 200
    inquiries_after = resp_list_after.json()
    assert not any(inq["id"] == inquiry_id for inq in inquiries_after)


@pytest.mark.asyncio
async def test_idempotency_key_avoids_duplicate_lead(test_client: AsyncClient):
    """Verify submitting with same idempotency_key returns identical lead without duplicate."""
    idem_key = "webhook-delivery-unique-12345"

    resp1 = await test_client.post("/v1/intake/lead", json={
        "source": "META_ADS",
        "full_name": "Amit Saxena",
        "mobile": "9829033333",
        "lead_type": "BUYER",
        "idempotency_key": idem_key,
    })
    assert resp1.status_code == 201
    lead_id_1 = resp1.json()["lead_id"]

    resp2 = await test_client.post("/v1/intake/lead", json={
        "source": "META_ADS",
        "full_name": "Amit Saxena",
        "mobile": "9829033333",
        "lead_type": "BUYER",
        "idempotency_key": idem_key,
    })
    assert resp2.status_code == 200
    assert resp2.json()["lead_id"] == lead_id_1


@pytest.mark.asyncio
async def test_convert_inquiry_edge_cases(test_client: AsyncClient):
    """Verify 404 on non-existent inquiry and 400 when converting an already converted inquiry."""
    # 404 for non-existent inquiry
    resp = await test_client.post(
        "/v1/crm/inquiries/99999/convert-to-lead",
        json={"assigned_to": "EMP-0001", "lead_type": "BUYER"}
    )
    assert resp.status_code == 404

    # Create inquiry and convert it
    resp_inq = await test_client.post("/v1/intake/inquiry", json={
        "inquiry_type": "PROBLEM_REPORT",
        "full_name": "Test User",
        "mobile": "9829044444",
        "details": {"issue": "Website form error"},
    })
    inquiry_id = resp_inq.json()["id"]

    resp_conv1 = await test_client.post(
        f"/v1/crm/inquiries/{inquiry_id}/convert-to-lead",
        json={"assigned_to": "EMP-0001"}
    )
    assert resp_conv1.status_code == 200

    # Converting again should return 400
    resp_conv2 = await test_client.post(
        f"/v1/crm/inquiries/{inquiry_id}/convert-to-lead",
        json={"assigned_to": "EMP-0001"}
    )
    assert resp_conv2.status_code == 400


@pytest.mark.asyncio
async def test_sequential_lead_id_generation(test_client: AsyncClient):
    """Verify distinct leads receive monotonically incremented 6-digit sequence IDs."""
    resp1 = await test_client.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "User One",
        "mobile": "9829050001",
        "lead_type": "BUYER",
    })
    resp2 = await test_client.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "User Two",
        "mobile": "9829050002",
        "lead_type": "BUYER",
    })

    assert resp1.status_code == 201
    assert resp2.status_code == 201

    id1 = resp1.json()["lead_id"]
    id2 = resp2.json()["lead_id"]

    seq1 = int(id1.split("-")[2])
    seq2 = int(id2.split("-")[2])
    assert seq2 == seq1 + 1
