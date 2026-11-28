# Opportunities Module (Sales Deal Closing Desk) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the end-to-end Opportunities module (`tbl_opportunities` schema, `/v1/opportunities` APIs with property matching & deal/registry pipeline, split-screen `OpportunitiesHub.tsx`, and `LeadDetail.tsx` Convert to Opportunity flow).

**Architecture:** Dedicated relational tables (`tbl_opportunities`, `tbl_opportunity_locations`, `tbl_opportunity_reschedules`, `tbl_opportunity_activities`) managed by `opportunity_service.py` and exposed on `/v1/opportunities` with role-scoped access (`SUPER_ADMIN`/`MD`/`SALES_MANAGER` global; reps see assigned records) and `ChannelPartner` owner masking. Frontend renders a split-screen React workspace with Recharts analytics, Web Speech API search, Google Places / coordinate fallback locality picker, live property match popup, and bidirectional Lead conversion sync.

**Tech Stack:** FastAPI, SQLAlchemy (async), Pydantic v2, pytest, React 18, TypeScript, Tailwind CSS, Recharts, Lucide React, Vite.

**Spec:** `docs/superpowers/specs/2026-11-28-opportunities-module-design.md`

## Global Constraints
- `customer_type` on Opportunity: `'END_USER' | 'INVESTOR'`; `loanable`: `'YES' | 'NO' | 'MAYBE'`; `property_type`: `1=Rent, 2=Buy/Sell, 3=PG`; `looking_type`: `1=Res, 2=Comm, 3=Agri, 4=Ind`; `lead_status`: `1=In Progress, 2=Disqualified, 4=Qualified (Deal Scheduled), 5=Closed (Deal Done)`.
- Direct close guard exact message (`HTTP 400`): `"You cannot close this lead because the client has not yet Buy any property."` when `deal_date is None`.
- Buy (`property_type=2`) Option 1 requires `deal_date <= now_utc` and strictly future `registry_date > now_utc`; auto-followup sets `max(registry_date - 2 days, now_utc + 1 hour)`.
- Live inventory matching & Option 1 Propira link filter strictly on `TblProperty.is_active == 1`, `verified_status == 1`, `sold_status == 0`, `recyclebin_status == 0`, `deleted_at IS NULL`, `(expiarydate IS NULL OR expiarydate >= now_utc)`.
- Cancelling out of `status=4` (`4 -> 1` or `4 -> 2`) or switching matched Propira property reverts prior `TblProperty.sold_status` from `1` back to `0`.
- All Opportunity endpoints require `Depends(get_current_employee)` (`callbacks.get_current_employee`) and check role/ownership scope (`403` otherwise); static `/dashboard` and `/export` routes are registered *before* `/{opportunity_id}`.
- Verification uses `c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe` and `npm --prefix c:\xampp\htdocs\om_shiv\frontend run build`.

## Review Focus
1. Attempting to close an Opportunity directly (`status=5`) without prior Option 1 Deal & Property record returns `HTTP 400` with the exact required detail string and never locks the record.
2. Cancelling or disqualifying a `status=4` Opportunity (or switching Propira property in Option 1) atomically rolls back the prior `TblProperty.sold_status` from `1` back to `0` (`Available`) and clears stale deal dates on `1`/`2`.
3. Selecting an already-sold (`sold_status != 0`), unverified (`verified_status != 1`), inactive (`is_active != 1`), or recycled property in Option 1 fails with `HTTP 400`/`404`, preventing double-selling.
4. `GET /v1/opportunities/{id}/related-properties` returns zero unverified/inactive/sold/expired properties, computes Haversine + budget + subcategory matches across multiple saved locations, and masks owner contact info for `FRANCHISEE_AGENT` / Channel Partner users while exposing it to internal sales staff.
5. Converting an already-converted, Disqualified (`lead_status=2`), or Property-converted (`property_id > 0` / `lead_status=5`) Lead returns `HTTP 400` with zero partial DB mutations; closing (`status=5`) updates linked `Lead.stage = "WON"` so Franchise Referral Partner rewards unlock.

---

### Task 1: Database Models, Sequence & Idempotent Migration `0015`

**Files:**
- Create: `backend/app/models/opportunities.py`
- Create: `backend/app/db/migrations/0015_opportunities_schema.py`
- Modify: `backend/app/db/base.py:10-17`
- Modify: `backend/app/db/migrations/runner.py:20-25`
- Create: `backend/tests/test_opportunities_api.py`

**Interfaces:**
- Produces: `OpportunitySequence`, `TblOpportunity`, `OpportunityLocation`, `OpportunityRescheduleLog`, `OpportunityActivity`, `OPPORTUNITY_STATUSES`, `DISQUALIFIED_REASONS` in `app/models/opportunities.py`.

- [ ] **Step 1: Write failing migration & model registration tests in `backend/tests/test_opportunities_api.py`**

Assert `TblOpportunity.__tablename__ == "tbl_opportunities"`, all 5 tables exist in `Base.metadata.tables`, and executing `run_all_migrations` / `0015_opportunities_schema.upgrade` creates the tables idempotently without error on SQLite.

- [ ] **Step 2: Run pytest to verify FAIL**

Run: `c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe c:\xampp\htdocs\om_shiv\backend\tests\test_opportunities_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.opportunities'`.

- [ ] **Step 3: Implement `app/models/opportunities.py`, register in `base.py`, add `0015_opportunities_schema.py` + `runner.py`**

Create the 5 SQLAlchemy 2.0 models matching spec Section 4 (`TblOpportunity`, `OpportunityLocation`, `OpportunityRescheduleLog`, `OpportunityActivity`, `OpportunitySequence`), export constants (`OPPORTUNITY_STATUSES`, `DISQUALIFIED_REASONS`), import `app.models.opportunities` in `app/db/base.py`, and add idempotent `0015_opportunities_schema.py` in `MIGRATION_STEPS`.

- [ ] **Step 4: Run pytest to verify PASS & Commit**

Run: `c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe c:\xampp\htdocs\om_shiv\backend\tests\test_opportunities_api.py -v`
Expected: PASS.
Commit: `feat(opportunities): add relational models and idempotent 0015 migration`

---

### Task 2: Opportunity Core Service, Conversion from Lead, Matching Engine & Export API

**Files:**
- Create: `backend/app/services/opportunity_service.py`
- Create: `backend/app/api/v1/endpoints/opportunities.py`
- Modify: `backend/app/main.py:15-35,88-96`
- Modify: `backend/tests/test_opportunities_api.py`

**Interfaces:**
- Consumes: Task 1 models, `callbacks.get_current_employee`, `callback_service` UTC/IST & HTML-XLS escape helpers, `franchise.ChannelPartner`, `leads.Lead` / `TblLead` / `LeadActivity`, `properties.TblProperty`.
- Produces on `/v1/opportunities`:
  - `GET /dashboard`
  - `GET /` (`tab`, `search`, `limit`, `offset`)
  - `POST /` (create standalone or convert from `source_lead_id`)
  - `GET /export` (`.xls` download, registered before `/{opportunity_id}`)
  - `GET /{opportunity_id}`
  - `PUT /{opportunity_id}` (blocked when `lead_open == 0`)
  - `GET /{opportunity_id}/related-properties` (`getrelatedProperty`)

- [ ] **Step 1: Write failing tests covering Core CRUD, Lead Conversion sync/guards, Dashboard/Tabs, `related-properties` matching & masking, Edit lock, and `.xls` export**

Pin Review Focus #3 (sold/unverified/inactive/recycled excluded), #4 (multi-location Haversine radius + text fallback, budget overlap, subcategory filter, `FRANCHISEE_AGENT` ChannelPartner masking vs internal sales visibility), and #5 (duplicate/disqualified/property-converted lead blocks cleanly with `400`).

- [ ] **Step 2: Run pytest to verify FAIL**

Run: `c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe c:\xampp\htdocs\om_shiv\backend\tests\test_opportunities_api.py -v`
Expected: FAIL (endpoints not implemented).

- [ ] **Step 3: Implement `opportunity_service.py`, `endpoints/opportunities.py`, and mount router in `app/main.py`**

Implement `generate_opportunity_code`, role-scoped dashboard/tab queries (`new`, `today`, `open`, `missing`, `in_progress`, `closed`, `all` using IST day bounds), standalone create + atomic Lead conversion (`tbl_leads.opportunity_converted = 1`, `opportunity_id`, `opportunity_datetime`, `lead_status = 4`, `leads.stage = "QUALIFIED"`, `LeadActivity`), requirement edit guard (`lead_open == 1`), Haversine distance + text fallback matching engine against live verified available `TblProperty`, Channel Partner contact masking, and `.xls` export.

- [ ] **Step 4: Run pytest to verify PASS & Commit**

Run: `c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe c:\xampp\htdocs\om_shiv\backend\tests\test_opportunities_api.py -v`
Expected: PASS.
Commit: `feat(opportunities): implement core CRUD, lead conversion, matching engine, and export APIs`

---

### Task 3: Deal Pipeline State Machine, Reschedule, Transfer, Reopen & Call Log

**Files:**
- Modify: `backend/app/services/opportunity_service.py`
- Modify: `backend/app/api/v1/endpoints/opportunities.py`
- Modify: `backend/tests/test_opportunities_api.py`

**Interfaces:**
- Produces on `/v1/opportunities`:
  - `POST /{opportunity_id}/reschedule` (future datetime, mandatory remark, blocked if `lead_open == 0`)
  - `POST /{opportunity_id}/status` (`1` In Progress, `2` Disqualified with reason `1..7`, `4` Qualified Option 1 Deal & Registry Schedule, `5` Option 2 Closed Deal Done)
  - `POST /{opportunity_id}/transfer` (blocked if `lead_open == 0`)
  - `POST /{opportunity_id}/reopen` (Disqualified `2 -> 1` only; Closed `5` blocked)
  - `POST /{opportunity_id}/call-log`

- [ ] **Step 1: Write failing tests covering Status State Machine, Deal & Registry validations, Auto-Followup `- 2 days`, Propira `sold_status` lock & rollback, Direct-Close block, Reschedule, Transfer, Reopen, and Parent Lead `WON`/`LOST` sync**

Pin Review Focus #1 (exact HTTP `400` detail `"You cannot close this lead because the client has not yet Buy any property."`), #2 (`4 -> 1`, `4 -> 2`, and Propira property switch rollback `TblProperty.sold_status = 0`), #3 (unavailable/unverified property rejection in Option 1), #5 (`status=5` sets parent `Lead.stage = "WON"` and `TblLead.lead_status = 5, lead_open = 0`), Rent/PG flexible Agreement Date vs Buy strict future `registry_date`, and future-only Reschedule + Disqualified Reopen.

- [ ] **Step 2: Run pytest to verify FAIL**

Run: `c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe c:\xampp\htdocs\om_shiv\backend\tests\test_opportunities_api.py -v`
Expected: FAIL (404/405 on lifecycle action endpoints).

- [ ] **Step 3: Implement lifecycle transitions, deal/registry validation, `sold_status` swap/rollback, and parent Lead sync**

Implement atomic Option 1 deal linking + `registry_date - 2 days` (clamped `>= now + 1h`) + `OpportunityRescheduleLog`, Option 2 direct-close guard, Disqualified `lead_open=0` + `1..7` reasons, `status=4` cancellation/switch `TblProperty.sold_status = 0` rollback, Reschedule, Transfer, Reopen (`2 -> 1`), and `call-log`.

- [ ] **Step 4: Run pytest (both `test_opportunities_api.py` and `test_lead_inflow_and_kanban.py`) & Commit**

Run: `c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe c:\xampp\htdocs\om_shiv\backend\tests\test_opportunities_api.py c:\xampp\htdocs\om_shiv\backend\tests\test_lead_inflow_and_kanban.py -v`
Expected: All PASS.
Commit: `feat(opportunities): add deal/registry pipeline, sold rollback, reschedule, transfer, and reopen`

---

### Task 4: Frontend Types, Locality Picker & Form / Related Properties Modals

**Files:**
- Create: `frontend/src/types/opportunities.ts`
- Create: `frontend/src/components/opportunities/LocalityMultiPicker.tsx`
- Create: `frontend/src/components/opportunities/OpportunityFormModal.tsx`
- Create: `frontend/src/components/opportunities/RelatedPropertiesModal.tsx`

**Interfaces:**
- Consumes Task 2/3 `/v1/opportunities*`, `/v1/leads/assignees`, `/v1/franchise/outlets` endpoints.
- Produces clean typed React components consumed by `OpportunitiesHub.tsx` in Task 5.

- [ ] **Step 1: Create `frontend/src/types/opportunities.ts` with exact types & lookup maps**

Include `OPPORTUNITY_STATUS_META`, `DISQUALIFIED_REASONS`, `PROPERTY_CATEGORIES`, `PROPERTY_SUBCATEGORIES` (matching `PropertyForm.tsx` IDs `1..11`), `AREA_UNITS`, `LOANABLE_OPTIONS`, `FURNISHING_OPTIONS`, `PROPERTY_AGE_OPTIONS`, and request/response interfaces.

- [ ] **Step 2: Build `LocalityMultiPicker.tsx` with `VITE_GOOGLE_MAPS_API_KEY` Places Autocomplete + city/lat-lng fallback**

Dynamically load Google Maps Places script only if `import.meta.env.VITE_GOOGLE_MAPS_API_KEY` is non-empty; always allow adding/removing multiple localities with Alwar/Jaipur/Bhiwadi/Neemrana preset coords + editable `latitude`, `longitude`, and `radius_km`.

- [ ] **Step 3: Build `OpportunityFormModal.tsx` (Create, Edit & Pre-fill from `sourceLead`) and `RelatedPropertiesModal.tsx`**

Include all Buyer Details (`END_USER` / `INVESTOR`, Name, Mobile 1, Mobile 2, Email, Address), Property Category/Subcategory, Budget From–To, Area From–To + Unit, BHK, Furnishing, Age, Loanable, `LocalityMultiPicker`, Franchisee & Staff dropdowns, and Remark. `RelatedPropertiesModal` renders matched properties with distance, price, BHK, area, verified status, owner contact (when unmasked), and optional quick "Select for Deal Schedule" callback.

- [ ] **Step 4: Run `npm --prefix frontend run build` to verify TypeScript compilation & Commit**

Run: `npm --prefix c:\xampp\htdocs\om_shiv\frontend run build`
Expected: PASS (`tsc && vite build` exit code `0`).
Commit: `feat(frontend): add Opportunity types, locality picker, form modal, and property match popup`

---

### Task 5: Split-Screen `OpportunitiesHub.tsx`, Analytics, Voice Search, Action Modals & `LeadDetail` Integration

**Files:**
- Create: `frontend/src/pages/OpportunitiesHub.tsx`
- Modify: `frontend/src/App.tsx:10-40,125-150`
- Modify: `frontend/src/layouts/AdminLayout.tsx:99-107,140-152`
- Modify: `frontend/src/pages/LeadDetail.tsx:615-715,905-945`

**Interfaces:**
- Consumes Task 4 components + Task 2/3 `/v1/opportunities*` endpoints.
- Integrates `/opportunities?tab=...&fromLead=...` with `AdminLayout.tsx` sidebar and `LeadDetail.tsx` CTA.

- [ ] **Step 1: Build `OpportunitiesHub.tsx` split-screen 2-pane workspace**

Include:
- Top KPI strip (`Today Opportunity`, `Missing Opportunity`, `Open`, `Closed`) + Recharts responsive breakdown chart (`Total`, `Open`, `Disqualified`, `Qualified - Propira`, `Qualified - Other`, `Closed`).
- Left pane: 7 Quick Tabs (`New Opportunity`, `Today Opportunity`, `Open Opportunity`, `Missing Opportunity`, `All Opportunity`, `In-Progress`, `Closed`), text search + **Voice Mic Search** (`SpeechRecognition` / `webkitSpeechRecognition`), Excel Export button, `+ Create Opportunity`, and scrollable opportunity cards.
- Right pane: 360° profile + green **`"X Properties Found"`** button opening `RelatedPropertiesModal`, plus quick action toolbar (`Call tel:` + `/call-log`, `Reschedule`, `Status / Deal Schedule`, `Transfer`, `Reopen`, `Edit` when unlocked, `Activity History`).
- Modals for `Status Change / Deal & Registry Schedule` (with In Progress / Disqualified 1..7 / Qualified Option 1 Buy vs Rent-PG fields & Propira property selector + `sellPropertyR` indicator / Option 2 Closed Deal Done), `Reschedule` (future datetime + mandatory remark), `Transfer` (Franchisee + Staff), and `Activity History`.
- Auto-handle `?fromLead=<leadUid>` query param by fetching `/v1/leads/{fromLead}` and opening pre-filled `OpportunityFormModal`.

- [ ] **Step 2: Wire `OpportunitiesHub` in `App.tsx`, update `AdminLayout.tsx` Opportunities submenu tabs, and add "Convert to Opportunity" CTA in `LeadDetail.tsx`**

Replace static `<ModuleHub>` at `/opportunities` in `App.tsx` with `<OpportunitiesHub />`; update `AdminLayout.tsx` `OPPORTUNITIES` `subItems` (`New Opportunity`, `Today Opportunity`, `Open Opportunity`, `Missing Opportunity`, `In-Progress`, `Closed`, `All Opportunity`) and auto-expand submenu on `/opportunities`; add **"Convert to Opportunity"** (or **"View Opportunity"** when `lead.opportunity_converted === 1`) in `LeadDetail.tsx` (`LeadDetail.tsx` hero/action & Opportunity row).

- [ ] **Step 3: Run full verification (`npm --prefix frontend run build` and `pytest -q`) & Commit**

Run: `npm --prefix c:\xampp\htdocs\om_shiv\frontend run build; if ($?) { c:\xampp\htdocs\om_shiv\.venv\Scripts\pytest.exe c:\xampp\htdocs\om_shiv\backend\tests -q }`
Expected: Vite build clean + all backend tests pass.
Commit: `feat(frontend): add split-screen OpportunitiesHub workspace and LeadDetail conversion CTA`
