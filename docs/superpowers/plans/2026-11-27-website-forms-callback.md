# Website Forms (Request A Callback & Report A Problem) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete, dynamic **Website Forms** CRM module (`Request A Callback` and `Report A Problem`) with round-robin `TELECALLER` assignment, `WEB{id}` tracking IDs, follow-up reschedule audit history, `lead_open` locking, disqualification workflows, Lead + `TblLead` conversion, Excel `.xls` export, and AlwarMap-themed React master-detail UI.

**Architecture:** Async SQLAlchemy models (`TblCallback`, `CallbackRescheduleLog`, `CallbackActivity`, plus extended triage columns on `WebsiteInquiry`) backed by modular FastAPI service/router layers (`callback_service.py`, `problem_service.py`, `callbacks.py`, `problems.py`, synced with `intake.py`) and a dedicated React workspace (`WebsiteFormsHub.tsx` + `ReportProblemPanel.tsx`) wired into `AdminLayout.tsx` and `App.tsx`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async SQLite + PostgreSQL), Pytest + httpx, React 18, TypeScript, Tailwind CSS (AlwarMap `#291BB0` / `#F04B42`), Vite.

**Spec:** [docs/superpowers/specs/2026-11-27-website-forms-callback-design.md](file:///c:/xampp/htdocs/om_shiv/docs/superpowers/specs/2026-11-27-website-forms-callback-design.md)

## Global Constraints
- `lead_unique_id` format is strictly `f"WEB{callback_id}"` assigned immediately after flush.
- Round-robin queries active `Employee` joined with `Role.code == "TELECALLER"` (`is_active == True`, `is_on_leave == False`, `deleted_at IS NULL`); zero active telecallers falls back safely to `assigned_user_id = None` (never fails public form submission).
- Status codes: `0=New`, `1=In Progress`, `2=Disqualified` (requires `disqualified_reason` in `1..7`, auto-sets `lead_open=0`), `3=Solved` (auto-sets `lead_open=0`), `4=Qualified`, `5=Converted to Lead` (auto-sets `lead_open=0`, `lead_converted=1`), `6=Converted Property` (terminal status tag/tab only, auto-sets `lead_open=0`, `lead_converted=1`).
- Exact error copy on lock/date validation failures: `"This Callback is closed so you cannot reschedule it."` and `"Schedule Date and Time should be greater than the current date and time."`.
- Excel export generates zero-dependency `.xls` HTML-table workbooks (`application/vnd.ms-excel`) with HTML-escaped cell values.
- All Admin UI buttons, active tabs, and modals use AlwarMap palette (`#291BB0` primary, `#F04B42` accent/danger).

## Review Focus
1. **Zero Active Telecallers on Intake:** Public `POST /v1/intake/callback` submitted when zero `TELECALLER` staff exist must succeed (`201 Created`) with `assigned_user_id=None`, `"Received"` activity logged, and `WEB{id}` set.
2. **Naive vs Aware Datetimes & IST Day Boundaries:** Calling `/reschedule` with a naive ISO string or past timestamp must normalize cleanly to UTC (avoiding SQLite `TypeError: can't compare offset-naive and offset-aware datetimes`), reject past/current times, and evaluate `today_calls` / `missing_calls` using IST (`UTC+05:30`) boundaries.
3. **Lock & Terminal State Bypass Attempts:** Calling `/reschedule`, `/transfer`, `/status`, or `/convert-to-lead` while `lead_open == 0` must return `400`; calling `/reopen` on `lead_status IN (5, 6)` must return `400`; calling `/status` with `lead_status=5` directly must return `400`.
4. **Dual Conversion Prevention Across Tables:** Submitting `POST /v1/intake/inquiry` with `inquiry_type="CALLBACK"` creates linked `WebsiteInquiry` + `TblCallback` (`website_inquiry_id`). Converting either side must lock/mark converted on both sides so a second conversion via the other endpoint returns `400`.
5. **Spreadsheet Injection / XSS in `.xls` Export & Unauthorized Access:** Calling any `/v1/callbacks*` or `/v1/problems*` endpoint without a valid Bearer token returns `401`; exporting customer messages containing `<script>` or HTML characters escapes entities cleanly in `.xls` output.

---

### Task 1: Callback & Problem Triage Data Models + Migration `0013`

**Files:**
- Create: `backend/app/models/callbacks.py`
- Modify: `backend/app/models/inquiries.py:22-55`
- Modify: `backend/app/models/__init__.py:1-45`
- Create: `backend/app/db/migrations/0013_website_forms_callback_schema.py`
- Modify: `backend/app/db/migrations/runner.py:10-24`
- Test: `backend/tests/test_callbacks_and_problems_api.py`

**Interfaces:**
- Produces:
  - Constants in `app.models.callbacks`: `CALLBACK_STATUSES: Dict[int, str]`, `DISQUALIFIED_REASONS: Dict[int, str]`, `PROBLEM_STATUSES: Tuple[str, ...]`, `CURRENT_UPDATE_OPTIONS: List[str]`
  - Models in `app.models.callbacks`: `TblCallback`, `CallbackRescheduleLog`, `CallbackActivity`
  - Extended `WebsiteInquiry` fields: `status`, `assigned_to`, `related_property_code`, `resolution_remark`, `resolved_by`, `resolved_at`, `updated_at`
  - Idempotent `upgrade(engine: AsyncEngine) -> None` in `0013_website_forms_callback_schema.py`

- [ ] **Step 1: Write failing schema & model tests**

Create `backend/tests/test_callbacks_and_problems_api.py` with async tests verifying model persistence and migration columns:
```python
import pytest
from sqlalchemy import text
from app.models.callbacks import (
    TblCallback,
    CallbackRescheduleLog,
    CallbackActivity,
    CALLBACK_STATUSES,
    DISQUALIFIED_REASONS,
)
from app.models.inquiries import WebsiteInquiry


@pytest.mark.asyncio
async def test_callback_models_and_defaults(db_session):
    assert CALLBACK_STATUSES[0] == "New"
    assert CALLBACK_STATUSES[6] == "Converted Property"
    assert DISQUALIFIED_REASONS[1] == "Inaccurate Data"
    assert len(DISQUALIFIED_REASONS) == 7

    cb = TblCallback(name="Rohan", mobile_number="9829011223", phone_code="+91", message="Call me")
    db_session.add(cb)
    await db_session.flush()
    cb.lead_unique_id = f"WEB{cb.callback_id}"
    await db_session.commit()
    await db_session.refresh(cb)

    assert cb.lead_unique_id == f"WEB{cb.callback_id}"
    assert cb.lead_status == 0
    assert cb.calls_status == 0
    assert cb.lead_open == 1
    assert cb.disqualified_reason == 0
    assert cb.lead_converted == 0

    inq = WebsiteInquiry(inquiry_type="PROBLEM_REPORT", full_name="Amit", mobile="919829000111")
    db_session.add(inq)
    await db_session.commit()
    await db_session.refresh(inq)
    assert inq.status == "NEW"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_callbacks_and_problems_api.py::test_callback_models_and_defaults -v` (from `c:\xampp\htdocs\om_shiv`)
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.callbacks'`.

- [ ] **Step 3: Implement models (`callbacks.py`, `inquiries.py`, `models/__init__.py`) and migration `0013`**

1. Create `backend/app/models/callbacks.py` defining:
   - `CALLBACK_STATUSES` (`0..6`), `DISQUALIFIED_REASONS` (`1..7`), `CURRENT_UPDATE_OPTIONS` (`["Interested", "Call Back Later", "Site Visit Planned", "Price Discussion", "Shared Details on WhatsApp", "Ringing / Follow-Up"]`), `PROBLEM_STATUSES = ("NEW", "IN_REVIEW", "RESOLVED", "REJECTED")`.
   - `TblCallback(__tablename__ = "tbl_callback")` with exact columns from Spec §4.1 (including `website_inquiry_id` FK `website_inquiries.id`, `deleted_at`, `created_date`, `modified_date`) and relationships `reschedule_logs` + `activities` (`cascade="all, delete-orphan"`).
   - `CallbackRescheduleLog(__tablename__ = "tbl_leadreschedule_followup")` with Spec §4.2 columns.
   - `CallbackActivity(__tablename__ = "tbl_callback_activities")` with Spec §4.3 columns.
2. Extend `WebsiteInquiry` in `backend/app/models/inquiries.py` with `status` (`default="NEW"`), `assigned_to`, `related_property_code`, `resolution_remark`, `resolved_by`, `resolved_at`, `updated_at`.
3. Import and export `TblCallback`, `CallbackRescheduleLog`, `CallbackActivity` in `backend/app/models/__init__.py`.
4. Create `backend/app/db/migrations/0013_website_forms_callback_schema.py` (`requires_session = False`) that runs `Base.metadata.create_all` for the 3 callback tables and idempotently executes `ALTER TABLE website_inquiries ADD COLUMN ...` for the 7 new columns (matching `0011_cp_4_tier_governance.py` SQLite + PostgreSQL DDL pattern), and register `"app.db.migrations.0013_website_forms_callback_schema"` in `backend/app/db/migrations/runner.py`.

- [ ] **Step 4: Run test & migration verification**

Run: `pytest backend/tests/test_callbacks_and_problems_api.py::test_callback_models_and_defaults -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/callbacks.py backend/app/models/inquiries.py backend/app/models/__init__.py backend/app/db/migrations/0013_website_forms_callback_schema.py backend/app/db/migrations/runner.py backend/tests/test_callbacks_and_problems_api.py
git commit -m "feat(db): add tbl_callback, reschedule log, activity tables and inquiry triage columns"
```

---

### Task 2: Callback Round-Robin Intake, State Machine & Dual-Sync Service

**Files:**
- Create: `backend/app/services/callback_service.py`
- Modify: `backend/app/api/v1/endpoints/intake.py:160-226`
- Modify: `backend/app/services/intake_service.py:249-355`
- Test: `backend/tests/test_callbacks_and_problems_api.py`

**Interfaces:**
- Consumes: `TblCallback`, `CallbackRescheduleLog`, `CallbackActivity`, `Employee`, `Role`, `Lead`, `TblLead`, `WebsiteInquiry`, `get_next_lead_id`, `normalize_phone`
- Produces:
  - `app.services.callback_service.callback_service` singleton (`CallbackService`):
    - `create_callback(db, *, name, mobile_number, phone_code="+91", message=None, property_id=None, property_code=None, assigned_user_id=None, website_inquiry_id=None, actor_emp_id=None, enforce_caller_scope=False) -> TblCallback`
    - `has_view_all(emp: Employee) -> bool`
    - `get_dashboard_counts(db, actor: Employee) -> Dict[str, int]`
    - `list_callbacks(db, actor: Employee, *, tab="new", search=None, sort_by="created_date", order_by="desc", limit=50, offset=0) -> Tuple[int, List[Dict[str, Any]]]`
    - `get_callback_detail(db, actor: Employee, callback_id: int) -> Dict[str, Any]`
    - `log_callback_call(db, actor: Employee, callback_id: int, *, remark: Optional[str] = None) -> Dict[str, Any]`
    - `reschedule_callback(db, actor: Employee, callback_id: int, *, current_update: str, remark: str, followup_datetime: datetime) -> Dict[str, Any]`
    - `change_callback_status(db, actor: Employee, callback_id: int, *, lead_status: int, remark: str, disqualified_reason: Optional[int] = None, calls_status: Optional[int] = None) -> Dict[str, Any]`
    - `transfer_callback(db, actor: Employee, callback_id: int, *, assigned_user_id: str, remark: str) -> Dict[str, Any]`
    - `reopen_callback(db, actor: Employee, callback_id: int, *, remark: Optional[str] = None) -> Dict[str, Any]`
    - `convert_callback_to_lead(db, actor: Employee, callback_id: int, *, customer_type: str, name: str, email: Optional[str], mobile: str, alternate_mobile: Optional[str], address: str, refer_by_relation: Optional[str], refer_by_name: Optional[str], refer_by_mobile: Optional[str], source: str, assigned_to: Optional[str]) -> Dict[str, Any]`
    - `export_callbacks_xls(db, actor: Employee, *, tab="all", search=None, sort_by="created_date", order_by="desc") -> str`
  - Public endpoint `POST /v1/intake/callback` in `backend/app/api/v1/endpoints/intake.py`.

- [ ] **Step 1: Write failing tests covering intake round-robin, Review Focus edge cases, state machine, conversion, and sync**

Append tests to `backend/tests/test_callbacks_and_problems_api.py`:
- `test_intake_callback_round_robin_and_zero_telecaller_fallback`:
  1. Without any `TELECALLER` staff, `POST /v1/intake/callback` returns `201`, `lead_unique_id` starts with `"WEB"`, `assigned_user_id is None`.
  2. With 2 active `TELECALLER` employees (`EMP-T001`, `EMP-T002`) and 1 inactive/on-leave telecaller (`EMP-T003`), 4 consecutive `POST /v1/intake/callback` submissions alternate strictly (`EMP-T001`, `EMP-T002`, `EMP-T001`, `EMP-T002`) and never assign `EMP-T003`.
- `test_inquiry_callback_sync_and_dual_conversion_guard`:
  1. `POST /v1/intake/inquiry` with `inquiry_type="CALLBACK"` creates both `WebsiteInquiry` and linked `TblCallback` (`website_inquiry_id`).
  2. Converting via `callback_service.convert_callback_to_lead` creates both `Lead` (`OB-...`) and `TblLead` (`lead_source_id=4`), marks `TblCallback.lead_status == 5`, `lead_open == 0`, AND sets `WebsiteInquiry.is_converted == True`.
  3. Attempting `intake_service.convert_inquiry_to_lead` afterwards fails with `HTTPException(400)`.
- `test_reschedule_status_transfer_reopen_state_machine`:
  1. Past datetime in `reschedule_callback` raises `HTTPException(400)` with `"Schedule Date and Time should be greater than the current date and time."`.
  2. Naive future UTC datetime normalizes cleanly and creates `CallbackRescheduleLog` + updates `followup_datetime`.
  3. `change_callback_status(lead_status=2)` without `disqualified_reason` raises `HTTPException(400)`; with `disqualified_reason=3`, auto-locks `lead_open=0`.
  4. While `lead_open == 0`, `reschedule_callback`, `transfer_callback`, `change_callback_status`, and `convert_callback_to_lead` all raise `400` (`"This Callback is closed..."`).
  5. `reopen_callback` restores `lead_open=1` and `lead_status=1`; `transfer_callback` changes `assigned_user_id` and resets `lead_status=0, calls_status=0`.
  6. Terminal status `6` (`Converted Property`) locks `lead_open=0`, and `reopen_callback` on `5` or `6` raises `400`. Also `change_callback_status(lead_status=5)` raises `400`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/test_callbacks_and_problems_api.py -v`
Expected: FAIL with `ImportError` / `404` on `/v1/intake/callback`.

- [ ] **Step 3: Implement `CallbackService` and wire `/v1/intake/callback` + inquiry sync**

1. Create `backend/app/services/callback_service.py`:
   - Normalize aware/naive datetimes via helper `_ensure_utc(dt: datetime) -> datetime` and compute IST (`timezone(timedelta(hours=5, minutes=30))`) today window converted to UTC for `today_calls` / `missing_calls`.
   - Implement deterministic `_pick_round_robin_telecaller(db)` querying `Employee` + `Role.code == "TELECALLER"` (`is_active == True`, `is_on_leave == False`, `deleted_at IS NULL`), ordered by `(count(callback_id), max(created_date) nulls first, employee_id ASC)`.
   - Implement all lifecycle methods with exact validation rules, activity logging (`tbl_callback_activities`), dual conversion (`Lead` + `TblLead`), reverse sync to `WebsiteInquiry`, and HTML-escaped `.xls` export helper.
2. Update `backend/app/api/v1/endpoints/intake.py`:
   - Add `CallbackIntakeRequest` (supporting `mobile_number` and alias/fallback `phone`, `phone_code="+91"`, non-blank `name`, optional `message`, `property_id`, `property_code`) and `POST /v1/intake/callback` (`201 Created`).
3. Update `backend/app/services/intake_service.py`:
   - In `create_website_inquiry`, if `inquiry_type.upper() == "CALLBACK"`, invoke `callback_service.create_callback(..., website_inquiry_id=inquiry.id)`.
   - In `convert_inquiry_to_lead`, after converting, also update any paired `TblCallback(website_inquiry_id == inquiry.id)` to `lead_status=5, lead_converted=1, lead_open=0, converted_lead_id=lead_id` and log `"Converted to Lead"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/test_callbacks_and_problems_api.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/callback_service.py backend/app/api/v1/endpoints/intake.py backend/app/services/intake_service.py backend/tests/test_callbacks_and_problems_api.py
git commit -m "feat(callbacks): add round-robin callback service, state machine, and intake sync"
```

---

### Task 3: Callback & Report A Problem REST API Routers + Auth Scoping + `.xls` Export

**Files:**
- Create: `backend/app/services/problem_service.py`
- Create: `backend/app/api/v1/endpoints/callbacks.py`
- Create: `backend/app/api/v1/endpoints/problems.py`
- Modify: `backend/app/main.py:15-31, 80-91`
- Test: `backend/tests/test_callbacks_and_problems_api.py`

**Interfaces:**
- Consumes: `callback_service`, `intake_service`, `WebsiteInquiry`, `Employee`, `Role`, `decode_access_token`
- Produces:
  - Shared JWT dependency resolving `(Employee, Role)` with strict `401 Unauthorized` when unauthenticated or inactive
  - Endpoints on `/v1/callbacks`: `POST /`, `GET /dashboard`, `GET /`, `GET /assignees`, `GET /export`, `GET /{callback_id}`, `POST /{callback_id}/log-call`, `POST /{callback_id}/reschedule`, `POST /{callback_id}/status`, `POST /{callback_id}/transfer`, `POST /{callback_id}/reopen`, `POST /{callback_id}/convert-to-lead`
  - Endpoints on `/v1/problems`: `GET /`, `PATCH /{inquiry_id}`, `POST /{inquiry_id}/convert-to-lead`, `GET /export`

- [ ] **Step 1: Write failing API integration tests for `/v1/callbacks` and `/v1/problems`**

Append tests to `backend/tests/test_callbacks_and_problems_api.py`:
- `test_callbacks_auth_dashboard_tabs_and_export`:
  - Unauthenticated `GET /v1/callbacks` and `GET /v1/problems` return `401`.
  - Authenticated MD (`auth_client_md`) creates callback manually (`POST /v1/callbacks`), checks `GET /v1/callbacks/dashboard` counters (`new_calls >= 1`, `open_calls >= 1`), creates a due/past followup and verifies `missing_calls` + `today_calls` tab filters, logs a call, reschedules, transfers to `EMP-0002`, verifies `auth_client_sales` (`EMP-0002` scoped visibility) sees transferred callback while non-assigned callbacks remain hidden.
  - Verifies `GET /v1/callbacks/export` returns `200`, `content-type` `application/vnd.ms-excel`, and escapes `<script>` payload (`&lt;script&gt;`).
- `test_problems_triage_and_convert_to_lead`:
  - Submits `POST /v1/intake/inquiry` with `inquiry_type="PROBLEM_REPORT"`, lists `GET /v1/problems?status=NEW`, updates status to `IN_REVIEW` -> `RESOLVED` with assignee & remark (`PATCH /v1/problems/{id}`), converts a problem report to CRM lead (`POST /v1/problems/{id}/convert-to-lead`), and downloads `GET /v1/problems/export` (`200`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/tests/test_callbacks_and_problems_api.py -v`
Expected: FAIL with `404` on `/v1/callbacks` and `/v1/problems`.

- [ ] **Step 3: Implement `problem_service.py`, `callbacks.py`, `problems.py`, and mount in `main.py`**

1. Create `backend/app/services/problem_service.py`:
   - Implement `list_problems(db, actor, *, status_filter="ALL", search=None, limit=50, offset=0)` returning `{ total, counts: { all, new, in_review, resolved, rejected }, items }` enriched with assignee name & linked property/inquiry details.
   - Scope visibility cleanly: `SUPER_ADMIN`, `MD`, `SALES_MANAGER`, `VERIFICATION_OFFICER`, or roles with `leads.view_all` / `properties.verify` / `all.*` see all; other staff see `assigned_to == actor.employee_id`.
   - Implement `update_problem_triage(db, actor, inquiry_id, *, status_val=None, assigned_to=None, resolution_remark=None)` setting `resolved_at`/`resolved_by` when transitioning to `RESOLVED` or `REJECTED`.
   - Implement `export_problems_xls(db, actor, *, status_filter="ALL", search=None) -> str` with `html.escape` protection.
2. Create `backend/app/api/v1/endpoints/callbacks.py` (`prefix="/v1/callbacks"`) and `backend/app/api/v1/endpoints/problems.py` (`prefix="/v1/problems"`) with strict Pydantic request/response schemas and `get_current_employee` dependency (`401` if invalid/missing token). Ensure static routes (`/dashboard`, `/assignees`, `/export`) are declared BEFORE dynamic `/{callback_id}`.
3. Register `callbacks.router` and `problems.router` in `backend/app/main.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/tests/test_callbacks_and_problems_api.py -v`
Expected: All tests in `test_callbacks_and_problems_api.py` PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/problem_service.py backend/app/api/v1/endpoints/callbacks.py backend/app/api/v1/endpoints/problems.py backend/app/main.py backend/tests/test_callbacks_and_problems_api.py
git commit -m "feat(api): add callbacks and problems CRUD, scoping, conversion, and xls export endpoints"
```

---

### Task 4: Frontend `WebsiteFormsHub` (`Request A Callback` Master-Detail Workspace)

**Files:**
- Create: `frontend/src/types/websiteForms.ts`
- Create: `frontend/src/pages/WebsiteFormsHub.tsx`

**Interfaces:**
- Consumes API endpoints: `/v1/callbacks/dashboard`, `/v1/callbacks`, `/v1/callbacks/assignees`, `/v1/callbacks/{id}`, `/v1/callbacks/{id}/log-call`, `/v1/callbacks/{id}/reschedule`, `/v1/callbacks/{id}/status`, `/v1/callbacks/{id}/transfer`, `/v1/callbacks/{id}/reopen`, `/v1/callbacks/{id}/convert-to-lead`, `/v1/callbacks/export`, `POST /v1/callbacks`.
- Produces: Typed `WebsiteFormsHub` component supporting `?tab=callbacks` and delegating `?tab=problems` (stubbed placeholder slot wired in Task 5).

- [ ] **Step 1: Define shared types and metadata in `frontend/src/types/websiteForms.ts`**

Create clean interfaces & lookup tables (`CALLBACK_STATUS_META` with exact colors/labels for codes `0..6`, `DISQUALIFIED_REASONS` `1..7`, `CURRENT_UPDATE_OPTIONS`, `CallbackSummary`, `CallbackDetail`, `DashboardCounts`, `AssigneeOption`, `ProblemReportItem`, `ProblemCounts`, and `authHeaders()` helper).

- [ ] **Step 2: Implement `Request A Callback` master-detail workspace in `frontend/src/pages/WebsiteFormsHub.tsx`**

Implement the AlwarMap-styled (`#291BB0` / `#F04B42`) master-detail interface matching screenshots 1–5:
- Top bar: mode switcher pills (`Request A Callback` / `Report A Problem`), `+ New Callback` modal button, `Export .xls` button (triggers authenticated blob download of `/v1/callbacks/export`), and the **7 callback filter tabs with live counters** (`Home / New`, `Today Calls`, `Open Calls`, `Missing Calls`, `Converted Lead`, `All Calls`, `Converted Property`).
- Left panel (~360px): Search box, `Sort By` (`Created Date`, `Follow-up Date`, `Name`), `Order By` (`DESC`, `ASC`), clickable callback cards showing customer name, `WEBxxx`, formatted timestamp, assigned telecaller, and status badge.
- Right panel:
  - Header showing customer name, `+91-{mobile}`, status badge, lock state pill (`Open / Active` vs `Closed — Reopen Required` / `Converted`), and **6 circular action buttons** (`Call / Log`, `Reschedule Follow-Up`, `Reopen / Status Lock`, `Call Transfer`, `Convert to Lead`, `Activity & Reschedule History`) + explicit `Change Status` CTA.
  - Lock-aware disabled styling when `lead_open === 0` or converted (`lead_status === 5 || 6`) for Reschedule, Transfer, and Convert buttons, plus one-click `Reopen Lead` action when `lead_open === 0 && (lead_status === 2 || lead_status === 3)`.
  - Contact Details card (`Follow Up Remark`, `Request ID` `WEBxxx`, `Customer Name`, `Mobile No.`, `Current Update`, `Status`, `Disqualification Reason`, `Message`, `Linked Property`) & Others card (`Receive Date`, `Followup Date`, `Assigned Telecaller`, `Converted Lead ID` clickable link to `/leads/${converted_lead_id}`).
  - Modals/drawers:
    1. **Reschedule Follow-Up Modal:** `Current Update *` select, `Remark *` textarea, `Schedule Date *` (`date` + `time` inputs combined to ISO datetime).
    2. **Change Status Modal:** `Status *` select (`0..4, 6`), conditional `Disqualification Reason *` select (`1..7`) shown when status is `2`, `Remark *` textarea.
    3. **Call Transfer Modal:** `Select Employee *` dropdown populated from `/v1/callbacks/assignees`, `Remark *` textarea.
    4. **Convert to Lead Form/Modal:** Matching Screenshot 5 fields (`Customer Type *` (`BUY`/`RENT`/`PG`), `Name *`, `Email`, `Mobile *`, `Alternate Mobile No`, `Address *`, `Refer By` relation/name/mobile, `Source *` default `"Website Callback"`, `Assignee *` dropdown from `/v1/callbacks/assignees`).
    5. **Activity & Reschedule History Modal/Tab:** Chronological timeline combining `reschedule_history` (old -> new dates) and `activities` audit log.
    6. **+ New Callback Modal:** Quick manual entry calling `POST /v1/callbacks`.

- [ ] **Step 3: Run TypeScript check to verify zero compile errors**

Run: `npx --prefix c:\xampp\htdocs\om_shiv\frontend tsc --noEmit`
Expected: Command exits with code 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/websiteForms.ts frontend/src/pages/WebsiteFormsHub.tsx
git commit -m "feat(ui): build Request A Callback master-detail workspace and modals"
```

---

### Task 5: `Report A Problem` Triage Panel, Sidebar & App Routing Integration + Full Verification

**Files:**
- Create: `frontend/src/components/website-forms/ReportProblemPanel.tsx`
- Modify: `frontend/src/pages/WebsiteFormsHub.tsx`
- Modify: `frontend/src/layouts/AdminLayout.tsx:108-118, 220-265` (check active submenu highlight for query params)
- Modify: `frontend/src/App.tsx:1-25, 110-132`

**Interfaces:**
- Consumes: `/v1/problems`, `/v1/problems/{id}`, `/v1/problems/{id}/convert-to-lead`, `/v1/problems/export`, `/v1/callbacks/assignees`.
- Produces: Complete `/website-forms` experience with sidebar links `Request A Callback` (`/website-forms?tab=callbacks`) and `Report A Problem` (`/website-forms?tab=problems`).

- [ ] **Step 1: Inspect `AdminLayout.tsx` lines `220-290` for submenu active state handling before editing**

Ensure `location.pathname + location.search` properly highlights active sub-item (`?tab=callbacks` vs `?tab=problems`) and auto-expands `Website Forms` accordion when visiting `/website-forms`.

- [ ] **Step 2: Implement `frontend/src/components/website-forms/ReportProblemPanel.tsx` and wire into `WebsiteFormsHub.tsx`**

- Status filter pills with counts (`All`, `New`, `In Review`, `Resolved`, `Rejected`), search bar, `.xls` export button.
- Master-detail split layout showing reporter name, mobile, email, `related_property_code` / `details` JSON fields cleanly formatted, assigned staff dropdown (`/v1/callbacks/assignees`), status selector (`NEW`, `IN_REVIEW`, `RESOLVED`, `REJECTED`), `resolution_remark` input + Save (`PATCH /v1/problems/{id}`), and 1-Click `Convert to Lead` modal/button (linking directly to `/leads/${converted_lead_id}` once converted).

- [ ] **Step 3: Update `AdminLayout.tsx` sidebar & `App.tsx` route**

1. In `AdminLayout.tsx`, replace the 3 placeholder subItems under `WEBSITE_FORMS` with:
   - `{ label: 'Request A Callback', path: '/website-forms?tab=callbacks' }`
   - `{ label: 'Report A Problem', path: '/website-forms?tab=problems' }`
   And check query-string matching on `sub.path` so active subItem styling highlights accurately.
2. In `App.tsx`, import `WebsiteFormsHub` and replace the static `<ModuleHub ... />` at `path="/website-forms"` with `<WebsiteFormsHub />`.

- [ ] **Step 4: Run full verification suite (Backend `pytest` + Frontend `npm run build`)**

Run:
1. `pytest backend/tests/test_callbacks_and_problems_api.py -v`
2. `pytest backend/tests -v` (confirm zero regressions across entire backend)
3. `npm --prefix c:\xampp\htdocs\om_shiv\frontend run build` (`tsc && vite build` exits 0 cleanly)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/website-forms/ReportProblemPanel.tsx frontend/src/pages/WebsiteFormsHub.tsx frontend/src/layouts/AdminLayout.tsx frontend/src/App.tsx
git commit -m "feat(website-forms): integrate Report A Problem triage, sidebar routes, and WebsiteFormsHub"
```
