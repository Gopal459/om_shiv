import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bot,
  Power,
  ShieldCheck,
  ShieldAlert,
  Activity,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertCircle,
  Eye,
  Zap,
  PauseCircle,
  FileText,
  X,
  Gauge,
} from 'lucide-react';

interface AgentMetrics {
  total_runs: number;
  success_runs: number;
  shadow_runs: number;
  blocked_runs: number;
}

interface AIAgentItem {
  id: number;
  agent_name: string;
  display_name: string;
  mode: 'DISABLED' | 'SHADOW' | 'LIVE';
  is_active: boolean;
  rate_limit_per_hour: number;
  requires_hitl: boolean;
  is_customer_facing: boolean;
  category: string;
  channel: string;
  description: string;
  metrics: AgentMetrics;
  updated_at: string | null;
}

interface AgentSummary {
  total: number;
  active: number;
  live: number;
  shadow: number;
  disabled: number;
  pending_approvals: number;
}

interface ExecutionLogItem {
  id: number;
  agent_name: string;
  lead_id: string | null;
  channel: string | null;
  mode: string;
  trigger_event: string | null;
  input_summary: string | null;
  output_response: string | null;
  status: string;
  created_at: string | null;
}

const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('access_token');
  return token
    ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    : { 'Content-Type': 'application/json' };
};

export const AIAgentHub: React.FC = () => {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<AIAgentItem[]>([]);
  const [summary, setSummary] = useState<AgentSummary>({
    total: 0,
    active: 0,
    live: 0,
    shadow: 0,
    disabled: 0,
    pending_approvals: 0,
  });
  const [loading, setLoading] = useState(true);
  const [updatingAgent, setUpdatingAgent] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'INACTIVE' | 'SHADOW' | 'LIVE'>('ALL');
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Logs drawer state
  const [logsModalAgent, setLogsModalAgent] = useState<AIAgentItem | null>(null);
  const [agentLogs, setAgentLogs] = useState<ExecutionLogItem[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);

  const fetchAgents = async () => {
    setLoading(true);
    try {
      const res = await fetch('/v1/ai/agents', { headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Failed to load AI agents');
      const data = await res.json();
      setAgents(data.agents || []);
      if (data.summary) setSummary(data.summary);
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Unable to load AI agents.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const updateAgent = async (
    agentName: string,
    payload: { mode?: string; is_active?: boolean; active_mode?: string; rate_limit_per_hour?: number; reason?: string }
  ) => {
    setUpdatingAgent(agentName);
    setBanner(null);
    try {
      const res = await fetch(`/v1/ai/agents/${agentName}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || 'Update failed');
      }
      const updated = await res.json();
      setBanner({
        type: 'success',
        text: `${updated.display_name} is now ${updated.is_active ? `ACTIVE (${updated.mode})` : 'INACTIVE (DISABLED)'}.`,
      });
      await fetchAgents();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message || 'Failed to update agent configuration.' });
    } finally {
      setUpdatingAgent(null);
    }
  };

  const handleQuickActiveToggle = (agent: AIAgentItem) => {
    if (agent.is_active) {
      updateAgent(agent.agent_name, {
        is_active: false,
        reason: 'Deactivated from Admin AI Agents Hub',
      });
    } else {
      updateAgent(agent.agent_name, {
        is_active: true,
        active_mode: 'SHADOW',
        reason: 'Activated in safe SHADOW mode from Admin AI Agents Hub',
      });
    }
  };

  const openLogsModal = async (agent: AIAgentItem) => {
    setLogsModalAgent(agent);
    setLoadingLogs(true);
    setAgentLogs([]);
    try {
      const res = await fetch(`/v1/ai/logs?agent_name=${encodeURIComponent(agent.agent_name)}&limit=30`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setAgentLogs(data.logs || []);
      }
    } catch {
      // keep empty
    } finally {
      setLoadingLogs(false);
    }
  };

  const categories = useMemo(
    () => ['ALL', ...Array.from(new Set(agents.map((a) => a.category || 'General')))],
    [agents]
  );

  const filteredAgents = useMemo(() => {
    return agents.filter((a) => {
      if (selectedCategory !== 'ALL' && a.category !== selectedCategory) return false;
      if (statusFilter === 'ACTIVE' && !a.is_active) return false;
      if (statusFilter === 'INACTIVE' && a.is_active) return false;
      if (statusFilter === 'SHADOW' && a.mode !== 'SHADOW') return false;
      if (statusFilter === 'LIVE' && a.mode !== 'LIVE') return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          a.display_name.toLowerCase().includes(q) ||
          a.agent_name.toLowerCase().includes(q) ||
          a.description.toLowerCase().includes(q) ||
          a.channel.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [agents, selectedCategory, statusFilter, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-display font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
            <Bot className="w-6 h-6 text-[#291BB0] dark:text-indigo-400" />
            <span>AI Agents Control Center</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            View all 13 AI agents, switch any agent Active / Inactive instantly, or choose between Safe Shadow Trial and Live execution.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={() => navigate('/ai-approvals')}
            className="px-3.5 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30 text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer"
          >
            <ShieldAlert className="w-4 h-4" />
            <span>HITL Approvals Queue</span>
            <span className="px-1.5 py-0.5 rounded-full bg-amber-500 text-white text-[10px]">
              {summary.pending_approvals}
            </span>
          </button>

          <button
            type="button"
            onClick={fetchAgents}
            disabled={loading}
            className="px-3.5 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200 text-xs font-bold flex items-center gap-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Status Banner */}
      {banner && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center justify-between gap-3 ${
            banner.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
              : 'bg-rose-50 dark:bg-rose-950/60 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {banner.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            )}
            <span className="font-medium">{banner.text}</span>
          </div>
          <button onClick={() => setBanner(null)} className="opacity-70 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4">
          <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Total Agents</div>
          <div className="text-2xl font-black text-slate-900 dark:text-white mt-1">{summary.total}</div>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4">
          <div className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">Active (On)</div>
          <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-1">{summary.active}</div>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4">
          <div className="text-[11px] font-semibold text-amber-600 dark:text-amber-400">Shadow Trial</div>
          <div className="text-2xl font-black text-amber-600 dark:text-amber-400 mt-1">{summary.shadow}</div>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4">
          <div className="text-[11px] font-semibold text-blue-600 dark:text-blue-400">Live Mode</div>
          <div className="text-2xl font-black text-blue-600 dark:text-blue-400 mt-1">{summary.live}</div>
        </div>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4">
          <div className="text-[11px] font-semibold text-rose-600 dark:text-rose-400">Inactive (Disabled)</div>
          <div className="text-2xl font-black text-rose-600 dark:text-rose-400 mt-1">{summary.disabled}</div>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors cursor-pointer ${
                selectedCategory === cat
                  ? 'bg-[#291BB0] text-white shadow-xs'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-200"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active Only</option>
            <option value="INACTIVE">Inactive Only</option>
            <option value="SHADOW">Shadow Trial Only</option>
            <option value="LIVE">Live Only</option>
          </select>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search agent..."
              className="pl-8 pr-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>
      </div>

      {/* Agents Grid */}
      {loading && agents.length === 0 ? (
        <div className="py-16 text-center text-sm text-slate-500 dark:text-slate-400">
          Loading AI Agents...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredAgents.map((agent) => {
            const isUpdating = updatingAgent === agent.agent_name;
            return (
              <div
                key={agent.agent_name}
                className={`bg-white dark:bg-slate-900 rounded-2xl border p-5 flex flex-col justify-between space-y-4 transition-all ${
                  agent.is_active
                    ? 'border-slate-200 dark:border-slate-800 shadow-sm'
                    : 'border-rose-200/70 dark:border-rose-900/40 opacity-85'
                }`}
              >
                {/* Card Top */}
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                          {agent.category}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                            agent.mode === 'LIVE'
                              ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30'
                              : agent.mode === 'SHADOW'
                              ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30'
                              : 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/30'
                          }`}
                        >
                          {agent.mode === 'DISABLED' ? 'INACTIVE' : agent.mode}
                        </span>
                        {agent.requires_hitl && (
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-indigo-500/10 text-indigo-600 dark:text-indigo-300">
                            HITL Guard
                          </span>
                        )}
                      </div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-snug">
                        {agent.display_name}
                      </h3>
                      <div className="text-[11px] font-mono text-slate-400">
                        {agent.channel}
                      </div>
                    </div>

                    {/* Primary Active / Inactive Switch */}
                    <button
                      type="button"
                      disabled={isUpdating}
                      onClick={() => handleQuickActiveToggle(agent)}
                      title={agent.is_active ? 'Click to Deactivate (Disable)' : 'Click to Activate (Shadow Mode)'}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer flex-shrink-0 ${
                        agent.is_active
                          ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs'
                          : 'bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <Power className="w-3.5 h-3.5" />
                      <span>{agent.is_active ? 'Active' : 'Inactive'}</span>
                    </button>
                  </div>

                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                    {agent.description}
                  </p>
                </div>

                {/* Mode Selector + Rate Limit + Metrics */}
                <div className="space-y-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                  {/* 3-State Mode Buttons */}
                  <div>
                    <div className="text-[10px] font-bold uppercase text-slate-400 mb-1.5">
                      Operating Mode
                    </div>
                    <div className="grid grid-cols-3 gap-1.5 bg-slate-100 dark:bg-slate-950 p-1 rounded-xl">
                      <button
                        type="button"
                        disabled={isUpdating}
                        onClick={() => updateAgent(agent.agent_name, { mode: 'DISABLED' })}
                        className={`py-1.5 rounded-lg text-[11px] font-bold flex items-center justify-center gap-1 transition-all cursor-pointer ${
                          agent.mode === 'DISABLED'
                            ? 'bg-rose-600 text-white shadow-xs'
                            : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'
                        }`}
                      >
                        <PauseCircle className="w-3 h-3" />
                        <span>Inactive</span>
                      </button>

                      <button
                        type="button"
                        disabled={isUpdating}
                        onClick={() => updateAgent(agent.agent_name, { mode: 'SHADOW' })}
                        className={`py-1.5 rounded-lg text-[11px] font-bold flex items-center justify-center gap-1 transition-all cursor-pointer ${
                          agent.mode === 'SHADOW'
                            ? 'bg-amber-500 text-slate-950 shadow-xs'
                            : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'
                        }`}
                      >
                        <Eye className="w-3 h-3" />
                        <span>Shadow</span>
                      </button>

                      <button
                        type="button"
                        disabled={isUpdating}
                        onClick={() => updateAgent(agent.agent_name, { mode: 'LIVE' })}
                        className={`py-1.5 rounded-lg text-[11px] font-bold flex items-center justify-center gap-1 transition-all cursor-pointer ${
                          agent.mode === 'LIVE'
                            ? 'bg-emerald-600 text-white shadow-xs'
                            : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'
                        }`}
                      >
                        <Zap className="w-3 h-3" />
                        <span>Live</span>
                      </button>
                    </div>
                  </div>

                  {/* Rate limit + View Logs */}
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                      <Gauge className="w-3.5 h-3.5" />
                      <span>Limit/hr:</span>
                      <select
                        disabled={isUpdating}
                        value={agent.rate_limit_per_hour}
                        onChange={(e) =>
                          updateAgent(agent.agent_name, {
                            rate_limit_per_hour: Number(e.target.value),
                          })
                        }
                        className="px-2 py-0.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs font-bold text-slate-800 dark:text-slate-200"
                      >
                        {[5, 10, 15, 20, 25, 30, 40, 50, 60, 100].map((val) => (
                          <option key={val} value={val}>
                            {val}
                          </option>
                        ))}
                      </select>
                    </div>

                    <button
                      type="button"
                      onClick={() => openLogsModal(agent)}
                      className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-[11px] font-bold flex items-center gap-1 cursor-pointer"
                    >
                      <Activity className="w-3 h-3 text-emerald-500" />
                      <span>Logs ({agent.metrics.total_runs})</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Agent Execution Logs Modal */}
      {logsModalAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs">
          <div className="w-full max-w-3xl bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-500" />
                  <span>{logsModalAgent.display_name} — Execution & Shadow Logs</span>
                </h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Mobile numbers and emails are automatically PII-masked.
                </p>
              </div>
              <button
                onClick={() => setLogsModalAgent(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-3">
              {loadingLogs ? (
                <div className="py-10 text-center text-xs text-slate-500">Loading audit logs...</div>
              ) : agentLogs.length === 0 ? (
                <div className="py-10 text-center text-xs text-slate-500">
                  No execution logs recorded yet for this agent.
                </div>
              ) : (
                agentLogs.map((log) => (
                  <div
                    key={log.id}
                    className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/70 space-y-1.5"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 font-bold">
                          {log.status}
                        </span>
                        <span className="font-mono text-slate-500">{log.mode}</span>
                        {log.lead_id && (
                          <span className="font-mono text-emerald-600 dark:text-emerald-400">
                            Lead: {log.lead_id}
                          </span>
                        )}
                      </div>
                      <span className="font-mono text-slate-400">
                        {log.created_at ? new Date(log.created_at).toLocaleString('en-IN') : ''}
                      </span>
                    </div>
                    {log.input_summary && (
                      <div className="text-xs text-slate-700 dark:text-slate-300">
                        <span className="font-semibold">Input:</span> {log.input_summary}
                      </div>
                    )}
                    {log.output_response && (
                      <div className="text-xs text-slate-600 dark:text-slate-400">
                        <span className="font-semibold">Result:</span> {log.output_response}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIAgentHub;
