# Enterprise Leads Management, Inflow Pipeline & Kanban Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete enterprise leads ecosystem including `tbl_leads` 54-field database migration, 6 inbound inflow handlers, dual-mode Kanban & Data Table views, Screenshot-1 sidebar submenus (Buy, Rent, PG, Create, Import), and Screenshot 2 & 3 pixel-perfect Lead Detail view.

**Architecture:** Full-stack async FastAPI backend with migration runner and repository pattern for `tbl_leads`, connected to a React 18 + TypeScript + Tailwind frontend featuring a dual-mode Kanban/Table interface and modular modal flows for manual creation and bulk CSV/Excel import.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), SQLite/MySQL, React 18, TypeScript, Tailwind CSS, Lucide React, Bun/Vite.

**Spec:** [docs/superpowers/specs/2026-11-23-leads-management-and-kanban-design.md](file:///c:/xampp/htdocs/om_shiv/docs/superpowers/specs/2026-11-23-leads-management-and-kanban-design.md)

---

## Global Constraints
- Full backward compatibility with existing lead routes (`/v1/leads/my-work`, `/v1/leads/{id}`) so all 60 existing pytest tests pass without regression.
- Exact visual reproduction of Screenshot 1 (Sidebar submenus), Screenshot 2 (Header & Contact Details), and Screenshot 3 (Property Details & Others).
- Universal soft-delete (`deleted_at`) supported across all lead deletion and recycle operations.
- 100% clean TypeScript build (`bun run build`) with zero lint or compilation errors.

## Review Focus
1. `tbl_leads` schema compatibility between existing tests expecting `id`/`lead_id` and legacy column names (`leads_id`, `lead_unique_id`).
2. Kanban drag/drop or 1-click stage transition updating both `stage` and `lead_status` in real-time.
3. CSV/Excel import parsing diverse headers (Name/Contact, Phone/Mobile, Budget, etc.) and normalizing phones to `91XXXXXXXXXX`.
4. Lead Detail visual fidelity: red capsule headers (`Contact Details >`, `Property Details >`, `Others >`) and 7 circular action buttons with precise tooltips and click handlers.
5. Filter persistence in URL search params (`?type=buy`, `?type=rent`, `?type=pg`, `?view=kanban`).

---

### Task 1: Database Migration `0005_tbl_leads_schema.py` & SQLAlchemy Model Alignment

**Files:**
- Create: `backend/app/db/migrations/0005_tbl_leads_schema.py`
- Modify: `backend/app/db/migrations/runner.py:10-16`
- Modify: `backend/app/models/leads.py`
- Test: `backend/tests/test_tbl_leads_schema.py`

**Interfaces:**
- Produces: `tbl_leads` table with all 54 columns, soft-delete column `deleted_at`, and `TblLead` / updated `Lead` model.

- [ ] **Step 1: Write the failing test for `tbl_leads` migration**

```python
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_tbl_leads_table_has_all_54_columns(db_session: AsyncSession):
    res = await db_session.execute(text("PRAGMA table_info(tbl_leads)"))
    cols = {row[1] for row in res.fetchall()}
    assert "leads_id" in cols
    assert "contact_name" in cols
    assert "mobile" in cols
    assert "dealer_have" in cols
    assert "lead_status" in cols
    assert "stage" in cols
    assert "rating" in cols
    assert "deleted_at" in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest backend/tests/test_tbl_leads_schema.py -v`
Expected: FAIL with "no such table: tbl_leads"

- [ ] **Step 3: Implement `0005_tbl_leads_schema.py` and register in `runner.py`**

Create `backend/app/db/migrations/0005_tbl_leads_schema.py` defining the full 54-column table `tbl_leads` with indexes on `mobile`, `lead_status`, `stage`, `deleted_at`, and add `"app.db.migrations.0005_tbl_leads_schema"` to `MIGRATION_STEPS` in `runner.py`.

- [ ] **Step 4: Update `backend/app/models/leads.py` with `TblLead` entity**

Define SQLAlchemy mapped model for `tbl_leads` with properties aliasing both legacy (`leads_id`, `contact_name`) and modern (`lead_id`, `full_name`) accessors for seamless interoperability.

- [ ] **Step 5: Run tests to verify migration and model pass**

Run: `.venv\Scripts\pytest backend/tests/test_tbl_leads_schema.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/migrations/ backend/app/models/leads.py backend/tests/test_tbl_leads_schema.py
git commit -m "feat(db): add 0005_tbl_leads_schema migration and TblLead model"
```

---

### Task 2: Backend Inflow Handlers, CSV Bulk Import & Kanban API

**Files:**
- Create: `backend/app/api/v1/endpoints/lead_inflow.py`
- Modify: `backend/app/api/v1/endpoints/leads.py`
- Modify: `backend/app/api/v1/__init__.py` or router inclusion
- Modify: `backend/app/repositories/lead_repo.py`
- Test: `backend/tests/test_lead_inflow_and_kanban.py`

**Interfaces:**
- Produces:
  - `POST /v1/leads/create` (Manual lead intake with 24 sources, property type)
  - `POST /v1/leads/import-bulk` (CSV / Excel batch intake)
  - `GET /v1/leads/kanban` (Grouped leads by status/stage with temperature badges)
  - `PATCH /v1/leads/{id}/stage` (1-click status / stage progression)

- [ ] **Step 1: Write tests for manual create, bulk CSV import, and Kanban grouping**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_manual_create_and_kanban_grouping(test_client: AsyncClient):
    resp = await test_client.post("/v1/leads/create", json={
        "contact_name": "Vikram Rathore",
        "mobile": "9829012345",
        "lead_type": "BUY",
        "lead_source_id": 1,
        "rating": 1,
        "indv_property_address": "Vaishali Nagar, Jaipur"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["contact_name"] == "Vikram Rathore"

    # Verify kanban endpoint groups lead into NEW status
    kb_resp = await test_client.get("/v1/leads/kanban?type=buy")
    assert kb_resp.status_code == 200
    kb_data = kb_resp.json()
    assert "new" in kb_data
    assert any(l["contact_name"] == "Vikram Rathore" for l in kb_data["new"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest backend/tests/test_lead_inflow_and_kanban.py -v`
Expected: FAIL (404 Not Found)

- [ ] **Step 3: Implement endpoints in `leads.py` and repository methods**

Implement `POST /v1/leads/create`, `POST /v1/leads/import-bulk` (handling CSV text or multipart files), `GET /v1/leads/kanban`, and `PATCH /v1/leads/{id}/stage`.

- [ ] **Step 4: Run tests to verify all endpoints pass**

Run: `.venv\Scripts\pytest backend/tests/test_lead_inflow_and_kanban.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/ backend/app/repositories/ backend/tests/test_lead_inflow_and_kanban.py
git commit -m "feat(api): add lead manual creation, CSV bulk import, and Kanban endpoints"
```

---

### Task 3: Sidebar Navigation Submenus (Screenshot 1) & Inflow Modals

**Files:**
- Modify: `frontend/src/layouts/AdminLayout.tsx`
- Create: `frontend/src/components/leads/CreateLeadModal.tsx`
- Create: `frontend/src/components/leads/ImportLeadModal.tsx`
- Modify: `frontend/src/App.tsx`
- Test: Frontend build with `bun run build`

**Interfaces:**
- Produces:
  - Sidebar with submenus: `Buy`, `Rent`, `PG`, `Create Lead`, `Import Lead`
  - `CreateLeadModal` with 24 lead sources, budget, type selector, customer details
  - `ImportLeadModal` with drag-and-drop CSV parser, preview table, and 1-click import

- [ ] **Step 1: Update `AdminLayout.tsx` to exact Screenshot 1 submenus**

Configure `LEADS` item with `Buy`, `Rent`, `PG`, `Create Lead`, and `Import Lead`.

- [ ] **Step 2: Create `CreateLeadModal.tsx`**

Build modal with property type tabs (`Buy`, `Rent`, `PG`), 24 lead sources dropdown (Newspaper, Facebook, Google, Direct Walk-in, etc.), name, mobile, email, address, budget min/max, and remarks.

- [ ] **Step 3: Create `ImportLeadModal.tsx`**

Build bulk import modal supporting CSV/Excel parsing, previewing up to 10 rows, duplicate detection, and batch submission to `/v1/leads/import-bulk`.

- [ ] **Step 4: Verify clean frontend build**

Run: `cd frontend; bun run build`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/layouts/AdminLayout.tsx frontend/src/components/leads/ frontend/src/App.tsx
git commit -m "feat(ui): add Screenshot-1 leads sidebar submenus, Create Lead modal, and CSV import modal"
```

---

### Task 4: Dual-Mode Interactive Kanban Board & Data Table Hub

**Files:**
- Create: `frontend/src/components/leads/LeadKanbanBoard.tsx`
- Create: `frontend/src/components/leads/LeadTableView.tsx`
- Modify: `frontend/src/pages/MyWork.tsx`
- Test: Frontend build with `bun run build`

**Interfaces:**
- Produces: Dual-mode toggle `[Kanban Board View]` ⇄ `[Table View]` in `/leads` with active property type filters (`All`, `Buy`, `Rent`, `PG`), temperature chips, search, and 1-click status advances.

- [ ] **Step 1: Implement `LeadKanbanBoard.tsx`**

Create 6-column pipeline (`New / Fresh`, `In Progress`, `Site Visit Planned`, `Qualified`, `Converted`, `Disqualified`) with card statistics, SLA indicator, quick call/WhatsApp buttons, and drag-and-drop or dropdown status advances.

- [ ] **Step 2: Implement `LeadTableView.tsx`**

Create responsive data table with customer name, mobile, property type badge, temperature flame, stage, SLA timer, and actions (`View Details`, `Call`, `Disqualify`).

- [ ] **Step 3: Integrate into `MyWork.tsx` with View Switcher & Inflow Modals**

Add top-level view toggle, search bar, property type pills, and connect `Create Lead` & `Import Lead` triggers.

- [ ] **Step 4: Verify clean frontend build**

Run: `cd frontend; bun run build`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/leads/ frontend/src/pages/MyWork.tsx
git commit -m "feat(ui): implement interactive dual-mode Kanban board and data table view"
```

---

### Task 5: Pixel-Perfect Lead Detail View Redesign (Screenshots 2 & 3)

**Files:**
- Modify: `frontend/src/pages/LeadDetail.tsx`
- Test: Frontend build with `bun run build`

**Interfaces:**
- Produces: Complete Lead Detail page matching Screenshots 2 & 3:
  - Header: Customer name, requirement subtitle, status/temperature pills
  - 7 circular quick action buttons (Call, Followup, Status toggle, Reassign, Property, Share, History)
  - Red capsule pill headers (`Contact Details >`, `Property Details >`, `Others >`) with exact styling and fields
  - Quick action modals for logging calls, updating follow-ups, and changing status

- [ ] **Step 1: Implement Top Header & 7 Circular Action Buttons**

Create the circular action button bar with tooltips and active handlers:
1. Call (Purple `#4f46e5`)
2. Follow-up (Red `#dc2626`)
3. Status Toggle (Yellow `#eab308`)
4. Reassign (Coral `#ef4444`)
5. Property (Blue `#2563eb`)
6. Share (Cyan `#0284c7`)
7. History / Log (Green `#16a34a`)

- [ ] **Step 2: Implement 3 Red Capsule Card Sections**

Implement:
1. `Contact Details >`: Follow Up Remark, Request ID (`PR141`), Customer Name, Mobile, Email, Address, Status, Current Update.
2. `Property Details >`: Property Id, Looking For, Property Type, Property Address.
3. `Others >`: Followup Date, Received Date, Last Updated Date & By, Assign Date & Assignee.

- [ ] **Step 3: Verify clean frontend build**

Run: `cd frontend; bun run build`
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LeadDetail.tsx
git commit -m "feat(ui): redesign Lead Detail view matching reference Screenshots 2 and 3"
```

---

### Task 6: End-to-End Verification & Commit

**Files:**
- Test: Run all backend tests and frontend production build
- Test: Manual verification of Kanban drag/status advance, modals, and detail cards

- [ ] **Step 1: Run all backend pytest tests**

Run: `.venv\Scripts\pytest backend/tests -v`
Expected: All 60+ tests pass with 0 failures

- [ ] **Step 2: Run frontend production build**

Run: `cd frontend; bun run build`
Expected: 0 TypeScript errors, clean bundle output

- [ ] **Step 3: Final branch commit and status check**

Run: `git status`
Expected: Working tree clean
