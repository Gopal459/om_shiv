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
} from 'lucide-react';

interface FranchiseOverview {
  channel_partners: { total: number; active: number };
  franchise_outlets: { total: number; active: number; cities: string[] };
  partner_sourced_leads: { total: number; converted: number };
  settled_payouts: { count: number; pending_count: number; total_amount: number };
}

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

  const activeTab = useMemo<'partners' | 'outlets' | 'leads' | 'payouts'>(() => {
    if (typeParam === 'outlets' || typeParam === 'leads' || typeParam === 'payouts') {
      return typeParam;
    }
    return 'partners';
  }, [typeParam]);

  const setActiveTab = (tab: 'partners' | 'outlets' | 'leads' | 'payouts') => {
    setSearchParams({ type: tab }, { replace: true });
  };

  const [overview, setOverview] = useState<FranchiseOverview>({
    channel_partners: { total: 0, active: 0 },
    franchise_outlets: { total: 0, active: 0, cities: [] },
    partner_sourced_leads: { total: 0, converted: 0 },
    settled_payouts: { count: 0, pending_count: 0, total_amount: 0 },
  });
  const [partners, setPartners] = useState<any[]>([]);
  const [outlets, setOutlets] = useState<any[]>([]);
  const [leads, setLeads] = useState<any[]>([]);
  const [payouts, setPayouts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [banner, setBanner] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modals
  const [modalType, setModalType] = useState<'partner' | 'outlet' | 'payout' | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Partner form
  const [pName, setPName] = useState('');
  const [pCompany, setPCompany] = useState('');
  const [pMobile, setPMobile] = useState('');
  const [pCity, setPCity] = useState('Jaipur');
  const [pRera, setPRera] = useState('');
  const [pOutletId, setPOutletId] = useState<string>('');
  const [pComm, setPComm] = useState('2.0');

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

  const fetchAll = async () => {
    setLoading(true);
    try {
      const headers = getAuthHeaders();
      const [ovRes, pRes, oRes, lRes, payRes] = await Promise.all([
        fetch('/v1/franchise/overview', { headers }),
        fetch('/v1/franchise/partners', { headers }),
        fetch('/v1/franchise/outlets', { headers }),
        fetch('/v1/franchise/leads', { headers }),
        fetch('/v1/franchise/payouts', { headers }),
      ]);
      if (ovRes.ok) setOverview(await ovRes.json());
      if (pRes.ok) {
        const d = await pRes.json();
        setPartners(d.partners || []);
      }
      if (oRes.ok) {
        const d = await oRes.json();
        setOutlets(d.outlets || []);
      }
      if (lRes.ok) {
        const d = await lRes.json();
        setLeads(d.leads || []);
      }
      if (payRes.ok) {
        const d = await payRes.json();
        setPayouts(d.payouts || []);
      }
    } catch {
      setBanner({ type: 'error', text: 'Failed to load Franchise & Partner data.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleCreatePartner = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setBanner(null);
    try {
      const res = await fetch('/v1/franchise/partners', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          full_name: pName,
          company_name: pCompany || undefined,
          mobile: pMobile,
          city: pCity,
          rera_number: pRera || undefined,
          outlet_id: pOutletId ? Number(pOutletId) : undefined,
          commission_pct: Number(pComm) || 2.0,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Could not add channel partner');
      }
      setModalType(null);
      setPName('');
      setPCompany('');
      setPMobile('');
      setPRera('');
      setBanner({ type: 'success', text: 'Channel Partner registered successfully.' });
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
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Could not add franchise outlet');
      }
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
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Could not create payout');
      }
      setModalType(null);
      setPayLeadId('');
      setPayProp('');
      setPayDeal('');
      setPayComm('');
      setPayNote('');
      setBanner({ type: 'success', text: 'Commission payout recorded.' });
      await fetchAll();
    } catch (err: any) {
      setBanner({ type: 'error', text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const togglePartnerActive = async (partner: any) => {
    const res = await fetch(`/v1/franchise/partners/${partner.id}`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify({ is_active: !partner.is_active }),
    });
    if (res.ok) await fetchAll();
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

  const filteredPartners = useMemo(() => {
    if (!searchQuery.trim()) return partners;
    const q = searchQuery.toLowerCase();
    return partners.filter(
      (p) =>
        p.full_name?.toLowerCase().includes(q) ||
        p.company_name?.toLowerCase().includes(q) ||
        p.partner_code?.toLowerCase().includes(q) ||
        p.mobile?.includes(q) ||
        p.city?.toLowerCase().includes(q)
    );
  }, [partners, searchQuery]);

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
            <span>Partner Ecosystem</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
            Franchise & Channel Partner Network
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-xl">
            Manage authorized real estate channel partners, franchise branch outlets, partner-sourced leads, and commission payouts live.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setModalType('partner')}
            className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Partner</span>
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
            <span>Active brokers ({overview.channel_partners.total} total)</span>
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
            <span>{overview.partner_sourced_leads.converted} converted deals</span>
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

      {/* Main Dynamic Workspace */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div className="flex flex-wrap gap-2">
            {[
              { id: 'partners', label: `Channel Partners (${partners.length})`, icon: Handshake },
              { id: 'outlets', label: `Franchise Outlets (${outlets.length})`, icon: Building2 },
              { id: 'leads', label: `Partner Sourced Leads (${leads.length})`, icon: Users },
              { id: 'payouts', label: `Payouts & Commissions (${payouts.length})`, icon: Wallet },
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

          <div className="flex items-center gap-2">
            {activeTab === 'payouts' && (
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

        {/* TAB 1: Channel Partners */}
        {activeTab === 'partners' && (
          filteredPartners.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              No channel partners found. Click <strong>Add Partner</strong> to register your first broker.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="p-3">Partner</th>
                    <th className="p-3">Contact & City</th>
                    <th className="p-3">Outlet / RERA</th>
                    <th className="p-3">Commission %</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {filteredPartners.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40">
                      <td className="p-3">
                        <div className="font-bold text-slate-900 dark:text-white">{p.full_name}</div>
                        <div className="text-[11px] text-slate-500">
                          {p.partner_code} {p.company_name ? `• ${p.company_name}` : ''}
                        </div>
                      </td>
                      <td className="p-3">
                        <div className="font-mono">{p.mobile}</div>
                        <div className="text-[11px] text-slate-500">{p.city}</div>
                      </td>
                      <td className="p-3">
                        <div>{p.outlet_name || 'Direct / Unassigned'}</div>
                        {p.rera_number && <div className="text-[11px] font-mono text-slate-400">{p.rera_number}</div>}
                      </td>
                      <td className="p-3 font-bold text-emerald-600 dark:text-emerald-400">
                        {p.commission_pct}%
                      </td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            p.is_active
                              ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                              : 'bg-rose-500/15 text-rose-700 dark:text-rose-300'
                          }`}
                        >
                          {p.is_active ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <button
                          type="button"
                          onClick={() => togglePartnerActive(p)}
                          className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-[11px] font-bold inline-flex items-center gap-1 cursor-pointer"
                        >
                          <Power className="w-3 h-3" />
                          <span>{p.is_active ? 'Deactivate' : 'Activate'}</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
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

        {/* TAB 3: Partner Sourced Leads */}
        {activeTab === 'leads' && (
          leads.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              No CRM leads with partner/franchise source found yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="p-3">Lead ID</th>
                    <th className="p-3">Customer</th>
                    <th className="p-3">Source</th>
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
                      <td className="p-3">{l.source}</td>
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

        {/* TAB 4: Payouts & Commissions */}
        {activeTab === 'payouts' && (
          payouts.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              No partner commission payouts logged yet. Click <strong>Log Payout</strong> to record one.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="p-3">Payout Code</th>
                    <th className="p-3">Partner</th>
                    <th className="p-3">Deal / Property</th>
                    <th className="p-3">Commission</th>
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
                        <div>{pay.property_title || pay.lead_id || 'Deal Commission'}</div>
                        <div className="text-[11px] text-slate-500">Deal: {formatINR(pay.deal_amount)}</div>
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

      {/* Bottom Shortcuts Preserved */}
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

      {/* Modals */}
      {modalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                {modalType === 'partner'
                  ? 'Register Channel Partner'
                  : modalType === 'outlet'
                  ? 'Add Franchise Outlet'
                  : 'Log Commission Payout'}
              </h3>
              <button onClick={() => setModalType(null)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            {modalType === 'partner' && (
              <form onSubmit={handleCreatePartner} className="space-y-3 text-xs">
                <input required placeholder="Full Name *" value={pName} onChange={(e) => setPName(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                <input placeholder="Agency / Company Name" value={pCompany} onChange={(e) => setPCompany(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                <div className="grid grid-cols-2 gap-2">
                  <input required placeholder="Mobile *" value={pMobile} onChange={(e) => setPMobile(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                  <input required placeholder="City *" value={pCity} onChange={(e) => setPCity(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input placeholder="RERA Number" value={pRera} onChange={(e) => setPRera(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                  <input type="number" step="0.1" placeholder="Commission %" value={pComm} onChange={(e) => setPComm(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                </div>
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
                    <option key={p.id} value={p.id}>{p.full_name} ({p.partner_code})</option>
                  ))}
                </select>
                <div className="grid grid-cols-2 gap-2">
                  <input placeholder="Lead ID (e.g. OB-2026-...)" value={payLeadId} onChange={(e) => setPayLeadId(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                  <input placeholder="Property Title" value={payProp} onChange={(e) => setPayProp(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input required type="number" placeholder="Deal Amount (₹) *" value={payDeal} onChange={(e) => setPayDeal(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                  <input required type="number" placeholder="Commission Amount (₹) *" value={payComm} onChange={(e) => setPayComm(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                </div>
                <input placeholder="Note / Reference" value={payNote} onChange={(e) => setPayNote(e.target.value)} className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800" />
                <button disabled={submitting} type="submit" className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold cursor-pointer">
                  {submitting ? 'Saving...' : 'Save Payout'}
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
