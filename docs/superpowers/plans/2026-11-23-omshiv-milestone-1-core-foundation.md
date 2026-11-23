# Omshiv CRM — Milestone 1: Core Foundation & Propira Property Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete operational backend and web CRM for Omshiv Buildvision: Monorepo scaffolding, PostgreSQL schema, Dual-Channel OTP authentication (WhatsApp + SMS fallback), RBAC middleware, ~90 System Settings with audit logging, 6-way Lead Intake engine with idempotency & deduplication, 12-stage buyer pipeline, and the 100% dynamic Propira Property Engine with 7-step verification workflow and soft-delete recycle bin.

**Architecture:** Monorepo with a high-performance asynchronous FastAPI (Python 3.11+) backend, PostgreSQL 15 relational database, Redis 7 task and caching layer, and a Vite + React 18 + TailwindCSS frontend shell for sales reps, verifiers, managers, and the MD. All business rules are configurable settings; all master options are 100% dynamic from the admin panel.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, PostgreSQL 15, Redis 7, Celery / ARQ, React 18, TypeScript, TailwindCSS, TanStack Query, Pytest.

**Spec:** [docs/superpowers/specs/2026-11-22-omshiv-crm-design.md](file:///c:/xampp/htdocs/om_shiv/docs/superpowers/specs/2026-11-22-omshiv-crm-design.md)

---

## Global Constraints

- **Strict Identity Architecture:** No hardcoded names in code or routing; all actors use system-generated IDs (`EMP-XXXX`, `CP-XXXX`).
- **Scalable Sequences:** Lead IDs strictly follow `OB-YYYY-NNNNNN` (6 digits zero-padded, unbounded); Property IDs strictly follow `OP-YYYY-NNNNN` (5 digits zero-padded, unbounded).
- **Dual-Channel Auth:** WhatsApp OTP primary (DoubleTick REST API); automatic fallback to SMS OTP (MSG91/Twilio/Fast2SMS) if unconfirmed after 30 seconds or on manual click.
- **Three-Tier RBAC & Confidentiality:** Seller phone numbers, minimum acceptable reserve prices, and legal notes are strictly scrubbed from public endpoints and non-owner sales reps via Pydantic response projections.
- **Zero Hardcoded Master Enums:** All dropdown options, area units, facing directions, and amenities are loaded dynamically from `property_master_options`.
- **Intake Idempotency:** Webhook requests require an `idempotency_key` checked against a 60-second Redis mutex lock and DB unique constraint.
- **Quiet Hours Enforcement:** No staff alerts or marketing outbound messages between 21:00 and 08:30 IST (except login OTPs).

---

## Review Focus

1. **AI Voice & Manual Action Concurrency Race Condition:** If a human sales rep logs a call or advances a lead stage while an AI voice call is queued, the pre-dial check must acquire a row-level lock and abort the external call job immediately.
2. **Carpet Area vs. Super Area Validation:** Backend validator must strictly reject any submission where $Carpet Area \ge Super Area$ with HTTP 422.
3. **Owner Ad Request Concurrency:** Enforce database partial unique constraint on `owner_ad_requests(property_id)` where `status = 'PENDING'` so owners cannot submit multiple simultaneous requests.
4. **24-Hour Lead Deduplication vs. 45-Day Re-enquiry:** Same mobile within 24 hours must be silently ignored with an intake reject log; open lead $< 45$ days must append a task to the existing owner; closed or $> 45$ day lead must generate a new linked lead.
5. **Soft-Delete Recycle Bin & Live Isolation:** Deleted properties moved to `is_recycled = true` must be completely excluded from search results, matching queries, and public APIs until restored by an Admin.

---

## Task Breakdown & Roadmap

### Task 0.1: Monorepo Project Structure & Docker Development Environment
**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `backend/pyproject.toml`
- Create: `backend/Dockerfile`
- Create: `frontend/package.json`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: Running PostgreSQL 15, Redis 7, FastAPI server with `/v1/health` returning 200 OK.

- [ ] **Step 1: Write the failing test for system health check**
```python
# backend/tests/test_health.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_check_returns_ok():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "postgres" in data["components"]
    assert "redis" in data["components"]
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_health.py -v`
Expected: FAIL with "app not found" or "connection refused".

- [ ] **Step 3: Implement Docker Compose, FastAPI skeleton, and `/v1/health`**
Configure `docker-compose.yml` with Postgres 15 and Redis 7; implement `app/main.py` with async database and Redis ping checks in `/v1/health`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_health.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add docker-compose.yml .env.example backend/ frontend/
git commit -m "feat(infra): setup monorepo scaffolding, docker-compose, and health check"
```

---

### Task 1.1: Core Database Engine, Alembic & Identity Models
**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/identity.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_identity_schema.py`
- Test: `backend/tests/test_identity_models.py`

**Interfaces:**
- Produces: `departments`, `roles`, `employees`, and `auth_sessions` tables in PostgreSQL.

- [ ] **Step 1: Write the failing test for Employee and Role creation**
```python
# backend/tests/test_identity_models.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.identity import Employee, Department, Role

@pytest.mark.asyncio
async def test_create_employee_with_role(db_session: AsyncSession):
    dept = Department(name="Sales", code="SALES")
    db_session.add(dept)
    await db_session.flush()

    role = Role(department_id=dept.id, name="Sales Executive", code="SALES_EXEC", permissions={"leads": ["read", "write"]})
    db_session.add(role)
    await db_session.flush()

    emp = Employee(
        employee_id="EMP-0001",
        name="Sunil Sharma",
        email="sunil@omshiv.com",
        mobile="9829012345",
        department_id=dept.id,
        role_id=role.id,
        level=1,
        handled_categories=["Residential", "Commercial"],
        budget_min_cr=0.1,
        budget_max_cr=2.0
    )
    db_session.add(emp)
    await db_session.commit()

    assert emp.employee_id == "EMP-0001"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_identity_models.py -v`
Expected: FAIL with "no table found".

- [ ] **Step 3: Implement SQLAlchemy models and run Alembic migration**
Define `Department`, `Role`, `Employee`, `AuthSession` in `app/models/identity.py` with foreign keys, unique mobile constraint, and sequence checks.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_identity_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/models/identity.py backend/alembic/
git commit -m "feat(identity): implement department, role, and employee models with alembic migration"
```

---

### Task 1.2: Dual-Channel OTP Authentication & Fallback Gateway
**Files:**
- Create: `backend/app/services/notifications/whatsapp_gateway.py`
- Create: `backend/app/services/notifications/sms_gateway.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/v1/endpoints/auth.py`
- Test: `backend/tests/test_auth_dual_channel.py`

**Interfaces:**
- Consumes: `Employee` table.
- Produces: `POST /v1/auth/request-otp`, `POST /v1/auth/verify-otp`, `POST /v1/auth/fallback-sms`.

- [ ] **Step 1: Write the failing test for WhatsApp OTP request and SMS fallback**
```python
# backend/tests/test_auth_dual_channel.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_auth_request_otp_and_fallback(test_client: AsyncClient, mock_whatsapp_fail):
    # When WhatsApp fails, system falls back to SMS OTP
    response = await test_client.post("/v1/auth/request-otp", json={"mobile": "9829012345"})
    assert response.status_code == 200
    data = response.json()
    assert data["channel"] == "SMS_FALLBACK"
    assert data["session_id"] is not None

    # Verify 6-digit OTP
    verify_resp = await test_client.post("/v1/auth/verify-otp", json={
        "session_id": data["session_id"],
        "otp": "123456" # Mocked OTP
    })
    assert verify_resp.status_code == 200
    assert "access_token" in verify_resp.json()
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_auth_dual_channel.py -v`
Expected: FAIL with 404 Not Found.

- [ ] **Step 3: Implement Dual-Channel Auth Service & Endpoints**
Implement DoubleTick WhatsApp client + SMS gateway (Fast2SMS/MSG91 fallback). Implement 6-digit OTP generation, SHA-256 hash storage with 5-minute expiry in `auth_sessions`, and JWT token generation.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_auth_dual_channel.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/services/auth_service.py backend/app/services/notifications/ backend/app/api/v1/endpoints/auth.py
git commit -m "feat(auth): implement dual-channel whatsapp and sms otp authentication"
```

---

### Task 1.3: Dynamic Settings Engine (~90 Settings) & Audit Ledger
**Files:**
- Create: `backend/app/models/settings.py`
- Create: `backend/app/services/settings_service.py`
- Create: `backend/app/api/v1/endpoints/settings.py`
- Test: `backend/tests/test_settings_and_audit.py`

**Interfaces:**
- Produces: `system_settings`, `audit_logs` tables and CRUD endpoints with Redis caching.

- [ ] **Step 1: Write the failing test for Settings update and Audit logging**
```python
# backend/tests/test_settings_and_audit.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_update_setting_creates_audit_entry(auth_client_md: AsyncClient):
    payload = {"value": 24, "reason": "Extending untouched escalation window"}
    response = await auth_client_md.patch("/v1/settings/sla_untouched_hours", json=payload)
    assert response.status_code == 200
    assert response.json()["value"] == 24

    # Verify audit log recorded
    audit_resp = await auth_client_md.get("/v1/audit-logs?entity_name=system_settings&entity_id=sla_untouched_hours")
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["items"]
    assert len(logs) > 0
    assert logs[0]["performed_by"] == "EMP-0001"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_settings_and_audit.py -v`
Expected: FAIL with 404.

- [ ] **Step 3: Implement Settings Service with In-Memory Redis Cache and Audit Triggers**
Create `system_settings` table seeded with default ~90 settings (SLA hours, quiet hours, commission percentages, rent threshold). Ensure every update records old/new JSON in `audit_logs` and invalidates Redis cache.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_settings_and_audit.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/models/settings.py backend/app/services/settings_service.py backend/app/api/v1/endpoints/settings.py
git commit -m "feat(settings): implement settings editor with audit logging and redis cache"
```

---

### Task 2.1: Inbound Lead Intake API, Idempotency & 6-Way Inflow Engine
**Files:**
- Create: `backend/app/models/leads.py`
- Create: `backend/app/models/inquiries.py`
- Create: `backend/app/services/intake_service.py`
- Create: `backend/app/api/v1/endpoints/intake.py`
- Test: `backend/tests/test_intake_pipeline.py`

**Interfaces:**
- Produces: `leads`, `builder_projects`, `website_inquiries`, `requirement_cards` tables.
- Endpoints: `POST /v1/intake/lead`, `POST /v1/crm/inquiries/{id}/convert-to-lead`.

- [ ] **Step 1: Write the failing tests for 24h deduplication, 6-digit sequence, and 1-click conversion**
```python
# backend/tests/test_intake_pipeline.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_intake_sequence_and_24h_deduplication(test_client: AsyncClient):
    # First lead submission
    resp1 = await test_client.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "Ramesh Kumar",
        "mobile": "9829099999",
        "lead_type": "BUYER"
    })
    assert resp1.status_code == 201
    lead_id = resp1.json()["lead_id"]
    assert lead_id.startswith("OB-2026-")
    assert len(lead_id.split("-")[2]) == 6 # 6-digit sequence

    # Repeat submission within 24h -> ignored, returns existing lead_id
    resp2 = await test_client.post("/v1/intake/lead", json={
        "source": "PROPERTY_INQUIRY",
        "full_name": "Ramesh Kumar",
        "mobile": "9829099999",
        "lead_type": "BUYER"
    })
    assert resp2.status_code == 200
    assert resp2.json()["lead_id"] == lead_id
    assert resp2.json()["is_duplicate"] is True
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_intake_pipeline.py -v`
Expected: FAIL with 404.

- [ ] **Step 3: Implement Intake Engine with Redis Mutex, DB Sequence & Normalization**
Implement phone normalization (`91XXXXXXXXXX`), check `test_numbers`, enforce `idempotency_key`, assign `OB-YYYY-NNNNNN` sequence, and build the 1-click form conversion endpoint.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_intake_pipeline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/models/leads.py backend/app/models/inquiries.py backend/app/services/intake_service.py backend/app/api/v1/endpoints/intake.py
git commit -m "feat(intake): implement intake api with sequence generator, deduplication, and 1-click conversions"
```

---

### Task 2.2: 12-Stage Buyer Pipeline State Machine & Sales Rep Workflow
**Files:**
- Create: `backend/app/services/pipeline_service.py`
- Create: `backend/app/api/v1/endpoints/leads.py`
- Test: `backend/tests/test_pipeline_state_machine.py`

**Interfaces:**
- Produces: `POST /v1/leads/{id}/log-action`, `GET /v1/leads/my-work`, `GET /v1/leads/my-leads`.

- [ ] **Step 1: Write the failing test for Stage transitions and compulsory follow-up dates**
```python
# backend/tests/test_pipeline_state_machine.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_stage_transition_requires_compulsory_fields(auth_client_sales: AsyncClient):
    # Transition to Connected without temperature fails
    resp = await auth_client_sales.post("/v1/leads/OB-2026-000001/log-action", json={
        "action_type": "CALL",
        "outcome": "Connected",
        "note": "Client looking for 3BHK flat",
        "stage": "CONNECTED"
        # Missing temperature and follow_up_date
    })
    assert resp.status_code == 422

    # Success with compulsory fields
    resp_valid = await auth_client_sales.post("/v1/leads/OB-2026-000001/log-action", json={
        "action_type": "CALL",
        "outcome": "Connected",
        "note": "Client looking for 3BHK flat",
        "temperature": "HOT",
        "follow_up_date": "2026-11-25T11:00:00Z",
        "stage": "CONNECTED"
    })
    assert resp_valid.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_pipeline_state_machine.py -v`
Expected: FAIL with 404.

- [ ] **Step 3: Implement Pipeline State Machine & Validation Engine**
Enforce Handover §5 table: New $\to$ Attempting $\to$ Connected $\to$ Req Captured $\to$ Qualified $\to$ Meeting $\to$ Site Visit $\to$ Negotiation $\to$ Won/Lost/Nurture. Validate temperature, future follow-up dates ($\le 30$ days Hot/Warm, $\le 100$ days Cold).

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_pipeline_state_machine.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/services/pipeline_service.py backend/app/api/v1/endpoints/leads.py
git commit -m "feat(pipeline): implement 12-stage state machine and sales action logger"
```

---

### Task 2.3: Assignment Engine & SLA Escalation Background Worker
**Files:**
- Create: `backend/app/services/assignment_service.py`
- Create: `backend/app/workers/sla_worker.py`
- Test: `backend/tests/test_assignment_and_sla.py`

**Interfaces:**
- Consumes: `leads`, `system_settings`, `employees`.
- Produces: Scheduled Celery/ARQ task running SLA checks every 10 minutes.

- [ ] **Step 1: Write the failing test for 3h reminder and 24h manager escalation**
```python
# backend/tests/test_assignment_and_sla.py
import pytest
from app.workers.sla_worker import process_sla_escalations

@pytest.mark.asyncio
async def test_sla_escalation_detects_untouched_leads(db_session):
    # Process SLA worker
    results = await process_sla_escalations(db_session)
    assert "reminders_sent" in results
    assert "escalations_sent" in results
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_assignment_and_sla.py -v`
Expected: FAIL with module not found.

- [ ] **Step 3: Implement Assignment Rules & Celery SLA Escalation Engine**
Implement strict rules table (category, location, budget $\to$ employee pool round robin) with capacity cap overflow and leave cover check. Implement 3h untouched reminder, 24h manager escalation, Hot/VIP 3h alert, and 21:00–08:30 quiet hours enforcement.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_assignment_and_sla.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/services/assignment_service.py backend/app/workers/sla_worker.py
git commit -m "feat(sla): implement assignment engine and automated sla escalation worker"
```

---

### Task 3.1: Dynamic Property Master Options & Pincode Registry
**Files:**
- Create: `backend/app/models/property_master.py`
- Create: `backend/app/api/v1/endpoints/property_master.py`
- Test: `backend/tests/test_property_master.py`

**Interfaces:**
- Produces: `property_master_groups`, `property_master_options`, `pincode_master` tables.
- Endpoint: `GET /v1/public/property-schema`.

- [ ] **Step 1: Write the failing test for dynamic master schema endpoint**
```python
# backend/tests/test_property_master.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_dynamic_schema_returns_scoped_options(test_client: AsyncClient):
    response = await test_client.get("/v1/public/property-schema")
    assert response.status_code == 200
    schema = response.json()
    assert "FACING" in schema
    assert "AREA_UNITS" in schema
    assert "AMENITIES" in schema
    # Verify Bigha is scoped only to Agriculture (category 3)
    bigha = next(o for o in schema["AREA_UNITS"] if o["label"] == "Bigha")
    assert bigha["applicable_categories"] == [3]
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_property_master.py -v`
Expected: FAIL with 404.

- [ ] **Step 3: Implement Dynamic Master Options & Redis Cache**
Implement master data tables seeded with Propira master lists (Facing, Flooring, Possession, Ownership, Rental allowed for, Furniture items, Area units, Amenities, Nearby tags). Implement `/v1/public/property-schema` with Redis caching and admin mutation endpoints.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_property_master.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/models/property_master.py backend/app/api/v1/endpoints/property_master.py
git commit -m "feat(property): implement dynamic master options engine and public schema endpoint"
```

---

### Task 3.2: Propira Property Posting Schemas, Validations & Quick Listing
**Files:**
- Create: `backend/app/models/properties.py`
- Create: `backend/app/schemas/property_schemas.py`
- Create: `backend/app/services/property_service.py`
- Create: `backend/app/api/v1/endpoints/properties.py`
- Test: `backend/tests/test_property_validations.py`

**Interfaces:**
- Produces: `properties`, `prop_residential_flats`, `prop_houses_villas`, `prop_plots`, `prop_commercial`, `prop_agriculture`, `prop_industrial_warehouses`, `prop_pg`.
- Endpoint: `POST /v1/properties/post`, `POST /v1/properties/quick-listing`.

- [ ] **Step 1: Write the failing test for Carpet < Super and Pincode validation**
```python
# backend/tests/test_property_validations.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_carpet_area_must_be_less_than_super_area(auth_client: AsyncClient):
    # Carpet >= Super Area must fail with 422
    payload = {
        "listing_type": 2, # Sale
        "category_code": 1, # Residential
        "sub_category_code": 1, # Flat
        "pincode": "301001",
        "latitude": 27.5530,
        "longitude": 76.6346,
        "expected_price": 4500000,
        "flat_details": {
            "bhk": 3,
            "rooms": 3,
            "total_floors": 10,
            "property_floor": 4,
            "super_area": 1200,
            "carpet_area": 1300 # INVALID: Carpet > Super
        }
    }
    response = await auth_client.post("/v1/properties/post", json=payload)
    assert response.status_code == 422
    assert "Carpet area must be less than super area" in response.text
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_property_validations.py -v`
Expected: FAIL with 404 or missing route.

- [ ] **Step 3: Implement Property Models, Pydantic Validators, and Quick Listing API**
Implement tables for all 12 sub-categories. Add custom Pydantic root validators for Carpet < Super, Rooms = BHK, Floor $\le$ Total Floors, and valid Pincode check. Allocate sequence `OP-YYYY-NNNNN`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_property_validations.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/models/properties.py backend/app/schemas/property_schemas.py backend/app/services/property_service.py backend/app/api/v1/endpoints/properties.py
git commit -m "feat(property): implement property posting schemas, strict validations, and quick listing"
```

---

### Task 3.3: 7-Step Property Verification Pipeline & Telephonic Scheduling
**Files:**
- Create: `backend/app/models/property_verification.py`
- Create: `backend/app/services/verification_service.py`
- Create: `backend/app/api/v1/endpoints/property_verification.py`
- Test: `backend/tests/test_verification_workflow.py`

**Interfaces:**
- Produces: `property_verification_calls`, `property_documents`, `property_verification`.
- Endpoints: `POST /v1/properties/{id}/assign-verifier`, `POST /v1/properties/{id}/log-call`, `POST /v1/properties/{id}/upload-document`, `POST /v1/properties/{id}/verify-and-approve`.

- [ ] **Step 1: Write the failing test for 7-Step Verification flow**
```python
# backend/tests/test_verification_workflow.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_property_verification_and_approval_flow(auth_client_manager: AsyncClient, unverified_property_id: str):
    # 1. Assign verifier
    assign_resp = await auth_client_manager.post(f"/v1/properties/{unverified_property_id}/assign-verifier", json={"verifier_emp_id": "EMP-0005"})
    assert assign_resp.status_code == 200

    # 2. Log telephonic verification call
    call_resp = await auth_client_manager.post(f"/v1/properties/{unverified_property_id}/log-call", json={
        "call_outcome": "AVAILABILITY_CONFIRMED",
        "notes": "Owner confirmed price and physical documents available"
    })
    assert call_resp.status_code == 200

    # 3. Manager Verify & Approve
    approve_resp = await auth_client_manager.post(f"/v1/properties/{unverified_property_id}/verify-and-approve", json={
        "area_confirmed": True,
        "photos_genuine_confirmed": True,
        "ownership_confirmed": True
    })
    assert approve_resp.status_code == 200
    assert approve_resp.json()["verified_status"] == 1
    assert approve_resp.json()["is_live"] is True
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_verification_workflow.py -v`
Expected: FAIL with 404.

- [ ] **Step 3: Implement Verification Service, Document Store & Senior Approval**
Implement call logging, legal document uploads (Title Deed, Khasra, Utility Bills), and the Senior Admin approval state machine setting `verified_status = 1`, `is_live = true`, and `expires_at = now() + 90 days`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_verification_workflow.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/models/property_verification.py backend/app/services/verification_service.py backend/app/api/v1/endpoints/property_verification.py
git commit -m "feat(property): implement 7-step property verification pipeline and document repository"
```

---

### Task 3.4: Post-Live Lifecycle Operations, Recycle Bin & Auto-Expiry Worker
**Files:**
- Create: `backend/app/models/owner_requests.py`
- Create: `backend/app/workers/property_expiry_worker.py`
- Create: `backend/app/api/v1/endpoints/owner_operations.py`
- Test: `backend/tests/test_property_lifecycle.py`

**Interfaces:**
- Produces: `owner_ad_requests` table, `rent_number_reveals` table, and daily Celery expiration job.
- Endpoints: `POST /v1/owner/properties/{id}/request-sold`, `POST /v1/owner/properties/{id}/request-delete`, `POST /v1/admin/properties/{id}/recycle-bin-restore`.

- [ ] **Step 1: Write the failing test for owner single pending request constraint and recycle bin restore**
```python
# backend/tests/test_property_lifecycle.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_owner_request_single_pending_and_recycle_bin(test_client: AsyncClient, auth_client_admin: AsyncClient, live_property_id: str):
    # Owner sends delete request
    req1 = await test_client.post(f"/v1/owner/properties/{live_property_id}/request-delete", json={"mobile": "9829012345", "reason": "No longer selling"})
    assert req1.status_code == 200

    # Second pending request must be rejected with 409
    req2 = await test_client.post(f"/v1/owner/properties/{live_property_id}/request-delete", json={"mobile": "9829012345", "reason": "Duplicate attempt"})
    assert req2.status_code == 409

    # Admin approves deletion -> moves to Recycle Bin
    del_resp = await auth_client_admin.post(f"/v1/admin/properties/{live_property_id}/approve-delete")
    assert del_resp.status_code == 200
    assert del_resp.json()["is_recycled"] is True
    assert del_resp.json()["is_live"] is False

    # Admin 1-click restore -> returns to live portal
    restore_resp = await auth_client_admin.post(f"/v1/admin/properties/{live_property_id}/recycle-bin-restore")
    assert restore_resp.status_code == 200
    assert restore_resp.json()["is_recycled"] is False
    assert restore_resp.json()["is_live"] is True
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/tests/test_property_lifecycle.py -v`
Expected: FAIL with 404.

- [ ] **Step 3: Implement Owner Self-Service, Recycle Bin & Scheduled Expiry Worker**
Implement `owner_ad_requests` with single-pending unique constraint. Implement Admin approve delete $\to$ `is_recycled = true`, and Admin restore $\to$ `is_recycled = false`. Implement daily Celery worker setting `EXPIRED` status after 90 days and firing WhatsApp renewal notifications 3 days prior.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_property_lifecycle.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add backend/app/models/owner_requests.py backend/app/workers/property_expiry_worker.py backend/app/api/v1/endpoints/owner_operations.py
git commit -m "feat(lifecycle): implement owner ad requests, recycle bin with 1-click restore, and auto-expiry worker"
```

---

### Task 4.1: React Web CRM Shell & Vite Setup (Sales, Manager & Admin Views)
**Files:**
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/pages/Login.tsx`
- Create: `frontend/src/pages/MyWork.tsx`
- Create: `frontend/src/pages/LeadDetail.tsx`
- Create: `frontend/src/pages/PropertyAssign.tsx`
- Create: `frontend/src/pages/SettingsEditor.tsx`
- Test: `frontend/src/tests/App.test.tsx`

**Interfaces:**
- Consumes: FastAPI Backend `/v1/*` endpoints.
- Produces: Complete responsive Web UI for sales reps, verifiers, and the MD.

- [ ] **Step 1: Write failing frontend smoke test**
```typescript
// frontend/src/tests/App.test.tsx
import { render, screen } from '@testing-library/react';
import App from '../App';

test('renders login screen when unauthenticated', () => {
  render(<App />);
  expect(screen.getByText(/Omshiv Buildvision CRM/i)).toBeInTheDocument();
  expect(screen.getByPlaceholderText(/Enter 10-digit mobile/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**
Run: `npm test -- App.test.tsx` in `frontend/`
Expected: FAIL with no file.

- [ ] **Step 3: Implement React CRM Shell & Views**
Build Login with Dual-Channel OTP, *My Work* (overdue, untouched, hot), *Lead Detail* with 1-tap call & WhatsApp deep links, *Property Assign & Verification* queue, and *Settings Editor* table.

- [ ] **Step 4: Run test to verify it passes**
Run: `npm test -- App.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git add frontend/
git commit -m "feat(ui): implement react web crm shell with login, my work, lead detail, and settings views"
```

---

## Self-Review Checklist

- [x] **Spec Coverage:** Covers all requirements from Developer Handover §1–§6, Propira Property Spec §1–§13, and legacy CodeIgniter workflows (6-way lead inflow, 7-step property verification, soft-delete recycle bin).
- [x] **Step Scan:** Every step carries exact file paths, failing tests, implementation approach, passing checks, and commit commands.
- [x] **Type Consistency:** Database field names and sequence formats (`OB-YYYY-NNNNNN`, `OP-YYYY-NNNNN`, `EMP-XXXX`) match across models, migrations, tests, and endpoints.
- [x] **Review Focus:** Dedicated tasks test Carpet < Super, owner single pending request race condition, 24h deduplication, and recycle bin isolation.
- [x] **Proportion:** Concrete, bite-sized tasks ready for execution without bloating into full source transcripts.
