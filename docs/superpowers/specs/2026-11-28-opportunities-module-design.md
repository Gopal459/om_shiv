# Opportunities Module (Sales Deal Closing Desk) — Design Specification

- **Date:** 2026-11-28
- **Status:** Updated Post Builder Check — Ready for Approval
- **Approach Selected:** Approach A — Dedicated Relational Opportunity Tables (`tbl_opportunities`, `tbl_opportunity_locations`, `tbl_opportunity_reschedules`, `tbl_opportunity_activities`) + Atomic Lead Sync (`leads` / `tbl_leads`)

---

## 1. Intent and Why

In Om Shiv CRM, raw inbound contacts (**Leads** in `leads` / `tbl_leads`) capture initial name, phone, source, and basic remarks. Once a telecaller qualifies a buyer/renter and captures exact property specifications (transaction type, category, subcategory, budget min–max, area min–max + unit, BHK, furnishing, age, loan preference, multiple preferred localities with geo-coordinates), that inquiry graduates into an **Opportunity** — tracked from property matching through site visits, Deal Date, Registry Date (`registry_date - 2 days` auto follow-up), Propira inventory sold-marking, and Deal Closing.

Today `/opportunities` in [App.tsx](file:///c:/xampp/htdocs/om_shiv/frontend/src/App.tsx) and [AdminLayout.tsx](file:///c:/xampp/htdocs/om_shiv/frontend/src/layouts/AdminLayout.tsx) renders only a static `<ModuleHub>` placeholder. This design replaces it with a complete backend + interactive split-screen workspace matching the full `Opportunities` lifecycle, plus a **Convert to Opportunity** action on [LeadDetail.tsx](file:///c:/xampp/htdocs/om_shiv/frontend/src/pages/LeadDetail.tsx).

---

## 2. Goals, Non-Goals, and Anti-Goals

### 2.1 Goals
- **Dedicated Relational Schema (Migration `0015_opportunities_schema.py`):**
  - `tbl_opportunities`, `tbl_opportunity_locations`, `tbl_opportunity_reschedules`, `tbl_opportunity_activities`, and atomic sequence counter (`opportunity_sequences` for `OPP-YYYY-NNNNNN`).
- **Lead → Opportunity Conversion (`LeadDetail.tsx` & `POST /v1/opportunities`):**
  - Support both standalone **Create Opportunity** and **Convert Lead to Opportunity** from `LeadDetail.tsx` (pre-filling Name, Mobile, Alternate Mobile, Email, Address, Transaction Type, Customer Type, Locality, Budget, Remarks).
  - Block converting leads that are already `opportunity_converted == 1`, Disqualified (`lead_status == 2`), or Property-Converted/Closed (`property_id > 0` or `lead_status == 5`) (`HTTP 400`).
  - Atomically set `tbl_leads.opportunity_converted = 1`, `tbl_leads.opportunity_id`, `tbl_leads.opportunity_datetime`, `tbl_leads.lead_status = 4` (so the lead moves into the `Qualified` Kanban column), `leads.stage = "QUALIFIED"`, and log `LeadActivity(action_type="CONVERTED_TO_OPPORTUNITY")`.
  - Keep linked `leads` / `tbl_leads` synced post-conversion: Closing an Opportunity (`status = 5`) updates `Lead.stage = "WON"` (unlocking `cp_governance_service` Referral Partner payouts) and `TblLead.lead_status = 5, lead_open = 0, deal_date, registry_date, dealclose_date`; Disqualifying (`status = 2`) updates `Lead.stage = "LOST"` and `TblLead.lead_status = 2, lead_open = 0`; Reopening (`2 -> 1`) restores `Lead.stage = "QUALIFIED"` and `TblLead.lead_status = 4, lead_open = 1`.
- **Interactive Split-Screen Workspace (`/opportunities`):**
  - **Top Summary & Recharts Analytics:** `Today` follow-up count, `Missing` (overdue open follow-up) count, 7 tab counts (`new`, `today`, `open`, `missing`, `all`, `in_progress`, `closed`), and visual breakdown (`Total`, `Open / In Progress`, `Disqualified`, `Qualified - Propira`, `Qualified - Other`, `Closed`).
  - **Left Pane:** Fast searchable list with Customer Name, Budget range, Preferred Localities, Status badge, `OPP-YYYY-NNNNNN` ID, **Voice Microphone Search** (`Web Speech API` with graceful non-supported fallback), and the **7 Quick Filter Tabs** (`New Opportunity`, `Today Opportunity`, `Open Opportunity`, `Missing Opportunity`, `All Opportunity`, `In-Progress`, `Closed`).
  - **Right Pane:** 360° Buyer Profile & Requirements view + **`"X Properties Found"`** green badge button opening the instant Matched Properties popup + full Quick Action Toolbar (`Call User` `tel:`, `Reschedule Follow-up`, `Status Change`, `Transfer`, `Reopen Lead`, `Edit Opportunity`, `History`, `Excel Export`).
- **Automatic Property Matching Engine (`getrelatedProperty`):**
  - Match **live available verified inventory** aligned with `PropertyHub`'s `verify_live` rule (`tbl_property.is_active == 1`, `verified_status == 1`, `sold_status == 0`, `recyclebin_status == 0`, `deleted_at IS NULL`, and `(expiarydate IS NULL OR expiarydate >= now)`) by:
    1. Category (`looking_type`) & Subcategory (`looking_subcat_type`) + Transaction (`property_type`: Rent=1, Sell=2, PG=3).
    2. Budget range overlap (`budget_from <= expected_price <= budget_to`, handling open upper/lower bounds cleanly).
    3. Multi-location Geo + Locality match: Haversine distance (`<= radius_km`, default 10 km) when Opportunity location and Property have `lat/lng`, plus text locality fallback (`location`, `sublocality_address`, `nearby_area`).
    4. Optional BHK refinement (`noof_bhk`) if requested on Residential Flat/House/Floor.
  - **Owner Contact Visibility:** Internal CRM staff (`SUPER_ADMIN`, `MD`, `SALES_MANAGER`, `TELECALLER`, `FIELD_EXECUTIVE`, `VERIFICATION_OFFICER` without linked `ChannelPartner`) receive owner name/mobile on matched cards to coordinate site visits; `FRANCHISEE_AGENT` or Channel-Partner-linked users enforce `cp_governance_service.py` tier visibility (blocks `ACTIVE_CP L1` & `REFERRAL_PARTNER`, masks owner phone/name when `cp_show_seller_contact` is disabled).
- **Deal Pipeline & Strict State Machine:**
  - Status `1` = **In Progress (Open)** (`lead_open = 1`).
  - Status `2` = **Disqualified** (mandatory `disqualified_reason` `1..7`; sets `lead_open = 0`).
  - Status `4` = **Qualified — Deal & Registry Schedule** (Option 1):
    - **Buy (`property_type = 2`):** validates `deal_date <= now` (past/present) and `registry_date > now` (strictly future), schedules **auto follow-up = `registry_date - 2 days`** (clamped `>= now + 1h`).
    - **Rent (`property_type = 1`) / PG (`property_type = 3`):** validates `deal_date <= now` and treats `registry_date` as optional **Agreement / Move-in Date** (if future date provided, auto-schedules `- 2 days` clamped `>= now + 1h`).
    - When `is_propira_property = True`, validates live available property (`is_active == 1`, `verified_status == 1`, `sold_status == 0`, `recyclebin_status == 0`, `deleted_at IS NULL`) and marks `tbl_property.sold_status = 1`.
    - Keeps `lead_open = 1`. **Cancellation / Property Switch:** Before closing (`status = 5`), transitioning from `status = 4` back to `1` (`In Progress`) or `2` (`Disqualified`), or switching to another property via Option 1, atomically reverts the prior linked Propira property's `tbl_property.sold_status` back to `0` (`Available`).
  - Status `5` = **Closed — Deal Done** (Option 2): **hard-blocked** (`HTTP 400`) with exact message `"You cannot close this lead because the client has not yet Buy any property."` unless Option 1 (`deal_date` / property purchase) was already completed! Closing locks `lead_open = 0` and blocks editing/rescheduling/transfer/reopen permanently.
- **Locations & Google Maps Key Support:**
  - Use Google Places Autocomplete for adding multiple localities (`locality_name`, `lat`, `lng`) when `VITE_GOOGLE_MAPS_API_KEY` is configured in frontend env; automatically fall back to editable Locality + City presets (`Alwar`, `Bhiwadi`, `Neemrana`, `Jaipur`) & manual Lat/Long inputs when no key is configured.

### 2.2 Non-Goals
- External CanvasJS CDN dependency (Recharts is already installed and matches `AdminDashboard.tsx`).
- Built-in WebRTC VoIP dialer (`tel:` link + logged `calls_status` / activity entries are used).

### 2.3 Anti-Goals
- Never allow closing an Opportunity directly (`status=5` / Closed) without a prior Option 1 Deal & Property purchase record.
- Never allow editing, rescheduling, or transferring locked (`lead_open == 0`) Opportunities without explicit Reopen (Disqualified only; Closed Deals stay terminal).
- Never mutate `TblProperty.sold_status = 1` without validating the property is currently available (`sold_status == 0` and not deleted).

---

## 3. Approaches Considered

- **Approach A (Selected): Dedicated Relational Opportunity Tables (`tbl_opportunities`, `tbl_opportunity_locations`, `tbl_opportunity_reschedules`, `tbl_opportunity_activities`)**
  - *Pros:* Clean normalized SQL for 7 tabs, IST `Today`/`Missing` queries, multi-locality matching, independent reschedule/activity logs, and clean Deal-vs-Closed constraints without overloading `tbl_leads`.
- **Approach B (Rejected): Extending `tbl_leads` with JSON requirements & extra statuses**
  - *Cons:* Collides raw lead statuses (`0..5`) with Opportunity statuses (`1, 2, 4, 5`), complicates multi-locality SQL radius queries, and mixes Lead vs Opportunity activity trails.

---

## 4. Database Schema (`0015_opportunities_schema.py`)

Registered in `MIGRATION_STEPS` in `backend/app/db/migrations/runner.py`.

### 4.1 `opportunity_sequences` (`OpportunitySequence`)
- `year` (`Integer` PK), `last_sequence` (`Integer` default `0`) → formats `OPP-{year}-{seq:06d}`.

### 4.2 `tbl_opportunities` (`TblOpportunity`)
| Column | Type | Notes |
|---|---|---|
| `opportunity_id` | `Integer` PK, AI | Primary key |
| `opportunity_code` | `String(32)` unique, indexed | `OPP-YYYY-NNNNNN` |
| `source_lead_id` | `String(32)` nullable, index, unique-when-set logic | Linked `leads.lead_id` / `tbl_leads.lead_unique_id` |
| `contact_name` | `String(255)` NOT NULL | Client name |
| `mobile` | `String(32)` NOT NULL, indexed | Normalized phone |
| `alternate_mobile` | `String(32)` nullable | Mobile 2 |
| `email` | `String(255)` nullable | Email |
| `address` | `Text` nullable | Client address |
| `customer_type` | `String(32)` default `'END_USER'` | `'END_USER'` \| `'INVESTOR'` |
| `property_type` | `Integer` default `2` | `1=Rent, 2=Buy/Sell, 3=PG` |
| `looking_type` | `Integer` default `1` | `1=Residential, 2=Commercial, 3=Agricultural, 4=Industrial` |
| `looking_subcat_type` | `Integer` default `1` | Matches `tbl_property.looking_subcat_type` (`1..11`) |
| `budget_from` | `Numeric(18,2)` default `0` | Minimum budget |
| `budget_to` | `Numeric(18,2)` default `0` | Maximum budget |
| `area_from` | `Numeric(12,2)` default `0` | Minimum area |
| `area_to` | `Numeric(12,2)` default `0` | Maximum area |
| `area_unit` | `String(32)` default `'Sq.Ft'` | `'Sq.Ft'`, `'Sq.Yd'`, `'Gaj'`, `'Sq.Meter'`, `'Acre'`, `'Bigha'` |
| `bhk` | `Integer` default `0` | `0=Any`, `1..5` |
| `furnishing` | `String(32)` nullable | `'FURNISHED'`, `'SEMI_FURNISHED'`, `'UNFURNISHED'` |
| `property_age` | `String(64)` nullable | e.g. `'UNDER_CONSTRUCTION'`, `'0_2_YEARS'`, `'2_5_YEARS'`, `'5_10_YEARS'`, `'10_PLUS_YEARS'` |
| `loanable` | `String(16)` default `'MAYBE'` | `'YES'`, `'NO'`, `'MAYBE'` |
| `remark` | `Text` nullable | Buyer requirement remarks |
| `assign_franch_id` | `Integer` default `0` | `franchise_outlets.id` (0 = Direct / Central) |
| `assign_franchstaff_id` | `Integer` default `0` | Legacy numeric employee PK synced with `assigned_to` |
| `assigned_to` | `String(32)` FK `employees.employee_id` (`ON DELETE SET NULL`), nullable, indexed | Primary assigned staff (`EMP-XXXX`) |
| `lead_status` | `Integer` default `1`, indexed | `1=In Progress (Open)`, `2=Disqualified`, `4=Qualified (Deal Scheduled)`, `5=Closed (Deal Done)` |
| `lead_open` | `Integer` default `1`, indexed | `1=Open/Unlocked`, `0=Locked (Disqualified or Closed)` |
| `calls_status` | `Integer` default `0` | `0=Not Called / New`, `1=Connected / Called` |
| `disqualified_reason` | `Integer` default `0` | `0=None`, `1..7` |
| `current_update` | `String(120)` nullable | Latest follow-up update label |
| `last_remark` | `Text` nullable | Latest interaction remark |
| `followup_datetime` | `DateTime(timezone=True)` nullable, indexed | Scheduled next follow-up |
| `deal_date` | `DateTime(timezone=True)` nullable | Option 1 Deal Date (`<= now`) |
| `registry_date` | `DateTime(timezone=True)` nullable | Option 1 Registry Date (`> now`) |
| `is_propira_property` | `Boolean` default `False` | `True` = Propira inventory (`matched_property_id` linked), `False` = External/Other property |
| `matched_property_id` | `Integer` nullable | `tbl_property.property_id` when Propira property bought |
| `matched_property_code` | `String(64)` nullable | `tbl_property.propertyid_no` |
| `deal_property_category` | `Integer` nullable | Snapshot category of dealt property |
| `deal_property_subcategory` | `Integer` nullable | Snapshot subcategory of dealt property |
| `deal_property_address` | `Text` nullable | Dealt property address |
| `deal_location_lat` | `String(64)` nullable | Dealt property lat |
| `deal_location_long` | `String(64)` nullable | Dealt property lng |
| `closed_at` | `DateTime(timezone=True)` nullable | Closed timestamp |
| `created_by` | `String(32)` nullable | Creator employee ID |
| `deleted_at` | `DateTime(timezone=True)` nullable, indexed | Soft delete |
| `created_at` | `DateTime(timezone=True)` default UTC now, indexed | |
| `updated_at` | `DateTime(timezone=True)` default/onupdate UTC now | |

### 4.3 `tbl_opportunity_locations` (`OpportunityLocation`)
- `id` (`Integer` PK), `opportunity_id` (FK `tbl_opportunities.opportunity_id` `ON DELETE CASCADE`, indexed), `locality_name` (`String(255)` NOT NULL), `latitude` (`Numeric(10,6)` nullable), `longitude` (`Numeric(10,6)` nullable), `radius_km` (`Integer` default `10`).

### 4.4 `tbl_opportunity_reschedules` (`OpportunityRescheduleLog`)
- `id` (`Integer` PK), `opportunity_id` (FK `tbl_opportunities.opportunity_id` `ON DELETE CASCADE`, indexed), `old_followup_datetime` (`DateTime(timezone=True)` nullable), `new_followup_datetime` (`DateTime(timezone=True)` NOT NULL), `current_update` (`String(120)` nullable), `remark` (`Text` NOT NULL), `rescheduled_by` (`String(32)` nullable), `created_at` (`DateTime(timezone=True)`).

### 4.5 `tbl_opportunity_activities` (`OpportunityActivity`)
- `id` (`Integer` PK), `opportunity_id` (FK `tbl_opportunities.opportunity_id` `ON DELETE CASCADE`, indexed), `action_type` (`String(40)` e.g. `CREATED`, `CALL`, `RESCHEDULE`, `STATUS_CHANGE`, `DEAL_SCHEDULED`, `CLOSED`, `DISQUALIFIED`, `TRANSFER`, `REOPEN`, `UPDATED`), `note` (`Text` nullable), `status_before` (`Integer` nullable), `status_after` (`Integer` nullable), `performed_by` (`String(32)` nullable), `created_at` (`DateTime(timezone=True)`).

---

## 5. Lifecycle, Scoping & Tab Definitions

### 5.1 Role Scoping
- Using `get_current_employee` (from `callbacks.py` or shared auth dep):
  - `SUPER_ADMIN`, `MD`, `SALES_MANAGER` view all non-deleted Opportunities.
  - Other roles view Opportunities where `assigned_to == actor.employee_id`.
- Every status transition, reschedule, transfer, reopen, and edit enforces the same role ownership scope (`403` otherwise) and returns `404` for soft-deleted/missing records.

### 5.2 Tab Semantics (IST Day Boundaries)
- `new` (**New Opportunity**): `lead_open == 1` AND `lead_status == 1` AND `calls_status == 0`
- `today` (**Today Opportunity**): `lead_open == 1` AND `followup_datetime` within `[IST today 00:00, IST today 23:59:59]`
- `open` (**Open Opportunity**): `lead_open == 1`
- `missing` (**Missing Opportunity**): `lead_open == 1` AND `followup_datetime IS NOT NULL` AND `followup_datetime < now_utc`
- `in_progress` (**In-Progress**): `lead_open == 1` AND `lead_status == 1`
- `closed` (**Closed**): `lead_open == 0` (`Disqualified` + `Closed Deal Done`)
- `all` (**All Opportunity**): all non-deleted Opportunities visible to actor

### 5.3 Deal & Registry Auto-Followup & Cancellation Rollback
- On Option 1 (**Qualified — Deal & Registry Schedule**):
  - `deal_date <= now_utc`.
  - For **Buy (`property_type == 2`)**: `registry_date` is required and must be strictly `> now_utc` (if violated → `HTTP 422`).
  - For **Rent (`property_type == 1`) / PG (`property_type == 3`)**: `registry_date` represents **Agreement / Move-in Date** and may be omitted or `>= deal_date`.
  - Auto-followup target: when `registry_date` is set and in the future, `followup_datetime = max(registry_date - timedelta(days=2), now_utc + timedelta(hours=1))` so pre-registry prep calls are never immediately flagged overdue. Record in `OpportunityRescheduleLog` & `OpportunityActivity(action_type="DEAL_SCHEDULED")`.
  - If `is_propira_property = True`: `matched_property_id` is required; verify `TblProperty` with `is_active == 1`, `verified_status == 1`, `sold_status == 0`, `recyclebin_status == 0`, `deleted_at IS NULL` (`404`/`400` if unavailable or already sold). If switching away from an earlier `matched_property_id`, revert the prior property's `sold_status` back to `0` (`Available`) before setting the new property's `sold_status = 1`.
- On Cancelling / Leaving `status = 4` (`4 -> 1 In Progress` or `4 -> 2 Disqualified`):
  - If an unpaid/unclosed `matched_property_id` (`is_propira_property = True`) was linked, atomically reset `TblProperty.sold_status = 0` (`Available`) and clear `deal_date`, `registry_date`, `is_propira_property`, `matched_property_id`, `matched_property_code` so the inventory returns to the market cleanly.
- On Option 2 (**Closed — Deal Done**):
  - If `opp.deal_date is None`: return `HTTP 400` with `detail="You cannot close this lead because the client has not yet Buy any property."`.
  - Otherwise set `lead_status = 5`, `lead_open = 0`, `closed_at = now_utc`, log `OpportunityActivity(action_type="CLOSED")`, and sync parent `Lead.stage = "WON"` / `TblLead` (`lead_status = 5`, `lead_open = 0`, `deal_date`, `registry_date`, `dealclose_date`).
- On **Reopen (`POST /v1/opportunities/{id}/reopen`)**:
  - Allowed when `lead_status == 2` (`Disqualified`): unlocks `lead_open = 1`, resets `lead_status = 1` (`In Progress`), `disqualified_reason = 0`, and syncs parent Lead back to `QUALIFIED` / `lead_open = 1` if linked.
  - Blocked (`HTTP 400`) if already open or permanently Closed (`lead_status == 5`).

---

## 8. Builder-Check Resolutions (Calls Made)
- **Live Available Inventory Scope:** `getrelatedProperty` and Option 1 Propira Deal linking filter strictly on `TblProperty.is_active == 1`, `verified_status == 1`, `sold_status == 0`, `recyclebin_status == 0`, `deleted_at IS NULL`, `(expiarydate IS NULL OR expiarydate >= now_utc)` — matching `PropertyHub`'s `verify_live` queue.
- **Bidirectional Lead Lifecycle Sync:** Converting sets `TblLead.lead_status = 4` & `Lead.stage = "QUALIFIED"` (preventing stale Kanban `New`/`In Progress` rows and duplicate conversion); closing (`status = 5`) sets `Lead.stage = "WON"` & `TblLead.lead_status = 5, lead_open = 0` (enabling `cp_governance_service` Referral Partner payouts); disqualifying/reopening stays synced.
- **Owner Contact Masking on `/related-properties`:** Internal CRM employees see owner name/mobile for coordinating visits; `FRANCHISEE_AGENT` or any actor tied to `ChannelPartner` inherits `cp_governance_service` tier checks and `cp_show_seller_contact` masking.

---

## 6. Backend API Endpoints (`/v1/opportunities`)

All endpoints require authenticated `Employee` (`Depends(get_current_employee)`).
- `GET /v1/opportunities/dashboard`: returns `{ counts: { new, today, open, missing, in_progress, closed, all }, chart_breakdown: { total, open, disqualified, qualified_propira, qualified_other, closed } }`.
- `GET /v1/opportunities`: filters `tab`, `search` (matches name, mobile, email, `opportunity_code`, locality, remark), `limit`, `offset` → list of `OpportunitySummary` including `matching_properties_count` so `"X Properties Found"` badge displays live in list/detail.
- `POST /v1/opportunities`: create Opportunity (standalone or linked via `source_lead_id`).
- `GET /v1/opportunities/export`: `.xls` downloadable spreadsheet (`application/vnd.ms-excel`) respecting `tab` & `search`. *(Registered before `/{opportunity_id}`.)*
- `GET /v1/opportunities/{opportunity_id}`: full 360° profile + `locations`, `activities`, `reschedules`, `matching_properties_count`.
- `PUT /v1/opportunities/{opportunity_id}`: update full requirements + locations (blocked if `lead_open == 0` → `HTTP 400`).
- `GET /v1/opportunities/{opportunity_id}/related-properties`: runs `getrelatedProperty` matching against `tbl_property` returning ranked available matches (`distance_km`, match reasons, owner info masked per role or internal view).
- `POST /v1/opportunities/{opportunity_id}/reschedule`: future `followup_datetime`, mandatory `remark`, `current_update`.
- `POST /v1/opportunities/{opportunity_id}/status`: transitions to `1` (In Progress), `2` (Disqualified), `4` (Qualified Option 1 Deal & Registry Schedule), or `5` (Option 2 Closed Deal Done).
- `POST /v1/opportunities/{opportunity_id}/transfer`: reassign `assigned_to` / `assign_franch_id` / `assign_franchstaff_id` (optionally resets `calls_status = 0` or logs `TRANSFER`, blocked when `lead_open == 0`).
- `POST /v1/opportunities/{opportunity_id}/reopen`: unlock disqualified Opportunity (`lead_status = 2` → `1`, `lead_open = 1`).
- `POST /v1/opportunities/{opportunity_id}/call-log`: mark `calls_status = 1` & append `CALL` activity (called alongside `tel:` click or call note modal).

---

## 7. Frontend Architecture

- **New Page & Subcomponents:**
  - `frontend/src/types/opportunities.ts`: interfaces & status/reason/category/subcat constants.
  - `frontend/src/pages/OpportunitiesHub.tsx`: replaces `/opportunities` placeholder in `App.tsx`.
    - Top summary strip (`Today`, `Missing`, Recharts donut/bar chart breakdown).
    - **Split-Screen 2-Pane Workspace:** Left list (`new/today/open/missing/all/in_progress/closed` tabs + search + Web Speech API Voice Mic button + Excel Export + `+ Create Opportunity`); Right 360° dossier + `"X Properties Found"` green badge + Quick Action Toolbar + Related Properties popup modal + Status/Deal Schedule modal + Reschedule modal + Transfer modal + Create/Edit modal + Activity Timeline modal.
  - Multi-locality component supporting Google Places Autocomplete when `import.meta.env.VITE_GOOGLE_MAPS_API_KEY` is present, with automatic city/area coordinate preset & manual lat/lng fallback.
- **Navigation (`AdminLayout.tsx`) & Lead Integration (`LeadDetail.tsx`):**
  - Update `AdminLayout.tsx` `OPPORTUNITIES` submenu links to match Opportunity tabs (`/opportunities?tab=new`, `today`, `missing`, `in_progress`, `closed`, `?action=create`).
  - Update `LeadDetail.tsx` with **"Convert to Opportunity"** CTA (hero + action/card button) navigating to `/opportunities?fromLead={leadUid}` (which auto-opens pre-filled Create Opportunity modal) or viewing existing linked Opportunity (`OPP-YYYY-NNNNNN`) when `lead.opportunity_converted === 1`.
