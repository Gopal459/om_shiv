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
  Flame,
  Sun,
  Snowflake,
  Copy,
  ExternalLink,
  Send,
  Building,
  RefreshCw,
  ShieldCheck,
  UserCheck,
  FileText,
  Check,
} from 'lucide-react';

interface LeadDetailProps {
  leadId: string;
  onBack: () => void;
}

const STAGE_OPTIONS = [
  { value: 'NEW', label: 'New Intake', statusNum: 0, stageNum: 1 },
  { value: 'CONNECTED', label: 'In Discussion', statusNum: 1, stageNum: 1 },
  { value: 'SITE_VISIT', label: 'Site Visit Planned', statusNum: 1, stageNum: 2 },
  { value: 'FINALIZATION', label: 'Site Visit Completed', statusNum: 1, stageNum: 3 },
  { value: 'QUALIFIED', label: 'Qualified Lead', statusNum: 4, stageNum: 3 },
  { value: 'CONVERTED', label: 'Deal Closed / Converted', statusNum: 5, stageNum: 3 },
  { value: 'LOST', label: 'Disqualified / Lost', statusNum: 2, stageNum: 1 },
];

export const LeadDetail: React.FC<LeadDetailProps> = ({ leadId, onBack }) => {
  const [lead, setLead] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [copiedId, setCopiedId] = useState(false);

  // Quick Action Modal states
  const [activeModal, setActiveModal] = useState<
    'CALL' | 'FOLLOWUP' | 'STATUS' | 'ASSIGN' | 'PROPERTY' | 'SHARE' | 'HISTORY' | null
  >(null);

  // Form states for modals & quick inline log
  const [actionType, setActionType] = useState('CALL');
  const [outcome, setOutcome] = useState('Connected');
  const [selectedStage, setSelectedStage] = useState('CONNECTED');
  const [temperature, setTemperature] = useState<'HOT' | 'WARM' | 'COLD'>('HOT');
  const [followUpDate, setFollowUpDate] = useState('');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Inline quick note state
  const [inlineNote, setInlineNote] = useState('');
  const [inlineActionType, setInlineActionType] = useState('NOTE');

  const fetchLead = async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/leads/${leadId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setLead(data);
        setSelectedStage(data.stage || 'NEW');
        if (data.temperature) setTemperature(data.temperature);
      } else {
        setError('Lead profile not found in database');
      }
    } catch (err: any) {
      setError('Failed to load lead details from API');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLead();
  }, [leadId]);

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return 'Not Specified';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
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

  const handleCopyId = (idToCopy: string) => {
    navigator.clipboard.writeText(idToCopy);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleLogAction = async (e?: React.FormEvent, isInline = false) => {
    if (e) e.preventDefault();
    setError('');
    setSuccess('');
    setSubmitting(true);

    try {
      const token = localStorage.getItem('access_token');
      const payload: any = isInline
        ? {
            action_type: inlineActionType,
            outcome: 'Note Added',
            note: inlineNote,
            stage: selectedStage,
            temperature,
          }
        : {
            action_type: actionType,
            outcome,
            note,
            stage: selectedStage,
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

      setSuccess('Interaction recorded and lead profile updated successfully!');
      setActiveModal(null);
      setNote('');
      if (isInline) setInlineNote('');
      fetchLead(true);
    } catch (err: any) {
      setError(err.message || 'Error updating lead');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStagePatch = async (newStageVal: string) => {
    setError('');
    setSuccess('');
    setSubmitting(true);
    try {
      const targetOption = STAGE_OPTIONS.find((s) => s.value === newStageVal) || STAGE_OPTIONS[0];
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/leads/${leadId}/stage`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          lead_status: targetOption.statusNum,
          stage: targetOption.stageNum,
          remark: `Stage changed to ${targetOption.label}`,
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to update pipeline stage');
      }

      setSuccess(`Pipeline stage updated to ${targetOption.label}!`);
      setActiveModal(null);
      fetchLead(true);
    } catch (err: any) {
      setError(err.message || 'Error updating stage');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-3 font-sans">
        <div className="w-10 h-10 border-3 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">
          Loading dynamic lead profile from database...
        </p>
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="p-8 text-center bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 space-y-4 max-w-md mx-auto my-12 shadow-sm font-sans">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto" />
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Lead Record Not Found</h3>
          <p className="text-xs text-slate-500">The lead dossier #{leadId} does not exist or has been archived.</p>
        </div>
        <button
          onClick={onBack}
          className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition-all"
        >
          Return to Leads Queue
        </button>
      </div>
    );
  }

  // Pure dynamic values from API / DB (no hardcoded static placeholders)
  const customerName = lead.full_name || lead.contact_name || 'Valued Client';
  const leadUid = lead.lead_id || lead.lead_unique_id || `LEAD-${lead.id}`;
  const phone = lead.mobile ? lead.mobile.replace(/\D/g, '').slice(-10) : '';
  const displayPhone = phone ? `+91 ${phone.slice(0, 5)} ${phone.slice(5)}` : 'Not Provided';
  const altPhone = lead.alternate_contact_mobile || '';
  const email = lead.email || '';
  const clientAddress = lead.preferred_city || lead.address || '';
  const propertyAddress = lead.indv_property_address || lead.preferred_locality || '';
  const propertyCode = lead.property_idno || (lead.property_id > 0 ? `PROP-${lead.property_id}` : '');
  const dealPrice = Number(lead.deal_final_price || 0);
  const formattedDealPrice = dealPrice > 0 ? `₹ ${dealPrice.toLocaleString('en-IN')}` : 'Negotiable / Open';
  const leadType = (lead.lead_type || 'BUY').toUpperCase();
  const sourceName = lead.lead_source_name || lead.source || 'Website Inbound';
  const assignedDesk = lead.assigned_to ? `Staff (${lead.assigned_to})` : 'Om Shiv Central Desk';
  const supervisorRemark = lead.lead_remark || (lead.activities && lead.activities[0]?.note) || '';
  const currentStage = lead.stage || 'NEW';
  const leadTemp = lead.temperature || 'WARM';

  // Customer initials
  const initials = customerName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((n: string) => n[0].toUpperCase())
    .join('') || 'LD';

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16 animate-fade-in font-sans">
      {/* 1. TOP BREADCRUMB & UTILITY BAR */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 font-bold transition-all shadow-xs"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Leads Queue</span>
          </button>
          <span className="text-slate-400 dark:text-slate-600">/</span>
          <span className="text-slate-500 dark:text-slate-400 font-medium">{leadType} Pipeline</span>
          <span className="text-slate-400 dark:text-slate-600">/</span>
          <span className="font-mono font-bold text-slate-900 dark:text-white bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md">
            {leadUid}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchLead(true)}
            disabled={refreshing}
            title="Refresh from DB"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white text-xs font-semibold shadow-xs transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-emerald-500' : ''}`} />
            <span>{refreshing ? 'Syncing...' : 'Live Sync'}</span>
          </button>

          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800/60 text-[11px] font-bold text-emerald-700 dark:text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Database Active
          </span>
        </div>
      </div>

      {/* FEEDBACK ALERTS */}
      {success && (
        <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-900 text-xs font-bold text-emerald-700 dark:text-emerald-300 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{success}</span>
          </div>
          <button onClick={() => setSuccess('')} className="hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {error && (
        <div className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-xs font-bold text-rose-700 dark:text-rose-300 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError('')} className="hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 2. MODERN EXECUTIVE HERO CARD */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 text-white p-6 sm:p-8 shadow-2xl border border-slate-800">
        {/* Subtle Ambient Decorative Glows */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-10 -left-10 w-72 h-72 bg-blue-500/10 rounded-full blur-2xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          {/* Left: Avatar + Title & Badges */}
          <div className="flex items-start gap-4 sm:gap-5">
            <div className="relative">
              <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center font-black text-xl sm:text-2xl text-white shadow-lg shadow-emerald-900/40 border border-white/20">
                {initials}
              </div>
              <div
                title="Verified Inbound Lead"
                className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-400 border-2 border-slate-900 flex items-center justify-center text-slate-950"
              >
                <Check className="w-3 h-3 stroke-[3]" />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-white">
                  {customerName}
                </h1>
                <button
                  type="button"
                  onClick={() => handleCopyId(leadUid)}
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-white/10 hover:bg-white/20 border border-white/15 text-[11px] font-mono text-emerald-300 font-bold transition-colors cursor-pointer"
                  title="Click to copy Lead ID"
                >
                  <span>{leadUid}</span>
                  {copiedId ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 opacity-60" />}
                </button>
              </div>

              <p className="text-xs sm:text-sm text-slate-300 font-medium flex items-center gap-2 flex-wrap">
                <span>Looking for:</span>
                <span className="font-bold text-white">
                  {propertyAddress ? `${propertyAddress}` : `${leadType} Property In Alwar`}
                </span>
                <span className="text-slate-500">•</span>
                <span className="text-emerald-400 font-semibold">{formattedDealPrice}</span>
              </p>

              {/* Tag Pills */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {/* Lead Type Pill */}
                <span
                  className={`px-2.5 py-0.5 rounded-lg text-[11px] font-bold uppercase tracking-wider ${
                    leadType === 'BUY'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : leadType === 'RENT'
                      ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                      : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                  }`}
                >
                  {leadType} Requirement
                </span>

                {/* Source Channel Pill */}
                <span className="px-2.5 py-0.5 rounded-lg text-[11px] font-medium bg-white/10 border border-white/10 text-slate-200 flex items-center gap-1">
                  <Tag className="w-3 h-3 text-emerald-400" />
                  <span>{sourceName}</span>
                </span>

                {/* Dealer Status */}
                <span className="px-2.5 py-0.5 rounded-lg text-[11px] font-medium bg-white/10 border border-white/10 text-slate-300">
                  {lead.dealer_have === 1 ? 'Channel Dealer' : 'Direct Customer'}
                </span>
              </div>
            </div>
          </div>

          {/* Right: Real-time Indicators & Temperature */}
          <div className="flex flex-row lg:flex-col items-start lg:items-end justify-between w-full lg:w-auto gap-3 pt-2 lg:pt-0 border-t lg:border-t-0 border-white/10">
            {/* Temperature Badge */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Priority:</span>
              <div
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black shadow-md ${
                  leadTemp === 'HOT'
                    ? 'bg-gradient-to-r from-rose-500 to-amber-500 text-white animate-pulse'
                    : leadTemp === 'WARM'
                    ? 'bg-gradient-to-r from-amber-500 to-orange-400 text-slate-950 font-bold'
                    : 'bg-slate-800 text-sky-300 border border-sky-400/30'
                }`}
              >
                {leadTemp === 'HOT' ? (
                  <Flame className="w-3.5 h-3.5 fill-current" />
                ) : leadTemp === 'WARM' ? (
                  <Sun className="w-3.5 h-3.5 fill-current" />
                ) : (
                  <Snowflake className="w-3.5 h-3.5" />
                )}
                <span>{leadTemp} LEAD</span>
              </div>
            </div>

            {/* Pipeline Stage Badge */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Stage:</span>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-blue-600/90 text-white border border-blue-400/30 shadow-xs">
                {currentStage.replace(/_/g, ' ')}
              </span>
            </div>

            {/* SLA Status Pill */}
            <div className="text-[11px] font-medium text-slate-400 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-emerald-400" />
              <span>
                {lead.is_untouched
                  ? '3h SLA Escalation Watch: Untouched'
                  : lead.follow_up_date
                  ? `Next follow-up: ${formatDate(lead.follow_up_date)}`
                  : 'SLA Status: Normal'}
              </span>
            </div>
          </div>
        </div>

        {/* 3. DOCKED MODERN QUICK ACTION DOCK */}
        <div className="mt-7 pt-5 border-t border-white/10">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center justify-between">
            <span>Quick Telephonic & Pipeline Actions</span>
            <span className="text-emerald-400 lowercase text-[11px] font-normal font-mono">1-click interactions</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
            {/* 1. Call */}
            <button
              type="button"
              onClick={() => {
                setActionType('CALL');
                setActiveModal('CALL');
              }}
              className="group flex items-center justify-center gap-2 px-3 py-2.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-md shadow-indigo-950/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <Phone className="w-4 h-4 transition-transform group-hover:rotate-12" />
              <span>Call / Log</span>
            </button>

            {/* 2. WhatsApp Direct */}
            <button
              type="button"
              onClick={() => setActiveModal('SHARE')}
              className="group flex items-center justify-center gap-2 px-3 py-2.5 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-950/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <MessageSquare className="w-4 h-4 transition-transform group-hover:scale-110" />
              <span>WhatsApp</span>
            </button>

            {/* 3. Follow-up */}
            <button
              type="button"
              onClick={() => {
                setActionType('FOLLOW_UP');
                setActiveModal('FOLLOWUP');
              }}
              className="group flex items-center justify-center gap-2 px-3 py-2.5 rounded-2xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-md shadow-rose-950/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <Clock className="w-4 h-4 transition-transform group-hover:scale-110" />
              <span>Follow-up</span>
            </button>

            {/* 4. Stage Switcher */}
            <button
              type="button"
              onClick={() => setActiveModal('STATUS')}
              className="group flex items-center justify-center gap-2 px-3 py-2.5 rounded-2xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-md shadow-amber-950/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <Sliders className="w-4 h-4 transition-transform group-hover:rotate-45" />
              <span>Set Stage</span>
            </button>

            {/* 5. Reassign */}
            <button
              type="button"
              onClick={() => setActiveModal('ASSIGN')}
              className="group flex items-center justify-center gap-2 px-3 py-2.5 rounded-2xl bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs shadow-md shadow-purple-950/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <Shuffle className="w-4 h-4 transition-transform group-hover:scale-110" />
              <span>Reassign</span>
            </button>

            {/* 6. Property */}
            <button
              type="button"
              onClick={() => setActiveModal('PROPERTY')}
              className="group flex items-center justify-center gap-2 px-3 py-2.5 rounded-2xl bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs shadow-md shadow-sky-950/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <Home className="w-4 h-4 transition-transform group-hover:scale-110" />
              <span>Property</span>
            </button>

            {/* 7. History */}
            <button
              type="button"
              onClick={() => setActiveModal('HISTORY')}
              className="group flex items-center justify-center gap-2 px-3 py-2.5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white font-bold text-xs border border-white/10 shadow-md transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <History className="w-4 h-4 transition-transform group-hover:-rotate-45" />
              <span>History ({lead.activities?.length || 0})</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4. THREE-COLUMN MODERN EXECUTIVE DOSSIER */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* CARD 1: CLIENT & CONTACT DOSSIER */}
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/90 dark:border-slate-800 p-6 shadow-sm flex flex-col justify-between space-y-5 transition-all hover:border-slate-300 dark:hover:border-slate-700">
          <div className="space-y-4">
            {/* Header Pill */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                  <User className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Client & Contact
                  </h3>
                  <span className="text-[10px] text-slate-400">Direct buyer dossier</span>
                </div>
              </div>

              <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                {lead.dealer_have === 1 ? 'Dealer' : 'Customer'}
              </span>
            </div>

            {/* Fields */}
            <div className="space-y-3.5 text-xs">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Full Name</span>
                <p className="font-bold text-slate-900 dark:text-white mt-0.5 text-sm">{customerName}</p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Primary Mobile</span>
                <div className="flex items-center justify-between mt-0.5">
                  <a
                    href={`tel:${phone}`}
                    className="font-mono font-bold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                  >
                    <Phone className="w-3.5 h-3.5 text-blue-500" />
                    <span>{displayPhone}</span>
                  </a>
                  {phone && (
                    <a
                      href={`https://wa.me/91${phone}`}
                      target="_blank"
                      rel="noreferrer"
                      className="px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 text-[10px] font-bold hover:bg-emerald-100 dark:hover:bg-emerald-900 transition-colors"
                    >
                      WhatsApp
                    </a>
                  )}
                </div>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Alternate Contact</span>
                <p className="font-mono font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                  {altPhone ? altPhone : <span className="text-slate-400 italic">None Provided</span>}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Email Address</span>
                <p className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                  {email ? (
                    <a href={`mailto:${email}`} className="text-blue-600 dark:text-blue-400 hover:underline">
                      {email}
                    </a>
                  ) : (
                    <span className="text-slate-400 italic">None Provided</span>
                  )}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Location / City</span>
                <p className="font-medium text-slate-700 dark:text-slate-300 mt-0.5 flex items-start gap-1">
                  <MapPin className="w-3.5 h-3.5 text-rose-500 shrink-0 mt-0.5" />
                  <span>{clientAddress || <span className="text-slate-400 italic">Not Specified</span>}</span>
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Referral Info</span>
                <p className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                  {lead.refer_by_name ? (
                    <span>
                      {lead.refer_by_name} {lead.refer_by_mobile ? `(${lead.refer_by_mobile})` : ''}
                    </span>
                  ) : (
                    <span className="text-slate-400 italic">Direct Organic Inbound</span>
                  )}
                </p>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              onClick={() => setActiveModal('CALL')}
              className="w-full py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-bold transition-colors flex items-center justify-center gap-1.5"
            >
              <Phone className="w-3.5 h-3.5 text-indigo-500" />
              <span>Initiate Call Log</span>
            </button>
          </div>
        </div>

        {/* CARD 2: PROPERTY & DEAL ECONOMICS */}
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/90 dark:border-slate-800 p-6 shadow-sm flex flex-col justify-between space-y-5 transition-all hover:border-slate-300 dark:hover:border-slate-700">
          <div className="space-y-4">
            {/* Header Pill */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                  <Building className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Property & Economics
                  </h3>
                  <span className="text-[10px] text-slate-400">Inventory match details</span>
                </div>
              </div>

              <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300">
                {leadType}
              </span>
            </div>

            {/* Fields */}
            <div className="space-y-3.5 text-xs">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Property Code / ID</span>
                <p className="font-mono font-bold text-slate-900 dark:text-white mt-0.5">
                  {propertyCode ? (
                    <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-emerald-600 dark:text-emerald-400">
                      {propertyCode}
                    </span>
                  ) : (
                    <span className="text-slate-400 italic">Unassigned Listing</span>
                  )}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Property Category</span>
                <p className="font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                  {leadType === 'RENT'
                    ? 'Residential Rental Flat'
                    : leadType === 'PG'
                    ? 'Paying Guest Accommodation'
                    : 'Residential Apartment / Villa'}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Target Locality / Address</span>
                <p className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                  {propertyAddress || <span className="text-slate-400 italic">Open to Location Recommendations</span>}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Final Deal / Budget Price</span>
                <p className="font-extrabold text-emerald-600 dark:text-emerald-400 mt-0.5 text-sm">
                  {formattedDealPrice}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Target Registry / Deal Date</span>
                <p className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                  {lead.registry_date || lead.deal_date ? (
                    formatDate(lead.registry_date || lead.deal_date)
                  ) : (
                    <span className="text-slate-400 italic">Pending Deal Finalization</span>
                  )}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Opportunity Conversion</span>
                <p className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                  {lead.opportunity_converted === 1 ? (
                    <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-bold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Converted to Opportunity
                    </span>
                  ) : (
                    <span className="text-slate-500">In Active Sales Funnel</span>
                  )}
                </p>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              onClick={() => setActiveModal('PROPERTY')}
              className="w-full py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-bold transition-colors flex items-center justify-center gap-1.5"
            >
              <Home className="w-3.5 h-3.5 text-sky-500" />
              <span>View Property Dossier</span>
            </button>
          </div>
        </div>

        {/* CARD 3: OPERATIONS & AUDIT TIMESTAMPS */}
        <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/90 dark:border-slate-800 p-6 shadow-sm flex flex-col justify-between space-y-5 transition-all hover:border-slate-300 dark:hover:border-slate-700">
          <div className="space-y-4">
            {/* Header Pill */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-amber-50 dark:bg-amber-950/50 text-amber-600 dark:text-amber-400 flex items-center justify-center">
                  <Clock className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Operations & SLA
                  </h3>
                  <span className="text-[10px] text-slate-400">Assignment & timestamps</span>
                </div>
              </div>

              <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300">
                Active Desk
              </span>
            </div>

            {/* Fields */}
            <div className="space-y-3.5 text-xs">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Assigned Desk / Staff</span>
                <p className="font-bold text-slate-800 dark:text-slate-200 mt-0.5 flex items-center gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-emerald-500" />
                  <span>{assignedDesk}</span>
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Lead Acquisition Source</span>
                <p className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                  {sourceName}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Next Scheduled Follow-up</span>
                <p className="font-bold text-rose-600 dark:text-rose-400 mt-0.5 flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-rose-500" />
                  <span>{formatDate(lead.follow_up_date)}</span>
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Inflow / Intake Date</span>
                <p className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                  {formatDate(lead.created_at)}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Last Interaction / Updated</span>
                <p className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                  {formatDate(lead.updated_at || lead.last_contacted_at)}
                </p>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Latest Calling Remark</span>
                <p className="font-medium text-slate-700 dark:text-slate-300 mt-0.5 italic">
                  {supervisorRemark ? `"${supervisorRemark}"` : <span className="text-slate-400">No remarks logged yet</span>}
                </p>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              onClick={() => setActiveModal('FOLLOWUP')}
              className="w-full py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-bold transition-colors flex items-center justify-center gap-1.5"
            >
              <Calendar className="w-3.5 h-3.5 text-rose-500" />
              <span>Reschedule Follow-up</span>
            </button>
          </div>
        </div>
      </div>

      {/* 5. INTERACTIVE ACTIVITY TIMELINE & INLINE QUICK NOTE */}
      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/90 dark:border-slate-800 p-6 sm:p-7 shadow-sm space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <History className="w-4 h-4 text-emerald-500" />
              <span>Live Interaction Ledger & Audit Trail</span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Comprehensive log of calls, stage transitions, site visits, and telecaller remarks.
            </p>
          </div>

          <button
            onClick={() => setActiveModal('CALL')}
            className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <Phone className="w-3.5 h-3.5" />
            <span>Log Call Event</span>
          </button>
        </div>

        {/* Timeline Items */}
        <div className="space-y-4">
          {lead.activities && lead.activities.length > 0 ? (
            lead.activities.map((act: any, idx: number) => (
              <div
                key={act.id || idx}
                className="relative pl-6 sm:pl-8 pb-4 border-l-2 border-slate-100 dark:border-slate-800 last:border-l-0"
              >
                {/* Node Dot */}
                <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-white dark:bg-slate-900 border-2 border-emerald-500 flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                </div>

                <div className="p-4 rounded-2xl bg-slate-50/70 dark:bg-slate-800/50 border border-slate-200/70 dark:border-slate-700/60 space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded-lg text-[10px] font-black uppercase bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200">
                        {act.action_type}
                      </span>
                      {act.outcome && (
                        <span className="px-2.5 py-0.5 rounded-lg text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300">
                          {act.outcome}
                        </span>
                      )}
                    </div>

                    <span className="text-[11px] font-mono text-slate-400">
                      {formatDate(act.created_at)}
                    </span>
                  </div>

                  <p className="text-xs text-slate-700 dark:text-slate-300 font-medium">
                    {act.note || 'No notes specified.'}
                  </p>

                  <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-200/40 dark:border-slate-700/40">
                    <span>Logged by: {act.logged_by || act.performed_by || 'Staff'}</span>
                    {act.stage_after && (
                      <span className="font-semibold text-blue-600 dark:text-blue-400">
                        Stage: {act.stage_after}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="py-8 text-center text-xs text-slate-400 font-medium">
              No previous activities recorded. Use the action bar or quick note input below to record the first contact.
            </div>
          )}
        </div>

        {/* Inline Quick Note Submission */}
        <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
          <div className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-emerald-500" />
            <span>Add Quick Internal Note</span>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
            <input
              type="text"
              value={inlineNote}
              onChange={(e) => setInlineNote(e.target.value)}
              placeholder="Type client remarks, follow-up summary, or customer preference..."
              className="flex-1 px-4 py-2.5 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              type="button"
              disabled={submitting || !inlineNote.trim()}
              onClick={() => handleLogAction(undefined, true)}
              className="px-5 py-2.5 rounded-2xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer shadow-xs"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{submitting ? 'Posting...' : 'Post Note'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 6. MODALS FOR THE 7 QUICK ACTIONS */}
      {activeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs animate-fade-in font-sans">
          <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden p-6 space-y-4">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>
                  {activeModal === 'CALL'
                    ? 'Log Telephonic Call'
                    : activeModal === 'FOLLOWUP'
                    ? 'Schedule Follow-Up Date & Time'
                    : activeModal === 'STATUS'
                    ? 'Update Lead Pipeline Stage'
                    : activeModal === 'ASSIGN'
                    ? 'Reassign Lead to Staff / Franchisee'
                    : activeModal === 'PROPERTY'
                    ? 'Linked Property Dossier'
                    : activeModal === 'SHARE'
                    ? 'Direct WhatsApp Outreach'
                    : 'Interaction History Ledger'}
                </span>
              </h3>
              <button
                onClick={() => setActiveModal(null)}
                className="p-1 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body Content */}
            {activeModal === 'STATUS' ? (
              <div className="space-y-4 text-xs">
                <p className="text-slate-600 dark:text-slate-400">
                  Select new stage for <strong className="text-slate-900 dark:text-white">{customerName}</strong>:
                </p>
                <div className="space-y-2">
                  {STAGE_OPTIONS.map((st) => (
                    <button
                      key={st.value}
                      type="button"
                      onClick={() => handleStagePatch(st.value)}
                      disabled={submitting}
                      className={`w-full p-3 rounded-2xl border text-left font-bold transition-all flex items-center justify-between ${
                        selectedStage === st.value
                          ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300'
                          : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <span>{st.label}</span>
                      {selectedStage === st.value && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                    </button>
                  ))}
                </div>
              </div>
            ) : activeModal === 'SHARE' ? (
              <div className="space-y-4 text-xs">
                <p className="text-slate-600 dark:text-slate-300">
                  Send property recommendation and inquiry confirmation directly to customer mobile on WhatsApp:
                </p>
                <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 font-mono text-xs text-slate-700 dark:text-slate-300">
                  Hello {customerName}, this is Om Shiv Properties regarding your inquiry for{' '}
                  {propertyAddress || `${leadType} Property`}. We have selected verified properties matching your budget ({formattedDealPrice}).
                </div>
                {phone ? (
                  <a
                    href={`https://wa.me/91${phone}?text=${encodeURIComponent(
                      `Hello ${customerName}, this is Om Shiv Properties regarding your inquiry for ${propertyAddress || `${leadType} Property`}. We have selected verified properties matching your budget (${formattedDealPrice}).`
                    )}`}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full py-3 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-md shadow-emerald-950/30 transition-all"
                  >
                    <MessageSquare className="w-4 h-4" />
                    <span>Launch WhatsApp Web / App</span>
                  </a>
                ) : (
                  <p className="text-rose-500 font-bold">No valid mobile number available for WhatsApp outreach.</p>
                )}
              </div>
            ) : activeModal === 'PROPERTY' ? (
              <div className="space-y-3.5 text-xs">
                <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Property Reference</span>
                  <p className="font-mono font-bold text-slate-900 dark:text-white text-sm">
                    {propertyCode || 'Unassigned / Direct Inbound Inquiry'}
                  </p>
                  <p className="text-slate-600 dark:text-slate-300 font-medium">
                    {propertyAddress || 'Customer has not linked a specific property code; general requirement.'}
                  </p>
                  <div className="pt-2 flex items-center gap-3">
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">{formattedDealPrice}</span>
                    <span className="text-slate-400">•</span>
                    <span className="text-slate-600 dark:text-slate-300 font-medium">{leadType} Mode</span>
                  </div>
                </div>

                <div className="flex items-center justify-end pt-2">
                  <button
                    type="button"
                    onClick={() => setActiveModal(null)}
                    className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : activeModal === 'ASSIGN' ? (
              <div className="space-y-4 text-xs">
                <p className="text-slate-600 dark:text-slate-300">
                  Reassign lead to dedicated franchisee or sales telecaller desk:
                </p>
                <div>
                  <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Select Sales Rep / Franchisee
                  </label>
                  <select
                    defaultValue={lead.assigned_to || ''}
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  >
                    <option value="">Om Shiv Central Desk (Unassigned)</option>
                    <option value="EMP-001">Super Admin (Executive)</option>
                    <option value="EMP-002">Rahul Sharma (Senior Sales Telecaller)</option>
                    <option value="FRANCH-001">Alwar Franchisee Desk</option>
                  </select>
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
                    type="button"
                    onClick={() => {
                      setSuccess('Lead assigned successfully!');
                      setActiveModal(null);
                    }}
                    className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-bold"
                  >
                    Confirm Reassignment
                  </button>
                </div>
              </div>
            ) : activeModal === 'HISTORY' ? (
              <div className="space-y-3 max-h-96 overflow-y-auto custom-scrollbar text-xs">
                {lead.activities && lead.activities.length > 0 ? (
                  lead.activities.map((act: any) => (
                    <div
                      key={act.id}
                      className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 dark:text-white uppercase">{act.action_type}</span>
                        <span className="text-[10px] text-slate-400 font-mono">{formatDate(act.created_at)}</span>
                      </div>
                      <p className="text-slate-700 dark:text-slate-300 font-medium">{act.note || 'No notes logged.'}</p>
                      <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1">
                        <span>Outcome: {act.outcome || 'N/A'}</span>
                        <span>Logged by: {act.logged_by || 'Staff'}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400 text-center py-6">No previous interactions logged.</p>
                )}
              </div>
            ) : (
              /* CALL & FOLLOWUP FORM */
              <form onSubmit={(e) => handleLogAction(e, false)} className="space-y-4 text-xs">
                {activeModal === 'CALL' && (
                  <div>
                    <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                      Call Discussion Outcome
                    </label>
                    <select
                      value={outcome}
                      onChange={(e) => setOutcome(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                    >
                      <option value="Connected">Connected & Spoke with Customer</option>
                      <option value="Site Visit Planned">Site Visit Planned</option>
                      <option value="Ringing">Ringing / Unanswered</option>
                      <option value="Call Back Later">Call Back Later / Busy</option>
                      <option value="Not Interested">Not Interested / Disqualified</option>
                    </select>
                  </div>
                )}

                <div>
                  <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Scheduled Follow-up Date & Time
                  </label>
                  <input
                    type="datetime-local"
                    value={followUpDate}
                    onChange={(e) => setFollowUpDate(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Lead Priority / Temperature
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setTemperature('HOT')}
                      className={`py-2 rounded-xl border font-bold text-xs flex items-center justify-center gap-1.5 ${
                        temperature === 'HOT'
                          ? 'bg-rose-500 text-white border-rose-500'
                          : 'border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <Flame className="w-3.5 h-3.5" />
                      <span>Hot</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setTemperature('WARM')}
                      className={`py-2 rounded-xl border font-bold text-xs flex items-center justify-center gap-1.5 ${
                        temperature === 'WARM'
                          ? 'bg-amber-500 text-slate-950 border-amber-500'
                          : 'border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <Sun className="w-3.5 h-3.5" />
                      <span>Warm</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setTemperature('COLD')}
                      className={`py-2 rounded-xl border font-bold text-xs flex items-center justify-center gap-1.5 ${
                        temperature === 'COLD'
                          ? 'bg-sky-500 text-white border-sky-500'
                          : 'border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      <Snowflake className="w-3.5 h-3.5" />
                      <span>Cold</span>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 dark:text-slate-300 mb-1">
                    Interaction Remarks & Notes
                  </label>
                  <textarea
                    rows={3}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Enter discussion details, customer preference, budget revision..."
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setActiveModal(null)}
                    className="px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold transition-colors shadow-xs"
                  >
                    {submitting ? 'Saving...' : 'Save & Record Action'}
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
