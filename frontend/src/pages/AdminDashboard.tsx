import React, { useState, useEffect } from 'react';
import {
  Users,
  CheckSquare,
  Building2,
  Trash2,
  Clock,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  PlusCircle,
  AlertTriangle,
  Sparkles,
  Layers,
  Database,
  Radio,
  Sliders,
  CheckCircle2,
} from 'lucide-react';
import { AdminTab } from '../layouts/AdminLayout';

interface AdminDashboardProps {
  onNavigate: (tab: AdminTab) => void;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ onNavigate }) => {
  const [stats, setStats] = useState({
    staffCount: 0,
    untouchedCount: 0,
    verificationCount: 0,
    recycleCount: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const headers: Record<string, string> = token
          ? { Authorization: `Bearer ${token}` }
          : {};

        const [staffRes, myWorkRes, recycleRes] = await Promise.all([
          fetch('/v1/admin/staff', { headers }).then((r) => (r.ok ? r.json() : [])),
          fetch('/v1/leads/my-work', { headers }).then((r) => (r.ok ? r.json() : [])),
          fetch('/v1/admin/recycle-bin', { headers }).then((r) => (r.ok ? r.json() : [])),
        ]);

        const untouched = Array.isArray(myWorkRes)
          ? myWorkRes.filter((l: any) => l.is_untouched).length
          : 0;

        setStats({
          staffCount: Array.isArray(staffRes) ? staffRes.length : 1,
          untouchedCount: untouched,
          verificationCount: 2, // Active listings in 7-step pipeline
          recycleCount: Array.isArray(recycleRes) ? recycleRes.length : 0,
        });
      } catch (err) {
        console.error('Failed to load dashboard stats', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Welcome Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-r from-emerald-950/80 via-slate-900 to-slate-900 dark:from-slate-900 dark:via-slate-800 dark:to-emerald-950/60 border border-emerald-800/40 dark:border-slate-800 rounded-3xl p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl">
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold mb-3 shadow-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span>Super Admin Command Hub</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight leading-tight">
            Omshiv Buildvision & Propira Overview
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 mt-2 max-w-xl leading-relaxed">
            Enterprise real estate pipeline monitoring, 6-way inbound lead routing, 7-step property verifications, and granular staff role controls.
          </p>
        </div>

        <div className="relative z-10 flex flex-wrap items-center gap-3 flex-shrink-0">
          <button
            onClick={() => onNavigate('STAFF')}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-emerald-900/40 hover:-translate-y-0.5 active:translate-y-0"
          >
            <PlusCircle className="w-4 h-4" />
            <span>+ Add Staff</span>
          </button>
          <button
            onClick={() => onNavigate('MY_WORK')}
            className="flex items-center gap-1.5 px-4 py-2.5 bg-slate-800/90 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-bold border border-slate-700 transition-all hover:-translate-y-0.5 active:translate-y-0"
          >
            <span>Lead Queue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Active Staff */}
        <div
          onClick={() => onNavigate('STAFF')}
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-blue-400 dark:hover:border-blue-500 rounded-2xl p-5 cursor-pointer transition-all duration-200 hover:-translate-y-0.5 shadow-sm hover:shadow-md group"
        >
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Active Staff
            </div>
            <div className="p-2.5 bg-blue-50 dark:bg-blue-950/80 border border-blue-200 dark:border-blue-800/60 rounded-xl text-blue-600 dark:text-blue-400 group-hover:scale-110 transition-transform">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-3xl font-black text-slate-900 dark:text-white">
              {loading ? '...' : stats.staffCount}
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800/80">
              Assigned
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-500" />
            <span>Multiple Roles & Granular Permissions</span>
          </div>
        </div>

        {/* Card 2: Untouched Leads */}
        <div
          onClick={() => onNavigate('MY_WORK')}
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-amber-400 dark:hover:border-amber-500 rounded-2xl p-5 cursor-pointer transition-all duration-200 hover:-translate-y-0.5 shadow-sm hover:shadow-md group"
        >
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Untouched Leads
            </div>
            <div className="p-2.5 bg-amber-50 dark:bg-amber-950/80 border border-amber-200 dark:border-amber-800/60 rounded-xl text-amber-600 dark:text-amber-400 group-hover:scale-110 transition-transform">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-3xl font-black text-amber-500 dark:text-amber-400">
              {loading ? '...' : stats.untouchedCount}
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800/80">
              3h SLA
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1 font-medium">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
            <span>Automated Manager Escalation Watch</span>
          </div>
        </div>

        {/* Card 3: Verifications */}
        <div
          onClick={() => onNavigate('VERIFICATION')}
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-400 dark:hover:border-emerald-500 rounded-2xl p-5 cursor-pointer transition-all duration-200 hover:-translate-y-0.5 shadow-sm hover:shadow-md group"
        >
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Verifications
            </div>
            <div className="p-2.5 bg-emerald-50 dark:bg-green-950/80 border border-emerald-200 dark:border-green-800/60 rounded-xl text-emerald-600 dark:text-emerald-400 group-hover:scale-110 transition-transform">
              <Building2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-3xl font-black text-emerald-600 dark:text-emerald-400">
              {loading ? '...' : stats.verificationCount}
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/80">
              7 Steps
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1 font-medium">
            <CheckSquare className="w-3.5 h-3.5 text-emerald-500" />
            <span>Telephonic, Documents & Physical Go-Live</span>
          </div>
        </div>

        {/* Card 4: Recycle Bin */}
        <div
          onClick={() => onNavigate('RECYCLE_BIN')}
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-rose-400 dark:hover:border-rose-500 rounded-2xl p-5 cursor-pointer transition-all duration-200 hover:-translate-y-0.5 shadow-sm hover:shadow-md group"
        >
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Recycled Listings
            </div>
            <div className="p-2.5 bg-rose-50 dark:bg-rose-950/80 border border-rose-200 dark:border-rose-800/60 rounded-xl text-rose-600 dark:text-rose-400 group-hover:scale-110 transition-transform">
              <Trash2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <div className="text-3xl font-black text-rose-500 dark:text-rose-400">
              {loading ? '...' : stats.recycleCount}
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/80">
              Safeguarded
            </span>
          </div>
          <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1 font-medium">
            <TrendingUp className="w-3.5 h-3.5 text-rose-500" />
            <span>1-Click Restore / Permanent Purge</span>
          </div>
        </div>
      </div>

      {/* Visual Pipeline Health Section */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-500" />
              <span>Inbound Leads & Verification Pipeline Health</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Automated routing distribution across 6 lead acquisition funnels.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/80 w-fit">
            System Normal (Zero Escalation)
          </span>
        </div>

        {/* Progress Bar Distribution */}
        <div className="space-y-3">
          <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden flex">
            <div className="bg-emerald-500 h-full w-[45%]" title="Active Telephonic: 45%"></div>
            <div className="bg-blue-500 h-full w-[25%]" title="Site Visit Scheduled: 25%"></div>
            <div className="bg-amber-500 h-full w-[18%]" title="Fresh Intake: 18%"></div>
            <div className="bg-purple-500 h-full w-[12%]" title="Legal Document Check: 12%"></div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-1">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span className="text-slate-600 dark:text-slate-400 font-medium">In Discussion (45%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
              <span className="text-slate-600 dark:text-slate-400 font-medium">Site Visit (25%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
              <span className="text-slate-600 dark:text-slate-400 font-medium">Fresh Intake (18%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span>
              <span className="text-slate-600 dark:text-slate-400 font-medium">Legal Check (12%)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Control Panels Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Core Administrative Controls */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            Administrative Controls
          </h3>

          <div className="space-y-3">
            <div
              onClick={() => onNavigate('STAFF')}
              className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 flex items-center justify-between cursor-pointer transition-all duration-150 hover:bg-slate-100 dark:hover:bg-slate-800/60 group"
            >
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                  Staff Roster & Multiple Roles
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Assign Super Admin, Sales Manager, Telecaller, or Verification Officer roles.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-500 transition-colors" />
            </div>

            <div
              onClick={() => onNavigate('DYNAMIC_MASTERS')}
              className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 flex items-center justify-between cursor-pointer transition-all duration-150 hover:bg-slate-100 dark:hover:bg-slate-800/60 group"
            >
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                  Dynamic Property Master Tables
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Add dynamic options (BHKs, Facing, Furnishing, Agricultural Bigha) with zero code changes.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-500 transition-colors" />
            </div>

            <div
              onClick={() => onNavigate('SETTINGS')}
              className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 flex items-center justify-between cursor-pointer transition-all duration-150 hover:bg-slate-100 dark:hover:bg-slate-800/60 group"
            >
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                  92 Dynamic System Settings & Audit Logs
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Live SLAs, WhatsApp / SMS credentials, quiet hours (21:00-09:00), and immutable audit trail.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-500 transition-colors" />
            </div>
          </div>
        </div>

        {/* Real Estate Operations Quick Shortcuts */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-500" />
            Propira Verification & Lead Engines
          </h3>

          <div className="space-y-3">
            <div
              onClick={() => onNavigate('MY_WORK')}
              className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 flex items-center justify-between cursor-pointer transition-all duration-150 hover:bg-slate-100 dark:hover:bg-slate-800/60 group"
            >
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  Prioritized Lead Queue
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Overdue follow-ups, untouched intake leads, today&apos;s appointments, and temperature sorting.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors" />
            </div>

            <div
              onClick={() => onNavigate('VERIFICATION')}
              className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 flex items-center justify-between cursor-pointer transition-all duration-150 hover:bg-slate-100 dark:hover:bg-slate-800/60 group"
            >
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  7-Step Property Verification Hub
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Manager approvals, document checks, and automated 90/30-day listing expiry timers.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors" />
            </div>

            <div
              onClick={() => onNavigate('RECYCLE_BIN')}
              className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 flex items-center justify-between cursor-pointer transition-all duration-150 hover:bg-slate-100 dark:hover:bg-slate-800/60 group"
            >
              <div>
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-rose-600 dark:group-hover:text-rose-400 transition-colors">
                  Recycle Bin & Owner Ad Requests
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Single-pending owner deletion requests and 1-click restore for accidental removals.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-rose-500 transition-colors" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
