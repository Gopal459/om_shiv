# Lead-to-Property Conversion — Short Design Specification

- **Date:** 2026-11-28
- **Status:** Approved
- **Theme Alignment:** AlwarMap Royal Indigo (`#291BB0`) & Coral Accent (`#F04B42`)

---

## 1. Intent & Why
On a Single Lead dossier ([LeadDetail.tsx](file:///c:/xampp/htdocs/om_shiv/frontend/src/pages/LeadDetail.tsx)), clicking `Property` currently opens a static read-only modal with only a `Close` button. When an inbound Lead is ready to be onboarded into property inventory (Option 1), staff need a 1-click **Convert to Property** workflow that pre-fills the full 124-column [PropertyForm.tsx](file:///c:/xampp/htdocs/om_shiv/frontend/src/pages/PropertyForm.tsx), atomically creates the `tbl_property` listing, links the new property onto `TblLead` and `Lead`, marks the Lead converted (`stage="WON"`, `lead_status=5`), and records an audit log entry.

## 2. Scope & Design
- **Backend (`property_service.py` + `leads.py`):**
  - Add optional `commit: bool = True` to `create_tbl_property` (`property_service.py:142`) so callers can wrap property creation inside an outer transaction cleanly.
  - Add `POST /v1/leads/{id}/convert-to-property` accepting `TblPropertyCreateRequest`:
    - Looks up `TblLead` and/or `Lead` (`404` if neither found).
    - Prevents duplicate conversion (`400` if `tbl_lead.property_id > 0` or `tbl_lead.property_idno` or `lead.related_listing_id` is already set).
    - Calls `create_tbl_property(payload, db=db, commit=False)` to create `TblProperty` (`propertyid_no` + `property_id`).
    - Updates `TblLead` (`property_id`, `property_idno`, `indv_property_address`, `deal_final_price`, `lead_status = 5`, `stage = 3`, `lead_remark`) and paired `Lead` (`related_listing_id = prop.propertyid_no`, `stage = "WON"`, `is_untouched = False`), plus logs `LeadActivity(action_type="CONVERTED_TO_PROPERTY", outcome=f"Property {prop.propertyid_no}", ...)` atomically before single `db.commit()`.
    - Updates `build_lead_detail_dict` in `leads.py` to also return `property_id: int` and `related_listing_id: Optional[str]` cleanly.
- **Frontend (`LeadDetail.tsx` + `PropertyForm.tsx` + `App.tsx`):**
  - **`LeadDetail.tsx`:** Add **Convert to Property** button directly in the hero quick-action bar (plus inside Card 2 `PROPERTY & ECONOMICS` and inside `activeModal === 'PROPERTY'`). If the lead already has a linked `propertyCode` (`OP-...` / `PROP-...` / `tbl_lead.property_id > 0`), display a linked badge and a **"View in Property Hub"** button (`/properties?search=...`) instead of letting staff double-convert. Clicking **Convert to Property** navigates to `/properties/create?fromLead=${lead.lead_id}`.
  - **`PropertyForm.tsx` & `App.tsx`:** Support `fromLead` query param (or prop) on `/properties/create`: fetch `GET /v1/leads/${fromLead}`, pre-fill `ownerName`, `ownerEmail`, `ownerMobile` (normalized 10-digit), `propertyType` (`RENT=1`, `PG=3`, `BUY/SELL=2`), `locationText` & `sublocality`, `expectedPrice`, and `description`; show a `"Converting Lead <id> → New Property"` banner; submit via `POST /v1/leads/${fromLead}/convert-to-property`; and navigate back to `/leads/${fromLead}` on success.

## 3. Approaches Considered
- **Selected (Approach A):** Pre-fill the full 124-column `PropertyForm.tsx` and commit via an atomic `POST /v1/leads/{id}/convert-to-property` endpoint. Reuses existing schema/UI and avoids half-created listings.
- **Rejected (Approach B):** Separate slim 6-field modal duplicating property creation inside `LeadDetail.tsx`.
