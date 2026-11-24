# Property Engine & 124-Column Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the Property Management System to match the user's legacy 124-column `tbl_property` and `tbl_payingguest` database schemas, provide the 7-submenu admin sidebar with bullet ring styling, build a dynamic multi-card Add/Edit property form matching user screenshots, and provide full backend REST APIs with conditional validation.

**Architecture:** 
1. Database layer: Migration `0006_tbl_property_schema.py` creating `tbl_property` (124 columns) and `tbl_payingguest` tables.
2. Domain layer: SQLAlchemy models `TblProperty` and `TblPayingGuest` in `backend/app/models/properties.py` and service/validation logic in `backend/app/services/property_service.py`.
3. API layer: Endpoints `GET /v1/properties/hub`, `POST /v1/properties/create`, `GET /v1/properties/{id}`, `PUT /v1/properties/{id}`, and `PATCH /v1/properties/{id}/status` in `backend/app/api/v1/endpoints/properties.py`.
4. Frontend layer: Admin sidebar menu updated with 7 submenus matching Screenshot 7 in `AdminLayout.tsx`, `PropertyHub.tsx` managing the 7 tab queues, and dynamic `PropertyForm.tsx` implementing the 6 cards and conditional validation rules matching Screenshots 8, 9, 10.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy (asyncpg/aiosqlite), Pydantic v2, React 19, TypeScript, Tailwind CSS, Lucide Icons, Vite.

**Spec:** `C:/Users/LENOVO/.gemini/antigravity/brain/7a67fb5d-7d80-4685-9f26-14985a345470/property-management-and-schema-design.md`

## Global Constraints
- `tbl_property` must implement the exact column names, data types, and default values from the user's SQL schema specification (124 columns).
- `tbl_payingguest` must store PG-specific attributes (gender, food_option, meal_type, rules).
- Strict validation rules:
  - Sale: `transaction_type` mandatory; if `possession_status == 1` then `construction_age` mandatory; `carpet_area < super_area` must be strictly enforced.
  - Rent: `rentalallow_forid` mandatory; if `whichpart_torent == 2` then `floor_torent` mandatory.
  - PG: `food_option == 1` requires `food_type` and `meal_type`.
  - Subcategories: Flat requires `project_name` + `noof_bhk`; House requires `constructed_floors` + `kitchen`; Plot requires `boundary`.
- Existing test baseline of 63 tests in `backend/tests` must continue to pass 100%.
- Frontend build `bun run build` must succeed without TypeScript or linting errors.

## Review Focus
1. `tbl_property` creation in migration runner must execute idempotently without dropping existing tables.
2. Numeric/Decimal casting for `expected_price`, `carpet_area`, `super_area` must handle strings, floats, and None values safely.
3. Tab filtering on `GET /v1/properties/hub` must correctly map each of the 7 states (`new_assign`, `verify_live`, `verification_done`, `expired`, `deleted`, `sold`, `request_live`).
4. `PropertyForm.tsx` must dynamically update visible fields when switching between Sale (`property_type=2`), Rent (`property_type=1`), and PG (`property_type=3`).
5. Photo upload in `PropertyForm.tsx` must enforce max 10 photos, minimum 10KB, and valid image formats.

---

### Task 1: Database Migration `0006_tbl_property_schema.py` & SQLAlchemy Models

**Files:**
- Create: `backend/app/db/migrations/0006_tbl_property_schema.py`
- Modify: `backend/app/db/migrations/runner.py`
- Modify: `backend/app/models/properties.py`
- Test: `backend/tests/test_tbl_property_schema.py`

**Steps:**
- [ ] Write failing migration test `backend/tests/test_tbl_property_schema.py` checking existence of `tbl_property` (124 columns) and `tbl_payingguest`.
- [ ] Run `pytest backend/tests/test_tbl_property_schema.py` to confirm failure.
- [ ] Implement `0006_tbl_property_schema.py` containing complete `CREATE TABLE IF NOT EXISTS tbl_property` and `CREATE TABLE IF NOT EXISTS tbl_payingguest` with SQLite/Postgres compatibility.
- [ ] Register `app.db.migrations.0006_tbl_property_schema` in `MIGRATION_STEPS` in `runner.py`.
- [ ] Add `TblProperty` and `TblPayingGuest` SQLAlchemy declarative models in `backend/app/models/properties.py`.
- [ ] Run `pytest backend/tests/test_tbl_property_schema.py` and verify all tests pass.
- [ ] Commit changes: `git commit -am "feat(db): add 0006_tbl_property_schema migration and TblProperty ORM models"`

---

### Task 2: Backend Property Hub & Create/Update REST Endpoints with Strict Validation

**Files:**
- Create: `backend/app/schemas/tbl_property_schemas.py`
- Modify: `backend/app/services/property_service.py`
- Modify: `backend/app/api/v1/endpoints/properties.py`
- Test: `backend/tests/test_tbl_property_api.py`

**Steps:**
- [ ] Write failing integration tests in `backend/tests/test_tbl_property_api.py`:
  - Test `GET /v1/properties/hub?tab=new_assign`
  - Test `POST /v1/properties/create` for Sale with valid fields
  - Test `POST /v1/properties/create` with invalid Sale rule (`carpet_area >= super_area`) expecting 422
  - Test `POST /v1/properties/create` for Rent with partial floor validation
  - Test `POST /v1/properties/create` for PG with food options validation
  - Test `PATCH /v1/properties/{id}/status` for assigning staff and toggling live
- [ ] Run `pytest backend/tests/test_tbl_property_api.py` to confirm failure.
- [ ] Implement Pydantic request & response schemas in `backend/app/schemas/tbl_property_schemas.py`.
- [ ] Implement service methods in `backend/app/services/property_service.py`:
  - `create_tbl_property(data, db)` with conditional checks
  - `get_tbl_properties_hub(tab, search, page, limit, db)`
  - `get_tbl_property_by_id(property_id, db)`
  - `update_tbl_property(property_id, data, db)`
  - `update_tbl_property_status(property_id, status_data, db)`
- [ ] Add the endpoints to `backend/app/api/v1/endpoints/properties.py`.
- [ ] Run `pytest backend/tests/test_tbl_property_api.py` and verify all tests pass.
- [ ] Run all backend tests: `pytest backend/tests` to ensure no regressions.
- [ ] Commit changes: `git commit -am "feat(api): add property hub and dynamic create/update endpoints with validation"`

---

### Task 3: Admin Sidebar Navigation Matching Screenshot 7

**Files:**
- Modify: `frontend/src/layouts/AdminLayout.tsx`
- Test: Visual inspection & build check

**Steps:**
- [ ] Update `navItems` under `id: 'PROPERTY'` in `AdminLayout.tsx` to include the 7 submenus:
  1. `New & Assign Properties` -> `/properties?tab=new_assign`
  2. `Verify & Live Properties` -> `/properties?tab=verify_live`
  3. `Verification Done` -> `/properties?tab=verification_done`
  4. `Expired Properties` -> `/properties?tab=expired`
  5. `Delete Property` -> `/properties?tab=deleted`
  6. `Sell Property` -> `/properties?tab=sold`
  7. `Request Live Property` -> `/properties?tab=request_live`
- [ ] Ensure subitems render with bullet ring icon (`Circle` component) matching Screenshot 7 styling.
- [ ] Verify sidebar navigation routes and query parameters.
- [ ] Commit changes: `git commit -am "feat(ui): update property sidebar menu with 7 submenus and bullet styling"`

---

### Task 4: Dynamic Multi-Card Property Form Matching Screenshots 8, 9, 10

**Files:**
- Create: `frontend/src/pages/PropertyForm.tsx`
- Modify: `frontend/src/App.tsx`
- Test: Component compilation and interaction tests

**Steps:**
- [ ] Create `frontend/src/pages/PropertyForm.tsx` implementing 6 section cards with red header badges:
  - **Card 1: User Info** (Owner Name, Owner Email, Owner Mobile, Source Type)
  - **Card 2: Location** (Posted Date, Expire Date, State, City, Location text, Map Lat/Long coordinates, Near By Area)
  - **Card 3: Property Detail** (Property Type: Buy/Rent/PG, Subcategory, Unit/Street, Area & Unit, Boundary, conditional fields based on type)
  - **Card 4: Price** (Select Price Format, Price per unit, Expected Price, Price In Words calculator, Price Negotiable toggle, Extra Charge toggle)
  - **Card 5: Features** (Width Of Facing Road, Facing, Corner toggle, Common Features icons/toggles: Water Supply, Electricity, Lift, Security, etc.)
  - **Card 6: Uploads** (Description textarea, Photos upload section with spec badges: max 10 photos, min 10KB, max 2MB, formats PNG/JPG/JPEG, dimensions 600x400)
- [ ] Add client-side validation reflecting server-side rules (e.g. carpet < super area, mandatory fields per property type).
- [ ] Connect form submission to `POST /v1/properties/create` and `PUT /v1/properties/{id}`.
- [ ] Route `/properties/create` and `/properties/:id/edit` in `App.tsx` to `PropertyForm`.
- [ ] Verify build: `bun run build`.
- [ ] Commit changes: `git commit -am "feat(ui): implement dynamic multi-card property form matching specs"`

---

### Task 5: Property Hub Management UI for 7 Submenu Views

**Files:**
- Create: `frontend/src/pages/PropertyHub.tsx`
- Modify: `frontend/src/App.tsx`
- Test: Verification of tab switching, search, staff assignment modal, and actions

**Steps:**
- [ ] Create `frontend/src/pages/PropertyHub.tsx` with:
  - Header with title, current tab badge, search bar, and "+ Add Property" button.
  - Submenu navigation tabs corresponding to the 7 views (`new_assign`, `verify_live`, `verification_done`, `expired`, `deleted`, `sold`, `request_live`).
  - Data table showing Property ID, Title, Type/Category, Price, Location, Owner Contact, Status, Assigned Staff, and Actions (View/Edit, Assign, Toggle Live, Move to Trash).
  - Quick Telecaller/Staff Assignment modal for `New & Assign Properties`.
  - Empty states with call-to-actions.
- [ ] Replace `ModuleHub` route for `/properties` with `PropertyHub` in `frontend/src/App.tsx`.
- [ ] Test tab switching and ensure URL query param `?tab=...` syncs with state.
- [ ] Run full frontend build: `bun run build`.
- [ ] Run all pytest tests: `pytest backend/tests`.
- [ ] Commit changes: `git commit -am "feat(ui): implement PropertyHub with 7 queue views and staff assignment"`

---

### Task 6: Final End-to-End Verification

**Files:**
- All created and modified files
- Test: Full backend test suite & full frontend production build

**Steps:**
- [ ] Execute backend pytest suite: `$env:PYTHONPATH='backend'; .venv\Scripts\pytest backend/tests -q`.
- [ ] Execute frontend build: `cd frontend; bun run build`.
- [ ] Verify zero console errors and zero failing tests.
- [ ] Push/commit final clean state.
