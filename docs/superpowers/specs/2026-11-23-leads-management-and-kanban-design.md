# Enterprise Leads Management, Inflow Pipeline & Kanban System Design

**Date:** 2026-11-23  
**Status:** Under Review (Approved Approach A)  
**Author:** Omshiv CRM Engineering  
**Scope:** Frontend Navigation, Dual-Mode Kanban/Table Hub, Lead Detail View (Screenshots 1, 2, 3), and `tbl_leads` Database Schema.

---

## 1. Intent & Context

The Omshiv Buildvision / Propira CRM requires an enterprise lead management engine capable of handling multi-channel lead inflows (website inquiries, builder projects, agent inquiries, 1-click form conversions, manual walk-ins, and bulk CSV imports). The user needs:
1. **Sidebar Navigation** with submenus: *Buy*, *Rent*, *PG*, *Create Lead*, *Import Lead* (matching Screenshot 1).
2. **Support for 6 Inbound Inflow Sources** with automated status tagging and franchisee routing.
3. **Dual-Mode Leads Management Hub** offering an instant toggle between an interactive **Kanban Board View** and a searchable **Data Table View**.
4. **Lead Detail Page Redesign** replicating the exact visual layout of Screenshots 2 & 3, including the top header with badges, 7 circular quick-action buttons, and red capsule pill headers (`Contact Details >`, `Property Details >`, `Others >`).
5. **Database Model & Migration (`tbl_leads`)** implementing the exact 54-field SQL structure, enum codes, and universal soft-delete (`deleted_at`).

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
- **Exact Visual Fidelity**: Match Screenshot 1 for sidebar submenus, and Screenshots 2 & 3 for Lead Detail cards and action strips.
- **Dual-Mode Kanban & Table**: Allow telecallers and sales managers to switch seamlessly between a drag-and-drop Kanban board and a tabular grid with search, filtering, and pagination.
- **Complete Schema Fidelity**: Implement all 54 columns of `tbl_leads` in SQLAlchemy and SQLite/MySQL migration, preserving backward compatibility with existing tests.
- **6 Inflow Methods**: Provide backend and frontend workflows for all 6 inflow sources, including bulk CSV/Excel import and manual lead creation with 24 lead sources.
- **Universal Soft-Delete**: Ensure all deletions soft-delete via `deleted_at`.

### Non-Goals
- Modifying non-lead modules (Property Verifications, Settings, Roles).
- Replacing external SMS/OTP gateways in local development (mocked/stubbed cleanly).

### Anti-Goals
- Breaking existing API routes (`/v1/leads/my-work`, `/v1/leads/{id}`) or breaking the 60 passing pytest tests.
- Rigid Kanban views that don't allow sorting, filtering, or quick tabular review.

---

## 3. Approaches Considered

### Approach A: Unified Dual-Mode Leads Hub with Full Inflow Modals & Schema Alignment (Selected)
- **Navigation**: Sidebar submenus for *Buy*, *Rent*, *PG*, *Create Lead*, *Import Lead*.
- **Hub View**: Single high-performance page with a top-right view switcher (`[Kanban Board View]` ⇄ `[Table View]`). Both modes support filtering by property type (`Buy`, `Rent`, `PG`), status, and temperature.
- **Lead Detail**: Pixel-faithful replica of Screenshots 2 & 3 with red capsule headers, 7 circular action buttons, and responsive cards.
- **Backend**: `0005_tbl_leads_schema.py` migration creating/upgrading `tbl_leads` with 54 fields and repository methods.
- **Why Chosen**: Provides the cleanest user experience, zero navigation friction, full mobile/desktop responsiveness, and 100% adherence to reference screenshots.

### Approach B: Disjoint Separate Pages for Every Submenu
- Separate independent pages for `/leads/buy`, `/leads/rent`, `/leads/pg` with only Kanban view and separate create/import pages.
- **Why Rejected**: Causes code duplication across 3 listing pages, slows navigation, and prevents cross-type filtering.

---

## 4. Architectural & Component Specification

### 4.1. Sidebar Navigation (Screenshot 1)
In `frontend/src/layouts/AdminLayout.tsx`, the `LEADS` item is updated to:
```typescript
{
  id: 'LEADS',
  path: '/leads',
  label: 'Leads',
  icon: Rocket,
  badge: 'Active',
  badgeColor: 'bg-rose-500/10 text-rose-500 border border-rose-500/20',
  subItems: [
    { label: 'Buy', path: '/leads?type=buy' },
    { label: 'Rent', path: '/leads?type=rent' },
    { label: 'PG', path: '/leads?type=pg' },
    { label: 'Create Lead', path: '/leads?action=create' },
    { label: 'Import Lead', path: '/leads?action=import' },
  ],
}
```

### 4.2. 6 Inbound Inflow Sources Specification
1. **Frontend Website / App Inquiries (`Api::saveLead`)**: Property inquiries with OTP verification and franchisee area routing.
2. **Builder Projects Enquiry (`Api::saveProjectLead`)**: Project inquiries stored with `lead_table_name="tbl_builder_project"`.
3. **Agent / Franchisee Direct Inquiries (`Api::saveAgentContactLead`)**: Routed with `assign_franch_id`.
4. **1-Click Public Form Conversions**: Inbound callback requests, problem reports, and service inquiries convert to leads with 1 click.
5. **Manual Lead Creation (`createLeads`)**: Admin/Telecaller modal with property type (Buy, Rent, PG), 24 lead sources (Facebook, Google, Newspaper, Walk-in, etc.), budget, and location.
6. **Bulk Excel / CSV Import (`importLeads`)**: Upload modal parsing CSV/Excel with column mapping, duplicate detection, and batch insertion.

### 4.3. Interactive Kanban Board View
- **Columns by Lead Status**:
  1. **New / Fresh (0)** - Blue accent
  2. **In Progress (1)** - Indigo accent
  3. **Site Visit / Inspection (Stage 2/3)** - Purple accent
  4. **Qualified (4)** - Teal accent
  5. **Converted / Deal Closed (5)** - Emerald accent
  6. **Disqualified / Lost (2)** - Rose accent
- **Card Content**:
  - Customer name & unique lead ID (e.g. `PR141` / `LEAD10023`)
  - Subtitle requirement (e.g. `2 BHK Flat in Alwar`)
  - Badges: Property Type (`Buy` / `Rent` / `PG`), Temperature (`HOT`, `WARM`, `COLD`), 3h SLA indicator.
  - Action buttons: Quick Call, Quick WhatsApp, View Details.
  - Drag-and-drop or 1-click status advance dropdown.

### 4.4. Lead Detail View (Screenshots 2 & 3)
- **Top Header**:
  - Customer Name: Large heading (e.g. `Img Tetst Lead`)
  - Subtitle: `Interested For 2 BHK Flat`
  - Status Badges: `New` (solid blue pill), `Cold` (solid gray/dark pill)
  - **7 Circular Action Buttons**:
    1. 📞 Call / Phone (`bg-indigo-600 hover:bg-indigo-700 text-white`)
    2. ⏰ Clock / Follow-up (`bg-rose-600 hover:bg-rose-700 text-white`)
    3. 🎚️ Toggle / Status (`bg-amber-500 hover:bg-amber-600 text-white`)
    4. 🔀 Reassign / Transfer (`bg-rose-500 hover:bg-rose-600 text-white`)
    5. 🏠 Property Details (`bg-blue-600 hover:bg-blue-700 text-white`)
    6. ↗️ Share / Forward (`bg-sky-500 hover:bg-sky-600 text-white`)
    7. 🕒 Action Logs / History (`bg-emerald-600 hover:bg-emerald-700 text-white`)
- **Card Section 1: Contact Details**
  - Header: Red capsule button `Contact Details >` (`bg-red-600 text-white px-4 py-1 rounded-full font-bold text-xs inline-flex items-center gap-1.5`)
  - Fields inside white rounded card:
    - Follow Up Remark: `N/A`
    - Request ID: `PR141` | Customer Name: `Img Tetst Lead` | Mobile No.: `+91-9352309592`
    - Email: `Tes69@Gmail.Com5`
    - Address: `Alwar5`
    - Status: `New` | Current Update: `N/A`
- **Card Section 2: Property Details**
  - Header: Red capsule button `Property Details >`
  - Fields inside white rounded card:
    - Property Id: `ALWSELL0607` | Looking For: `Flat` | Property Type: `Residential`
    - Property Address: `Bhagat Singh Circle, Sector 7, Alwar, Rajasthan, India`
- **Card Section 3: Others**
  - Header: Red capsule button `Others >`
  - Fields inside white rounded card:
    - Followup Date: `19-Sep-2022 11:57 AM`
    - Received Date: `19-Sep-2022 11:57 AM`
    - Last Updated Date: `19-Sep-2022 11:57 AM` | Last Updated By: `N/A`
    - Assign Date: `19-Sep-2022 11:57 AM` | Assign To: `Om Shiv Properties`

---

## 5. Database Schema & Migration Specification

### Migration `0005_tbl_leads_schema.py`
Ensures table `tbl_leads` exists with all 54 columns:
- `leads_id` INT AUTO_INCREMENT PRIMARY KEY
- `assign_franch_id` INT DEFAULT 0
- `assign_franchstaff_id` INT DEFAULT 0
- `assignfranchisee_date` DATETIME NULL
- `assignfranchiseestaff_date` DATETIME NULL
- `property_id` INT DEFAULT 0
- `lead_table_name` VARCHAR(264) NULL
- `dealer_have` INT DEFAULT 0 (1=Yes, 2=No)
- `lead_status_id` INT NULL
- `lead_source_id` INT NULL
- `address` TEXT NULL
- `contact_name` VARCHAR(255) NOT NULL
- `email` VARCHAR(255) NULL
- `mobile` VARCHAR(32) NOT NULL
- `permission` TEXT NULL
- `nextfollowup_datetime` TIMESTAMP NULL
- `deal_final_price` DECIMAL(18,2) DEFAULT 0.00
- `registry_date` DATETIME NULL
- `property_idno` VARCHAR(200) NULL
- `indv_property_address` TEXT NULL
- `approve_lead_remark` TEXT NULL
- `approve_by` INT DEFAULT 0
- `approve_lead_date` DATETIME NULL
- `deal_close_by` INT DEFAULT 0
- `dealclose_date` DATETIME NULL
- `deal_date` DATETIME NULL
- `lead_status` INT DEFAULT 0 (0=New, 1=In progress, 2=Disqualified, 3=Solved, 4=Qualified, 5=Converted)
- `lead_close_date` DATETIME NULL
- `reference_relation_by` VARCHAR(255) NULL
- `refer_by_name` VARCHAR(255) NULL
- `refer_by_mobile` VARCHAR(255) NULL
- `alternate_contact_mobile` VARCHAR(255) NULL
- `create_by` VARCHAR(255) NULL
- `lead_unique_id` VARCHAR(255) NULL
- `lastfollowup_id` INT DEFAULT 0
- `lastcallstatus_id` INT DEFAULT 0
- `calls_status` INT DEFAULT 0
- `lead_open` INT DEFAULT 1
- `lead_remark` TEXT NULL
- `stage` INT DEFAULT 1 (1=General Follow-up, 2=Site Visit Planned, 3=Site Visit Completed, 4=Re-Site Visit Planned)
- `location_lat` VARCHAR(255) NULL
- `location_long` VARCHAR(255) NULL
- `rating` INT DEFAULT 3 (1=Hot, 2=Warm, 3=Cold)
- `current_update` INT DEFAULT 0
- `update_userid` INT DEFAULT 0
- `disqualified_reason` INT DEFAULT 0
- `is_admin` INT DEFAULT 0
- `call_status_qulified` INT DEFAULT 0
- `last_callstatus_updatetime` DATETIME NULL
- `sold_status` INT DEFAULT 0
- `opportunity_converted` INT DEFAULT 0
- `opportunity_id` INT DEFAULT 0
- `opportunity_datetime` DATETIME NULL
- `deleted_at` TIMESTAMP NULL (Soft-delete support)
- `created_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `modified_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

---

## 6. Verification Plan
1. **Database Migration**: Run migration runner and verify all 54 columns and soft-delete index.
2. **Backend Test Suite**: Verify all 60 existing tests pass + new test for `tbl_leads` and CRUD/inflows.
3. **Frontend Build**: Run `cd frontend; bun run build` to confirm zero TypeScript compilation errors.
4. **Visual Verification**: Confirm sidebar submenus match Screenshot 1, and Lead Detail sections match Screenshots 2 & 3.
