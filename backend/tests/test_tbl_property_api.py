import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_sale_property_success(auth_client_md: AsyncClient):
    """Test creating a valid Sale property with strict rules."""
    payload = {
        "property_type": 2,  # Sale
        "looking_type": 1,   # Residential
        "looking_subcat_type": 1,  # Flat
        "source_type": 2,   # Owner
        "source_owner_name": "Ramesh Kumar",
        "source_owner_email": "ramesh@example.com",
        "source_owner_mobile": "9876543210",
        "state_id": 1,
        "city_id": 1,
        "sublocality_address": "Flat 302, Royal Residency, Alwar",
        "location": "Alwar Bypass Road",
        "pincode": "301001",
        "expected_price": 4500000.0,
        "price_negociable": 1,
        "transaction_type": 1,  # Resale
        "property_ownership": 2,  # Freehold
        "possession_status": 1,  # Ready
        "construction_age": "2 Years",
        "super_area": "1200",
        "carpet_area": "950",
        "noof_bhk": 2,
        "project_name": "Royal Residency",
        "featurepowerbackup": 1,
        "feature_watersupply": 1,
        "images": "[\"/uploads/prop1.jpg\"]",
    }
    resp = await auth_client_md.post("/v1/properties/create", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["property_id"] > 0
    assert "propertyid_no" in data
    assert data["property_type"] == 2
    assert float(data["expected_price"]) == 4500000.0


@pytest.mark.asyncio
async def test_create_sale_property_fails_carpet_ge_super(auth_client_md: AsyncClient):
    """Test carpet_area >= super_area fails with 422."""
    payload = {
        "property_type": 2,
        "looking_type": 1,
        "source_owner_name": "Ramesh Kumar",
        "source_owner_mobile": "9876543210",
        "state_id": 1,
        "city_id": 1,
        "expected_price": 5000000.0,
        "transaction_type": 1,
        "super_area": "1000",
        "carpet_area": "1200",  # Invalid: carpet >= super
    }
    resp = await auth_client_md.post("/v1/properties/create", json=payload)
    assert resp.status_code == 422
    assert "carpet_area must be strictly less than super_area" in resp.text


@pytest.mark.asyncio
async def test_create_rent_property_partial_floor_validation(auth_client_md: AsyncClient):
    """Test rent property with partial rent requires floor_torent."""
    payload = {
        "property_type": 1,  # Rent
        "looking_type": 1,
        "source_owner_name": "Suresh Sharma",
        "source_owner_mobile": "9876543211",
        "state_id": 1,
        "city_id": 1,
        "expected_price": 15000.0,
        "rentalallow_forid": "Family",
        "whichpart_torent": 2,  # Part
        "floor_torent": 0,      # Invalid when part
    }
    resp = await auth_client_md.post("/v1/properties/create", json=payload)
    assert resp.status_code == 422
    assert "floor_torent is required when renting part of property" in resp.text


@pytest.mark.asyncio
async def test_create_pg_property_food_validation(auth_client_md: AsyncClient):
    """Test PG property with food_option requires meal_type."""
    payload = {
        "property_type": 3,  # PG
        "looking_type": 1,
        "source_owner_name": "Sunil Verma",
        "source_owner_mobile": "9876543212",
        "state_id": 1,
        "city_id": 1,
        "expected_price": 7500.0,
        "pg_details": {
            "pg_name": "Shiv PG",
            "gender": 1,
            "room_type": 2,
            "food_option": 1,  # With Food
            "meal_type": "",   # Missing!
        }
    }
    resp = await auth_client_md.post("/v1/properties/create", json=payload)
    assert resp.status_code == 422
    assert "meal_type is required when food option is enabled" in resp.text


@pytest.mark.asyncio
async def test_properties_hub_and_status_update(auth_client_md: AsyncClient):
    """Test GET /v1/properties/hub and PATCH /v1/properties/tbl/{id}/status."""
    # 1. Create a fresh property
    payload = {
        "property_type": 2,
        "looking_type": 1,
        "source_owner_name": "Test Hub Owner",
        "source_owner_mobile": "9111122222",
        "state_id": 1,
        "city_id": 1,
        "expected_price": 3000000.0,
        "transaction_type": 1,
        "super_area": "1000",
        "carpet_area": "800",
    }
    create_resp = await auth_client_md.post("/v1/properties/create", json=payload)
    assert create_resp.status_code == 201
    prop_id = create_resp.json()["property_id"]

    # 2. Check in new_assign hub tab
    hub_resp = await auth_client_md.get("/v1/properties/hub?tab=new_assign")
    assert hub_resp.status_code == 200
    hub_data = hub_resp.json()
    assert any(p["property_id"] == prop_id for p in hub_data["items"])

    # 3. Update status (verify & live)
    status_resp = await auth_client_md.patch(
        f"/v1/properties/tbl/{prop_id}/status",
        json={"verified_status": 1, "is_active": 1}
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["verified_status"] == 1
    assert status_resp.json()["is_active"] == 1

    # 4. Check in verify_live hub tab
    live_hub = await auth_client_md.get("/v1/properties/hub?tab=verify_live")
    assert live_hub.status_code == 200
    assert any(p["property_id"] == prop_id for p in live_hub.json()["items"])


@pytest.mark.asyncio
async def test_upload_property_image_success(auth_client_md: AsyncClient):
    """Test uploading a valid property photo (15KB JPEG)."""
    # Create fake image payload: 15KB JPEG
    fake_img = b"\xff\xd8\xff" + b"A" * 15000 + b"\xff\xd9"
    files = {"file": ("test_living_room.jpg", fake_img, "image/jpeg")}
    
    resp = await auth_client_md.post("/v1/properties/upload-image", files=files)
    assert resp.status_code == 201
    data = resp.json()
    assert "url" in data
    assert data["url"].startswith("/uploads/properties/")
    assert data["size"] > 10000


@pytest.mark.asyncio
async def test_upload_property_image_rejects_under_10kb(auth_client_md: AsyncClient):
    """Test image smaller than 10KB is rejected with 400."""
    tiny_img = b"\xff\xd8\xff" + b"A" * 500  # ~500 bytes
    files = {"file": ("tiny.jpg", tiny_img, "image/jpeg")}
    resp = await auth_client_md.post("/v1/properties/upload-image", files=files)
    assert resp.status_code == 400
    assert "Minimum image size" in resp.text


@pytest.mark.asyncio
async def test_upload_property_image_rejects_invalid_format(auth_client_md: AsyncClient):
    """Test non-image file is rejected with 400."""
    fake_doc = b"Hello world text document" * 1000
    files = {"file": ("document.txt", fake_doc, "text/plain")}
    resp = await auth_client_md.post("/v1/properties/upload-image", files=files)
    assert resp.status_code == 400
    assert "Invalid image format" in resp.text

