import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from 'recharts';
import {
  FileText,
  Search,
  Users,
  Handshake,
  CheckCircle2,
  Layers,
  ArrowRight,
  TrendingUp,
  Clock,
  AlertTriangle,
  Building2,
  Calendar,
  Sparkles,
  Zap,
  Activity,
  Award,
  PhoneCall,
  MapPin,
  RefreshCw,
  PlusCircle,
  Filter,
} from 'lucide-react';
import { AdminTab } from '../layouts/AdminLayout';

interface AdminDashboardProps {
  onNavigate?: (tab: AdminTab) => void;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    staffCount: 1,
    untouchedCount: 0,
    verificationCount: 2,
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
        verificationCount: 2,
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

  // 1. Opportunity Donut Data matching Screenshot 1
  const opportunityData = [
    { name: 'New', value: 44, color: '#10b981' }, // Green
    { name: 'Open', value: 47, color: '#6366f1' }, // Indigo
    { name: 'All', value: 64, color: '#38bdf8' }, // Sky Blue
    { name: 'Missing', value: 47, color: '#f97316' }, // Orange
    { name: 'Qualified', value: 15, color: '#d946ef' }, // Magenta
  ];
  const totalOpportunities = opportunityData.reduce((acc, curr) => acc + curr.value, 0);

  // 2. Call Performance Horizontal Bar Data matching Screenshot 2
  const callPerformanceData = [
    {
      category: 'Calls',
      inbound: 39,
      connected: 44,
      siteVisit: 44,
      followUp: 38,
      missed: 1,
      totalCalls: 99,
    },
    {
      category: 'Problem',
      inbound: 6,
      connected: 6,
      siteVisit: 6,
      followUp: 3,
      missed: 0,
      totalCalls: 14,
    },
  ];

  // 3. Property Inventory Lifecycle Column Data matching Screenshot 2
  const propertyLifecycleData = [
    {
      stage: 'New & Assign Property',
      primary: 460,
      verified: 184,
      expired: 38,
    },
    {
      stage: 'Verified & Live Property',
      primary: 138,
      verified: 23,
      expired: 8,
    },
    {
      stage: 'Expired Properties',
      primary: 4,
      verified: 2,
      expired: 1,
    },
    {
      stage: 'Deleted Properties',
      primary: 28,
      verified: 9,
      expired: 4,
    },
    {
      stage: 'Sold Properties',
      primary: 42,
      verified: 8,
      expired: 2,
    },
  ];

  // 4. Executive Leaderboard Data
  const leaderboardData = [
    { rank: 1, name: 'Ramesh Sharma', role: 'Sales Manager', calls: 142, visits: 28, deals: 8, rate: '86%' },
    { rank: 2, name: 'Sunita Verma', role: 'Senior Telecaller', calls: 188, visits: 19, deals: 6, rate: '79%' },
    { rank: 3, name: 'Vikas Choudhary', role: 'Field Executive', calls: 94, visits: 34, deals: 5, rate: '74%' },
    { rank: 4, name: 'Pooja Jangid', role: 'Verification Officer', calls: 110, visits: 22, deals: 4, rate: '68%' },
  ];

  // 5. Live Inbound & SLA Activity Stream Data
  const liveActivities = [
    { id: 1, text: 'New Inbound Inquiry for 3 BHK Villa in Jagatpura', source: 'Website Form', time: '2 mins ago', badge: 'Fresh Lead', alert: false },
    { id: 2, text: 'Lead OM-2026-0042 untouched for 2h 45m (Approaching 3h SLA)', source: 'SLA Escalation', time: '12 mins ago', badge: 'SLA Warning', alert: true },
    { id: 3, text: 'Physical site verification completed for Royal Heritage Mansarovar', source: '7-Step Hub', time: '24 mins ago', badge: 'Verified', alert: false },
    { id: 4, text: 'Channel Partner "Shree Ram Realty" added 2 buyer inquiries', source: 'Franchise', time: '41 mins ago', badge: 'Partner Sync', alert: false },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* 1. TOP HERO BANNER */}
      <div className="relative overflow-hidden rounded-3xl border border-[#291BB0]/30 dark:border-slate-800 bg-gradient-to-br from-[#140D5C] via-[#1F1588] to-[#291BB0] text-white p-6 sm:p-8 lg:p-10 shadow-2xl shadow-[#291BB0]/25 group">
        <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-[#3b2cc9]/35 blur-3xl pointer-events-none animate-float"></div>
        <div className="absolute -bottom-24 -right-24 w-96 h-96 rounded-full bg-[#F04B42]/25 blur-3xl pointer-events-none animate-float-delayed"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F04B42]/20 border border-[#F04B42]/50 text-rose-200 text-xs font-bold shadow-xs backdrop-blur-md">
                <span className="w-2 h-2 rounded-full bg-[#F04B42] animate-ping"></span>
                <Sparkles className="w-3.5 h-3.5 text-[#F04B42]" />
                <span>AlwarMap Command Center</span>
              </div>

              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 border border-white/10 text-slate-200 text-xs font-medium backdrop-blur-md">
                <Calendar className="w-3 h-3 text-slate-300" />
                <span>{currentDateString}</span>
              </div>
            </div>

            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-display font-black tracking-tight leading-tight">
              {greeting},{' '}
              <span className="bg-gradient-to-r from-white via-indigo-200 to-[#FF8A80] bg-clip-text text-transparent">
                AlwarMap CRM
              </span>
            </h1>

            <p className="text-xs sm:text-sm text-indigo-100/85 leading-relaxed max-w-xl">
              Enterprise real estate operations, 4-tier Channel Partner governance, AI agent automation, and verified property pipeline.
            </p>
          </div>

          <div className="relative z-10 flex flex-wrap items-center gap-3 lg:flex-col lg:items-end flex-shrink-0">
            <button
              onClick={() => navigate('/staff')}
              className="shimmer-effect group flex items-center gap-2.5 px-5 py-3 bg-[#F04B42] hover:bg-[#d93b32] text-white rounded-2xl text-xs font-bold transition-all duration-300 shadow-xl shadow-[#F04B42]/30 hover:-translate-y-1 active:translate-y-0"
            >
              <PlusCircle className="w-4 h-4 transition-transform group-hover:rotate-90 duration-300" />
              <span>+ Add Staff Member</span>
            </button>

            <div className="flex items-center gap-2">
              <button
                onClick={() => navigate('/leads')}
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

      {/* 2. 6 VIBRANT GRADIENT KPI CARDS MATCHING SCREENSHOT 1 */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-rose-500" />
            <span>Real-Time Lead & Opportunity Portfolio</span>
          </h2>
          <span className="text-xs text-slate-400">Live Database Counters</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: New Leads (Purple Gradient) */}
          <div
            onClick={() => navigate('/leads?filter=new')}
            className="relative overflow-hidden rounded-2xl p-5 text-white bg-gradient-to-br from-fuchsia-600 via-purple-600 to-indigo-700 shadow-lg shadow-purple-900/20 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl group"
          >
            {/* Decorative Glass Circle In Overlay */}
            <div className="absolute -top-6 -left-6 w-24 h-24 rounded-full bg-white/10 blur-sm pointer-events-none"></div>
            <div className="flex items-start justify-between relative z-10">
              <div className="p-3 rounded-2xl bg-white/15 backdrop-blur-md border border-white/20 group-hover:scale-110 transition-transform">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <div className="text-right">
                <div className="text-3xl font-black tracking-tight">236</div>
                <div className="text-xs font-semibold text-purple-100">New Leads</div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-white/15 flex items-center justify-between text-xs relative z-10">
              <div className="flex items-center gap-1 font-bold text-purple-100 group-hover:underline">
                <span>More Info</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              </div>
              <span className="font-mono text-[11px] font-bold text-purple-200">PR 111 FR 123</span>
            </div>
          </div>

          {/* Card 2: Open Leads (Orange Gradient) */}
          <div
            onClick={() => navigate('/leads?filter=open')}
            className="relative overflow-hidden rounded-2xl p-5 text-white bg-gradient-to-br from-amber-500 via-orange-500 to-red-600 shadow-lg shadow-orange-900/20 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl group"
          >
            <div className="absolute -top-6 -left-6 w-24 h-24 rounded-full bg-white/10 blur-sm pointer-events-none"></div>
            <div className="flex items-start justify-between relative z-10">
              <div className="p-3 rounded-2xl bg-white/15 backdrop-blur-md border border-white/20 group-hover:scale-110 transition-transform">
                <Search className="w-6 h-6 text-white" />
              </div>
              <div className="text-right">
                <div className="text-3xl font-black tracking-tight">267</div>
                <div className="text-xs font-semibold text-orange-100">Open Leads</div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-white/15 flex items-center justify-between text-xs relative z-10">
              <div className="flex items-center gap-1 font-bold text-orange-100 group-hover:underline">
                <span>More Info</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              </div>
              <span className="font-mono text-[11px] font-bold text-orange-200">PR 120 FR 131</span>
            </div>
          </div>

          {/* Card 3: Missing Leads (Deep Crimson/Brown Gradient) */}
          <div
            onClick={() => navigate('/leads?filter=untouched')}
            className="relative overflow-hidden rounded-2xl p-5 text-white bg-gradient-to-br from-rose-800 via-stone-800 to-neutral-900 shadow-lg shadow-rose-950/30 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl group"
          >
            <div className="absolute -top-6 -left-6 w-24 h-24 rounded-full bg-white/10 blur-sm pointer-events-none"></div>
            <div className="flex items-start justify-between relative z-10">
              <div className="p-3 rounded-2xl bg-white/15 backdrop-blur-md border border-white/20 group-hover:scale-110 transition-transform">
                <Users className="w-6 h-6 text-white" />
              </div>
              <div className="text-right">
                <div className="text-3xl font-black tracking-tight">267</div>
                <div className="text-xs font-semibold text-rose-200">Missing Leads</div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-white/15 flex items-center justify-between text-xs relative z-10">
              <div className="flex items-center gap-1 font-bold text-rose-200 group-hover:underline">
                <span>More Info</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              </div>
              <span className="font-mono text-[11px] font-bold text-rose-300">PR 120 FR 131</span>
            </div>
          </div>

          {/* Card 4: Converted Opportunity (Deep Navy/Blue Gradient) */}
          <div
            onClick={() => navigate('/opportunities')}
            className="relative overflow-hidden rounded-2xl p-5 text-white bg-gradient-to-br from-slate-900 via-blue-950 to-indigo-950 shadow-lg shadow-blue-950/40 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl group border border-slate-800/80"
          >
            <div className="absolute -top-6 -left-6 w-24 h-24 rounded-full bg-white/10 blur-sm pointer-events-none"></div>
            <div className="flex items-start justify-between relative z-10">
              <div className="p-3 rounded-2xl bg-white/15 backdrop-blur-md border border-white/20 group-hover:scale-110 transition-transform">
                <Handshake className="w-6 h-6 text-white" />
              </div>
              <div className="text-right">
                <div className="text-3xl font-black tracking-tight text-white">52</div>
                <div className="text-xs font-semibold text-blue-200">Converted Opportunity</div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-white/15 flex items-center justify-between text-xs relative z-10">
              <div className="flex items-center gap-1 font-bold text-blue-200 group-hover:underline">
                <span>More Info</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              </div>
              <span className="font-mono text-[11px] font-bold text-blue-300">PR 17 FR 33</span>
            </div>
          </div>

          {/* Card 5: Qualified Leads (Teal/Cyan Gradient) */}
          <div
            onClick={() => navigate('/leads?filter=qualified')}
            className="relative overflow-hidden rounded-2xl p-5 text-white bg-gradient-to-br from-teal-600 via-emerald-600 to-cyan-700 shadow-lg shadow-teal-900/20 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl group"
          >
            <div className="absolute -top-6 -left-6 w-24 h-24 rounded-full bg-white/10 blur-sm pointer-events-none"></div>
            <div className="flex items-start justify-between relative z-10">
              <div className="p-3 rounded-2xl bg-white/15 backdrop-blur-md border border-white/20 group-hover:scale-110 transition-transform">
                <CheckCircle2 className="w-6 h-6 text-white" />
              </div>
              <div className="text-right">
                <div className="text-3xl font-black tracking-tight">5</div>
                <div className="text-xs font-semibold text-teal-100">Qualified Leads</div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-white/15 flex items-center justify-between text-xs relative z-10">
              <div className="flex items-center gap-1 font-bold text-teal-100 group-hover:underline">
                <span>More Info</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              </div>
              <span className="font-mono text-[11px] font-bold text-teal-200">PR 1 FR 0</span>
            </div>
          </div>

          {/* Card 6: All Leads (Royal Indigo/Blue Gradient) */}
          <div
            onClick={() => navigate('/leads')}
            className="relative overflow-hidden rounded-2xl p-5 text-white bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-700 shadow-lg shadow-indigo-900/20 cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl group sm:col-span-2 lg:col-span-3"
          >
            <div className="absolute -top-6 -left-6 w-24 h-24 rounded-full bg-white/10 blur-sm pointer-events-none"></div>
            <div className="flex items-start justify-between relative z-10">
              <div className="p-3 rounded-2xl bg-white/15 backdrop-blur-md border border-white/20 group-hover:scale-110 transition-transform">
                <Layers className="w-6 h-6 text-white" />
              </div>
              <div className="text-right">
                <div className="text-3xl font-black tracking-tight">332</div>
                <div className="text-xs font-semibold text-indigo-100">All Intake Leads</div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-white/15 flex items-center justify-between text-xs relative z-10">
              <div className="flex items-center gap-1 font-bold text-indigo-100 group-hover:underline">
                <span>More Info</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
              </div>
              <span className="font-mono text-[11px] font-bold text-indigo-200">PR 141 FR 169 (100% Inbound)</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. RECHARTS ANALYTICS: OPPORTUNITY DONUT + CALL HORIZONTAL BARS + PROPERTY LIFECYCLE */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* CHART 1: OPPORTUNITY DONUT CHART (Screenshot 1) */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Filter className="w-4 h-4 text-purple-500" />
                <span>Opportunity Distribution</span>
              </h3>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/80">
                {totalOpportunities} Deals
              </span>
            </div>

            <div className="h-60 relative flex items-center justify-center my-3">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(15, 23, 42, 0.95)',
                      borderRadius: '12px',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#fff',
                      fontSize: '12px',
                    }}
                  />
                  <Pie
                    data={opportunityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {opportunityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>

              {/* Center Donut Ring Label */}
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-2xl font-black text-slate-900 dark:text-white">
                  {totalOpportunities}
                </span>
                <span className="text-[10px] uppercase font-bold text-slate-400">Total</span>
              </div>
            </div>
          </div>

          {/* Legend Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px]">
            {opportunityData.map((item) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }}></span>
                <span className="text-slate-600 dark:text-slate-400 font-medium truncate">
                  {item.name}: <strong className="text-slate-900 dark:text-white">{item.value}</strong>
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* CHART 2: CALL PERFORMANCE HORIZONTAL BARS (Screenshot 2) */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <PhoneCall className="w-4 h-4 text-blue-500" />
                <span>Call Activity & Escalations</span>
              </h3>
              <div className="flex items-center gap-2 text-[11px]">
                <span className="px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-bold border border-blue-200 dark:border-blue-800">
                  Calls (99)
                </span>
                <span className="px-2 py-0.5 rounded-md bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 font-bold border border-rose-200 dark:border-rose-800">
                  Problem (14)
                </span>
              </div>
            </div>

            <div className="h-64 mt-3">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={callPerformanceData}
                  margin={{ top: 10, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                  <XAxis type="number" fontSize={11} stroke="#94a3b8" />
                  <YAxis type="category" dataKey="category" fontSize={12} stroke="#94a3b8" width={60} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(15, 23, 42, 0.95)',
                      borderRadius: '12px',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#fff',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="inbound" name="Inbound" fill="#38bdf8" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="connected" name="Connected" fill="#6366f1" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="siteVisit" name="Site Visit" fill="#10b981" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="followUp" name="Follow-Up" fill="#f97316" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="totalCalls" name="Total Activity" fill="#d946ef" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
            <span>Telephonic qualification tracking & customer satisfaction score</span>
            <span className="font-semibold text-emerald-600 dark:text-emerald-400">98.4% Resolution Rate</span>
          </div>
        </div>
      </div>

      {/* CHART 3: PROPERTY INVENTORY LIFECYCLE (Screenshot 2) */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 sm:p-7 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Building2 className="w-4 h-4 text-emerald-500" />
              <span>Property Inventory Status & Lifecycle Distribution</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Live status tracking across intake, active verification, expired 90/30-day listings, and sold properties.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/properties')}
              className="text-xs font-bold text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1"
            >
              <span>Manage Inventory</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="h-72 w-full mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={propertyLifecycleData}
              margin={{ top: 20, right: 30, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="stage" fontSize={11} stroke="#94a3b8" />
              <YAxis fontSize={11} stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  borderRadius: '12px',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#fff',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              <Bar dataKey="primary" name="Active Volume" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
              <Bar dataKey="verified" name="Verified & Legal Clear" fill="#6366f1" radius={[6, 6, 0, 0]} />
              <Bar dataKey="expired" name="30/90d Timer Expired" fill="#10b981" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4. EXECUTIVE ADDITIONS: LEADERBOARD & LIVE SLA ACTIVITY STREAM */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEADERBOARD (2 Columns) */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Award className="w-4 h-4 text-amber-500" />
              <span>Top Real Estate Executives & Telecallers</span>
            </h3>
            <span className="text-[11px] font-bold text-slate-400">This Month</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="p-3">Rank</th>
                  <th className="p-3">Executive</th>
                  <th className="p-3 text-center">Calls</th>
                  <th className="p-3 text-center">Site Visits</th>
                  <th className="p-3 text-center">Won Deals</th>
                  <th className="p-3 text-right">Win Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {leaderboardData.map((item) => (
                  <tr key={item.rank} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="p-3">
                      <span
                        className={`inline-flex items-center justify-center w-6 h-6 rounded-full font-bold text-xs ${
                          item.rank === 1
                            ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                            : item.rank === 2
                            ? 'bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200'
                            : 'bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300'
                        }`}
                      >
                        #{item.rank}
                      </span>
                    </td>
                    <td className="p-3 font-semibold text-slate-900 dark:text-white">
                      <div>{item.name}</div>
                      <div className="text-[10px] text-slate-400 font-normal">{item.role}</div>
                    </td>
                    <td className="p-3 text-center font-mono font-bold text-slate-700 dark:text-slate-300">
                      {item.calls}
                    </td>
                    <td className="p-3 text-center font-mono font-bold text-blue-600 dark:text-blue-400">
                      {item.visits}
                    </td>
                    <td className="p-3 text-center font-mono font-bold text-emerald-600 dark:text-emerald-400">
                      {item.deals}
                    </td>
                    <td className="p-3 text-right">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                        {item.rate}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* LIVE INBOUND ACTIVITY STREAM (1 Column) */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-500" />
                <span>Live Activity Stream</span>
              </h3>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            </div>

            <div className="space-y-3.5 mt-3">
              {liveActivities.map((act) => (
                <div key={act.id} className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-100 dark:border-slate-800/80 space-y-1">
                  <div className="flex items-center justify-between text-[10px]">
                    <span
                      className={`font-bold px-2 py-0.2 rounded-full ${
                        act.alert
                          ? 'bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300'
                          : 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300'
                      }`}
                    >
                      {act.badge}
                    </span>
                    <span className="text-slate-400">{act.time}</span>
                  </div>
                  <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 leading-snug">
                    {act.text}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => navigate('/leads')}
            className="w-full mt-2 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl text-xs font-bold transition-all text-center"
          >
            Open Full Activity Ledger &rarr;
          </button>
        </div>
      </div>

      {/* 5. JAIPUR LOCALITY DEMAND HOTSPOTS */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <MapPin className="w-4 h-4 text-rose-500" />
            <span>Jaipur Locality Demand Heatmap & Hotspots</span>
          </h3>
          <span className="text-xs text-slate-400">Buyer Inquiry Volume</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-1">
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase">Vaishali Nagar</div>
            <div className="text-lg font-black text-rose-600 dark:text-rose-400">94% Demand</div>
            <div className="text-[10px] text-slate-400">114 Inquiries</div>
          </div>
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-1">
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase">Mansarovar</div>
            <div className="text-lg font-black text-emerald-600 dark:text-emerald-400">88% Demand</div>
            <div className="text-[10px] text-slate-400">96 Inquiries</div>
          </div>
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-1">
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase">Jagatpura</div>
            <div className="text-lg font-black text-blue-600 dark:text-blue-400">82% Demand</div>
            <div className="text-[10px] text-slate-400">84 Inquiries</div>
          </div>
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-1">
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase">Ajmer Road</div>
            <div className="text-lg font-black text-amber-600 dark:text-amber-400">76% Demand</div>
            <div className="text-[10px] text-slate-400">62 Inquiries</div>
          </div>
          <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 space-y-1">
            <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase">Tonk Road</div>
            <div className="text-lg font-black text-purple-600 dark:text-purple-400">71% Demand</div>
            <div className="text-[10px] text-slate-400">54 Inquiries</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
