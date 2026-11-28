export type CallbackStatusCode = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export type CallbackTab =
  | 'new'
  | 'today'
  | 'open'
  | 'missing'
  | 'converted'
  | 'all'
  | 'converted_property';

export type CallbackSortBy = 'created_date' | 'followup_datetime' | 'name' | 'callback_id';
export type CallbackOrderBy = 'desc' | 'asc';

export interface CallbackStatusMeta {
  code: CallbackStatusCode;
  label: string;
  badgeClass: string;
  dotClass: string;
}

export const CALLBACK_STATUS_META: Record<number, CallbackStatusMeta> = {
  0: {
    code: 0,
    label: 'New',
    badgeClass:
      'bg-[#291BB0]/10 text-[#291BB0] dark:bg-indigo-500/20 dark:text-indigo-300 border-[#291BB0]/25 dark:border-indigo-400/30',
    dotClass: 'bg-[#291BB0] dark:bg-indigo-400',
  },
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
  3: {
    code: 3,
    label: 'Solved',
    badgeClass:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25',
    dotClass: 'bg-emerald-500',
  },
  4: {
    code: 4,
    label: 'Qualified',
    badgeClass:
      'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/25',
    dotClass: 'bg-amber-500',
  },
  5: {
    code: 5,
    label: 'Converted to Lead',
    badgeClass:
      'bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/25',
    dotClass: 'bg-purple-500',
  },
  6: {
    code: 6,
    label: 'Converted Property',
    badgeClass:
      'bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/25',
    dotClass: 'bg-teal-500',
  },
};

export const DISQUALIFIED_REASONS: Record<number, string> = {
  1: 'Inaccurate Data',
  2: 'Not Interested',
  3: 'Not Response',
  4: 'Call Me Later',
  5: 'Disconnecting Call',
  6: 'Rejected',
  7: 'Other',
};

export const CURRENT_UPDATE_OPTIONS: readonly string[] = [
  'Interested',
  'Call Back Later',
  'Site Visit Planned',
  'Price Discussion',
  'Shared Details on WhatsApp',
  'Ringing / Follow-Up',
];

export interface CallbackRescheduleLogItem {
  id: number;
  callback_id: number;
  old_followup_datetime: string | null;
  new_followup_datetime: string;
  current_update: string | null;
  remark: string;
  rescheduled_by: string | null;
  rescheduled_by_name?: string | null;
  created_at: string;
}

export interface CallbackActivityItem {
  id: number;
  callback_id: number;
  action_type: string;
  title: string;
  status_before: number | null;
  status_after: number | null;
  remark: string | null;
  performed_by: string | null;
  performed_by_name?: string | null;
  created_at: string;
}

export interface CallbackSummary {
  callback_id: number;
  lead_unique_id: string | null;
  name: string;
  mobile_number: string;
  phone_code: string;
  message: string | null;
  property_id: number | null;
  property_code: string | null;
  property_title?: string | null;
  assigned_user_id: string | null;
  assigned_user_name: string | null;
  lead_status: number;
  status_label: string;
  calls_status: number;
  lead_open: number;
  disqualified_reason: number;
  disqualified_reason_label: string | null;
  current_update: string | null;
  last_remark: string | null;
  followup_datetime: string | null;
  opportunity_converted: number;
  lead_converted: number;
  converted_lead_id: string | null;
  website_inquiry_id: number | null;
  created_date: string | null;
  modified_date: string | null;
}

export interface CallbackDetail extends CallbackSummary {
  reschedule_history: CallbackRescheduleLogItem[];
  activities: CallbackActivityItem[];
}

export interface DashboardCounts {
  new_calls: number;
  today_calls: number;
  open_calls: number;
  missing_calls: number;
  converted_leads: number;
  all_calls: number;
  converted_property: number;
}

export interface AssigneeOption {
  employee_id: string;
  name: string;
  role_name: string | null;
  role_code: string | null;
  is_active: boolean;
}

export type ProblemStatus = 'NEW' | 'IN_REVIEW' | 'RESOLVED' | 'REJECTED';

export const PROBLEM_STATUS_META: Record<
  ProblemStatus,
  { label: string; badgeClass: string }
> = {
  NEW: {
    label: 'New',
    badgeClass:
      'bg-[#291BB0]/10 text-[#291BB0] dark:bg-indigo-500/20 dark:text-indigo-300 border-[#291BB0]/25',
  },
  IN_REVIEW: {
    label: 'In Review',
    badgeClass:
      'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/25',
  },
  RESOLVED: {
    label: 'Resolved',
    badgeClass:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/25',
  },
  REJECTED: {
    label: 'Rejected',
    badgeClass:
      'bg-[#F04B42]/10 text-[#F04B42] dark:text-red-300 border-[#F04B42]/30',
  },
};

export interface ProblemReportItem {
  id: number;
  inquiry_type: string;
  full_name: string;
  mobile: string;
  email: string | null;
  details: Record<string, any> | null;
  status: ProblemStatus;
  assigned_to: string | null;
  assigned_to_name: string | null;
  related_property_code: string | null;
  property_title: string | null;
  resolution_remark: string | null;
  resolved_by: string | null;
  resolved_by_name: string | null;
  resolved_at: string | null;
  is_converted: boolean;
  converted_lead_id: string | null;
  converted_by_emp_id: string | null;
  converted_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProblemCounts {
  all: number;
  new: number;
  in_review: number;
  resolved: number;
  rejected: number;
}

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
