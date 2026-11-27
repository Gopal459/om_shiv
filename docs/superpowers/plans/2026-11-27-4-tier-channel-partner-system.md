# 4-Tier Channel Partner (CP) & Franchise Governance Implementation Plan

**Goal:** Extend the existing dynamic Franchise & Channel Partner Network (`backend/app/models/franchise.py`, `backend/app/api/v1/endpoints/franchise.py`, `frontend/src/pages/FranchiseHub.tsx`) to support Omshiv's 4 finalized CP categories with strict level-based inventory access control, instant suspension, registry-gated capped referral rewards, and creator link/code attribution + retainers.

### Confirmed Decisions
- **Referral Partner Reward & Cap:** Custom fixed reward amount (₹) and custom annual reward limit per partner, editable directly in the Admin UI.
- **Broker CP Co-Broking Split:** Default **50%** co-broking split, customizable per Broker CP.
- **Phase 1 Scope:** Build the complete 4-tier CP system, server-side inventory masking/access checks, mediated meetings, attribution, and live **Access Preview** inside Admin CRM (`FranchiseHub.tsx`) first (separate external CP login portal can follow in Phase 2).

---

## 1. The 4 CP Categories & Business Rules Matrix

| Feature / Rule | 1. Broker CP | 2. Active CP (L1 → L2 → L3) | 3. Referral Partner | 4. Creator Partner |
|---|---|---|---|---|
| **Profile** | Established brokers with own office setup | Daily field CPs working exclusively with Omshiv | Salaried/fresher individuals sending occasional leads | Social media / YouTube / Instagram influencers |
| **Inventory Access** | Co-broking shared inventory | **L1 (0–30d):** None<br>**L2 (30d + Cert + Mgr Rec):** Property address only (NO owner name/phone)<br>**L3 (clean record):** Supervised direct meeting via Omshiv | None (lead submission only) | Public/promotional listings via tracking link |
| **Site Visit Rule** | Co-broking / coordinated | **L1:** Only accompanied by Omshiv staff<br>**L2/L3:** Tracked visit | Handled by Omshiv team | Handled by Omshiv team |
| **Payout Model** | Co-broking split % (`co_broking_split_pct`) | Standard CP % (`commission_pct`) | **Fixed ₹ reward ONLY on Registry** (`CONVERTED`/`REGISTERED`) | Deal **Commission %** on code/link leads + **Monthly Retainer** (top creators) |
| **Limits / Guards** | Office verification | **Instant Kill Switch** on any violation/problem | **Annual reward cap** (e.g. max N registries/FY) | Valid tracking code / referral link attribution |

---

## 2. Database Schema Changes (Migration `0011_cp_4_tier_governance`)

### A. Extend `channel_partners` (`backend/app/models/franchise.py`)
Add fields cleanly (nullable/defaulted for zero breaking change):
- `cp_type`: `BROKER_CP` | `ACTIVE_CP` | `REFERRAL_PARTNER` | `CREATOR_PARTNER` (indexed)
- **Broker CP fields:**
  - `has_office_setup` (bool, default `False`)
  - `office_address` (Text, nullable)
  - `co_broking_split_pct` (Numeric(5,2), nullable — e.g. `50.00`)
- **Active CP Ladder & Governance fields:**
  - `active_level`: `L1` | `L2` | `L3` (default `"L1"`)
  - `joined_at` (DateTime UTC, tracks 30-day & 1–2 month tenure)
  - `is_certified` (bool, default `False`) & `certified_at` (DateTime, nullable)
  - `recommended_by` (String `employee_id`, nullable) & `recommended_at` (DateTime, nullable)
  - `l3_approved_by` (String `employee_id`, nullable) & `l3_approved_at` (DateTime, nullable)
  - `clean_record` (bool, default `True`) & `violation_notes` (Text, nullable)
  - `suspended_at` (DateTime, nullable), `suspended_by` (String, nullable), `suspension_reason` (Text, nullable)
- **Referral Partner fields:**
  - `fixed_reward_amount` (Numeric(12,2), nullable)
  - `annual_reward_limit` (Integer, default `5`)
- **Creator Partner fields:**
  - `tracking_code` (String(40), unique index, nullable — e.g. `ROHIT26`)
  - `social_handle` / `platform` (String, nullable)
  - `is_top_creator` (bool, default `False`)
  - `monthly_retainer_amount` (Numeric(12,2), default `0.00`)

### B. Extend `leads` (`backend/app/models/leads.py`)
- `partner_id` (FK -> `channel_partners.id`, nullable, indexed)
- `referral_code` (String(40), nullable, indexed — captures Creator tracking code / CP code automatically from form or URL `?ref=...`)
- `accompanied_by` (String `employee_id`, nullable — mandatory for Active CP L1 site visits)

### C. Extend `partner_payouts` (`backend/app/models/franchise.py`)
- `payout_type`: `CO_BROKING` | `COMMISSION` | `REFERRAL_FIXED` | `CREATOR_COMMISSION` | `CREATOR_RETAINER`
- `fiscal_year`: e.g. `"2026-27"` (enforces Referral Partner annual cap accurately)

### D. New Table: `cp_mediated_meetings` (`backend/app/models/franchise.py`)
Tracks L3 Active CP requests for Omshiv-mediated owner-buyer meetings:
- `id`, `partner_id`, `property_id`, `lead_id`, `requested_slot`, `supervisor_emp_id`, `status` (`REQUESTED`, `APPROVED`, `COMPLETED`, `REJECTED`), `notes`, `created_at`

---

## 3. Backend Implementation Phases

### Phase 1: Schema & Business Rules Service (`cp_governance_service.py`)
1. **Tenure & Promotion Validator for Active CP (`ACTIVE_CP`):**
   - **L1 → L2 Eligibility Check:** Must satisfy ALL three:
     1. `(now - joined_at).days >= 30`
     2. `is_certified == True`
     3. `recommended_by` (Manager employee_id) provided
   - **L2 → L3 Eligibility Check:** Must satisfy:
     1. Currently `L2` and `(now - joined_at).days >= 60` (configurable 30–60 days after L2)
     2. `clean_record == True` (zero strikes/complaints)
     3. Supervisor approval recorded
   - **Instant Suspension (`suspend_partner`):** Sets `is_active = False`, `clean_record = False`, records `suspended_at`, `suspended_by`, `suspension_reason`, appends immutable `AuditLog`, and immediately revokes inventory/lead/meeting access.
2. **Backend Inventory Masking & Access Guard (`get_cp_scoped_inventory`):**
   - `SUSPENDED` / inactive CP → `403 Forbidden`
   - `ACTIVE_CP` at `L1` → Returns `[]` (`access_level: "LOCKED_L1"`, message: *"L1 partners cannot browse inventory; schedule visits accompanied by Omshiv staff"*)
   - `ACTIVE_CP` at `L2` / `L3` → Returns verified live properties with `city`, `locality`, `address`, `expected_price`, specs, **WITH `owner_name` and `owner_mobile` completely omitted/masked (`null` / `"Omshiv Managed"`)**
   - `BROKER_CP` → Returns co-broking eligible listings (still respecting Omshiv deal registration rules)
3. **Referral Partner Reward & Annual Limit Guard:**
   - When creating a `REFERRAL_FIXED` payout:
     1. Check linked `Lead.stage` is `CONVERTED` / `WON` / `REGISTERED` (blocks payout before registry!)
     2. Count existing `REFERRAL_FIXED` payouts for that `partner_id` in the current fiscal year; if `count >= annual_reward_limit`, reject with `400/422` ("Annual referral reward cap reached").
4. **Creator Attribution & Retainer Runner:**
   - Extend `/v1/intake/lead` and `/v1/intake/inquiry` (`backend/app/api/v1/endpoints/intake.py`) to accept optional `referral_code` / `partner_code`.
   - Automatically resolve matching active `ChannelPartner` by `tracking_code` or `partner_code` and link `Lead.partner_id` + `Lead.referral_code`.
   - Endpoint `POST /v1/franchise/payouts/generate-retainers` to generate monthly `CREATOR_RETAINER` payouts for active `is_top_creator = True` Creator Partners.

### Phase 2: API Endpoints (`backend/app/api/v1/endpoints/franchise.py`)
Add endpoints alongside existing `/v1/franchise/*`:
- `PATCH /v1/franchise/partners/{id}/promote` — Promote Active CP (`L1 → L2` or `L2 → L3`) with server-side eligibility validation (plus optional Manager override audit log).
- `POST /v1/franchise/partners/{id}/certify` — Mark training certification complete.
- `POST /v1/franchise/partners/{id}/suspend` — Instant zero-tolerance kill switch (requires reason).
- `POST /v1/franchise/partners/{id}/reinstate` — Admin-only reactivation after review.
- `GET /v1/franchise/partners/{id}/inventory` — Demonstrates & enforces exact level-scoped inventory view (L1 blocked, L2 address-only without owner info, Broker co-broking).
- `GET/POST/PATCH /v1/franchise/meetings` — Manage L3 Omshiv-mediated direct meetings.
- `POST /v1/franchise/payouts/generate-retainers` — Monthly retainer batch for top Creator Partners.

---

## 4. Frontend Implementation (`FranchiseHub.tsx` + New Components)

1. **4-Type CP Filter & Cards/Table in `FranchiseHub.tsx`:**
   - Type filter pills: `All CPs` | `Broker CP` | `Active CP` | `Referral Partner` | `Creator Partner`
   - **Active CP Ladder Badge (`L1` / `L2` / `L3`)** with inline progress indicators:
     - Tenure days (`18/30 days`), Certification status (`Certified ✓` / `Pending`), Manager Recommendation button, **Promote to L2/L3** button, and red **Instant Suspend** button.
   - **Referral Partner Quota Meter:** e.g. `2 / 5 Annual Registry Rewards Used` + fixed reward badge (`₹5,000 / registry`).
   - **Creator Partner Attribution Box:** Copyable tracking link (`https://omshiv.com/?ref=ROHIT26`), tracked leads count, Commission %, and `Top Creator Retainer` badge.
   - **Broker CP Badge:** Office verified badge + Co-broking split %.
2. **Inventory Access Preview Drawer (Per CP):**
   - Manager can click **"Preview Access"** on any CP to verify live what that CP sees (e.g. L1 = Blocked, L2 = Address visible / Owner hidden).
3. **L3 Mediated Meetings Tab:**
   - Approve/schedule Omshiv-supervised owner meetings for L3 Active CPs.
4. **Update Register Partner Modal:**
   - Step 1: Pick CP Type (`Broker CP`, `Active CP`, `Referral Partner`, `Creator Partner`) -> dynamically displays the exact relevant inputs (Office address & split % vs L1 start vs Fixed reward & annual cap vs Tracking code & retainer).

---

## 5. Testing Plan
- Unit & API tests in `backend/tests/test_cp_4_tier_governance.py`:
  1. Active CP L1 cannot access inventory; L1 visit without Omshiv staff `accompanied_by` is rejected.
  2. Active CP promotion L1 → L2 fails before 30 days or without certification + manager recommendation; succeeds when all 3 met.
  3. Active CP L2 inventory response strips `owner_name` and `owner_mobile`.
  4. Instant Suspend immediately blocks inventory, meetings, and payouts (`403 Forbidden`) and writes `AuditLog`.
  5. Referral Partner payout blocked if lead is not registered (`CONVERTED`/`REGISTERED`) and blocked once annual limit is reached.
  6. Creator Partner link (`referral_code`) auto-attaches `partner_id` on lead intake and calculates commission/retainer payouts.
- Frontend `tsc && vite build` clean check.
