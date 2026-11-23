import React, { useState, useEffect, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
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
  Sun,
  Moon,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

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
  activeTab?: AdminTab;
  onSelectTab?: (tab: AdminTab) => void;
  onLogout: () => void;
  children?: React.ReactNode;
}

export interface NavItem {
  id: AdminTab;
  path: string;
  label: string;
  shortLabel: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeColor?: string;
}

export interface NavCategory {
  title: string;
  items: NavItem[];
}

export const AdminLayout: React.FC<AdminLayoutProps> = ({
  user,
  activeTab: activeTabProp,
  onSelectTab,
  onLogout,
  children,
}) => {
  const { toggleTheme, isDark } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  // Collapsible sidebar state (persisted in localStorage)
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('omshiv_sidebar_collapsed') === 'true';
  });

  // Mobile drawer state
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem('omshiv_sidebar_collapsed', String(isCollapsed));
  }, [isCollapsed]);

  // Derive activeTab from URL pathname if not explicitly passed
  const activeTab = useMemo<AdminTab>(() => {
    if (activeTabProp) return activeTabProp;
    const p = location.pathname;
    if (p.startsWith('/staff')) return 'STAFF';
    if (p.startsWith('/leads')) {
      if (p.length > 7) return 'LEAD_DETAIL';
      return 'MY_WORK';
    }
    if (p.startsWith('/verifications')) return 'VERIFICATION';
    if (p.startsWith('/recycle-bin')) return 'RECYCLE_BIN';
    if (p.startsWith('/masters')) return 'DYNAMIC_MASTERS';
    if (p.startsWith('/settings')) return 'SETTINGS';
    return 'DASHBOARD';
  }, [activeTabProp, location.pathname]);

  const isSuperAdmin = user?.role === 'SUPER_ADMIN' || user?.role === 'MD';

  const navCategories: NavCategory[] = [
    {
      title: 'Overview',
      items: [
        {
          id: 'DASHBOARD',
          path: '/dashboard',
          label: 'Executive Dashboard',
          shortLabel: 'Dashboard',
          icon: LayoutDashboard,
          badge: 'Live',
          badgeColor: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20',
        },
      ],
    },
    {
      title: 'Staff & Access',
      items: [
        {
          id: 'STAFF',
          path: '/staff',
          label: 'Staff & Roles Manager',
          shortLabel: 'Staff',
          icon: Users,
          badge: isSuperAdmin ? 'Admin' : undefined,
          badgeColor: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20',
        },
      ],
    },
    {
      title: 'Sales & Inventory',
      items: [
        {
          id: 'MY_WORK',
          path: '/leads',
          label: 'Sales Queue & Leads',
          shortLabel: 'Leads',
          icon: CheckSquare,
        },
        {
          id: 'VERIFICATION',
          path: '/verifications',
          label: 'Property Verifications',
          shortLabel: 'Verify',
          icon: Building2,
          badge: '7-Step',
          badgeColor: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20',
        },
        {
          id: 'RECYCLE_BIN',
          path: '/recycle-bin',
          label: 'Recycle Bin & Requests',
          shortLabel: 'Recycle',
          icon: Trash2,
        },
      ],
    },
    {
      title: 'System & Schema',
      items: [
        {
          id: 'DYNAMIC_MASTERS',
          path: '/masters',
          label: 'Dynamic Master Options',
          shortLabel: 'Masters',
          icon: Sliders,
        },
        {
          id: 'SETTINGS',
          path: '/settings',
          label: 'System Settings & Audit',
          shortLabel: 'Settings',
          icon: Settings,
        },
      ],
    },
  ];

  // Flat list for header lookup
  const flatNavItems = navCategories.flatMap((c) => c.items);
  const currentNav =
    flatNavItems.find(
      (n) =>
        n.id === activeTab ||
        (n.id === 'MY_WORK' && activeTab === 'LEAD_DETAIL') ||
        n.path === location.pathname ||
        (n.path !== '/dashboard' && n.path !== '/' && location.pathname.startsWith(n.path))
    ) || flatNavItems[0];

  return (
    <div
      className={`min-h-screen flex transition-colors duration-300 font-sans ${
        isDark ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'
      }`}
    >
      {/* Mobile Backdrop Overlay */}
      {isMobileOpen && (
        <div
          onClick={() => setIsMobileOpen(false)}
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm lg:hidden transition-opacity"
        />
      )}

      {/* Sidebar Navigation */}
      <aside
        className={`fixed lg:sticky top-0 h-screen z-50 flex flex-col transition-all duration-300 ease-in-out border-r select-none ${
          isDark
            ? 'bg-slate-900/95 border-slate-800 backdrop-blur-md shadow-2xl shadow-black/40'
            : 'bg-white border-slate-200/90 shadow-lg shadow-slate-200/60'
        } ${isCollapsed ? 'lg:w-20' : 'lg:w-64'} ${
          isMobileOpen ? 'translate-x-0 w-64' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div
          className={`h-16 px-4 border-b flex items-center justify-between ${
            isDark ? 'border-slate-800/80' : 'border-slate-200'
          }`}
        >
          <div
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-3 overflow-hidden cursor-pointer"
          >
            <div className="relative p-2.5 bg-gradient-to-tr from-emerald-600 to-green-500 rounded-xl shadow-md shadow-emerald-900/30 flex-shrink-0 group">
              <Building2 className="w-5 h-5 text-white" />
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full animate-ping opacity-75"></span>
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full"></span>
            </div>
            {(!isCollapsed || isMobileOpen) && (
              <div className="overflow-hidden leading-tight">
                <h1
                  className={`text-sm font-black tracking-tight truncate ${
                    isDark ? 'text-white' : 'text-slate-900'
                  }`}
                >
                  Omshiv Buildvision
                </h1>
                <p className="text-[10px] text-emerald-500 font-mono tracking-wider font-bold">
                  PROPORTAL ENGINE
                </p>
              </div>
            )}
          </div>

          {/* Mobile Close Button */}
          <button
            onClick={() => setIsMobileOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Categories & Links */}
        <nav className="flex-1 px-3 py-4 space-y-4 overflow-y-auto overflow-x-hidden custom-scrollbar">
          {navCategories.map((category) => (
            <div key={category.title} className="space-y-1">
              {(!isCollapsed || isMobileOpen) ? (
                <div
                  className={`px-3 pb-1 text-[10px] font-bold uppercase tracking-wider ${
                    isDark ? 'text-slate-500' : 'text-slate-400'
                  }`}
                >
                  {category.title}
                </div>
              ) : (
                <div className="border-t border-slate-200 dark:border-slate-800 my-2 mx-2"></div>
              )}

              {category.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  activeTab === item.id ||
                  (item.id === 'MY_WORK' && activeTab === 'LEAD_DETAIL') ||
                  location.pathname === item.path ||
                  (item.path !== '/dashboard' && item.path !== '/' && location.pathname.startsWith(item.path));

                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      navigate(item.path);
                      if (onSelectTab) onSelectTab(item.id);
                      setIsMobileOpen(false);
                    }}
                    title={isCollapsed && !isMobileOpen ? item.label : undefined}
                    className={`relative w-full flex items-center rounded-xl text-xs font-semibold transition-all duration-200 group ${
                      isCollapsed && !isMobileOpen
                        ? 'justify-center p-3'
                        : 'justify-between px-3.5 py-2.5'
                    } ${
                      isActive
                        ? 'bg-gradient-to-r from-emerald-600 to-green-600 text-white shadow-md shadow-emerald-900/30 font-bold'
                        : isDark
                        ? 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                        : 'text-slate-600 hover:bg-slate-100/90 hover:text-slate-900'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon
                        className={`w-4 h-4 flex-shrink-0 transition-transform duration-200 group-hover:scale-110 ${
                          isActive
                            ? 'text-white'
                            : isDark
                            ? 'text-slate-400 group-hover:text-emerald-400'
                            : 'text-slate-500 group-hover:text-emerald-600'
                        }`}
                      />
                      {(!isCollapsed || isMobileOpen) && (
                        <span className="truncate">{item.label}</span>
                      )}
                    </div>

                    {(!isCollapsed || isMobileOpen) && item.badge && (
                      <span
                        className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${
                          isActive
                            ? 'bg-emerald-700/80 text-white'
                            : item.badgeColor || 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}

                    {/* Collapsed Active Glow Bar */}
                    {isCollapsed && !isMobileOpen && isActive && (
                      <span className="absolute left-1 top-2 bottom-2 w-1 bg-white rounded-full"></span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Sidebar Collapse Toggle & User Profile Card */}
        <div
          className={`p-3 border-t space-y-2 ${
            isDark
              ? 'border-slate-800/80 bg-slate-900/80'
              : 'border-slate-200 bg-slate-50/90'
          }`}
        >
          {/* Quick Collapse Button inside Sidebar */}
          <button
            onClick={() => setIsCollapsed((prev) => !prev)}
            className={`hidden lg:flex w-full items-center justify-center gap-2 p-2 rounded-xl text-xs font-semibold border transition-all ${
              isDark
                ? 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:text-white hover:bg-slate-800'
                : 'bg-white border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-100 shadow-xs'
            }`}
            title={isCollapsed ? 'Expand Sidebar Menu' : 'Collapse Sidebar Menu'}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4 text-emerald-500" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4" />
                <span>Collapse Menu</span>
              </>
            )}
          </button>

          {/* User Info & Logout */}
          <div
            className={`flex items-center ${
              isCollapsed && !isMobileOpen ? 'justify-center' : 'justify-between'
            } pt-1`}
          >
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-600 to-green-500 flex items-center justify-center text-white font-bold text-xs flex-shrink-0 shadow-sm">
                {user?.name ? user.name.slice(0, 2).toUpperCase() : 'AD'}
              </div>
              {(!isCollapsed || isMobileOpen) && (
                <div className="overflow-hidden">
                  <div
                    className={`text-xs font-bold truncate ${
                      isDark ? 'text-white' : 'text-slate-900'
                    }`}
                  >
                    {user?.name || 'Super Admin'}
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-emerald-500 font-mono font-semibold">
                    <Shield className="w-2.5 h-2.5" />
                    <span>{user?.role || 'SUPER_ADMIN'}</span>
                  </div>
                </div>
              )}
            </div>

            {(!isCollapsed || isMobileOpen) && (
              <button
                onClick={onLogout}
                className={`p-1.5 rounded-lg transition-colors ${
                  isDark
                    ? 'text-slate-400 hover:text-rose-400 hover:bg-slate-800'
                    : 'text-slate-500 hover:text-rose-600 hover:bg-rose-50'
                }`}
                title="Log out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen bg-grid-pattern relative">
        {/* Top Navbar Header */}
        <header
          className={`h-16 px-4 sm:px-6 lg:px-8 border-b flex items-center justify-between sticky top-0 z-40 backdrop-blur-xl transition-all ${
            isDark
              ? 'bg-slate-900/90 border-slate-800 shadow-lg shadow-black/20'
              : 'bg-white/90 border-slate-200/80 shadow-xs'
          }`}
        >
          {/* Left: Mobile Drawer Trigger + Desktop Menu Pill + Active Tab Breadcrumb */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsMobileOpen(true)}
              className="lg:hidden p-2 rounded-xl text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Open Navigation"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Desktop Menu Toggle Button */}
            <button
              onClick={() => setIsCollapsed((prev) => !prev)}
              className={`hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border transition-all text-xs font-semibold ${
                isDark
                  ? 'bg-slate-800/80 border-slate-700/80 text-slate-300 hover:bg-slate-700 hover:text-white'
                  : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200 hover:text-slate-900'
              }`}
              title={isCollapsed ? 'Expand sidebar menu' : 'Collapse sidebar menu'}
            >
              {isCollapsed ? (
                <>
                  <ChevronRight className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Menu</span>
                </>
              ) : (
                <>
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Collapse</span>
                </>
              )}
            </button>

            {/* Breadcrumb Module Badge */}
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline text-xs text-slate-400 font-medium">Console &gt;</span>
              <span
                className={`text-xs font-bold px-3 py-1 rounded-lg border ${
                  isDark
                    ? 'bg-slate-800/90 border-slate-700 text-emerald-400'
                    : 'bg-emerald-50 border-emerald-200 text-emerald-800'
                }`}
              >
                {currentNav?.label || 'Executive Console'}
              </span>
            </div>
          </div>

          {/* Right: Live Backend Indicator & Light/Dark Theme Switcher */}
          <div className="flex items-center gap-3">
            {/* Live Backend Active Pill */}
            <div
              className={`hidden md:flex items-center gap-2 text-[11px] font-semibold px-3 py-1.5 rounded-full border shadow-2xs ${
                isDark
                  ? 'bg-slate-900/90 border-slate-800 text-slate-300'
                  : 'bg-emerald-50/80 border-emerald-200 text-emerald-800'
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>FastAPI Backend Active (Port 8000)</span>
            </div>

            {/* LIGHT / DARK MODE TOGGLE BUTTON */}
            <button
              onClick={toggleTheme}
              className={`relative flex items-center gap-2 px-3.5 py-1.5 rounded-xl border text-xs font-bold transition-all shadow-sm ${
                isDark
                  ? 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-amber-300 hover:text-amber-200 shadow-slate-900/30'
                  : 'bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-700 hover:text-slate-900 shadow-slate-200/50'
              }`}
              title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {isDark ? (
                <>
                  <Sun className="w-4 h-4 text-amber-400" />
                  <span>Light Mode</span>
                </>
              ) : (
                <>
                  <Moon className="w-4 h-4 text-slate-700" />
                  <span>Dark Mode</span>
                </>
              )}
            </button>
          </div>
        </header>

        {/* Content Body */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AdminLayout;
