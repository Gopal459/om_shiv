import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  RefreshCw,
  Clock,
  AlertCircle,
} from 'lucide-react';

interface ApprovalItem {
  id: string;
  agent_name: string;
  lead_id: string | null;
  action_type: string;
  proposed_payload: Record<string, any>;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  requested_at: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
}

const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('access_token');
  return token
    ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    : { 'Content-Type': 'application/json' };
};

export const AIApprovalsQueue: React.FC = () => {
  const navigate = useNavigate();
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<'PENDING' | 'APPROVED' | 'REJECTED' | 'ALL'>('PENDING');
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchApprovals = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/v1/ai/approvals?status=${statusFilter}`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error('Failed to load approval queue');
      const data = await res.json();
      setApprovals(data.approvals || []);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Unable to load approvals.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, [statusFilter]);

  const handleDecision = async (id: string, decision: 'approve' | 'reject') => {
    setProcessingId(id);
    setMessage(null);
    try {
      const res = await fetch(`/v1/ai/approvals/${id}/${decision}`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ review_note: notes[id] || undefined }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Action failed');
      }
      setMessage({
        type: 'success',
        text: decision === 'approve'
          ? 'Action approved and safely applied to CRM.'
          : 'Action rejected. Lead remains unchanged.',
      });
      await fetchApprovals();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to process decision.' });
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-amber-500" />
            <span>AI Human-in-the-Loop (HITL) Approvals Queue</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Sensitive AI proposals (such as marking a lead LOST or overriding pricing) wait here until a human manager approves or rejects them.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => navigate('/ai-agents')}
            className="px-3.5 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to AI Agents</span>
          </button>

          <button
            type="button"
            onClick={fetchApprovals}
            className="px-3.5 py-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {message && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center gap-2 ${
            message.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
              : 'bg-rose-50 dark:bg-rose-950/60 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* Status Filter Pills */}
      <div className="flex flex-wrap gap-2">
        {(['PENDING', 'APPROVED', 'REJECTED', 'ALL'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setStatusFilter(tab)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-colors cursor-pointer ${
              statusFilter === tab
                ? 'bg-slate-900 dark:bg-emerald-600 text-white'
                : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Approval Cards */}
      {loading ? (
        <div className="py-16 text-center text-sm text-slate-500">Loading approval requests...</div>
      ) : approvals.length === 0 ? (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-10 text-center space-y-2">
          <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
          <div className="text-sm font-bold text-slate-900 dark:text-white">
            No {statusFilter.toLowerCase()} approval requests
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Whenever an AI agent proposes a sensitive CRM change, it will appear here for sign-off.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {approvals.map((item) => (
            <div
              key={item.id}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-3 shadow-xs"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-lg text-[11px] font-bold bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                    {item.action_type}
                  </span>
                  <span className="text-xs font-mono text-slate-500">{item.agent_name}</span>
                  {item.lead_id && (
                    <button
                      type="button"
                      onClick={() => navigate(`/leads/${item.lead_id}`)}
                      className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400 hover:underline cursor-pointer"
                    >
                      Lead: {item.lead_id}
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-2 text-[11px] text-slate-400">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{item.requested_at ? new Date(item.requested_at).toLocaleString('en-IN') : ''}</span>
                  <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-bold text-slate-700 dark:text-slate-300">
                    {item.status}
                  </span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/70 dark:border-slate-700/60 text-xs text-slate-700 dark:text-slate-300 font-mono">
                {JSON.stringify(item.proposed_payload)}
              </div>

              {item.status === 'PENDING' ? (
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 pt-1">
                  <input
                    type="text"
                    value={notes[item.id] || ''}
                    onChange={(e) => setNotes((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    placeholder="Optional manager review note..."
                    className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs text-slate-900 dark:text-white"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={processingId === item.id}
                      onClick={() => handleDecision(item.id, 'approve')}
                      className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Approve & Apply</span>
                    </button>
                    <button
                      type="button"
                      disabled={processingId === item.id}
                      onClick={() => handleDecision(item.id, 'reject')}
                      className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Reviewed by <span className="font-semibold">{item.reviewed_by || 'Manager'}</span>
                  {item.review_note ? ` — "${item.review_note}"` : ''}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AIApprovalsQueue;
