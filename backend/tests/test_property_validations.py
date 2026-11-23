import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.property_master_service import seed_property_masters


@pytest.mark.asyncio
async def test_carpet_area_must_be_less_than_super_area(test_client: AsyncClient, db_session: AsyncSession):
    await seed_property_masters(db_session)

    # Carpet >= Super Area must fail with 422
    payload = {
        "listing_type": 2,  # Sale
        "category_code": 1,  # Residential
        "sub_category_code": 1,  # Flat
        "title": "Luxury 3BHK Flat",
        "description": "Spacious flat near city center",
        "pincode": "301001",
        "city": "Alwar",
        "locality": "Sector 5",
        "latitude": 27.5530,
        "longitude": 76.6346,
        "expected_price": 4500000,
        "owner_name": "Rajesh Kumar",
        "owner_mobile": "9829012345",
        "posted_by_role": "OWNER",
        "flat_details": {
            "bhk": 3,
            "rooms": 3,
            "bathrooms": 2,
            "balconies": 2,
            "total_floors": 10,
            "property_floor": 4,
            "super_area": 1200,
            "carpet_area": 1300,  # INVALID: Carpet > Super
        },
    }
    response = await test_client.post("/v1/properties/post", json=payload)
    assert response.status_code == 422
    assert "Carpet area must be less than super area" in response.text


@pytest.mark.asyncio
async def test_room_count_must_equal_bhk(test_client: AsyncClient, db_session: AsyncSession):
    await seed_property_masters(db_session)

    payload = {
        "listing_type": 2,
        "category_code": 1,
        "sub_category_code": 1,
        "title": "3BHK Flat",
        "pincode": "301001",
        "city": "Alwar",
        "locality": "Sector 5",
        "latitude": 27.5530,
        "longitude": 76.6346,
        "expected_price": 4500000,
        "owner_name": "Rajesh Kumar",
        "owner_mobile": "9829012345",
        "flat_details": {
            "bhk": 3,
            "rooms": 4,  # INVALID: rooms != bhk
            "bathrooms": 2,
            "total_floors": 10,
            "property_floor": 4,
            "super_area": 1500,
            "carpet_area": 1100,
        },
    }
    response = await test_client.post("/v1/properties/post", json=payload)
    assert response.status_code == 422
    assert "Room count must equal BHK" in response.text


@pytest.mark.asyncio
async def test_property_floor_cannot_exceed_total_floors(test_client: AsyncClient, db_session: AsyncSession):
    await seed_property_masters(db_session)

    payload = {
        "listing_type": 2,
        "category_code": 1,
        "sub_category_code": 1,
        "title": "3BHK Flat",
        "pincode": "301001",
        "city": "Alwar",
        "locality": "Sector 5",
        "latitude": 27.5530,
        "longitude": 76.6346,
        "expected_price": 4500000,
        "owner_name": "Rajesh Kumar",
        "owner_mobile": "9829012345",
        "flat_details": {
            "bhk": 3,
            "rooms": 3,
            "bathrooms": 2,
            "total_floors": 5,
            "property_floor": 8,  # INVALID: Floor > Total
            "super_area": 1500,
            "carpet_area": 1100,
        },
    }
    response = await test_client.post("/v1/properties/post", json=payload)
    assert response.status_code == 422
    assert "Property floor cannot exceed total floors" in response.text


@pytest.mark.asyncio
async def test_valid_property_post_generates_5digit_sequence(test_client: AsyncClient, db_session: AsyncSession):
    await seed_property_masters(db_session)

    payload = {
        "listing_type": 2,
        "category_code": 1,
        "sub_category_code": 1,
        "title": "Valid Luxury 3BHK Flat",
        "description": "Beautiful garden facing apartment",
        "pincode": "301001",
        "city": "Alwar",
        "locality": "Sector 5",
        "latitude": 27.5530,
        "longitude": 76.6346,
        "expected_price": 4500000,
        "owner_name": "Rajesh Kumar",
        "owner_mobile": "9829012345",
        "posted_by_role": "OWNER",
        "flat_details": {
            "bhk": 3,
            "rooms": 3,
            "bathrooms": 2,
            "balconies": 2,
            "total_floors": 10,
            "property_floor": 4,
            "super_area": 1500,
            "carpet_area": 1100,
        },
    }
    response = await test_client.post("/v1/properties/post", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "property_id" in data
    # Format: OP-YYYY-NNNNN (5 digits zero-padded)
    parts = data["property_id"].split("-")
    assert len(parts) == 3
    assert parts[0] == "OP"
    assert len(parts[2]) == 5
    assert data["verified_status"] == 0
    assert data["is_live"] is False


@pytest.mark.asyncio
async def test_quick_listing_flow(test_client: AsyncClient, db_session: AsyncSession):
    await seed_property_masters(db_session)

    payload = {
        "title": "Quick Post Villa",
        "listing_type": 2,
        "category_code": 1,
        "sub_category_code": 2,
        "expected_price": 7500000,
        "pincode": "301001",
        "owner_name": "Suresh Patel",
        "owner_mobile": "9829077777",
    }
    response = await test_client.post("/v1/properties/quick-listing", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["property_id"].startswith("OP-")
    assert data["source"] == "QUICK_LISTING"
    assert data["verified_status"] == 0
