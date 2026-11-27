"""Comprehensive API tests for the 4-Tier Channel Partner governance engine."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
import pytest

os.environ.setdefault("PYTEST_CURRENT_TEST", "true")
os.environ.setdefault("TESTING", "true")

from app.models.leads import Lead
from app.models.properties import Property
from app.models.property_master import PincodeMaster


class Test4TierChannelPartnerGovernance:
    """Validates Broker CP, Active CP (L1/L2/L3 + kill switch), Referral Partner, and Creator Partner rules."""

    @pytest.mark.asyncio
    async def test_active_cp_ladder_owner_masking_and_instant_suspend(self, auth_client_md, db_session):
        # Seed a live verified property with real owner mobile & name
        db_session.add(PincodeMaster(pincode="302021", city="Jaipur", district="Jaipur", state="Rajasthan", is_serviceable=True))
        await db_session.flush()
        prop = Property(
            property_id="OP-2026-TEST01",
            listing_type=2,
            category_code=1,
            sub_category_code=1,
            title="Shyam Heights 3 BHK",
            pincode="302021",
            city="Jaipur",
            locality="Vaishali Nagar",
            expected_price=7500000,
            owner_name="Secret Owner Sharma",
            owner_mobile="9829098765",
            is_live=True,
            verified_status=1,
        )
        db_session.add(prop)
        await db_session.commit()

        # 1. Onboard an Active CP with 35 days tenure (starts at L1)
        joined_35d_ago = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        res_cp = await auth_client_md.post(
            "/v1/franchise/partners",
            json={
                "cp_type": "ACTIVE_CP",
                "full_name": "Ravi Active CP",
                "mobile": "9829012340",
                "city": "Jaipur",
                "joined_at": joined_35d_ago,
            },
        )
        assert res_cp.status_code == 201
        cp = res_cp.json()
        assert cp["active_level"] == "L1"

        # 2. L1 Inventory MUST be locked
        inv_l1 = await auth_client_md.get(f"/v1/franchise/partners/{cp['id']}/inventory")
        assert inv_l1.status_code == 200
        assert inv_l1.json()["access_level"] == "LOCKED_L1"
        assert inv_l1.json()["items"] == []
        assert inv_l1.json()["requires_accompanied_visit"] is True

        # 3. Promote to L2 BEFORE certification -> MUST FAIL (422)
        fail_prom = await auth_client_md.patch(
            f"/v1/franchise/partners/{cp['id']}/promote",
            json={"target_level": "L2", "manager_emp_id": "EMP-0001"},
        )
        assert fail_prom.status_code == 422

        # 4. Certify then promote to L2 -> SUCCEEDS
        cert_res = await auth_client_md.post(f"/v1/franchise/partners/{cp['id']}/certify")
        assert cert_res.status_code == 200
        assert cert_res.json()["is_certified"] is True

        ok_prom = await auth_client_md.patch(
            f"/v1/franchise/partners/{cp['id']}/promote",
            json={"target_level": "L2", "manager_emp_id": "EMP-0001"},
        )
        assert ok_prom.status_code == 200
        assert ok_prom.json()["active_level"] == "L2"

        # 5. L2 Inventory shows property address/locality BUT MUST MASK owner name & phone
        inv_l2 = await auth_client_md.get(f"/v1/franchise/partners/{cp['id']}/inventory")
        assert inv_l2.status_code == 200
        l2_data = inv_l2.json()
        assert l2_data["can_view_address"] is True
        assert l2_data["can_view_owner_contact"] is False
        assert len(l2_data["items"]) == 1
        assert l2_data["items"][0]["owner_mobile"] is None
        assert l2_data["items"][0]["owner_name"] == "Omshiv Managed"

        # 6. L3 Mediated Meeting blocked at L2
        mtg_fail = await auth_client_md.post(
            "/v1/franchise/meetings",
            json={
                "partner_id": cp["id"],
                "property_id": "OP-2026-TEST01",
                "requested_slot": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert mtg_fail.status_code == 403

        # 7. Instant Suspend -> immediately blocks inventory (403 Forbidden)
        susp_res = await auth_client_md.post(
            f"/v1/franchise/partners/{cp['id']}/suspend",
            json={"reason": "Attempted bypassing Omshiv to contact owner directly"},
        )
        assert susp_res.status_code == 200
        assert susp_res.json()["is_active"] is False
        assert susp_res.json()["clean_record"] is False

        inv_blocked = await auth_client_md.get(f"/v1/franchise/partners/{cp['id']}/inventory")
        assert inv_blocked.status_code == 403

    @pytest.mark.asyncio
    async def test_referral_partner_registry_only_and_annual_limit(self, test_client, db_session):
        # Create a Referral Partner with ₹7,500 fixed reward & annual limit = 1
        res_ref = await test_client.post(
            "/v1/franchise/partners",
            json={
                "cp_type": "REFERRAL_PARTNER",
                "full_name": "Neha Salaried Referrer",
                "mobile": "9829077700",
                "city": "Jaipur",
                "fixed_reward_amount": 7500,
                "annual_reward_limit": 1,
            },
        )
        assert res_ref.status_code == 201
        ref_cp = res_ref.json()

        # Lead 1 still NEW (not registered yet) -> Payout MUST FAIL (422)
        db_session.add(
            Lead(
                lead_id="OB-2026-REF1",
                full_name="Lead Unregistered",
                mobile="919829010001",
                source="Partner Referral",
                stage="NEW",
            )
        )
        # Lead 2 CONVERTED (registered)
        db_session.add(
            Lead(
                lead_id="OB-2026-REF2",
                full_name="Lead Registered",
                mobile="919829010002",
                source="Partner Referral",
                stage="CONVERTED",
            )
        )
        # Lead 3 also CONVERTED (will exceed annual cap of 1)
        db_session.add(
            Lead(
                lead_id="OB-2026-REF3",
                full_name="Lead Cap Exceeded",
                mobile="919829010003",
                source="Partner Referral",
                stage="CONVERTED",
            )
        )
        await db_session.commit()

        bad_pay = await test_client.post(
            "/v1/franchise/payouts",
            json={"partner_id": ref_cp["id"], "lead_id": "OB-2026-REF1"},
        )
        assert bad_pay.status_code == 422

        # Reward #1 on registered lead -> SUCCEEDS using fixed_reward_amount
        ok_pay = await test_client.post(
            "/v1/franchise/payouts",
            json={"partner_id": ref_cp["id"], "lead_id": "OB-2026-REF2"},
        )
        assert ok_pay.status_code == 201
        assert ok_pay.json()["payout_type"] == "REFERRAL_FIXED"
        assert ok_pay.json()["commission_amount"] == 7500.0

        # Reward #2 in same FY -> BLOCKED by annual limit (422)
        cap_pay = await test_client.post(
            "/v1/franchise/payouts",
            json={"partner_id": ref_cp["id"], "lead_id": "OB-2026-REF3"},
        )
        assert cap_pay.status_code == 422

    @pytest.mark.asyncio
    async def test_creator_partner_link_attribution_and_retainer(self, test_client):
        res_cr = await test_client.post(
            "/v1/franchise/partners",
            json={
                "cp_type": "CREATOR_PARTNER",
                "full_name": "Rohit Reels Influencer",
                "mobile": "9829088800",
                "city": "Jaipur",
                "tracking_code": "ROHIT26",
                "social_handle": "@rohit_jaipur_homes",
                "is_top_creator": True,
                "monthly_retainer_amount": 25000,
            },
        )
        assert res_cr.status_code == 201

        # Submit inbound lead via /v1/intake/lead with referral_code="ROHIT26"
        intake_res = await test_client.post(
            "/v1/intake/lead",
            json={
                "source": "Creator Link",
                "full_name": "Instagram Follower Buyer",
                "mobile": "9829099111",
                "referral_code": "ROHIT26",
            },
        )
        assert intake_res.status_code == 201

        # Verify Creator shows tracked_leads_count == 1
        list_res = await test_client.get("/v1/franchise/partners?cp_type=CREATOR_PARTNER")
        assert list_res.status_code == 200
        creator = list_res.json()["partners"][0]
        assert creator["tracked_leads_count"] == 1

        # Generate monthly retainers (idempotent)
        ret1 = await test_client.post("/v1/franchise/payouts/generate-retainers")
        assert ret1.status_code == 200
        assert ret1.json()["generated_count"] == 1

        ret2 = await test_client.post("/v1/franchise/payouts/generate-retainers")
        assert ret2.status_code == 200
        assert ret2.json()["generated_count"] == 0
        assert ret2.json()["skipped_existing"] == 1
