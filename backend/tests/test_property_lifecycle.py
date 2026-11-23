import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.properties import Property
from app.services.property_master_service import seed_property_masters
from app.services.property_service import generate_property_id
from app.workers.property_expiry_worker import process_property_expiries


@pytest.fixture
async def live_property(db_session: AsyncSession) -> Property:
    await seed_property_masters(db_session)
    prop_id = await generate_property_id(db_session)
    now = datetime.now(timezone.utc)
    prop = Property(
        property_id=prop_id,
        listing_type=2,  # Sale
        category_code=1,
        sub_category_code=1,
        title="Live Test Property",
        pincode="301001",
        city="Alwar",
        expected_price=5000000,
        owner_name="Owner Ram",
        owner_mobile="9829012345",
        verified_status=1,
        is_live=True,
        is_recycled=False,
        expires_at=now + timedelta(days=90),
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)
    return prop


@pytest.mark.asyncio
async def test_owner_request_single_pending_and_recycle_bin(
    test_client: AsyncClient,
    db_session: AsyncSession,
    live_property: Property,
):
    pid = live_property.property_id

    # 1. Owner sends delete request
    req1 = await test_client.post(
        f"/v1/owner/properties/{pid}/request-delete",
        json={"mobile": "9829012345", "reason": "No longer selling"},
    )
    assert req1.status_code == 200
    assert req1.json()["status"] == "PENDING"

    # 2. Second pending request must be rejected with 409 Conflict
    req2 = await test_client.post(
        f"/v1/owner/properties/{pid}/request-delete",
        json={"mobile": "9829012345", "reason": "Duplicate attempt"},
    )
    assert req2.status_code == 409
    assert "pending request already exists" in req2.text

    # 3. Admin approves deletion -> moves to Recycle Bin
    del_resp = await test_client.post(f"/v1/admin/properties/{pid}/approve-delete")
    assert del_resp.status_code == 200
    assert del_resp.json()["is_recycled"] is True
    assert del_resp.json()["is_live"] is False

    # 4. Admin 1-click restore from recycle bin -> returns to live portal
    restore_resp = await test_client.post(f"/v1/admin/properties/{pid}/recycle-bin-restore")
    assert restore_resp.status_code == 200
    assert restore_resp.json()["is_recycled"] is False
    assert restore_resp.json()["is_live"] is True


@pytest.mark.asyncio
async def test_auto_expiry_background_worker(db_session: AsyncSession):
    await seed_property_masters(db_session)
    now = datetime.now(timezone.utc)

    # Property expired 2 days ago
    prop_expired = Property(
        property_id="OP-2026-000888",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Expired Property",
        pincode="301001",
        city="Alwar",
        expected_price=4000000,
        owner_name="Expired Owner",
        owner_mobile="9829088888",
        verified_status=1,
        is_live=True,
        is_recycled=False,
        expires_at=now - timedelta(days=2),
    )
    # Property still active
    prop_active = Property(
        property_id="OP-2026-000889",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Active Property",
        pincode="301001",
        city="Alwar",
        expected_price=4000000,
        owner_name="Active Owner",
        owner_mobile="9829088889",
        verified_status=1,
        is_live=True,
        is_recycled=False,
        expires_at=now + timedelta(days=10),
    )
    db_session.add_all([prop_expired, prop_active])
    await db_session.commit()

    results = await process_property_expiries(db=db_session)
    assert results["expired_count"] >= 1

    await db_session.refresh(prop_expired)
    await db_session.refresh(prop_active)
    assert prop_expired.is_live is False
    assert prop_active.is_live is True
