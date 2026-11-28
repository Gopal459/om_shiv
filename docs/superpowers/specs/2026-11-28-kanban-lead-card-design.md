# Kanban Lead Card Enrichment & UI Redesign — Short Design Specification

- **Date:** 2026-11-28
- **Status:** Approved
- **Theme Alignment:** AlwarMap Royal Indigo (`#291BB0`) & Coral Accent (`#F04B42`)

---

## 1. Intent & Why
The Kanban Lead Card in `/leads` (`LeadKanbanBoard.tsx`) currently renders too sparsely compared to the legacy Omshiv card layout and contains a JSX falsy-number bug where `deal_final_price = 0` prints literal `0` under the address. Enriching `/v1/leads/kanban` and redesigning the card layout brings full lead context (requirement headline, created date, full address, temperature ribbon, assigned rep / source, follow-up/call datetime, current update/remark, status pill) directly onto every Kanban card while preserving drag-and-drop and quick actions.

## 2. Scope & Changes
- **Backend (`backend/app/api/v1/endpoints/leads.py` `GET /v1/leads/kanban`):**
  - Batch-load paired `Lead` records (`Lead.lead_id.in_(unique_ids)`), assigned `Employee` names (`Employee.employee_id.in_(assignee_ids)`), and `Property` titles (`Property.property_id` or `Property.id`), avoiding N+1 queries.
  - Enrich each serialized card dictionary (preserving all existing fields cleanly) with:
    - `requirement_title`: resolved `property_title` if linked, else derived from `lead_remark` / `BUY / RENT / PG` requirement (never `"N/A"`).
    - `source_name`: `LEAD_SOURCES_MAP.get(lead_source_id, "Website Inbound Inquiry")` (or mapped modern `source`).
    - `assigned_to`: `Lead.assigned_to` or `Staff #{assign_franchstaff_id}` if > 0.
    - `assigned_to_name`: resolved `Employee.name` or `"Om Shiv Properties"`.
    - `followup_datetime`: ISO-UTC string of `Lead.follow_up_date` or `TblLead.nextfollowup_datetime` or `TblLead.last_callstatus_updatetime` or `created_date`.
    - `current_update`: `CURRENT_UPDATE_OPTIONS` label / `latest LeadActivity.outcome` / `lead_remark` / `"General Follow-Up"`.
    - Ensure `created_date` emits UTC-aware ISO strings (`+00:00`) even on SQLite.
- **Frontend (`frontend/src/components/leads/LeadKanbanBoard.tsx`):**
  - Fix `{Boolean(lead.deal_final_price && lead.deal_final_price > 0) && ...}` so `0` never renders.
  - Render polished 5-row AlwarMap card matching the legacy reference screenshot:
    1. Top row: Requirement headline + `lead_unique_id` (`OB-...`) + Drag Grip + `lead_type` badge.
    2. Row 2: `User` icon + `contact_name` (left) | formatted `created_date` `DD-MMM-YYYY` (right).
    3. Row 3: `MapPin` icon + full `address || property_address` + INR price pill when `> 0`.
    4. Row 4: Temperature tag (`Hot` / `Warm` / `Cold`) + `Bookmark` icon + `assigned_to_name` (`Om Shiv Properties` fallback) + `Clock` icon + formatted `followup_datetime`.
    5. Row 5 + Footer: `TrendingUp` icon + `current_update` (left) + Status badge (`New`, `In Progress`, `Site Visit`, `Qualified`, `Deal Closed`, `Disqualified`) (right), plus compact Call, WhatsApp, and `Next Stage >` controls in `#291BB0` / `#F04B42` styling.

## 3. Approaches Considered
- **Selected:** Extend existing `GET /v1/leads/kanban` response in-place with batch lookups and redesign `LeadKanbanBoard.tsx` card. Zero DB migrations, zero extra HTTP requests per card.
- **Rejected:** Calling `GET /v1/leads/{id}` per card from React (N+1 waterfall) or adding a new table.
