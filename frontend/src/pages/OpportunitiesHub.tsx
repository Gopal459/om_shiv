import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRightLeft,
  Building2,
  Calendar,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Download,
  Edit3,
  ExternalLink,
  History,
  Home,
  IndianRupee,
  Loader2,
  Lock,
  Mail,
  MapPin,
  Mic,
  MicOff,
  Phone,
  PhoneCall,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  SlidersHorizontal,
  Sparkles,
  Tag,
  User,
  UserCheck,
  X,
} from 'lucide-react';
import {
  AssigneeOption,
  DISQUALIFIED_REASONS,
  FranchiseOutletOption,
  OPPORTUNITY_STATUS_META,
  OpportunityActivity,
  OpportunityDashboardResponse,
  OpportunityDetail,
  OpportunityRescheduleLog,
  OpportunitySummary,
  OpportunityTab,
  PROPERTY_CATEGORIES,
  PROPERTY_SUBCATEGORIES_BY_CATEGORY,
  RelatedPropertyItem,
  authHeaders,
} from '../types/opportunities';
import OpportunityFormModal from '../components/opportunities/OpportunityFormModal';
import RelatedPropertiesModal from '../components/opportunities/RelatedPropertiesModal';

const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

const VALID_TABS: OpportunityTab[] = [
  'new',
  'today',
  'open',
  'missing',
  'in_progress',
  'closed',
  'all',
];

const OPPORTUNITY_TABS: { key: OpportunityTab; label: string }[] = [
  { key: 'new', label: 'New Opportunity' },
  { key: 'today', label: 'Today Opportunity' },
  { key: 'open', label: 'Open Opportunity' },
  { key: 'missing', label: 'Missing Opportunity' },
  { key: 'in_progress', label: 'In-Progress' },
  { key: 'closed', label: 'Closed' },
  { key: 'all', label: 'All Opportunity' },
];

const EMPTY_DASHBOARD: OpportunityDashboardResponse = {
  counts: {
    new: 0,
    today: 0,
    open: 0,
    missing: 0,
    all: 0,
    in_progress: 0,
    closed: 0,
  },
  chart_breakdown: {
    total: 0,
    open: 0,
    disqualified: 0,
    qualified_propira: 0,
    qualified_other: 0,
    closed: 0,
  },
};

type ActionModalKind = 'reschedule' | 'status' | 'transfer' | 'reopen' | null;

interface SourceLeadPrefill {
  lead_id: string;
  contact_name?: string;
  mobile?: string;
  alternate_mobile?: string;
  email?: string;
  address?: string;
  property_type?: number;
  budget_to?: number;
  locality?: string;
  remark?: string;
  assigned_to?: string;
}

function formatBudgetShort(val: number): string {
  if (!val || val <= 0) return '';
  if (val >= 10_000_000) return `₹${(val / 10_000_000).toFixed(2)} Cr`;
  if (val >= 100_000) return `₹${(val / 100_000).toFixed(2)} L`;
  return `₹${val.toLocaleString('en-IN')}`;
}

function formatBudgetRange(from?: number, to?: number): string {
  const f = from || 0;
  const t = to || 0;
  if (f <= 0 && t <= 0) return 'Budget Open';
  if (f > 0 && t > 0 && f !== t) {
    return `${formatBudgetShort(f)} – ${formatBudgetShort(t)}`;
  }
  return formatBudgetShort(t || f);
}

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
  return {
    date: `${target.getFullYear()}-${pad(target.getMonth() + 1)}-${pad(target.getDate())}`,
    time: `${pad(target.getHours())}:${pad(target.getMinutes())}`,
  };
}

function getPropertyTypeLabel(pt?: number): string {
  if (pt === 1) return 'Rent';
  if (pt === 2) return 'Buy / Sell';
  if (pt === 3) return 'PG';
  return 'Buy / Sell';
}

function getCategoryLabel(catId?: number | null): string {
  if (!catId) return '—';
  return PROPERTY_CATEGORIES.find((c) => c.id === catId)?.label || `Category #${catId}`;
}

function getSubcategoryLabel(catId?: number | null, subId?: number | null): string {
  if (!subId) return 'Any';
  const list = catId ? PROPERTY_SUBCATEGORIES_BY_CATEGORY[catId] || [] : [];
  return list.find((s) => s.id === subId)?.label || `Subcategory #${subId}`;
}

function getStatusMeta(code: number) {
  return (
    OPPORTUNITY_STATUS_META[code] || {
      code,
      label: `Status ${code}`,
      badgeClass:
        'bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-500/20',
      dotClass: 'bg-slate-400',
    }
  );
}

async function parseError(res: Response, fallback: string): Promise<string> {
  const data = await res.json().catch(() => null);
  const detail = data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (detail !== undefined && detail !== null) return JSON.stringify(detail);
  return fallback;
}

export const OpportunitiesHub: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  const tabParam = (searchParams.get('tab') || 'new') as OpportunityTab;
  const activeTab: OpportunityTab = VALID_TABS.includes(tabParam) ? tabParam : 'new';
  const idParam = searchParams.get('id');
  const fromLeadParam = searchParams.get('fromLead');
  const actionParam = searchParams.get('action');

  // Search + Voice
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const speechSupported = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return Boolean(
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    );
  }, []);

  // Data state
  const [dashboard, setDashboard] = useState<OpportunityDashboardResponse>(EMPTY_DASHBOARD);
  const [items, setItems] = useState<OpportunitySummary[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const n = idParam ? parseInt(idParam, 10) : NaN;
    return Number.isFinite(n) && n > 0 ? n : null;
  });
  const selectedIdRef = useRef<number | null>(null);
  const pendingSelectIdRef = useRef<number | null>(null);
  selectedIdRef.current = selectedId;

  const [detail, setDetail] = useState<OpportunityDetail | null>(null);
  const [assignees, setAssignees] = useState<AssigneeOption[]>([]);
  const [outlets, setOutlets] = useState<FranchiseOutletOption[]>([]);

  // Loading & banners
  const [listLoading, setListLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [banner, setBanner] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Modals
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [editingOpportunity, setEditingOpportunity] = useState<OpportunityDetail | null>(null);
  const [sourceLeadPrefill, setSourceLeadPrefill] = useState<SourceLeadPrefill | null>(null);
  const [relatedModalOpen, setRelatedModalOpen] = useState(false);
  const [actionModal, setActionModal] = useState<ActionModalKind>(null);
  const [modalError, setModalError] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(true);
  const historyRef = useRef<HTMLDivElement | null>(null);

  // Reschedule form state
  const [rsDate, setRsDate] = useState('');
  const [rsTime, setRsTime] = useState('');
  const [rsCurrentUpdate, setRsCurrentUpdate] = useState('');
  const [rsRemark, setRsRemark] = useState('');

  // Status / Deal Schedule form state
  const [stStatus, setStStatus] = useState<number>(1);
  const [stDisqReason, setStDisqReason] = useState<number>(1);
  const [stDealDate, setStDealDate] = useState('');
  const [stRegistryDate, setStRegistryDate] = useState('');
  const [stIsPropira, setStIsPropira] = useState(false);
  const [stMatchedPropId, setStMatchedPropId] = useState('');
  const [stDealCategory, setStDealCategory] = useState<number>(1);
  const [stDealSubcategory, setStDealSubcategory] = useState<number>(1);
  const [stDealAddress, setStDealAddress] = useState('');
  const [stDealLat, setStDealLat] = useState('');
  const [stDealLong, setStDealLong] = useState('');
  const [stRemark, setStRemark] = useState('');

  // Transfer form state
  const [trFranchId, setTrFranchId] = useState<number>(0);
  const [trEmployeeId, setTrEmployeeId] = useState('');
  const [trRemark, setTrRemark] = useState('');

  // Reopen form state
  const [roRemark, setRoRemark] = useState('');

  // Debounce search
  useEffect(() => {
    const t = window.setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
    }, 250);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  // Cleanup speech recognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  const setActiveTab = (tab: OpportunityTab) => {
    const next = new URLSearchParams(searchParams);
    next.set('tab', tab);
    next.delete('id');
    setSearchParams(next, { replace: true });
  };

  // Fetch dashboard
  const fetchDashboard = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/opportunities/dashboard`, {
        headers: authHeaders(false),
      });
      if (res.ok) {
        setDashboard(await res.json());
      }
    } catch {
      // non-fatal
    }
  }, []);

  // Fetch assignees & outlets for Transfer modal
  const fetchDropdowns = useCallback(async () => {
    try {
      const headers = authHeaders(false);
      const [aRes, oRes] = await Promise.all([
        fetch(`${API_BASE}/v1/leads/assignees`, { headers }),
        fetch(`${API_BASE}/v1/franchise/outlets`, { headers }),
      ]);
      if (aRes.ok) {
        const aData = await aRes.json();
        if (Array.isArray(aData)) setAssignees(aData);
      }
      if (oRes.ok) {
        const oData = await oRes.json();
        if (oData?.outlets && Array.isArray(oData.outlets)) {
          setOutlets(oData.outlets);
        }
      }
    } catch {
      // non-fatal
    }
  }, []);

  // Fetch list
  const fetchList = useCallback(
    async (preferSelectId?: number | null): Promise<OpportunitySummary[]> => {
      setListLoading(true);
      try {
        const params = new URLSearchParams({
          tab: activeTab,
          limit: '100',
          offset: '0',
        });
        if (debouncedSearch) params.set('search', debouncedSearch);

        const res = await fetch(`${API_BASE}/v1/opportunities?${params.toString()}`, {
          headers: authHeaders(false),
        });
        if (!res.ok) {
          throw new Error(await parseError(res, 'Failed to fetch opportunities.'));
        }
        const data = await res.json();
        const fetchedItems: OpportunitySummary[] = data.items || [];
        setItems(fetchedItems);
        setTotal(typeof data.total === 'number' ? data.total : fetchedItems.length);

        const pendingId = pendingSelectIdRef.current;
        pendingSelectIdRef.current = null;
        const urlId = idParam ? parseInt(idParam, 10) : NaN;
        const candidateId =
          preferSelectId !== undefined
            ? preferSelectId
            : pendingId ??
              (Number.isFinite(urlId) && urlId > 0 ? urlId : selectedIdRef.current);

        if (candidateId && fetchedItems.some((i) => i.opportunity_id === candidateId)) {
          setSelectedId(candidateId);
        } else if (fetchedItems.length > 0) {
          setSelectedId(fetchedItems[0].opportunity_id);
        } else {
          setSelectedId(null);
          setDetail(null);
        }
        return fetchedItems;
      } catch (err: any) {
        setBanner({
          type: 'error',
          text: err?.message || 'Unable to load opportunities queue.',
        });
        return [];
      } finally {
        setListLoading(false);
      }
    },
    [activeTab, debouncedSearch, idParam]
  );

  // Fetch detail
  const fetchDetail = useCallback(async (oppId: number) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`${API_BASE}/v1/opportunities/${oppId}`, {
        headers: authHeaders(false),
      });
      if (!res.ok) {
        if (res.status === 403 || res.status === 404) {
          setDetail(null);
          return;
        }
        throw new Error(await parseError(res, 'Failed to load opportunity details.'));
      }
      setDetail(await res.json());
    } catch (err: any) {
      setBanner({
        type: 'error',
        text: err?.message || 'Failed to load opportunity details.',
      });
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    fetchDropdowns();
  }, [fetchDashboard, fetchDropdowns]);

  useEffect(() => {
    fetchList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, debouncedSearch]);

  useEffect(() => {
    if (idParam) {
      const parsed = parseInt(idParam, 10);
      if (Number.isFinite(parsed) && parsed > 0) {
        setSelectedId(parsed);
      }
    }
  }, [idParam]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    fetchDetail(selectedId);
  }, [selectedId, fetchDetail]);

  // Handle ?fromLead=<uid> and ?action=create
  useEffect(() => {
    if (fromLeadParam) {
      let cancelled = false;
      fetch(`${API_BASE}/v1/leads/${encodeURIComponent(fromLeadParam)}`, {
        headers: authHeaders(false),
      })
        .then(async (res) => {
          if (!res.ok) throw new Error(await parseError(res, 'Could not load source lead.'));
          return res.json();
        })
        .then((leadData) => {
          if (cancelled) return;
          const lt = String(leadData.lead_type || 'BUY').toUpperCase();
          const pt = lt === 'RENT' ? 1 : lt === 'PG' ? 3 : 2;
          const rawAssigned = leadData.assigned_to || '';
          const prefill: SourceLeadPrefill = {
            lead_id: leadData.lead_id || fromLeadParam,
            contact_name: leadData.full_name || '',
            mobile: leadData.mobile || '',
            alternate_mobile: leadData.alternate_contact_mobile || '',
            email: leadData.email || '',
            address: leadData.preferred_city || '',
            property_type: pt,
            budget_to: Number(leadData.budget_max || leadData.deal_final_price || 0) || undefined,
            locality: leadData.preferred_locality || leadData.indv_property_address || '',
            remark: leadData.lead_remark || '',
            assigned_to:
              rawAssigned && !String(rawAssigned).startsWith('Staff #')
                ? rawAssigned
                : undefined,
          };
          setEditingOpportunity(null);
          setSourceLeadPrefill(prefill);
          setFormModalOpen(true);
        })
        .catch((err: any) => {
          if (!cancelled) {
            setBanner({
              type: 'error',
              text: err?.message || 'Failed to load lead for conversion.',
            });
          }
        });
      return () => {
        cancelled = true;
      };
    } else if (actionParam === 'create') {
      setEditingOpportunity(null);
      setSourceLeadPrefill(null);
      setFormModalOpen(true);
    }
  }, [fromLeadParam, actionParam]);

  const refreshAll = async (targetId?: number | null) => {
    const [, refreshed] = await Promise.all([fetchDashboard(), fetchList(targetId)]);
    const idToLoad =
      targetId && refreshed.some((r) => r.opportunity_id === targetId)
        ? targetId
        : refreshed[0]?.opportunity_id ?? null;
    if (idToLoad) {
      await fetchDetail(idToLoad);
    }
  };

  // Voice Microphone Search
  const toggleVoiceSearch = () => {
    if (!speechSupported) return;
    if (isListening && recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
      setIsListening(false);
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: any) => {
      const transcript = event?.results?.[0]?.[0]?.transcript || '';
      if (transcript.trim()) {
        setSearchInput(transcript.trim());
      }
      setIsListening(false);
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    setIsListening(true);
    recognition.start();
  };

  // Export Excel (.xls Blob)
  const handleExportXls = async () => {
    setExporting(true);
    setBanner(null);
    try {
      const params = new URLSearchParams({ tab: activeTab });
      if (debouncedSearch) params.set('search', debouncedSearch);

      const res = await fetch(`${API_BASE}/v1/opportunities/export?${params.toString()}`, {
        headers: authHeaders(false),
      });
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to export opportunities.'));
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `opportunities_${activeTab}.xls`;
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

  // Call User (tel: + POST call-log)
  const handleCallUser = async () => {
    if (!detail) return;
    setBanner(null);
    try {
      const res = await fetch(
        `${API_BASE}/v1/opportunities/${detail.opportunity_id}/call-log`,
        {
          method: 'POST',
          headers: authHeaders(true),
          body: JSON.stringify({ remark: 'Outbound call initiated from Opportunities Hub' }),
        }
      );
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to log call.'));
      }
      setBanner({
        type: 'success',
        text: `Call logged for ${detail.contact_name}.`,
      });
      await refreshAll(detail.opportunity_id);
    } catch (err: any) {
      setBanner({
        type: 'error',
        text: err?.message || 'Could not log call.',
      });
    }
  };

  // Open action modals
  const openRescheduleModal = () => {
    if (!detail) return;
    const { date, time } = getDefaultScheduleDateAndTime();
    setRsDate(date);
    setRsTime(time);
    setRsCurrentUpdate(detail.current_update || '');
    setRsRemark('');
    setModalError(null);
    setActionModal('reschedule');
  };

  const openStatusModal = (prefillProp?: RelatedPropertyItem) => {
    if (!detail) return;
    const pad = (n: number) => String(n).padStart(2, '0');
    const now = new Date();
    const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    const nextWeek = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
    const nextWeekStr = `${nextWeek.getFullYear()}-${pad(nextWeek.getMonth() + 1)}-${pad(nextWeek.getDate())}`;

    if (prefillProp) {
      setStStatus(4);
      setStIsPropira(true);
      setStMatchedPropId(String(prefillProp.property_id));
      setStDealCategory(prefillProp.looking_type || 1);
      setStDealSubcategory(prefillProp.looking_subcat_type || 0);
      setStDealAddress(
        [
          prefillProp.project_name,
          prefillProp.sublocality_address,
          prefillProp.location,
          prefillProp.pincode,
        ]
          .filter(Boolean)
          .join(', ')
      );
      setStDealLat(prefillProp.location_lat || '');
      setStDealLong(prefillProp.location_long || '');
      setStDealDate(todayStr);
      setStRegistryDate(nextWeekStr);
      setStRemark(`Selected Propira property ${prefillProp.propertyid_no || `#${prefillProp.property_id}`} for deal`);
    } else {
      setStStatus(detail.lead_status === 4 ? 5 : detail.lead_status || 1);
      setStDisqReason(detail.disqualified_reason || 1);
      setStIsPropira(detail.is_propira_property || false);
      setStMatchedPropId(detail.matched_property_id ? String(detail.matched_property_id) : '');
      setStDealCategory(detail.deal_property_category || detail.looking_type || 1);
      setStDealSubcategory(detail.deal_property_subcategory || detail.looking_subcat_type || 0);
      setStDealAddress(detail.deal_property_address || '');
      setStDealLat(detail.deal_location_lat || '');
      setStDealLong(detail.deal_location_long || '');
      setStDealDate(detail.deal_date ? detail.deal_date.slice(0, 10) : todayStr);
      setStRegistryDate(detail.registry_date ? detail.registry_date.slice(0, 10) : nextWeekStr);
      setStRemark('');
    }
    setModalError(null);
    setActionModal('status');
  };

  const openTransferModal = () => {
    if (!detail) return;
    setTrFranchId(detail.assign_franch_id || 0);
    setTrEmployeeId(detail.assigned_to || '');
    setTrRemark('');
    setModalError(null);
    setActionModal('transfer');
  };

  const openReopenModal = () => {
    if (!detail) return;
    setRoRemark('');
    setModalError(null);
    setActionModal('reopen');
  };

  // Submit Reschedule
  const handleSubmitReschedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    setModalError(null);

    if (!rsDate || !rsTime) {
      setModalError('Please choose both follow-up date and time.');
      return;
    }
    const target = new Date(`${rsDate}T${rsTime}:00`);
    if (Number.isNaN(target.getTime()) || target.getTime() <= Date.now()) {
      setModalError('Follow-up date and time must be in the future.');
      return;
    }
    if (!rsRemark.trim()) {
      setModalError('Remark is mandatory when rescheduling.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(
        `${API_BASE}/v1/opportunities/${detail.opportunity_id}/reschedule`,
        {
          method: 'POST',
          headers: authHeaders(true),
          body: JSON.stringify({
            followup_datetime: target.toISOString(),
            current_update: rsCurrentUpdate.trim() || null,
            remark: rsRemark.trim(),
          }),
        }
      );
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to reschedule follow-up.'));
      }
      setActionModal(null);
      setBanner({
        type: 'success',
        text: `Follow-up rescheduled for ${detail.opportunity_code}.`,
      });
      await refreshAll(detail.opportunity_id);
    } catch (err: any) {
      setModalError(err?.message || 'Failed to reschedule follow-up.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Status / Deal Schedule
  const handleSubmitStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    setModalError(null);

    const payload: Record<string, any> = {
      lead_status: stStatus,
      remark: stRemark.trim() || null,
    };

    if (stStatus === 2) {
      if (!stDisqReason) {
        setModalError('Please select a disqualification reason.');
        return;
      }
      payload.disqualified_reason = stDisqReason;
    } else if (stStatus === 4) {
      if (!stDealDate || !stRegistryDate) {
        setModalError('Both Deal Date and Registry Date are required.');
        return;
      }
      const dealIso = new Date(`${stDealDate}T10:00:00`).toISOString();
      const regDt = new Date(`${stRegistryDate}T10:00:00`);
      if (detail.property_type === 2 && regDt.getTime() <= Date.now()) {
        setModalError('Registry Date must be in the future for Buy/Sell opportunities.');
        return;
      }
      payload.deal_date = dealIso;
      payload.registry_date = regDt.toISOString();
      payload.is_propira_property = stIsPropira;
      payload.matched_property_id =
        stIsPropira && stMatchedPropId ? parseInt(stMatchedPropId, 10) : null;
      payload.deal_property_category = stDealCategory || null;
      payload.deal_property_subcategory = stDealSubcategory || null;
      payload.deal_property_address = stDealAddress.trim() || null;
      payload.deal_location_lat = stDealLat.trim() || null;
      payload.deal_location_long = stDealLong.trim() || null;
    }

    setSubmitting(true);
    try {
      const res = await fetch(
        `${API_BASE}/v1/opportunities/${detail.opportunity_id}/status`,
        {
          method: 'POST',
          headers: authHeaders(true),
          body: JSON.stringify(payload),
        }
      );
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to update opportunity status.'));
      }
      setActionModal(null);
      setBanner({
        type: 'success',
        text: `Updated status to ${getStatusMeta(stStatus).label}.`,
      });
      await refreshAll(detail.opportunity_id);
    } catch (err: any) {
      setModalError(err?.message || 'Failed to update status.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Transfer
  const handleSubmitTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    setModalError(null);

    if (!trEmployeeId && trFranchId === detail.assign_franch_id) {
      setModalError('Please choose a staff member or franchise outlet.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(
        `${API_BASE}/v1/opportunities/${detail.opportunity_id}/transfer`,
        {
          method: 'POST',
          headers: authHeaders(true),
          body: JSON.stringify({
            assigned_to: trEmployeeId || null,
            assign_franch_id: trFranchId,
            remark: trRemark.trim() || null,
          }),
        }
      );
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to transfer opportunity.'));
      }
      setActionModal(null);
      setBanner({
        type: 'success',
        text: `Opportunity ${detail.opportunity_code} transferred successfully.`,
      });
      await refreshAll(detail.opportunity_id);
    } catch (err: any) {
      setModalError(err?.message || 'Failed to transfer opportunity.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Reopen
  const handleSubmitReopen = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail) return;
    setModalError(null);
    setSubmitting(true);
    try {
      const res = await fetch(
        `${API_BASE}/v1/opportunities/${detail.opportunity_id}/reopen`,
        {
          method: 'POST',
          headers: authHeaders(true),
          body: JSON.stringify({ remark: roRemark.trim() || 'Reopened for active follow-up' }),
        }
      );
      if (!res.ok) {
        throw new Error(await parseError(res, 'Failed to reopen opportunity.'));
      }
      setActionModal(null);
      setBanner({
        type: 'success',
        text: `Opportunity ${detail.opportunity_code} reopened and moved to In Progress.`,
      });
      await refreshAll(detail.opportunity_id);
    } catch (err: any) {
      setModalError(err?.message || 'Failed to reopen opportunity.');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Form Modal close / save
  const handleFormModalClose = () => {
    setFormModalOpen(false);
    setEditingOpportunity(null);
    setSourceLeadPrefill(null);
    if (fromLeadParam || actionParam) {
      const next = new URLSearchParams(searchParams);
      next.delete('fromLead');
      next.delete('action');
      setSearchParams(next, { replace: true });
    }
  };

  const handleFormSaved = async (saved: OpportunityDetail | OpportunitySummary) => {
    const isEdit = Boolean(editingOpportunity);
    setFormModalOpen(false);
    setEditingOpportunity(null);
    setSourceLeadPrefill(null);

    const next = new URLSearchParams(searchParams);
    next.delete('fromLead');
    next.delete('action');
    if (!isEdit) {
      next.set('tab', 'new');
    }
    next.set('id', String(saved.opportunity_id));
    setSearchParams(next, { replace: true });

    pendingSelectIdRef.current = saved.opportunity_id;
    setBanner({
      type: 'success',
      text: isEdit
        ? `Updated ${saved.opportunity_code}.`
        : `Created opportunity ${saved.opportunity_code}.`,
    });
    await refreshAll(saved.opportunity_id);
  };

  // Chart data
  const chartData = useMemo(() => {
    const cb = dashboard.chart_breakdown;
    return [
      { name: 'Total', value: cb.total, color: '#291BB0' },
      { name: 'Open', value: cb.open, color: '#0ea5e9' },
      { name: 'Disqualified', value: cb.disqualified, color: '#F04B42' },
      { name: 'Qual. Propira', value: cb.qualified_propira, color: '#f59e0b' },
      { name: 'Qual. Other', value: cb.qualified_other, color: '#8b5cf6' },
      { name: 'Closed', value: cb.closed, color: '#10b981' },
    ];
  }, [dashboard]);

  // Combined timeline for History section
  const timelineEntries = useMemo(() => {
    if (!detail) return [];
    const list: {
      id: string;
      kind: 'activity' | 'reschedule';
      title: string;
      note: string | null;
      actor: string | null;
      created_at: string | null;
      extra?: string;
    }[] = [];

    for (const a of detail.activities || ([] as OpportunityActivity[])) {
      list.push({
        id: `act-${a.id}`,
        kind: 'activity',
        title: a.action_type.replace(/_/g, ' '),
        note: a.note,
        actor: a.performed_by_name || a.performed_by,
        created_at: a.created_at,
      });
    }
    for (const r of detail.reschedules || ([] as OpportunityRescheduleLog[])) {
      list.push({
        id: `rs-${r.id}`,
        kind: 'reschedule',
        title: `Rescheduled${r.current_update ? ` • ${r.current_update}` : ''}`,
        note: r.remark,
        actor: r.rescheduled_by_name || r.rescheduled_by,
        created_at: r.created_at,
        extra: r.new_followup_datetime ? `Next: ${formatDateTime(r.new_followup_datetime)}` : undefined,
      });
    }
    return list.sort((a, b) => {
      const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
      const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
      return tb - ta;
    });
  }, [detail]);

  const isLocked = detail ? detail.lead_open === 0 : false;
  const canReopen = detail ? detail.lead_status === 2 : false;
  const dealSubcats = PROPERTY_SUBCATEGORIES_BY_CATEGORY[stDealCategory] || [];

  return (
    <div className="space-y-4">
      {/* Top Header + Actions */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
                Opportunities &amp; Deal Pipeline
              </h1>
              <span className="px-2.5 py-0.5 text-[11px] font-semibold rounded-full bg-[#291BB0]/10 text-[#291BB0] dark:bg-indigo-500/20 dark:text-indigo-300 border border-[#291BB0]/20">
                360° Matching
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Qualify buyer &amp; investor requirements, run live property matching, schedule deals &amp; registry, and close conversions.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setEditingOpportunity(null);
                setSourceLeadPrefill(null);
                setFormModalOpen(true);
              }}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              Create Opportunity
            </button>
            <button
              type="button"
              onClick={handleExportXls}
              disabled={exporting}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors disabled:opacity-60 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 text-[#291BB0] dark:text-indigo-400" />
              {exporting ? 'Exporting...' : 'Export Excel'}
            </button>
            <button
              type="button"
              onClick={() => refreshAll(selectedId)}
              title="Refresh"
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${listLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* KPI Cards + Recharts Breakdown */}
        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 grid grid-cols-1 xl:grid-cols-12 gap-4 items-center">
          {/* 5 KPI Cards */}
          <div className="xl:col-span-7 grid grid-cols-2 sm:grid-cols-5 gap-2.5">
            {[
              {
                key: 'today' as OpportunityTab,
                label: 'Today',
                value: dashboard.counts.today,
                accent: 'text-[#291BB0] dark:text-indigo-300',
              },
              {
                key: 'missing' as OpportunityTab,
                label: 'Missing',
                value: dashboard.counts.missing,
                accent:
                  dashboard.counts.missing > 0
                    ? 'text-[#F04B42] dark:text-red-400'
                    : 'text-slate-700 dark:text-slate-200',
                alert: dashboard.counts.missing > 0,
              },
              {
                key: 'open' as OpportunityTab,
                label: 'Open / Active',
                value: dashboard.counts.open,
                accent: 'text-sky-600 dark:text-sky-400',
              },
              {
                key: 'closed' as OpportunityTab,
                label: 'Closed',
                value: dashboard.counts.closed,
                accent: 'text-emerald-600 dark:text-emerald-400',
              },
              {
                key: 'all' as OpportunityTab,
                label: 'Total',
                value: dashboard.counts.all,
                accent: 'text-slate-900 dark:text-white',
              },
            ].map((kpi) => {
              const isSelected = activeTab === kpi.key;
              return (
                <button
                  key={kpi.key}
                  type="button"
                  onClick={() => setActiveTab(kpi.key)}
                  className={`text-left p-3 rounded-xl border transition-all cursor-pointer ${
                    kpi.alert
                      ? 'bg-amber-50/70 dark:bg-rose-950/30 border-[#F04B42]/40 hover:border-[#F04B42]'
                      : isSelected
                      ? 'bg-[#291BB0]/5 dark:bg-[#291BB0]/20 border-[#291BB0]/50'
                      : 'bg-slate-50/70 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700 hover:border-[#291BB0]/40'
                  }`}
                >
                  <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 truncate">
                    {kpi.label}
                  </div>
                  <div className={`text-xl font-black mt-0.5 ${kpi.accent}`}>
                    {kpi.value}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Recharts BarChart */}
          <div className="xl:col-span-5 h-28 bg-slate-50/70 dark:bg-slate-800/40 rounded-xl border border-slate-200/80 dark:border-slate-700/80 px-2 pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 4, right: 8, left: -24, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#cbd5e1" opacity={0.35} />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 10, fill: '#64748b' }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    fontSize: '11px',
                    borderRadius: '10px',
                    border: '1px solid #e2e8f0',
                  }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={26}>
                  {chartData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 7 Quick Filter Tabs */}
        <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex flex-wrap gap-2">
          {OPPORTUNITY_TABS.map((t) => {
            const isActive = activeTab === t.key;
            const count = dashboard.counts[t.key] ?? 0;
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
      </div>

      {/* Feedback Banner */}
      {banner && (
        <div
          className={`flex items-center justify-between gap-3 px-4 py-3 rounded-xl border text-xs font-medium ${
            banner.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
              : 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {banner.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            )}
            <span>{banner.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setBanner(null)}
            className="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/5"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Split-Screen 2-Pane Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* LEFT PANE: Search + List */}
        <div className="lg:col-span-5 xl:col-span-4 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-3 border-b border-slate-100 dark:border-slate-800 space-y-2.5">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search code, name, mobile, locality..."
                  className="w-full pl-8 pr-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#291BB0]/40"
                />
              </div>

              {speechSupported && (
                <button
                  type="button"
                  onClick={toggleVoiceSearch}
                  title={isListening ? 'Stop voice search' : 'Voice Search'}
                  className={`p-2 rounded-xl border transition-all cursor-pointer ${
                    isListening
                      ? 'bg-[#F04B42] text-white border-[#F04B42] animate-pulse'
                      : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:text-[#291BB0]'
                  }`}
                >
                  {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </button>
              )}
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
              <span>
                Showing <strong className="text-slate-700 dark:text-slate-200">{items.length}</strong> of{' '}
                {total}
              </span>
              {debouncedSearch && (
                <button
                  type="button"
                  onClick={() => setSearchInput('')}
                  className="text-[#291BB0] dark:text-indigo-400 hover:underline font-medium"
                >
                  Clear search
                </button>
              )}
            </div>
          </div>

          {/* List Cards */}
          <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-[68vh] overflow-y-auto">
            {listLoading && items.length === 0 && (
              <div className="py-12 flex items-center justify-center text-xs text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin mr-2 text-[#291BB0]" />
                Loading opportunities...
              </div>
            )}

            {!listLoading && items.length === 0 && (
              <div className="py-12 px-4 text-center space-y-2">
                <Sparkles className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto" />
                <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                  No opportunities in this queue
                </p>
                <p className="text-[11px] text-slate-400">
                  Switch tabs or create a new opportunity to get started.
                </p>
              </div>
            )}

            {items.map((item) => {
              const isSelected = selectedId === item.opportunity_id;
              const statusMeta = getStatusMeta(item.lead_status);
              const firstLocality = item.locations?.[0]?.locality_name;
              const extraLocs =
                item.locations && item.locations.length > 1
                  ? ` (+${item.locations.length - 1})`
                  : '';

              return (
                <button
                  key={item.opportunity_id}
                  type="button"
                  onClick={() => setSelectedId(item.opportunity_id)}
                  className={`w-full text-left p-3.5 transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-[#291BB0]/5 dark:bg-[#291BB0]/20 border-l-4 border-[#291BB0]'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-800/50 border-l-4 border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono font-bold text-[#291BB0] dark:text-indigo-300">
                          {item.opportunity_code}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-semibold">
                          {getPropertyTypeLabel(item.property_type)}
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white truncate mt-0.5">
                        {item.contact_name}
                      </h3>
                    </div>

                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border flex-shrink-0 ${statusMeta.badgeClass}`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${statusMeta.dotClass}`} />
                      {statusMeta.label}
                    </span>
                  </div>

                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-600 dark:text-slate-400">
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {formatBudgetRange(item.budget_from, item.budget_to)}
                    </span>
                    {firstLocality && (
                      <span className="inline-flex items-center gap-1 truncate max-w-[160px]">
                        <MapPin className="w-3 h-3 text-[#F04B42] flex-shrink-0" />
                        <span className="truncate">
                          {firstLocality}
                          {extraLocs}
                        </span>
                      </span>
                    )}
                  </div>

                  <div className="mt-2 flex items-center justify-between gap-2 text-[11px]">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-semibold">
                      <Home className="w-3 h-3" />
                      {item.matching_properties_count} Properties Found
                    </span>

                    <span className="text-slate-500 dark:text-slate-400 truncate">
                      {item.assigned_to_name || item.assigned_to || 'Unassigned'}
                    </span>
                  </div>

                  {item.followup_datetime && (
                    <div className="mt-1.5 flex items-center gap-1 text-[10px] text-slate-400 dark:text-slate-500">
                      <Clock className="w-3 h-3" />
                      <span>Follow-up: {formatDateTime(item.followup_datetime)}</span>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* RIGHT PANE: 360° Opportunity Profile */}
        <div className="lg:col-span-7 xl:col-span-8 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm min-h-[520px]">
          {detailLoading && !detail && (
            <div className="py-24 flex items-center justify-center text-xs text-slate-400">
              <Loader2 className="w-5 h-5 animate-spin mr-2 text-[#291BB0]" />
              Loading 360° opportunity profile...
            </div>
          )}

          {!detailLoading && !detail && (
            <div className="py-24 px-6 text-center space-y-2">
              <Building2 className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto" />
              <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">
                Select an Opportunity
              </h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Choose an opportunity from the left queue to inspect full requirements, matching inventory, and deal actions.
              </p>
            </div>
          )}

          {detail && (
            <div className="p-5 space-y-5">
              {/* Profile Header */}
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 pb-4 border-b border-slate-100 dark:border-slate-800">
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-md bg-[#291BB0]/10 text-[#291BB0] dark:bg-indigo-500/20 dark:text-indigo-300">
                      {detail.opportunity_code}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold border ${
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
                    {detail.source_lead_id && (
                      <Link
                        to={`/leads/${encodeURIComponent(detail.source_lead_id)}`}
                        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:text-[#291BB0] dark:hover:text-indigo-300 border border-slate-200 dark:border-slate-700"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Lead: {detail.source_lead_id}
                      </Link>
                    )}
                  </div>

                  <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                    {detail.contact_name}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {detail.customer_type === 'INVESTOR' ? 'Investor' : 'End User'} ·{' '}
                    {getPropertyTypeLabel(detail.property_type)} · Created{' '}
                    {formatDateTime(detail.created_at)}
                  </p>
                </div>

                {/* X Properties Found Green Clickable Badge */}
                <button
                  type="button"
                  onClick={() => setRelatedModalOpen(true)}
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition-colors cursor-pointer flex-shrink-0"
                >
                  <Home className="w-4 h-4" />
                  <span>{detail.matching_properties_count} Properties Found</span>
                </button>
              </div>

              {/* Quick Action Toolbar */}
              <div className="flex flex-wrap items-center gap-2">
                {/* 1. Call User */}
                <a
                  href={`tel:${detail.mobile}`}
                  onClick={handleCallUser}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white text-xs font-semibold shadow-sm transition-colors"
                >
                  <PhoneCall className="w-3.5 h-3.5" />
                  Call User
                </a>

                {/* 2. Reschedule */}
                <button
                  type="button"
                  onClick={openRescheduleModal}
                  disabled={isLocked}
                  title={isLocked ? 'Locked — Reopen or Closed' : 'Reschedule Follow-up'}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors disabled:opacity-45 disabled:cursor-not-allowed cursor-pointer"
                >
                  <CalendarClock className="w-3.5 h-3.5 text-amber-500" />
                  Reschedule
                </button>

                {/* 3. Status / Deal Schedule */}
                <button
                  type="button"
                  onClick={() => openStatusModal()}
                  disabled={isLocked}
                  title={isLocked ? 'Locked — Reopen required' : 'Change Status / Deal Schedule'}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors disabled:opacity-45 disabled:cursor-not-allowed cursor-pointer"
                >
                  <SlidersHorizontal className="w-3.5 h-3.5 text-[#291BB0] dark:text-indigo-400" />
                  Status / Deal
                </button>

                {/* 4. Transfer */}
                <button
                  type="button"
                  onClick={openTransferModal}
                  disabled={isLocked}
                  title={isLocked ? 'Locked — Reopen required' : 'Transfer Opportunity'}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors disabled:opacity-45 disabled:cursor-not-allowed cursor-pointer"
                >
                  <ArrowRightLeft className="w-3.5 h-3.5 text-sky-500" />
                  Transfer
                </button>

                {/* 5. Reopen (when Disqualified) */}
                {canReopen && (
                  <button
                    type="button"
                    onClick={openReopenModal}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Reopen
                  </button>
                )}

                {/* 6. Edit */}
                <button
                  type="button"
                  onClick={() => {
                    setEditingOpportunity(detail);
                    setSourceLeadPrefill(null);
                    setFormModalOpen(true);
                  }}
                  disabled={isLocked}
                  title={isLocked ? 'Locked — Cannot edit closed/disqualified opportunity' : 'Edit Opportunity'}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors disabled:opacity-45 disabled:cursor-not-allowed cursor-pointer"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  Edit
                </button>

                {/* 7. History */}
                <button
                  type="button"
                  onClick={() => {
                    setHistoryOpen(true);
                    historyRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold transition-colors cursor-pointer"
                >
                  <History className="w-3.5 h-3.5" />
                  History ({timelineEntries.length})
                </button>
              </div>

              {/* Lock Notice */}
              {isLocked && (
                <div className="flex items-center justify-between gap-3 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300">
                  <div className="flex items-center gap-2">
                    <Lock className="w-4 h-4 flex-shrink-0" />
                    <span>
                      {detail.lead_status === 5
                        ? 'This opportunity is permanently Closed / Won.'
                        : `Disqualified${detail.disqualified_reason_label ? ` (${detail.disqualified_reason_label})` : ''}. Reopen to resume follow-ups or edits.`}
                    </span>
                  </div>
                  {canReopen && (
                    <button
                      type="button"
                      onClick={openReopenModal}
                      className="px-3 py-1 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-semibold cursor-pointer"
                    >
                      Reopen Now
                    </button>
                  )}
                </div>
              )}

              {/* 360° Requirement Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Contact & Client Type */}
                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#291BB0] dark:text-indigo-400">
                    <User className="w-3.5 h-3.5" />
                    Client &amp; Contact
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200">
                      <Phone className="w-3.5 h-3.5 text-slate-400" />
                      <span className="font-semibold">{detail.mobile}</span>
                      {detail.alternate_mobile && (
                        <span className="text-slate-400">/ {detail.alternate_mobile}</span>
                      )}
                    </div>
                    {detail.email && (
                      <div className="flex items-center gap-2 text-slate-600 dark:text-slate-300">
                        <Mail className="w-3.5 h-3.5 text-slate-400" />
                        <span>{detail.email}</span>
                      </div>
                    )}
                    {detail.address && (
                      <div className="flex items-start gap-2 text-slate-600 dark:text-slate-300">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 mt-0.5 flex-shrink-0" />
                        <span>{detail.address}</span>
                      </div>
                    )}
                    <div className="pt-1 flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded bg-slate-200/70 dark:bg-slate-700 text-[11px] font-semibold text-slate-700 dark:text-slate-200">
                        {detail.customer_type === 'INVESTOR' ? 'Investor' : 'End User'}
                      </span>
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                        Calls Logged: {detail.calls_status}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Property Preferences & Budget */}
                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#291BB0] dark:text-indigo-400">
                    <IndianRupee className="w-3.5 h-3.5" />
                    Property &amp; Budget
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 font-semibold">Category</span>
                      <p className="font-semibold text-slate-800 dark:text-slate-200">
                        {getCategoryLabel(detail.looking_type)} ·{' '}
                        {getSubcategoryLabel(detail.looking_type, detail.looking_subcat_type)}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 font-semibold">Budget</span>
                      <p className="font-bold text-[#291BB0] dark:text-indigo-300">
                        {formatBudgetRange(detail.budget_from, detail.budget_to)}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 font-semibold">Area</span>
                      <p className="font-medium text-slate-700 dark:text-slate-300">
                        {detail.area_from || detail.area_to
                          ? `${detail.area_from || 0} – ${detail.area_to || 0} ${detail.area_unit}`
                          : 'Any'}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 font-semibold">Specs</span>
                      <p className="font-medium text-slate-700 dark:text-slate-300">
                        {detail.bhk > 0 ? `${detail.bhk} BHK` : 'Any BHK'}
                        {detail.furnishing ? ` · ${detail.furnishing}` : ''}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 font-semibold">Age / Loan</span>
                      <p className="font-medium text-slate-700 dark:text-slate-300">
                        {detail.property_age || 'Any'} · Loan: {detail.loanable || 'MAYBE'}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 font-semibold">Next Follow-up</span>
                      <p className="font-medium text-slate-700 dark:text-slate-300">
                        {formatDateTime(detail.followup_datetime)}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Target Localities */}
                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#291BB0] dark:text-indigo-400">
                    <MapPin className="w-3.5 h-3.5" />
                    Preferred Localities ({detail.locations?.length || 0})
                  </div>
                  {detail.locations && detail.locations.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {detail.locations.map((loc, idx) => (
                        <div
                          key={`${loc.locality_name}-${idx}`}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs"
                        >
                          <span className="font-semibold text-slate-800 dark:text-slate-200">
                            {loc.locality_name}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            ({loc.radius_km} km)
                          </span>
                          {loc.latitude != null && loc.longitude != null && (
                            <a
                              href={`https://www.google.com/maps?q=${loc.latitude},${loc.longitude}`}
                              target="_blank"
                              rel="noreferrer"
                              title={`Lat: ${loc.latitude}, Lng: ${loc.longitude}`}
                              className="text-[#291BB0] dark:text-indigo-400 hover:underline inline-flex items-center"
                            >
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No preferred localities specified.</p>
                  )}
                </div>

                {/* Assignment & Remarks */}
                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#291BB0] dark:text-indigo-400">
                    <UserCheck className="w-3.5 h-3.5" />
                    Assignment &amp; Remarks
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between gap-2">
                      <span className="text-slate-400">Assigned Staff:</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {detail.assigned_to_name || detail.assigned_to || 'Unassigned'}
                      </span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span className="text-slate-400">Franchise Outlet:</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {detail.franchise_name || (detail.assign_franch_id > 0 ? `#${detail.assign_franch_id}` : 'Central Desk')}
                      </span>
                    </div>
                    {(detail.current_update || detail.last_remark || detail.remark) && (
                      <div className="pt-1.5 border-t border-slate-200/70 dark:border-slate-700/70 text-slate-600 dark:text-slate-300">
                        {detail.current_update && (
                          <p>
                            <span className="font-semibold">Update:</span> {detail.current_update}
                          </p>
                        )}
                        {(detail.last_remark || detail.remark) && (
                          <p className="mt-0.5">
                            <span className="font-semibold">Remark:</span>{' '}
                            {detail.last_remark || detail.remark}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Deal & Registry Summary Card (when status 4 or 5) */}
              {(detail.lead_status === 4 || detail.lead_status === 5 || detail.deal_date) && (
                <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-800/70 bg-emerald-50/50 dark:bg-emerald-950/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                      <Calendar className="w-4 h-4" />
                      Deal &amp; Registry Schedule
                    </div>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-600 text-white">
                      {detail.is_propira_property ? 'Propira Inventory' : 'External Property'}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 font-semibold">Deal Date</span>
                      <p className="font-semibold text-slate-800 dark:text-slate-200">
                        {formatDateTime(detail.deal_date)}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 font-semibold">Registry Date</span>
                      <p className="font-semibold text-slate-800 dark:text-slate-200">
                        {formatDateTime(detail.registry_date)}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] uppercase text-slate-400 font-semibold">Property</span>
                      <p className="font-semibold text-slate-800 dark:text-slate-200">
                        {detail.matched_property_code ||
                          (detail.matched_property_id ? `#${detail.matched_property_id}` : 'External')}
                      </p>
                    </div>
                  </div>
                  {detail.deal_property_address && (
                    <p className="text-xs text-slate-600 dark:text-slate-300">
                      <span className="font-semibold">Address:</span> {detail.deal_property_address}
                    </p>
                  )}
                </div>
              )}

              {/* Collapsible History Timeline */}
              <div
                ref={historyRef}
                className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => setHistoryOpen((p) => !p)}
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800/60 flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-200 cursor-pointer"
                >
                  <span className="flex items-center gap-2">
                    <History className="w-4 h-4 text-[#291BB0] dark:text-indigo-400" />
                    Activity &amp; Reschedule Timeline ({timelineEntries.length})
                  </span>
                  {historyOpen ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>

                {historyOpen && (
                  <div className="p-4 space-y-3 max-h-72 overflow-y-auto">
                    {timelineEntries.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No activity logged yet.</p>
                    ) : (
                      timelineEntries.map((entry) => (
                        <div
                          key={entry.id}
                          className="flex items-start gap-3 text-xs pb-3 border-b border-slate-100 dark:border-slate-800 last:border-b-0 last:pb-0"
                        >
                          <div
                            className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${
                              entry.kind === 'reschedule' ? 'bg-amber-500' : 'bg-[#291BB0]'
                            }`}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-semibold text-slate-800 dark:text-slate-200">
                                {entry.title}
                              </span>
                              <span className="text-[10px] text-slate-400 flex-shrink-0">
                                {formatDateTime(entry.created_at)}
                              </span>
                            </div>
                            {entry.extra && (
                              <p className="text-[11px] text-amber-600 dark:text-amber-400 font-medium mt-0.5">
                                {entry.extra}
                              </p>
                            )}
                            {entry.note && (
                              <p className="text-slate-600 dark:text-slate-400 mt-0.5">
                                {entry.note}
                              </p>
                            )}
                            {entry.actor && (
                              <p className="text-[10px] text-slate-400 mt-0.5">
                                By: {entry.actor}
                              </p>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create / Edit Opportunity Modal */}
      <OpportunityFormModal
        isOpen={formModalOpen}
        onClose={handleFormModalClose}
        onSaved={handleFormSaved}
        editingOpportunity={editingOpportunity}
        sourceLeadPrefill={sourceLeadPrefill}
      />

      {/* Related Properties Matching Modal */}
      <RelatedPropertiesModal
        isOpen={relatedModalOpen}
        onClose={() => setRelatedModalOpen(false)}
        opportunity={detail}
        onSelectForDeal={(prop) => {
          setRelatedModalOpen(false);
          openStatusModal(prop);
        }}
      />

      {/* Action Modals (Reschedule, Status/Deal, Transfer, Reopen) */}
      {actionModal && detail && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget && !submitting) setActionModal(null);
          }}
        >
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                {actionModal === 'reschedule' && 'Reschedule Follow-up'}
                {actionModal === 'status' && 'Update Status / Deal Schedule'}
                {actionModal === 'transfer' && 'Transfer Opportunity'}
                {actionModal === 'reopen' && 'Reopen Opportunity'}
              </h3>
              <button
                type="button"
                onClick={() => !submitting && setActionModal(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 max-h-[80vh] overflow-y-auto">
              {modalError && (
                <div className="mb-4 flex items-start gap-2.5 p-3 rounded-xl bg-[#F04B42]/10 border border-[#F04B42]/30 text-[#F04B42] text-xs">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>{modalError}</span>
                </div>
              )}

              {/* 1. Reschedule Form */}
              {actionModal === 'reschedule' && (
                <form onSubmit={handleSubmitReschedule} className="space-y-3.5 text-xs">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                        Next Date <span className="text-[#F04B42]">*</span>
                      </label>
                      <input
                        type="date"
                        value={rsDate}
                        onChange={(e) => setRsDate(e.target.value)}
                        required
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                        Next Time <span className="text-[#F04B42]">*</span>
                      </label>
                      <input
                        type="time"
                        value={rsTime}
                        onChange={(e) => setRsTime(e.target.value)}
                        required
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                      Current Update
                    </label>
                    <input
                      type="text"
                      value={rsCurrentUpdate}
                      onChange={(e) => setRsCurrentUpdate(e.target.value)}
                      placeholder="e.g. Site visit planned, Waiting for family confirmation"
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                      Remark <span className="text-[#F04B42]">*</span>
                    </label>
                    <textarea
                      rows={3}
                      value={rsRemark}
                      onChange={(e) => setRsRemark(e.target.value)}
                      required
                      placeholder="Mandatory note for rescheduling..."
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setActionModal(null)}
                      className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-4 py-2 rounded-lg bg-[#291BB0] hover:bg-[#1f138e] text-white font-semibold disabled:opacity-60"
                    >
                      {submitting ? 'Saving...' : 'Save Reschedule'}
                    </button>
                  </div>
                </form>
              )}

              {/* 2. Status / Deal Schedule Form */}
              {actionModal === 'status' && (
                <form onSubmit={handleSubmitStatus} className="space-y-3.5 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                      Target Status
                    </label>
                    <select
                      value={stStatus}
                      onChange={(e) => setStStatus(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    >
                      <option value={1}>In Progress</option>
                      <option value={2}>Disqualified (Locks Opportunity)</option>
                      <option value={4}>Qualified — Deal &amp; Registry Schedule (Option 1)</option>
                      <option value={5}>Closed / Won — Deal Done (Option 2)</option>
                    </select>
                  </div>

                  {stStatus === 2 && (
                    <div>
                      <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                        Disqualification Reason <span className="text-[#F04B42]">*</span>
                      </label>
                      <select
                        value={stDisqReason}
                        onChange={(e) => setStDisqReason(Number(e.target.value))}
                        className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                      >
                        {Object.entries(DISQUALIFIED_REASONS).map(([code, label]) => (
                          <option key={code} value={code}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {stStatus === 4 && (
                    <div className="space-y-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                            Deal Date <span className="text-[#F04B42]">*</span>
                          </label>
                          <input
                            type="date"
                            value={stDealDate}
                            onChange={(e) => setStDealDate(e.target.value)}
                            required
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                          />
                        </div>
                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                            Registry Date <span className="text-[#F04B42]">*</span>
                          </label>
                          <input
                            type="date"
                            value={stRegistryDate}
                            onChange={(e) => setStRegistryDate(e.target.value)}
                            required
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                          />
                        </div>
                      </div>

                      <label className="flex items-center gap-2 font-semibold text-slate-700 dark:text-slate-200 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={stIsPropira}
                          onChange={(e) => setStIsPropira(e.target.checked)}
                          className="rounded border-slate-300 text-[#291BB0]"
                        />
                        Propira Inventory Property
                      </label>

                      {stIsPropira && (
                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                            Matched Property ID
                          </label>
                          <input
                            type="number"
                            value={stMatchedPropId}
                            onChange={(e) => setStMatchedPropId(e.target.value)}
                            placeholder="Property ID"
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                          />
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                            Property Category
                          </label>
                          <select
                            value={stDealCategory}
                            onChange={(e) => {
                              const c = Number(e.target.value);
                              setStDealCategory(c);
                              setStDealSubcategory(
                                PROPERTY_SUBCATEGORIES_BY_CATEGORY[c]?.[0]?.id ?? 0
                              );
                            }}
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                          >
                            {PROPERTY_CATEGORIES.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                            Sub-category
                          </label>
                          <select
                            value={stDealSubcategory}
                            onChange={(e) => setStDealSubcategory(Number(e.target.value))}
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                          >
                            <option value={0}>Any</option>
                            {dealSubcats.map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                          Property Address
                        </label>
                        <input
                          type="text"
                          value={stDealAddress}
                          onChange={(e) => setStDealAddress(e.target.value)}
                          placeholder="Deal property address"
                          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                            Latitude
                          </label>
                          <input
                            type="text"
                            value={stDealLat}
                            onChange={(e) => setStDealLat(e.target.value)}
                            placeholder="Optional"
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                          />
                        </div>
                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                            Longitude
                          </label>
                          <input
                            type="text"
                            value={stDealLong}
                            onChange={(e) => setStDealLong(e.target.value)}
                            placeholder="Optional"
                            className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {stStatus === 5 && (
                    <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300">
                      Closing / Winning permanently locks this opportunity. Deal &amp; Registry Schedule (Option 1) must already be recorded.
                    </div>
                  )}

                  <div>
                    <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                      Remark
                    </label>
                    <textarea
                      rows={2}
                      value={stRemark}
                      onChange={(e) => setStRemark(e.target.value)}
                      placeholder="Optional status change note..."
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setActionModal(null)}
                      className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-4 py-2 rounded-lg bg-[#291BB0] hover:bg-[#1f138e] text-white font-semibold disabled:opacity-60"
                    >
                      {submitting ? 'Updating...' : 'Update Status'}
                    </button>
                  </div>
                </form>
              )}

              {/* 3. Transfer Form */}
              {actionModal === 'transfer' && (
                <form onSubmit={handleSubmitTransfer} className="space-y-3.5 text-xs">
                  <div>
                    <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                      Franchise Outlet
                    </label>
                    <select
                      value={trFranchId}
                      onChange={(e) => setTrFranchId(Number(e.target.value))}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    >
                      <option value={0}>Central Desk</option>
                      {outlets
                        .filter((o) => o.is_active)
                        .map((o) => (
                          <option key={o.id} value={o.id}>
                            {o.name} ({o.city})
                          </option>
                        ))}
                    </select>
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                      Assign Staff
                    </label>
                    <select
                      value={trEmployeeId}
                      onChange={(e) => setTrEmployeeId(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    >
                      <option value="">Keep current / Unassigned</option>
                      {assignees.map((a) => (
                        <option key={a.employee_id} value={a.employee_id}>
                          {a.name}
                          {a.role_name ? ` (${a.role_name})` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                      Transfer Remark
                    </label>
                    <textarea
                      rows={2}
                      value={trRemark}
                      onChange={(e) => setTrRemark(e.target.value)}
                      placeholder="Reason for transfer..."
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setActionModal(null)}
                      className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-4 py-2 rounded-lg bg-[#291BB0] hover:bg-[#1f138e] text-white font-semibold disabled:opacity-60"
                    >
                      {submitting ? 'Transferring...' : 'Transfer Opportunity'}
                    </button>
                  </div>
                </form>
              )}

              {/* 4. Reopen Form */}
              {actionModal === 'reopen' && (
                <form onSubmit={handleSubmitReopen} className="space-y-3.5 text-xs">
                  <p className="text-slate-600 dark:text-slate-300">
                    Reopening <strong>{detail.opportunity_code}</strong> will move it back to{' '}
                    <strong>In Progress</strong> and unlock follow-ups, editing, and transfers.
                  </p>
                  <div>
                    <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-1">
                      Remark
                    </label>
                    <textarea
                      rows={2}
                      value={roRemark}
                      onChange={(e) => setRoRemark(e.target.value)}
                      placeholder="Reason for reopening..."
                      className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setActionModal(null)}
                      className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-semibold disabled:opacity-60"
                    >
                      {submitting ? 'Reopening...' : 'Reopen Opportunity'}
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

export default OpportunitiesHub;
