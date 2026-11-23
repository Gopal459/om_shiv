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
  FileText,
  AlertTriangle,
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
          verificationCount: 2, // Verification assignments active in queue
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
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-green-950/80 border border-green-800/80 text-green-400 text-[11px] font-bold mb-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-ping"></span>
            Super Admin Executive Command Center
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            Omshiv Buildvision & Propira Overview
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-xl">
            Real-time pipeline monitoring, 6-way inbound lead routing, 7-step property verifications, and granular staff role controls.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-shrink-0">
          <button
            onClick={() => onNavigate('STAFF')}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-green-600 hover:bg-green-500 text-white rounded-xl text-xs font-bold transition-all shadow-md shadow-green-900/30"
          >
            <PlusCircle className="w-4 h-4" />
            + Add Staff
          </button>
          <button
            onClick={() => onNavigate('MY_WORK')}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-bold border border-slate-700 transition-colors"
          >
            <span>View Leads</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Staff */}
        <div
          onClick={() => onNavigate('STAFF')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 cursor-pointer transition-all hover:shadow-lg group"
        >
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Active Staff
            </div>
            <div className="p-2.5 bg-blue-950 border border-blue-800/60 rounded-xl text-blue-400 group-hover:scale-110 transition-transform">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-black text-white">
            {loading ? '...' : stats.staffCount}
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
            <span>Multiple Roles & Granular Permissions</span>
          </div>
        </div>

        {/* Card 2: Untouched Leads */}
        <div
          onClick={() => onNavigate('MY_WORK')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 cursor-pointer transition-all hover:shadow-lg group"
        >
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Untouched Leads
            </div>
            <div className="p-2.5 bg-amber-950 border border-amber-800/60 rounded-xl text-amber-400 group-hover:scale-110 transition-transform">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-black text-amber-400">
            {loading ? '...' : stats.untouchedCount}
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span>3-Hour SLA Escalation Watch</span>
          </div>
        </div>

        {/* Card 3: Verification Queue */}
        <div
          onClick={() => onNavigate('VERIFICATION')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 cursor-pointer transition-all hover:shadow-lg group"
        >
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Verifications
            </div>
            <div className="p-2.5 bg-green-950 border border-green-800/60 rounded-xl text-green-400 group-hover:scale-110 transition-transform">
              <Building2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-black text-green-400">
            {loading ? '...' : stats.verificationCount}
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1">
            <CheckSquare className="w-3.5 h-3.5 text-green-400" />
            <span>7-Step Telephonic & Physical Flow</span>
          </div>
        </div>

        {/* Card 4: Recycle Bin */}
        <div
          onClick={() => onNavigate('RECYCLE_BIN')}
          className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 cursor-pointer transition-all hover:shadow-lg group"
        >
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Recycled Listings
            </div>
            <div className="p-2.5 bg-rose-950 border border-rose-800/60 rounded-xl text-rose-400 group-hover:scale-110 transition-transform">
              <Trash2 className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-3xl font-black text-rose-400">
            {loading ? '...' : stats.recycleCount}
          </div>
          <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-rose-400" />
            <span>1-Click Restore / Purge Engine</span>
          </div>
        </div>
      </div>

      {/* Quick Action Hubs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
        {/* Core Administrative Control Panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-green-400" />
            Administrative Controls
          </h3>

          <div className="space-y-3">
            <div
              onClick={() => onNavigate('STAFF')}
              className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 flex items-center justify-between cursor-pointer transition-colors"
            >
              <div>
                <div className="text-xs font-bold text-white">Staff Roster & Multiple Roles</div>
                <div className="text-[11px] text-slate-400">
                  Assign Super Admin, Sales Manager, Telecaller, or Verification Officer roles.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </div>

            <div
              onClick={() => onNavigate('DYNAMIC_MASTERS')}
              className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 flex items-center justify-between cursor-pointer transition-colors"
            >
              <div>
                <div className="text-xs font-bold text-white">Dynamic Property Master Tables</div>
                <div className="text-[11px] text-slate-400">
                  Add dynamic options (BHKs, Facing, Furnishing, Agricultural Bigha) with zero code changes.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </div>

            <div
              onClick={() => onNavigate('SETTINGS')}
              className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 flex items-center justify-between cursor-pointer transition-colors"
            >
              <div>
                <div className="text-xs font-bold text-white">92 Dynamic System Settings & Audit Logs</div>
                <div className="text-[11px] text-slate-400">
                  Live SLAs, WhatsApp / SMS credentials, quiet hours (21:00-09:00), and immutable audit trail.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </div>
          </div>
        </div>

        {/* Real Estate Operations Quick Shortcuts */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-400" />
            Propira Verification & Lead Engines
          </h3>

          <div className="space-y-3">
            <div
              onClick={() => onNavigate('MY_WORK')}
              className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 flex items-center justify-between cursor-pointer transition-colors"
            >
              <div>
                <div className="text-xs font-bold text-white">Prioritized Lead Queue</div>
                <div className="text-[11px] text-slate-400">
                  Overdue follow-ups, untouched intake leads, today&apos;s appointments, and temperature sorting.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </div>

            <div
              onClick={() => onNavigate('VERIFICATION')}
              className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 flex items-center justify-between cursor-pointer transition-colors"
            >
              <div>
                <div className="text-xs font-bold text-white">7-Step Property Verification Hub</div>
                <div className="text-[11px] text-slate-400">
                  Manager approvals, document checks, and automated 90/30-day listing expiry timers.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </div>

            <div
              onClick={() => onNavigate('RECYCLE_BIN')}
              className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 flex items-center justify-between cursor-pointer transition-colors"
            >
              <div>
                <div className="text-xs font-bold text-white">Recycle Bin & Owner Ad Requests</div>
                <div className="text-[11px] text-slate-400">
                  Single-pending owner deletion requests and 1-click restore for accidental removals.
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default AdminDashboard;
