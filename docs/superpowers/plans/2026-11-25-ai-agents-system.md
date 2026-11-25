# AI Agent Automation System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate a 13-agent AI automation platform into the Omshiv Real Estate CRM (FastAPI + PostgreSQL/SQLite + React) for automated property matching, qualification, multi-channel messaging, voice intake, site visits, and nurturing, wrapped in non-negotiable safety guardrails (instant per-agent feature flags, dry-run/shadow mode, human-in-the-loop approvals, rate limiting, day-one consent tracking, async scheduling, and DPDP-compliant PII retention).

**Architecture:** A modular AI engine (`app/services/ai/`) layered on top of existing CRM business logic without touching legacy tables. Safety guardrails intercept every action: verifying TRAI/DND quiet hours and consent before outbound contact, running in `SHADOW` mode by default, staging sensitive actions into a Human-In-The-Loop (`AIApprovalQueue`) queue, and dispatching asynchronous nurturing and property alerts via a dedicated scheduler worker (`app/workers/ai_scheduler.py`).

**Tech Stack:** FastAPI, SQLAlchemy (async), Alembic, Pydantic v2, Redis, Exotel Telephony API, DoubleTick WhatsApp Cloud Gateway, OpenAI API (with GPT-4o Vision & deterministic offline test mocks), React, TypeScript, Tailwind CSS.

**Spec:** `c:\xampp\htdocs\om_shiv\docs\superpowers\plans\Ai agent plsn.md`

---

## Global Constraints & Compliance Policies

- **Zero Breaking Changes:** Existing tables (`leads`, `properties`, `system_settings`, `audit_logs`) and API routes must remain fully functional.
- **Dynamic Feature Flags:** Every agent must have an independent flag (`DISABLED`, `SHADOW`, `LIVE`) stored in database and reconfigurable in real-time with zero server restart.
- **Shadow/Dry-Run Mode First:** Customer-facing communication (WhatsApp, Voice, SMS) defaults to `SHADOW` mode, recording intent, prompt, and response in `ai_agent_execution_logs` without firing external network calls.
- **Human-in-the-Loop (HITL) for Sensitive Mutations:** Changing lead stage to `LOST`, altering contractual records, or sending legal notices is staged in `ai_approval_queue` and requires explicit human staff sign-off.
- **Pre-Dial TRAI/DND & Quiet Hours Policy:** Outbound voice calls and marketing WhatsApp messages are strictly prohibited between 21:00 and 09:00 IST (`is_quiet_hours` check) and require verified prior opt-in (`CustomerConsent.is_opted_in == True`).
- **Immediate Opt-Out:** Customer replying "STOP", "UNSUBSCRIBE", or "BAND KARO" on any channel immediately revokes consent across all channels and halts active journeys.
- **Data Retention & PII Policy (DPDP Act 2023):**
  - Mobile numbers and customer names in `ai_agent_execution_logs` are masked (`+91 98****3210`) when displayed to non-admin roles.
  - Raw execution and conversation logs are retained for **90 days**, after which automated cleanup purges body text while keeping anonymized metric counters.
  - `CustomerConsent` records are retained permanently as required for regulatory audit trails.
  - Telephony audio recordings expire at the provider after **30 days**.
- **Deterministic Offline Testing:** All test suites must use deterministic local mocks (`mock_ai_service`). Zero live OpenAI/Exotel/DoubleTick calls during test runs.
- **Full Alembic Reversibility:** Migration `0011` must contain both complete `upgrade()` and `downgrade()` logic.

---

## Review Focus

1. **Pre-Dial TRAI/DND Enforcement:** If an outbound voice call is scheduled at 21:30 IST or for a lead without verified opt-in, the telephony client must NOT make an HTTP request to Exotel and must log `BLOCKED_QUIET_HOURS` or `BLOCKED_NO_CONSENT`.
2. **Opt-Out Propagation:** An incoming message containing "STOP" must immediately write `is_opted_in=False` to `CustomerConsent` and cancel any pending automated follow-up scheduled in `ai_scheduler`.
3. **Shadow Mode Leakage Protection:** When `whatsapp_agent` or `voice_calling_agent` is set to `SHADOW`, verifying mock assertions prove zero external HTTP dispatches to DoubleTick or Exotel.
4. **HITL Destructive Staging:** When an agent triggers a stage update to `LOST`, `leads.stage` must remain unchanged and an entry must appear in `ai_approval_queue` with status `PENDING`.
5. **Alembic Down-Migration Cleanliness:** Running `alembic downgrade -1` from version 0011 must cleanly remove all 5 AI tables without leaving dangling foreign keys or schema errors.

---

## Task Decomposition

### Task 1: AI Safety Database Models, Schema Migration & Rollback Coverage

**Files:**
- Create: `backend/app/models/ai_agents.py`
- Modify: `backend/app/db/base.py`
- Create: `backend/alembic/versions/0011_ai_agents_safety_schema.py`
- Test: `backend/tests/test_ai_agent_models.py`
- Test: `backend/tests/test_ai_migration_reversible.py`

**Interfaces:**
- Consumes: `app.core.database.Base`, `JSON_TYPE`
- Produces: Models `AIAgentConfig`, `CustomerConsent`, `AIApprovalQueue`, `AIAgentExecutionLog`, `PropertyAlertHistory`

- [ ] **Step 1: Write the failing tests (Models & Migration Reversibility)**

```python
# backend/tests/test_ai_agent_models.py
import pytest
from sqlalchemy import select
from app.models.ai_agents import (
    AIAgentConfig,
    CustomerConsent,
    AIApprovalQueue,
    AIAgentExecutionLog,
    PropertyAlertHistory,
)

@pytest.mark.asyncio
async def test_ai_agent_models_creation(db_session):
    config = AIAgentConfig(
        agent_name="property_search",
        display_name="AI Property Search Agent",
        mode="SHADOW",
        rate_limit_per_hour=10,
        requires_hitl=False,
        is_customer_facing=False,
    )
    db_session.add(config)
    await db_session.commit()
    
    fetched = (await db_session.execute(
        select(AIAgentConfig).where(AIAgentConfig.agent_name == "property_search")
    )).scalar_one_or_none()
    assert fetched is not None
    assert fetched.mode == "SHADOW"
```

```python
# backend/tests/test_ai_migration_reversible.py
import pytest
from alembic.config import Config
from alembic import command

def test_migration_0011_upgrade_and_downgrade():
    alembic_cfg = Config("backend/alembic.ini")
    alembic_cfg.set_main_option("script_location", "backend/alembic")
    # Upgrade to head
    command.upgrade(alembic_cfg, "head")
    # Downgrade back to 0010
    command.downgrade(alembic_cfg, "0010_add_soft_delete")
    # Re-upgrade to head
    command.upgrade(alembic_cfg, "head")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_agent_models.py backend/tests/test_ai_migration_reversible.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.ai_agents'`

- [ ] **Step 3: Implement `app/models/ai_agents.py`, register in `app/db/base.py`, and create `0011_ai_agents_safety_schema.py`**

Define tables:
- `ai_agent_configs`: `id`, `agent_name` (unique index), `display_name`, `mode` (`DISABLED`, `SHADOW`, `LIVE`), `rate_limit_per_hour`, `requires_hitl`, `is_customer_facing`, `extra_config` (JSON)
- `customer_consents`: `id`, `mobile` (index), `channel` (`WHATSAPP`, `VOICE`, `SMS`), `is_opted_in` (bool), `consent_source`, `opted_in_at`, `opted_out_at`, `opt_out_reason`
- `ai_approval_queue`: `id` (UUID), `agent_name`, `lead_id`, `action_type`, `proposed_payload` (JSON), `status` (`PENDING`, `APPROVED`, `REJECTED`), `requested_at`, `reviewed_by`, `reviewed_at`, `review_note`
- `ai_agent_execution_logs`: `id`, `agent_name`, `lead_id`, `channel`, `mode`, `trigger_event`, `input_summary`, `output_response`, `tools_called` (JSON), `status` (`SUCCESS`, `SHADOW_LOGGED`, `BLOCKED_CONSENT`, `BLOCKED_RATE_LIMIT`, `BLOCKED_FLAG`, `PENDING_APPROVAL`, `ERROR`), `approval_id`, `error_message`, `created_at`
- `property_alert_history`: `id`, `lead_id`, `property_id`, `channel`, `sent_at`, `status`

In `0011_ai_agents_safety_schema.py`, implement complete `upgrade()` creating all 5 tables and indexes, and `downgrade()` dropping all 5 tables cleanly.

- [ ] **Step 4: Run tests to verify they pass**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_agent_models.py backend/tests/test_ai_migration_reversible.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/ai_agents.py backend/app/db/base.py backend/alembic/versions/0011_ai_agents_safety_schema.py backend/tests/test_ai_agent_models.py backend/tests/test_ai_migration_reversible.py
git commit -m "feat(ai): add ai safety models, schema migration and reversible downgrade test"
```

---

### Task 2: Core Safety Guardrails Engine (Flags, Shadow Mode, Rate Limits, Consent, PII Masking)

**Files:**
- Create: `backend/app/services/ai/safety_guardrails.py`
- Test: `backend/tests/test_ai_safety_guardrails.py`

**Interfaces:**
- Consumes: `AIAgentConfig`, `CustomerConsent`, `AIAgentExecutionLog`, `PropertyAlertHistory`
- Produces: `SafetyGuardrailsService` with methods:
  - `get_agent_mode(agent_name: str) -> str`
  - `verify_consent(mobile: str, channel: str) -> bool`
  - `register_consent(mobile: str, channel: str, is_opted_in: bool, source: str, reason: str = None)`
  - `check_rate_limit(mobile: str, channel: str, max_per_hour: int) -> bool`
  - `is_duplicate_property_alert(lead_id: str, property_id: str, cooldown_days: int = 7) -> bool`
  - `mask_pii(text_or_mobile: str) -> str`
  - `record_execution_log(...) -> AIAgentExecutionLog`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_safety_guardrails.py
import pytest
from app.services.ai.safety_guardrails import SafetyGuardrailsService
from app.models.ai_agents import AIAgentConfig

@pytest.mark.asyncio
async def test_opt_out_blocks_messaging(db_session):
    guard = SafetyGuardrailsService(db_session)
    await guard.register_consent("919876543210", "WHATSAPP", is_opted_in=False, source="INCOMING_SMS", reason="STOP")
    allowed = await guard.verify_consent("919876543210", "WHATSAPP")
    assert allowed is False

@pytest.mark.asyncio
async def test_pii_masking():
    guard = SafetyGuardrailsService(None)
    masked = guard.mask_pii("919829012345")
    assert masked == "9198****2345"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_safety_guardrails.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.safety_guardrails'`

- [ ] **Step 3: Implement `SafetyGuardrailsService` in `backend/app/services/ai/safety_guardrails.py`**

Implement consent lookups, instant flag resolution, rate limiting via sliding window timestamp query, 7-day alert deduplication check, PII masking utility, and execution logging.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_safety_guardrails.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/safety_guardrails.py backend/tests/test_ai_safety_guardrails.py
git commit -m "feat(ai): implement safety guardrails, consent validator and pii masking"
```

---

### Task 3: Shared LLM Client, Prompt Registry & Deterministic Test Fixtures

**Files:**
- Create: `backend/app/services/ai/llm_client.py`
- Create: `backend/app/services/ai/prompts.py`
- Create: `backend/tests/ai_mocks.py`
- Test: `backend/tests/test_ai_llm_client.py`

**Interfaces:**
- Consumes: `settings.OPENAI_API_KEY`, `settings.OPENAI_MODEL`, `settings.OPENAI_BASE_URL`
- Produces: `AIClientService.chat_completion_json(...)`, `mock_ai_service` test fixture

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_llm_client.py
import pytest
from app.services.ai.llm_client import AIClientService
from tests.ai_mocks import MockAIClientService

@pytest.mark.asyncio
async def test_llm_deterministic_mock():
    mock_client = MockAIClientService()
    mock_client.set_canned_response({"location": "Jaipur", "bhk": 3, "budget_max": 8000000})
    res = await mock_client.chat_completion_json("sys", "user", {})
    assert res["location"] == "Jaipur"
    assert res["bhk"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_llm_client.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.llm_client'`

- [ ] **Step 3: Implement `AIClientService`, `prompts.py`, and `MockAIClientService`**

Implement async OpenAI client using `httpx`, JSON cleaning/parsing, structured schema validation, token estimation, and Hindi/English system prompt templates. In `tests/ai_mocks.py`, export `MockAIClientService` and pytest fixture to be used in all agent tests for zero-cost, 100% deterministic testing.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_llm_client.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/llm_client.py backend/app/services/ai/prompts.py backend/tests/ai_mocks.py backend/tests/test_ai_llm_client.py
git commit -m "feat(ai): implement shared llm client and deterministic mock fixtures"
```

---

### Task 4: Controlled Backend Tool Registry & HITL Approval Stager

**Files:**
- Create: `backend/app/services/ai/tools.py`
- Test: `backend/tests/test_ai_tools.py`

**Interfaces:**
- Consumes: `Lead`, `Property`, `AIApprovalQueue`, `LeadActivity`
- Produces: `AIToolRegistry` with:
  - `search_properties(db, filters: dict) -> list[dict]`
  - `update_lead_requirements(db, lead_id: str, updates: dict) -> bool`
  - `stage_sensitive_action(db, agent_name: str, lead_id: str, action_type: str, payload: dict) -> str`
  - `execute_approved_action(db, approval_id: str, reviewer_id: str) -> bool`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_tools.py
import pytest
from app.services.ai.tools import AIToolRegistry
from app.models.leads import Lead
from app.models.ai_agents import AIApprovalQueue

@pytest.mark.asyncio
async def test_sensitive_action_is_staged_not_executed(db_session):
    lead = Lead(lead_id="OB-2026-000001", full_name="Ramesh Kumar", mobile="9829012345", stage="NEW")
    db_session.add(lead)
    await db_session.commit()
    
    tools = AIToolRegistry(db_session)
    approval_id = await tools.stage_sensitive_action(
        agent_name="lead_qualification",
        lead_id="OB-2026-000001",
        action_type="STAGE_CHANGE_LOST",
        payload={"reason": "Customer budget too low"}
    )
    
    await db_session.refresh(lead)
    assert lead.stage == "NEW"
    
    queue_item = await db_session.get(AIApprovalQueue, approval_id)
    assert queue_item is not None
    assert queue_item.status == "PENDING"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_tools.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.tools'`

- [ ] **Step 3: Implement `AIToolRegistry` in `backend/app/services/ai/tools.py`**

Include read-only property search using SQLAlchemy filters (city, locality, budget, category), safe requirements writer, and staging logic for `STAGE_CHANGE_LOST`, `STATUS_CHANGE_CANCELLED`, and other sensitive actions.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_tools.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/tools.py backend/tests/test_ai_tools.py
git commit -m "feat(ai): implement controlled tool registry and hitl approval stager"
```

---

### Task 5: Agent 1 - AI Property Search Agent (Deterministic Mock Tested)

**Files:**
- Create: `backend/app/services/ai/agents/property_search_agent.py`
- Test: `backend/tests/test_ai_property_search_agent.py`

**Interfaces:**
- Consumes: `AIClientService`, `AIToolRegistry`, `SafetyGuardrailsService`
- Produces: `PropertySearchAgent.search_properties_conversational(query: str, session_context: dict = None) -> dict`

- [ ] **Step 1: Write the failing test with mock fixture**

```python
# backend/tests/test_ai_property_search_agent.py
import pytest
from app.services.ai.agents.property_search_agent import PropertySearchAgent
from app.models.properties import Property
from tests.ai_mocks import MockAIClientService

@pytest.mark.asyncio
async def test_conversational_property_search_deterministic(db_session):
    prop = Property(
        property_id="OP-2026-00001",
        listing_type=2, category_code=1, sub_category_code=1,
        title="Luxury 3 BHK Flat in Vaishali Nagar",
        city="Jaipur", locality="Vaishali Nagar", pincode="302021",
        expected_price=8500000, owner_name="Sharma Ji", owner_mobile="9829011111",
        is_live=True
    )
    db_session.add(prop)
    await db_session.commit()
    
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "city": "Jaipur", "locality": "Vaishali Nagar", "bhk": 3, "max_price": 8500000
    })
    
    agent = PropertySearchAgent(db_session, ai_client=mock_ai)
    result = await agent.search_properties_conversational("Mujhe Jaipur Vaishali Nagar me 85 lakh tak flat chahiye")
    assert result["success"] is True
    assert len(result["properties"]) > 0
    assert result["properties"][0]["property_id"] == "OP-2026-00001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_property_search_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.property_search_agent'`

- [ ] **Step 3: Implement `PropertySearchAgent` in `backend/app/services/ai/agents/property_search_agent.py`**

Parse query using structured LLM output into search parameters (`city`, `locality`, `bhk`, `max_price`), execute SQLAlchemy query against verified live listings, and format response with property citations.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_property_search_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/agents/property_search_agent.py backend/tests/test_ai_property_search_agent.py
git commit -m "feat(ai): implement agent 1 property search agent with deterministic test"
```

---

### Task 6: Agent 2 - AI Lead Qualification Agent (Deterministic Mock Tested)

**Files:**
- Create: `backend/app/services/ai/agents/lead_qualification_agent.py`
- Test: `backend/tests/test_ai_lead_qualification_agent.py`

**Interfaces:**
- Consumes: `AIClientService`, `AIToolRegistry`, `SafetyGuardrailsService`, `Lead`
- Produces: `LeadQualificationAgent.qualify_lead(lead_id: str, conversation_transcript: str) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_lead_qualification_agent.py
import pytest
from app.services.ai.agents.lead_qualification_agent import LeadQualificationAgent
from app.models.leads import Lead
from tests.ai_mocks import MockAIClientService

@pytest.mark.asyncio
async def test_qualify_hot_lead_deterministic(db_session):
    lead = Lead(lead_id="OB-2026-000002", full_name="Vijay Verma", mobile="9829022222", stage="NEW")
    db_session.add(lead)
    await db_session.commit()
    
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "budget_max": 8000000,
        "timeline": "IMMEDIATE",
        "temperature": "HOT",
        "qualification_score": 90,
        "summary": "Ready buyer for 3 BHK in Mansarovar"
    })
    
    agent = LeadQualificationAgent(db_session, ai_client=mock_ai)
    transcript = "Customer: I need 3 BHK in Mansarovar within 80 lakh, planning to purchase next week."
    res = await agent.qualify_lead("OB-2026-000002", transcript)
    
    assert res["temperature"] == "HOT"
    assert res["budget_max"] == 8000000
    
    await db_session.refresh(lead)
    assert lead.temperature == "HOT"
    assert lead.budget_max == 8000000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_lead_qualification_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.lead_qualification_agent'`

- [ ] **Step 3: Implement `LeadQualificationAgent` in `backend/app/services/ai/agents/lead_qualification_agent.py`**

Extract budget, timeline, location, BHK, score 0-100, classify `HOT`/`WARM`/`COLD`/`FUTURE_PROSPECT`, update lead fields and log to `LeadActivity`.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_lead_qualification_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/agents/lead_qualification_agent.py backend/tests/test_ai_lead_qualification_agent.py
git commit -m "feat(ai): implement agent 2 lead qualification agent"
```

---

### Task 7: Agent 3 - AI Customer Support Agent & Escalation Router

**Files:**
- Create: `backend/app/services/ai/agents/customer_support_agent.py`
- Test: `backend/tests/test_ai_customer_support_agent.py`

**Interfaces:**
- Consumes: `AIClientService`, `Property`, `SafetyGuardrailsService`
- Produces: `CustomerSupportAgent.answer_inquiry(customer_query: str, property_id: str = None) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_customer_support_agent.py
import pytest
from app.services.ai.agents.customer_support_agent import CustomerSupportAgent
from tests.ai_mocks import MockAIClientService

@pytest.mark.asyncio
async def test_escalation_detected_on_dispute(db_session):
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "response": "Connecting you immediately with our senior legal assistance desk.",
        "escalate_to_human": True,
        "escalation_reason": "LEGAL_DISPUTE"
    })
    agent = CustomerSupportAgent(db_session, ai_client=mock_ai)
    res = await agent.answer_inquiry("I want to file a legal fraud complaint against your broker!")
    assert res["escalate_to_human"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_customer_support_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.customer_support_agent'`

- [ ] **Step 3: Implement `CustomerSupportAgent` in `backend/app/services/ai/agents/customer_support_agent.py`**

Retrieve verified property data, answer FAQs, guard against hallucinations, detect conflict/legal/complex negotiation and flag `escalate_to_human=True`.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_customer_support_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/agents/customer_support_agent.py backend/tests/test_ai_customer_support_agent.py
git commit -m "feat(ai): implement agent 3 customer support agent"
```

---

### Task 8: Agent 5 - AI Sales Assistant Agent & HITL Approvals

**Files:**
- Create: `backend/app/services/ai/agents/sales_assistant_agent.py`
- Test: `backend/tests/test_ai_sales_assistant_agent.py`

**Interfaces:**
- Consumes: `AIClientService`, `AIToolRegistry`, `Lead`, `LeadActivity`
- Produces: `SalesAssistantAgent`:
  - `generate_lead_summary(lead_id: str) -> dict`
  - `recommend_followup_message(lead_id: str) -> dict`
  - `request_stage_update(lead_id: str, new_stage: str, reason: str) -> str`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_sales_assistant_agent.py
import pytest
from app.services.ai.agents.sales_assistant_agent import SalesAssistantAgent
from app.models.leads import Lead, LeadActivity
from tests.ai_mocks import MockAIClientService

@pytest.mark.asyncio
async def test_sales_assistant_summary_generation(db_session):
    lead = Lead(lead_id="OB-2026-000003", full_name="Sanjay Gupta", mobile="9829033333", stage="CONTACTED")
    act = LeadActivity(lead_id="OB-2026-000003", action_type="CALL", outcome="DISCUSSED", note="Looking for plot near Alwar bypass")
    db_session.add_all([lead, act])
    await db_session.commit()
    
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "full_name": "Sanjay Gupta",
        "summary": "Customer is interested in residential plots near Alwar bypass.",
        "recommended_action": "Share approved township layout on WhatsApp."
    })
    
    agent = SalesAssistantAgent(db_session, ai_client=mock_ai)
    summary = await agent.generate_lead_summary("OB-2026-000003")
    assert summary["full_name"] == "Sanjay Gupta"
    assert "plot" in summary["summary"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_sales_assistant_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.sales_assistant_agent'`

- [ ] **Step 3: Implement `SalesAssistantAgent` in `backend/app/services/ai/agents/sales_assistant_agent.py`**

Compile lead history and activities, generate executive briefing, draft follow-up messages, and stage sensitive stage updates into `AIApprovalQueue`.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_sales_assistant_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/agents/sales_assistant_agent.py backend/tests/test_ai_sales_assistant_agent.py
git commit -m "feat(ai): implement agent 5 sales assistant agent"
```

---

### Task 9: Agent 6 - AI Document Processing Agent (OCR & Scanned PDF Pipeline)

**Files:**
- Create: `backend/app/services/ai/agents/document_processing_agent.py`
- Create: `backend/app/services/ai/ocr_service.py`
- Test: `backend/tests/test_ai_document_processing_agent.py`

**Interfaces:**
- Consumes: `pypdf`, `pytesseract` or OpenAI GPT-4o Vision, `AIClientService`
- Produces: `DocumentProcessingAgent`:
  - `extract_from_pdf_bytes(file_bytes: bytes, filename: str) -> dict`
  - `extract_from_image_bytes(file_bytes: bytes, filename: str) -> dict`
  - `extract_property_document(text_content: str, doc_type: str = "REGISTRY") -> dict`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_document_processing_agent.py
import pytest
from app.services.ai.agents.document_processing_agent import DocumentProcessingAgent
from tests.ai_mocks import MockAIClientService

@pytest.mark.asyncio
async def test_extract_registry_document_from_text():
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "khasra_number": "412",
        "plot_area": "250 Sq Yards",
        "locality": "Vaishali Nagar",
        "owner_name": "Ram Lal Sharma",
        "is_missing_required_fields": False
    })
    agent = DocumentProcessingAgent(ai_client=mock_ai)
    sample_text = "Registry Deed: Khasra No 412, Area 250 Sq Yards, Locality Vaishali Nagar, Owner Ram Lal Sharma."
    res = await agent.extract_property_document(sample_text)
    assert res["khasra_number"] == "412"
    assert res["owner_name"] == "Ram Lal Sharma"

@pytest.mark.asyncio
async def test_pdf_buffer_text_extraction():
    # Test OCR / PDF text extraction pipeline
    from app.services.ai.ocr_service import extract_text_from_file_buffer
    dummy_text = b"%PDF-1.4 ... Dummy PDF Content ..."
    text = await extract_text_from_file_buffer(dummy_text, "test.pdf")
    assert isinstance(text, str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_document_processing_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.document_processing_agent'`

- [ ] **Step 3: Implement `ocr_service.py` and `DocumentProcessingAgent`**

Implement:
1. `ocr_service.py`: PDF reader (using standard `pypdf` buffer parsing) + Vision/OCR fallback for scanned image pages (`.png`, `.jpg`, `.jpeg`).
2. `DocumentProcessingAgent`: Parses extracted text using structured LLM schema into property metadata (khasra, plot area, unit, owner name, registry date, missing required fields, and inconsistent info flags).

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_document_processing_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/ocr_service.py backend/app/services/ai/agents/document_processing_agent.py backend/tests/test_ai_document_processing_agent.py
git commit -m "feat(ai): implement agent 6 document processing with pdf and ocr pipeline"
```

---

### Task 10: Omnichannel Intake - Agent 8 (Meta Ads) & Agent 9 (Instagram)

**Files:**
- Create: `backend/app/services/ai/agents/meta_lead_agent.py`
- Create: `backend/app/api/v1/endpoints/ai_webhooks.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_ai_meta_lead_agent.py`

**Interfaces:**
- Consumes: `Lead`, `SafetyGuardrailsService`, `LeadQualificationAgent`
- Produces: `MetaLeadAgent.process_meta_lead(payload: dict) -> dict`, Webhook routes `/v1/ai/webhooks/meta`, `/v1/ai/webhooks/instagram`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_meta_lead_agent.py
import pytest
from app.services.ai.agents.meta_lead_agent import MetaLeadAgent
from app.models.leads import Lead
from app.models.ai_agents import CustomerConsent

@pytest.mark.asyncio
async def test_meta_lead_intake_creates_lead_and_consent(db_session):
    agent = MetaLeadAgent(db_session)
    payload = {
        "leadgen_id": "meta_123456",
        "full_name": "Anita Roy",
        "mobile": "9829044444",
        "city": "Jaipur",
        "ad_name": "Vaishali Nagar Project Launch"
    }
    res = await agent.process_meta_lead(payload)
    assert res["created"] is True
    
    lead = (await db_session.execute(Lead.select().where(Lead.mobile == "9829044444"))).scalar_one_or_none()
    assert lead is not None
    assert lead.source == "META_LEAD_ADS"
    
    consent = (await db_session.execute(CustomerConsent.select().where(CustomerConsent.mobile == "9829044444"))).scalar_one_or_none()
    assert consent is not None
    assert consent.is_opted_in is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_meta_lead_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.meta_lead_agent'`

- [ ] **Step 3: Implement `MetaLeadAgent` and webhook routes in `ai_webhooks.py`**

Validate Meta lead payload, check deduplication using `idempotency_key`, record `CustomerConsent` with `source="META_FORM"`, create `Lead`, and trigger qualification.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_meta_lead_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/agents/meta_lead_agent.py backend/app/api/v1/endpoints/ai_webhooks.py backend/app/main.py backend/tests/test_ai_meta_lead_agent.py
git commit -m "feat(ai): implement agent 8 meta and agent 9 instagram lead intake"
```

---

### Task 11: Agent 7 - AI WhatsApp Agent (Shadow Mode & Instant Opt-Out)

**Files:**
- Create: `backend/app/services/ai/agents/whatsapp_agent.py`
- Modify: `backend/app/api/v1/endpoints/ai_webhooks.py`
- Test: `backend/tests/test_ai_whatsapp_agent.py`

**Interfaces:**
- Consumes: `WhatsAppGateway`, `SafetyGuardrailsService`, `PropertySearchAgent`
- Produces: `WhatsAppAgent.handle_incoming_message(mobile: str, text: str) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_whatsapp_agent.py
import pytest
from app.services.ai.agents.whatsapp_agent import WhatsAppAgent
from app.models.ai_agents import AIAgentConfig, AIAgentExecutionLog, CustomerConsent

@pytest.mark.asyncio
async def test_whatsapp_stop_unsubscribes_instantly(db_session):
    agent = WhatsAppAgent(db_session)
    res = await agent.handle_incoming_message("9829055555", "STOP")
    assert res["status"] == "OPTED_OUT"
    
    consent = (await db_session.execute(CustomerConsent.select().where(CustomerConsent.mobile == "9829055555"))).scalar_one_or_none()
    assert consent is not None
    assert consent.is_opted_in is False

@pytest.mark.asyncio
async def test_whatsapp_shadow_mode_does_not_send_live_message(db_session):
    cfg = AIAgentConfig(agent_name="whatsapp_agent", display_name="WhatsApp", mode="SHADOW")
    db_session.add(cfg)
    await db_session.commit()
    
    agent = WhatsAppAgent(db_session)
    res = await agent.handle_incoming_message("9829055555", "Hello, do you have flats in Alwar?")
    assert res["mode"] == "SHADOW"
    assert res["dispatched_live"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_whatsapp_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.whatsapp_agent'`

- [ ] **Step 3: Implement `WhatsAppAgent` in `backend/app/services/ai/agents/whatsapp_agent.py`**

Process incoming WhatsApp message:
1. Detect opt-out keywords ("STOP", "UNSUBSCRIBE", "BAND KARO") -> update `CustomerConsent` immediately.
2. Check feature flag mode (`DISABLED` -> no-op; `SHADOW` -> generate answer, record to `AIAgentExecutionLog`, do NOT send HTTP request; `LIVE` -> send via `whatsapp_gateway`).
3. Connect with `PropertySearchAgent` and `LeadQualificationAgent` for conversational replies.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_whatsapp_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/agents/whatsapp_agent.py backend/tests/test_ai_whatsapp_agent.py
git commit -m "feat(ai): implement agent 7 whatsapp agent with shadow mode and opt-out"
```

---

### Task 12: Agent 13 - AI Voice Calling Agent (Exotel Contract & TRAI Pre-Dial Gate)

**Files:**
- Create: `backend/app/services/ai/telephony_client.py`
- Create: `backend/app/services/ai/agents/voice_calling_agent.py`
- Modify: `backend/app/api/v1/endpoints/ai_webhooks.py`
- Test: `backend/tests/test_ai_voice_calling_agent.py`

**Interfaces:**
- Consumes: `SafetyGuardrailsService`, `LeadQualificationAgent`
- Produces: `ExotelTelephonyClient`, `VoiceCallingAgent.trigger_outbound_call(lead_id: str) -> dict`, `process_call_transcript(lead_id: str, transcript: str) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_voice_calling_agent.py
import pytest
from app.services.ai.agents.voice_calling_agent import VoiceCallingAgent
from app.models.leads import Lead
from app.models.ai_agents import AIAgentConfig, CustomerConsent
from tests.ai_mocks import MockTelephonyClient

@pytest.mark.asyncio
async def test_voice_call_blocked_without_consent(db_session):
    lead = Lead(lead_id="OB-2026-000004", full_name="Sunil Joshi", mobile="9829066666", stage="NEW")
    db_session.add(lead)
    await db_session.commit()
    
    mock_telephony = MockTelephonyClient()
    agent = VoiceCallingAgent(db_session, telephony_client=mock_telephony)
    res = await agent.trigger_outbound_call("OB-2026-000004")
    
    assert res["status"] == "BLOCKED_NO_CONSENT"
    assert mock_telephony.calls_dispatched == 0

@pytest.mark.asyncio
async def test_voice_call_shadow_mode_logs_without_calling(db_session):
    cfg = AIAgentConfig(agent_name="voice_calling_agent", display_name="Voice Call", mode="SHADOW")
    lead = Lead(lead_id="OB-2026-000004b", full_name="Sunil Joshi", mobile="9829066667", stage="NEW")
    consent = CustomerConsent(mobile="9829066667", channel="VOICE", is_opted_in=True)
    db_session.add_all([cfg, lead, consent])
    await db_session.commit()
    
    mock_telephony = MockTelephonyClient()
    agent = VoiceCallingAgent(db_session, telephony_client=mock_telephony)
    res = await agent.trigger_outbound_call("OB-2026-000004b")
    
    assert res["mode"] == "SHADOW"
    assert res["call_dispatched"] is False
    assert mock_telephony.calls_dispatched == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_voice_calling_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.voice_calling_agent'`

- [ ] **Step 3: Implement `telephony_client.py` and `VoiceCallingAgent`**

1. `ExotelTelephonyClient`:
   - Outbound Call API: `POST https://{api_key}:{api_token}@api.exotel.com/v1/Accounts/{sid}/Calls/connect.json`
   - Payload: `From={agent_flow_number}`, `To={customer_mobile}`, `CallerId={virtual_number}`, `StatusCallback={webhook_url}`
2. `VoiceCallingAgent`:
   - **Pre-Dial Gate 1:** Check TRAI quiet hours (`is_quiet_hours(21:00, 09:00)`). Block if inside quiet hours.
   - **Pre-Dial Gate 2:** Check `customer_consents` for channel `VOICE`. Block with `BLOCKED_NO_CONSENT` if missing or opted-out.
   - **Pre-Dial Gate 3:** Check feature flag mode: if `SHADOW`, log execution and return without dispatching call. If `LIVE`, dispatch via Exotel client.
   - **Transcript Ingestion:** Webhook parses speech-to-text transcript (Hindi/Hinglish), extracts budget/BHK/timeline, and updates lead.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_voice_calling_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/telephony_client.py backend/app/services/ai/agents/voice_calling_agent.py backend/tests/test_ai_voice_calling_agent.py
git commit -m "feat(ai): implement agent 13 voice calling with exotel contract and trai pre-dial gate"
```

---

### Task 13: Agent 12 - AI New Property Alert Agent (Anti-Spam & Deduplication)

**Files:**
- Create: `backend/app/services/ai/agents/new_property_alert_agent.py`
- Test: `backend/tests/test_ai_new_property_alert_agent.py`

**Interfaces:**
- Consumes: `Property`, `Lead`, `SafetyGuardrailsService`, `PropertyAlertHistory`
- Produces: `NewPropertyAlertAgent.dispatch_alerts_for_property(property_id: str) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_new_property_alert_agent.py
import pytest
from app.services.ai.agents.new_property_alert_agent import NewPropertyAlertAgent
from app.models.properties import Property
from app.models.leads import Lead
from app.models.ai_agents import PropertyAlertHistory, CustomerConsent

@pytest.mark.asyncio
async def test_duplicate_alert_suppressed(db_session):
    prop = Property(
        property_id="OP-2026-00005", listing_type=2, category_code=1, sub_category_code=1,
        title="2 BHK Flat", city="Alwar", expected_price=3000000, owner_name="X", owner_mobile="999", is_live=True
    )
    lead = Lead(lead_id="OB-2026-000005", full_name="Prem", mobile="9829077777", preferred_city="Alwar", budget_max=3500000)
    consent = CustomerConsent(mobile="9829077777", channel="WHATSAPP", is_opted_in=True)
    history = PropertyAlertHistory(lead_id="OB-2026-000005", property_id="OP-2026-00005", channel="WHATSAPP", status="SENT")
    db_session.add_all([prop, lead, consent, history])
    await db_session.commit()
    
    agent = NewPropertyAlertAgent(db_session)
    res = await agent.dispatch_alerts_for_property("OP-2026-00005")
    assert res["eligible_leads_count"] == 1
    assert res["dispatched_count"] == 0
    assert res["suppressed_duplicate_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_new_property_alert_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.new_property_alert_agent'`

- [ ] **Step 3: Implement `NewPropertyAlertAgent` in `backend/app/services/ai/agents/new_property_alert_agent.py`**

Find matching leads by location, budget, and category; check 7-day duplicate suppression via `PropertyAlertHistory`; verify active consent; dispatch shadow or live alerts; record to history.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_new_property_alert_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/agents/new_property_alert_agent.py backend/tests/test_ai_new_property_alert_agent.py
git commit -m "feat(ai): implement agent 12 new property alert agent with anti-spam deduplication"
```

---

### Task 14: Agent 4 - AI Site Visit Booking Agent

**Files:**
- Create: `backend/app/services/ai/agents/site_visit_agent.py`
- Test: `backend/tests/test_ai_site_visit_agent.py`

**Interfaces:**
- Consumes: `Property`, `Lead`, `LeadActivity`
- Produces: `SiteVisitAgent`:
  - `check_available_slots(property_id: str, visit_date: str) -> list[str]`
  - `book_site_visit(lead_id: str, property_id: str, slot: str, visitor_notes: str) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_site_visit_agent.py
import pytest
from app.services.ai.agents.site_visit_agent import SiteVisitAgent
from app.models.leads import Lead
from app.models.properties import Property

@pytest.mark.asyncio
async def test_book_site_visit_workflow(db_session):
    lead = Lead(lead_id="OB-2026-000006", full_name="Geeta Sharma", mobile="9829088888")
    prop = Property(property_id="OP-2026-00006", listing_type=2, category_code=1, sub_category_code=1, title="Plot", city="Alwar", expected_price=2000000, owner_name="Y", owner_mobile="888")
    db_session.add_all([lead, prop])
    await db_session.commit()
    
    agent = SiteVisitAgent(db_session)
    booking = await agent.book_site_visit("OB-2026-000006", "OP-2026-00006", "2026-12-01 11:00", "Customer coming by car")
    assert booking["success"] is True
    assert booking["booking_id"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_site_visit_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.site_visit_agent'`

- [ ] **Step 3: Implement `SiteVisitAgent` in `backend/app/services/ai/agents/site_visit_agent.py`**

Validate slot availability, prevent duplicate booking for same property/time, create visit activity in CRM, and prepare confirmation message payload.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_site_visit_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/agents/site_visit_agent.py backend/tests/test_ai_site_visit_agent.py
git commit -m "feat(ai): implement agent 4 site visit booking agent"
```

---

### Task 15: Agent 10 & 11 - AI Follow-Up & Post-Site Visit Nurturing Engine

**Files:**
- Create: `backend/app/services/ai/agents/followup_journey_agent.py`
- Test: `backend/tests/test_ai_followup_journey_agent.py`

**Interfaces:**
- Consumes: `Lead`, `LeadActivity`, `CustomerConsent`, `SafetyGuardrailsService`
- Produces: `FollowupJourneyAgent`:
  - `evaluate_nurturing_step(lead_id: str) -> dict`
  - `process_post_visit_feedback(lead_id: str, visit_id: str, feedback_text: str) -> dict`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_followup_journey_agent.py
import pytest
from app.services.ai.agents.followup_journey_agent import FollowupJourneyAgent
from app.models.leads import Lead
from tests.ai_mocks import MockAIClientService

@pytest.mark.asyncio
async def test_post_visit_future_prospect_handled(db_session):
    lead = Lead(lead_id="OB-2026-000007", full_name="Manish", mobile="9829099999", stage="SITE_VISIT_DONE")
    db_session.add(lead)
    await db_session.commit()
    
    mock_ai = MockAIClientService()
    mock_ai.set_canned_response({
        "intent": "FUTURE_PROSPECT",
        "timeline_months": 3,
        "feedback_summary": "Liked property but planning purchase in 3 months",
        "scheduled_follow_up_days": 60
    })
    
    agent = FollowupJourneyAgent(db_session, ai_client=mock_ai)
    res = await agent.process_post_visit_feedback(
        "OB-2026-000007", "SV-1", "Property acchi lagi lekin abhi 3 mahine baad lenge."
    )
    assert res["intent"] == "FUTURE_PROSPECT"
    assert res["scheduled_follow_up_days"] >= 60
    
    await db_session.refresh(lead)
    assert lead.temperature == "FUTURE_PROSPECT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_followup_journey_agent.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ai.agents.followup_journey_agent'`

- [ ] **Step 3: Implement `FollowupJourneyAgent` in `backend/app/services/ai/agents/followup_journey_agent.py`**

Handle lifecycle nurturing (Day 0 welcome, Day 1 recommendations, Day 3 check-in, Day 7 follow-up) and post-visit scenarios: interested, 3 months future timeline, budget mismatch, not interested (opt-out), or human escalation.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_followup_journey_agent.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai/agents/followup_journey_agent.py backend/tests/test_ai_followup_journey_agent.py
git commit -m "feat(ai): implement agent 10 follow-up and agent 11 post-visit nurturing"
```

---

### Task 16: Asynchronous Background Scheduler & Cron Runners (`ai_scheduler.py`)

**Files:**
- Create: `backend/app/workers/ai_scheduler.py`
- Create: `backend/app/api/v1/endpoints/ai_cron.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_ai_scheduler.py`

**Interfaces:**
- Consumes: `FollowupJourneyAgent`, `NewPropertyAlertAgent`, `VoiceCallingAgent`, `AIAgentExecutionLog`
- Produces:
  - `run_nurturing_cycle(db: AsyncSession) -> dict`
  - `run_property_alert_queue(db: AsyncSession) -> dict`
  - `run_call_retry_cycle(db: AsyncSession) -> dict`
  - `run_pii_retention_purge(db: AsyncSession, retention_days: int = 90) -> dict`
  - Cron Endpoints: `POST /v1/ai/cron/nurturing-runner`, `POST /v1/ai/cron/property-alerts-runner`, `POST /v1/ai/cron/retention-purge`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_scheduler.py
import pytest
from datetime import datetime, timezone, timedelta
from app.workers.ai_scheduler import run_nurturing_cycle, run_pii_retention_purge
from app.models.leads import Lead
from app.models.ai_agents import AIAgentExecutionLog

@pytest.mark.asyncio
async def test_scheduler_nurturing_triggers_eligible_lead(db_session):
    # Lead created 3 days ago, eligible for Day 3 follow-up
    three_days_ago = datetime.now(timezone.utc) - timedelta(days=3, hours=1)
    lead = Lead(lead_id="OB-2026-SCHED01", full_name="Aman", mobile="9829011223", stage="CONTACTED", created_at=three_days_ago)
    db_session.add(lead)
    await db_session.commit()
    
    res = await run_nurturing_cycle(db_session)
    assert res["processed_leads"] >= 1

@pytest.mark.asyncio
async def test_pii_retention_purge_cleans_old_logs(db_session):
    # Log created 95 days ago
    old_date = datetime.now(timezone.utc) - timedelta(days=95)
    old_log = AIAgentExecutionLog(
        agent_name="whatsapp_agent", lead_id="OB-OLD", channel="WHATSAPP", mode="SHADOW",
        trigger_event="INCOMING", input_summary="Raw customer secret info", created_at=old_date
    )
    db_session.add(old_log)
    await db_session.commit()
    
    purge_res = await run_pii_retention_purge(db_session, retention_days=90)
    assert purge_res["purged_count"] >= 1
    
    await db_session.refresh(old_log)
    assert old_log.input_summary == "[PURGED_PER_PII_POLICY]"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_scheduler.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.workers.ai_scheduler'`

- [ ] **Step 3: Implement `app/workers/ai_scheduler.py` and `ai_cron.py` endpoints**

Implement:
1. `run_nurturing_cycle`: scans leads whose age / last activity matches Day 0, Day 1, Day 3, Day 7, Day 15, Day 30 cadences, verifies quiet hours and consent, and evaluates next action.
2. `run_call_retry_cycle`: finds failed/missed outbound calls and retries once outside quiet hours.
3. `run_pii_retention_purge`: locates logs older than 90 days and scrubs `input_summary`, `output_response`, and raw payload text per DPDP guidelines.
4. `ai_cron.py`: exposes API key protected cron webhook routes for external schedulers or background intervals.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_scheduler.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/workers/ai_scheduler.py backend/app/api/v1/endpoints/ai_cron.py backend/app/main.py backend/tests/test_ai_scheduler.py
git commit -m "feat(ai): implement async background scheduler and pii retention purge"
```

---

### Task 17: AI Agent Safety Control Center API & Admin Endpoints

**Files:**
- Create: `backend/app/api/v1/endpoints/ai_admin.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_ai_admin_api.py`

**Interfaces:**
- Consumes: `AIAgentConfig`, `AIApprovalQueue`, `AIAgentExecutionLog`, `CustomerConsent`
- Produces: REST Endpoints:
  - `GET /v1/ai/agents` - List all 13 agents with status and modes
  - `PATCH /v1/ai/agents/{agent_name}` - Toggle mode (`DISABLED`, `SHADOW`, `LIVE`) or update rate limits
  - `GET /v1/ai/approvals` - List pending HITL approvals
  - `POST /v1/ai/approvals/{id}/approve` - Execute staged approval action
  - `POST /v1/ai/approvals/{id}/reject` - Reject staged action
  - `GET /v1/ai/logs` - Query execution and shadow logs (with PII masking)
  - `POST /v1/ai/consent/opt-out` - Manual opt-out toggle

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ai_admin_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_get_ai_agents_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/v1/ai/agents")
        assert res.status_code == 200
        data = res.json()
        assert "agents" in data
        assert len(data["agents"]) >= 13
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_admin_api.py -q`
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Implement `ai_admin.py` and register router in `main.py`**

Provide full admin controls with authentication, permission checks, audit logging of configuration updates, PII masking in log inspection, and seed default configs for all 13 agents on first boot.

- [ ] **Step 4: Run test to verify it passes**

Run: `& "C:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe" backend/tests/test_ai_admin_api.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/ai_admin.py backend/app/main.py backend/tests/test_ai_admin_api.py
git commit -m "feat(ai): add ai agent admin control center and hitl endpoints"
```

---

### Task 18: Frontend - AI Agent Control Center, HITL Queue & Lead AI Tab

**Files:**
- Create: `frontend/src/pages/AIAgentHub.tsx`
- Create: `frontend/src/pages/AIApprovalsQueue.tsx`
- Modify: `frontend/src/layouts/AdminLayout.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/LeadDetail.tsx`
- Test: `frontend` build check

**Interfaces:**
- Consumes: `/v1/ai/agents`, `/v1/ai/approvals`, `/v1/ai/logs`
- Produces:
  - Agent Control Center page: grid of 13 agent cards with instant toggle switches (Live, Shadow, Disabled), hourly rate limit spinners, and log counters.
  - HITL Approvals Queue page: review table showing staged CRM actions with "Approve" and "Reject" buttons.
  - Lead Detail AI Tab: shows lead qualification insights, conversation history, and opt-in/opt-out status badges.

- [ ] **Step 1: Write/Update frontend components and route definitions**

Add `/admin/ai-agents` and `/admin/ai-approvals` routes in `App.tsx` and sidebar navigation links in `AdminLayout.tsx`.

- [ ] **Step 2: Implement `AIAgentHub.tsx` and `AIApprovalsQueue.tsx`**

Build responsive UI with real-time feedback, shadow mode warning badges, and safety toggles.

- [ ] **Step 3: Update `LeadDetail.tsx` to surface AI Qualification & Logs**

Add an "AI Assistant & History" section in the lead overview showing qualification temperature, requirement summary, and consent status.

- [ ] **Step 4: Run frontend build to verify zero compile or TypeScript errors**

Run: `npm --prefix frontend run build`
Expected: Build succeeds with exit code 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/AIAgentHub.tsx frontend/src/pages/AIApprovalsQueue.tsx frontend/src/layouts/AdminLayout.tsx frontend/src/App.tsx frontend/src/pages/LeadDetail.tsx
git commit -m "feat(ui): add ai agent control hub and hitl approval queue"
```

---

## Execution Self-Review

1. **Background Job / Scheduler:** Fully covered in Task 16 (`app/workers/ai_scheduler.py` and `POST /v1/ai/cron/*`) for Day 0/1/3/7/15/30 nurturing, property alert queue, call retries, and quiet hours.
2. **OCR/PDF Pipeline:** Fully covered in Task 9 (`ocr_service.py`) with `pypdf` buffer parsing and image OCR for scanned registry deeds.
3. **Named Telephony Provider & Pre-Dial TRAI Check:** Specified **Exotel** in Task 12 with explicit pre-dial gate checking quiet hours, DND consent verification, and shadow mode interception before network requests.
4. **Deterministic LLM Testing:** Defined `MockAIClientService` in Task 3 and wired it into all agent test tasks (Tasks 5, 6, 7, 8, 9, 12, 15) for zero-cost, reliable CI testing.
5. **Alembic Downgrade Reversibility:** Added `test_ai_migration_reversible.py` in Task 1 testing complete `upgrade("head")` and `downgrade("0010_add_soft_delete")`.
6. **Data Retention & PII Policy:** Formulated in Global Constraints, Task 2 (masking), and Task 16 (90-day automated purge of conversation content under DPDP guidelines).
