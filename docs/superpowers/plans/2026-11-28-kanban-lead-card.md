# Kanban Lead Card Enrichment & UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich `/v1/leads/kanban` with requirement headline, source/assignee names, follow-up datetime, and current update status, fix the literal `0` rendering bug, and redesign `LeadKanbanBoard.tsx` cards to display all 1st-screenshot details in clean AlwarMap (`#291BB0` / `#F04B42`) styling.

**Architecture:** One batch-enriched backend query inside `GET /v1/leads/kanban` (`leads.py`) joining `Lead`, `Employee`, and `Property` metadata cleanly (zero N+1 queries), paired with a redesigned 5-row Kanban card in `LeadKanbanBoard.tsx` backwards-compatible with `LeadTableView.tsx`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pytest, React 18, TypeScript, Tailwind CSS, Lucide Icons.

**Spec:** [docs/superpowers/specs/2026-11-28-kanban-lead-card-design.md](file:///c:/xampp/htdocs/om_shiv/docs/superpowers/specs/2026-11-28-kanban-lead-card-design.md)

## Global Constraints
- Never break existing `/v1/leads/kanban` field names (`leads_id`, `lead_unique_id`, `contact_name`, `mobile`, `email`, `address`, `lead_type`, `rating`, `lead_status`, `stage`, `property_address`, `deal_final_price`, `lead_remark`, `created_date`).
- All serialized datetimes from SQLite/PostgreSQL must carry UTC tzinfo (`+00:00`) via `_ensure_utc_iso`.
- Never render raw falsy numeric `0` in JSX (`Boolean(...)` or explicit `> 0` ternary).
- Primary CTA / hover / active brand colors use `#291BB0` and `#F04B42`.

## Review Focus
1. **Zero Budget Falsy Render:** A lead with `deal_final_price = 0` must never display `0` anywhere in the card UI.
2. **N+1 Queries & Missing Relations:** A Kanban board with `TblLead`-only rows (no paired `Lead`, `Employee`, or `Property`) must safely populate sensible defaults (`"Om Shiv Properties"`, `"General Follow-Up"`, requirement fallback) without raising `AttributeError` or `None` crashes.
3. **Naive SQLite Dates:** `created_date` and `followup_datetime` serialized from SQLite must emit `+00:00` UTC offsets so frontend `DD-MMM-YYYY hh:mm A` formatting displays accurate IST times.
4. **Long Addresses & Text Wrapping:** Long street addresses or remarks must truncate cleanly (`line-clamp-1` / `truncate`) without blowing out the `w-80` Kanban column width.
5. **Drag & Quick-Action Event Propagation:** Clicking `Call`, `WhatsApp`, or `Next Stage >` must call `e.stopPropagation()` and never accidentally open `onSelectLead`.

---

### Task 1: Enrich `/v1/leads/kanban` Backend Response (TDD)

**Files:**
- Modify: `backend/app/api/v1/endpoints/leads.py:337-402`
- Test: `backend/tests/test_lead_inflow_and_kanban.py`

**Interfaces:**
- Produces enriched fields on each `KanbanLeadItem` dict in `GET /v1/leads/kanban`:
  - `requirement_title: str`
  - `source_name: str`
  - `assigned_to: Optional[str]`
  - `assigned_to_name: str`
  - `followup_datetime: Optional[str]`
  - `current_update: str`
  - `status_label: str`

- [ ] **Step 1: Write failing test in `backend/tests/test_lead_inflow_and_kanban.py`**

Add `test_kanban_card_enrichment_fields_and_utc_dates` testing a created/converted lead (and a `TblLead` linked with `Lead.assigned_to` + `follow_up_date`) and asserting `/v1/leads/kanban` returns `requirement_title`, `source_name`, `assigned_to_name`, UTC-offset `created_date` & `followup_datetime` (`+00:00`), `current_update`, and `status_label`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\pytest.exe backend/tests/test_lead_inflow_and_kanban.py -v`
Expected: FAIL because `requirement_title` / `assigned_to_name` / `current_update` are missing.

- [ ] **Step 3: Implement batch enrichment in `get_kanban_board` (`backend/app/api/v1/endpoints/leads.py`)**

Batch-query `Lead` (`Lead.lead_id.in_(unique_ids)` + selectinload `activities`), `Employee` (`Employee.employee_id.in_(assignee_ids)`), and `Property` (`Property.property_id.in_(listing_ids)` or `Property.id.in_(prop_ids)`) once, normalize datetimes to UTC ISO, resolve `requirement_title`, `source_name`, `assigned_to_name` (fallback `"Om Shiv Properties"`), `followup_datetime`, `current_update` (fallback `"General Follow-Up"`), and `status_label`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\pytest.exe backend/tests/test_lead_inflow_and_kanban.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/leads.py backend/tests/test_lead_inflow_and_kanban.py
git commit -m "feat(leads): enrich kanban card payload with requirement, assignee, followup, and update fields"
```

---

### Task 2: Redesign `LeadKanbanBoard.tsx` Lead Card UI & Fix `0` Bug

**Files:**
- Modify: `frontend/src/components/leads/LeadKanbanBoard.tsx:1-371`

**Interfaces:**
- Consumes enriched optional fields on `KanbanLeadItem` (`requirement_title`, `source_name`, `assigned_to`, `assigned_to_name`, `followup_datetime`, `current_update`, `status_label`), backwards-compatible with `LeadTableView.tsx`.

- [ ] **Step 1: Extend `KanbanLeadItem` interface and add clean IST date/INR formatters in `LeadKanbanBoard.tsx`**

Add `formatCardDate` (`DD-MMM-YYYY`) and `formatCardDateTime` (`DD-MMM-YYYY hh:mm A`), plus helper `getStatusPill(lead_status, stage)` returning semantic colored pill label (`New`, `In Progress`, `Site Visit`, `Qualified`, `Converted`, `Disqualified`).

- [ ] **Step 2: Redesign card markup matching 1st-screenshot 5-row structure & fix falsy `0` bug**

Render:
1. Top header row (above hairline border): Requirement title (`lead.requirement_title || ...`) + Drag grip + compact `lead_unique_id` & `lead_type` badge.
2. Row 2: `User` icon + `lead.contact_name` (left) | `formatCardDate(lead.created_date)` (right).
3. Row 3: `MapPin` icon + `lead.address || lead.property_address` + INR price pill strictly guarded with `Number(lead.deal_final_price) > 0 ? ... : null` (never rendering `0`).
4. Row 4: Temperature tag pill (`Hot` / `Warm` / `Cold`) + `Bookmark` icon + `lead.assigned_to_name || lead.source_name || 'Om Shiv Properties'` + `Clock` icon + `formatCardDateTime(lead.followup_datetime || lead.created_date)`.
5. Row 5: `TrendingUp` icon + `lead.current_update || lead.lead_remark || 'General Follow-Up'` (left) + Status badge pill (right).
6. Compact footer action bar: Call (`tel:`), WhatsApp (`wa.me`), and `Next Stage >` (`bg-[#291BB0]` hover styling) with `e.stopPropagation()`.

- [ ] **Step 3: Verify TypeScript build & full backend suite**

Run: `.\.venv\Scripts\pytest.exe backend/tests -q` and `npm --prefix c:\xampp\htdocs\om_shiv\frontend run build`
Expected: All backend tests pass and Vite `tsc && vite build` exits 0 cleanly.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/leads/LeadKanbanBoard.tsx
git commit -m "style(leads): redesign Kanban lead card with full details and fix zero price bug"
```
