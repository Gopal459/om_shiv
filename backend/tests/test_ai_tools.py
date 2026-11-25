import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.tools import AIToolRegistry
from app.models.leads import Lead, LeadActivity
from app.models.ai_agents import AIApprovalQueue
from app.models.properties import Property, PropResidentialFlat
from app.models.settings import AuditLog
from app.services.property_master_service import seed_property_masters


@pytest.mark.asyncio
async def test_sensitive_action_is_staged_not_executed(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000001",
        full_name="Ramesh Kumar",
        mobile="9829012345",
        stage="NEW",
    )
    db_session.add(lead)
    await db_session.commit()

    tools = AIToolRegistry(db_session)
    approval_id = await tools.stage_sensitive_action(
        agent_name="lead_qualification",
        lead_id="OB-2026-000001",
        action_type="STAGE_CHANGE_LOST",
        payload={"reason": "Customer budget too low"},
    )

    await db_session.refresh(lead)
    assert lead.stage == "NEW"

    queue_item = await db_session.get(AIApprovalQueue, approval_id)
    assert queue_item is not None
    assert queue_item.status == "PENDING"
    assert queue_item.agent_name == "lead_qualification"
    assert queue_item.proposed_payload["reason"] == "Customer budget too low"


@pytest.mark.asyncio
async def test_execute_approved_action(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000002",
        full_name="Sita Devi",
        mobile="9829012346",
        stage="NEW",
    )
    db_session.add(lead)
    await db_session.commit()

    tools = AIToolRegistry(db_session)
    approval_id = await tools.stage_sensitive_action(
        agent_name="lead_qualification",
        lead_id="OB-2026-000002",
        action_type="STAGE_CHANGE_LOST",
        payload={"reason": "Customer bought elsewhere"},
    )

    # Reviewer approves the action
    success = await tools.execute_approved_action(
        approval_id=approval_id,
        reviewer_id="EMP-0001",
        review_note="Verified with customer on call",
    )
    assert success is True

    # Lead stage should now be LOST
    await db_session.refresh(lead)
    assert lead.stage == "LOST"
    assert lead.lost_reason == "Customer bought elsewhere"

    # Queue item should be APPROVED
    queue_item = await db_session.get(AIApprovalQueue, approval_id)
    assert queue_item.status == "APPROVED"
    assert queue_item.reviewed_by == "EMP-0001"
    assert queue_item.review_note == "Verified with customer on call"
    assert queue_item.reviewed_at is not None

    # LeadActivity should be logged
    activities = (
        await db_session.execute(
            select(LeadActivity).where(LeadActivity.lead_id == "OB-2026-000002")
        )
    ).scalars().all()
    assert len(activities) >= 1
    approval_activity = [a for a in activities if a.outcome == "APPROVED"][0]
    assert approval_activity.stage_before == "NEW"
    assert approval_activity.stage_after == "LOST"
    assert approval_activity.performed_by == "EMP-0001"

    # AuditLog should be recorded
    audit_logs = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.entity_id == "OB-2026-000002")
        )
    ).scalars().all()
    assert len(audit_logs) >= 1
    assert audit_logs[0].entity_name == "Lead"
    assert audit_logs[0].action == "AI_APPROVAL_STAGE_CHANGE_LOST"
    assert audit_logs[0].performed_by == "EMP-0001"


@pytest.mark.asyncio
async def test_reject_staged_action(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000003",
        full_name="Amit Patel",
        mobile="9829012347",
        stage="NEW",
    )
    db_session.add(lead)
    await db_session.commit()

    tools = AIToolRegistry(db_session)
    approval_id = await tools.stage_sensitive_action(
        agent_name="lead_qualification",
        lead_id="OB-2026-000003",
        action_type="STAGE_CHANGE_LOST",
        payload={"reason": "Customer unresponsive"},
    )

    # Reviewer rejects the action
    success = await tools.reject_staged_action(
        approval_id=approval_id,
        reviewer_id="EMP-0001",
        review_note="Customer just called back",
    )
    assert success is True

    # Lead stage remains NEW
    await db_session.refresh(lead)
    assert lead.stage == "NEW"

    # Queue item is REJECTED
    queue_item = await db_session.get(AIApprovalQueue, approval_id)
    assert queue_item.status == "REJECTED"
    assert queue_item.reviewed_by == "EMP-0001"
    assert queue_item.review_note == "Customer just called back"


@pytest.mark.asyncio
async def test_non_pending_action_cannot_be_re_reviewed(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000004",
        full_name="Sunil Joshi",
        mobile="9829012348",
        stage="NEW",
    )
    db_session.add(lead)
    await db_session.commit()

    tools = AIToolRegistry(db_session)
    approval_id = await tools.stage_sensitive_action(
        agent_name="lead_qualification",
        lead_id="OB-2026-000004",
        action_type="STAGE_CHANGE_LOST",
        payload={"reason": "Out of budget"},
    )

    # Approve first time
    assert await tools.execute_approved_action(approval_id, reviewer_id="EMP-0001") is True

    # Approving or rejecting again should return False
    assert await tools.execute_approved_action(approval_id, reviewer_id="EMP-0001") is False
    assert await tools.reject_staged_action(approval_id, reviewer_id="EMP-0001") is False


@pytest.mark.asyncio
async def test_search_properties(db_session: AsyncSession):
    await seed_property_masters(db_session)

    # Property 1: 3 BHK in Jaipur, Sale, 85L, live
    p1 = Property(
        property_id="OP-2026-00010",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Luxury 3 BHK Flat in Vaishali Nagar",
        city="Jaipur",
        locality="Vaishali Nagar",
        pincode="301001",
        expected_price=8500000,
        owner_name="Sharma Ji",
        owner_mobile="9829011111",
        is_live=True,
    )
    flat1 = PropResidentialFlat(
        property=p1,
        bhk=3,
        rooms=3,
        bathrooms=2,
        super_area=1450,
        carpet_area=1200,
    )

    # Property 2: 2 BHK in Jaipur, Sale, 45L, live
    p2 = Property(
        property_id="OP-2026-00011",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Affordable 2 BHK Flat in Mansarovar",
        city="Jaipur",
        locality="Mansarovar",
        pincode="301001",
        expected_price=4500000,
        owner_name="Verma Ji",
        owner_mobile="9829022222",
        is_live=True,
    )
    flat2 = PropResidentialFlat(
        property=p2,
        bhk=2,
        rooms=2,
        bathrooms=2,
        super_area=1000,
        carpet_area=850,
    )

    # Property 3: 3 BHK in Alwar, Sale, 60L, NOT LIVE
    p3 = Property(
        property_id="OP-2026-00012",
        listing_type=2,
        category_code=1,
        sub_category_code=1,
        title="Unverified 3 BHK in Alwar",
        city="Alwar",
        locality="Scheme 8",
        pincode="301001",
        expected_price=6000000,
        owner_name="Gupta Ji",
        owner_mobile="9829033333",
        is_live=False,
    )

    db_session.add_all([p1, flat1, p2, flat2, p3])
    await db_session.commit()

    tools = AIToolRegistry(db_session)

    # 1. Search city=Jaipur, max_price=5000000 -> Should return p2 only
    res_budget = await tools.search_properties({"city": "Jaipur", "max_price": 5000000})
    assert len(res_budget) == 1
    assert res_budget[0]["property_id"] == "OP-2026-00011"
    assert res_budget[0]["bhk"] == 2
    assert res_budget[0]["expected_price"] == 4500000.0

    # 2. Search bhk=3 in Jaipur -> Should return p1
    res_bhk = await tools.search_properties({"city": "Jaipur", "bhk": 3})
    assert len(res_bhk) == 1
    assert res_bhk[0]["property_id"] == "OP-2026-00010"
    assert res_bhk[0]["bhk"] == 3

    # 3. Search Alwar -> Should return 0 since p3 is_live=False
    res_alwar = await tools.search_properties({"city": "Alwar"})
    assert len(res_alwar) == 0

    # 4. Search locality Mansarovar
    res_loc = await tools.search_properties({"locality": "Mansarovar"})
    assert len(res_loc) == 1
    assert res_loc[0]["property_id"] == "OP-2026-00011"


@pytest.mark.asyncio
async def test_get_lead_details(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000005",
        full_name="Pooja Sharma",
        mobile="9829012349",
        stage="CONTACTED",
        temperature="HOT",
        budget_min=4000000,
        budget_max=6000000,
        preferred_city="Jaipur",
        preferred_locality="Vaishali Nagar",
    )
    db_session.add(lead)
    await db_session.commit()

    tools = AIToolRegistry(db_session)
    details = await tools.get_lead_details("OB-2026-000005")
    assert details is not None
    assert details["lead_id"] == "OB-2026-000005"
    assert details["full_name"] == "Pooja Sharma"
    assert details["temperature"] == "HOT"
    assert details["budget_min"] == 4000000.0
    assert details["budget_max"] == 6000000.0
    assert details["preferred_city"] == "Jaipur"

    # Non-existent lead
    assert await tools.get_lead_details("NON_EXISTENT") is None


@pytest.mark.asyncio
async def test_update_lead_requirements_safe(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000006",
        full_name="Deepak Verma",
        mobile="9829012350",
        stage="NEW",
        budget_min=2000000,
        budget_max=3000000,
        preferred_city="Alwar",
    )
    db_session.add(lead)
    await db_session.commit()

    tools = AIToolRegistry(db_session)

    # Safely update requirements including non-destructive fields
    # And include an attempt to update stage (which should be safely ignored)
    success = await tools.update_lead_requirements(
        lead_id="OB-2026-000006",
        updates={
            "budget_min": 3500000,
            "budget_max": 5000000,
            "preferred_city": "Jaipur",
            "preferred_locality": "Malviya Nagar",
            "temperature": "WARM",
            "stage": "LOST",  # MUST NOT MUTATE STAGE
        },
    )
    assert success is True

    await db_session.refresh(lead)
    assert float(lead.budget_min) == 3500000.0
    assert float(lead.budget_max) == 5000000.0
    assert lead.preferred_city == "Jaipur"
    assert lead.preferred_locality == "Malviya Nagar"
    assert lead.temperature == "WARM"
    # Verify stage was NOT mutated!
    assert lead.stage == "NEW"

    # Verify LeadActivity was created
    activities = (
        await db_session.execute(
            select(LeadActivity).where(LeadActivity.lead_id == "OB-2026-000006")
        )
    ).scalars().all()
    assert len(activities) >= 1
    assert activities[0].action_type == "REQUIREMENTS_UPDATE"
    assert activities[0].temperature == "WARM"


@pytest.mark.asyncio
async def test_positional_db_calling_convention(db_session: AsyncSession):
    lead = Lead(
        lead_id="OB-2026-000007",
        full_name="Rajesh Gupta",
        mobile="9829012351",
        stage="NEW",
    )
    db_session.add(lead)
    await db_session.commit()

    # Tools initialized without db session, passing db_session as first argument
    tools = AIToolRegistry()

    # 1. stage_sensitive_action(db, agent_name, lead_id, action_type, payload)
    approval_id = await tools.stage_sensitive_action(
        db_session,
        "lead_qualification",
        "OB-2026-000007",
        "STAGE_CHANGE_LOST",
        {"reason": "Not interested"},
    )
    assert approval_id is not None

    # 2. get_lead_details(db, lead_id)
    details = await tools.get_lead_details(db_session, "OB-2026-000007")
    assert details is not None
    assert details["lead_id"] == "OB-2026-000007"

    # 3. update_lead_requirements(db, lead_id, updates)
    ok = await tools.update_lead_requirements(
        db_session,
        "OB-2026-000007",
        {"temperature": "COLD"},
    )
    assert ok is True

    # 4. execute_approved_action(db, approval_id, reviewer_id)
    exec_ok = await tools.execute_approved_action(
        db_session,
        approval_id,
        "EMP-0001",
    )
    assert exec_ok is True

    await db_session.refresh(lead)
    assert lead.stage == "LOST"
    assert lead.temperature == "COLD"


def test_tool_definitions_schema():
    defs = AIToolRegistry.get_tool_definitions()
    assert isinstance(defs, list)
    assert len(defs) == 4
    tool_names = [d["function"]["name"] for d in defs]
    assert "search_properties" in tool_names
    assert "get_lead_details" in tool_names
    assert "update_lead_requirements" in tool_names
    assert "stage_sensitive_action" in tool_names
