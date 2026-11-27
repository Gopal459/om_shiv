"""API tests for the dynamic Franchise & Channel Partner Network endpoints."""

from __future__ import annotations

import os
import pytest

os.environ.setdefault("PYTEST_CURRENT_TEST", "true")
os.environ.setdefault("TESTING", "true")

from app.models.leads import Lead


class TestFranchiseAPI:
    """Tests for /v1/franchise/* dynamic endpoints."""

    @pytest.mark.asyncio
    async def test_overview_starts_clean_and_reflects_live_mutations(self, test_client, db_session):
        # 1. Seed a real partner-sourced lead in CRM
        lead = Lead(
            lead_id="OB-2026-PARTNER1",
            full_name="Partner Referred Buyer",
            mobile="919829099999",
            source="Referral / Channel Partner",
            stage="CONVERTED",
        )
        db_session.add(lead)
        await db_session.commit()

        # 2. Create a Franchise Outlet
        out_res = await test_client.post(
            "/v1/franchise/outlets",
            json={
                "name": "Vaishali Nagar Branch",
                "city": "Jaipur",
                "locality": "Vaishali Nagar",
                "manager_name": "Vikram Rathore",
                "manager_mobile": "9829011122",
            },
        )
        assert out_res.status_code == 201
        outlet = out_res.json()
        assert outlet["outlet_code"].startswith("OUT-")

        # 3. Register a Channel Partner linked to that outlet
        cp_res = await test_client.post(
            "/v1/franchise/partners",
            json={
                "full_name": "Suresh Jain",
                "company_name": "PinkCity Realty",
                "mobile": "9829055566",
                "city": "Jaipur",
                "rera_number": "RAJ/A/2026/001",
                "outlet_id": outlet["id"],
                "commission_pct": 2.5,
            },
        )
        assert cp_res.status_code == 201
        partner = cp_res.json()
        assert partner["partner_code"].startswith("CP-")
        assert partner["outlet_name"] == "Vaishali Nagar Branch"

        # 4. Create and Settle a Payout
        pay_res = await test_client.post(
            "/v1/franchise/payouts",
            json={
                "partner_id": partner["id"],
                "lead_id": "OB-2026-PARTNER1",
                "property_title": "Shyam Heights 3 BHK",
                "deal_amount": 7500000,
                "commission_amount": 187500,
                "status": "PENDING",
            },
        )
        assert pay_res.status_code == 201
        payout = pay_res.json()

        settle_res = await test_client.patch(
            f"/v1/franchise/payouts/{payout['id']}",
            json={"status": "SETTLED", "note": "NEFT cleared"},
        )
        assert settle_res.status_code == 200
        assert settle_res.json()["status"] == "SETTLED"

        # 5. Check Overview KPIs match exact DB state
        ov_res = await test_client.get("/v1/franchise/overview")
        assert ov_res.status_code == 200
        ov = ov_res.json()
        assert ov["channel_partners"]["active"] == 1
        assert ov["franchise_outlets"]["active"] == 1
        assert "Jaipur" in ov["franchise_outlets"]["cities"]
        assert ov["partner_sourced_leads"]["total"] == 1
        assert ov["partner_sourced_leads"]["converted"] == 1
        assert ov["settled_payouts"]["count"] == 1
        assert ov["settled_payouts"]["total_amount"] == 187500.0

        # 6. Toggle Partner Inactive -> updates active count
        tog_res = await test_client.patch(
            f"/v1/franchise/partners/{partner['id']}",
            json={"is_active": False},
        )
        assert tog_res.status_code == 200
        assert tog_res.json()["is_active"] is False

        ov2 = (await test_client.get("/v1/franchise/overview")).json()
        assert ov2["channel_partners"]["active"] == 0
        assert ov2["channel_partners"]["total"] == 1

        # 7. Partner-sourced leads list
        leads_res = await test_client.get("/v1/franchise/leads")
        assert leads_res.status_code == 200
        assert len(leads_res.json()["leads"]) == 1
        assert leads_res.json()["leads"][0]["lead_id"] == "OB-2026-PARTNER1"
