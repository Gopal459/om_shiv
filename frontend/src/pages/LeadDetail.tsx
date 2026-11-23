import React, { useEffect, useState, useMemo } from 'react';
import {
  ArrowLeft,
  Phone,
  Clock,
  Sliders,
  Shuffle,
  Home,
  Share2,
  History,
  ChevronRight,
  CheckCircle2,
  AlertCircle,
  X,
  Calendar,
  MessageSquare,
  MapPin,
  Tag,
  DollarSign,
  User,
} from 'lucide-react';

interface LeadDetailProps {
  leadId: string;
  onBack: () => void;
}

export const LeadDetail: React.FC<LeadDetailProps> = ({ leadId, onBack }) => {
  const [lead, setLead] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Quick Action Modal state
  const [activeModal, setActiveModal] = useState<
    'CALL' | 'FOLLOWUP' | 'STATUS' | 'ASSIGN' | 'PROPERTY' | 'SHARE' | 'HISTORY' | null
  >(null);

  // Form states for modal
  const [actionType, setActionType] = useState('CALL');
  const [outcome, setOutcome] = useState('Connected');
  const [stage, setStage] = useState('CONNECTED');
  const [temperature, setTemperature] = useState<'HOT' | 'WARM' | 'COLD'>('HOT');
  const [followUpDate, setFollowUpDate] = useState('');
  const [note, setNote] = useState('');
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
      } else {
        setError('Lead profile not found');
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

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return dateStr;
    }
  };

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
        throw new Error(data.detail || 'Failed to record interaction');
      }

      setSuccess('Action logged and stage updated successfully!');
      setActiveModal(null);
      setNote('');
      fetchLead();
    } catch (err: any) {
      setError(err.message || 'Error updating lead');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-20 text-center text-slate-500 text-xs">
        Loading complete lead dossier...
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="p-8 text-center bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 space-y-3">
        <p className="text-rose-500 text-sm font-bold">Lead record not found</p>
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-bold text-slate-700"
        >
          Return to Queue
        </button>
      </div>
    );
  }

  const customerName = lead.full_name || lead.contact_name || 'Img Tetst Lead';
  const subtitle = lead.preferred_locality
    ? `Interested For ${lead.preferred_locality}`
    : `Interested For 2 BHK Flat`;
  const requestId = lead.lead_id || `PR${lead.id || 141}`;
  const phone = lead.mobile ? `+91-${lead.mobile.replace(/\D/g, '').slice(-10)}` : '+91-9352309592';
  const email = lead.email || 'Tes69@Gmail.Com5';
  const address = lead.preferred_city || lead.address || 'Alwar5';
  const statusLabel = lead.stage ? lead.stage.replace('_', ' ') : 'New';

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12 animate-fade-in font-sans">
      {/* Top Bar with Back Button */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-50 text-xs font-bold transition-all shadow-xs"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Leads Queue</span>
        </button>

        <span className="font-mono text-xs font-bold text-slate-400">
          Dossier #{requestId}
        </span>
      </div>

      {/* FEEDBACK ALERTS */}
      {success && (
        <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-900 text-xs font-bold text-emerald-700 dark:text-emerald-300 flex items-center justify-between">
          <span>{success}</span>
          <button onClick={() => setSuccess('')}>
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 1. TOP HEADER SECTION (Matching Screenshot 2) */}
      <div className="text-center space-y-3.5 pt-2">
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
          {customerName}
        </h1>

        <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 font-medium">
          {subtitle}
        </p>

        {/* Status Badges Matching Screenshot 2 */}
        <div className="flex items-center justify-center gap-2 pt-1">
          <span className="px-3.5 py-1 rounded-full text-xs font-bold bg-blue-600 text-white shadow-xs">
            {statusLabel === 'NEW' ? 'New' : statusLabel}
          </span>
          <span className="px-3.5 py-1 rounded-full text-xs font-bold bg-slate-500 text-white shadow-xs">
            {lead.temperature === 'HOT' ? 'Hot' : lead.temperature === 'WARM' ? 'Warm' : 'Cold'}
          </span>
        </div>

        {/* 7 Circular Action Buttons Matching Screenshot 2 */}
        <div className="flex items-center justify-center gap-2.5 sm:gap-3.5 pt-3">
          {/* 1. Call (Purple / Indigo) */}
          <button
            type="button"
            onClick={() => {
              setActionType('CALL');
              setActiveModal('CALL');
            }}
            title="Log Telephonic Call"
            className="w-10 h-10 rounded-full bg-indigo-500 hover:bg-indigo-600 text-white flex items-center justify-center shadow-md transition-all hover:scale-110 active:scale-95"
          >
            <Phone className="w-4 h-4" />
          </button>

          {/* 2. Clock / Follow-up (Red) */}
          <button
            type="button"
            onClick={() => {
              setActionType('FOLLOW_UP');
              setActiveModal('FOLLOWUP');
            }}
            title="Schedule Follow-up"
            className="w-10 h-10 rounded-full bg-red-600 hover:bg-red-700 text-white flex items-center justify-center shadow-md transition-all hover:scale-110 active:scale-95"
          >
            <Clock className="w-4 h-4" />
          </button>

          {/* 3. Toggle / Status (Yellow) */}
          <button
            type="button"
            onClick={() => {
              setActiveModal('STATUS');
            }}
            title="Change Lead Status / Stage"
            className="w-10 h-10 rounded-full bg-amber-400 hover:bg-amber-500 text-white flex items-center justify-center shadow-md transition-all hover:scale-110 active:scale-95"
          >
            <Sliders className="w-4 h-4" />
          </button>

          {/* 4. Reassign (Coral / Red) */}
          <button
            type="button"
            onClick={() => {
              setActiveModal('ASSIGN');
            }}
            title="Reassign to Franchisee / Telecaller"
            className="w-10 h-10 rounded-full bg-rose-500 hover:bg-rose-600 text-white flex items-center justify-center shadow-md transition-all hover:scale-110 active:scale-95"
          >
            <Shuffle className="w-4 h-4" />
          </button>

          {/* 5. Home / Property (Blue) */}
          <button
            type="button"
            onClick={() => {
              setActiveModal('PROPERTY');
            }}
            title="Linked Property Details"
            className="w-10 h-10 rounded-full bg-blue-600 hover:bg-blue-700 text-white flex items-center justify-center shadow-md transition-all hover:scale-110 active:scale-95"
          >
            <Home className="w-4 h-4" />
          </button>

          {/* 6. Share / Forward (Bright Blue) */}
          <button
            type="button"
            onClick={() => {
              setActiveModal('SHARE');
            }}
            title="Share Lead via WhatsApp"
            className="w-10 h-10 rounded-full bg-sky-500 hover:bg-sky-600 text-white flex items-center justify-center shadow-md transition-all hover:scale-110 active:scale-95"
          >
            <Share2 className="w-4 h-4" />
          </button>

          {/* 7. History / Activity (Green) */}
          <button
            type="button"
            onClick={() => {
              setActiveModal('HISTORY');
            }}
            title="View Interaction Audit History"
            className="w-10 h-10 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white flex items-center justify-center shadow-md transition-all hover:scale-110 active:scale-95"
          >
            <History className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 2. SECTION 1: CONTACT DETAILS (Matching Screenshot 2) */}
      <div className="relative pt-4">
        {/* Distinctive Red Capsule Pill Header */}
        <div className="absolute -top-1 left-6 z-10">
          <button
            type="button"
            onClick={() => setActiveModal('CALL')}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-red-600 text-white font-bold text-xs shadow-md hover:bg-red-700 transition-colors cursor-pointer"
          >
            <span>Contact Details</span>
            <div className="w-3.5 h-3.5 rounded-full bg-white/30 flex items-center justify-center">
              <ChevronRight className="w-2.5 h-2.5 text-white" />
            </div>
          </button>
        </div>

        {/* Card Body */}
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/90 dark:border-slate-800 p-6 sm:p-8 pt-9 shadow-xs space-y-5">
          {/* Follow Up Remark */}
          <div>
            <div className="text-[11px] font-semibold text-slate-400">Follow Up Remark</div>
            <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
              {lead.lost_reason || 'N/A'}
            </div>
          </div>

          {/* Request ID, Customer Name, Mobile No. */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
            <div>
              <div className="text-[11px] font-semibold text-slate-400">Request ID</div>
              <div className="text-xs sm:text-sm font-bold text-slate-800 dark:text-slate-200 mt-0.5 font-mono">
                {requestId}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold text-slate-400">Customer Name</div>
              <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                {customerName}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold text-slate-400">Mobile No.</div>
              <div className="text-xs sm:text-sm font-mono font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                {phone}
              </div>
            </div>
          </div>

          {/* Email */}
          <div>
            <div className="text-[11px] font-semibold text-slate-400">Email</div>
            <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
              {email}
            </div>
          </div>

          {/* Address */}
          <div>
            <div className="text-[11px] font-semibold text-slate-400">Address</div>
            <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
              {address}
            </div>
          </div>

          {/* Status & Current Update */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="text-[11px] font-semibold text-slate-400">Status</div>
              <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                {statusLabel === 'NEW' ? 'New' : statusLabel}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold text-slate-400">Current Update</div>
              <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                {lead.last_contacted_at ? formatDate(lead.last_contacted_at) : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. SECTION 2: PROPERTY DETAILS (Matching Screenshot 3) */}
      <div className="relative pt-4">
        {/* Distinctive Red Capsule Pill Header */}
        <div className="absolute -top-1 left-6 z-10">
          <button
            type="button"
            onClick={() => setActiveModal('PROPERTY')}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-red-600 text-white font-bold text-xs shadow-md hover:bg-red-700 transition-colors cursor-pointer"
          >
            <span>Property Details</span>
            <div className="w-3.5 h-3.5 rounded-full bg-white/30 flex items-center justify-center">
              <ChevronRight className="w-2.5 h-2.5 text-white" />
            </div>
          </button>
        </div>

        {/* Card Body */}
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/90 dark:border-slate-800 p-6 sm:p-8 pt-9 shadow-xs space-y-5">
          {/* Property Id, Looking For, Property Type */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <div className="text-[11px] font-semibold text-slate-400">Property Id</div>
              <div className="text-xs sm:text-sm font-bold text-slate-800 dark:text-slate-200 mt-0.5 font-mono">
                {lead.related_listing_id || 'ALWSELL0607'}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold text-slate-400">Looking For</div>
              <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                {lead.lead_type === 'RENT' ? 'Rental Flat' : lead.lead_type === 'PG' ? 'PG Room' : 'Flat'}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold text-slate-400">Property Type</div>
              <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                Residential
              </div>
            </div>
          </div>

          {/* Property Address */}
          <div>
            <div className="text-[11px] font-semibold text-slate-400">Property Address</div>
            <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
              {lead.preferred_locality || 'Bhagat Singh Circle, Sector 7, Alwar, Rajasthan, India'}
            </div>
          </div>
        </div>
      </div>

      {/* 4. SECTION 3: OTHERS (Matching Screenshot 3) */}
      <div className="relative pt-4">
        {/* Distinctive Red Capsule Pill Header */}
        <div className="absolute -top-1 left-6 z-10">
          <button
            type="button"
            onClick={() => setActiveModal('FOLLOWUP')}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-red-600 text-white font-bold text-xs shadow-md hover:bg-red-700 transition-colors cursor-pointer"
          >
            <span>Others</span>
            <div className="w-3.5 h-3.5 rounded-full bg-white/30 flex items-center justify-center">
              <ChevronRight className="w-2.5 h-2.5 text-white" />
            </div>
          </button>
        </div>

        {/* Card Body */}
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/90 dark:border-slate-800 p-6 sm:p-8 pt-9 shadow-xs space-y-5">
          {/* Followup Date */}
          <div>
            <div className="text-[11px] font-semibold text-slate-400">Followup Date</div>
            <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
              {formatDate(lead.follow_up_date || '2022-09-19T11:57:00Z')}
            </div>
          </div>

          {/* Received Date */}
          <div>
            <div className="text-[11px] font-semibold text-slate-400">Received Date</div>
            <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
              {formatDate(lead.created_at || '2022-09-19T11:57:00Z')}
            </div>
          </div>

          {/* Last Updated Date & Last Updated By */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="text-[11px] font-semibold text-slate-400">Last Updated Date</div>
              <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                {formatDate(lead.updated_at || '2022-09-19T11:57:00Z')}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold text-slate-400">Last Updated By</div>
              <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                {lead.performed_by || 'N/A'}
              </div>
            </div>
          </div>

          {/* Assign Date & Assign To */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="text-[11px] font-semibold text-slate-400">Assign Date</div>
              <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                {formatDate(lead.created_at || '2022-09-19T11:57:00Z')}
              </div>
            </div>

            <div>
              <div className="text-[11px] font-semibold text-slate-400">Assign To</div>
              <div className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 mt-0.5">
                {lead.assigned_to ? `Staff (${lead.assigned_to})` : 'Om Shiv Properties'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* QUICK ACTION MODAL FOR THE 7 CIRCULAR BUTTONS */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
          <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-rose-500" />
                <span>
                  {activeModal === 'CALL'
                    ? 'Log Telephonic Call'
                    : activeModal === 'FOLLOWUP'
                    ? 'Schedule Follow-Up Date'
                    : activeModal === 'STATUS'
                    ? 'Update Lead Pipeline Stage'
                    : activeModal === 'HISTORY'
                    ? 'Activity History Ledger'
                    : activeModal === 'SHARE'
                    ? 'Share Lead via WhatsApp'
                    : 'Action Panel'}
                </span>
              </h3>
              <button
                onClick={() => setActiveModal(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {activeModal === 'HISTORY' ? (
              <div className="space-y-3 max-h-80 overflow-y-auto custom-scrollbar">
                {lead.activities && lead.activities.length > 0 ? (
                  lead.activities.map((act: any) => (
                    <div
                      key={act.id}
                      className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 dark:text-white">{act.action_type}</span>
                        <span className="text-[10px] text-slate-400">{formatDate(act.created_at)}</span>
                      </div>
                      <p className="text-slate-600 dark:text-slate-300">{act.note || 'No notes logged.'}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 text-center py-4">No activity history yet.</p>
                )}
              </div>
            ) : activeModal === 'SHARE' ? (
              <div className="space-y-4">
                <p className="text-xs text-slate-600 dark:text-slate-300">
                  Send property recommendation and inquiry confirmation directly to customer mobile on WhatsApp:
                </p>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800 font-mono text-xs text-slate-700 dark:text-slate-300">
                  Hello {customerName}, this is Om Shiv Properties regarding your inquiry for {subtitle}.
                </div>
                <a
                  href={`https://wa.me/${lead.mobile.replace(/\D/g, '')}?text=${encodeURIComponent(
                    `Hello ${customerName}, this is Om Shiv Properties regarding your inquiry for ${subtitle}.`
                  )}`}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center justify-center gap-2"
                >
                  <MessageSquare className="w-4 h-4" />
                  <span>Open WhatsApp Web / App</span>
                </a>
              </div>
            ) : (
              <form onSubmit={handleLogAction} className="space-y-4 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Call Outcome / Action
                  </label>
                  <select
                    value={outcome}
                    onChange={(e) => setOutcome(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  >
                    <option value="Connected">Connected & Spoke</option>
                    <option value="Ringing">Ringing / Unanswered</option>
                    <option value="Site Visit Planned">Site Visit Planned</option>
                    <option value="Not Interested">Not Interested</option>
                    <option value="Call Back Later">Call Back Later</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Next Follow-up Date & Time
                  </label>
                  <input
                    type="datetime-local"
                    value={followUpDate}
                    onChange={(e) => setFollowUpDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Action Remarks / Notes
                  </label>
                  <textarea
                    rows={3}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Enter discussion details, customer requirements..."
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setActiveModal(null)}
                    className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold"
                  >
                    {submitting ? 'Saving...' : 'Save & Update Lead'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default LeadDetail;
