# Modern Admin Portal & Role-Based Access Control Spec

**Date:** 2026-11-23  
**Status:** Approved  
**Author:** Omshiv CRM Engineering  
**Scope:** Admin Portal, Username/Password Auth, Executive Dashboard, Staff & Role Permission Management

---

## 1. Executive Summary & Intent
The system requires a dedicated, modern administrative console for the Omshiv Buildvision CRM & Propira Real Estate Engine. Super Admin and authorized staff must be able to log in securely using credentials (`username`/`userId` and `password`), view an operational Executive Dashboard, manage employees across multiple departments and roles, and dynamically configure granular module permissions.

---

## 2. Authentication & Identity Architecture
### 2.1 Credential Schema Update (`Employee`)
Extend `Employee` model with:
- `username`: `VARCHAR(50)`, unique, indexable (case-insensitive search).
- `password_hash`: `VARCHAR(255)`, securely hashed with PBKDF2-HMAC-SHA256 (with cryptographically random 16-byte salt, 100,000 iterations).

### 2.2 Default Super Admin Seed
Idempotently seeded on startup / migration:
- **Employee ID:** `EMP-0001`
- **Name:** `Super Administrator`
- **Username:** `admin`
- **Email:** `admin@omshiv.in`
- **Mobile:** `9876543210`
- **Password:** `Admin@123`
- **Role:** `SUPER_ADMIN` (permissions: full wildcard `{"*": ["*"]}`)

### 2.3 Login Endpoint
- `POST /v1/auth/admin/login`
  - **Payload:** `{ "username": "admin", "password": "..." }` (accepts username, email, or employee_id).
  - **Response:**
    ```json
    {
      "access_token": "jwt_token...",
      "token_type": "bearer",
      "user": {
        "employee_id": "EMP-0001",
        "name": "Super Administrator",
        "username": "admin",
        "role": "SUPER_ADMIN",
        "department": "MANAGEMENT",
        "permissions": { ... }
      }
    }
    ```

---

## 3. Staff & Role-Based Permissions
### 3.1 Role Hierarchy
1. `SUPER_ADMIN`: Unrestricted master access.
2. `SALES_MANAGER`: Full lead access, team reassignment, reports.
3. `TELECALLER`: Lead action logging, inquiry conversion, calling queue.
4. `VERIFICATION_OFFICER`: Property verification pipeline, document upload, approval checklists.
5. `FIELD_EXECUTIVE`: Site visit logs, customer meetings.
6. `FRANCHISEE_AGENT`: Regional property submissions and assigned leads.

### 3.2 Granular Module Permission Structure
Permissions stored in `roles.permissions` JSON:
```json
{
  "leads": ["view_all", "view_assigned", "create", "edit_stage", "convert_inquiries"],
  "properties": ["post_listing", "verify", "approve_reject", "recycle_bin"],
  "masters": ["view", "manage_options", "manage_pincodes"],
  "staff": ["view_staff", "create_staff", "edit_permissions"],
  "settings": ["view_settings", "edit_settings", "view_audit"]
}
```

### 3.3 Admin Staff APIs
- `GET /v1/admin/staff` - List all employees with their department, role, status.
- `POST /v1/admin/staff` - Create new staff (generates `EMP-XXXX` sequence, hashes password).
- `GET /v1/admin/roles` - List all predefined roles with active permission definitions.
- `PUT /v1/admin/roles/{code}/permissions` - Update granular permissions for a role.

---

## 4. Modern Admin UI Architecture
### 4.1 Layout & Navigation (`AdminLayout`)
- **Collapsible Modern Sidebar:**
  - Branding: Omshiv Buildvision Logo + Propira Engine subtitle.
  - Navigation links:
    - 📊 **Dashboard** (Executive metrics, quick action triggers, lead stream)
    - 👥 **Staff & Roles** (Directory, Add Staff modal, Permission matrix)
    - 🎯 **Leads & Inquiries** (My Work queue, unassigned leads, 1-click callback conversion)
    - 🏢 **Properties & Verification** (Verification queue, listings, Recycle Bin with 1-click restore)
    - ⚙️ **Dynamic Masters** (Dynamic property options & pincodes editor)
    - 🛡️ **Settings & Audit** (The 92 dynamic parameters & audit trail)
  - User footer: Avatar, user name, role badge, and one-click Logout.

### 4.2 Executive Dashboard (`AdminDashboard`)
- KPI metrics row:
  - Total Active Leads
  - Untouched / Urgent Leads
  - Properties in Verification Queue
  - Soft-Deleted Properties in Recycle Bin
  - Total Active Staff
- Quick Actions:
  - "+ Add Staff Member"
  - "Review Verification Queue"
  - "1-Click Convert Inquiries"
  - "Configure Master Options"
- Real-time recent leads activity table.

### 4.3 Staff & Permission Manager (`StaffManager`)
- Staff Directory table with status pills (Active/Inactive), Role badges, and Contact info.
- "Add Staff" modal: Full name, Username, Password, Mobile, Email, Department, Role.
- Interactive Role Permission Matrix: Accordion/grid of modules with checkboxes to toggle permissions and save dynamically.

---

## 5. Verification & Acceptance Criteria
1. Backend tests passing: Admin login, password hashing, staff creation, role permissions update.
2. Frontend build passing: Clean TypeScript compilation and Vite production build.
3. Super Admin can log in with `admin` / `Admin@123` and access all administrative capabilities.
