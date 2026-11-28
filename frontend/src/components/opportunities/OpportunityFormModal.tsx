import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  ChevronDown,
  Loader2,
  Save,
  User,
  X,
} from 'lucide-react';
import {
  AREA_UNITS,
  AssigneeOption,
  FURNISHING_OPTIONS,
  FranchiseOutletOption,
  LOANABLE_OPTIONS,
  OpportunityDetail,
  OpportunitySummary,
  PROPERTY_AGE_OPTIONS,
  PROPERTY_CATEGORIES,
  PROPERTY_SUBCATEGORIES_BY_CATEGORY,
  authHeaders,
} from '../../types/opportunities';
import LocalityMultiPicker from './LocalityMultiPicker';
import type { OpportunityLocationInput } from '../../types/opportunities';

const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

// ── Source lead prefill shape ─────────────────────────────
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

// ── Props ─────────────────────────────────────────────────
interface OpportunityFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: (opp: OpportunityDetail | OpportunitySummary) => void;
  editingOpportunity?: OpportunityDetail | null;
  sourceLeadPrefill?: SourceLeadPrefill | null;
}

// ── Default form state ────────────────────────────────────
interface FormState {
  // Client
  contact_name: string;
  mobile: string;
  alternate_mobile: string;
  email: string;
  address: string;
  customer_type: 'END_USER' | 'INVESTOR';
  // Property preference
  property_type: number;
  looking_type: number;
  looking_subcat_type: number;
  // Budget
  budget_from: string;
  budget_to: string;
  // Area
  area_from: string;
  area_to: string;
  area_unit: string;
  // Specs
  bhk: string;
  furnishing: string;
  property_age: string;
  loanable: 'YES' | 'NO' | 'MAYBE';
  // Remark
  remark: string;
  // Assignment
  assign_franch_id: number;
  assigned_to: string;
  // Follow-up
  followup_date: string;
  followup_time: string;
  // Locations
  locations: OpportunityLocationInput[];
}

function defaultForm(
  editing?: OpportunityDetail | null,
  prefill?: SourceLeadPrefill | null
): FormState {
  if (editing) {
    const fdt = editing.followup_datetime ? new Date(editing.followup_datetime) : null;
    const pad = (n: number) => String(n).padStart(2, '0');
    return {
      contact_name: editing.contact_name ?? '',
      mobile: editing.mobile ?? '',
      alternate_mobile: editing.alternate_mobile ?? '',
      email: editing.email ?? '',
      address: editing.address ?? '',
      customer_type: (editing.customer_type as 'END_USER' | 'INVESTOR') ?? 'END_USER',
      property_type: editing.property_type ?? 2,
      looking_type: editing.looking_type ?? 1,
      looking_subcat_type: editing.looking_subcat_type ?? 1,
      budget_from: editing.budget_from ? String(editing.budget_from) : '',
      budget_to: editing.budget_to ? String(editing.budget_to) : '',
      area_from: editing.area_from ? String(editing.area_from) : '',
      area_to: editing.area_to ? String(editing.area_to) : '',
      area_unit: editing.area_unit ?? 'Sq.Ft',
      bhk: editing.bhk ? String(editing.bhk) : '',
      furnishing: editing.furnishing ?? '',
      property_age: editing.property_age ?? '',
      loanable: (editing.loanable as 'YES' | 'NO' | 'MAYBE') ?? 'MAYBE',
      remark: editing.remark ?? '',
      assign_franch_id: editing.assign_franch_id ?? 0,
      assigned_to: editing.assigned_to ?? '',
      followup_date: fdt
        ? `${fdt.getFullYear()}-${pad(fdt.getMonth() + 1)}-${pad(fdt.getDate())}`
        : '',
      followup_time: fdt
        ? `${pad(fdt.getHours())}:${pad(fdt.getMinutes())}`
        : '',
      locations: editing.locations ?? [],
    };
  }

  // Prefill from lead
  const pf = prefill;
  return {
    contact_name: pf?.contact_name ?? '',
    mobile: pf?.mobile ?? '',
    alternate_mobile: pf?.alternate_mobile ?? '',
    email: pf?.email ?? '',
    address: pf?.address ?? '',
    customer_type: 'END_USER',
    property_type: pf?.property_type ?? 2,
    looking_type: 1,
    looking_subcat_type: 1,
    budget_from: '',
    budget_to: pf?.budget_to ? String(pf.budget_to) : '',
    area_from: '',
    area_to: '',
    area_unit: 'Sq.Ft',
    bhk: '',
    furnishing: '',
    property_age: '',
    loanable: 'MAYBE',
    remark: pf?.remark ?? '',
    assign_franch_id: 0,
    assigned_to: pf?.assigned_to ?? '',
    followup_date: '',
    followup_time: '',
    locations:
      pf?.locality
        ? [{ locality_name: pf.locality, latitude: null, longitude: null, radius_km: 10 }]
        : [],
  };
}

// ── Section header helper ────────────────────────────────
const SectionHeader: React.FC<{ label: string }> = ({ label }) => (
  <div className="col-span-2 flex items-center gap-2 mt-2 mb-1">
    <span className="text-xs font-semibold uppercase tracking-widest text-[#291BB0] dark:text-indigo-400">
      {label}
    </span>
    <div className="flex-1 h-px bg-[#291BB0]/15 dark:bg-indigo-500/20" />
  </div>
);

// ── Field wrapper ────────────────────────────────────────
const Field: React.FC<{
  label: string;
  required?: boolean;
  children: React.ReactNode;
  fullWidth?: boolean;
}> = ({ label, required, children, fullWidth }) => (
  <div className={fullWidth ? 'col-span-2' : ''}>
    <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
      {label}
      {required && <span className="text-[#F04B42] ml-0.5">*</span>}
    </label>
    {children}
  </div>
);

const inputCls =
  'w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#291BB0]/40 focus:border-[#291BB0] dark:focus:border-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed';

const selectCls = `${inputCls} appearance-none`;

// ── Main modal component ─────────────────────────────────
const OpportunityFormModal: React.FC<OpportunityFormModalProps> = ({
  isOpen,
  onClose,
  onSaved,
  editingOpportunity,
  sourceLeadPrefill,
}) => {
  const isEdit = !!editingOpportunity;

  // Form data
  const [form, setForm] = useState<FormState>(
    () => defaultForm(editingOpportunity, sourceLeadPrefill)
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dropdown data
  const [assignees, setAssignees] = useState<AssigneeOption[]>([]);
  const [outlets, setOutlets] = useState<FranchiseOutletOption[]>([]);
  const [loadingDropdowns, setLoadingDropdowns] = useState(false);

  const isMounted = useRef(true);
  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  // ── Reset state fully ─────────────────────────────────
  const fullReset = () => {
    setForm(defaultForm(null, null));
    setError(null);
    setSubmitting(false);
  };

  const handleClose = () => {
    fullReset();
    onClose();
  };

  // ── Load dropdowns when opened ─────────────────────────
  useEffect(() => {
    if (!isOpen) return;

    // Re-init form state when modal opens
    setForm(defaultForm(editingOpportunity, sourceLeadPrefill));
    setError(null);

    setLoadingDropdowns(true);
    const headers = authHeaders(false);

    Promise.all([
      fetch(`${API_BASE}/v1/leads/assignees`, { headers }).then((r) => r.json()),
      fetch(`${API_BASE}/v1/franchise/outlets`, { headers }).then((r) => r.json()),
    ])
      .then(([aData, oData]) => {
        if (!isMounted.current) return;
        if (Array.isArray(aData)) setAssignees(aData);
        if (oData?.outlets && Array.isArray(oData.outlets)) setOutlets(oData.outlets);
      })
      .catch(() => {
        // non-critical — user can still submit without dropdowns
      })
      .finally(() => {
        if (isMounted.current) setLoadingDropdowns(false);
      });
  }, [isOpen, editingOpportunity, sourceLeadPrefill]);

  // ── Field update helpers ───────────────────────────────
  const setField = <K extends keyof FormState>(key: K, val: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: val }));

  const handleLookingTypeChange = (lt: number) => {
    // Reset subcat when parent category changes
    const firstSubcat = PROPERTY_SUBCATEGORIES_BY_CATEGORY[lt]?.[0]?.id ?? 0;
    setForm((prev) => ({
      ...prev,
      looking_type: lt,
      looking_subcat_type: firstSubcat,
    }));
  };

  // ── Build submission payload ───────────────────────────
  const buildPayload = () => {
    const followup_datetime =
      form.followup_date && form.followup_time
        ? new Date(`${form.followup_date}T${form.followup_time}:00`).toISOString()
        : null;

    const base = {
      contact_name: form.contact_name.trim(),
      mobile: form.mobile.trim(),
      alternate_mobile: form.alternate_mobile.trim() || null,
      email: form.email.trim() || null,
      address: form.address.trim() || null,
      customer_type: form.customer_type,
      property_type: form.property_type,
      looking_type: form.looking_type,
      looking_subcat_type: form.looking_subcat_type,
      budget_from: parseFloat(form.budget_from) || 0,
      budget_to: parseFloat(form.budget_to) || 0,
      area_from: parseFloat(form.area_from) || 0,
      area_to: parseFloat(form.area_to) || 0,
      area_unit: form.area_unit,
      bhk: parseInt(form.bhk, 10) || 0,
      furnishing: form.furnishing || null,
      property_age: form.property_age || null,
      loanable: form.loanable,
      remark: form.remark.trim() || null,
      assign_franch_id: form.assign_franch_id,
      locations: form.locations.filter((l) => l.locality_name.trim() !== ''),
    };

    if (!isEdit) {
      return {
        ...base,
        assigned_to: form.assigned_to || null,
        followup_datetime,
        source_lead_id: sourceLeadPrefill?.lead_id ?? null,
      };
    }

    // For update, only send locations (server replaces them)
    return {
      ...base,
      locations: form.locations.filter((l) => l.locality_name.trim() !== ''),
    };
  };

  // ── Submit ────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.contact_name.trim()) {
      setError('Contact name is required.');
      return;
    }
    if (!form.mobile.trim()) {
      setError('Mobile number is required.');
      return;
    }

    setSubmitting(true);
    setError(null);

    const url = isEdit
      ? `${API_BASE}/v1/opportunities/${editingOpportunity!.opportunity_id}`
      : `${API_BASE}/v1/opportunities`;
    const method = isEdit ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method,
        headers: authHeaders(true),
        body: JSON.stringify(buildPayload()),
      });
      const json = await res.json();
      if (!res.ok) {
        const detail = json?.detail;
        throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
      }
      onSaved(json as OpportunityDetail);
      fullReset();
      onClose();
    } catch (err: unknown) {
      if (isMounted.current) {
        setError(err instanceof Error ? err.message : 'An error occurred. Please try again.');
      }
    } finally {
      if (isMounted.current) setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const subcats = PROPERTY_SUBCATEGORIES_BY_CATEGORY[form.looking_type] ?? [];
  const title = isEdit ? 'Edit Opportunity' : 'New Opportunity';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
    >
      <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[92vh] flex flex-col overflow-hidden border border-gray-200 dark:border-gray-700">
        {/* Modal header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-[#291BB0]/5 to-transparent dark:from-indigo-500/10">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#291BB0]/10 dark:bg-indigo-500/20">
              <User className="h-5 w-5 text-[#291BB0] dark:text-indigo-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
              {sourceLeadPrefill && !isEdit && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Converting Lead: <strong>{sourceLeadPrefill.lead_id}</strong>
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Error bar */}
        {error && (
          <div className="mx-6 mt-4 flex items-start gap-3 p-3 rounded-lg bg-[#F04B42]/10 border border-[#F04B42]/30 text-[#F04B42]">
            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <p className="text-sm">{error}</p>
            <button
              type="button"
              onClick={() => setError(null)}
              className="ml-auto text-[#F04B42] hover:opacity-70"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Form body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto">
          <div className="px-6 py-4 grid grid-cols-2 gap-4">

            {/* ── Client Details ── */}
            <SectionHeader label="Client Details" />

            <Field label="Contact Name" required>
              <input
                type="text"
                placeholder="Full name"
                value={form.contact_name}
                onChange={(e) => setField('contact_name', e.target.value)}
                className={inputCls}
                required
              />
            </Field>

            <Field label="Mobile" required>
              <input
                type="tel"
                placeholder="10-digit mobile"
                value={form.mobile}
                onChange={(e) => setField('mobile', e.target.value)}
                className={inputCls}
                required
              />
            </Field>

            <Field label="Alternate Mobile">
              <input
                type="tel"
                placeholder="Alternate number"
                value={form.alternate_mobile}
                onChange={(e) => setField('alternate_mobile', e.target.value)}
                className={inputCls}
              />
            </Field>

            <Field label="Email">
              <input
                type="email"
                placeholder="email@example.com"
                value={form.email}
                onChange={(e) => setField('email', e.target.value)}
                className={inputCls}
              />
            </Field>

            <Field label="Address" fullWidth>
              <input
                type="text"
                placeholder="Current address"
                value={form.address}
                onChange={(e) => setField('address', e.target.value)}
                className={inputCls}
              />
            </Field>

            <Field label="Customer Type">
              <div className="relative">
                <select
                  value={form.customer_type}
                  onChange={(e) =>
                    setField('customer_type', e.target.value as 'END_USER' | 'INVESTOR')
                  }
                  className={selectCls}
                >
                  <option value="END_USER">End User</option>
                  <option value="INVESTOR">Investor</option>
                </select>
                <ChevronDown className="absolute right-2.5 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>
            </Field>

            {/* ── Property Preference ── */}
            <SectionHeader label="Property Preference" />

            <Field label="Requirement Type" required>
              <div className="relative">
                <select
                  value={form.property_type}
                  onChange={(e) => setField('property_type', Number(e.target.value))}
                  className={selectCls}
                >
                  <option value={1}>Rent</option>
                  <option value={2}>Buy / Sell</option>
                  <option value={3}>PG</option>
                </select>
                <ChevronDown className="absolute right-2.5 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>
            </Field>

            <Field label="Category" required>
              <div className="relative">
                <select
                  value={form.looking_type}
                  onChange={(e) => handleLookingTypeChange(Number(e.target.value))}
                  className={selectCls}
                >
                  {PROPERTY_CATEGORIES.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2.5 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>
            </Field>

            <Field label="Sub-category" fullWidth>
              <div className="relative">
                <select
                  value={form.looking_subcat_type}
                  onChange={(e) => setField('looking_subcat_type', Number(e.target.value))}
                  className={selectCls}
                >
                  <option value={0}>Any</option>
                  {subcats.map((sc) => (
                    <option key={sc.id} value={sc.id}>
                      {sc.label}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2.5 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>
            </Field>

            {/* ── Budget ── */}
            <SectionHeader label="Budget Range (₹)" />

            <Field label="Budget From">
              <input
                type="number"
                min={0}
                placeholder="Min budget"
                value={form.budget_from}
                onChange={(e) => setField('budget_from', e.target.value)}
                className={inputCls}
              />
            </Field>

            <Field label="Budget To">
              <input
                type="number"
                min={0}
                placeholder="Max budget"
                value={form.budget_to}
                onChange={(e) => setField('budget_to', e.target.value)}
                className={inputCls}
              />
            </Field>

            {/* ── Area ── */}
            <SectionHeader label="Area Range" />

            <Field label="Area From">
              <input
                type="number"
                min={0}
                placeholder="Min area"
                value={form.area_from}
                onChange={(e) => setField('area_from', e.target.value)}
                className={inputCls}
              />
            </Field>

            <div className="flex gap-2">
              <Field label="Area To">
                <input
                  type="number"
                  min={0}
                  placeholder="Max area"
                  value={form.area_to}
                  onChange={(e) => setField('area_to', e.target.value)}
                  className={inputCls}
                />
              </Field>

              <Field label="Unit">
                <div className="relative">
                  <select
                    value={form.area_unit}
                    onChange={(e) => setField('area_unit', e.target.value)}
                    className={selectCls}
                  >
                    {AREA_UNITS.map((u) => (
                      <option key={u} value={u}>{u}</option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
                </div>
              </Field>
            </div>

            {/* ── Specifications ── */}
            <SectionHeader label="Specifications" />

            <Field label="BHK">
              <input
                type="number"
                min={0}
                placeholder="0 = any"
                value={form.bhk}
                onChange={(e) => setField('bhk', e.target.value)}
                className={inputCls}
              />
            </Field>

            <Field label="Furnishing">
              <div className="relative">
                <select
                  value={form.furnishing}
                  onChange={(e) => setField('furnishing', e.target.value)}
                  className={selectCls}
                >
                  <option value="">Any</option>
                  {FURNISHING_OPTIONS.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2.5 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>
            </Field>

            <Field label="Property Age">
              <div className="relative">
                <select
                  value={form.property_age}
                  onChange={(e) => setField('property_age', e.target.value)}
                  className={selectCls}
                >
                  <option value="">Any</option>
                  {PROPERTY_AGE_OPTIONS.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2.5 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>
            </Field>

            <Field label="Loanable">
              <div className="flex gap-2">
                {LOANABLE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setField('loanable', opt.value)}
                    className={`flex-1 py-2 text-sm font-medium rounded-lg border transition-all ${
                      form.loanable === opt.value
                        ? 'bg-[#291BB0] text-white border-[#291BB0]'
                        : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-[#291BB0] hover:text-[#291BB0]'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </Field>

            {/* ── Preferred Localities ── */}
            <SectionHeader label="Preferred Localities" />

            <div className="col-span-2">
              <LocalityMultiPicker
                value={form.locations}
                onChange={(locs) => setField('locations', locs)}
                disabled={submitting}
              />
            </div>

            {/* ── Assignment ── */}
            <SectionHeader label="Franchise & Staff Assignment" />

            <Field label="Franchise Outlet">
              <div className="relative">
                <select
                  value={form.assign_franch_id}
                  onChange={(e) => setField('assign_franch_id', Number(e.target.value))}
                  disabled={loadingDropdowns}
                  className={selectCls}
                >
                  <option value={0}>None / Central Desk</option>
                  {outlets
                    .filter((o) => o.is_active)
                    .map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.name} ({o.city})
                      </option>
                    ))}
                </select>
                <ChevronDown className="absolute right-2.5 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>
            </Field>

            {!isEdit && (
              <Field label="Assign To">
                <div className="relative">
                  <select
                    value={form.assigned_to}
                    onChange={(e) => setField('assigned_to', e.target.value)}
                    disabled={loadingDropdowns}
                    className={selectCls}
                  >
                    <option value="">Self (auto-assign)</option>
                    {assignees.map((a) => (
                      <option key={a.employee_id} value={a.employee_id}>
                        {a.name}
                        {a.role_name ? ` (${a.role_name})` : ''}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-2.5 top-2.5 h-4 w-4 text-gray-400 pointer-events-none" />
                </div>
              </Field>
            )}

            {/* ── Follow-up ── */}
            {!isEdit && (
              <>
                <SectionHeader label="Follow-up Schedule" />

                <Field label="Follow-up Date">
                  <input
                    type="date"
                    value={form.followup_date}
                    onChange={(e) => setField('followup_date', e.target.value)}
                    className={inputCls}
                  />
                </Field>

                <Field label="Follow-up Time">
                  <input
                    type="time"
                    value={form.followup_time}
                    onChange={(e) => setField('followup_time', e.target.value)}
                    className={inputCls}
                  />
                </Field>
              </>
            )}

            {/* ── Remark ── */}
            <SectionHeader label="Remarks" />

            <Field label="Remark" fullWidth>
              <textarea
                rows={3}
                placeholder="Additional notes or requirement details…"
                value={form.remark}
                onChange={(e) => setField('remark', e.target.value)}
                className={`${inputCls} resize-none`}
              />
            </Field>
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={submitting}
              className="px-5 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center gap-2 px-5 py-2 text-sm font-semibold rounded-lg bg-[#291BB0] hover:bg-[#1f14a0] text-white transition-colors disabled:opacity-60 shadow-sm"
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              {submitting ? 'Saving…' : isEdit ? 'Save Changes' : 'Create Opportunity'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default OpportunityFormModal;
