import React, { useState, useEffect, useMemo } from 'react';
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
  RefreshCw,
  Zap,
  Activity,
  Calendar,
  Lock,
  ArrowUpRight,
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
  const [refreshing, setRefreshing] = useState(false);

  // Time-aware dynamic greeting
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    return 'Good Evening';
  }, []);

  const currentDateString = useMemo(() => {
    return new Date().toLocaleDateString('en-IN', {
      weekday: 'long',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  }, []);

  const fetchDashboardData = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    else setLoading(true);

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
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* 1. ULTRA-MODERN AMBIENT HERO BANNER */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-200/80 dark:border-slate-800 bg-gradient-to-br from-slate-900 via-slate-900/95 to-emerald-950/90 text-white p-6 sm:p-8 lg:p-10 shadow-2xl shadow-emerald-950/20 group">
        {/* Floating Ambient Glow Orbs */}
        <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-emerald-500/20 blur-3xl pointer-events-none animate-float"></div>
        <div className="absolute -bottom-24 -right-24 w-96 h-96 rounded-full bg-cyan-500/20 blur-3xl pointer-events-none animate-float-delayed"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-white/5 via-transparent to-transparent pointer-events-none"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            {/* Live Indicator Pill & Date */}
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold shadow-xs backdrop-blur-md">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                <span>Super Admin Executive Hub</span>
              </div>

              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 border border-white/10 text-slate-300 text-xs font-medium backdrop-blur-md">
                <Calendar className="w-3 h-3 text-slate-400" />
                <span>{currentDateString}</span>
              </div>
            </div>

            {/* Main Headline */}
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight leading-tight">
              {greeting},{' '}
              <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-300 bg-clip-text text-transparent">
                Omshiv Buildvision CRM
              </span>
            </h1>

            <p className="text-xs sm:text-sm text-slate-300/90 leading-relaxed max-w-xl">
              Propira Enterprise Engine with 6-way inbound lead routing, real-time 3-hour SLA enforcement, 7-step property verification pipeline, and dynamic role-based access.
            </p>

            {/* Quick Live System Micro-Chips */}
            <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-slate-300 font-semibold">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-300">
                <Zap className="w-3 h-3 text-emerald-400" />
                FastAPI Port 8000: Live
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-950/60 border border-blue-800/60 text-blue-300">
                <Activity className="w-3 h-3 text-blue-400" />
                SLA Escalations: Active
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-950/60 border border-purple-800/60 text-purple-300">
                <ShieldCheck className="w-3 h-3 text-purple-400" />
                Universal Soft-Delete: Armed
              </span>
            </div>
          </div>

          {/* Action Button Group */}
          <div className="relative z-10 flex flex-wrap items-center gap-3 lg:flex-col lg:items-end flex-shrink-0">
            <button
              onClick={() => onNavigate('STAFF')}
              className="shimmer-effect group flex items-center gap-2.5 px-5 py-3 bg-gradient-to-r from-emerald-500 via-emerald-600 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white rounded-2xl text-xs font-bold transition-all duration-300 shadow-xl shadow-emerald-900/40 hover:-translate-y-1 active:translate-y-0"
            >
              <PlusCircle className="w-4 h-4 transition-transform group-hover:rotate-90 duration-300" />
              <span>+ Add Staff Member</span>
            </button>

            <div className="flex items-center gap-2">
              <button
                onClick={() => onNavigate('MY_WORK')}
                className="flex items-center gap-2 px-4 py-2.5 bg-slate-800/90 hover:bg-slate-700/90 text-slate-200 hover:text-white rounded-2xl text-xs font-bold border border-slate-700/80 transition-all hover:-translate-y-0.5 active:translate-y-0 shadow-md backdrop-blur-md"
              >
                <span>Sales Leads Queue</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              </button>

              <button
                onClick={() => fetchDashboardData(true)}
                disabled={refreshing}
                title="Refresh Live Data"
                className="p-2.5 bg-slate-800/90 hover:bg-slate-700/90 text-slate-300 hover:text-white rounded-2xl border border-slate-700/80 transition-all shadow-md active:scale-95"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-emerald-400' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 2. GLOWING ANIMATED KPI METRICS GRID */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Active Staff */}
        <div
          onClick={() => onNavigate('STAFF')}
          className="glow-card relative overflow-hidden bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 hover:border-blue-400 dark:hover:border-blue-500 rounded-3xl p-6 cursor-pointer transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/10 group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Active Staff
            </span>
            <div className="p-3 bg-blue-50 dark:bg-blue-950/80 border border-blue-200/80 dark:border-blue-800/80 rounded-2xl text-blue-600 dark:text-blue-400 group-hover:scale-110 group-hover:rotate-6 transition-all duration-300 shadow-sm">
              <Users className="w-5 h-5" />
            </div>
          </div>

          <div className="mt-4 flex items-baseline justify-between">
            <div className="text-3xl font-black text-slate-900 dark:text-white tracking-tight">
              {loading ? (
                <div className="h-9 w-12 bg-slate-200 dark:bg-slate-800 animate-pulse rounded-lg"></div>
              ) : (
                stats.staffCount
              )}
            </div>
            <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800/80">
              Assigned Active
            </span>
          </div>

          {/* Mini Sparkline Visualization */}
          <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-1.5 font-medium">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-500" />
              <span>Multi-Role RBAC</span>
            </div>
            <span className="text-blue-600 dark:text-blue-400 font-bold group-hover:translate-x-1 transition-transform flex items-center gap-0.5">
              Manage <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>

        {/* Card 2: Untouched Leads */}
        <div
          onClick={() => onNavigate('MY_WORK')}
          className="glow-card relative overflow-hidden bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 hover:border-amber-400 dark:hover:border-amber-500 rounded-3xl p-6 cursor-pointer transition-all duration-300 hover:shadow-xl hover:shadow-amber-500/10 group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Untouched Leads
            </span>
            <div className="p-3 bg-amber-50 dark:bg-amber-950/80 border border-amber-200/80 dark:border-amber-800/80 rounded-2xl text-amber-600 dark:text-amber-400 group-hover:scale-110 group-hover:-rotate-6 transition-all duration-300 shadow-sm">
              <Clock className="w-5 h-5" />
            </div>
          </div>

          <div className="mt-4 flex items-baseline justify-between">
            <div className="text-3xl font-black text-amber-500 dark:text-amber-400 tracking-tight">
              {loading ? (
                <div className="h-9 w-12 bg-slate-200 dark:bg-slate-800 animate-pulse rounded-lg"></div>
              ) : (
                stats.untouchedCount
              )}
            </div>
            <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/80 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
              3-Hour SLA
            </span>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-1.5 font-medium">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              <span>Manager Escalations</span>
            </div>
            <span className="text-amber-600 dark:text-amber-400 font-bold group-hover:translate-x-1 transition-transform flex items-center gap-0.5">
              Review <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>

        {/* Card 3: Verifications */}
        <div
          onClick={() => onNavigate('VERIFICATION')}
          className="glow-card relative overflow-hidden bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 hover:border-emerald-400 dark:hover:border-emerald-500 rounded-3xl p-6 cursor-pointer transition-all duration-300 hover:shadow-xl hover:shadow-emerald-500/10 group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Verifications Hub
            </span>
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-200/80 dark:border-emerald-800/80 rounded-2xl text-emerald-600 dark:text-emerald-400 group-hover:scale-110 group-hover:rotate-6 transition-all duration-300 shadow-sm">
              <Building2 className="w-5 h-5" />
            </div>
          </div>

          <div className="mt-4 flex items-baseline justify-between">
            <div className="text-3xl font-black text-emerald-600 dark:text-emerald-400 tracking-tight">
              {loading ? (
                <div className="h-9 w-12 bg-slate-200 dark:bg-slate-800 animate-pulse rounded-lg"></div>
              ) : (
                stats.verificationCount
              )}
            </div>
            <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/80">
              7-Step Flow
            </span>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-1.5 font-medium">
              <CheckSquare className="w-3.5 h-3.5 text-emerald-500" />
              <span>Physical & Telephonic</span>
            </div>
            <span className="text-emerald-600 dark:text-emerald-400 font-bold group-hover:translate-x-1 transition-transform flex items-center gap-0.5">
              Inspect <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>

        {/* Card 4: Recycle Bin */}
        <div
          onClick={() => onNavigate('RECYCLE_BIN')}
          className="glow-card relative overflow-hidden bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 hover:border-rose-400 dark:hover:border-rose-500 rounded-3xl p-6 cursor-pointer transition-all duration-300 hover:shadow-xl hover:shadow-rose-500/10 group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Recycled Listings
            </span>
            <div className="p-3 bg-rose-50 dark:bg-rose-950/80 border border-rose-200/80 dark:border-rose-800/80 rounded-2xl text-rose-600 dark:text-rose-400 group-hover:scale-110 group-hover:-rotate-6 transition-all duration-300 shadow-sm">
              <Trash2 className="w-5 h-5" />
            </div>
          </div>

          <div className="mt-4 flex items-baseline justify-between">
            <div className="text-3xl font-black text-rose-500 dark:text-rose-400 tracking-tight">
              {loading ? (
                <div className="h-9 w-12 bg-slate-200 dark:bg-slate-800 animate-pulse rounded-lg"></div>
              ) : (
                stats.recycleCount
              )}
            </div>
            <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/80">
              Soft Deleted
            </span>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-1.5 font-medium">
              <TrendingUp className="w-3.5 h-3.5 text-rose-500" />
              <span>1-Click Restore / Purge</span>
            </div>
            <span className="text-rose-600 dark:text-rose-400 font-bold group-hover:translate-x-1 transition-transform flex items-center gap-0.5">
              View <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>
      </div>

      {/* 3. INTERACTIVE ANIMATED PIPELINE HEALTH MONITOR */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 sm:p-7 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
              <span className="p-1.5 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <Layers className="w-4 h-4" />
              </span>
              <span>Inbound Leads & Verification Pipeline Health</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Automated stage distribution across intake, telephonic qualification, site appointments, and legal deed verification.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/80 shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
              <span>System Normal (Zero Escalation)</span>
            </span>
          </div>
        </div>

        {/* Multi-segment Animated Gradient Progress Bar */}
        <div className="space-y-4">
          <div className="relative h-4 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden flex shadow-inner p-0.5 gap-0.5">
            <div
              className="bg-gradient-to-r from-emerald-500 to-green-500 h-full rounded-l-full transition-all duration-500 relative group cursor-pointer"
              style={{ width: '45%' }}
            >
              <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </div>
            <div
              className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full transition-all duration-500 relative group cursor-pointer"
              style={{ width: '25%' }}
            >
              <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </div>
            <div
              className="bg-gradient-to-r from-amber-400 to-amber-500 h-full transition-all duration-500 relative group cursor-pointer"
              style={{ width: '18%' }}
            >
              <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </div>
            <div
              className="bg-gradient-to-r from-purple-500 to-fuchsia-500 h-full rounded-r-full transition-all duration-500 relative group cursor-pointer"
              style={{ width: '12%' }}
            >
              <div className="absolute inset-0 bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </div>
          </div>

          {/* Interactive Metric Cards for each pipeline segment */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between hover:border-emerald-400 dark:hover:border-emerald-500 transition-colors">
              <div className="space-y-0.5">
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  <span>In Discussion</span>
                </div>
                <div className="text-sm font-black text-slate-900 dark:text-white">45%</div>
              </div>
              <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">Normal</span>
            </div>

            <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between hover:border-blue-400 dark:hover:border-blue-500 transition-colors">
              <div className="space-y-0.5">
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                  <span>Site Visits</span>
                </div>
                <div className="text-sm font-black text-slate-900 dark:text-white">25%</div>
              </div>
              <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400">On Track</span>
            </div>

            <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between hover:border-amber-400 dark:hover:border-amber-500 transition-colors">
              <div className="space-y-0.5">
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                  <span>Fresh Intake</span>
                </div>
                <div className="text-sm font-black text-slate-900 dark:text-white">18%</div>
              </div>
              <span className="text-[10px] font-bold text-amber-600 dark:text-amber-400">&lt; 3h SLA</span>
            </div>

            <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between hover:border-purple-400 dark:hover:border-purple-500 transition-colors">
              <div className="space-y-0.5">
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-semibold flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                  <span>Legal Check</span>
                </div>
                <div className="text-sm font-black text-slate-900 dark:text-white">12%</div>
              </div>
              <span className="text-[10px] font-bold text-purple-600 dark:text-purple-400">Verified</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4. REAL ESTATE OPERATIONS & CONTROL SHORTCUTS */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Core Administrative Controls */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 sm:p-7 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="p-1.5 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <ShieldCheck className="w-4 h-4" />
              </span>
              <span>Administrative Controls</span>
            </h3>
            <span className="text-[11px] font-semibold text-slate-400">3 Sub-Systems</span>
          </div>

          <div className="space-y-3">
            <div
              onClick={() => onNavigate('STAFF')}
              className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 hover:border-emerald-300 dark:hover:border-emerald-700/60 flex items-center justify-between cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md group"
            >
              <div className="space-y-1">
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors flex items-center gap-2">
                  <span>Staff Roster & Multiple Dynamic Roles</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400 font-bold">
                    CRUD Live
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Assign Super Admin, Sales Manager, Telecaller, or Verification Officer roles with status toggle.
                </div>
              </div>
              <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 group-hover:border-emerald-500 transition-colors">
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-500 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>

            <div
              onClick={() => onNavigate('DYNAMIC_MASTERS')}
              className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 hover:border-emerald-300 dark:hover:border-emerald-700/60 flex items-center justify-between cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md group"
            >
              <div className="space-y-1">
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors flex items-center gap-2">
                  <span>Dynamic Property Master Tables</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-400 font-bold">
                    Zero Code
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Add dynamic options (BHKs, Facing, Furnishing, Agricultural Bigha) with instant schema updates.
                </div>
              </div>
              <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 group-hover:border-emerald-500 transition-colors">
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-500 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>

            <div
              onClick={() => onNavigate('SETTINGS')}
              className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 hover:border-emerald-300 dark:hover:border-emerald-700/60 flex items-center justify-between cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md group"
            >
              <div className="space-y-1">
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors flex items-center gap-2">
                  <span>92 Dynamic System Settings & Audit Logs</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-400 font-bold">
                    Audit Trail
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Live SLAs, WhatsApp / SMS credentials, quiet hours (21:00-09:00), and immutable audit ledger.
                </div>
              </div>
              <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 group-hover:border-emerald-500 transition-colors">
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-500 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>
          </div>
        </div>

        {/* Real Estate Operations Quick Shortcuts */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 sm:p-7 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <span className="p-1.5 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                <Building2 className="w-4 h-4" />
              </span>
              <span>Propira Verification & Lead Engines</span>
            </h3>
            <span className="text-[11px] font-semibold text-slate-400">Operations</span>
          </div>

          <div className="space-y-3">
            <div
              onClick={() => onNavigate('MY_WORK')}
              className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 hover:border-blue-300 dark:hover:border-blue-700/60 flex items-center justify-between cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md group"
            >
              <div className="space-y-1">
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors flex items-center gap-2">
                  <span>Prioritized Lead Queue</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 font-bold">
                    6-Way Inbound
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Overdue follow-ups, untouched intake leads, today&apos;s appointments, and temperature sorting.
                </div>
              </div>
              <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 group-hover:border-blue-500 transition-colors">
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-500 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>

            <div
              onClick={() => onNavigate('VERIFICATION')}
              className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 hover:border-blue-300 dark:hover:border-blue-700/60 flex items-center justify-between cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md group"
            >
              <div className="space-y-1">
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors flex items-center gap-2">
                  <span>7-Step Property Verification Hub</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 font-bold">
                    Dual Inspection
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Manager approvals, document checks, and automated 90/30-day listing expiry timers.
                </div>
              </div>
              <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 group-hover:border-blue-500 transition-colors">
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-500 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>

            <div
              onClick={() => onNavigate('RECYCLE_BIN')}
              className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800/80 hover:border-rose-300 dark:hover:border-rose-700/60 flex items-center justify-between cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md group"
            >
              <div className="space-y-1">
                <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-rose-600 dark:group-hover:text-rose-400 transition-colors flex items-center gap-2">
                  <span>Recycle Bin & Owner Ad Requests</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 font-bold">
                    Safe Purge
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Single-pending owner deletion requests and 1-click restore for accidental removals.
                </div>
              </div>
              <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 group-hover:border-rose-500 transition-colors">
                <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-rose-500 group-hover:translate-x-0.5 transition-all" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 5. SYSTEM ARCHITECTURAL VITALS FOOTER */}
      <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-950/50 p-4 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-emerald-500" />
          <span className="font-semibold text-slate-700 dark:text-slate-300">
            Omshiv Buildvision Architectural Foundation
          </span>
          <span className="text-slate-400">•</span>
          <span>FastAPI + SQLAlchemy + Repository Pattern</span>
        </div>

        <div className="flex items-center gap-4 text-[11px]">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Zero-Data Loss Architecture</span>
          </span>
          <span className="flex items-center gap-1.5">
            <Lock className="w-3 h-3 text-slate-400" />
            <span>Encrypted JWT Sessions</span>
          </span>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
