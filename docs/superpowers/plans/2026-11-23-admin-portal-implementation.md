# Modern Admin Portal & Role-Based Access Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete modern Admin Portal with UserId/Password authentication, an Executive Dashboard, and Role-Based Staff & Permission Management for Omshiv Buildvision CRM.

**Architecture:** Extend the `Employee` model with username and PBKDF2-HMAC password hashing, add dedicated `/v1/auth/admin/login` and `/v1/admin/staff` APIs, and implement a modern React sidebar layout with an Executive KPI Dashboard and interactive Role Permission Matrix.

**Tech Stack:** FastAPI, SQLAlchemy (Async), Pydantic v2, PyJWT, React 18, TypeScript, Tailwind CSS, Lucide icons, Bun runtime.

**Spec:** `docs/superpowers/specs/2026-11-23-admin-portal-design.md`

## Global Constraints
- Passwords must be hashed using PBKDF2-HMAC-SHA256 with cryptographically random 16-byte salt and at least 100,000 iterations.
- Default Super Admin credentials: username `admin`, email `admin@omshiv.in`, password `Admin@123`, role `SUPER_ADMIN`.
- System roles: `SUPER_ADMIN`, `SALES_MANAGER`, `TELECALLER`, `VERIFICATION_OFFICER`, `FIELD_EXECUTIVE`, `FRANCHISEE_AGENT`.
- Admin Login accepts username, email, or employee_id as login identifier.
- Zero hardcoded UI select enums; permissions are persisted as JSON objects in `roles.permissions`.

## Review Focus
1. Password hash verification correctly rejects malformed or altered hashes without raising 500 errors.
2. Case-insensitive username lookup ensures `Admin` or `ADMIN` resolves to `admin`.
3. Inactive staff (`is_active = False`) are blocked from logging in with a 403 Forbidden.
4. Granular permissions update persists and immediately reflects in newly issued tokens.
5. Frontend sidebar navigates smoothly between Dashboard, Staff, Leads, Properties, Masters, and Settings.

---

### Task 1: Backend Credential Hashing, Schema Extension & Seeding

**Files:**
- Modify: `backend/app/models/identity.py`
- Create: `backend/app/core/passwords.py`
- Modify: `backend/app/services/identity_seed.py`
- Test: `backend/tests/test_admin_auth.py`

**Interfaces:**
- Consumes: `app.models.identity.Employee`, `app.models.identity.Role`, `app.models.identity.Department`
- Produces: `hash_password(password: str) -> str`, `verify_password(plain: str, hashed: str) -> bool`, seeded `admin` employee.

- [ ] **Step 1: Write tests for password hashing and employee credentials**
- [ ] **Step 2: Run test to verify it fails (`pytest backend/tests/test_admin_auth.py`)**
- [ ] **Step 3: Implement `hash_password` and `verify_password` in `app/core/passwords.py`**
- [ ] **Step 4: Update `Employee` model with `username` and `password_hash` fields in `app/models/identity.py`**
- [ ] **Step 5: Implement `seed_admin_user` in `app/services/identity_seed.py`**
- [ ] **Step 6: Run tests to verify they pass**
- [ ] **Step 7: Commit changes**

---

### Task 2: Admin Login API (`POST /v1/auth/admin/login`)

**Files:**
- Create: `backend/app/api/v1/endpoints/admin_auth.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_admin_auth.py`

**Interfaces:**
- Consumes: `app.core.passwords.verify_password`, `app.core.security.create_access_token`
- Produces: `POST /v1/auth/admin/login` returning `{ access_token, token_type, user: { employee_id, name, username, role, department, permissions } }`

- [ ] **Step 1: Add login endpoint tests to `test_admin_auth.py` (success, bad password, inactive user, case insensitivity)**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `/v1/auth/admin/login` in `backend/app/api/v1/endpoints/admin_auth.py`**
- [ ] **Step 4: Register router in `backend/app/main.py`**
- [ ] **Step 5: Run tests to verify all pass**
- [ ] **Step 6: Commit changes**

---

### Task 3: Admin Staff & Role Permission APIs

**Files:**
- Create: `backend/app/api/v1/endpoints/admin_staff.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_admin_staff.py`

**Interfaces:**
- Produces:
  - `GET /v1/admin/staff`
  - `POST /v1/admin/staff`
  - `GET /v1/admin/roles`
  - `PUT /v1/admin/roles/{code}/permissions`

- [ ] **Step 1: Write tests in `test_admin_staff.py` for listing staff, creating staff, and updating role permissions**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement endpoints in `backend/app/api/v1/endpoints/admin_staff.py`**
- [ ] **Step 4: Register router in `backend/app/main.py`**
- [ ] **Step 5: Run tests to verify all pass**
- [ ] **Step 6: Commit changes**

---

### Task 4: Modern Admin UI Shell, Layout & Executive Dashboard

**Files:**
- Create: `frontend/src/layouts/AdminLayout.tsx`
- Create: `frontend/src/pages/AdminDashboard.tsx`
- Modify: `frontend/src/pages/Login.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `/v1/auth/admin/login`, `/v1/leads/my-work`, `/v1/verification/queue`, `/v1/admin/recycle-bin`, `/v1/admin/staff`
- Produces: Sleek sidebar navigation, KPI overview cards, quick actions, and seamless tab transitions.

- [ ] **Step 1: Update `Login.tsx` with modern Username/Password login tab and quick-fill for `admin` / `Admin@123`**
- [ ] **Step 2: Implement `AdminLayout.tsx` with sidebar navigation, branding, user badge, and logout**
- [ ] **Step 3: Implement `AdminDashboard.tsx` with live KPI stats cards, action shortcuts, and recent lead feed**
- [ ] **Step 4: Update `App.tsx` to mount `AdminLayout` and routes**
- [ ] **Step 5: Verify build with `bun run build`**
- [ ] **Step 6: Commit changes**

---

### Task 5: Staff & Role Permission Manager UI

**Files:**
- Create: `frontend/src/pages/StaffManager.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `/v1/admin/staff`, `/v1/admin/roles`, `PUT /v1/admin/roles/{code}/permissions`
- Produces: Interactive staff roster table, "Add Staff" modal, and Role Permission Matrix with module checkboxes.

- [ ] **Step 1: Implement `StaffManager.tsx` with staff directory, creation dialog, and permission matrix editor**
- [ ] **Step 2: Wire `StaffManager` into `App.tsx` under the "Staff & Roles" sidebar link**
- [ ] **Step 3: Verify build with `bun run build`**
- [ ] **Step 4: Commit changes**

---

### Task 6: Whole-Suite Verification & Final Build Verification

- [ ] **Step 1: Run full backend test suite (`pytest backend/tests`) to ensure 100% pass across all 50+ tests**
- [ ] **Step 2: Run frontend production build (`bun run build`) in `frontend/`**
- [ ] **Step 3: Verify end-to-end `bun dev` runner compatibility**
- [ ] **Step 4: Final commit and summary report**
