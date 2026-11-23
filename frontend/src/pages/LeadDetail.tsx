import React, { useEffect, useState } from 'react';
import { ArrowLeft, Phone, MessageSquare, Calendar, Flame, CheckCircle, AlertCircle } from 'lucide-react';

interface LeadDetailProps {
  leadId: string;
  onBack: () => void;
}

const STAGES = [
  'NEW',
  'ATTEMPTING',
  'CONNECTED',
  'REQ_CAPTURED',
  'QUALIFIED',
  'MEETING',
  'SITE_VISIT',
  'NEGOTIATION',
  'WON',
  'LOST',
];

export const LeadDetail: React.FC<LeadDetailProps> = ({ leadId, onBack }) => {
  const [lead, setLead] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form states
  const [actionType, setActionType] = useState('CALL');
  const [outcome, setOutcome] = useState('Connected');
  const [stage, setStage] = useState('CONNECTED');
  const [temperature, setTemperature] = useState<'HOT' | 'WARM' | 'COLD'>('HOT');
  const [followUpDate, setFollowUpDate] = useState('');
  const [note, setNote] = useState('');
  const [lostReason, setLostReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchLead = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/leads/${leadId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setLead(data);
        setStage(data.stage || 'CONNECTED');
        if (data.temperature) setTemperature(data.temperature);
      }
    } catch (err: any) {
      setError('Failed to load lead details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLead();
  }, [leadId]);

  const handleLogAction = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setSubmitting(true);

    try {
      const token = localStorage.getItem('access_token');
      const payload: any = {
        action_type: actionType,
        outcome,
        note,
        stage,
        temperature,
        follow_up_date: followUpDate ? new Date(followUpDate).toISOString() : null,
      };

      if (stage === 'LOST') {
        payload.lost_reason = lostReason;
      }

      const res = await fetch(`/v1/leads/${leadId}/log-action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to log action');
      }

      setSuccess('Action logged and stage updated successfully!');
      setNote('');
      fetchLead();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-slate-500">Loading lead profile...</div>;
  if (!lead) return <div className="p-8 text-center text-red-500">Lead not found.</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="p-2 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <span className="font-mono text-xs font-bold text-slate-500">{lead.lead_id}</span>
          <h2 className="text-2xl font-bold text-slate-900">{lead.full_name}</h2>
        </div>
      </div>

      {/* Pipeline Visualizer */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm overflow-x-auto">
        <div className="flex items-center gap-2 min-w-max">
          {STAGES.map((s, idx) => {
            const isCurrent = lead.stage === s;
            return (
              <div
                key={s}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 ${
                  isCurrent
                    ? 'bg-green-600 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600'
                }`}
              >
                <span>{idx + 1}.</span> {s.replace('_', ' ')}
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Log Action Form */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-600" /> Log Rep Action & Transition
          </h3>

          {error && (
            <div className="mb-4 bg-red-50 border-l-4 border-red-500 p-3 flex items-center text-red-700 text-sm">
              <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="mb-4 bg-green-50 border-l-4 border-green-500 p-3 flex items-center text-green-700 text-sm">
              <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0" />
              <span>{success}</span>
            </div>
          )}

          <form onSubmit={handleLogAction} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Action Type
                </label>
                <select
                  value={actionType}
                  onChange={(e) => setActionType(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                >
                  <option value="CALL">Phone Call</option>
                  <option value="WHATSAPP">WhatsApp Chat</option>
                  <option value="MEETING">Meeting</option>
                  <option value="SITE_VISIT">Site Visit</option>
                  <option value="NOTE">Internal Note</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Outcome
                </label>
                <input
                  type="text"
                  required
                  value={outcome}
                  onChange={(e) => setOutcome(e.target.value)}
                  placeholder="Connected, Busy, Visited..."
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Target Stage
                </label>
                <select
                  value={stage}
                  onChange={(e) => setStage(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm font-semibold"
                >
                  {STAGES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Temperature
                </label>
                <select
                  value={temperature}
                  onChange={(e) => setTemperature(e.target.value as any)}
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                >
                  <option value="HOT">HOT (High Intent)</option>
                  <option value="WARM">WARM (Interested)</option>
                  <option value="COLD">COLD (Long Term)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                  Compulsory Follow-Up
                </label>
                <input
                  type="datetime-local"
                  required={stage !== 'NEW' && stage !== 'WON' && stage !== 'LOST'}
                  value={followUpDate}
                  onChange={(e) => setFollowUpDate(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2 text-sm"
                />
              </div>
            </div>

            {stage === 'LOST' && (
              <div>
                <label className="block text-xs font-bold text-red-700 uppercase mb-1">
                  Compulsory Lost Reason
                </label>
                <input
                  type="text"
                  required
                  value={lostReason}
                  onChange={(e) => setLostReason(e.target.value)}
                  placeholder="Budget too high, bought elsewhere, etc."
                  className="w-full border border-red-300 rounded-lg p-2 text-sm"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Meeting / Call Notes
              </label>
              <textarea
                rows={3}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Details of the conversation, client preferences..."
                className="w-full border border-slate-300 rounded-lg p-2 text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-2.5 rounded-lg bg-green-600 text-white font-semibold text-sm hover:bg-green-700 shadow-sm disabled:opacity-50"
            >
              {submitting ? 'Saving...' : 'Save & Update Lead'}
            </button>
          </form>
        </div>

        {/* Right Column: Profile & Timeline */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 mb-3">Lead Summary</h3>
            <div className="text-sm space-y-2 text-slate-600">
              <p><strong>Mobile:</strong> {lead.mobile}</p>
              <p><strong>Source:</strong> {lead.source}</p>
              <p><strong>Type:</strong> {lead.lead_type}</p>
              <p><strong>Budget:</strong> ₹{(lead.budget_min || 0).toLocaleString()} - ₹{(lead.budget_max || 0).toLocaleString()}</p>
              <p><strong>Locality:</strong> {lead.preferred_locality || 'Alwar'}</p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 mb-3">Activity Timeline</h3>
            <div className="space-y-3">
              {(lead.activities || []).map((act: any) => (
                <div key={act.id} className="text-xs border-l-2 border-green-500 pl-3 py-1">
                  <div className="font-bold text-slate-800">{act.action_type || act.action} ({act.outcome})</div>
                  <div className="text-slate-500">{act.note}</div>
                  <div className="text-slate-400 text-[10px] mt-0.5">{new Date(act.created_at).toLocaleString()} by {act.performed_by}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default LeadDetail;
