import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.property_master import PropertyMasterGroup, PropertyMasterOption, PincodeMaster
from app.services.property_master_service import seed_property_masters


@pytest.mark.asyncio
async def test_dynamic_schema_returns_scoped_options(test_client: AsyncClient, db_session: AsyncSession):
    await seed_property_masters(db_session)

    response = await test_client.get("/v1/public/property-schema")

    assert response.status_code == 200
    schema = response.json()

    assert "FACING" in schema
    assert "AREA_UNITS" in schema
    assert "AMENITIES" in schema
    assert "FLOORING" in schema
    assert "POSSESSION_STATUS" in schema

    # Verify Bigha is scoped specifically to Agriculture (category 3)
    bigha = next((o for o in schema["AREA_UNITS"] if o["label"] == "Bigha"), None)
    assert bigha is not None
    assert bigha["applicable_categories"] == [3]

    # Verify Sq.ft is universal
    sqft = next((o for o in schema["AREA_UNITS"] if o["label"] == "Sq.ft"), None)
    assert sqft is not None
    assert sqft["applicable_categories"] == []


@pytest.mark.asyncio
async def test_admin_create_property_master_option(test_client: AsyncClient, db_session: AsyncSession):
    await seed_property_masters(db_session)

    payload = {
        "group_code": "FACING",
        "code": "NORTH_NORTH_EAST",
        "label": "North-North-East",
        "display_order": 99,
        "applicable_categories": [],
    }
    create_resp = await test_client.post("/v1/admin/property-master/options", json=payload)
    assert create_resp.status_code == 201

    # Check that it appears in public schema
    schema_resp = await test_client.get("/v1/public/property-schema")
    assert schema_resp.status_code == 200
    facing_options = schema_resp.json()["FACING"]
    assert any(o["code"] == "NORTH_NORTH_EAST" for o in facing_options)


@pytest.mark.asyncio
async def test_pincode_validation_and_lookup(test_client: AsyncClient, db_session: AsyncSession):
    await seed_property_masters(db_session)

    # Existing serviceable pincode
    resp_valid = await test_client.get("/v1/public/pincodes/301001")
    assert resp_valid.status_code == 200
    data = resp_valid.json()
    assert data["pincode"] == "301001"
    assert data["city"] == "Alwar"
    assert data["state"] == "Rajasthan"
    assert data["is_serviceable"] is True

    # Non-existent pincode
    resp_invalid = await test_client.get("/v1/public/pincodes/999999")
    assert resp_invalid.status_code == 404
