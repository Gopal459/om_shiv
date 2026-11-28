# Lead Create Form: Assign Staff, Customer Type & Reference Details — Design

**Date:** 2026-11-28
**Status:** Approved (short design)

## 1. Intent & Why
Manual inbound lead creation (`CreateLeadModal` → `POST /v1/leads/create`) currently omits three operational fields needed at intake time:
1. **Assign Staff** (`assigned_to`, optional) so walk-in/phone leads can be assigned immediately at creation or left on Om Shiv Central Desk.
2. **Customer Type** (`User` / `Investor` / `Broker`) so sales reps immediately know whether the caller is an end-user, investor, or broker/dealer.
3. **Reference Details** (`Client` / `Relative` / `Employee` type, Reference Name, Reference Mobile) so referral attribution is captured cleanly in `tbl_leads` (`reference_relation_by`, `refer_by_name`, `refer_by_mobile`).

## 2. Approach
Add dedicated schema + UI fields end-to-end across `models/leads.py`, migration `0014_lead_customer_type.py`, `leads.py`, `CreateLeadModal.tsx`, and `LeadDetail.tsx`.
- *Why alternatives don't fit:* Reusing `TblLead.dealer_have` (`0/1/2`) alone cannot distinguish `User` vs `Investor`, and hardcoding staff options on the frontend quickly goes stale. Keeping `customer_type` as its own column while syncing `dealer_have = 1` for `BROKER` preserves legacy compatibility cleanly.

## 3. Specification
- **Database (`0014_lead_customer_type.py`, `models/leads.py`):**
  - Add `customer_type VARCHAR(32) NOT NULL DEFAULT 'USER'` to both `leads` and `tbl_leads`.
- **Backend (`backend/app/api/v1/endpoints/leads.py`):**
  - Add `GET /v1/leads/assignees` (defined *before* `GET /{id}`) returning active, non-deleted `Employee` records (`employee_id`, `name`, `role_name`, `role_code`, `is_active`).
  - Extend `LeadCreateManual` with optional `assigned_to`, `customer_type` (`USER` | `INVESTOR` | `BROKER`, default `USER`), `reference_type` (`Client` | `Relative` | `Employee`), `refer_by_name`, and `refer_by_mobile`.
  - Validate non-empty `assigned_to` against active `Employee` (`400` if missing/inactive); sync `Lead.assigned_to = emp.employee_id`, `TblLead.assign_franchstaff_id = emp.id`, `TblLead.assignfranchiseestaff_date = now`.
  - Sync `customer_type` on both `Lead` and `TblLead`; set `TblLead.dealer_have = 1` when `BROKER` (else `2` when explicitly created via manual form).
  - Persist trimmed `reference_type` → `TblLead.reference_relation_by`, `refer_by_name`, `refer_by_mobile`.
  - Expose `customer_type` and `reference_relation_by` in `LeadDetailResponse` and `build_lead_detail_dict`.
- **Frontend (`CreateLeadModal.tsx`, `LeadDetail.tsx`):**
  - Fetch `/v1/leads/assignees` when `CreateLeadModal` opens; render a prominent, bold-labeled **Assign Staff (Optional)** `<select>` dropdown defaulting to `Om Shiv Central Desk (Unassigned)`.
  - Add **Customer Type** selector (`User`, `Investor`, `Broker`, default `User`).
  - Add optional **Reference Details** section: **Reference Type** (`Client`, `Relative`, `Employee`), **Reference Name**, and **Reference Mobile** (reset all fields cleanly after create).
  - Display `Customer Type` pill/badge and `Reference Type` alongside `refer_by_name` / `refer_by_mobile` in `LeadDetail.tsx`.
