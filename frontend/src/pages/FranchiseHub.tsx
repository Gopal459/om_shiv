import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Sparkles,
  CheckCircle2,
  Handshake,
  Building2,
  Users,
  Wallet,
  Plus,
  RefreshCw,
  Search,
  Power,
  ArrowRight,
  Layers,
  X,
  AlertCircle,
  MapPin,
  Phone,
  ShieldAlert,
  Award,
  ArrowUpRight,
  Eye,
  Calendar,
  Link2,
  Copy,
  Lock,
} from 'lucide-react';

type CPType = 'BROKER_CP' | 'ACTIVE_CP' | 'REFERRAL_PARTNER' | 'CREATOR_PARTNER';

interface FranchiseOverview {
  channel_partners: { total: number; active: number; by_tier?: Record<string, number> };
  franchise_outlets: { total: number; active: number; cities: string[] };
  partner_sourced_leads: { total: number; converted: number };
  settled_payouts: { count: number; pending_count: number; total_amount: number };
  pending_meetings?: number;
}

const CP_TYPE_META: Record<CPType, { label: string; short: string; color: string }> = {
  BROKER_CP: {
    label: 'Broker CP (Co-Broking)',
    short: 'Broker CP',
    color: 'bg-blue-500/10 text-blue-600 dark:text-blue-300 border-blue-500/20',
  },
  ACTIVE_CP: {
    label: 'Active CP (L1–L3 Ladder)',
    short: 'Active CP',
    color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-300 border-emerald-500/20',
  },
  REFERRAL_PARTNER: {
    label: 'Referral Partner (Fixed Reward)',
    short: 'Referral',
    color: 'bg-amber-500/10 text-amber-600 dark:text-amber-300 border-amber-500/20',
  },
  CREATOR_PARTNER: {
    label: 'Creator Partner (Influencer)',
    short: 'Creator',
    color: 'bg-purple-500/10 text-purple-600 dark:text-purple-300 border-purple-500/20',
  },
};

const getAuthHeaders = (): Record<string, string> => {
  const token = localStorage.getItem('access_token');
  return token
    ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    : { 'Content-Type': 'application/json' };
};

const formatINR = (amount: number) => {
  if (!amount) return '₹0';
  if (amount >= 10_000_000) return `₹${(amount / 10_000_000).toFixed(2)} Cr`;
  if (amount >= 100_000) return `₹${(amount / 100_000).toFixed(2)} L`;
  return `₹${amount.toLocaleString('en-IN')}`;
};

export const FranchiseHub: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const typeParam = searchParams.get('type')?.toLowerCase();

  const activeTab = useMemo<'partners' | 'outlets' | 'meetings' | 'leads' | 'payouts'>(() => {
    if (
      typeParam === 'outlets' ||
      typeParam === 'meetings' ||
      typeParam === 'leads' ||
      typeParam === 'payouts'
    ) {
      return typeParam;
    }
    return 'partners';
  }, [typeParam]);

  const setActiveTab = (tab: 'partners' | 'outlets' | 'meetings' | 'leads' | 'payouts') => {
    setSearchParams({ type: tab }, { replace: true });
  };

  const [overview, setOverview] = useState<FranchiseOverview>({
    channel_partners: { total: 0, active: 0, by_tier: {} },
    franchise_outlets: { total: 0, active: 0, cities: [] },
    partner_sourced_leads: { total: 0, converted: 0 },
    settled_payouts: { count: 0, pending_count: 0, total_amount: 0 },
    pending_meetings: 0,
  });
  const [partners, setPartners] = useState<any[]>([]);
  const [outlets, setOutlets] = useState<any[]>([]);
  const [meetings, setMeetings] = useState<any[]>([]);
  const [leads, setLeads] = useState<any[]>([]);
  const [payouts, setPayouts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [cpTierFilter, setCpTierFilter] = useState<'ALL' | CPType>('ALL');
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modals
  const [modalType, setModalType] = useState<'partner' | 'outlet' | 'payout' | 'meeting' | 'suspend' | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [suspendTarget, setSuspendTarget] = useState<any>(null);
  const [suspendReason, setSuspendReason] = useState('');

  // Inventory Access Preview Modal
  const [previewData, setPreviewData] = useState<any>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewPartnerName, setPreviewPartnerName] = useState('');

  // Partner form
  const [pType, setPType] = useState<CPType>('BROKER_CP');
  const [pName, setPName] = useState('');
  const [pCompany, setPCompany] = useState('');
  const [pMobile, setPMobile] = useState('');
  const [pCity, setPCity] = useState('Jaipur');
  const [pRera, setPRera] = useState('');
  const [pOutletId, setPOutletId] = useState<string>('');
  const [pComm, setPComm] = useState('2.0');
  // Tier-specific partner fields
  const [pHasOffice, setPHasOffice] = useState(true);
  const [pOfficeAddress, setPOfficeAddress] = useState('');
  const [pCoSplit, setPCoSplit] = useState('50');
  const [pFixedReward, setPFixedReward] = useState('5000');
  const [pAnnualLimit, setPAnnualLimit] = useState('5');
  const [pTrackingCode, setPTrackingCode] = useState('');
  const [pSocialHandle, setPSocialHandle] = useState('');
  const [pTopCreator, setPTopCreator] = useState(false);
  const [pRetainer, setPRetainer] = useState('0');

  // Outlet form
  const [oName, setOName] = useState('');
  const [oCity, setOCity] = useState('Jaipur');
  const [oLocality, setOLocality] = useState('');
  const [oManager, setOManager] = useState('');
  const [oMobile, setOMobile] = useState('');

  // Payout form
  const [payPartnerId, setPayPartnerId] = useState('');
  const [payLeadId, setPayLeadId] = useState('');
  const [payProp, setPayProp] = useState('');
  const [payDeal, setPayDeal] = useState('');
  const [payComm, setPayComm] = useState('');
  const [payNote, setPayNote] = useState('');

  // Meeting form
  const [mPartnerId, setMPartnerId] = useState('');
  const [mPropertyId, setMPropertyId] = useState('');
  const [mLeadId, setMLeadId] = useState('');
  const [mSlot, setMSlot] = useState('');
  const [mNotes, setMNotes] = useState('');

  const fetchAll = async () => {
    setLoading(true);
    try {
      const headers = getAuthHeaders();
      const [ovRes, pRes, oRes, mRes, lRes, payRes] = await Promise.all([
        fetch('/v1/franchise/overview', { headers }),
        fetch('/v1/franchise/partners', { headers }),
        fetch('/v1/franchise/outlets', { headers }),
        fetch('/v1/franchise/meetings', { headers }),
        fetch('/v1/franchise/leads', { headers }),
        fetch('/v1/franchise/payouts', { headers }),
      ]);
      if (ovRes.ok) setOverview(await ovRes.json());
      if (pRes.ok) setPartners((await pRes.json()).partners || []);
      if (oRes.ok) setOutlets((await oRes.json()).outlets || []);
      if (mRes.ok) setMeetings((await mRes.json()).meetings || []);
      if (lRes.ok) setLeads((await lRes.json()).leads || []);
      if (payRes.ok) setPayouts((await payRes.json()).payouts || []);
    } catch {
      setBanner({ type: 'error', text: 'Failed to load Franchise & Partner data.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleApiError = async (res: Response, fallback: string) => {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || fallback);
  };

  const handleCreatePartner = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setBanner(null);
    try {
      const res = await fetch('/v1/franchise/partners', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          cp_type: pType,
          full_name: pName,
          company_name: pCompany || undefined,
          mobile: pMobile,
          city: pCity,
          rera_number: pRera || undefined,
          outlet_id: pOutletId ? Number(pOutletId) : undefined,
          commission_pct: Number(pComm) || 2.0,
          has_office_setup: pType === 'BROKER_CP' ? pHasOffice : false,
          office_address: pType === 'BROKER_CP' ? pOfficeAddress || undefined : undefined,
          co_broking_split_pct: pType === 'BROKER_CP' ? Number(pCoSplit) || 50 : 50,
          fixed_reward_amount: pType === 'REFERRAL_PARTNER' ? Number(pFixedReward) || 5000 : 5000,
          annual_reward_limit: pType === 'REFERRAL_PARTNER' ? Number(pAnnualLimit) || 5 : 5,
          tracking_code: pType === 'CREATOR_PARTNER' && pTrackingCode ? pTrackingCode : undefined,
          social_handle: pType === 'CREATOR_PARTNER' ? pSocialHandle || undefined : undefined,
          is_top_creator: pType === 'CREATOR_PARTNER' ? pTopCreator : false,
          monthly_retainer_amount: pType === 'CREATOR_PARTNER' ? Number(pRetainer) || 0 : 0,
        }),
      });
      if (!res.ok) await handleApiError(res, 'Could not add partner');
      setModalType(null);
      setPName('');
      setPCompany('');
      setPMobile('');
      setPRera('');
      setPOfficeAddress('');
      setPTrackingCode('');
      setPSocialHandle('');
      setBanner({ type: 'success', text: `${CP_TYPE_META[pType].short} registered successfully.` });
      await fetchAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateOutlet = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setBanner(null);
    try {
      const res = await fetch('/v1/franchise/outlets', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name: oName,
          city: oCity,
          locality: oLocality || undefined,
          manager_name: oManager || undefined,
          manager_mobile: oMobile || undefined,
        }),
      });
      if (!res.ok) await handleApiError(res, 'Could not create outlet');
      setModalType(null);
      setOName('');
      setOLocality('');
      setOManager('');
      setOMobile('');
      setBanner({ type: 'success', text: 'Franchise Outlet created successfully.' });
      await fetchAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreatePayout = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!payPartnerId) return;
    setSubmitting(true);
    setBanner(null);
    try {
      const res = await fetch('/v1/franchise/payouts', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          partner_id: Number(payPartnerId),
          lead_id: payLeadId || undefined,
          property_title: payProp || undefined,
          deal_amount: Number(payDeal) || 0,
          commission_amount: Number(payComm) || 0,
          status: 'PENDING',
          note: payNote || undefined,
        }),
      });
      if (!res.ok) await handleApiError(res, 'Could not create payout');
      setModalType(null);
      setPayLeadId('');
      setPayProp('');
      setPayDeal('');
      setPayComm('');
      setPayNote('');
      setBanner({ type: 'success', text: 'Payout recorded successfully.' });
      await fetchAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateMeeting = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mPartnerId) return;
    setSubmitting(true);
    setBanner(null);
    try {
      const res = await fetch('/v1/franchise/meetings', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          partner_id: Number(mPartnerId),
          property_id: mPropertyId,
          lead_id: mLeadId || undefined,
          requested_slot: mSlot ? new Date(mSlot).toISOString() : new Date().toISOString(),
          notes: mNotes || undefined,
        }),
      });
      if (!res.ok) await handleApiError(res, 'Could not schedule mediated meeting');
      setModalType(null);
      setMPropertyId('');
      setMLeadId('');
      setMNotes('');
      setBanner({ type: 'success', text: 'L3 Omshiv-mediated meeting requested.' });
      await fetchAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCertify = async (partner: any) => {
    setBanner(null);
    try {
      const res = await fetch(`/v1/franchise/partners/${partner.id}/certify`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!res.ok) await handleApiError(res, 'Certification failed');
      setBanner({ type: 'success', text: `${partner.full_name} marked Certified.` });
      await fetchAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message });
    }
  };

  const handlePromote = async (partner: any, targetLevel: 'L2' | 'L3') => {
    setBanner(null);
    try {
      const res = await fetch(`/v1/franchise/partners/${partner.id}/promote`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ target_level: targetLevel }),
      });
      if (!res.ok) await handleApiError(res, `Promotion to ${targetLevel} blocked`);
      setBanner({ type: 'success', text: `${partner.full_name} promoted to ${targetLevel}!` });
      await fetchAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message });
    }
  };

  const handleConfirmSuspend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!suspendTarget) return;
    setSubmitting(true);
    setBanner(null);
    try {
      const res = await fetch(`/v1/franchise/partners/${suspendTarget.id}/suspend`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ reason: suspendReason }),
      });
      if (!res.ok) await handleApiError(res, 'Suspension failed');
      setModalType(null);
      setSuspendTarget(null);
      setSuspendReason('');
      setBanner({ type: 'success', text: `${suspendTarget.full_name} suspended immediately — all access revoked.` });
      await fetchAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReinstate = async (partner: any) => {
    setBanner(null);
    try {
      const res = await fetch(`/v1/franchise/partners/${partner.id}/reinstate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ note: 'Reinstated after admin review' }),
      });
      if (!res.ok) await handleApiError(res, 'Reinstate failed');
      setBanner({ type: 'success', text: `${partner.full_name} reinstated.` });
      await fetchAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message });
    }
  };

  const handlePreviewInventory = async (partner: any) => {
    setPreviewPartnerName(`${partner.full_name} (${CP_TYPE_META[partner.cp_type as CPType]?.short || partner.cp_type})`);
    setPreviewData(null);
    setPreviewError(null);
    try {
      const res = await fetch(`/v1/franchise/partners/${partner.id}/inventory`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        setPreviewError(err.detail || 'Access blocked');
      } else {
        setPreviewData(await res.json());
      }
    } catch (err: any) {
      setPreviewError(err.message);
    }
  };

  const handleGenerateRetainers = async () => {
    setBanner(null);
    try {
      const res = await fetch('/v1/franchise/payouts/generate-retainers', {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!res.ok) await handleApiError(res, 'Could not generate retainers');
      const data = await res.json();
      setBanner({
        type: 'success',
        text: `Retainers for ${data.month}: ${data.generated_count} created, ${data.skipped_existing} already existed.`,
      });
      await fetchAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message });
    }
  };

  const toggleOutletActive = async (outlet: any) => {
    const res = await fetch(`/v1/franchise/outlets/${outlet.id}`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({ is_active: !outlet.is_active }),
    });
    if (res.ok) await fetchAll();
  };

  const markPayoutSettled = async (payoutId: number) => {
    const res = await fetch(`/v1/franchise/payouts/${payoutId}`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({ status: 'SETTLED' }),
    });
    if (res.ok) {
      setBanner({ type: 'success', text: 'Payout marked as SETTLED.' });
      await fetchAll();
    }
  };

  const updateMeetingStatus = async (meetingId: number, statusVal: string) => {
    const res = await fetch(`/v1/franchise/meetings/${meetingId}`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({ status: statusVal }),
    });
    if (res.ok) {
      setBanner({ type: 'success', text: `Meeting status updated to ${statusVal}.` });
      await fetchAll();
    }
  };

  const filteredPartners = useMemo(() => {
    return partners.filter((p) => {
      if (cpTierFilter !== 'ALL' && p.cp_type !== cpTierFilter) return false;
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        p.full_name?.toLowerCase().includes(q) ||
        p.company_name?.toLowerCase().includes(q) ||
        p.partner_code?.toLowerCase().includes(q) ||
        p.tracking_code?.toLowerCase().includes(q) ||
        p.mobile?.includes(q) ||
        p.city?.toLowerCase().includes(q)
      );
    });
  }, [partners, cpTierFilter, searchQuery]);

  const filteredOutlets = useMemo(() => {
    if (!searchQuery.trim()) return outlets;
    const q = searchQuery.toLowerCase();
    return outlets.filter(
      (o) =>
        o.name?.toLowerCase().includes(q) ||
        o.city?.toLowerCase().includes(q) ||
        o.outlet_code?.toLowerCase().includes(q)
    );
  }, [outlets, searchQuery]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header Banner */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs font-bold">
            <Sparkles className="w-3.5 h-3.5 text-rose-500" />
            <span>4-Tier Partner Ecosystem</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
            Franchise & Channel Partner Network
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-2xl">
            Manage Broker CPs, Active CPs (L1–L3 Ladder & owner privacy), Referral Partners (capped registry rewards), and Creator Partners (code attribution & retainers).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setModalType('partner')}
            className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add CP</span>
          </button>
          <button
            type="button"
            onClick={() => setModalType('outlet')}
            className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 text-white font-bold text-xs rounded-xl flex items-center gap-1.5 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Outlet</span>
          </button>
          <button
            type="button"
            onClick={fetchAll}
            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold text-xs rounded-xl flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold text-xs rounded-xl transition-all cursor-pointer"
          >
            Dashboard
          </button>
        </div>
      </div>

      {banner && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center justify-between gap-3 ${
            banner.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
              : 'bg-rose-50 dark:bg-rose-950/60 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {banner.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            <span className="font-medium">{banner.text}</span>
          </div>
          <button onClick={() => setBanner(null)}>
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 4 Live Dynamic Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <button
          type="button"
          onClick={() => setActiveTab('partners')}
          className="text-left bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-400 rounded-2xl p-5 shadow-xs transition-all cursor-pointer"
        >
          <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            CHANNEL PARTNERS
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 dark:text-white">
            {overview.channel_partners.active}
          </div>
          <div className="mt-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>Active across 4 tiers ({overview.channel_partners.total} total)</span>
          </div>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('outlets')}
          className="text-left bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-400 rounded-2xl p-5 shadow-xs transition-all cursor-pointer"
        >
          <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            FRANCHISE OUTLETS
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 dark:text-white">
            {overview.franchise_outlets.active}
          </div>
          <div className="mt-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>
              {overview.franchise_outlets.cities.length > 0
                ? `${overview.franchise_outlets.cities.join(', ')} locations`
                : 'No outlets added yet'}
            </span>
          </div>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('leads')}
          className="text-left bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-400 rounded-2xl p-5 shadow-xs transition-all cursor-pointer"
        >
          <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            PARTNER SOURCED LEADS
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 dark:text-white">
            {overview.partner_sourced_leads.total}
          </div>
          <div className="mt-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>{overview.partner_sourced_leads.converted} converted / registered</span>
          </div>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('payouts')}
          className="text-left bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-emerald-400 rounded-2xl p-5 shadow-xs transition-all cursor-pointer"
        >
          <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            SETTLED PAYOUTS
          </div>
          <div className="mt-2 text-2xl font-black text-slate-900 dark:text-white">
            {overview.settled_payouts.count}
          </div>
          <div className="mt-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>
              {formatINR(overview.settled_payouts.total_amount)} cleared ({overview.settled_payouts.pending_count} pending)
            </span>
          </div>
        </button>
      </div>

      {/* Main Workspace */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div className="flex flex-wrap gap-2">
            {[
              { id: 'partners', label: `Channel Partners (${partners.length})`, icon: Handshake },
              { id: 'outlets', label: `Outlets (${outlets.length})`, icon: Building2 },
              { id: 'meetings', label: `L3 Mediated Meetings (${meetings.length})`, icon: Calendar },
              { id: 'leads', label: `Partner Leads (${leads.length})`, icon: Users },
              { id: 'payouts', label: `Payouts & Retainers (${payouts.length})`, icon: Wallet },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-3.5 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer ${
                    activeTab === tab.id
                      ? 'bg-slate-900 dark:bg-emerald-600 text-white'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {activeTab === 'payouts' && (
              <>
                <button
                  type="button"
                  onClick={handleGenerateRetainers}
                  className="px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold cursor-pointer"
                >
                  Generate Monthly Retainers
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (partners.length > 0 && !payPartnerId) setPayPartnerId(String(partners[0].id));
                    setModalType('payout');
                  }}
                  className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Log Payout</span>
                </button>
              </>
            )}
            {activeTab === 'meetings' && (
              <button
                type="button"
                onClick={() => {
                  const l3s = partners.filter((p) => p.cp_type === 'ACTIVE_CP' && p.active_level === 'L3' && p.is_active);
                  if (l3s.length > 0) setMPartnerId(String(l3s[0].id));
                  setModalType('meeting');
                }}
                className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Request L3 Meeting</span>
              </button>
            )}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
                className="pl-8 pr-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs text-slate-900 dark:text-white"
              />
            </div>
          </div>
        </div>

        {/* TAB 1: 4-Tier Channel Partners */}
        {activeTab === 'partners' && (
          <div className="space-y-4">
            {/* 4-Tier Filter Pills */}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setCpTierFilter('ALL')}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold cursor-pointer ${
                  cpTierFilter === 'ALL'
                    ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                }`}
              >
                All CPs ({partners.length})
              </button>
              {(['BROKER_CP', 'ACTIVE_CP', 'REFERRAL_PARTNER', 'CREATOR_PARTNER'] as CPType[]).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setCpTierFilter(t)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold cursor-pointer border ${
                    cpTierFilter === t
                      ? 'bg-emerald-600 text-white border-emerald-600'
                      : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300'
                  }`}
                >
                  {CP_TYPE_META[t].short} ({partners.filter((p) => p.cp_type === t).length})
                </button>
              ))}
            </div>

            {filteredPartners.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                No partners in this category yet. Click <strong>Add CP</strong> to onboard one.
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {filteredPartners.map((p) => {
                  const meta = CP_TYPE_META[(p.cp_type || 'BROKER_CP') as CPType] || CP_TYPE_META.BROKER_CP;
                  return (
                    <div
                      key={p.id}
                      className={`p-5 rounded-2xl border space-y-3 transition-all ${
                        p.is_active
                          ? 'bg-slate-50/70 dark:bg-slate-950/50 border-slate-200 dark:border-slate-800'
                          : 'bg-rose-50/40 dark:bg-rose-950/20 border-rose-300 dark:border-rose-900/60'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${meta.color}`}>
                              {meta.short}
                            </span>
                            {p.cp_type === 'ACTIVE_CP' && (
                              <span className="px-2 py-0.5 rounded-md text-[10px] font-black bg-slate-900 dark:bg-white text-white dark:text-slate-900">
                                {p.active_level} • {p.tenure_days}d
                              </span>
                            )}
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                p.is_active
                                  ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                                  : 'bg-rose-500/15 text-rose-700 dark:text-rose-300'
                              }`}
                            >
                              {p.is_active ? 'ACTIVE' : 'SUSPENDED'}
                            </span>
                          </div>
                          <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                            {p.full_name} <span className="text-xs font-mono text-slate-400">({p.partner_code})</span>
                          </h4>
                          <div className="text-[11px] text-slate-500">
                            {p.mobile} • {p.city} {p.company_name ? `• ${p.company_name}` : ''}
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => handlePreviewInventory(p)}
                          className="px-2.5 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-[11px] font-bold flex items-center gap-1 hover:border-emerald-500 cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5 text-emerald-500" />
                          <span>Access View</span>
                        </button>
                      </div>

                      {/* Tier-Specific Details */}
                      {p.cp_type === 'BROKER_CP' && (
                        <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 text-xs flex flex-wrap items-center justify-between gap-2">
                          <span>Office: {p.has_office_setup ? `Verified (${p.office_address || p.city})` : 'Not set'}</span>
                          <span className="font-bold text-blue-600 dark:text-blue-400">
                            Co-Broking Split: {p.co_broking_split_pct}%
                          </span>
                        </div>
                      )}

                      {p.cp_type === 'ACTIVE_CP' && (
                        <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 text-xs space-y-2">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span>
                              Certified: <strong>{p.is_certified ? 'Yes ✓' : 'No'}</strong> • Clean Record:{' '}
                              <strong>{p.clean_record ? 'Clean ✓' : 'Flagged ⚠'}</strong>
                            </span>
                            <span className="text-[11px] text-slate-500">
                              {p.active_level === 'L1'
                                ? 'L1: No inventory, accompanied visits only'
                                : p.active_level === 'L2'
                                ? 'L2: Address only (Owner masked)'
                                : 'L3: Direct meeting via Omshiv enabled'}
                            </span>
                          </div>
                          {p.is_active && (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {!p.is_certified && (
                                <button
                                  type="button"
                                  onClick={() => handleCertify(p)}
                                  className="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-[11px] font-bold flex items-center gap-1 cursor-pointer"
                                >
                                  <Award className="w-3 h-3" />
                                  <span>Mark Certified</span>
                                </button>
                              )}
                              {p.active_level === 'L1' && (
                                <button
                                  type="button"
                                  onClick={() => handlePromote(p, 'L2')}
                                  className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold flex items-center gap-1 cursor-pointer"
                                >
                                  <ArrowUpRight className="w-3 h-3" />
                                  <span>Promote → L2</span>
                                </button>
                              )}
                              {p.active_level === 'L2' && (
                                <button
                                  type="button"
                                  onClick={() => handlePromote(p, 'L3')}
                                  className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold flex items-center gap-1 cursor-pointer"
                                >
                                  <ArrowUpRight className="w-3 h-3" />
                                  <span>Promote → L3</span>
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {p.cp_type === 'REFERRAL_PARTNER' && (
                        <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 text-xs flex flex-wrap items-center justify-between gap-2">
                          <span>
                            Registry Fixed Reward: <strong className="text-amber-600">{formatINR(p.fixed_reward_amount)}</strong>
                          </span>
                          <span className="font-bold">
                            FY {p.current_fy} Cap: {p.fy_rewards_used} / {p.annual_reward_limit} used
                          </span>
                        </div>
                      )}

                      {p.cp_type === 'CREATOR_PARTNER' && (
                        <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 text-xs flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <Link2 className="w-3.5 h-3.5 text-purple-500" />
                            <code className="font-mono font-bold text-purple-600 dark:text-purple-300">
                              ?ref={p.tracking_code}
                            </code>
                            <button
                              type="button"
                              onClick={() => {
                                navigator.clipboard.writeText(`${window.location.origin}/?ref=${p.tracking_code}`);
                                setBanner({ type: 'success', text: `Copied creator link for ${p.tracking_code}` });
                              }}
                              className="text-slate-400 hover:text-slate-700"
                              title="Copy tracking link"
                            >
                              <Copy className="w-3 h-3" />
                            </button>
                          </div>
                          <span>
                            Deals/Leads: <strong>{p.tracked_leads_count}</strong> •{' '}
                            {p.is_top_creator ? `Retainer ${formatINR(p.monthly_retainer_amount)}/mo` : `${p.commission_pct}% comm`}
                          </span>
                        </div>
                      )}

                      {/* Bottom Governance Row: Instant Kill Switch */}
                      <div className="flex items-center justify-between pt-2 border-t border-slate-200/70 dark:border-slate-800 text-[11px]">
                        <span className="text-slate-500">
                          {p.suspension_reason ? `Suspended: ${p.suspension_reason}` : `Outlet: ${p.outlet_name || 'Central Desk'}`}
                        </span>
                        {p.is_active ? (
                          <button
                            type="button"
                            onClick={() => {
                              setSuspendTarget(p);
                              setSuspendReason('');
                              setModalType('suspend');
                            }}
                            className="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-bold flex items-center gap-1 cursor-pointer"
                          >
                            <ShieldAlert className="w-3 h-3" />
                            <span>Instant Suspend</span>
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleReinstate(p)}
                            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-900 text-white font-bold flex items-center gap-1 cursor-pointer"
                          >
                            <Power className="w-3 h-3" />
                            <span>Reinstate</span>
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: Franchise Outlets */}
        {activeTab === 'outlets' && (
          filteredOutlets.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              No franchise outlets found. Click <strong>Add Outlet</strong> to add a branch office.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredOutlets.map((o) => (
                <div
                  key={o.id}
                  className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-950/50 space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-[10px] font-mono text-slate-400">{o.outlet_code}</span>
                      <h4 className="text-sm font-bold text-slate-900 dark:text-white">{o.name}</h4>
                      <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                        <MapPin className="w-3 h-3 text-rose-500" />
                        <span>{o.locality ? `${o.locality}, ${o.city}` : o.city}</span>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleOutletActive(o)}
                      className={`px-2.5 py-1 rounded-lg text-[10px] font-bold cursor-pointer ${
                        o.is_active
                          ? 'bg-emerald-600 text-white'
                          : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                      }`}
                    >
                      {o.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </div>
                  <div className="text-xs text-slate-600 dark:text-slate-400 flex items-center justify-between pt-2 border-t border-slate-200/70 dark:border-slate-800">
                    <span className="flex items-center gap-1">
                      <Phone className="w-3 h-3" />
                      {o.manager_name || 'No manager'} {o.manager_mobile ? `(${o.manager_mobile})` : ''}
                    </span>
                    <span className="font-bold">{o.active_partner_count} partners</span>
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {/* TAB 3: L3 Mediated Meetings */}
        {activeTab === 'meetings' && (
          meetings.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              No L3 Omshiv-mediated direct meetings requested yet.
            </div>
          ) : (
            <div className="space-y-3">
              {meetings.map((m) => (
                <div key={m.id} className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
                  <div>
                    <div className="font-bold text-slate-900 dark:text-white">
                      {m.meeting_code} • {m.partner_name} ({m.partner_code})
                    </div>
                    <div className="text-slate-500 mt-0.5">
                      Property: <span className="font-mono">{m.property_id}</span>
                      {m.lead_id ? ` • Lead: ${m.lead_id}` : ''} • Slot: {new Date(m.requested_slot).toLocaleString('en-IN')}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 font-bold">{m.status}</span>
                    {m.status === 'REQUESTED' && (
                      <>
                        <button
                          type="button"
                          onClick={() => updateMeetingStatus(m.id, 'APPROVED')}
                          className="px-3 py-1 rounded-lg bg-emerald-600 text-white font-bold cursor-pointer"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          onClick={() => updateMeetingStatus(m.id, 'REJECTED')}
                          className="px-3 py-1 rounded-lg bg-rose-600 text-white font-bold cursor-pointer"
                        >
                          Reject
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {/* TAB 4: Partner Sourced Leads */}
        {activeTab === 'leads' && (
          leads.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              No CRM leads with partner/referral attribution found yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="p-3">Lead ID</th>
                    <th className="p-3">Customer</th>
                    <th className="p-3">Attribution / Ref Code</th>
                    <th className="p-3">City & Budget</th>
                    <th className="p-3">Stage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {leads.map((l) => (
                    <tr
                      key={l.lead_id}
                      onClick={() => navigate(`/leads/${l.lead_id}`)}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer"
                    >
                      <td className="p-3 font-mono font-bold text-emerald-600 dark:text-emerald-400">{l.lead_id}</td>
                      <td className="p-3">
                        <div className="font-bold">{l.full_name}</div>
                        <div className="text-[11px] font-mono text-slate-500">{l.mobile}</div>
                      </td>
                      <td className="p-3">
                        <div>{l.source}</div>
                        {l.referral_code && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-600">
                            ref: {l.referral_code}
                          </span>
                        )}
                      </td>
                      <td className="p-3">
                        {l.preferred_city || '—'} {l.budget_max ? `• ${formatINR(l.budget_max)}` : ''}
                      </td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-bold text-[10px]">
                          {l.stage}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {/* TAB 5: Payouts & Retainers */}
        {activeTab === 'payouts' && (
          payouts.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              No payouts logged yet. Click <strong>Log Payout</strong> or <strong>Generate Monthly Retainers</strong>.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="p-3">Payout</th>
                    <th className="p-3">Partner</th>
                    <th className="p-3">Type / FY</th>
                    <th className="p-3">Deal / Property</th>
                    <th className="p-3">Amount</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {payouts.map((pay) => (
                    <tr key={pay.id}>
                      <td className="p-3 font-mono font-bold">{pay.payout_code}</td>
                      <td className="p-3">
                        <div className="font-bold">{pay.partner_name}</div>
                        <div className="text-[11px] text-slate-500">{pay.partner_code}</div>
                      </td>
                      <td className="p-3">
                        <div className="font-bold">{pay.payout_type}</div>
                        <div className="text-[11px] text-slate-400">FY {pay.fiscal_year}</div>
                      </td>
                      <td className="p-3">
                        <div>{pay.property_title || pay.lead_id || 'Commission'}</div>
                        {pay.deal_amount > 0 && (
                          <div className="text-[11px] text-slate-500">Deal: {formatINR(pay.deal_amount)}</div>
                        )}
                      </td>
                      <td className="p-3 font-bold text-emerald-600 dark:text-emerald-400">
                        {formatINR(pay.commission_amount)}
                      </td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            pay.status === 'SETTLED'
                              ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                              : 'bg-amber-500/15 text-amber-700 dark:text-amber-300'
                          }`}
                        >
                          {pay.status}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        {pay.status !== 'SETTLED' && (
                          <button
                            type="button"
                            onClick={() => markPayoutSettled(pay.id)}
                            className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold cursor-pointer"
                          >
                            Mark Settled
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>

      {/* Bottom Operations Shortcuts */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Layers className="w-4 h-4 text-rose-500" />
          <span>Available Sub-Sections & Operations</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div
            onClick={() => navigate('/staff?tab=roles')}
            className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 hover:border-rose-400 flex items-center justify-between cursor-pointer transition-all group"
          >
            <div>
              <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-rose-600">
                Assign Franchise Dynamic Roles
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400">
                Configure permissions for franchisee staff members
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-rose-500" />
          </div>
          <div
            onClick={() => navigate('/leads')}
            className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 hover:border-rose-400 flex items-center justify-between cursor-pointer transition-all group"
          >
            <div>
              <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-rose-600">
                Prioritized Sales Lead Queue
              </div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400">
                Review partner submitted customer inquiries
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-rose-500" />
          </div>
        </div>
      </div>

      {/* Inventory Access Preview Modal */}
      {(previewData || previewError) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs">
          <div className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Lock className="w-4 h-4 text-emerald-500" />
                  <span>Server-Scoped Inventory Access — {previewPartnerName}</span>
                </h3>
              </div>
              <button
                onClick={() => {
                  setPreviewData(null);
                  setPreviewError(null);
                }}
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            {previewError ? (
              <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300 font-semibold">
                BLOCKED (403): {previewError}
              </div>
            ) : (
              <div className="space-y-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-medium">
                  {previewData.message}
                </div>
                <div className="flex flex-wrap gap-2 text-[11px]">
                  <span className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-800">
                    Browse Inventory: <strong>{previewData.can_browse_inventory ? 'Allowed' : 'Locked'}</strong>
                  </span>
                  <span className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-800">
                    Owner Phone/Name: <strong>{previewData.can_view_owner_contact ? 'Visible' : 'Masked ✓'}</strong>
                  </span>
                  <span className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-800">
                    L3 Mediated Meeting: <strong>{previewData.can_request_mediated_meeting ? 'Unlocked' : 'Locked'}</strong>
                  </span>
                </div>
                {previewData.items?.length > 0 && (
                  <div className="space-y-2">
                    {previewData.items.slice(0, 6).map((item: any) => (
                      <div key={item.property_id} className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                        <div>
                          <div className="font-bold">{item.title} ({item.property_id})</div>
                          <div className="text-[11px] text-slate-500">
                            {item.locality ? `${item.locality}, ${item.city}` : item.city} • Owner: {item.owner_name} (Phone: Masked)
                          </div>
                        </div>
                        <div className="font-bold text-emerald-600">{formatINR(item.expected_price)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Modals */}
      {modalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs">
          <div className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                {modalType === 'partner'
                  ? 'Register Channel Partner (4 Tiers)'
                  : modalType === 'outlet'
                  ? 'Add Franchise Outlet'
                  : modalType === 'payout'
                  ? 'Log Commission / Referral Payout'
                  : modalType === 'meeting'
                  ? 'Request L3 Mediated Meeting'
                  : `Instant Suspend — ${suspendTarget?.full_name}`}
              </h3>
              <button onClick={() => setModalType(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            {modalType === 'partner' && (
              <form onSubmit={handleCreatePartner} className="space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-1.5">
                  {(['BROKER_CP', 'ACTIVE_CP', 'REFERRAL_PARTNER', 'CREATOR_PARTNER'] as CPType[]).map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setPType(t)}
                      className={`p-2 rounded-xl border text-left font-bold cursor-pointer ${
                        pType === t
                          ? 'bg-emerald-600 text-white border-emerald-600'
                          : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700'
                      }`}
                    >
                      {CP_TYPE_META[t].short}
                    </button>
                  ))}
                </div>

                <input required placeholder="Full Name *" value={pName} onChange={(e) => setPName(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                <div className="grid grid-cols-2 gap-2">
                  <input required placeholder="Mobile *" value={pMobile} onChange={(e) => setPMobile(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                  <input required placeholder="City *" value={pCity} onChange={(e) => setPCity(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                </div>

                {pType === 'BROKER_CP' && (
                  <div className="p-3 rounded-xl bg-blue-500/5 border border-blue-500/20 space-y-2">
                    <div className="font-bold text-blue-600 dark:text-blue-300">Broker CP (Office Setup & Co-Broking)</div>
                    <input placeholder="Agency / Firm Name" value={pCompany} onChange={(e) => setPCompany(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900" />
                    <input placeholder="Office Address" value={pOfficeAddress} onChange={(e) => setPOfficeAddress(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900" />
                    <div className="grid grid-cols-2 gap-2 items-center">
                      <label className="flex items-center gap-2 font-semibold">
                        <input type="checkbox" checked={pHasOffice} onChange={(e) => setPHasOffice(e.target.checked)} />
                        <span>Own Office Verified</span>
                      </label>
                      <input type="number" step="1" placeholder="Co-Broking Split %" value={pCoSplit} onChange={(e) => setPCoSplit(e.target.value)} className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900" />
                    </div>
                  </div>
                )}

                {pType === 'ACTIVE_CP' && (
                  <div className="p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/20 space-y-2">
                    <div className="font-bold text-emerald-600 dark:text-emerald-300">Active CP starts at L1 (0–30 days)</div>
                    <p className="text-[11px] text-slate-500">No inventory for first 30 days; site visits accompanied by Omshiv staff. Upgrade to L2/L3 after certification & manager review.</p>
                    <input type="number" step="0.1" placeholder="Commission %" value={pComm} onChange={(e) => setPComm(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900" />
                  </div>
                )}

                {pType === 'REFERRAL_PARTNER' && (
                  <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 space-y-2">
                    <div className="font-bold text-amber-600 dark:text-amber-300">Referral Partner (Fixed Reward on Registry)</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[10px] text-slate-500">Fixed Reward (₹ / Registry)</label>
                        <input type="number" required value={pFixedReward} onChange={(e) => setPFixedReward(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900" />
                      </div>
                      <div>
                        <label className="text-[10px] text-slate-500">Annual Limit (Rewards / FY)</label>
                        <input type="number" required min="1" value={pAnnualLimit} onChange={(e) => setPAnnualLimit(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900" />
                      </div>
                    </div>
                  </div>
                )}

                {pType === 'CREATOR_PARTNER' && (
                  <div className="p-3 rounded-xl bg-purple-500/5 border border-purple-500/20 space-y-2">
                    <div className="font-bold text-purple-600 dark:text-purple-300">Creator Partner (Tracking Link & Retainer)</div>
                    <div className="grid grid-cols-2 gap-2">
                      <input placeholder="Custom Code (e.g. ROHIT26)" value={pTrackingCode} onChange={(e) => setPTrackingCode(e.target.value)} className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900" />
                      <input placeholder="Instagram / YouTube Handle" value={pSocialHandle} onChange={(e) => setPSocialHandle(e.target.value)} className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900" />
                    </div>
                    <div className="grid grid-cols-2 gap-2 items-center">
                      <label className="flex items-center gap-2 font-semibold">
                        <input type="checkbox" checked={pTopCreator} onChange={(e) => setPTopCreator(e.target.checked)} />
                        <span>Top Creator (Retainer)</span>
                      </label>
                      <input type="number" placeholder="Monthly Retainer ₹" value={pRetainer} onChange={(e) => setPRetainer(e.target.value)} className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900" />
                    </div>
                  </div>
                )}

                <select value={pOutletId} onChange={(e) => setPOutletId(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                  <option value="">Assign Franchise Outlet (Optional)</option>
                  {outlets.map((o) => (
                    <option key={o.id} value={o.id}>{o.name} ({o.city})</option>
                  ))}
                </select>

                <button disabled={submitting} type="submit" className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold cursor-pointer">
                  {submitting ? 'Saving...' : 'Save Partner'}
                </button>
              </form>
            )}

            {modalType === 'outlet' && (
              <form onSubmit={handleCreateOutlet} className="space-y-3 text-xs">
                <input required placeholder="Outlet / Branch Name *" value={oName} onChange={(e) => setOName(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                <div className="grid grid-cols-2 gap-2">
                  <input required placeholder="City *" value={oCity} onChange={(e) => setOCity(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                  <input placeholder="Locality" value={oLocality} onChange={(e) => setOLocality(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input placeholder="Branch Manager Name" value={oManager} onChange={(e) => setOManager(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                  <input placeholder="Manager Mobile" value={oMobile} onChange={(e) => setOMobile(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                </div>
                <button disabled={submitting} type="submit" className="w-full py-2.5 rounded-xl bg-slate-900 dark:bg-emerald-600 text-white font-bold cursor-pointer">
                  {submitting ? 'Saving...' : 'Create Outlet'}
                </button>
              </form>
            )}

            {modalType === 'payout' && (
              <form onSubmit={handleCreatePayout} className="space-y-3 text-xs">
                <select required value={payPartnerId} onChange={(e) => setPayPartnerId(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                  <option value="">Select Channel Partner *</option>
                  {partners.map((p) => (
                    <option key={p.id} value={p.id}>{p.full_name} ({CP_TYPE_META[p.cp_type as CPType]?.short || p.cp_type})</option>
                  ))}
                </select>
                <div className="grid grid-cols-2 gap-2">
                  <input placeholder="Lead ID (Required for Referral)" value={payLeadId} onChange={(e) => setPayLeadId(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                  <input placeholder="Property Title" value={payProp} onChange={(e) => setPayProp(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input type="number" placeholder="Deal Amount (₹)" value={payDeal} onChange={(e) => setPayDeal(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                  <input type="number" placeholder="Reward / Commission (₹)" value={payComm} onChange={(e) => setPayComm(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                </div>
                <input placeholder="Note / Reference" value={payNote} onChange={(e) => setPayNote(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                <button disabled={submitting} type="submit" className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold cursor-pointer">
                  {submitting ? 'Saving...' : 'Save Payout'}
                </button>
              </form>
            )}

            {modalType === 'meeting' && (
              <form onSubmit={handleCreateMeeting} className="space-y-3 text-xs">
                <select required value={mPartnerId} onChange={(e) => setMPartnerId(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                  <option value="">Select L3 Active CP *</option>
                  {partners.filter((p) => p.cp_type === 'ACTIVE_CP' && p.active_level === 'L3').map((p) => (
                    <option key={p.id} value={p.id}>{p.full_name} ({p.partner_code})</option>
                  ))}
                </select>
                <div className="grid grid-cols-2 gap-2">
                  <input required placeholder="Property ID (e.g. OP-2026-00001) *" value={mPropertyId} onChange={(e) => setMPropertyId(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                  <input placeholder="Lead ID" value={mLeadId} onChange={(e) => setMLeadId(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                </div>
                <input required type="datetime-local" value={mSlot} onChange={(e) => setMSlot(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                <input placeholder="Notes for Omshiv Supervisor" value={mNotes} onChange={(e) => setMNotes(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                <button disabled={submitting} type="submit" className="w-full py-2.5 rounded-xl bg-emerald-600 text-white font-bold cursor-pointer">
                  {submitting ? 'Submitting...' : 'Request Omshiv-Mediated Meeting'}
                </button>
              </form>
            )}

            {modalType === 'suspend' && (
              <form onSubmit={handleConfirmSuspend} className="space-y-3 text-xs">
                <p className="text-rose-600 dark:text-rose-400 font-semibold">
                  Warning: Instant Suspend immediately revokes all inventory, meeting, and payout access for {suspendTarget?.full_name}.
                </p>
                <textarea required rows={3} placeholder="Reason for suspension / violation details *" value={suspendReason} onChange={(e) => setSuspendReason(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-rose-300 dark:border-rose-800 bg-slate-50 dark:bg-slate-800" />
                <button disabled={submitting} type="submit" className="w-full py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold cursor-pointer">
                  {submitting ? 'Suspending...' : 'Confirm Instant Suspend'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default FranchiseHub;

