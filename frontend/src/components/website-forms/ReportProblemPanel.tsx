import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Building2,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  Mail,
  Phone,
  RefreshCw,
  Save,
  Search,
  UserCheck,
  UserPlus,
  X,
} from 'lucide-react';
import {
  AssigneeOption,
  PROBLEM_STATUS_META,
  ProblemCounts,
  ProblemReportItem,
  ProblemStatus,
  authHeaders,
} from '../../types/websiteForms';

interface ReportProblemPanelProps {
  assignees?: AssigneeOption[];
}

type ProblemFilterStatus = 'ALL' | ProblemStatus;

const PROBLEM_FILTER_TABS: {
  key: ProblemFilterStatus;
  label: string;
  countKey: keyof ProblemCounts;
}[] = [
  { key: 'ALL', label: 'All', countKey: 'all' },
  { key: 'NEW', label: 'New', countKey: 'new' },
  { key: 'IN_REVIEW', label: 'In Review', countKey: 'in_review' },
  { key: 'RESOLVED', label: 'Resolved', countKey: 'resolved' },
  { key: 'REJECTED', label: 'Rejected', countKey: 'rejected' },
];

const PROBLEM_STATUS_OPTIONS: ProblemStatus[] = [
  'NEW',
  'IN_REVIEW',
  'RESOLVED',
  'REJECTED',
];

const LEAD_TYPE_OPTIONS: Array<'BUYER' | 'SELLER' | 'TENANT' | 'OWNER'> = [
  'BUYER',
  'SELLER',
  'TENANT',
  'OWNER',
];

const EMPTY_COUNTS: ProblemCounts = {
  all: 0,
  new: 0,
  in_review: 0,
  resolved: 0,
  rejected: 0,
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

function humanizeKey(key: string): string {
  return key
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function formatDetailValue(val: unknown): string {
  if (val === null || val === undefined || val === '') return '—';
  if (typeof val === 'boolean') return val ? 'Yes' : 'No';
  if (typeof val === 'object') {
    try {
      return JSON.stringify(val, null, 2);
    } catch {
      return String(val);
    }
  }
  return String(val);
}

function getProblemStatusMeta(statusVal: string) {
  return (
    PROBLEM_STATUS_META[statusVal as ProblemStatus] || {
      label: statusVal || 'Unknown',
      badgeClass:
        'bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-500/20',
    }
  );
}

export const ReportProblemPanel: React.FC<ReportProblemPanelProps> = ({
  assignees: propAssignees,
}) => {
  // Filter & search state
  const [statusFilter, setStatusFilter] = useState<ProblemFilterStatus>('ALL');
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Data state
  const [counts, setCounts] = useState<ProblemCounts>(EMPTY_COUNTS);
  const [items, setItems] = useState<ProblemReportItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const selectedIdRef = useRef<number | null>(null);
  selectedIdRef.current = selectedId;

  const [localAssignees, setLocalAssignees] = useState<AssigneeOption[]>([]);
  const assignees = useMemo(
    () => (propAssignees && propAssignees.length > 0 ? propAssignees : localAssignees),
    [propAssignees, localAssignees]
  );

  // Loading & feedback state
  const [listLoading, setListLoading] = useState(false);
  const [savingTriage, setSavingTriage] = useState(false);
  const [converting, setConverting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [banner, setBanner] = useState<{
    type: 'success' | 'error';
    text: string;
    leadId?: string;
  } | null>(null);

  // Triage form state (synced to selected problem item)
  const [triageStatus, setTriageStatus] = useState<ProblemStatus>('NEW');
  const [triageAssignee, setTriageAssignee] = useState<string>('');
  const [triageRemark, setTriageRemark] = useState<string>('');

  // Convert-to-Lead modal state
  const [convertOpen, setConvertOpen] = useState(false);
  const [convertError, setConvertError] = useState<string | null>(null);
  const [cvLeadType, setCvLeadType] = useState<'BUYER' | 'SELLER' | 'TENANT' | 'OWNER'>('BUYER');
  const [cvAssignee, setCvAssignee] = useState<string>('');
  const [cvBudgetMin, setCvBudgetMin] = useState<string>('');
  const [cvBudgetMax, setCvBudgetMax] = useState<string>('');

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

  const fetchAssignees = useCallback(async () => {
    if (propAssignees && propAssignees.length > 0) return;
    try {
      const res = await fetch('/v1/callbacks/assignees', {
        headers: authHeaders(false),
      });
      if (res.ok) {
        setLocalAssignees(await res.json());
      }
    } catch {
      // Non-fatal
    }
  }, [propAssignees]);

  const fetchProblems = useCallback(
    async (preferSelectId?: number | null) => {
      setListLoading(true);
      try {
        const params = new URLSearchParams({
          status: statusFilter,
          limit: '100',
          offset: '0',
        });
        if (debouncedSearch) {
          params.set('search', debouncedSearch);
        }
        const res = await fetch(`/v1/problems?${params.toString()}`, {
          headers: authHeaders(false),
        });
        if (!res.ok) {
          throw new Error(await parseError(res, 'Failed to fetch problem reports.'));
        }
        const data = await res.json();
        const fetchedItems: ProblemReportItem[] = data.items || [];
        setItems(fetchedItems);
        setTotal(typeof data.total === 'number' ? data.total : fetchedItems.length);
        setCounts(data.counts || EMPTY_COUNTS);

        const candidateId =
          preferSelectId !== undefined ? preferSelectId : selectedIdRef.current;
        if (candidateId && fetchedItems.some((item) => item.id === candidateId)) {
          setSelectedId(candidateId);
        } else if (fetchedItems.length > 0) {
          setSelectedId(fetchedItems[0].id);
        } else {
          setSelectedId(null);
        }
      } catch (err: any) {
        setBanner({
          type: 'error',
          text: err?.message || 'Unable to load problem reports.',
        });
      } finally {
        setListLoading(false);
      }
    },
    [statusFilter, debouncedSearch]
  );

  useEffect(() => {
    fetchAssignees();
  }, [fetchAssignees]);

  useEffect(() => {
    fetchProblems();
  }, [fetchProblems]);

  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedId) || null,
    [items, selectedId]
  );

  // Sync triage form fields whenever selected problem changes
  useEffect(() => {
    if (!selectedItem) return;
    setTriageStatus(selectedItem.status || 'NEW');
    setTriageAssignee(selectedItem.assigned_to || '');
    setTriageRemark(selectedItem.resolution_remark || '');
  }, [selectedItem]);

  // Extract primary description + structured metadata fields from details JSON
  const parsedDetails = useMemo(() => {
    const details = selectedItem?.details;
    if (!details || typeof details !== 'object') {
      return { primaryText: null as string | null, extraEntries: [] as Array<[string, unknown]> };
    }
    const primaryKeys = ['description', 'message', 'problem', 'issue', 'comment'];
    let primaryText: string | null = null;
    let usedKey: string | null = null;

    for (const k of primaryKeys) {
      const val = details[k];
      if (typeof val === 'string' && val.trim()) {
        primaryText = val.trim();
        usedKey = k;
        break;
      }
    }

    const extraEntries = Object.entries(details).filter(
      ([k, v]) => k !== usedKey && v !== null && v !== undefined && String(v).trim() !== ''
    );
    return { primaryText, extraEntries };
  }, [selectedItem]);

  const handleSaveTriage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;
    setSavingTriage(true);
    setBanner(null);

    try {
      const res = await fetch(`/v1/problems/${selectedItem.id}`, {
        method: 'PATCH',
        headers: authHeaders(true),
        body: JSON.stringify({
          status: triageStatus,
          assigned_to: triageAssignee,
          resolution_remark: triageRemark,
        }),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to save problem triage update.'));
      }
      const updated: ProblemReportItem = await res.json();
      setBanner({
        type: 'success',
        text: `Updated PRB-${updated.id} (${getProblemStatusMeta(updated.status).label}).`,
      });
      await fetchProblems(updated.id);
    } catch (err: any) {
      setBanner({
        type: 'error',
        text: err?.message || 'Failed to update problem report.',
      });
    } finally {
      setSavingTriage(false);
    }
  };

  const openConvertModal = () => {
    if (!selectedItem || selectedItem.is_converted) return;
    setCvLeadType('BUYER');
    setCvAssignee(selectedItem.assigned_to || assignees[0]?.employee_id || '');
    setCvBudgetMin('');
    setCvBudgetMax('');
    setConvertError(null);
    setConvertOpen(true);
  };

  const handleConvertToLead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;
    setConvertError(null);

    const minVal = cvBudgetMin.trim() ? Number(cvBudgetMin) : null;
    const maxVal = cvBudgetMax.trim() ? Number(cvBudgetMax) : null;
    if (minVal !== null && Number.isNaN(minVal)) {
      setConvertError('Minimum budget must be a valid number.');
      return;
    }
    if (maxVal !== null && Number.isNaN(maxVal)) {
      setConvertError('Maximum budget must be a valid number.');
      return;
    }
    if (minVal !== null && maxVal !== null && minVal > maxVal) {
      setConvertError('Minimum budget cannot exceed maximum budget.');
      return;
    }

    setConverting(true);
    try {
      const res = await fetch(`/v1/problems/${selectedItem.id}/convert-to-lead`, {
        method: 'POST',
        headers: authHeaders(true),
        body: JSON.stringify({
          assigned_to: cvAssignee || null,
          lead_type: cvLeadType,
          budget_min: minVal,
          budget_max: maxVal,
        }),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to convert problem report to lead.'));
      }
      const lead = await res.json();
      setConvertOpen(false);
      setBanner({
        type: 'success',
        text: `Problem PRB-${selectedItem.id} converted to Lead ${lead.lead_id}.`,
        leadId: lead.lead_id,
      });
      await fetchProblems(selectedItem.id);
    } catch (err: any) {
      setConvertError(err?.message || 'Conversion failed.');
    } finally {
      setConverting(false);
    }
  };

  const handleExportXls = async () => {
    setExporting(true);
    setBanner(null);
    try {
      const params = new URLSearchParams({ status: statusFilter });
      if (debouncedSearch) {
        params.set('search', debouncedSearch);
      }
      const res = await fetch(`/v1/problems/export?${params.toString()}`, {
        headers: authHeaders(false),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to export problem reports.'));
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `problems_${statusFilter.toLowerCase()}.xls`;
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

  return (
    <div className="space-y-4">
      {/* Status Filter Pills + Actions Bar */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {PROBLEM_FILTER_TABS.map((tab) => {
              const isActive = statusFilter === tab.key;
              const count = counts[tab.countKey] ?? 0;
              const isNewAlert = tab.key === 'NEW' && count > 0 && !isActive;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setStatusFilter(tab.key)}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                    isActive
                      ? 'bg-[#291BB0] hover:bg-[#1f138e] text-white border-[#291BB0] shadow-sm'
                      : 'bg-slate-50 dark:bg-slate-800/70 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-[#291BB0]/40'
                  }`}
                >
                  <span>{tab.label}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded-md text-[11px] font-bold ${
                      isActive
                        ? 'bg-white/20 text-white'
                        : isNewAlert
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

          <div className="flex flex-wrap items-center gap-2">
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
              onClick={() => fetchProblems(selectedId)}
              title="Refresh"
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${listLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
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

      {/* Master-Detail Split Layout */}
      <div className="flex flex-col lg:flex-row gap-4 items-start">
        {/* LEFT PANEL (~360px): Search + Problem Report Queue */}
        <div className="w-full lg:w-[360px] shrink-0 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col max-h-[calc(100vh-250px)]">
          <div className="p-3 border-b border-slate-100 dark:border-slate-800 space-y-2 bg-slate-50/70 dark:bg-slate-900">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search reporter, mobile, property code..."
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

            <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 px-0.5">
              <span>
                Showing <strong className="text-slate-700 dark:text-slate-200">{items.length}</strong> of{' '}
                <strong className="text-slate-700 dark:text-slate-200">{total}</strong>
              </span>
              <span className="uppercase tracking-wider font-semibold text-[10px] text-[#291BB0] dark:text-indigo-400">
                {PROBLEM_FILTER_TABS.find((t) => t.key === statusFilter)?.label}
              </span>
            </div>
          </div>

          <div className="overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800 flex-1">
            {listLoading && items.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 dark:text-slate-400">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#291BB0]" />
                Loading problem reports...
              </div>
            ) : items.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500 dark:text-slate-400">
                No problem reports match this filter.
              </div>
            ) : (
              items.map((item) => {
                const isSelected = item.id === selectedId;
                const statusMeta = getProblemStatusMeta(item.status);
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setSelectedId(item.id)}
                    className={`w-full text-left p-3.5 transition-colors cursor-pointer border-l-4 ${
                      isSelected
                        ? 'bg-[#291BB0]/5 dark:bg-indigo-950/30 border-l-[#291BB0]'
                        : 'bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 border-l-transparent'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="font-semibold text-sm text-slate-900 dark:text-white truncate">
                          {item.full_name}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                          <span className="font-mono font-semibold text-[#291BB0] dark:text-indigo-300">
                            PRB-{item.id}
                          </span>
                          <span>•</span>
                          <span>{item.mobile}</span>
                        </div>
                      </div>

                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border shrink-0 ${statusMeta.badgeClass}`}
                      >
                        {statusMeta.label}
                      </span>
                    </div>

                    {item.related_property_code && (
                      <div className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md">
                        <Building2 className="w-3 h-3 text-[#291BB0] dark:text-indigo-400" />
                        {item.related_property_code}
                      </div>
                    )}

                    <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                      <span className="truncate">
                        Assignee:{' '}
                        <span className="font-medium text-slate-700 dark:text-slate-300">
                          {item.assigned_to_name || item.assigned_to || 'Unassigned'}
                        </span>
                      </span>
                      <span className="shrink-0">{formatDateTime(item.created_at)}</span>
                    </div>

                    {item.is_converted && item.converted_lead_id && (
                      <div className="mt-1.5 inline-flex items-center gap-1 text-[10px] font-semibold text-purple-700 dark:text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded-md">
                        Lead {item.converted_lead_id}
                      </div>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT PANEL: Problem Details & Triage Controls */}
        <div className="flex-1 min-w-0 w-full space-y-4">
          {!selectedItem ? (
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-12 text-center shadow-sm">
              <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-slate-300 dark:text-slate-600" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                Select a problem report from the list
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Review reported listing or portal issues, assign staff, log resolution remarks, or convert to a lead.
              </p>
            </div>
          ) : (
            <>
              {/* Header Card */}
              <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm">
                <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                        {selectedItem.full_name}
                      </h2>
                      <span className="px-2.5 py-0.5 rounded-lg bg-[#291BB0]/10 text-[#291BB0] dark:bg-indigo-500/20 dark:text-indigo-300 font-mono text-xs font-bold">
                        PRB-{selectedItem.id}
                      </span>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                          getProblemStatusMeta(selectedItem.status).badgeClass
                        }`}
                      >
                        {getProblemStatusMeta(selectedItem.status).label}
                      </span>
                      {selectedItem.is_converted && selectedItem.converted_lead_id && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/25">
                          Converted to Lead
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 dark:text-slate-300">
                      <a
                        href={`tel:${selectedItem.mobile.replace(/\s+/g, '')}`}
                        className="inline-flex items-center gap-1.5 font-semibold text-[#291BB0] dark:text-indigo-300 hover:underline"
                      >
                        <Phone className="w-3.5 h-3.5" />
                        {selectedItem.mobile}
                      </a>
                      {selectedItem.email && (
                        <>
                          <span className="text-slate-300 dark:text-slate-700">|</span>
                          <a
                            href={`mailto:${selectedItem.email}`}
                            className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300 hover:underline"
                          >
                            <Mail className="w-3.5 h-3.5 text-slate-400" />
                            {selectedItem.email}
                          </a>
                        </>
                      )}
                      <span className="text-slate-300 dark:text-slate-700">|</span>
                      <span className="inline-flex items-center gap-1 text-slate-500 dark:text-slate-400">
                        <Clock className="w-3.5 h-3.5" />
                        Submitted {formatDateTime(selectedItem.created_at)}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    {selectedItem.is_converted && selectedItem.converted_lead_id ? (
                      <Link
                        to={`/leads/${selectedItem.converted_lead_id}`}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold shadow-sm transition-colors"
                      >
                        <span>View Lead {selectedItem.converted_lead_id}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    ) : (
                      <button
                        type="button"
                        onClick={openConvertModal}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
                      >
                        <UserPlus className="w-3.5 h-3.5" />
                        Convert to Lead
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Details & Triage Grid */}
              <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
                {/* Left 3 cols: Reporter & Problem Payload */}
                <div className="xl:col-span-3 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                      <FileText className="w-4 h-4 text-[#291BB0] dark:text-indigo-400" />
                      Reported Problem Details
                    </h3>
                    {selectedItem.updated_at && (
                      <span className="text-[11px] text-slate-400">
                        Updated {formatDateTime(selectedItem.updated_at)}
                      </span>
                    )}
                  </div>

                  {/* Property Reference */}
                  <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
                    <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Related Property
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-slate-800 dark:text-slate-100">
                      <Building2 className="w-4 h-4 text-[#291BB0] dark:text-indigo-400 shrink-0" />
                      {selectedItem.related_property_code || selectedItem.property_title ? (
                        <span>
                          {selectedItem.related_property_code && (
                            <strong className="font-mono">{selectedItem.related_property_code}</strong>
                          )}
                          {selectedItem.related_property_code && selectedItem.property_title
                            ? ' — '
                            : ''}
                          {selectedItem.property_title || ''}
                        </span>
                      ) : (
                        <span className="text-slate-400">General Portal / No Property Linked</span>
                      )}
                    </div>
                  </div>

                  {/* Primary Problem Description */}
                  <div>
                    <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
                      Problem Description
                    </div>
                    <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-200 whitespace-pre-wrap">
                      {parsedDetails.primaryText || 'No description text provided by reporter.'}
                    </div>
                  </div>

                  {/* Structured JSON Fields */}
                  {parsedDetails.extraEntries.length > 0 && (
                    <div>
                      <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-2">
                        Additional Submitted Fields
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                        {parsedDetails.extraEntries.map(([k, v]) => (
                          <div
                            key={k}
                            className="p-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40"
                          >
                            <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                              {humanizeKey(k)}
                            </div>
                            <div className="mt-0.5 font-medium text-slate-800 dark:text-slate-100 break-words whitespace-pre-wrap">
                              {formatDetailValue(v)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Resolution Audit */}
                  {(selectedItem.resolved_by || selectedItem.resolved_at) && (
                    <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                      <span>
                        Resolved By:{' '}
                        <strong className="text-slate-700 dark:text-slate-200">
                          {selectedItem.resolved_by_name || selectedItem.resolved_by || '—'}
                        </strong>
                      </span>
                      <span>{formatDateTime(selectedItem.resolved_at)}</span>
                    </div>
                  )}
                </div>

                {/* Right 2 cols: Triage & Resolution Form */}
                <div className="xl:col-span-2 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm">
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-4">
                    <UserCheck className="w-4 h-4 text-[#291BB0] dark:text-indigo-400" />
                    Triage & Resolution
                  </h3>

                  <form onSubmit={handleSaveTriage} className="space-y-3.5 text-xs">
                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Triage Status
                      </label>
                      <select
                        value={triageStatus}
                        onChange={(e) => setTriageStatus(e.target.value as ProblemStatus)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                      >
                        {PROBLEM_STATUS_OPTIONS.map((st) => (
                          <option key={st} value={st}>
                            {getProblemStatusMeta(st).label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Assigned Staff
                      </label>
                      <select
                        value={triageAssignee}
                        onChange={(e) => setTriageAssignee(e.target.value)}
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                      >
                        <option value="">Unassigned</option>
                        {assignees.map((emp) => (
                          <option key={emp.employee_id} value={emp.employee_id}>
                            {emp.name} ({emp.role_name || emp.employee_id})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                        Resolution Remark
                      </label>
                      <textarea
                        rows={4}
                        value={triageRemark}
                        onChange={(e) => setTriageRemark(e.target.value)}
                        placeholder="Add verification findings, fix notes, or rejection reason..."
                        className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#291BB0]/30"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={savingTriage}
                      className="w-full inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white font-semibold shadow-sm transition-colors disabled:opacity-60 cursor-pointer"
                    >
                      <Save className="w-3.5 h-3.5" />
                      {savingTriage ? 'Saving Update...' : 'Save Triage Update'}
                    </button>
                  </form>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Convert to Lead Modal */}
      {convertOpen && selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Convert Problem Report to Lead
                </h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                  PRB-{selectedItem.id} • {selectedItem.full_name} ({selectedItem.mobile})
                </p>
              </div>
              <button
                type="button"
                onClick={() => setConvertOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleConvertToLead} className="p-5 space-y-3.5 text-xs">
              {convertError && (
                <div className="px-3 py-2.5 rounded-xl bg-[#F04B42]/10 border border-[#F04B42]/30 text-[#F04B42] dark:text-red-300 font-medium flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{convertError}</span>
                </div>
              )}

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                  Lead Type <span className="text-[#F04B42]">*</span>
                </label>
                <select
                  value={cvLeadType}
                  onChange={(e) =>
                    setCvLeadType(e.target.value as 'BUYER' | 'SELLER' | 'TENANT' | 'OWNER')
                  }
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  {LEAD_TYPE_OPTIONS.map((lt) => (
                    <option key={lt} value={lt}>
                      {lt}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                  Assign Lead To
                </label>
                <select
                  value={cvAssignee}
                  onChange={(e) => setCvAssignee(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  <option value="">Default (Current Assignee / You)</option>
                  {assignees.map((emp) => (
                    <option key={emp.employee_id} value={emp.employee_id}>
                      {emp.name} ({emp.role_name || emp.employee_id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                    Budget Min (Optional)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={cvBudgetMin}
                    onChange={(e) => setCvBudgetMin(e.target.value)}
                    placeholder="e.g. 2500000"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-200 mb-1">
                    Budget Max (Optional)
                  </label>
                  <input
                    type="number"
                    min={0}
                    value={cvBudgetMax}
                    onChange={(e) => setCvBudgetMax(e.target.value)}
                    placeholder="e.g. 5000000"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setConvertOpen(false)}
                  className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={converting}
                  className="px-4 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white font-semibold disabled:opacity-60 cursor-pointer"
                >
                  {converting ? 'Converting...' : 'Confirm Conversion'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportProblemPanel;
