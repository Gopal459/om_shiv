import React from 'react';
import {
  LayoutDashboard,
  Users,
  CheckSquare,
  Building2,
  Trash2,
  Sliders,
  Settings,
  LogOut,
  Shield,
  ShieldAlert,
} from 'lucide-react';

export type AdminTab =
  | 'DASHBOARD'
  | 'STAFF'
  | 'MY_WORK'
  | 'LEAD_DETAIL'
  | 'VERIFICATION'
  | 'RECYCLE_BIN'
  | 'DYNAMIC_MASTERS'
  | 'SETTINGS';

interface AdminLayoutProps {
  user: any;
  activeTab: AdminTab;
  onSelectTab: (tab: AdminTab) => void;
  onLogout: () => void;
  children: React.ReactNode;
}

export const AdminLayout: React.FC<AdminLayoutProps> = ({
  user,
  activeTab,
  onSelectTab,
  onLogout,
  children,
}) => {
  const isSuperAdmin = user?.role === 'SUPER_ADMIN' || user?.role === 'MD';

  const navItems = [
    {
      id: 'DASHBOARD' as AdminTab,
      label: 'Executive Dashboard',
      icon: LayoutDashboard,
      badge: 'Live',
    },
    {
      id: 'STAFF' as AdminTab,
      label: 'Staff & Roles Manager',
      icon: Users,
      badge: isSuperAdmin ? 'Admin' : undefined,
    },
    {
      id: 'MY_WORK' as AdminTab,
      label: 'Sales Queue & Leads',
      icon: CheckSquare,
    },
    {
      id: 'VERIFICATION' as AdminTab,
      label: 'Property Verifications',
      icon: Building2,
    },
    {
      id: 'RECYCLE_BIN' as AdminTab,
      label: 'Recycle Bin & Requests',
      icon: Trash2,
    },
    {
      id: 'DYNAMIC_MASTERS' as AdminTab,
      label: 'Dynamic Master Options',
      icon: Sliders,
    },
    {
      id: 'SETTINGS' as AdminTab,
      label: 'System Settings & Audit',
      icon: Settings,
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col flex-shrink-0">
        {/* Brand Header */}
        <div className="h-16 px-5 border-b border-slate-800 flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-green-600 to-emerald-500 rounded-xl shadow-md">
            <Building2 className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-black text-white tracking-tight leading-tight">
              Omshiv Buildvision
            </h1>
            <p className="text-[10px] text-green-400 font-mono tracking-wider">
              PROPORTAL ENGINE
            </p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <div className="px-3 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Modules & Operations
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              activeTab === item.id ||
              (item.id === 'MY_WORK' && activeTab === 'LEAD_DETAIL');

            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-green-600 text-white shadow-lg shadow-green-900/30'
                    : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${
                      isActive
                        ? 'bg-green-700 text-green-100'
                        : 'bg-slate-800 text-slate-300 border border-slate-700'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User Profile & Logout Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-green-950 border border-green-700/60 flex items-center justify-center text-green-300 font-bold text-xs">
                {user?.name ? user.name.slice(0, 2).toUpperCase() : 'AD'}
              </div>
              <div className="overflow-hidden">
                <div className="text-xs font-bold text-white truncate">
                  {user?.name || 'Administrator'}
                </div>
                <div className="flex items-center gap-1 text-[10px] text-green-400 font-mono">
                  <Shield className="w-2.5 h-2.5" />
                  <span>{user?.role || 'SUPER_ADMIN'}</span>
                </div>
              </div>
            </div>

            <button
              onClick={onLogout}
              className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
              title="Log out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-slate-950 overflow-y-auto">
        {/* Top bar */}
        <header className="h-16 border-b border-slate-800/80 px-6 flex items-center justify-between bg-slate-900/40 backdrop-blur-sm sticky top-0 z-40">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400">Current View:</span>
            <span className="text-xs font-bold text-white bg-slate-800 px-2.5 py-1 rounded-md border border-slate-700">
              {navItems.find((n) => n.id === activeTab)?.label || 'Console'}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-slate-400 bg-slate-900/80 border border-slate-800 px-3 py-1 rounded-full">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              <span>FastAPI Backend Active (Port 8000)</span>
            </div>
          </div>
        </header>

        {/* Content Body */}
        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
export default AdminLayout;
