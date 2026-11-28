# Lead-to-Property Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable atomic **Lead → New Property** conversion from a Single Lead dossier (`LeadDetail.tsx`), pre-filling `PropertyForm.tsx`, creating `tbl_property`, linking `property_id`/`property_idno` onto `TblLead` & `Lead`, marking the Lead converted, and preventing duplicate conversion.

**Architecture:** One transactional `POST /v1/leads/{id}/convert-to-property` endpoint reusing `create_tbl_property(..., commit=False)` in `property_service.py`, paired with `LeadDetail.tsx` CTA/linked state and `PropertyForm.tsx` `?fromLead=` pre-fill & redirect back to `/leads/${fromLead}`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pytest + httpx, React 18, TypeScript, Tailwind CSS (`#291BB0` / `#F04B42`), Vite.

**Spec:** [docs/superpowers/specs/2026-11-28-lead-to-property-conversion-design.md](file:///c:/xampp/htdocs/om_shiv/docs/superpowers/specs/2026-11-28-lead-to-property-conversion-design.md)

## Global Constraints
- Atomic transaction: if Lead update or `LeadActivity` creation fails, zero orphan `tbl_property` rows may commit (`create_tbl_property` supports `commit=False`).
- Duplicate guard: attempting `POST /v1/leads/{id}/convert-to-property` on an already property-linked lead returns `400 Bad Request`.
- AlwarMap UI colors (`#291BB0` primary, `#F04B42` accent) on new CTAs and conversion banner.

## Review Focus
1. **Duplicate Conversion Block:** Calling `POST /v1/leads/{id}/convert-to-property` a second time on a Lead already linked to a property must return `400` and create zero extra `tbl_property` rows.
2. **Rollback Atomicity:** If conversion fails mid-flight or the lead ID does not exist (`404`), `create_tbl_property` must not leave an unlinked orphan row committed in `tbl_property`.
3. **10-Digit Mobile Normalization in `PropertyForm`:** Lead mobile stored as `919829012345` must pre-fill cleanly in `PropertyForm`'s `ownerMobile` field (`9829012345`) so `PropertyForm`'s 10-digit mobile regex check passes without manual editing.
4. **Budget / Price Fallback on Pre-fill:** When `lead.deal_final_price == 0` and `budget_max` is `null`/0, `expectedPrice` must stay a valid positive default (`'4500000'`) so `PropertyForm` submission doesn't fail `expected_price > 0` silently.
5. **Dual-Entity & TblLead-Only Leads:** Converting a lead that exists only in `tbl_leads` (no modern `Lead` row) or only in `leads` (or both) must succeed cleanly without crashing on `None`.

---

### Task 1: Backend Atomic `POST /v1/leads/{id}/convert-to-property` Endpoint (TDD)

**Files:**
- Modify: `backend/app/services/property_service.py:142-283`
- Modify: `backend/app/api/v1/endpoints/leads.py:775-860`
- Test: `backend/tests/test_lead_inflow_and_kanban.py`

**Interfaces:**
- Consumes: `TblPropertyCreateRequest`, `create_tbl_property(payload, db, commit=False)`
- Produces:
  - `POST /v1/leads/{id}/convert-to-property` -> `201 Created`:
    `{ status, lead_id, property_id, propertyid_no, stage, lead_status }`
  - Enriched `GET /v1/leads/{id}` fields: `property_id: int`, `related_listing_id: Optional[str]`

- [ ] **Step 1: Write failing tests in `backend/tests/test_lead_inflow_and_kanban.py`**

Add `test_convert_lead_to_property_atomic_and_duplicate_guard` verifying:
1. Converting non-existent lead `OB-9999-999999` returns `404` and inserts zero `TblProperty` rows.
2. Converting an active lead creates a `TblProperty` row (`verified_status=0`), links `property_id` & `property_idno` onto `TblLead` + `related_listing_id` & `stage="WON"` onto `Lead`, records `CONVERTED_TO_PROPERTY` in `LeadActivity`, and returns `201`.
3. Calling `POST /v1/leads/{id}/convert-to-property` a second time returns `400`.
4. `GET /v1/leads/{id}` reflects `property_id > 0`, `property_idno`, `related_listing_id`, `stage == "WON"`, and `"CONVERTED_TO_PROPERTY"` activity.

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\pytest.exe backend/tests/test_lead_inflow_and_kanban.py -v`
Expected: FAIL with `404` / `405` on `/convert-to-property`.

- [ ] **Step 3: Update `create_tbl_property` (`commit: bool = True`) and implement `/v1/leads/{id}/convert-to-property`**

1. In `backend/app/services/property_service.py:142`, add `commit: bool = True` to `create_tbl_property`; flush instead of committing when `commit=False`.
2. In `backend/app/api/v1/endpoints/leads.py`:
   - Expose `"property_id": tbl_lead.property_id if tbl_lead else 0` and `"related_listing_id": (lead.related_listing_id if lead else None) or (tbl_lead.property_idno if tbl_lead else None)` inside `build_lead_detail_dict`.
   - Implement `@router.post("/{id}/convert-to-property", status_code=status.HTTP_201_CREATED)` accepting `TblPropertyCreateRequest`, validating lead existence (`404`) and duplicate conversion (`400`), calling `create_tbl_property(..., commit=False)`, updating `TblLead` & `Lead` & inserting `LeadActivity`, and committing once.

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\pytest.exe backend/tests/test_lead_inflow_and_kanban.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/property_service.py backend/app/api/v1/endpoints/leads.py backend/tests/test_lead_inflow_and_kanban.py
git commit -m "feat(leads): add atomic POST /v1/leads/{id}/convert-to-property endpoint"
```

---

### Task 2: Frontend `LeadDetail.tsx` CTA/Linked State + `PropertyForm.tsx` Pre-Fill & Submission

**Files:**
- Modify: `frontend/src/pages/LeadDetail.tsx`
- Modify: `frontend/src/pages/PropertyForm.tsx`
- Modify: `frontend/src/App.tsx:134-142`

**Interfaces:**
- Consumes: `GET /v1/leads/{id}`, `POST /v1/leads/{id}/convert-to-property`
- Produces: `/properties/create?fromLead=<leadId>` route handling & Lead Detail Convert-to-Property UX.

- [ ] **Step 1: Add Convert-to-Property CTA and Linked Property State in `LeadDetail.tsx`**

1. Add `Convert to Property` button in the top quick-action bar (next to `Property`), in Card 2 (`PROPERTY & ECONOMICS` footer), and inside `activeModal === 'PROPERTY'` — navigating to `/properties/create?fromLead=${encodeURIComponent(lead.lead_id || leadId)}` when unlinked, or showing a clickable `View Linked Property` shortcut (`/properties`) when `propertyCode` is already linked.

- [ ] **Step 2: Support `?fromLead=` pre-fill and atomic conversion submit in `PropertyForm.tsx` & `App.tsx`**

1. In `App.tsx`, wrap `/properties/create` in a thin `PropertyCreatePage` using `useSearchParams` to pass `fromLeadId={searchParams.get('fromLead')}` and `onSuccess={() => navigate(fromLead ? `/leads/${fromLead}` : '/properties')}`, `onBack={() => navigate(fromLead ? `/leads/${fromLead}` : '/properties')}`.
2. In `PropertyForm.tsx`: accept `fromLeadId?: string | null`; when present, fetch `GET /v1/leads/${fromLeadId}` on mount, normalize mobile to last 10 digits for `ownerMobile`, map `lead_type` to `propertyType`, populate `ownerName`, `ownerEmail`, `locationText`, `sublocality`, positive `expectedPrice` (`deal_final_price > 0 || budget_max > 0 ? ... : '4500000'`), and `description`; render a top AlwarMap `#291BB0` banner showing `"Converting Lead ${fromLeadId} → New Property Listing"`; and on submit POST to `/v1/leads/${encodeURIComponent(fromLeadId)}/convert-to-property`!

- [ ] **Step 3: Verify full backend suite and frontend Vite build**

Run: `.\.venv\Scripts\pytest.exe backend/tests -q` and `npm --prefix c:\xampp\htdocs\om_shiv\frontend run build`
Expected: All backend tests pass and `tsc && vite build` exits 0 cleanly.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LeadDetail.tsx frontend/src/pages/PropertyForm.tsx frontend/src/App.tsx
git commit -m "feat(ui): wire Convert to Property workflow from LeadDetail to pre-filled PropertyForm"
```
