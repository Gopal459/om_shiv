# Website Forms (Request A Callback & Report A Problem) — Design Specification

- **Date:** 2026-11-27
- **Author:** AlwarMap Engineering
- **Status:** Approved Ready for User Sign-Off (Builder Check Resolved)
- **Theme Alignment:** AlwarMap Royal Indigo (`#291BB0`) & Coral Accent (`#F04B42`)

---

## 1. Intent and Why

Public website and mobile app visitors submit two primary intake forms:
1. **Request A Callback** (contact page / property detail callback widget with Name, Mobile, Country Code, Message, Optional Property ID).
2. **Report A Problem** (broken listing, wrong price/owner info, or portal issue).

Today `/website-forms` in the Admin panel renders a static placeholder (`ModuleHub`) with hardcoded metrics, and `website_inquiries` lacks automated calling-team round-robin assignment, `WEB{id}` tracking IDs, follow-up reschedule audit trails, lock/unlock protection (`lead_open`), disqualification reasons, call transfers, Excel exports, and a structured `Convert to Lead` form.

This specification defines a complete, relational backend and master-detail Admin workspace for **Request A Callback** and **Report A Problem** inside the existing FastAPI + React/Tailwind AlwarMap CRM.

---

## 2. Goals, Non-Goals, and Anti-Goals

### 2.1 Goals
- **Dedicated Callback Tables (`0013` migration):** `tbl_callback`, `tbl_leadreschedule_followup`, and `tbl_callback_activities`, plus triage status/resolution columns on `website_inquiries` for `PROBLEM_REPORT`.
- **Auto Round-Robin Assignment (`TELECALLER`):** Incoming callbacks assign automatically in fair round-robin order to active `employees` with `Role.code == "TELECALLER"` (`is_active=True`, `is_on_leave=False`, `deleted_at IS NULL`).
- **Auto Unique Code:** Every new callback receives `lead_unique_id = f"WEB{callback_id}"` immediately on creation, plus an initial `"Received"` activity log.
- **Full Callback Lifecycle State Machine:**
  - Status codes `0..6`: `0=New`, `1=In Progress`, `2=Disqualified`, `3=Solved`, `4=Qualified`, `5=Converted to Lead`, `6=Converted Property`.
  - Lock/unlock rule (`lead_open`): Setting status `2` (Disqualified) or `3` (Solved) or `5` (Converted to Lead) or `6` (Converted Property) automatically locks `lead_open = 0`. Locked callbacks block **Reschedule Follow-Up** and **Call Transfer** until unlocked via **Reopen Lead**.
  - Disqualification (`lead_status = 2`) requires `disqualified_reason` (`1..7`).
  - Reschedule Follow-Up validates `followup_datetime > now()` strictly and logs old & new datetimes into `tbl_leadreschedule_followup`.
  - Call Transfer resets `lead_status = 0` (`New`) and `calls_status = 0` so it appears in the new assignee's `New Calls` tab.
  - **Convert to Lead** opens the full conversion form (`Customer Type`, `Name`, `Email`, `Mobile`, `Alternate Mobile No`, `Address`, `Refer By`, `Source`, `Assignee`) and atomically creates both an active `Lead` (`OB-YYYY-NNNNNN`) and a synced `TblLead` (`tbl_leads`, `source = "Website Callback"`), marking `tbl_callback.lead_status = 5`, `lead_converted = 1`, `lead_open = 0`.
- **Dashboard Summary & 7 Filter Tabs:** `Home / New Calls`, `Today Calls`, `Open Calls`, `Missing Calls`, `Converted Lead`, `All Calls`, `Converted Property` with live counts scoped by user role (`SUPER_ADMIN` / `SALES_MANAGER` see all; `TELECALLER` sees assigned callbacks).
- **Excel Export:** Export currently filtered callbacks (and problem reports) directly as downloadable Excel `.xls` (`application/vnd.ms-excel` HTML-table workbook requiring zero external Python libraries).
- **Report A Problem Triage:** Sidebar sub-item `/website-forms?tab=problems` manages `WebsiteInquiry(inquiry_type="PROBLEM_REPORT")` rows with status updates (`NEW`, `IN_REVIEW`, `RESOLVED`, `REJECTED`), staff assignment, resolution remarks, 1-click convert to lead, and `.xls` export.

### 2.2 Non-Goals
- Public visitor-facing React website pages (this delivers public intake APIs `POST /v1/intake/callback` + existing `POST /v1/intake/inquiry` and the Admin/Telecaller CRM UI).
- Built-in WebRTC/VoIP calling dialer (`tel:` link + logged call interaction & `calls_status` updates are used).

### 2.3 Anti-Goals
- Never hardcode employee names or fixed numeric `designations_id = 7` checks against missing legacy tables; query `Role.code == "TELECALLER"` dynamically via `roles` + `employees`.
- Never mutate locked (`lead_open == 0`) or converted (`lead_status == 5`) callbacks on reschedule/transfer without explicit reopen.
- Never allow dual-source divergence: `POST /v1/intake/inquiry` with `inquiry_type="CALLBACK"` must also create a synced `tbl_callback` record.

---

## 3. Approaches Considered and Selection

- **Approach A (Selected): Dedicated `tbl_callback`, `tbl_leadreschedule_followup`, and `tbl_callback_activities` tables + `website_inquiries` triage columns**
  - Cleanly matches the PHP CRM data model (`WEB{id}`, reschedule datetime history, lock state, missing-call queries) while integrating cleanly with `employees.employee_id`, `leads`, and `tbl_leads`.
- **Approach B (Rejected): Extending `website_inquiries` JSON `details` only**
  - Rejected because JSON history/dates break clean SQL filtering for `Today Calls` / `Missing Calls` / `tbl_leadreschedule_followup` and deviate from the explicit `tbl_callback` schema.

---

## 4. Database Schema & Migrations

Migration file: `backend/app/db/migrations/0013_website_forms_callback_schema.py` (added to `MIGRATION_STEPS` in `runner.py`).

### 4.1 `tbl_callback` (`TblCallback`)
| Column | Type | Notes |
|---|---|---|
| `callback_id` | `Integer` PK, AI | Primary key |
| `lead_unique_id` | `String(64)` unique, indexed, nullable initially | Updated to `f"WEB{callback_id}"` immediately after flush |
| `name` | `String(255)` NOT NULL | Customer name |
| `mobile_number` | `String(32)` NOT NULL, indexed | Stored digits / cleaned mobile |
| `phone_code` | `String(16)` default `"+91"` | Country code |
| `message` | `Text` nullable | Customer inquiry message |
| `property_id` | `Integer` nullable | Optional numeric `properties.id` |
| `property_code` | `String(32)` nullable | Optional listing code e.g. `OP-2026-00001` |
| `assigned_user_id` | `String(32)` FK `employees.employee_id` (`ON DELETE SET NULL`), nullable, indexed | Auto-assigned `TELECALLER` |
| `lead_status` | `Integer` default `0`, NOT NULL, indexed | `0=New, 1=In Progress, 2=Disqualified, 3=Solved, 4=Qualified, 5=Converted to Lead, 6=Converted Property` |
| `calls_status` | `Integer` default `0`, NOT NULL | `0=Not Called, 1=Connected` |
| `lead_open` | `Integer` default `1`, NOT NULL, indexed | `1=Open/Active, 0=Closed/Locked` |
| `disqualified_reason` | `Integer` default `0`, NOT NULL | `0=None, 1..7` reasons |
| `current_update` | `String(120)` nullable | Latest follow-up update category (e.g. `Interested`, `Call Back Later`, `Site Visit Planned`, `Price Discussion`) |
| `last_remark` | `Text` nullable | Latest telecaller remark |
| `followup_datetime` | `DateTime(timezone=True)` nullable, indexed | Next scheduled follow-up |
| `opportunity_converted` | `Integer` default `0`, NOT NULL | `0/1` |
| `lead_converted` | `Integer` default `0`, NOT NULL | `0/1` |
| `converted_lead_id` | `String(32)` nullable | Linked `OB-YYYY-NNNNNN` after conversion |
| `website_inquiry_id` | `Integer` FK `website_inquiries.id` (`ON DELETE SET NULL`), nullable, indexed | Cross-reference when submitted via `POST /v1/intake/inquiry` (`inquiry_type="CALLBACK"`) to prevent duplicate conversion |
| `deleted_at` | `DateTime(timezone=True)` nullable, indexed | Soft delete support |
| `created_date` | `DateTime(timezone=True)` default UTC now, NOT NULL, indexed | Created timestamp |
| `modified_date` | `DateTime(timezone=True)` default/onupdate UTC now, NOT NULL | Modified timestamp |

### 4.2 `tbl_leadreschedule_followup` (`CallbackRescheduleLog`)
| Column | Type | Notes |
|---|---|---|
| `id` | `Integer` PK, AI | |
| `callback_id` | `Integer` FK `tbl_callback.callback_id` (`ON DELETE CASCADE`), indexed | |
| `old_followup_datetime` | `DateTime(timezone=True)` nullable | Previous schedule |
| `new_followup_datetime` | `DateTime(timezone=True)` NOT NULL | New future schedule |
| `current_update` | `String(120)` nullable | Update category chosen in modal |
| `remark` | `Text` NOT NULL | Mandatory remark |
| `rescheduled_by` | `String(32)` nullable | `employee_id` of actor |
| `created_at` | `DateTime(timezone=True)` default UTC now, NOT NULL | |

### 4.3 `tbl_callback_activities` (`CallbackActivity`)
| Column | Type | Notes |
|---|---|---|
| `id` | `Integer` PK, AI | |
| `callback_id` | `Integer` FK `tbl_callback.callback_id` (`ON DELETE CASCADE`), indexed | |
| `action_type` | `String(32)` NOT NULL | `RECEIVED`, `CALL_LOG`, `RESCHEDULED`, `STATUS_CHANGED`, `TRANSFERRED`, `REOPENED`, `CONVERTED` |
| `title` | `String(120)` NOT NULL | e.g. `"Received"`, `"Rescheduled"`, `"Status Changed"` |
| `status_before` | `Integer` nullable | Prior `lead_status` |
| `status_after` | `Integer` nullable | New `lead_status` |
| `remark` | `Text` nullable | Action note |
| `performed_by` | `String(32)` nullable | `employee_id` or `"SYSTEM"` |
| `created_at` | `DateTime(timezone=True)` default UTC now, NOT NULL | |

### 4.4 `website_inquiries` Extensions (for Report A Problem)
Add safe nullable/defaulted columns via `ALTER TABLE` (idempotent in migration `0013` and model `WebsiteInquiry`):
- `status` (`String(32)`, default `"NEW"`, nullable=False — `NEW`, `IN_REVIEW`, `RESOLVED`, `REJECTED`)
- `assigned_to` (`String(32)`, FK `employees.employee_id` `ON DELETE SET NULL`, nullable=True)
- `related_property_code` (`String(32)`, nullable=True)
- `resolution_remark` (`Text`, nullable=True)
- `resolved_by` (`String(32)`, nullable=True)
- `resolved_at` (`DateTime(timezone=True)`, nullable=True)
- `updated_at` (`DateTime(timezone=True)`, default UTC now, onupdate UTC now, nullable=True)

---

## 5. Business Logic & Constants

### 5.1 Round-Robin Telecaller Assignment
1. Fetch all active, non-deleted `Employee` rows joined with `Role` where `Role.code == "TELECALLER"`, `Employee.is_active == True`, `Employee.is_on_leave == False`, `Employee.deleted_at IS NULL`.
2. Count assigned `tbl_callback` rows (plus `MAX(created_date)` per employee) for candidate IDs.
3. Sort by `(total_assigned_callbacks ASC, latest_assigned_created_date ASC nulls first, employee_id ASC)` and pick index `0`.
4. If no active `TELECALLER` exists, leave `assigned_user_id = None` (so public submission still succeeds and Admin can assign manually).

### 5.2 Disqualification Reasons (`DISQUALIFIED_REASONS`)
1. `Inaccurate Data`
2. `Not Interested`
3. `Not Response`
4. `Call Me Later`
5. `Disconnecting Call`
6. `Rejected`
7. `Other`

### 5.3 Status Map (`CALLBACK_STATUSES`) & State-Machine Guards
- `0`: `New`
- `1`: `In Progress`
- `2`: `Disqualified` *(auto-locks `lead_open = 0`; requires `disqualified_reason` in `1..7`)*
- `3`: `Solved` *(auto-locks `lead_open = 0`)*
- `4`: `Qualified`
- `5`: `Converted to Lead` *(auto-locks `lead_open = 0`, `lead_converted = 1`)*
- `6`: `Converted Property` *(terminal status option via `Change Status` & dashboard filter tab only — **not** a property-creation conversion flow; auto-locks `lead_open = 0`, `lead_converted = 1`)*

**State-Machine Lock Guards:**
- While `lead_open == 0`: **Reschedule**, **Call Transfer**, **Change Status**, and **Convert to Lead** are all rejected (`400 Bad Request`).
- Terminal converted records (`lead_status IN (5, 6)` or `lead_converted == 1`): permanently locked — **Reopen Lead** is only permitted for `lead_status IN (2, 3)` (`Disqualified` / `Solved`) and returns `400` on `5` or `6`.

### 5.4 Dashboard Tab Filters
Timezone boundary for `Today` / `Missing` uses IST (`UTC+05:30`) day start/end converted to UTC for consistent SQL comparisons across SQLite & PostgreSQL:
- **Home / New Calls (`new`):** `lead_status == 0`
- **Today Calls (`today`):** `followup_datetime >= today_start_utc AND followup_datetime <= today_end_utc AND lead_open == 1`
- **Open Calls (`open`):** `lead_open == 1`
- **Missing Calls (`missing`):** `followup_datetime IS NOT NULL AND followup_datetime < now_utc AND lead_open == 1 AND lead_status NOT IN (2, 3, 5, 6)`
- **Converted Lead (`converted`):** `lead_status == 5`
- **All Calls (`all`):** all non-deleted records within user's visibility scope
- **Converted Property (`converted_property`):** `lead_status == 6`

### 5.5 Visibility Scope & Authorization *(Includes Builder Calls)*
- **Callback Read / List Scope:** `SUPER_ADMIN`, `SALES_MANAGER`, or roles with `leads.view_all` see all callbacks; `TELECALLER` and other staff without `view_all` see callbacks where `assigned_user_id == actor_emp_id`.
- **Callback Actions (`reschedule`, `status`, `transfer`, `reopen`, `log-call`, `convert-to-lead`, `export`):** Any authenticated staff member who has visibility access to the callback can perform these actions on it (matching calling-team handoff and reopen workflow); `POST /v1/callbacks/{id}/status` blocks setting `5` directly (`5` must go through `/convert-to-lead`).
- **Report A Problem Permissions *(Builder Call)*:** `SUPER_ADMIN`, `SALES_MANAGER`, `VERIFICATION_OFFICER`, or roles with `leads.view_all` / `properties.verify` view and triage all `PROBLEM_REPORT` items (`GET`, `PATCH`, `convert-to-lead`, `export`); other roles see only items where `assigned_to == actor_emp_id`.
- Missing/invalid auth token on CRM routes returns `401 Unauthorized` (only `POST /v1/intake/callback` and `POST /v1/intake/inquiry` are public).

---

## 6. API Contract

### 6.1 Public Intake Endpoints (`/v1/intake`)
- `POST /v1/intake/callback`:
  - Payload: `{ name: str (required, non-blank), mobile_number (alias phone): str (required), phone_code: str (default "+91"), message?: str, property_id?: int, property_code?: str }`
  - **Intake Rule *(Builder Call)*:** Does **not** apply 24h lead deduplication or test-number suppression — every valid public callback request creates a fresh `WEB{callback_id}` record in `tbl_callback` so customer callback commitments are never silently dropped, assigns active `TELECALLER` via round-robin, logs `"Received"`, and returns `201 Created` (`{ ...CallbackResponse }`). Does not duplicate into `website_inquiries`.
- `POST /v1/intake/inquiry`:
  - When `inquiry_type == "CALLBACK"`, creates `WebsiteInquiry` **and** automatically creates a linked `tbl_callback` row (`website_inquiry_id = inquiry.id`) with `WEB{id}` + round-robin assignment.
  - Converting either side (`POST /v1/callbacks/{id}/convert-to-lead` or `POST /v1/crm/inquiries/{id}/convert-to-lead`) atomically syncs `is_converted=True, converted_lead_id=...` on the paired `WebsiteInquiry` and `lead_status=5, lead_converted=1, lead_open=0, converted_lead_id=...` on any paired `TblCallback` to prevent duplicate conversion.

### 6.2 Callback CRM Endpoints (`/v1/callbacks`)
- `POST /v1/callbacks` *(Authenticated Manual Entry — Builder Call)*:
  - Used by the `+ New Callback` modal. Accepts `{ name, mobile_number, phone_code?, message?, property_id?, property_code?, assigned_user_id? }`.
  - If `assigned_user_id` is provided (for `view_all` managers), assigns to that employee; otherwise if the creator is a scoped `TELECALLER` without `view_all`, defaults `assigned_user_id` to creator (`actor_emp_id`) so the record stays in their view; otherwise runs round-robin `TELECALLER` assignment. Returns `201 Created`.
- `GET /v1/callbacks/dashboard` -> `{ new_calls, today_calls, open_calls, missing_calls, converted_leads, all_calls, converted_property }`
- `GET /v1/callbacks` -> params `tab` (`new|today|open|missing|converted|all|converted_property`), `search`, `sort_by` (`created_date|followup_datetime|name|callback_id`), `order_by` (`asc|desc`), `limit`, `offset`. Returns `{ total, items: CallbackSummary[] }`.
- `GET /v1/callbacks/assignees` -> active staff list for Call Transfer / Convert-to-Lead / Manual Callback Assignee dropdowns (`employee_id`, `name`, `role_name`, `role_code`, `is_active`).
- `GET /v1/callbacks/{callback_id}` -> detailed record + `reschedule_history` + `activities` + `assigned_user_name` + `property_title` (if resolved).
- `POST /v1/callbacks/{callback_id}/log-call` -> `{ calls_status: 1, remark?: str }` logs call attempt/connected event without overwriting follow-up schedule.
- `POST /v1/callbacks/{callback_id}/reschedule` -> `{ current_update: str, remark: str, followup_datetime: datetime }`. Validates `lead_open == 1`, `lead_status != 5`, `followup_datetime > now_utc`. Returns `400` with exact message `"This Callback is closed so you cannot reschedule it."` / `"Schedule Date and Time should be greater than the current date and time."` on violation.
- `POST /v1/callbacks/{callback_id}/status` -> `{ lead_status: int (0..4, 6), remark: str, disqualified_reason?: int (1..7), calls_status?: int }`. Requires `lead_open == 1`. Requires `disqualified_reason` when `lead_status == 2`. Rejects `lead_status == 5` (must use `/convert-to-lead`). Auto-sets `lead_open = 0` when `lead_status in (2, 3, 6)` (and `lead_converted = 1` for `6`).
- `POST /v1/callbacks/{callback_id}/transfer` -> `{ assigned_user_id: str, remark: str }`. Validates `lead_open == 1` & `lead_status NOT IN (5, 6)`. Resets `lead_status = 0`, `calls_status = 0`.
- `POST /v1/callbacks/{callback_id}/reopen` -> `{ remark?: str }`. Allowed only when `lead_open == 0` and `lead_status IN (2, 3)`. Sets `lead_open = 1`, moves `lead_status` to `1` (`In Progress`), logs `"Reopened"`.
- `POST /v1/callbacks/{callback_id}/convert-to-lead` -> `{ customer_type: str ("BUY"|"RENT"|"PG"|"BUYER"|...), name: str, email?: str, mobile: str, alternate_mobile?: str, address: str, refer_by_relation?: str, refer_by_name?: str, refer_by_mobile?: str, source: str (default "Website Callback"), assigned_to?: str }`. Rejects if `lead_open == 0` or `lead_converted == 1`. Creates synced `Lead` (`OB-YYYY-NNNNNN`) + `TblLead` (`tbl_leads`), updates `tbl_callback` (`lead_status = 5`, `lead_converted = 1`, `lead_open = 0`, `converted_lead_id = lead_id`), syncs paired `WebsiteInquiry` if linked, and logs `"Converted to Lead"`.
- `GET /v1/callbacks/export` -> accepts same `tab`, `search`, `sort_by`, `order_by` filters; returns Excel `.xls` (`application/vnd.ms-excel`) download.

### 6.3 Report A Problem Endpoints (`/v1/problems`)
- `GET /v1/problems` -> params `status` (`ALL|NEW|IN_REVIEW|RESOLVED|REJECTED`), `search`, `limit`, `offset` -> returns `{ total, counts: { all, new, in_review, resolved, rejected }, items }`.
- `PATCH /v1/problems/{inquiry_id}` -> update `status`, `assigned_to`, `resolution_remark`.
- `POST /v1/problems/{inquiry_id}/convert-to-lead` -> proxies `intake_service.convert_inquiry_to_lead`.
- `GET /v1/problems/export` -> downloadable `.xls` report.

---

## 7. Frontend Architecture (`AlwarMap` Theme)

- **Sidebar (`AdminLayout.tsx`):** Under `Website Forms`:
  - `Request A Callback` -> `/website-forms?tab=callbacks`
  - `Report A Problem` -> `/website-forms?tab=problems`
- **Route (`/website-forms` in `App.tsx`):** Replace `<ModuleHub>` with `<WebsiteFormsHub />`.
- **`WebsiteFormsHub.tsx` (`frontend/src/pages/WebsiteFormsHub.tsx`):**
  - **Request A Callback mode:**
    - Top header bar with live 7-tab pills & counters (`Home / New`, `Today Calls`, `Open Calls`, `Missing Calls`, `Converted Lead`, `All Calls`, `Converted Property`), `+ New Callback` manual log button, and `Export .xls` button.
    - **Master-Detail Split Layout:**
      - Left panel (~340px–380px): Search input, `Sort By` (`Created Date`, `Follow-up Date`, `Name`), `Order By` (`DESC`, `ASC`), scrollable callback cards displaying customer name, `WEBxxx`, timestamp, assigned caller, and semantic status badge.
      - Right panel: Customer name, `+91-mobile`, status badge, **Lock indicator pill (`Open` / `Closed — Reopen required`)**, and **6 Quick-Action circular buttons** + explicit `Change Status` button:
        1. Call / Log (`tel:` + log connected call)
        2. Reschedule Follow-Up (disabled when `lead_open == 0` or `lead_status == 5`)
        3. Lead Open/Close Toggle (opens Change Status or triggers Reopen Lead when locked)
        4. Call Transfer (disabled when locked/converted)
        5. Convert to Lead (switches right pane or modal to full Conversion Form with Customer Type, Name, Email, Mobile, Alternate Mobile No, Address, Refer By, Source, Assignee)
        6. Activity & Reschedule History
      - Details sections: `Contact Details` (`Follow Up Remark`, `Request ID` `WEBxxx`, `Customer Name`, `Mobile No.`, `Current Update`, `Status`, `Disqualification Reason`, `Message`, `Linked Property`) and `Others` (`Receive Date`, `Followup Date`, `Assigned Telecaller`, `Converted Lead ID`).
  - **Report A Problem mode (`?tab=problems`):**
    - Status filter chips (`All`, `New`, `In Review`, `Resolved`, `Rejected`) + search + `.xls` export.
    - Master-detail view showing reporter name, mobile, email, property code/details, problem description, assignee dropdown, resolution status/remark form, and 1-Click `Convert to Lead`.

---

## 8. Builder Handoff Notes
- Build using existing SQLAlchemy async session patterns (`get_db`), `auth.py` JWT user lookup (`Employee` + `Role`), and Vite Tailwind classes (`#291BB0` primary, `#F04B42` accent).
- Add comprehensive `pytest` integration tests in `backend/tests/test_callbacks_and_problems_api.py` covering round-robin assignment, `WEB{id}` generation, strict future datetime validation, `lead_open` lock/unlock blocking reschedule/transfer, disqualification reason enforcement, transfer reset to `New`, Convert to Lead (`Lead` + `TblLead`), `.xls` export, and Report A Problem updates.
