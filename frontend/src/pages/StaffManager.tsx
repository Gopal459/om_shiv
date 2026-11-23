import React, { useState, useEffect } from 'react';
import {
  Users,
  UserPlus,
  Shield,
  Check,
  AlertCircle,
  RefreshCw,
  KeyRound,
  Building,
  Save,
  CheckSquare,
  X,
} from 'lucide-react';

export const StaffManager: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<'ROSTER' | 'PERMISSIONS'>('ROSTER');
  const [staff, setStaff] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [selectedRoleCode, setSelectedRoleCode] = useState<string>('SALES_MANAGER');
  const [rolePermissions, setRolePermissions] = useState<Record<string, string[]>>({});

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Add Staff Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newMobile, setNewMobile] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newDept, setNewDept] = useState('SALES');
  const [newRole, setNewRole] = useState('SALES_MANAGER');
  const [creating, setCreating] = useState(false);

  const fetchStaffAndRoles = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const headers: Record<string, string> = token
        ? { Authorization: `Bearer ${token}` }
        : {};

      const [staffRes, rolesRes] = await Promise.all([
        fetch('/v1/admin/staff', { headers }).then((r) => (r.ok ? r.json() : [])),
        fetch('/v1/admin/roles', { headers }).then((r) => (r.ok ? r.json() : [])),
      ]);

      setStaff(staffRes);
      setRoles(rolesRes);

      const current = rolesRes.find((r: any) => r.code === selectedRoleCode) || rolesRes[0];
      if (current) {
        setSelectedRoleCode(current.code);
        setRolePermissions(current.permissions || {});
      }
    } catch (err: any) {
      setError('Failed to load staff and roles');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStaffAndRoles();
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
      fetchStaffAndRoles();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCreateStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
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

      setShowAddModal(false);
      setSuccessMsg(`Staff member ${data.name} (${data.employee_id}) created successfully!`);
      setNewName('');
      setNewUsername('');
      setNewPassword('');
      setNewMobile('');
      setNewEmail('');
      fetchStaffAndRoles();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
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
        { key: 'delete', label: 'Delete / Mark Lost' },
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
      label: 'Staff Directory & Access Control',
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-400" />
            Staff & Role Permissions Hub
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage employees, assign multiple organizational roles, and configure granular module permissions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-green-600 hover:bg-green-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-green-900/30"
          >
            <UserPlus className="w-4 h-4" />
            + Add Staff Member
          </button>
          <button
            onClick={fetchStaffAndRoles}
            disabled={loading}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs border border-slate-700 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Sub Tabs */}
      <div className="flex rounded-xl bg-slate-900 p-1 border border-slate-800 w-fit">
        <button
          onClick={() => setActiveSubTab('ROSTER')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
            activeSubTab === 'ROSTER'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          Staff Directory ({staff.length})
        </button>
        <button
          onClick={() => setActiveSubTab('PERMISSIONS')}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
            activeSubTab === 'PERMISSIONS'
              ? 'bg-blue-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          Role & Module Permission Matrix
        </button>
      </div>

      {successMsg && (
        <div className="p-3 bg-green-950/80 border border-green-700/60 rounded-xl text-green-300 text-xs flex items-center gap-2">
          <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-950/80 border border-red-700/60 rounded-xl text-red-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* VIEW 1: STAFF DIRECTORY */}
      {activeSubTab === 'ROSTER' && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-4">Emp ID</th>
                  <th className="p-4">Staff Name</th>
                  <th className="p-4">Username</th>
                  <th className="p-4">Mobile & Email</th>
                  <th className="p-4">Department</th>
                  <th className="p-4">Assigned Role</th>
                  <th className="p-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-200">
                {staff.map((emp) => (
                  <tr key={emp.id} className="hover:bg-slate-800/40">
                    <td className="p-4 font-mono font-bold text-green-400">
                      {emp.employee_id}
                    </td>
                    <td className="p-4 font-semibold text-white">{emp.name}</td>
                    <td className="p-4 font-mono text-slate-300">{emp.username || '—'}</td>
                    <td className="p-4">
                      <div>{emp.mobile}</div>
                      {emp.email && <div className="text-[11px] text-slate-400">{emp.email}</div>}
                    </td>
                    <td className="p-4">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] border border-slate-700">
                        {emp.department_name || 'Management'}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className="px-2 py-0.5 rounded bg-blue-950 text-blue-300 text-[10px] font-bold border border-blue-800">
                        {emp.role_code || 'STAFF'}
                      </span>
                    </td>
                    <td className="p-4 text-center">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          emp.is_active
                            ? 'bg-green-950 text-green-400 border border-green-800'
                            : 'bg-red-950 text-red-400 border border-red-800'
                        }`}
                      >
                        {emp.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* VIEW 2: ROLE PERMISSION MATRIX */}
      {activeSubTab === 'PERMISSIONS' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Roles Selector Sidebar */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1.5">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-3 pb-2">
              Select Role to Configure
            </div>
            {roles.map((r) => (
              <button
                key={r.code}
                onClick={() => handleSelectRole(r.code)}
                className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-between ${
                  selectedRoleCode === r.code
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-900/30'
                    : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
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
          <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white">
                  Configuring Permissions for:{' '}
                  <span className="text-blue-400 font-mono">{selectedRoleCode}</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Check modules to grant access. Permissions apply across all users holding this role.
                </p>
              </div>

              <button
                onClick={handleSavePermissions}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-green-600 hover:bg-green-500 text-white font-bold text-xs rounded-xl shadow-md transition-colors flex-shrink-0"
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
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3"
                  >
                    <div className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                      <CheckSquare className="w-4 h-4 text-green-400" />
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
                                ? 'bg-slate-800/80 text-white font-semibold'
                                : 'text-slate-400 hover:bg-slate-800/30'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => handleTogglePermission(modKey, p.key)}
                              className="w-4 h-4 rounded text-green-600 focus:ring-green-500 border-slate-700 bg-slate-900"
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

      {/* MODAL: ADD STAFF */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-green-400" />
                Add New Staff Member
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateStaff} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g. Ramesh Chandra"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-2 focus:ring-green-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Login Username *
                  </label>
                  <input
                    type="text"
                    required
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="e.g. ramesh"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-2 focus:ring-green-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Password *
                  </label>
                  <input
                    type="password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Min 6 characters"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-2 focus:ring-green-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    10-Digit Mobile *
                  </label>
                  <input
                    type="tel"
                    required
                    value={newMobile}
                    onChange={(e) => setNewMobile(e.target.value)}
                    placeholder="e.g. 9829012345"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-2 focus:ring-green-500 focus:outline-none"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Email Address (Optional)
                  </label>
                  <input
                    type="email"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    placeholder="e.g. ramesh@omshiv.in"
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-2 focus:ring-green-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Department *
                  </label>
                  <select
                    value={newDept}
                    onChange={(e) => setNewDept(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-2 focus:ring-green-500 focus:outline-none"
                  >
                    <option value="SALES">Sales & Business Development</option>
                    <option value="OPERATIONS">Operations & Verification</option>
                    <option value="MANAGEMENT">Executive Management</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Assigned Role *
                  </label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:ring-2 focus:ring-green-500 focus:outline-none"
                  >
                    <option value="SUPER_ADMIN">Super Administrator</option>
                    <option value="SALES_MANAGER">Sales Manager</option>
                    <option value="TELECALLER">Telecaller</option>
                    <option value="VERIFICATION_OFFICER">Verification Officer</option>
                    <option value="FIELD_EXECUTIVE">Field Executive</option>
                    <option value="FRANCHISEE_AGENT">Franchisee / Channel Partner</option>
                  </select>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-5 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-md transition-colors"
                >
                  {creating ? 'Creating...' : 'Create Staff Member'}
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
