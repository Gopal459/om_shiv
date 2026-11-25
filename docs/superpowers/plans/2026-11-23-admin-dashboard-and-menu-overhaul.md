# Admin Dashboard & Enterprise Sidebar Navigation Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the 11-module sidebar navigation with collapsible submenus, 6 vibrant gradient KPI cards with PR/FR metrics, 3 Recharts interactive analytics charts (Opportunity Donut, Call Horizontal Bar, and Property Inventory Column Bar), and high-value executive widgets (Leaderboard, SLA activity stream, and Jaipur locality hotspots).

**Architecture:** Modern React + TypeScript + Recharts SPA architecture integrated into `AdminLayout.tsx` and `AdminDashboard.tsx`, with URL routing via `react-router-dom` and persistent sub-menu state.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Recharts 3.11, Lucide React, Vite, FastAPI backend.

**Spec:** [dashboard-and-menu-design.md](file:///C:/Users/LENOVO/.gemini/antigravity/brain/7a67fb5d-7d80-4685-9f26-14985a345470/dashboard-and-menu-design.md)

---

## Global Constraints
- Zero disruption to existing functionality (`StaffManager`, `MyWork`, `LeadDetail`, `PropertyVerification`, `RecycleBinView`, `SettingsEditor`, `DynamicMastersEditor`).
- Full light and dark mode compatibility with high contrast.
- 100% clean TypeScript build (`bun run build`).
- All 60 backend pytest tests must continue passing.

## Review Focus
1. Menu collapse & submenu drawer state persistence when navigating between views.
2. Recharts responsive container dimensions ensuring no chart overflow on mobile/tablet or sidebar collapse.
3. Dark and light mode tooltip readability inside Recharts pie and bar charts.
4. "More Info ->" click routing correctly to the appropriate lead filter or property view.
5. Consistent color fidelity matching the user's reference screenshots.

---

### Task 1: 11-Module Sidebar Navigation with Collapsible Submenus & Sub-Routes

**Files:**
- Modify: `frontend/src/layouts/AdminLayout.tsx`
- Modify: `frontend/src/App.tsx`
- Test: Verify build with `bun run build`

- [x] **Step 1: Define Submenu Navigation Schema in `AdminLayout.tsx`**
  - Add 11 top-level categories matching Screenshot 3:
    1. Dashboard (`/dashboard`)
    2. Website Forms (`/website-forms` with submenus: Inbound Inquiries, Contact Us, Valuations)
    3. Leads (`/leads` with submenus: All Leads, New Intake, Untouched 3h SLA, Qualified)
    4. Opportunities (`/opportunities` with submenus: Active Pipeline, Site Visits, Won)
    5. Property (`/properties` with submenus: All Inventory, 7-Step Verifications `/verifications`, Expired Listings, Recycle Bin `/recycle-bin`)
    6. Homepage CMS (`/homepage` with submenus: Hero Banners, Featured Projects)
    7. Panel User (`/staff` with submenus: Staff Directory, Dynamic Roles, Permissions)
    8. Blog (`/blogs` with submenus: Articles, Market Reports)
    9. Propira Users (`/users` with submenus: Buyers, Sellers, Owners)
    10. Pages (`/pages` with submenus: CMS Pages, Terms)
    11. Franchise (`/franchise` with submenus: Channel Partners, Outlets)
    12. System Settings & Masters (`/settings`, `/masters`)
  - Add state for open/collapsed submenu sections (`openSubmenus: Record<string, boolean>`).
  - Add red/coral active accent styling matching Screenshot 3 (`border-l-4 border-rose-500 text-rose-500 bg-rose-500/10` or active badge).

- [x] **Step 2: Add Sub-Routes & Placeholder Views in `App.tsx`**
  - Register route handlers for all top-level paths and submenus so clicking any menu item loads a dedicated view without 404 or white screen.

- [x] **Step 3: Build & verify navigation**
  - Run `cd frontend; bun run build` and ensure 0 TypeScript errors.

---

### Task 2: 6 Colorful Vibrant Gradient KPI Cards Component

**Files:**
- Modify: `frontend/src/pages/AdminDashboard.tsx`
- Test: Verify build with `bun run build`

- [x] **Step 1: Implement the 6 Gradient KPI Cards**
  - Match Screenshot 1 exact visual specifications:
    1. **New Leads**: Purple gradient (`from-fuchsia-600 via-purple-600 to-indigo-700`), count 236, `PR 111 FR 123`, `More Info ->`
    2. **Open Leads**: Orange gradient (`from-amber-500 via-orange-500 to-red-600`), count 267, `PR 120 FR 131`, `More Info ->`
    3. **Missing Leads**: Crimson/Brown gradient (`from-rose-800 via-stone-800 to-neutral-900`), count 267, `PR 120 FR 131`, `More Info ->`
    4. **Converted Opportunity**: Navy/Blue gradient (`from-slate-900 via-blue-950 to-indigo-950`), count 52, `PR 17 FR 33`, `More Info ->`
    5. **Qualified Leads**: Teal/Cyan gradient (`from-teal-600 via-emerald-600 to-cyan-700`), count 5, `PR 1 FR 0`, `More Info ->`
    6. **All Leads**: Royal Blue gradient (`from-blue-600 via-indigo-600 to-violet-700`), count 332, `PR 141 FR 169`, `More Info ->`
  - Add subtle glassmorphism circles in top-left corner of cards matching the screenshot aesthetic.
  - Connect `More Info ->` to navigate to `/leads`.

- [x] **Step 2: Build & verify cards**
  - Run `cd frontend; bun run build` and ensure 0 TypeScript errors.

---

### Task 3: 3 Recharts Visual Analytics Widgets

**Files:**
- Modify: `frontend/src/pages/AdminDashboard.tsx`
- Test: Verify build with `bun run build`

- [x] **Step 1: Implement Opportunity Donut Chart**
  - Import `ResponsiveContainer`, `PieChart`, `Pie`, `Cell`, `Tooltip`, `Legend` from `recharts`.
  - Data: New (44, `#10b981`), Open (47, `#6366f1`), Missing (47, `#f59e0b`), Qualified (15, `#d946ef`), All (64, `#38bdf8`).
  - Center label in donut hole with total count.
  - Custom dark/light mode tooltip.

- [x] **Step 2: Implement Call Performance Horizontal Bar Chart**
  - Import `BarChart`, `Bar`, `XAxis`, `YAxis`, `CartesianGrid` from `recharts` with `layout="vertical"`.
  - Categories: `Calls` (with colored breakdown bars: 39, 44, 44, 38, 1, 99) and `Problem` (6, 6, 6, 3, 0, 14).
  - High-contrast bar colors matching Screenshot 2.

- [x] **Step 3: Implement Property Lifecycle Multi-Column Chart**
  - Recharts vertical grouped BarChart with categories:
    - New & Assign Property
    - Verified & Live Property
    - Expired Properties
    - Deleted Properties
    - Sold Properties
  - Multi-bar series matching Screenshot 2.

- [x] **Step 4: Build & verify charts**
  - Run `cd frontend; bun run build` and ensure 0 TypeScript errors.

---

### Task 4: Executive Additions, End-to-End Verification & Commit

**Files:**
- Modify: `frontend/src/pages/AdminDashboard.tsx`
- Test: `bun run build` and `pytest backend/tests`

- [x] **Step 1: Add High-Value Executive Additions**
  - **Agent / Telecaller Leaderboard**: Performance table with avatar, calls logged, site visits, and conversion rate.
  - **Live Lead Activity Ticker**: Real-time event log with time-ago stamps.
  - **Jaipur Hotspot Demand Chips**: Locality demand indicators (Vaishali, Mansarovar, Jagatpura, etc.).

- [x] **Step 2: End-to-End Verification**
  - Build frontend: `bun run build` (Passed in 8.20s)
  - Run backend tests: `.venv\Scripts\pytest backend/tests -q` (60 passed in 9.18s)
  - Verify clean working tree and commit changes to `feature/milestone-1-core-foundation`.
