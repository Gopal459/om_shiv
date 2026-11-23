import React, { useState, useEffect } from 'react';
import {
  Users,
  UserPlus,
  Shield,
  Check,
  AlertCircle,
  RefreshCw,
  Save,
  CheckSquare,
  X,
  Plus,
  Trash2,
  Edit2,
  Key,
  ShieldAlert,
  ChevronRight,
  Layers,
} from 'lucide-react';

export const StaffManager: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'ROSTER' | 'ROLES' | 'PERMISSIONS'>('ROSTER');
  const [staff, setStaff] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [selectedRoleCode, setSelectedRoleCode] = useState<string>('SALES_MANAGER');
  const [rolePermissions, setRolePermissions] = useState<Record<string, string[]>>({});

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Add Staff Modal State
  const [showAddStaffModal, setShowAddStaffModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newMobile, setNewMobile] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newDept, setNewDept] = useState('SALES');
  const [newRole, setNewRole] = useState('SALES_MANAGER');
  const [creatingStaff, setCreatingStaff] = useState(false);

  // Edit Staff Modal State
  const [editingStaff, setEditingStaff] = useState<any>(null);
  const [editStaffName, setEditStaffName] = useState('');
  const [editStaffMobile, setEditStaffMobile] = useState('');
  const [editStaffEmail, setEditStaffEmail] = useState('');
  const [editStaffDept, setEditStaffDept] = useState('');
  const [editStaffRole, setEditStaffRole] = useState('');
  const [updatingStaff, setUpdatingStaff] = useState(false);

  // Add Dynamic Role Modal State
  const [showAddRoleModal, setShowAddRoleModal] = useState(false);
  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleCode, setNewRoleCode] = useState('');
  const [newRoleDept, setNewRoleDept] = useState('SALES');
  const [creatingRole, setCreatingRole] = useState(false);

  // Edit Dynamic Role Modal State
  const [editingRole, setEditingRole] = useState<any>(null);
  const [editRoleName, setEditRoleName] = useState('');
  const [editRoleDept, setEditRoleDept] = useState('');
  const [updatingRole, setUpdatingRole] = useState(false);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const headers: Record<string, string> = token
        ? { Authorization: `Bearer ${token}` }
        : {};

      const [staffRes, rolesRes, deptRes] = await Promise.all([
        fetch('/v1/admin/staff', { headers }).then((r) => (r.ok ? r.json() : [])),
        fetch('/v1/admin/roles', { headers }).then((r) => (r.ok ? r.json() : [])),
        fetch('/v1/admin/departments', { headers }).then((r) => (r.ok ? r.json() : [])),
      ]);

      setStaff(staffRes);
      setRoles(rolesRes);
      setDepartments(deptRes);

      if (rolesRes.length > 0) {
        // Keep selected role or select first available
        const current = rolesRes.find((r: any) => r.code === selectedRoleCode) || rolesRes[0];
        if (current) {
          setSelectedRoleCode(current.code);
          setRolePermissions(current.permissions || {});
        }
        if (!newRole && rolesRes[0]) {
          setNewRole(rolesRes[0].code);
        }
      }
    } catch (err: any) {
      setError('Failed to load staff and role data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const handleSelectRole = (code: string) => {
    setSelectedRoleCode(code);
    const target = roles.find((r) => r.code === code);
    if (target) {
      setRolePermissions(target.permissions || {});
    }
    setSuccessMsg('');
    setError('');
  };

  const handleTogglePermission = (module: string, permKey: string) => {
    setRolePermissions((prev) => {
      const currentList = prev[module] || [];
      const updated = currentList.includes(permKey)
        ? currentList.filter((k) => k !== permKey)
        : [...currentList, permKey];
      return { ...prev, [module]: updated };
    });
  };

  const handleSavePermissions = async () => {
    setError('');
    setSuccessMsg('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/admin/roles/${selectedRoleCode}/permissions`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ permissions: rolePermissions }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to update permissions');
      }

      setSuccessMsg(`Permissions for role '${selectedRoleCode}' updated successfully!`);
      fetchAllData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  // --- STAFF ACTIONS ---

  const handleCreateStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingStaff(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/v1/admin/staff', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          name: newName,
          username: newUsername,
          password: newPassword,
          mobile: newMobile,
          email: newEmail || null,
          department_code: newDept,
          role_code: newRole,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create staff');
      }

      setShowAddStaffModal(false);
      setSuccessMsg(`Staff member ${data.name} (${data.employee_id}) created successfully!`);
      setNewName('');
      setNewUsername('');
      setNewPassword('');
      setNewMobile('');
      setNewEmail('');
      fetchAllData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreatingStaff(false);
    }
  };

  const handleOpenEditStaff = (emp: any) => {
    setEditingStaff(emp);
    setEditStaffName(emp.name);
    setEditStaffMobile(emp.mobile);
    setEditStaffEmail(emp.email || '');
    setEditStaffDept(emp.department_code || 'SALES');
    setEditStaffRole(emp.role_code || roles[0]?.code || 'SALES_MANAGER');
  };

  const handleUpdateStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStaff) return;
    setUpdatingStaff(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/admin/staff/${editingStaff.employee_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          name: editStaffName,
          mobile: editStaffMobile,
          email: editStaffEmail || null,
          department_code: editStaffDept,
          role_code: editStaffRole,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update staff member');

      setEditingStaff(null);
      setSuccessMsg(`Staff member ${data.name} updated successfully!`);
      fetchAllData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUpdatingStaff(false);
    }
  };

  const handleDeleteStaff = async (employeeId: string, name: string) => {
    if (!window.confirm(`Are you sure you want to soft delete staff member '${name}' (${employeeId})?`)) {
      return;
    }
    setError('');
    setSuccessMsg('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/admin/staff/${employeeId}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to soft delete staff');

      setSuccessMsg(data.message || `Staff member ${name} soft-deleted.`);
      fetchAllData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  // --- ROLE ACTIONS ---

  const handleCreateRole = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingRole(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/v1/admin/roles', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          name: newRoleName,
          code: newRoleCode ? newRoleCode.toUpperCase() : undefined,
          department_code: newRoleDept,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to create role');

      setShowAddRoleModal(false);
      setSuccessMsg(`Dynamic Role '${data.name}' (${data.code}) created successfully!`);
      setNewRoleName('');
      setNewRoleCode('');
      fetchAllData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreatingRole(false);
    }
  };

  const handleOpenEditRole = (role: any) => {
    setEditingRole(role);
    setEditRoleName(role.name);
    setEditRoleDept(role.department_code || 'SALES');
  };

  const handleUpdateRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRole) return;
    setUpdatingRole(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/admin/roles/${editingRole.code}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          name: editRoleName,
          department_code: editRoleDept,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to update role');

      setEditingRole(null);
      setSuccessMsg(`Role '${data.name}' updated successfully!`);
      fetchAllData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUpdatingRole(false);
    }
  };

  const handleDeleteRole = async (code: string, name: string) => {
    if (!window.confirm(`Are you sure you want to soft delete role '${name}' (${code})?`)) {
      return;
    }
    setError('');
    setSuccessMsg('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/admin/roles/${code}`, {
        method: 'DELETE',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to soft delete role');

      setSuccessMsg(data.message || `Role '${name}' soft-deleted.`);
      fetchAllData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  // Predefined permission matrix blueprint
  const MODULE_PERMISSION_SCHEMA: Record<string, { label: string; perms: { key: string; label: string }[] }> = {
    leads: {
      label: 'Leads & Inquiries Management',
      perms: [
        { key: 'view_all', label: 'View All Organization Leads' },
        { key: 'view_assigned', label: 'View Only Assigned Leads' },
        { key: 'create', label: 'Create New Leads' },
        { key: 'edit_stage', label: 'Log Actions & Advance Pipeline Stage' },
        { key: 'delete', label: 'Soft Delete / Mark Lost' },
        { key: 'reassign', label: 'Reassign Leads to Other Staff' },
        { key: 'convert_inquiries', label: '1-Click Convert Website Inquiries' },
      ],
    },
    properties: {
      label: 'Propira Property Engine & Listings',
      perms: [
        { key: 'view_all', label: 'View All Property Inventory' },
        { key: 'post_listing', label: 'Post New Property / Quick Listing' },
        { key: 'verify', label: 'Perform 7-Step Telephonic/Physical Verification' },
        { key: 'approve_reject', label: 'Approve or Reject Property Listings' },
        { key: 'recycle_bin', label: 'Access Recycle Bin & 1-Click Restore' },
      ],
    },
    masters: {
      label: 'Dynamic Master Options & Pincodes',
      perms: [
        { key: 'view', label: 'View Dynamic Schemas' },
        { key: 'manage_options', label: 'Add / Edit Dynamic Property Options' },
        { key: 'manage_pincodes', label: 'Manage Pincode Serviceability' },
      ],
    },
    staff: {
      label: 'Staff Directory & Role CRUD',
      perms: [
        { key: 'view_staff', label: 'View Staff Directory' },
        { key: 'create_staff', label: 'Add New Staff & Generate EMP-ID' },
        { key: 'edit_permissions', label: 'Configure Role Module Permissions' },
      ],
    },
    settings: {
      label: 'System Settings & Audit Ledger',
      perms: [
        { key: 'view_settings', label: 'View 92 Dynamic System Parameters' },
        { key: 'edit_settings', label: 'Update System Settings & SLAs' },
        { key: 'view_audit', label: 'View Security Audit Logs' },
      ],
    },
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-emerald-500" />
            Staff & Dynamic Roles Hub
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Full dynamic CRUD for organizational roles, staff accounts, and granular module permissions with soft-delete safeguards.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeSubTab === 'ROLES' ? (
            <button
              onClick={() => setShowAddRoleModal(true)}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-blue-900/20"
            >
              <Plus className="w-4 h-4" />
              + Add Dynamic Role
            </button>
          ) : (
            <button
              onClick={() => {
                if (roles.length > 0 && !newRole) setNewRole(roles[0].code);
                setShowAddStaffModal(true);
              }}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-emerald-900/20"
            >
              <UserPlus className="w-4 h-4" />
              + Add Staff Member
            </button>
          )}

          <button
            onClick={fetchAllData}
            disabled={loading}
            className="p-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl text-xs border border-slate-200 dark:border-slate-700 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 3-Way Sub Tabs */}
      <div className="flex flex-wrap rounded-xl bg-slate-100 dark:bg-slate-900 p-1 border border-slate-200 dark:border-slate-800 w-fit">
        <button
          onClick={() => setActiveSubTab('ROSTER')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
            activeSubTab === 'ROSTER'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Staff Directory ({staff.length})
        </button>
        <button
          onClick={() => setActiveSubTab('ROLES')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
            activeSubTab === 'ROLES'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Role Management & CRUD ({roles.length})
        </button>
        <button
          onClick={() => setActiveSubTab('PERMISSIONS')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
            activeSubTab === 'PERMISSIONS'
              ? 'bg-emerald-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Module Permission Matrix
        </button>
      </div>

      {successMsg && (
        <div className="p-3 bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-200 dark:border-emerald-700/60 rounded-xl text-emerald-800 dark:text-emerald-300 text-xs flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-50 dark:bg-rose-950/80 border border-rose-200 dark:border-rose-700/60 rounded-xl text-rose-800 dark:text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* VIEW 1: STAFF DIRECTORY */}
      {activeSubTab === 'ROSTER' && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="p-4">Emp ID</th>
                  <th className="p-4">Staff Name</th>
                  <th className="p-4">Username</th>
                  <th className="p-4">Mobile & Email</th>
                  <th className="p-4">Department</th>
                  <th className="p-4">Dynamic Role</th>
                  <th className="p-4 text-center">Status</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-800 dark:text-slate-200">
                {staff.map((emp) => (
                  <tr key={emp.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="p-4 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                      {emp.employee_id}
                    </td>
                    <td className="p-4 font-semibold text-slate-900 dark:text-white">{emp.name}</td>
                    <td className="p-4 font-mono text-slate-600 dark:text-slate-400">
                      {emp.username || '—'}
                    </td>
                    <td className="p-4">
                      <div>{emp.mobile}</div>
                      <div className="text-[11px] text-slate-400">{emp.email || 'No email'}</div>
                    </td>
                    <td className="p-4 text-slate-600 dark:text-slate-300">
                      {emp.department_name || 'General'}
                    </td>
                    <td className="p-4">
                      <span className="inline-flex items-center gap-1 font-semibold px-2 py-0.5 rounded-full text-[11px] bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800/80">
                        <Shield className="w-3 h-3 text-blue-500" />
                        {emp.role_name || emp.role_code || 'Staff'}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          emp.is_active
                            ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                            : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                        }`}
                      >
                        {emp.is_active ? 'Active' : 'Deactivated'}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleOpenEditStaff(emp)}
                          className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
                          title="Edit Staff Member"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        {emp.employee_id !== 'EMP-0001' && emp.username !== 'admin' && (
                          <button
                            onClick={() => handleDeleteStaff(emp.employee_id, emp.name)}
                            className="p-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/60 dark:hover:bg-rose-900/60 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900/80"
                            title="Soft Delete Staff Member"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* VIEW 2: DYNAMIC ROLES CRUD */}
      {activeSubTab === 'ROLES' && (
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Configured Dynamic Roles ({roles.length})
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  All roles are stored in database and mapped to modular permission policies.
                </p>
              </div>
              <button
                onClick={() => setShowAddRoleModal(true)}
                className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Role
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="p-4">Role Name</th>
                    <th className="p-4">Unique Code</th>
                    <th className="p-4">Department</th>
                    <th className="p-4">Assigned Staff</th>
                    <th className="p-4">Status</th>
                    <th className="p-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-800 dark:text-slate-200">
                  {roles.map((r) => {
                    const isSystemRole = r.code === 'SUPER_ADMIN' || r.code === 'MD';
                    return (
                      <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                        <td className="p-4 font-bold text-slate-900 dark:text-white">
                          <div className="flex items-center gap-2">
                            <Shield className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                            <span>{r.name}</span>
                          </div>
                        </td>
                        <td className="p-4 font-mono font-bold text-blue-600 dark:text-blue-400">
                          {r.code}
                        </td>
                        <td className="p-4 text-slate-600 dark:text-slate-300">
                          {r.department_name || r.department_code || 'General'}
                        </td>
                        <td className="p-4">
                          <span className="font-semibold text-slate-700 dark:text-slate-300">
                            {r.employee_count} Member(s)
                          </span>
                        </td>
                        <td className="p-4">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                            Active
                          </span>
                        </td>
                        <td className="p-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => {
                                handleSelectRole(r.code);
                                setActiveSubTab('PERMISSIONS');
                              }}
                              className="px-2.5 py-1 rounded-lg bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/60 dark:hover:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-semibold text-xs flex items-center gap-1"
                              title="Configure Module Permissions"
                            >
                              <span>Permissions</span>
                              <ChevronRight className="w-3 h-3" />
                            </button>

                            {!isSystemRole && (
                              <>
                                <button
                                  onClick={() => handleOpenEditRole(r)}
                                  className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300"
                                  title="Edit Role Name or Department"
                                >
                                  <Edit2 className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => handleDeleteRole(r.code, r.name)}
                                  className="p-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/60 dark:hover:bg-rose-900/60 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900/80"
                                  title="Soft Delete Role"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* VIEW 3: MODULE PERMISSIONS MATRIX */}
      {activeSubTab === 'PERMISSIONS' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Role Selector Sidebar */}
          <div className="lg:col-span-1 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 space-y-1 shadow-sm">
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider px-3 pb-2">
              Select Role to Configure
            </div>

            {roles.map((r) => (
              <button
                key={r.code}
                onClick={() => handleSelectRole(r.code)}
                className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs font-semibold flex items-center justify-between transition-colors ${
                  selectedRoleCode === r.code
                    ? 'bg-blue-600 text-white font-bold shadow-sm'
                    : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <div>
                  <div className="leading-tight">{r.name}</div>
                  <div className="text-[10px] font-mono opacity-70">{r.code}</div>
                </div>
                <Shield className="w-3.5 h-3.5 opacity-60" />
              </button>
            ))}
          </div>

          {/* Module Permissions Grid */}
          <div className="lg:col-span-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 space-y-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Configuring Permissions for:{' '}
                  <span className="text-blue-600 dark:text-blue-400 font-mono">{selectedRoleCode}</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Check modules to grant access. Permissions apply across all users holding this role.
                </p>
              </div>

              <button
                onClick={handleSavePermissions}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl shadow-md transition-colors flex-shrink-0"
              >
                <Save className="w-4 h-4" />
                Save Permissions
              </button>
            </div>

            <div className="space-y-6">
              {Object.entries(MODULE_PERMISSION_SCHEMA).map(([modKey, modConfig]) => {
                const currentPerms = rolePermissions[modKey] || [];
                return (
                  <div
                    key={modKey}
                    className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-3"
                  >
                    <div className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-2">
                      <CheckSquare className="w-4 h-4 text-emerald-500" />
                      <span>{modConfig.label}</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                      {modConfig.perms.map((p) => {
                        const isChecked = currentPerms.includes(p.key);
                        return (
                          <label
                            key={p.key}
                            className={`flex items-center gap-2.5 p-2 rounded-lg cursor-pointer text-xs transition-colors ${
                              isChecked
                                ? 'bg-white dark:bg-slate-800/80 text-slate-900 dark:text-white font-semibold shadow-xs border border-slate-200 dark:border-slate-700'
                                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/30'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => handleTogglePermission(modKey, p.key)}
                              className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900"
                            />
                            <span>{p.label}</span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* MODAL 1: ADD STAFF MEMBER */}
      {showAddStaffModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-emerald-500" />
                Add New Staff Member
              </h3>
              <button
                onClick={() => setShowAddStaffModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateStaff} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g. Ramesh Chandra"
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Login Username *
                  </label>
                  <input
                    type="text"
                    required
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="e.g. ramesh"
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Password *
                  </label>
                  <input
                    type="password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Min 6 characters"
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    10-Digit Mobile *
                  </label>
                  <input
                    type="tel"
                    required
                    value={newMobile}
                    onChange={(e) => setNewMobile(e.target.value)}
                    placeholder="e.g. 9829012345"
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Email Address (Optional)
                  </label>
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="e.g. ramesh@omshiv.in"
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Department *
                  </label>
                  <select
                    value={newDept}
                    onChange={(e) => setNewDept(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  >
                    {departments.length > 0 ? (
                      departments.map((d) => (
                        <option key={d.code} value={d.code}>
                          {d.name}
                        </option>
                      ))
                    ) : (
                      <>
                        <option value="SALES">Sales & Business Development</option>
                        <option value="OPERATIONS">Operations & Verification</option>
                        <option value="MANAGEMENT">Executive Management</option>
                      </>
                    )}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Assigned Role (Dynamic) *
                  </label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  >
                    {roles.map((r) => (
                      <option key={r.code} value={r.code}>
                        {r.name} ({r.code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddStaffModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold text-xs rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingStaff}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-md transition-colors"
                >
                  {creatingStaff ? 'Creating...' : 'Create Staff Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: EDIT STAFF MEMBER */}
      {editingStaff && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Edit2 className="w-5 h-5 text-blue-500" />
                Edit Staff Member ({editingStaff.employee_id})
              </h3>
              <button
                onClick={() => setEditingStaff(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateStaff} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={editStaffName}
                    onChange={(e) => setEditStaffName(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    10-Digit Mobile *
                  </label>
                  <input
                    type="tel"
                    required
                    value={editStaffMobile}
                    onChange={(e) => setEditStaffMobile(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    value={editStaffEmail}
                    onChange={(e) => setEditStaffEmail(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Department
                  </label>
                  <select
                    value={editStaffDept}
                    onChange={(e) => setEditStaffDept(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  >
                    {departments.length > 0 ? (
                      departments.map((d) => (
                        <option key={d.code} value={d.code}>
                          {d.name}
                        </option>
                      ))
                    ) : (
                      <>
                        <option value="SALES">Sales & Business Development</option>
                        <option value="OPERATIONS">Operations & Verification</option>
                        <option value="MANAGEMENT">Executive Management</option>
                      </>
                    )}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Assigned Role
                  </label>
                  <select
                    value={editStaffRole}
                    onChange={(e) => setEditStaffRole(e.target.value)}
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                  >
                    {roles.map((r) => (
                      <option key={r.code} value={r.code}>
                        {r.name} ({r.code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingStaff(null)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold text-xs rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updatingStaff}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-md transition-colors"
                >
                  {updatingStaff ? 'Saving...' : 'Update Staff Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: ADD DYNAMIC ROLE */}
      {showAddRoleModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-blue-500" />
                Add New Dynamic Role
              </h3>
              <button
                onClick={() => setShowAddRoleModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateRole} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Role Display Name *
                </label>
                <input
                  type="text"
                  required
                  value={newRoleName}
                  onChange={(e) => setNewRoleName(e.target.value)}
                  placeholder="e.g. Senior Verification Officer"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Unique Role Code (Optional - Auto generated)
                </label>
                <input
                  type="text"
                  value={newRoleCode}
                  onChange={(e) => setNewRoleCode(e.target.value.toUpperCase())}
                  placeholder="e.g. SR_VERIFICATION_OFFICER"
                  className="w-full font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none uppercase"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Department *
                </label>
                <select
                  value={newRoleDept}
                  onChange={(e) => setNewRoleDept(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="SALES">Sales & Business Development</option>
                  <option value="OPERATIONS">Operations & Verification</option>
                  <option value="MANAGEMENT">Executive Management</option>
                </select>
              </div>

              <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddRoleModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold text-xs rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingRole}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-md transition-colors"
                >
                  {creatingRole ? 'Creating...' : 'Create Dynamic Role'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: EDIT DYNAMIC ROLE */}
      {editingRole && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Edit2 className="w-5 h-5 text-blue-500" />
                Edit Dynamic Role ({editingRole.code})
              </h3>
              <button
                onClick={() => setEditingRole(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateRole} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Role Display Name *
                </label>
                <input
                  type="text"
                  required
                  value={editRoleName}
                  onChange={(e) => setEditRoleName(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Department *
                </label>
                <select
                  value={editRoleDept}
                  onChange={(e) => setEditRoleDept(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="SALES">Sales & Business Development</option>
                  <option value="OPERATIONS">Operations & Verification</option>
                  <option value="MANAGEMENT">Executive Management</option>
                </select>
              </div>

              <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingRole(null)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold text-xs rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updatingRole}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-md transition-colors"
                >
                  {updatingRole ? 'Saving...' : 'Update Role'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default StaffManager;
