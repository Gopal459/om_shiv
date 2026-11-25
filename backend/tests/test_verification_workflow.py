import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.properties import Property
from app.services.property_master_service import seed_property_masters
from app.services.property_service import generate_property_id


@pytest.fixture
async def unverified_property(db_session: AsyncSession) -> Property:
    await seed_property_masters(db_session)
    prop_id = await generate_property_id(db_session)
    prop = Property(
        property_id=prop_id,
        listing_type=2,  # Sale
        category_code=1,
        sub_category_code=1,
        title="Unverified Test Property",
        pincode="301001",
        city="Alwar",
        expected_price=5000000,
        owner_name="Test Owner",
        owner_mobile="9829011111",
        verified_status=0,
        is_live=False,
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)
    return prop


@pytest.mark.asyncio
async def test_property_verification_and_approval_flow(
    test_client: AsyncClient,
    db_session: AsyncSession,
    unverified_property: Property,
):
    pid = unverified_property.property_id

    # 1. Assign verifier
    assign_resp = await test_client.post(
        f"/v1/properties/{pid}/assign-verifier",
        json={"verifier_emp_id": "EMP-0005", "assigned_by": "EMP-0001"},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["status"] == "ASSIGNED"
    assert assign_resp.json()["assigned_to"] == "EMP-0005"

    # 2. Log telephonic verification call
    call_resp = await test_client.post(
        f"/v1/properties/{pid}/log-call",
        json={
            "caller_emp_id": "EMP-0005",
            "call_outcome": "AVAILABILITY_CONFIRMED",
            "notes": "Owner confirmed price and physical documents available",
            "confirmed_price": 5000000,
            "scheduled_visit_date": "2026-11-26T10:00:00Z",
        },
    )
    assert call_resp.status_code == 200
    assert call_resp.json()["call_outcome"] == "AVAILABILITY_CONFIRMED"

    # 3. Upload verification document
    doc_resp = await test_client.post(
        f"/v1/properties/{pid}/upload-document",
        json={
            "doc_type": "TITLE_DEED",
            "file_url": "https://storage.omshiv.com/docs/deed_123.pdf",
            "uploaded_by": "EMP-0005",
        },
    )
    assert doc_resp.status_code == 200
    assert doc_resp.json()["doc_type"] == "TITLE_DEED"

    # 4. Manager Verify & Approve -> sets verified_status = 1, is_live = True, and 90-day expiry
    approve_resp = await test_client.post(
        f"/v1/properties/{pid}/verify-and-approve",
        json={
            "area_confirmed": True,
            "photos_genuine_confirmed": True,
            "ownership_confirmed": True,
            "approver_emp_id": "EMP-0001",
        },
    )
    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["verified_status"] == 1
    assert data["is_live"] is True
    assert data["expires_at"] is not None
