import React, { useState, useEffect, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Gauge,
  FileText,
  Rocket,
  Filter,
  Building2,
  Home,
  Users,
  Radio,
  UserCheck,
  Layers,
  Handshake,
  Settings,
  LogOut,
  Shield,
  Sun,
  Moon,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Circle,
  Bot,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import alwarMapLogo from '../image/logo1.png';

export type AdminTab =
  | 'DASHBOARD'
  | 'WEBSITE_FORMS'
  | 'LEADS'
  | 'OPPORTUNITIES'
  | 'PROPERTY'
  | 'HOMEPAGE'
  | 'STAFF'
  | 'BLOG'
  | 'PROPIRA_USERS'
  | 'PAGES'
  | 'FRANCHISE'
  | 'SETTINGS'
  | 'DYNAMIC_MASTERS'
  | 'VERIFICATION'
  | 'RECYCLE_BIN'
  | 'MY_WORK'
  | 'LEAD_DETAIL'
  | 'AI_AGENTS'
  | 'AI_APPROVALS';

export interface SubMenuItem {
  label: string;
  path: string;
}

export interface NavItem {
  id: string;
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  badgeColor?: string;
  subItems?: SubMenuItem[];
}

interface AdminLayoutProps {
  user: any;
  activeTab?: AdminTab;
  onSelectTab?: (tab: AdminTab) => void;
  onLogout: () => void;
  children?: React.ReactNode;
}

export const AdminLayout: React.FC<AdminLayoutProps> = ({
  user,
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

  // Submenu accordion state
  const [openSubmenus, setOpenSubmenus] = useState<Record<string, boolean>>({});

  useEffect(() => {
    localStorage.setItem('omshiv_sidebar_collapsed', String(isCollapsed));
  }, [isCollapsed]);

  useEffect(() => {
    if (location.pathname.startsWith('/website-forms')) {
      setOpenSubmenus((prev) =>
        prev.WEBSITE_FORMS === true ? prev : { ...prev, WEBSITE_FORMS: true }
      );
    }
    if (location.pathname.startsWith('/opportunities')) {
      setOpenSubmenus((prev) =>
        prev.OPPORTUNITIES === true ? prev : { ...prev, OPPORTUNITIES: true }
      );
    }
  }, [location.pathname]);

  // 11 Core Modules Matching Screenshot 3
  const navItems: NavItem[] = useMemo(() => [
    {
      id: 'DASHBOARD',
      path: '/dashboard',
      label: 'Dashboard',
      icon: Gauge,
    },
    {
      id: 'WEBSITE_FORMS',
      path: '/website-forms',
      label: 'Website Forms',
      icon: FileText,
      subItems: [
        { label: 'Request A Callback', path: '/website-forms?tab=callbacks' },
        { label: 'Report A Problem', path: '/website-forms?tab=problems' },
      ],
    },
    {
      id: 'LEADS',
      path: '/leads',
      label: 'Leads',
      icon: Rocket,
      badge: 'Active',
      badgeColor: 'bg-[#F04B42]/10 text-[#F04B42] border border-[#F04B42]/25',
      subItems: [
        { label: 'Buy', path: '/leads?type=buy' },
        { label: 'Rent', path: '/leads?type=rent' },
        { label: 'PG', path: '/leads?type=pg' },
        { label: 'Create Lead', path: '/leads?action=create' },
        { label: 'Import Lead', path: '/leads?action=import' },
      ],
    },
    {
      id: 'OPPORTUNITIES',
      path: '/opportunities',
      label: 'Opportunities',
      icon: Filter,
      subItems: [
        { label: 'New Opportunity', path: '/opportunities?tab=new' },
        { label: 'Today Opportunity', path: '/opportunities?tab=today' },
        { label: 'Open Opportunity', path: '/opportunities?tab=open' },
        { label: 'Missing Opportunity', path: '/opportunities?tab=missing' },
        { label: 'In-Progress', path: '/opportunities?tab=in_progress' },
        { label: 'Closed', path: '/opportunities?tab=closed' },
        { label: 'All Opportunity', path: '/opportunities?tab=all' },
        { label: 'Create Opportunity', path: '/opportunities?action=create' },
      ],
    },
    {
      id: 'PROPERTY',
      path: '/properties',
      label: 'Property',
      icon: Building2,
      subItems: [
        { label: 'New & Assign Properties', path: '/properties?tab=new_assign' },
        { label: 'Verify & Live Properties', path: '/properties?tab=verify_live' },
        { label: 'Verification Done', path: '/properties?tab=verification_done' },
        { label: 'Expired Properties', path: '/properties?tab=expired' },
        { label: 'Delete Property', path: '/properties?tab=deleted' },
        { label: 'Sell Property', path: '/properties?tab=sold' },
        { label: 'Request Live Property', path: '/properties?tab=request_live' },
      ],
    },
    // {
    //   id: 'HOMEPAGE',
    //   path: '/homepage',
    //   label: 'Homepage',
    //   icon: Home,
    //   subItems: [
    //     { label: 'Hero Banners', path: '/homepage?tab=banners' },
    //     { label: 'Featured Projects', path: '/homepage?tab=featured' },
    //   ],
    // },
    {
      id: 'STAFF',
      path: '/staff',
      label: 'Panel User',
      icon: Users,
      badge: 'Admin',
      badgeColor: 'bg-blue-500/10 text-blue-500 border border-blue-500/20',
      subItems: [
        { label: 'Staff Directory', path: '/staff?tab=roster' },
        { label: 'Dynamic Roles & CRUD', path: '/staff?tab=roles' },
        { label: 'Permissions Matrix', path: '/staff?tab=permissions' },
      ],
    },
    {
      id: 'BLOG',
      path: '/blogs',
      label: 'Blog',
      icon: Radio,
      subItems: [
        { label: 'All Articles', path: '/blogs' },
        { label: 'Market Insights', path: '/blogs?cat=reports' },
      ],
    },
    {
      id: 'USERS',
      path: '/users',
      label: 'Users',
      icon: UserCheck,
      subItems: [
        { label: 'Registered Buyers', path: '/users?type=buyers' },
        { label: 'Property Owners & Sellers', path: '/users?type=owners' },
      ],
    },
    // {
    //   id: 'PAGES',
    //   path: '/pages',
    //   label: 'Pages',
    //   icon: Layers,
    //   subItems: [
    //     { label: 'CMS Static Pages', path: '/pages' },
    //     { label: 'Legal & Policies', path: '/pages?type=legal' },
    //   ],
    // },
    {
      id: 'FRANCHISE',
      path: '/franchise',
      label: 'Franchise',
      icon: Handshake,
      subItems: [
        { label: 'Channel Partners', path: '/franchise?type=partners' },
        { label: 'Franchise Outlets', path: '/franchise?type=outlets' },
      ],
    },
    {
      id: 'AI_AGENTS',
      path: '/ai-agents',
      label: 'AI Agents',
      icon: Bot,
      badge: '13 AI',
      badgeColor: 'bg-[#291BB0]/10 text-[#291BB0] dark:text-indigo-300 border border-[#291BB0]/25',
      subItems: [
        { label: 'All Agents Control', path: '/ai-agents' },
        { label: 'HITL Approvals Queue', path: '/ai-approvals' },
      ],
    },
    {
      id: 'SETTINGS',
      path: '/settings',
      label: 'Settings & Schema',
      icon: Settings,
      subItems: [
        { label: 'System Settings', path: '/settings' },
        { label: 'Dynamic Property Masters', path: '/masters' },
      ],
    },
  ], []);

  // Determine active item from current location
  const isItemActive = (item: NavItem) => {
    const currentBase = location.pathname;
    if (item.path === '/dashboard') {
      return currentBase === '/' || currentBase === '/dashboard';
    }
    if (currentBase === item.path) return true;
    if (item.subItems?.some((sub) => currentBase.startsWith(sub.path.split('?')[0]))) {
      return true;
    }
    return currentBase.startsWith(item.path);
  };

  const currentNav = useMemo(() => {
    return (
      navItems.find((n) => isItemActive(n)) ||
      navItems[0]
    );
  }, [location.pathname, navItems]);

  const toggleSubmenu = (itemId: string) => {
    setOpenSubmenus((prev) => ({
      ...prev,
      [itemId]: !prev[itemId],
    }));
  };

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
            ? 'bg-slate-900/98 border-slate-800 backdrop-blur-md shadow-2xl shadow-black/40'
            : 'bg-white border-slate-200 shadow-xl shadow-slate-200/50'
        } ${isCollapsed ? 'lg:w-20' : 'lg:w-64'} ${
          isMobileOpen ? 'translate-x-0 w-64' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div
          className={`h-20 px-3 border-b flex items-center justify-between ${
            isDark ? 'border-slate-800' : 'border-slate-200'
          }`}
        >
          <div
            onClick={() => navigate('/dashboard')}
            className="flex items-center justify-center overflow-hidden cursor-pointer w-full"
          >
            {(!isCollapsed || isMobileOpen) ? (
              <div className="w-full bg-white rounded-2xl px-2 py-1 border border-slate-200/90 shadow-sm flex items-center justify-center overflow-hidden">
                <img
                  src={alwarMapLogo}
                  alt="AlwarMap.com"
                  className="h-14 w-full object-contain scale-125"
                />
              </div>
            ) : (
              <div className="relative mx-auto w-10 h-10 rounded-xl bg-[#291BB0] border-2 border-[#F04B42] flex items-center justify-center shadow-md shadow-[#291BB0]/30">
                <span className="text-white font-display font-black text-base tracking-tight">
                  A<span className="text-[#F04B42]">.</span>
                </span>
              </div>
            )}
          </div>

          <button
            onClick={() => setIsMobileOpen(false)}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 11-Module Sidebar Navigation List */}
        <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto overflow-x-hidden custom-scrollbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isItemActive(item);
            const hasSub = item.subItems && item.subItems.length > 0;
            const isSubOpen = openSubmenus[item.id] ?? active;

            return (
              <div key={item.id} className="space-y-0.5">
                <button
                  type="button"
                  onClick={() => {
                    if (hasSub && (!isCollapsed || isMobileOpen)) {
                      toggleSubmenu(item.id);
                    } else {
                      navigate(item.path);
                      setIsMobileOpen(false);
                    }
                  }}
                  title={isCollapsed && !isMobileOpen ? item.label : undefined}
                  className={`relative w-full flex items-center rounded-xl text-xs font-semibold transition-all duration-200 group ${
                    isCollapsed && !isMobileOpen
                      ? 'justify-center p-3'
                      : 'justify-between px-3.5 py-2.5'
                  } ${
                    active
                      ? 'bg-[#291BB0]/10 dark:bg-[#291BB0]/25 text-[#291BB0] dark:text-indigo-300 border-l-4 border-[#F04B42] font-bold shadow-xs'
                      : isDark
                      ? 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon
                      className={`w-4 h-4 flex-shrink-0 transition-transform duration-200 group-hover:scale-110 ${
                        active
                          ? 'text-[#F04B42]'
                          : isDark
                          ? 'text-slate-400 group-hover:text-indigo-300'
                          : 'text-slate-500 group-hover:text-[#291BB0]'
                      }`}
                    />
                    {(!isCollapsed || isMobileOpen) && (
                      <span className="truncate">{item.label}</span>
                    )}
                  </div>

                  {(!isCollapsed || isMobileOpen) && (
                    <div className="flex items-center gap-1.5">
                      {item.badge && (
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${
                            active
                              ? 'bg-[#F04B42] text-white'
                              : item.badgeColor || 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                      {hasSub && (
                        <span className="text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200 transition-transform">
                          {isSubOpen ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                          )}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Collapsed Glow Accent */}
                  {isCollapsed && !isMobileOpen && active && (
                    <span className="absolute left-1 top-2 bottom-2 w-1 bg-[#F04B42] rounded-full"></span>
                  )}
                </button>

                {/* Submenu Drawer */}
                {hasSub && isSubOpen && (!isCollapsed || isMobileOpen) && (
                  <div className="pl-7 pr-2 py-1 space-y-1 animate-slide-down border-l border-slate-200 dark:border-slate-800 ml-4 my-1">
                    {item.subItems!.map((sub) => {
                      const [subBase, subQuery] = sub.path.split('?');
                      let isSubActive = false;
                      if (location.pathname === subBase) {
                        if (subQuery) {
                          const subParams = new URLSearchParams(subQuery);
                          const curParams = new URLSearchParams(location.search);
                          const allMatch = Array.from(subParams.entries()).every(
                            ([k, v]) => curParams.get(k) === v
                          );
                          const isDefaultWebsiteFormsCallback =
                            subBase === '/website-forms' &&
                            subParams.get('tab') === 'callbacks' &&
                            !curParams.get('tab');
                          isSubActive = allMatch || isDefaultWebsiteFormsCallback;
                        } else {
                          isSubActive = !location.search;
                        }
                      }
                      return (
                        <button
                          key={sub.path}
                          type="button"
                          onClick={() => {
                            navigate(sub.path);
                            setIsMobileOpen(false);
                          }}
                          className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center justify-between group/sub ${
                            isSubActive
                              ? 'text-[#291BB0] dark:text-indigo-300 font-bold bg-[#291BB0]/10 dark:bg-[#291BB0]/25'
                              : 'text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/50'
                          }`}
                        >
                          <div className="flex items-center gap-2 truncate">
                            <Circle className={`w-3 h-3 flex-shrink-0 stroke-[2.5] ${isSubActive ? 'text-[#F04B42]' : 'text-slate-400 group-hover/sub:text-slate-200'}`} />
                            <span className="truncate">{sub.label}</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            {(sub.label.includes('Delete Property') || sub.label.includes('Sell Property')) && (
                              <ChevronRight className="w-3 h-3 text-slate-400/70 group-hover/sub:text-slate-300" />
                            )}
                            {isSubActive && <span className="w-1.5 h-1.5 rounded-full bg-[#F04B42]"></span>}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Sidebar Collapse Toggle & User Profile Card */}
        <div
          className={`p-3 border-t space-y-2 ${
            isDark ? 'border-slate-800 bg-slate-900/80' : 'border-slate-200 bg-slate-50/90'
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
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#291BB0] to-[#F04B42] flex items-center justify-center text-white font-bold text-xs flex-shrink-0 shadow-sm">
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
                  <div className="flex items-center gap-1 text-[10px] text-[#3b2cc9] dark:text-indigo-400 font-mono font-semibold">
                    <Shield className="w-2.5 h-2.5 text-[#F04B42]" />
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
              <span className="hidden sm:inline text-xs text-slate-400 font-medium">AlwarMap &gt;</span>
              <span
                className={`text-xs font-bold px-3 py-1 rounded-lg border ${
                  isDark
                    ? 'bg-[#291BB0]/20 border-[#291BB0]/40 text-indigo-300'
                    : 'bg-[#eef0ff] border-[#dce0ff] text-[#291BB0]'
                }`}
              >
                {currentNav.label}
              </span>
            </div>
          </div>

          {/* Right: Live Backend Indicator & Light/Dark Theme Switcher */}
          <div className="flex items-center gap-3">
            {/* Live Backend Active Pill */}
            

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
