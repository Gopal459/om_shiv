# Lead Create Form: Assign Staff, Customer Type & Reference Details Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional Assign Staff select dropdown, Customer Type (`USER` / `INVESTOR` / `BROKER`), and Reference Details (`Client` / `Relative` / `Employee`, name, mobile) across the Lead database schema, FastAPI API, `CreateLeadModal`, and `LeadDetail`.

**Architecture:** Extend `Lead` and `TblLead` with `customer_type` via an idempotent migration, expose `GET /v1/leads/assignees` and extended `POST /v1/leads/create` + `GET /v1/leads/{id}` payloads in `leads.py`, then wire live staff loading, bold Assign Staff select box, Customer Type buttons, and Reference fields into `CreateLeadModal.tsx` and display them in `LeadDetail.tsx`.

**Tech Stack:** FastAPI, SQLAlchemy (async), Pydantic v2, pytest, React 18, TypeScript, Tailwind CSS, Vite.

**Spec:** `docs/superpowers/specs/2026-11-28-lead-create-staff-customer-reference-design.md`

## Global Constraints
- `customer_type` allowed values: `USER`, `INVESTOR`, `BROKER` (case-insensitive input normalized to uppercase; default `USER`); `BROKER` sets `TblLead.dealer_have = 1`, `USER` / `INVESTOR` set `TblLead.dealer_have = 2` on manual create.
- `reference_type` allowed values when provided: `Client`, `Relative`, `Employee` (case-insensitive input normalized to Title Case; optional/nullable).
- `assigned_to` is optional (`null` or empty string leaves lead unassigned with `Lead.assigned_to = None`, `TblLead.assign_franchstaff_id = 0`).
- New migration uses the codebase's idempotent SQLite (`PRAGMA table_info`) + PostgreSQL (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`) pattern and is registered in `MIGRATION_STEPS`.
- Verification runs `pytest` via `c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe` and `npm --prefix c:\xampp\htdocs\om_shiv\frontend run build`.

## Review Focus
1. Empty/omitted `assigned_to` (`""` or `null`) creates an unassigned lead cleanly without error.
2. Unknown or inactive `assigned_to` rejects `POST /v1/leads/create` with HTTP `400` and creates zero rows in `leads` / `tbl_leads`.
3. Invalid `customer_type` or invalid `reference_type` returns HTTP `422`, while omitting them uses defaults (`USER`, `None`).
4. Route ordering keeps `GET /v1/leads/assignees` separate from `GET /v1/leads/{id}` (must return `200` list, never `404 Lead 'assignees' not found`).
5. Trimming & normalization handle whitespace-only strings and messy phone numbers (`+91 98290-12345`) in Reference fields cleanly, and `GET /v1/leads/{id}` returns both `customer_type` and `reference_relation_by`.

---

### Task 1: Schema, Migration & Leads API Support

**Files:**
- Create: `backend/app/db/migrations/0014_lead_customer_type.py`
- Modify: `backend/app/db/migrations/runner.py:10-25`
- Modify: `backend/app/models/leads.py:33-38,165-169`
- Modify: `backend/app/api/v1/endpoints/leads.py:86-168,280-345,773-860`
- Test: `backend/tests/test_lead_inflow_and_kanban.py`

**Interfaces:**
- Produces:
  - `Lead.customer_type: str` and `TblLead.customer_type: str` (`DEFAULT 'USER'`)
  - `GET /v1/leads/assignees -> List[{employee_id, name, role_name, role_code, is_active}]`
  - `POST /v1/leads/create` accepting `LeadCreateManual` (`assigned_to`, `customer_type`, `reference_type`, `refer_by_name`, `refer_by_mobile`) and returning `customer_type`, `assigned_to`, `reference_relation_by`, `refer_by_name`, `refer_by_mobile`
  - `GET /v1/leads/{id}` (`LeadDetailResponse`) including `customer_type: str = "USER"` and `reference_relation_by: Optional[str] = None`

- [ ] **Step 1: Write failing tests in `backend/tests/test_lead_inflow_and_kanban.py`**

Add tests covering:
- `test_lead_assignees_endpoint_and_route_ordering(auth_client_md, db_session)`: ensures `GET /v1/leads/assignees` returns `200` with `EMP-0001`, omits inactive employees, and is not captured by `GET /v1/leads/{id}`.
- `test_manual_lead_create_with_staff_customer_type_and_reference(auth_client_md, db_session)`: creates a Broker lead assigned to `EMP-0001` with `reference_type="relative"`, `refer_by_name="  Suresh Sharma  "`, `refer_by_mobile="98290-55555"`, asserts `customer_type == "BROKER"`, `dealer_have == 1`, `assigned_to == "EMP-0001"`, `reference_relation_by == "Relative"`, and verifies `GET /v1/leads/{lead_uid}` returns all persisted fields; also creates an Investor lead with `assigned_to: ""` (optional/unassigned) and asserts `assigned_to is None` and `dealer_have == 2`.
- `test_manual_lead_create_validation_and_invalid_assignee(auth_client_md)`: verifies HTTP `400` on unknown/inactive `assigned_to` (and zero rows inserted), and HTTP `422` on invalid `customer_type` or `reference_type`.

- [ ] **Step 2: Run targeted pytest to verify FAIL**

Run: `c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe c:\xampp\htdocs\om_shiv\backend\tests\test_lead_inflow_and_kanban.py -v`
Expected: FAIL on missing `/v1/leads/assignees` and missing `customer_type` / `assigned_to` / `reference_relation_by` fields.

- [ ] **Step 3: Add `customer_type` column & idempotent migration `0014_lead_customer_type.py`**

- Update `Lead` and `TblLead` in `backend/app/models/leads.py` with `customer_type: Mapped[str] = mapped_column(String(32), default="USER", nullable=False)`.
- Create `backend/app/db/migrations/0014_lead_customer_type.py` with idempotent `COLUMN_ADDITIONS` for `leads` and `tbl_leads`, and register `"app.db.migrations.0014_lead_customer_type"` in `MIGRATION_STEPS` in `backend/app/db/migrations/runner.py`.

- [ ] **Step 4: Implement assignees endpoint & extended create/detail schemas in `backend/app/api/v1/endpoints/leads.py`**

- Add `CustomerType` / `ReferenceType` validation in `LeadCreateManual` (`assigned_to: Optional[str] = None`, `customer_type: str = "USER"`, `reference_type: Optional[str] = None`, `refer_by_name: Optional[str] = None`, `refer_by_mobile: Optional[str] = None`), normalizing whitespace-only strings to `None`.
- Add `@router.get("/assignees")` before `@router.get("/{id}")` returning active non-deleted `Employee` rows ordered by `Employee.name.asc()` with `Employee.role` eager-loaded.
- In `create_manual_lead`: when `assigned_to` is non-empty, lookup active non-deleted `Employee` (raise `HTTPException(400)` if missing); set `Lead.assigned_to = emp.employee_id`, `TblLead.assign_franchstaff_id = emp.id`, `TblLead.assignfranchiseestaff_date = now`. Set `customer_type` on both models, sync `TblLead.dealer_have = 1 if customer_type == "BROKER" else 2`, and set `TblLead.reference_relation_by`, `refer_by_name`, `refer_by_mobile`.
- Add `customer_type` and `reference_relation_by` to `LeadDetailResponse` and `build_lead_detail_dict`.

- [ ] **Step 5: Run pytest and verify PASS**

Run: `c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe c:\xampp\htdocs\om_shiv\backend\tests\test_lead_inflow_and_kanban.py -v`
Expected: PASS (9/9).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/leads.py backend/app/db/migrations/0014_lead_customer_type.py backend/app/db/migrations/runner.py backend/app/api/v1/endpoints/leads.py backend/tests/test_lead_inflow_and_kanban.py
git commit -m "feat(leads): support assign_to, customer_type, and reference details on manual lead creation"
```

---

### Task 2: Frontend `CreateLeadModal` & `LeadDetail` UI

**Files:**
- Modify: `frontend/src/components/leads/CreateLeadModal.tsx`
- Modify: `frontend/src/pages/LeadDetail.tsx`

**Interfaces:**
- Consumes from Task 1:
  - `GET /v1/leads/assignees` → `Array<{ employee_id: string; name: string; role_name?: string | null }>`
  - `POST /v1/leads/create` payload (`assigned_to`, `customer_type`, `reference_type`, `refer_by_name`, `refer_by_mobile`)
  - `GET /v1/leads/{id}` response (`customer_type`, `reference_relation_by`, `refer_by_name`, `refer_by_mobile`, `assigned_to`)

- [ ] **Step 1: Update `CreateLeadModal.tsx` with Customer Type, bold Assign Staff select box, and Reference Details**

- Fetch `/v1/leads/assignees` when `isOpen` is true (non-blocking if unauthenticated/empty, resetting form fields on submit success).
- Add **Customer Type** segmented selector (`USER` → `User`, `INVESTOR` → `Investor`, `BROKER` → `Broker`, default `USER`).
- Add a prominent, bold-styled **Assign Staff (Optional)** `<select>` dropdown (`font-bold`, highlighted border/ring) with default `"Om Shiv Central Desk (Unassigned)"` and dynamic employee options (`name (role_name || employee_id)`).
- Add **Reference Details (Optional)** grouped block with **Reference Type** `<select>` (`""` Optional, `Client`, `Relative`, `Employee`), **Reference Name** input, and **Reference Mobile** input.
- Include `assigned_to: assignedTo || null`, `customer_type: customerType`, `reference_type: referenceType || null`, `refer_by_name: referByName.trim() || null`, `refer_by_mobile: referByMobile.trim() || null` in the `POST /v1/leads/create` payload.

- [ ] **Step 2: Display Customer Type & Reference Type in `LeadDetail.tsx`**

- Update hero & Client card customer badge in `LeadDetail.tsx` to show `BROKER` / `INVESTOR` / `USER` label (`lead.customer_type`, falling back to `lead.dealer_have === 1 ? 'Broker / Dealer' : 'Customer'`).
- Display `lead.reference_relation_by` pill/prefix alongside `lead.refer_by_name` and `lead.refer_by_mobile` in Client & Contact Referral Info.

- [ ] **Step 3: Run frontend TypeScript & Vite build verification**

Run: `npm --prefix c:\xampp\htdocs\om_shiv\frontend run build`
Expected: PASS (`tsc && vite build` exit code `0`, zero TS errors).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/leads/CreateLeadModal.tsx frontend/src/pages/LeadDetail.tsx
git commit -m "feat(frontend): add Assign Staff, Customer Type, and Reference Details to CreateLeadModal"
```
