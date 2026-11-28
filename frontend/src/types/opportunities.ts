// ============================================================
// Opportunities Module — TypeScript Types & Constants
// ============================================================

// ── Tab types ──────────────────────────────────────────────
export type OpportunityTab =
  | 'new'
  | 'today'
  | 'open'
  | 'missing'
  | 'all'
  | 'in_progress'
  | 'closed';

// ── Location input (sent to / received from API) ───────────
export interface OpportunityLocationInput {
  locality_name: string;
  latitude: number | null;
  longitude: number | null;
  radius_km: number;
}

// ── Summary (returned by list endpoint) ───────────────────
export interface OpportunitySummary {
  opportunity_id: number;
  opportunity_code: string;
  source_lead_id: string | null;
  contact_name: string;
  mobile: string;
  customer_type: 'END_USER' | 'INVESTOR';
  property_type: number;
  looking_type: number;
  looking_subcat_type: number;
  budget_from: number;
  budget_to: number;
  area_from: number;
  area_to: number;
  area_unit: string;
  bhk: number;
  lead_status: number;
  status_label: string;
  lead_open: number;
  calls_status: number;
  assigned_to: string | null;
  assigned_to_name: string | null;
  assign_franch_id: number;
  followup_datetime: string | null;
  deal_date: string | null;
  registry_date: string | null;
  is_propira_property: boolean;
  matched_property_code: string | null;
  locations: OpportunityLocationInput[];
  matching_properties_count: number;
  created_at: string | null;
}

// ── Activity ───────────────────────────────────────────────
export interface OpportunityActivity {
  id: number;
  opportunity_id: number;
  action_type: string;
  note: string | null;
  status_before: number | null;
  status_after: number | null;
  performed_by: string | null;
  performed_by_name: string | null;
  created_at: string | null;
}

// ── Reschedule log ─────────────────────────────────────────
export interface OpportunityRescheduleLog {
  id: number;
  opportunity_id: number;
  old_followup_datetime: string | null;
  new_followup_datetime: string | null;
  current_update: string | null;
  remark: string | null;
  rescheduled_by: string | null;
  rescheduled_by_name: string | null;
  created_at: string | null;
}

// ── Detail (returned by get + create + update endpoints) ───
export interface OpportunityDetail extends OpportunitySummary {
  alternate_mobile: string | null;
  email: string | null;
  address: string | null;
  furnishing: string | null;
  property_age: string | null;
  loanable: 'YES' | 'NO' | 'MAYBE' | null;
  remark: string | null;
  assign_franchstaff_id: number | null;
  franchise_name: string | null;
  disqualified_reason: number | null;
  disqualified_reason_label: string | null;
  current_update: string | null;
  last_remark: string | null;
  matched_property_id: number | null;
  deal_property_category: number | null;
  deal_property_subcategory: number | null;
  deal_property_address: string | null;
  deal_location_lat: string | null;
  deal_location_long: string | null;
  closed_at: string | null;
  created_by: string | null;
  updated_at: string | null;
  activities: OpportunityActivity[];
  reschedules: OpportunityRescheduleLog[];
}

// ── Dashboard ──────────────────────────────────────────────
export interface OpportunityDashboardResponse {
  counts: Record<OpportunityTab, number>;
  chart_breakdown: {
    total: number;
    open: number;
    disqualified: number;
    qualified_propira: number;
    qualified_other: number;
    closed: number;
  };
}

// ── Related properties ─────────────────────────────────────
export interface RelatedPropertyItem {
  property_id: number;
  propertyid_no: string | null;
  property_type: number;
  looking_type: number;
  looking_subcat_type: number | null;
  project_name: string | null;
  location: string | null;
  sublocality_address: string | null;
  nearby_area: string | null;
  pincode: string | null;
  location_lat: string | null;
  location_long: string | null;
  noof_bhk: number | null;
  area: number | null;
  area_unit: string | null;
  expected_price: number;
  price_negociable: number | null;
  description: string | null;
  images: string | null;
  is_exclusive: number | null;
  distance_km: number | null;
  match_reasons: string[];
  owner_masked: boolean;
  source_owner_name: string | null;
  source_owner_mobile: string | null;
  source_owner_email: string | null;
  created_date: string | null;
}

export interface RelatedPropertiesResponse {
  opportunity_id: number;
  count: number;
  owner_masked: boolean;
  restricted_reason: string | null;
  items: RelatedPropertyItem[];
}

// ── Dropdown options ───────────────────────────────────────
export interface FranchiseOutletOption {
  id: number;
  outlet_code: string;
  name: string;
  city: string;
  is_active: boolean;
}

export interface AssigneeOption {
  employee_id: string;
  name: string;
  role_name: string | null;
  role_code: string | null;
  is_active?: boolean;
}

// ── Status meta ────────────────────────────────────────────
export interface OpportunityStatusMeta {
  code: number;
  label: string;
  badgeClass: string;
  dotClass: string;
}

export const OPPORTUNITY_STATUS_META: Record<number, OpportunityStatusMeta> = {
  1: {
    code: 1,
    label: 'In Progress',
    badgeClass:
      'bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/25',
    dotClass: 'bg-sky-500',
  },
  2: {
    code: 2,
    label: 'Disqualified',
    badgeClass:
      'bg-[#F04B42]/10 text-[#F04B42] dark:text-red-300 border-[#F04B42]/30',
    dotClass: 'bg-[#F04B42]',
  },
  4: {
    code: 4,
    label: 'Deal Scheduled',
    badgeClass:
      'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/25',
    dotClass: 'bg-amber-500',
  },
  5: {
    code: 5,
    label: 'Closed / Won',
    badgeClass:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25',
    dotClass: 'bg-emerald-500',
  },
};

// ── Disqualified reasons ───────────────────────────────────
export const DISQUALIFIED_REASONS: Record<number, string> = {
  1: 'Inaccurate Data',
  2: 'Not Interested',
  3: 'Not Responding',
  4: 'Call Me Later',
  5: 'Disconnecting Call',
  6: 'Rejected',
  7: 'Other',
};

// ── Property categories & sub-categories ──────────────────
export const PROPERTY_CATEGORIES: { id: number; label: string }[] = [
  { id: 1, label: 'Residential' },
  { id: 2, label: 'Commercial' },
  { id: 3, label: 'Agricultural' },
  { id: 4, label: 'Industrial' },
];

export const PROPERTY_SUBCATEGORIES_BY_CATEGORY: Record<
  number,
  { id: number; label: string }[]
> = {
  1: [
    { id: 1, label: 'Flat / Apartment' },
    { id: 2, label: 'Independent House / Villa' },
    { id: 3, label: 'Residential Plot / Land' },
    { id: 4, label: 'Builder Floor' },
  ],
  2: [
    { id: 5, label: 'Commercial Office' },
    { id: 6, label: 'Commercial Retail Shop' },
    { id: 7, label: 'Commercial Plot' },
  ],
  3: [
    { id: 8, label: 'Agricultural Farmland' },
    { id: 9, label: 'Farmhouse Land' },
  ],
  4: [
    { id: 10, label: 'Industrial Factory / Shed' },
    { id: 11, label: 'Industrial Plot' },
  ],
};

// ── Area units ─────────────────────────────────────────────
export const AREA_UNITS: string[] = [
  'Sq.Ft',
  'Sq.Yd',
  'Gaj',
  'Sq.Meter',
  'Acre',
  'Bigha',
];

// ── Furnishing options ─────────────────────────────────────
export const FURNISHING_OPTIONS: string[] = [
  'Unfurnished',
  'Semi-Furnished',
  'Fully Furnished',
];

// ── Property age options ───────────────────────────────────
export const PROPERTY_AGE_OPTIONS: string[] = [
  'New / Under Construction',
  '0-1 Year',
  '1-3 Years',
  '3-5 Years',
  '5-10 Years',
  '10+ Years',
];

// ── Loanable options ───────────────────────────────────────
export const LOANABLE_OPTIONS: { value: 'YES' | 'NO' | 'MAYBE'; label: string }[] =
  [
    { value: 'YES', label: 'Yes' },
    { value: 'NO', label: 'No' },
    { value: 'MAYBE', label: 'Maybe' },
  ];

// ── Auth headers helper (matches websiteForms.ts pattern) ──
export const authHeaders = (includeJson = true): Record<string, string> => {
  const token = localStorage.getItem('access_token');
  const headers: Record<string, string> = {};
  if (includeJson) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};
