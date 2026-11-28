import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  ArrowRightLeft,
  Building2,
  CalendarClock,
  CheckCircle2,
  Clock,
  Download,
  History,
  Lock,
  LockOpen,
  MessageSquare,
  Phone,
  PhoneCall,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  SlidersHorizontal,
  Sparkles,
  UserCheck,
  UserPlus,
  X,
} from 'lucide-react';
import {
  AssigneeOption,
  CALLBACK_STATUS_META,
  CallbackDetail,
  CallbackOrderBy,
  CallbackSortBy,
  CallbackSummary,
  CallbackTab,
  CURRENT_UPDATE_OPTIONS,
  DISQUALIFIED_REASONS,
  DashboardCounts,
  authHeaders,
} from '../types/websiteForms';
import ReportProblemPanel from '../components/website-forms/ReportProblemPanel';

type ModalKind =
  | 'reschedule'
  | 'status'
  | 'transfer'
  | 'convert'
  | 'history'
  | 'new_callback'
  | null;

const CALLBACK_TABS: {
  key: CallbackTab;
  label: string;
  countKey: keyof DashboardCounts;
}[] = [
  { key: 'new', label: 'Home / New', countKey: 'new_calls' },
  { key: 'today', label: 'Today Calls', countKey: 'today_calls' },
  { key: 'open', label: 'Open Calls', countKey: 'open_calls' },
  { key: 'missing', label: 'Missing Calls', countKey: 'missing_calls' },
  { key: 'converted', label: 'Converted Lead', countKey: 'converted_leads' },
  { key: 'all', label: 'All Calls', countKey: 'all_calls' },
  { key: 'converted_property', label: 'Converted Property', countKey: 'converted_property' },
];

const CHANGEABLE_STATUS_CODES: number[] = [0, 1, 2, 3, 4, 6];

const EMPTY_COUNTS: DashboardCounts = {
  new_calls: 0,
  today_calls: 0,
  open_calls: 0,
  missing_calls: 0,
  converted_leads: 0,
  all_calls: 0,
  converted_property: 0,
};

function formatDateTime(value?: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

function getDefaultScheduleDateAndTime(): { date: string; time: string } {
  const target = new Date(Date.now() + 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, '0');
  const date = `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}`;
  const time = `${pad(target.getHours())}:${pad(target.getMinutes())}`;
  return { date, time };
}

function getStatusMeta(code: number) {
  return (
    CALLBACK_STATUS_META[code] || {
      code: 0,
      label: 'Unknown',
      badgeClass:
        'bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-500/20',
      dotClass: 'bg-slate-400',
    }
  );
}

export const WebsiteFormsHub: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const modeParam = (searchParams.get('tab') || 'callbacks').toLowerCase();
  const activeMode: 'callbacks' | 'problems' =
    modeParam === 'problems' ? 'problems' : 'callbacks';

  const setMode = (mode: 'callbacks' | 'problems') => {
    setSearchParams({ tab: mode }, { replace: true });
  };

  // Callback filter & sort state
  const [activeTab, setActiveTab] = useState<CallbackTab>('new');
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sortBy, setSortBy] = useState<CallbackSortBy>('created_date');
  const [orderBy, setOrderBy] = useState<CallbackOrderBy>('desc');

  // Data state
  const [counts, setCounts] = useState<DashboardCounts>(EMPTY_COUNTS);
  const [items, setItems] = useState<CallbackSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const selectedIdRef = useRef<number | null>(null);
  const pendingSelectIdRef = useRef<number | null>(null);
  selectedIdRef.current = selectedId;
  const [detail, setDetail] = useState<CallbackDetail | null>(null);
  const [assignees, setAssignees] = useState<AssigneeOption[]>([]);

  // Loading & feedback state
  const [listLoading, setListLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [banner, setBanner] = useState<{
    type: 'success' | 'error';
    text: string;
    leadId?: string;
  } | null>(null);

  // Modal state
  const [modalKind, setModalKind] = useState<ModalKind>(null);
  const [modalError, setModalError] = useState<string | null>(null);

  // 1. Reschedule form state
  const [rsCurrentUpdate, setRsCurrentUpdate] = useState<string>(CURRENT_UPDATE_OPTIONS[0]);
  const [rsRemark, setRsRemark] = useState('');
  const [rsDate, setRsDate] = useState('');
  const [rsTime, setRsTime] = useState('');

  // 2. Change Status form state
  const [stStatus, setStStatus] = useState<number>(1);
  const [stReason, setStReason] = useState<number>(1);
  const [stRemark, setStRemark] = useState('');
  const [stCallConnected, setStCallConnected] = useState(false);

  // 3. Call Transfer form state
  const [trEmployeeId, setTrEmployeeId] = useState('');
  const [trRemark, setTrRemark] = useState('');

  // 4. Convert to Lead form state
  const [cvCustomerType, setCvCustomerType] = useState<'BUY' | 'RENT' | 'PG'>('BUY');
  const [cvName, setCvName] = useState('');
  const [cvEmail, setCvEmail] = useState('');
  const [cvMobile, setCvMobile] = useState('');
  const [cvAlternateMobile, setCvAlternateMobile] = useState('');
  const [cvAddress, setCvAddress] = useState('');
  const [cvReferRelation, setCvReferRelation] = useState('');
  const [cvReferName, setCvReferName] = useState('');
  const [cvReferMobile, setCvReferMobile] = useState('');
  const [cvSource, setCvSource] = useState('Website Callback');
  const [cvAssignee, setCvAssignee] = useState('');

  // 5. History modal sub-filter
  const [historyFilter, setHistoryFilter] = useState<'all' | 'reschedule' | 'activities'>('all');

  // 6. + New Callback modal form state
  const [ncName, setNcName] = useState('');
  const [ncPhoneCode, setNcPhoneCode] = useState('+91');
  const [ncMobile, setNcMobile] = useState('');
  const [ncPropertyCode, setNcPropertyCode] = useState('');
  const [ncAssignee, setNcAssignee] = useState('');
  const [ncMessage, setNcMessage] = useState('');

  // Debounce search input
  useEffect(() => {
    const t = window.setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
    }, 250);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  const parseError = async (res: Response, fallback: string): Promise<string> => {
    const data = await res.json().catch(() => null);
    if (data && typeof data.detail === 'string' && data.detail.trim()) {
      return data.detail;
    }
    if (data && Array.isArray(data.detail) && data.detail.length > 0) {
      return data.detail.map((d: any) => d.msg || String(d)).join(', ');
    }
    return fallback;
  };

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await fetch('/v1/callbacks/dashboard', {
        headers: authHeaders(false),
      });
      if (res.ok) {
        setCounts(await res.json());
      }
    } catch {
      // Non-fatal; list loader surfaces network issues
    }
  }, []);

  const fetchAssignees = useCallback(async () => {
    try {
      const res = await fetch('/v1/callbacks/assignees', {
        headers: authHeaders(false),
      });
      if (res.ok) {
        setAssignees(await res.json());
      }
    } catch {
      // Non-fatal
    }
  }, []);

  const fetchCallbacksList = useCallback(
    async (preferSelectId?: number | null): Promise<CallbackSummary[]> => {
      setListLoading(true);
      try {
        const params = new URLSearchParams({
          tab: activeTab,
          sort_by: sortBy,
          order_by: orderBy,
          limit: '100',
          offset: '0',
        });
        if (debouncedSearch) {
          params.set('search', debouncedSearch);
        }
        const res = await fetch(`/v1/callbacks?${params.toString()}`, {
          headers: authHeaders(false),
        });
        if (!res.ok) {
          throw new Error(await parseError(res, 'Failed to fetch callbacks.'));
        }
        const data = await res.json();
        const fetchedItems: CallbackSummary[] = data.items || [];
        setItems(fetchedItems);
        setTotal(typeof data.total === 'number' ? data.total : fetchedItems.length);

        const pendingId = pendingSelectIdRef.current;
        pendingSelectIdRef.current = null;
        const candidateId =
          preferSelectId !== undefined
            ? preferSelectId
            : pendingId ?? selectedIdRef.current;
        if (
          candidateId &&
          fetchedItems.some((item) => item.callback_id === candidateId)
        ) {
          setSelectedId(candidateId);
        } else if (fetchedItems.length > 0) {
          setSelectedId(fetchedItems[0].callback_id);
        } else {
          setSelectedId(null);
          setDetail(null);
        }
        return fetchedItems;
      } catch (err: any) {
        setBanner({
          type: 'error',
          text: err?.message || 'Unable to load callback queue.',
        });
        return [];
      } finally {
        setListLoading(false);
      }
    },
    [activeTab, sortBy, orderBy, debouncedSearch]
  );

  const fetchCallbackDetail = useCallback(async (callbackId: number) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`/v1/callbacks/${callbackId}`, {
        headers: authHeaders(false),
      });
      if (!res.ok) {
        if (res.status === 403 || res.status === 404) {
          setDetail(null);
          return;
        }
        throw new Error(await parseError(res, 'Failed to load callback details.'));
      }
      setDetail(await res.json());
    } catch (err: any) {
      setBanner({
        type: 'error',
        text: err?.message || 'Failed to load callback details.',
      });
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeMode !== 'callbacks') return;
    fetchDashboard();
    fetchAssignees();
  }, [activeMode, fetchDashboard, fetchAssignees]);

  useEffect(() => {
    if (activeMode !== 'callbacks') return;
    fetchCallbacksList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeMode, activeTab, sortBy, orderBy, debouncedSearch]);

  useEffect(() => {
    if (activeMode !== 'callbacks' || !selectedId) {
      if (!selectedId) setDetail(null);
      return;
    }
    fetchCallbackDetail(selectedId);
  }, [activeMode, selectedId, fetchCallbackDetail]);

  const refreshAll = async (targetId?: number | null) => {
    const [, refreshedList] = await Promise.all([
      fetchDashboard(),
      fetchCallbacksList(targetId),
    ]);
    const idToLoad =
      targetId && refreshedList.some((r) => r.callback_id === targetId)
        ? targetId
        : refreshedList[0]?.callback_id ?? null;
    if (idToLoad) {
      await fetchCallbackDetail(idToLoad);
    }
  };

  // Lock state derived flags
  const isConverted = Boolean(
    detail &&
      (detail.lead_status === 5 ||
        detail.lead_status === 6 ||
        detail.lead_converted === 1)
  );
  const isLocked = Boolean(detail && (detail.lead_open === 0 || isConverted));
  const canReopen = Boolean(
    detail &&
      detail.lead_open === 0 &&
      (detail.lead_status === 2 || detail.lead_status === 3) &&
      detail.lead_converted !== 1
  );

  const lockPill = useMemo(() => {
    if (!detail) return null;
    if (detail.lead_open === 1 && !isConverted) {
      return {
        label: 'Open / Active',
        className:
          'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25',
        icon: LockOpen,
      };
    }
    if (isConverted) {
      return {
        label: 'Converted & Locked',
        className:
          'bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/25',
        icon: Lock,
      };
    }
    return {
      label: 'Closed — Reopen Required',
      className:
        'bg-[#F04B42]/10 text-[#F04B42] dark:text-red-300 border-[#F04B42]/30',
      icon: Lock,
    };
  }, [detail, isConverted]);

  // Combined chronological timeline for History modal
  const combinedTimeline = useMemo(() => {
    if (!detail) return [];
    const entries: Array<{
      id: string;
      kind: 'reschedule' | 'activity';
      created_at: string;
      title: string;
      subtitle?: string;
      remark?: string | null;
      actor?: string | null;
      oldDt?: string | null;
      newDt?: string | null;
      statusBefore?: number | null;
      statusAfter?: number | null;
    }> = [];

    if (historyFilter === 'all' || historyFilter === 'reschedule') {
      for (const r of detail.reschedule_history || []) {
        entries.push({
          id: `rs-${r.id}`,
          kind: 'reschedule',
          created_at: r.created_at,
          title: `Follow-Up Rescheduled${r.current_update ? ` • ${r.current_update}` : ''}`,
          remark: r.remark,
          actor: r.rescheduled_by_name || r.rescheduled_by,
          oldDt: r.old_followup_datetime,
          newDt: r.new_followup_datetime,
        });
      }
    }

    if (historyFilter === 'all' || historyFilter === 'activities') {
      for (const a of detail.activities || []) {
        entries.push({
          id: `act-${a.id}`,
          kind: 'activity',
          created_at: a.created_at,
          title: a.title,
          subtitle: a.action_type,
          remark: a.remark,
          actor: a.performed_by_name || a.performed_by,
          statusBefore: a.status_before,
          statusAfter: a.status_after,
        });
      }
    }

    return entries.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [detail, historyFilter]);

  // --- Action Handlers ---

  const handleExportXls = async () => {
    setExporting(true);
    setBanner(null);
    try {
      const params = new URLSearchParams({
        tab: activeTab,
        sort_by: sortBy,
        order_by: orderBy,
      });
      if (debouncedSearch) {
        params.set('search', debouncedSearch);
      }
      const res = await fetch(`/v1/callbacks/export?${params.toString()}`, {
        headers: authHeaders(false),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to export callbacks.'));
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `callbacks_${activeTab}.xls`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setBanner({
        type: 'error',
        text: err?.message || 'Excel export failed.',
      });
    } finally {
      setExporting(false);
    }
  };

  const handleLogCall = async () => {
    if (!detail) return;
    setSubmitting(true);
    setBanner(null);
    try {
      const res = await fetch(`/v1/callbacks/${detail.callback_id}/log-call`, {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({ remark: 'Call logged from Website Forms workspace' }),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to log call.'));
      }
      setBanner({
        type: 'success',
        text: `Call logged for ${detail.lead_unique_id || detail.name}.`,
      });
      await refreshAll(detail.callback_id);
      const dialNumber = `${detail.phone_code || '+91'}${detail.mobile_number}`.replace(/\s+/g, '');
      window.location.href = `tel:${dialNumber}`;
    } catch (err: any) {
      setBanner({
        type: 'error',
        text: err?.message || 'Could not log call.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReopen = async () => {
    if (!detail || !canReopen) return;
    setSubmitting(true);
    setBanner(null);
    try {
      const res = await fetch(`/v1/callbacks/${detail.callback_id}/reopen`, {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({ remark: 'Reopened for follow-up' }),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to reopen callback.'));
      }
      setBanner({
        type: 'success',
        text: `${detail.lead_unique_id || 'Callback'} reopened and moved to In Progress.`,
      });
      await refreshAll(detail.callback_id);
    } catch (err: any) {
      setBanner({
        type: 'error',
        text: err?.message || 'Could not reopen callback.',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const openRescheduleModal = () => {
    if (!detail || isLocked) return;
    const { date, time } = getDefaultScheduleDateAndTime();
    setRsCurrentUpdate(
      detail.current_update && CURRENT_UPDATE_OPTIONS.includes(detail.current_update)
        ? detail.current_update
        : CURRENT_UPDATE_OPTIONS[0]
    );
    setRsRemark('');
    setRsDate(date);
    setRsTime(time);
    setModalError(null);
    setModalKind('reschedule');
  };

  const openChangeStatusModal = () => {
    if (!detail || isLocked) return;
    const safeStatus = detail.lead_status === 5 ? 1 : detail.lead_status;
    setStStatus(safeStatus);
    setStReason(detail.disqualified_reason >= 1 ? detail.disqualified_reason : 1);
    setStRemark('');
    setStCallConnected(detail.calls_status === 1);
    setModalError(null);
    setModalKind('status');
  };

  const openTransferModal = () => {
    if (!detail || isLocked) return;
    const defaultTarget =
      assignees.find((a) => a.employee_id !== detail.assigned_user_id)?.employee_id ||
      assignees[0]?.employee_id ||
      '';
    setTrEmployeeId(defaultTarget);
    setTrRemark('');
    setModalError(null);
    setModalKind('transfer');
  };

  const openConvertModal = () => {
    if (!detail || isLocked) return;
    setCvCustomerType('BUY');
    setCvName(detail.name || '');
    setCvEmail('');
    setCvMobile(detail.mobile_number || '');
    setCvAlternateMobile('');
    setCvAddress('');
    setCvReferRelation('');
    setCvReferName('');
    setCvReferMobile('');
    setCvSource('Website Callback');
    setCvAssignee(detail.assigned_user_id || assignees[0]?.employee_id || '');
    setModalError(null);
    setModalKind('convert');
  };

  const openNewCallbackModal = () => {
    setNcName('');
    setNcPhoneCode('+91');
    setNcMobile('');
    setNcPropertyCode('');
    setNcAssignee('');
    setNcMessage('');
    setModalError(null);
    setModalKind('new_callback');
  };

  const handleSubmitReschedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    setModalError(null);

    const remarkClean = rsRemark.trim();
    if (!remarkClean) {
      setModalError('Remark is required.');
      return;
    }
    if (!rsDate || !rsTime) {
      setModalError('Schedule Date and Time are required.');
      return;
    }
    const combined = new Date(`${rsDate}T${rsTime}:00`);
    if (Number.isNaN(combined.getTime()) || combined.getTime() <= Date.now()) {
      setModalError('Schedule Date and Time should be greater than the current date and time.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`/v1/callbacks/${detail.callback_id}/reschedule`, {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({
          current_update: rsCurrentUpdate,
          remark: remarkClean,
          followup_datetime: combined.toISOString(),
        }),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to reschedule follow-up.'));
      }
      setModalKind(null);
      setBanner({
        type: 'success',
        text: `Follow-up scheduled for ${formatDateTime(combined.toISOString())}.`,
      });
      await refreshAll(detail.callback_id);
    } catch (err: any) {
      setModalError(err?.message || 'Failed to reschedule follow-up.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    setModalError(null);

    const remarkClean = stRemark.trim();
    if (!remarkClean) {
      setModalError('Remark is required when changing callback status.');
      return;
    }
    if (stStatus === 2 && (!stReason || stReason < 1 || stReason > 7)) {
      setModalError('Please select a Disqualification Reason.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`/v1/callbacks/${detail.callback_id}/status`, {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({
          lead_status: stStatus,
          remark: remarkClean,
          disqualified_reason: stStatus === 2 ? stReason : undefined,
          calls_status: stCallConnected ? 1 : undefined,
        }),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to update callback status.'));
      }
      setModalKind(null);
      setBanner({
        type: 'success',
        text: `Status updated to ${getStatusMeta(stStatus).label}.`,
      });
      await refreshAll(detail.callback_id);
    } catch (err: any) {
      setModalError(err?.message || 'Failed to update status.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    setModalError(null);

    if (!trEmployeeId) {
      setModalError('Please select an employee to transfer to.');
      return;
    }
    const remarkClean = trRemark.trim();
    if (!remarkClean) {
      setModalError('Transfer remark is required.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`/v1/callbacks/${detail.callback_id}/transfer`, {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({
          assigned_user_id: trEmployeeId,
          remark: remarkClean,
        }),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to transfer callback.'));
      }
      setModalKind(null);
      const emp = assignees.find((a) => a.employee_id === trEmployeeId);
      setBanner({
        type: 'success',
        text: `Callback transferred to ${emp?.name || trEmployeeId} and reset to New.`,
      });
      await refreshAll(detail.callback_id);
    } catch (err: any) {
      setModalError(err?.message || 'Failed to transfer callback.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitConvert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    setModalError(null);

    if (!cvName.trim() || !cvMobile.trim() || !cvAddress.trim() || !cvSource.trim()) {
      setModalError('Customer Type, Name, Mobile, Address, and Source are required.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`/v1/callbacks/${detail.callback_id}/convert-to-lead`, {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({
          customer_type: cvCustomerType,
          name: cvName.trim(),
          email: cvEmail.trim() || null,
          mobile: cvMobile.trim(),
          alternate_mobile: cvAlternateMobile.trim() || null,
          address: cvAddress.trim(),
          refer_by_relation: cvReferRelation.trim() || null,
          refer_by_name: cvReferName.trim() || null,
          refer_by_mobile: cvReferMobile.trim() || null,
          source: cvSource.trim() || 'Website Callback',
          assigned_to: cvAssignee || null,
        }),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to convert callback to lead.'));
      }
      const data = await res.json();
      setModalKind(null);
      setBanner({
        type: 'success',
        text: `Callback converted to Lead ${data.lead_id}.`,
        leadId: data.lead_id,
      });
      await refreshAll(detail.callback_id);
    } catch (err: any) {
      setModalError(err?.message || 'Conversion failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitNewCallback = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    if (!ncName.trim() || !ncMobile.trim()) {
      setModalError('Customer name and mobile number are required.');
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch('/v1/callbacks', {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({
          name: ncName.trim(),
          phone_code: ncPhoneCode.trim() || '+91',
          mobile_number: ncMobile.trim(),
          property_code: ncPropertyCode.trim() || null,
          assigned_user_id: ncAssignee || null,
          message: ncMessage.trim() || null,
        }),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to create callback.'));
      }
      const created: CallbackDetail = await res.json();
      setModalKind(null);
      setBanner({
        type: 'success',
        text: `Created callback ${created.lead_unique_id || `#${created.callback_id}`}.`,
      });
      if (activeTab !== 'new' && activeTab !== 'open' && activeTab !== 'all') {
        pendingSelectIdRef.current = created.callback_id;
        setActiveTab('new');
        await fetchDashboard();
      } else {
        await refreshAll(created.callback_id);
      }
    } catch (err: any) {
      setModalError(err?.message || 'Failed to create callback.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Header & Mode Switcher */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
                  Website Forms Hub
                </h1>
                <span className="px-2.5 py-0.5 text-[11px] font-semibold rounded-full bg-[#291BB0]/10 text-[#291BB0] dark:bg-indigo-500/20 dark:text-indigo-300 border border-[#291BB0]/20">
                  Inbound CRM
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Manage website callback requests, follow-up schedules, telecaller handoffs, and problem reports.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Mode Switcher Pills */}
            <div className="inline-flex rounded-xl bg-slate-100 dark:bg-slate-800 p-1 border border-slate-200 dark:border-slate-700">
              <button
                type="button"
                onClick={() => setMode('callbacks')}
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                  activeMode === 'callbacks'
                    ? 'bg-[#291BB0] hover:bg-[#1f138e] text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <PhoneCall className="w-3.5 h-3.5" />
                Request A Callback
              </button>
              <button
                type="button"
                onClick={() => setMode('problems')}
                className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                  activeMode === 'problems'
                    ? 'bg-[#291BB0] hover:bg-[#1f138e] text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                Report A Problem
              </button>
            </div>

            {activeMode === 'callbacks' && (
              <>
                <button
                  type="button"
                  onClick={openNewCallbackModal}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  + New Callback
                </button>
                <button
                  type="button"
                  onClick={handleExportXls}
                  disabled={exporting}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors disabled:opacity-60 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5 text-[#291BB0] dark:text-indigo-400" />
                  {exporting ? 'Exporting...' : 'Export .xls'}
                </button>
                <button
                  type="button"
                  onClick={() => refreshAll(selectedId)}
                  title="Refresh"
                  className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
                >
                  <RefreshCw className={`w-4 h-4 ${listLoading ? 'animate-spin' : ''}`} />
                </button>
              </>
            )}
          </div>
        </div>

        {/* 7 Callback Filter Tabs with Live Counters */}
        {activeMode === 'callbacks' && (
          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex flex-wrap gap-2">
            {CALLBACK_TABS.map((t) => {
              const isActive = activeTab === t.key;
              const count = counts[t.countKey] ?? 0;
              const isMissingAlert = t.key === 'missing' && count > 0 && !isActive;
              return (
                <button
                  key={t.key}
                  type="button"
                  onClick={() => setActiveTab(t.key)}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                    isActive
                      ? 'bg-[#291BB0] hover:bg-[#1f138e] text-white border-[#291BB0] shadow-sm'
                      : 'bg-slate-50 dark:bg-slate-800/70 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-[#291BB0]/40'
                  }`}
                >
                  <span>{t.label}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded-md text-[11px] font-bold ${
                      isActive
                        ? 'bg-white/20 text-white'
                        : isMissingAlert
                        ? 'bg-[#F04B42] text-white'
                        : 'bg-slate-200/80 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Feedback Banner */}
      {banner && (
        <div
          className={`flex items-center justify-between gap-3 px-4 py-3 rounded-xl border text-xs font-medium ${
            banner.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
              : 'bg-[#F04B42]/10 border-[#F04B42]/30 text-[#F04B42] dark:text-red-300'
          }`}
        >
          <div className="flex items-center gap-2 flex-wrap">
            {banner.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{banner.text}</span>
            {banner.leadId && (
              <Link
                to={`/leads/${banner.leadId}`}
                className="inline-flex items-center gap-1 underline font-bold hover:opacity-80"
              >
                Open Lead {banner.leadId}
                <ArrowRight className="w-3 h-3" />
              </Link>
            )}
          </div>
          <button
            type="button"
            onClick={() => setBanner(null)}
            className="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Mode Content */}
      {activeMode === 'problems' ? (
        <ReportProblemPanel assignees={assignees} />
      ) : (
        <div className="flex flex-col lg:flex-row gap-4 items-start">
          {/* LEFT PANEL (~360px): Search, Sort, Order, Callback Cards */}
          <div className="w-full lg:w-[360px] shrink-0 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col max-h-[calc(100vh-230px)]">
            <div className="p-3 border-b border-slate-100 dark:border-slate-800 space-y-2.5 bg-slate-50/70 dark:bg-slate-900">
              <div className="relative">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search name, mobile, WEB ID, property..."
                  className="w-full pl-9 pr-8 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30 focus:border-[#291BB0]"
                />
                {searchInput && (
                  <button
                    type="button"
                    onClick={() => setSearchInput('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="flex items-center gap-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-2.5 py-1.5">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <select
                    aria-label="Sort By"
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as CallbackSortBy)}
                    className="w-full bg-transparent text-[11px] font-medium text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
                  >
                    <option value="created_date">Created Date</option>
                    <option value="followup_datetime">Follow-up Date</option>
                    <option value="name">Name</option>
                  </select>
                </div>

                <select
                  aria-label="Order By"
                  value={orderBy}
                  onChange={(e) => setOrderBy(e.target.value as CallbackOrderBy)}
                  className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-2.5 py-1.5 text-[11px] font-medium text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
                >
                  <option value="desc">Order: DESC</option>
                  <option value="asc">Order: ASC</option>
                </select>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 px-0.5">
                <span>
                  Showing <strong className="text-slate-700 dark:text-slate-200">{items.length}</strong> of{' '}
                  <strong className="text-slate-700 dark:text-slate-200">{total}</strong>
                </span>
                <span className="uppercase tracking-wider font-semibold text-[10px] text-[#291BB0] dark:text-indigo-400">
                  {CALLBACK_TABS.find((t) => t.key === activeTab)?.label}
                </span>
              </div>
            </div>

            <div className="overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800 flex-1">
              {listLoading && items.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500 dark:text-slate-400">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#291BB0]" />
                  Loading callbacks...
                </div>
              ) : items.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500 dark:text-slate-400">
                  No callbacks match this filter.
                </div>
              ) : (
                items.map((item) => {
                  const isSelected = item.callback_id === selectedId;
                  const statusMeta = getStatusMeta(item.lead_status);
                  const webId = item.lead_unique_id || `WEB${item.callback_id}`;
                  return (
                    <button
                      key={item.callback_id}
                      type="button"
                      onClick={() => setSelectedId(item.callback_id)}
                      className={`w-full text-left p-3.5 transition-colors cursor-pointer border-l-4 ${
                        isSelected
                          ? 'bg-[#291BB0]/5 dark:bg-indigo-950/30 border-l-[#291BB0]'
                          : 'bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 border-l-transparent'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-sm text-slate-900 dark:text-white truncate">
                              {item.name}
                            </span>
                            {item.lead_open === 0 && (
                              <Lock className="w-3 h-3 text-[#F04B42] shrink-0" />
                            )}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                            <span className="font-mono font-semibold text-[#291BB0] dark:text-indigo-300">
                              {webId}
                            </span>
                            <span>•</span>
                            <span>
                              {item.phone_code || '+91'}-{item.mobile_number}
                            </span>
                          </div>
                        </div>

                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0 ${statusMeta.badgeClass}`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${statusMeta.dotClass}`} />
                          {statusMeta.label}
                        </span>
                      </div>

                      <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                        <span className="truncate">
                          Caller:{' '}
                          <span className="font-medium text-slate-700 dark:text-slate-300">
                            {item.assigned_user_name || item.assigned_user_id || 'Unassigned'}
                          </span>
                        </span>
                        <span className="shrink-0">{formatDateTime(item.created_date)}</span>
                      </div>

                      {item.followup_datetime && (
                        <div className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-medium text-amber-700 dark:text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded-md">
                          <Clock className="w-3 h-3" />
                          Follow-up: {formatDateTime(item.followup_datetime)}
                        </div>
                      )}
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* RIGHT PANEL: Detail Header, Circular Action Buttons, Contact Details, Others */}
          <div className="flex-1 min-w-0 w-full space-y-4">
            {detailLoading && !detail ? (
              <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-12 text-center shadow-sm">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-[#291BB0]" />
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Loading callback details...
                </p>
              </div>
            ) : !detail ? (
              <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-12 text-center shadow-sm">
                <PhoneCall className="w-8 h-8 mx-auto mb-2 text-slate-300 dark:text-slate-600" />
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                  Select a callback from the list
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  View caller details, log calls, reschedule follow-ups, transfer, or convert to a lead.
                </p>
              </div>
            ) : (
              <>
                {/* Detail Header + Lock Pill + 6 Circular Action Buttons */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm">
                  <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                          {detail.name}
                        </h2>
                        <span className="px-2.5 py-0.5 rounded-lg bg-[#291BB0]/10 text-[#291BB0] dark:bg-indigo-500/20 dark:text-indigo-300 font-mono text-xs font-bold">
                          {detail.lead_unique_id || `WEB${detail.callback_id}`}
                        </span>
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                            getStatusMeta(detail.lead_status).badgeClass
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              getStatusMeta(detail.lead_status).dotClass
                            }`}
                          />
                          {getStatusMeta(detail.lead_status).label}
                        </span>
                        {lockPill && (
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${lockPill.className}`}
                          >
                            <lockPill.icon className="w-3 h-3" />
                            {lockPill.label}
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 dark:text-slate-300">
                        <a
                          href={`tel:${(detail.phone_code || '+91').replace(/\s+/g, '')}${detail.mobile_number}`}
                          className="inline-flex items-center gap-1.5 font-semibold text-[#291BB0] dark:text-indigo-300 hover:underline"
                        >
                          <Phone className="w-3.5 h-3.5" />
                          {detail.phone_code || '+91'}-{detail.mobile_number}
                        </a>
                        <span className="text-slate-300 dark:text-slate-700">|</span>
                        <span
                          className={`inline-flex items-center gap-1 font-medium ${
                            detail.calls_status === 1
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-slate-500 dark:text-slate-400'
                          }`}
                        >
                          <PhoneCall className="w-3.5 h-3.5" />
                          {detail.calls_status === 1 ? 'Call Connected' : 'Not Called Yet'}
                        </span>
                      </div>
                    </div>

                    {/* Explicit CTAs alongside 6 circular action buttons */}
                    <div className="flex flex-wrap items-center gap-2">
                      {canReopen ? (
                        <button
                          type="button"
                          onClick={handleReopen}
                          disabled={submitting}
                          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#F04B42] hover:bg-[#d93b32] text-white text-xs font-bold shadow-sm transition-colors disabled:opacity-60 cursor-pointer"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          Reopen Lead
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={openChangeStatusModal}
                          disabled={isLocked}
                          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white text-xs font-semibold shadow-sm transition-colors disabled:opacity-45 disabled:cursor-not-allowed cursor-pointer"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          Change Status
                        </button>
                      )}
                    </div>
                  </div>

                  {/* 6 Circular Quick-Action Buttons */}
                  <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center gap-4">
                    {/* 1. Call / Log */}
                    <button
                      type="button"
                      onClick={handleLogCall}
                      disabled={submitting}
                      title="Call & Log Connection"
                      className="group flex flex-col items-center gap-1.5 cursor-pointer disabled:opacity-50"
                    >
                      <span className="w-11 h-11 rounded-full flex items-center justify-center bg-[#291BB0] group-hover:bg-[#1f138e] text-white shadow-sm transition-transform group-hover:scale-105">
                        <Phone className="w-4 h-4" />
                      </span>
                      <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        Call / Log
                      </span>
                    </button>

                    {/* 2. Reschedule Follow-Up */}
                    <button
                      type="button"
                      onClick={openRescheduleModal}
                      disabled={isLocked}
                      title={
                        isLocked
                          ? 'Locked — Reopen callback to reschedule'
                          : 'Reschedule Follow-Up'
                      }
                      className="group flex flex-col items-center gap-1.5 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <span className="w-11 h-11 rounded-full flex items-center justify-center bg-sky-500/15 text-sky-700 dark:text-sky-300 border border-sky-500/30 group-hover:bg-sky-500 group-hover:text-white transition-all">
                        <CalendarClock className="w-4 h-4" />
                      </span>
                      <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        Reschedule
                      </span>
                    </button>

                    {/* 3. Reopen / Status Lock */}
                    <button
                      type="button"
                      onClick={canReopen ? handleReopen : openChangeStatusModal}
                      disabled={isConverted || submitting}
                      title={
                        canReopen
                          ? 'Reopen Closed Callback'
                          : isConverted
                          ? 'Converted callback is permanently locked'
                          : 'Change Status / Lock'
                      }
                      className="group flex flex-col items-center gap-1.5 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <span
                        className={`w-11 h-11 rounded-full flex items-center justify-center border transition-all ${
                          canReopen
                            ? 'bg-[#F04B42] text-white border-[#F04B42] group-hover:bg-[#d93b32]'
                            : 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30 group-hover:bg-amber-500 group-hover:text-white'
                        }`}
                      >
                        {canReopen ? (
                          <LockOpen className="w-4 h-4" />
                        ) : (
                          <Lock className="w-4 h-4" />
                        )}
                      </span>
                      <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        {canReopen ? 'Reopen' : 'Status Lock'}
                      </span>
                    </button>

                    {/* 4. Call Transfer */}
                    <button
                      type="button"
                      onClick={openTransferModal}
                      disabled={isLocked}
                      title={
                        isLocked
                          ? 'Locked — Reopen callback to transfer'
                          : 'Transfer Callback to Employee'
                      }
                      className="group flex flex-col items-center gap-1.5 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <span className="w-11 h-11 rounded-full flex items-center justify-center bg-indigo-500/15 text-[#291BB0] dark:text-indigo-300 border border-[#291BB0]/30 group-hover:bg-[#291BB0] group-hover:text-white transition-all">
                        <ArrowRightLeft className="w-4 h-4" />
                      </span>
                      <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        Transfer
                      </span>
                    </button>

                    {/* 5. Convert to Lead */}
                    <button
                      type="button"
                      onClick={openConvertModal}
                      disabled={isLocked}
                      title={
                        isLocked
                          ? 'Locked / Already converted'
                          : 'Convert Callback to Lead'
                      }
                      className="group flex flex-col items-center gap-1.5 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <span className="w-11 h-11 rounded-full flex items-center justify-center bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 group-hover:bg-emerald-600 group-hover:text-white transition-all">
                        <UserPlus className="w-4 h-4" />
                      </span>
                      <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        Convert Lead
                      </span>
                    </button>

                    {/* 6. Activity & Reschedule History */}
                    <button
                      type="button"
                      onClick={() => {
                        setHistoryFilter('all');
                        setModalError(null);
                        setModalKind('history');
                      }}
                      title="View Activity & Reschedule History"
                      className="group flex flex-col items-center gap-1.5 cursor-pointer"
                    >
                      <span className="w-11 h-11 rounded-full flex items-center justify-center bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 group-hover:bg-slate-700 group-hover:text-white transition-all">
                        <History className="w-4 h-4" />
                      </span>
                      <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                        History ({(detail.activities?.length || 0) + (detail.reschedule_history?.length || 0)})
                      </span>
                    </button>
                  </div>

                  {isLocked && (
                    <div
                      className={`mt-4 px-3.5 py-2.5 rounded-xl border text-xs flex items-center justify-between gap-2 ${
                        isConverted
                          ? 'bg-purple-500/5 border-purple-500/20 text-purple-800 dark:text-purple-200'
                          : 'bg-[#F04B42]/5 border-[#F04B42]/25 text-[#F04B42] dark:text-red-300'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Lock className="w-4 h-4 shrink-0" />
                        <span>
                          {isConverted
                            ? 'This callback is terminally converted and permanently locked.'
                            : 'This callback is closed. Reschedule, Transfer, Status Change, and Convert are disabled until reopened.'}
                        </span>
                      </div>
                      {canReopen && (
                        <button
                          type="button"
                          onClick={handleReopen}
                          disabled={submitting}
                          className="px-2.5 py-1 rounded-lg bg-[#F04B42] hover:bg-[#d93b32] text-white font-semibold shrink-0 cursor-pointer"
                        >
                          Reopen Now
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Detail Cards Grid: Contact Details & Others */}
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                  {/* Contact Details Card */}
                  <div className="xl:col-span-2 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <MessageSquare className="w-4 h-4 text-[#291BB0] dark:text-indigo-400" />
                        Contact Details
                      </h3>
                      <span className="text-[11px] text-slate-400">
                        Modified {formatDateTime(detail.modified_date)}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                      <div className="sm:col-span-2 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                          Follow Up Remark
                        </div>
                        <div className="mt-1 text-slate-800 dark:text-slate-100 font-medium">
                          {detail.last_remark || 'No follow-up remark recorded yet.'}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Request ID
                        </div>
                        <div className="mt-0.5 font-mono font-bold text-[#291BB0] dark:text-indigo-300">
                          {detail.lead_unique_id || `WEB${detail.callback_id}`}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Customer Name
                        </div>
                        <div className="mt-0.5 font-semibold text-slate-900 dark:text-white">
                          {detail.name}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Mobile No.
                        </div>
                        <div className="mt-0.5 font-semibold text-slate-900 dark:text-white">
                          {detail.phone_code || '+91'}-{detail.mobile_number}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Current Update
                        </div>
                        <div className="mt-0.5 font-medium text-slate-800 dark:text-slate-200">
                          {detail.current_update || '—'}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Status
                        </div>
                        <div className="mt-0.5 font-semibold text-slate-800 dark:text-slate-200">
                          {getStatusMeta(detail.lead_status).label}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Disqualification Reason
                        </div>
                        <div className="mt-0.5 font-medium text-slate-800 dark:text-slate-200">
                          {detail.disqualified_reason
                            ? detail.disqualified_reason_label ||
                              DISQUALIFIED_REASONS[detail.disqualified_reason] ||
                              `Reason #${detail.disqualified_reason}`
                            : '—'}
                        </div>
                      </div>

                      <div className="sm:col-span-2">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Message
                        </div>
                        <div className="mt-1 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 text-slate-700 dark:text-slate-200 whitespace-pre-wrap">
                          {detail.message || 'No message provided by visitor.'}
                        </div>
                      </div>

                      <div className="sm:col-span-2">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Linked Property
                        </div>
                        <div className="mt-1 flex items-center gap-2 text-slate-800 dark:text-slate-200">
                          <Building2 className="w-4 h-4 text-[#291BB0] dark:text-indigo-400 shrink-0" />
                          {detail.property_code || detail.property_title || detail.property_id ? (
                            <span>
                              {detail.property_code ? (
                                <strong className="font-mono">{detail.property_code}</strong>
                              ) : (
                                `Property #${detail.property_id}`
                              )}
                              {detail.property_title ? ` — ${detail.property_title}` : ''}
                            </span>
                          ) : (
                            <span className="text-slate-400">General Website Inquiry</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Others Card */}
                  <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <UserCheck className="w-4 h-4 text-[#291BB0] dark:text-indigo-400" />
                      Others
                    </h3>

                    <div className="space-y-3.5 text-xs">
                      <div>
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Receive Date
                        </div>
                        <div className="mt-0.5 font-medium text-slate-800 dark:text-slate-200">
                          {formatDateTime(detail.created_date)}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Followup Date
                        </div>
                        <div className="mt-0.5 font-semibold text-slate-900 dark:text-white">
                          {formatDateTime(detail.followup_datetime)}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Assigned Telecaller
                        </div>
                        <div className="mt-0.5 font-semibold text-slate-900 dark:text-white">
                          {detail.assigned_user_name || detail.assigned_user_id || 'Unassigned'}
                        </div>
                        {detail.assigned_user_id && detail.assigned_user_name && (
                          <div className="text-[11px] font-mono text-slate-400">
                            {detail.assigned_user_id}
                          </div>
                        )}
                      </div>

                      <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                        <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                          Converted Lead ID
                        </div>
                        {detail.converted_lead_id ? (
                          <Link
                            to={`/leads/${detail.converted_lead_id}`}
                            className="mt-1 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#291BB0]/10 text-[#291BB0] dark:bg-indigo-500/20 dark:text-indigo-300 font-mono font-bold hover:underline"
                          >
                            {detail.converted_lead_id}
                            <ArrowRight className="w-3 h-3" />
                          </Link>
                        ) : (
                          <div className="mt-0.5 text-slate-400">Not converted</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ==================== MODALS ==================== */}
      {modalKind && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div
            className={`w-full bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden ${
              modalKind === 'convert' || modalKind === 'history'
                ? 'max-w-2xl'
                : 'max-w-md'
            }`}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  {modalKind === 'reschedule' && 'Reschedule Follow-Up'}
                  {modalKind === 'status' && 'Change Callback Status'}
                  {modalKind === 'transfer' && 'Call Transfer'}
                  {modalKind === 'convert' && 'Convert Callback to Lead'}
                  {modalKind === 'history' && 'Activity & Reschedule History'}
                  {modalKind === 'new_callback' && 'New Callback Request'}
                </h3>
                {detail && modalKind !== 'new_callback' && (
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                    {detail.lead_unique_id || `WEB${detail.callback_id}`} • {detail.name}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setModalKind(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 max-h-[80vh] overflow-y-auto">
              {modalError && (
                <div className="mb-4 px-3 py-2.5 rounded-xl bg-[#F04B42]/10 border border-[#F04B42]/30 text-[#F04B42] dark:text-red-300 text-xs font-medium flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{modalError}</span>
                </div>
              )}

              {/* 1. Reschedule Follow-Up Modal */}
              {modalKind === 'reschedule' && (
                <form onSubmit={handleSubmitReschedule} className="space-y-3.5 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                      Current Update <span className="text-[#F04B42]">*</span>
                    </label>
                    <select
                      required
                      value={rsCurrentUpdate}
                      onChange={(e) => setRsCurrentUpdate(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                    >
                      {CURRENT_UPDATE_OPTIONS.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Schedule Date <span className="text-[#F04B42]">*</span>
                      </label>
                      <input
                        type="date"
                        required
                        value={rsDate}
                        onChange={(e) => setRsDate(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Schedule Time <span className="text-[#F04B42]">*</span>
                      </label>
                      <input
                        type="time"
                        required
                        value={rsTime}
                        onChange={(e) => setRsTime(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                      Remark <span className="text-[#F04B42]">*</span>
                    </label>
                    <textarea
                      required
                      rows={3}
                      value={rsRemark}
                      onChange={(e) => setRsRemark(e.target.value)}
                      placeholder="Enter discussion notes and next follow-up context..."
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setModalKind(null)}
                      className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-semibold cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-4 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white font-semibold disabled:opacity-60 cursor-pointer"
                    >
                      {submitting ? 'Saving...' : 'Save Schedule'}
                    </button>
                  </div>
                </form>
              )}

              {/* 2. Change Status Modal */}
              {modalKind === 'status' && (
                <form onSubmit={handleSubmitStatus} className="space-y-3.5 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                      Status <span className="text-[#F04B42]">*</span>
                    </label>
                    <select
                      required
                      value={stStatus}
                      onChange={(e) => setStStatus(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                    >
                      {CHANGEABLE_STATUS_CODES.map((code) => (
                        <option key={code} value={code}>
                          {getStatusMeta(code).label}
                        </option>
                      ))}
                    </select>
                    {(stStatus === 2 || stStatus === 3 || stStatus === 6) && (
                      <p className="mt-1.5 text-[11px] text-[#F04B42] font-medium">
                        {stStatus === 6
                          ? 'Setting Converted Property permanently locks this callback.'
                          : `Setting ${getStatusMeta(stStatus).label} will close and lock this callback until reopened.`}
                      </p>
                    )}
                  </div>

                  {stStatus === 2 && (
                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Disqualification Reason <span className="text-[#F04B42]">*</span>
                      </label>
                      <select
                        required
                        value={stReason}
                        onChange={(e) => setStReason(Number(e.target.value))}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                      >
                        {Object.entries(DISQUALIFIED_REASONS).map(([code, label]) => (
                          <option key={code} value={Number(code)}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                      Remark <span className="text-[#F04B42]">*</span>
                    </label>
                    <textarea
                      required
                      rows={3}
                      value={stRemark}
                      onChange={(e) => setStRemark(e.target.value)}
                      placeholder="Explain reason for status change..."
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                    />
                  </div>

                  <label className="flex items-center gap-2 text-slate-700 dark:text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={stCallConnected}
                      onChange={(e) => setStCallConnected(e.target.checked)}
                      className="rounded border-slate-300 text-[#291BB0] focus:ring-[#291BB0]"
                    />
                    <span>Mark call as connected</span>
                  </label>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setModalKind(null)}
                      className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-semibold cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-4 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white font-semibold disabled:opacity-60 cursor-pointer"
                    >
                      {submitting ? 'Updating...' : 'Update Status'}
                    </button>
                  </div>
                </form>
              )}

              {/* 3. Call Transfer Modal */}
              {modalKind === 'transfer' && (
                <form onSubmit={handleSubmitTransfer} className="space-y-3.5 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                      Select Employee <span className="text-[#F04B42]">*</span>
                    </label>
                    <select
                      required
                      value={trEmployeeId}
                      onChange={(e) => setTrEmployeeId(e.target.value)}
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                    >
                      <option value="">Select target employee...</option>
                      {assignees.map((emp) => (
                        <option key={emp.employee_id} value={emp.employee_id}>
                          {emp.name} ({emp.role_name || emp.employee_id})
                        </option>
                      ))}
                    </select>
                    <p className="mt-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                      Transferring resets status to <strong>New</strong> so it enters the assignee&apos;s New Calls queue.
                    </p>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                      Remark <span className="text-[#F04B42]">*</span>
                    </label>
                    <textarea
                      required
                      rows={3}
                      value={trRemark}
                      onChange={(e) => setTrRemark(e.target.value)}
                      placeholder="Handoff notes for the receiving telecaller..."
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setModalKind(null)}
                      className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-semibold cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-4 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white font-semibold disabled:opacity-60 cursor-pointer"
                    >
                      {submitting ? 'Transferring...' : 'Transfer Callback'}
                    </button>
                  </div>
                </form>
              )}

              {/* 4. Convert to Lead Modal */}
              {modalKind === 'convert' && (
                <form onSubmit={handleSubmitConvert} className="space-y-4 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Customer Type <span className="text-[#F04B42]">*</span>
                      </label>
                      <select
                        required
                        value={cvCustomerType}
                        onChange={(e) =>
                          setCvCustomerType(e.target.value as 'BUY' | 'RENT' | 'PG')
                        }
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      >
                        <option value="BUY">BUY</option>
                        <option value="RENT">RENT</option>
                        <option value="PG">PG</option>
                      </select>
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Name <span className="text-[#F04B42]">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={cvName}
                        onChange={(e) => setCvName(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      />
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Email
                      </label>
                      <input
                        type="email"
                        value={cvEmail}
                        onChange={(e) => setCvEmail(e.target.value)}
                        placeholder="customer@example.com"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      />
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Mobile <span className="text-[#F04B42]">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={cvMobile}
                        onChange={(e) => setCvMobile(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      />
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Alternate Mobile No
                      </label>
                      <input
                        type="text"
                        value={cvAlternateMobile}
                        onChange={(e) => setCvAlternateMobile(e.target.value)}
                        placeholder="Optional alternate number"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      />
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Source <span className="text-[#F04B42]">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={cvSource}
                        onChange={(e) => setCvSource(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      />
                    </div>

                    <div className="sm:col-span-2">
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Address / Preferred Locality <span className="text-[#F04B42]">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={cvAddress}
                        onChange={(e) => setCvAddress(e.target.value)}
                        placeholder="e.g. Scheme No. 2, Alwar"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      />
                    </div>

                    <div className="sm:col-span-2">
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Assignee <span className="text-[#F04B42]">*</span>
                      </label>
                      <select
                        required
                        value={cvAssignee}
                        onChange={(e) => setCvAssignee(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      >
                        <option value="">Select assignee...</option>
                        {assignees.map((emp) => (
                          <option key={emp.employee_id} value={emp.employee_id}>
                            {emp.name} ({emp.role_name || emp.employee_id})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Refer By Section */}
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 space-y-2.5">
                    <div className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase tracking-wider">
                      Refer By (Optional)
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                      <input
                        type="text"
                        value={cvReferRelation}
                        onChange={(e) => setCvReferRelation(e.target.value)}
                        placeholder="Relation (e.g. Friend)"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                      />
                      <input
                        type="text"
                        value={cvReferName}
                        onChange={(e) => setCvReferName(e.target.value)}
                        placeholder="Referrer Name"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                      />
                      <input
                        type="text"
                        value={cvReferMobile}
                        onChange={(e) => setCvReferMobile(e.target.value)}
                        placeholder="Referrer Mobile"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setModalKind(null)}
                      className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-semibold cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-5 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white font-semibold disabled:opacity-60 cursor-pointer"
                    >
                      {submitting ? 'Converting...' : 'Convert to Lead'}
                    </button>
                  </div>
                </form>
              )}

              {/* 5. Activity & Reschedule History Modal */}
              {modalKind === 'history' && detail && (
                <div className="space-y-4 text-xs">
                  <div className="inline-flex rounded-xl bg-slate-100 dark:bg-slate-800 p-1 border border-slate-200 dark:border-slate-700">
                    {(
                      [
                        { id: 'all', label: 'All Timeline' },
                        { id: 'reschedule', label: `Reschedules (${detail.reschedule_history?.length || 0})` },
                        { id: 'activities', label: `Activities (${detail.activities?.length || 0})` },
                      ] as const
                    ).map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setHistoryFilter(tab.id)}
                        className={`px-3 py-1 rounded-lg font-semibold transition-colors cursor-pointer ${
                          historyFilter === tab.id
                            ? 'bg-[#291BB0] text-white'
                            : 'text-slate-600 dark:text-slate-300'
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {combinedTimeline.length === 0 ? (
                    <div className="py-8 text-center text-slate-500 dark:text-slate-400">
                      No timeline events recorded yet.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {combinedTimeline.map((entry) => (
                        <div
                          key={entry.id}
                          className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/50 space-y-1.5"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                              {entry.kind === 'reschedule' ? (
                                <CalendarClock className="w-3.5 h-3.5 text-sky-500" />
                              ) : (
                                <History className="w-3.5 h-3.5 text-[#291BB0] dark:text-indigo-400" />
                              )}
                              {entry.title}
                            </span>
                            <span className="text-[11px] text-slate-400">
                              {formatDateTime(entry.created_at)}
                            </span>
                          </div>

                          {entry.kind === 'reschedule' && (
                            <div className="text-[11px] font-medium text-sky-700 dark:text-sky-300 flex flex-wrap items-center gap-1.5">
                              <span>
                                {entry.oldDt ? formatDateTime(entry.oldDt) : 'Unscheduled'}
                              </span>
                              <ArrowRight className="w-3 h-3" />
                              <span className="font-bold">
                                {formatDateTime(entry.newDt)}
                              </span>
                            </div>
                          )}

                          {entry.kind === 'activity' &&
                            entry.statusBefore !== null &&
                            entry.statusBefore !== undefined &&
                            entry.statusAfter !== null &&
                            entry.statusAfter !== undefined &&
                            entry.statusBefore !== entry.statusAfter && (
                              <div className="text-[11px] text-slate-500 dark:text-slate-400">
                                {getStatusMeta(entry.statusBefore).label} →{' '}
                                <strong className="text-slate-700 dark:text-slate-200">
                                  {getStatusMeta(entry.statusAfter).label}
                                </strong>
                              </div>
                            )}

                          {entry.remark && (
                            <p className="text-slate-700 dark:text-slate-200">
                              {entry.remark}
                            </p>
                          )}

                          {entry.actor && (
                            <div className="text-[11px] text-slate-400">
                              By {entry.actor}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 6. + New Callback Modal */}
              {modalKind === 'new_callback' && (
                <form onSubmit={handleSubmitNewCallback} className="space-y-3.5 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                      Customer Name <span className="text-[#F04B42]">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={ncName}
                      onChange={(e) => setNcName(e.target.value)}
                      placeholder="Full name"
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-2.5">
                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Code
                      </label>
                      <input
                        type="text"
                        value={ncPhoneCode}
                        onChange={(e) => setNcPhoneCode(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      />
                    </div>
                    <div className="col-span-2">
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Mobile Number <span className="text-[#F04B42]">*</span>
                      </label>
                      <input
                        type="text"
                        required
                        value={ncMobile}
                        onChange={(e) => setNcMobile(e.target.value)}
                        placeholder="9876543210"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Property Code
                      </label>
                      <input
                        type="text"
                        value={ncPropertyCode}
                        onChange={(e) => setNcPropertyCode(e.target.value)}
                        placeholder="e.g. OP-2026-00001"
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Assign Telecaller
                      </label>
                      <select
                        value={ncAssignee}
                        onChange={(e) => setNcAssignee(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                      >
                        <option value="">Auto Round-Robin</option>
                        {assignees.map((emp) => (
                          <option key={emp.employee_id} value={emp.employee_id}>
                            {emp.name} ({emp.role_name || emp.employee_id})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                      Message / Inquiry Note
                    </label>
                    <textarea
                      rows={3}
                      value={ncMessage}
                      onChange={(e) => setNcMessage(e.target.value)}
                      placeholder="Optional customer message..."
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setModalKind(null)}
                      className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-semibold cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-4 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white font-semibold disabled:opacity-60 cursor-pointer"
                    >
                      {submitting ? 'Creating...' : 'Create Callback'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WebsiteFormsHub;
