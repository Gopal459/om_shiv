import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Building2,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  Eye,
  Edit,
  Trash2,
  RotateCcw,
  UserCheck,
  Tag,
  AlertCircle,
  ExternalLink,
  MapPin,
  Check,
  X,
  Phone,
  RefreshCw,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import PropertyForm from './PropertyForm';

interface PropertyItem {
  property_id: number;
  propertyid_no: string;
  property_type: number;
  looking_type: number;
  looking_subcat_type: number;
  title: string;
  expected_price: number;
  city_id: number;
  sublocality_address?: string;
  location?: string;
  source_owner_name?: string;
  source_owner_mobile?: string;
  verified_status: number;
  is_active: number;
  sold_status: number;
  recyclebin_status: number;
  assigned_user_id: number;
  live_request_sent: number;
  delete_request_sent: number;
  sold_request_sent: number;
  created_date?: string;
  images?: string;
}

const TAB_CONFIG: Record<string, { label: string; desc: string; badge: string; color: string }> = {
  new_assign: {
    label: 'New & Assign Properties',
    desc: 'Fresh property submissions pending telephonic assignment and staff verification.',
    badge: 'Pending Intake',
    color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
  },
  verify_live: {
    label: 'Verify & Live Properties',
    desc: 'Active live inventory publicly accessible and visible to buyers on the portal.',
    badge: 'Portal Live',
    color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20',
  },
  verification_done: {
    label: 'Verification Done',
    desc: 'Properties verified by field staff awaiting final live portal activation.',
    badge: 'Verified Queue',
    color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
  },
  expired: {
    label: 'Expired Properties',
    desc: 'Listings that reached the end of their listing validity period (30/90 days).',
    badge: 'Listing Expired',
    color: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20',
  },
  deleted: {
    label: 'Delete Property (Recycle Bin)',
    desc: 'Properties soft-deleted or with active deletion requests; can be restored or purged.',
    badge: 'Trash Bin',
    color: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20',
  },
  sold: {
    label: 'Sell Property (Sold Queue)',
    desc: 'Successfully transacted and sold properties closed by franchise or agents.',
    badge: 'Deal Closed',
    color: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20',
  },
  request_live: {
    label: 'Request Live Property',
    desc: 'Listings submitted by external sellers/agents requesting portal live activation.',
    badge: 'Live Requests',
    color: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20',
  },
};

export const PropertyHub: React.FC = () => {
  const { isDark } = useTheme();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Active Tab from query param (default: new_assign)
  const currentTab = searchParams.get('tab') || 'new_assign';
  const tabInfo = TAB_CONFIG[currentTab] || TAB_CONFIG.new_assign;

  // View state: 'LIST' | 'CREATE' | 'EDIT'
  const [viewMode, setViewMode] = useState<'LIST' | 'CREATE' | 'EDIT'>('LIST');
  const [editingId, setEditingId] = useState<number | null>(null);

  // Data State
  const [items, setItems] = useState<PropertyItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Quick Action Modal (Staff Assignment)
  const [assignModalProp, setAssignModalProp] = useState<PropertyItem | null>(null);
  const [selectedStaffId, setSelectedStaffId] = useState<number>(1);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Fetch properties from backend
  const fetchProperties = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const q = new URLSearchParams({
        tab: currentTab,
        page: String(page),
        limit: '20',
      });
      if (search.trim()) q.append('search', search.trim());

      const res = await fetch(`/v1/properties/hub?${q.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('Failed to fetch properties');
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Error fetching properties' });
    } finally {
      setLoading(false);
    }
  }, [currentTab, search, page]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  const handleTabChange = (newTab: string) => {
    setSearchParams({ tab: newTab });
    setPage(1);
    setViewMode('LIST');
    setEditingId(null);
  };

  const handleQuickStatusChange = async (propertyId: number, statusPayload: any, successMsg: string) => {
    setUpdatingStatus(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/properties/tbl/${propertyId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(statusPayload),
      });
      if (!res.ok) throw new Error('Status update failed');
      setNotification({ type: 'success', message: successMsg });
      fetchProperties();
      setAssignModalProp(null);
    } catch (err: any) {
      setNotification({ type: 'error', message: err.message || 'Status update error' });
    } finally {
      setUpdatingStatus(false);
    }
  };

  const formatPrice = (price: number) => {
    if (!price) return '₹ 0';
    if (price >= 10000000) return `₹ ${(price / 10000000).toFixed(2)} Cr`;
    if (price >= 100000) return `₹ ${(price / 100000).toFixed(2)} L`;
    return `₹ ${price.toLocaleString('en-IN')}`;
  };

  if (viewMode === 'CREATE') {
    return (
      <PropertyForm
        onBack={() => setViewMode('LIST')}
        onSuccess={() => {
          setViewMode('LIST');
          fetchProperties();
          setNotification({ type: 'success', message: 'Property created successfully!' });
        }}
      />
    );
  }

  if (viewMode === 'EDIT' && editingId) {
    return (
      <PropertyForm
        propertyId={editingId}
        onBack={() => {
          setViewMode('LIST');
          setEditingId(null);
        }}
        onSuccess={() => {
          setViewMode('LIST');
          setEditingId(null);
          fetchProperties();
          setNotification({ type: 'success', message: 'Property updated successfully!' });
        }}
      />
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Notifications */}
      {notification && (
        <div
          className={`p-4 rounded-xl flex items-center justify-between text-sm animate-slide-down ${
            notification.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400'
              : 'bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400'
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
            )}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="p-1 hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header Banner & Add Property CTA */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5">
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold border ${tabInfo.color}`}
            >
              {tabInfo.badge} ({total})
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            {tabInfo.label}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
            {tabInfo.desc}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchProperties}
            disabled={loading}
            className="p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 transition-colors"
            title="Refresh List"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={() => setViewMode('CREATE')}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white font-bold text-xs shadow-md shadow-rose-500/20 flex items-center gap-2 transition-all"
          >
            <Plus className="w-4 h-4" />
            Add Property
          </button>
        </div>
      </div>

      {/* 7-Tab Navigation Bar Matching Screenshot 7 */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none border-b border-slate-200 dark:border-slate-800">
        {Object.entries(TAB_CONFIG).map(([tabKey, config]) => {
          const isActive = currentTab === tabKey;
          return (
            <button
              key={tabKey}
              type="button"
              onClick={() => handleTabChange(tabKey)}
              className={`px-4 py-2.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all flex items-center gap-2 ${
                isActive
                  ? 'bg-rose-500 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isActive ? 'bg-white' : 'bg-slate-300 dark:bg-slate-600'
                }`}
              ></span>
              {config.label}
            </button>
          );
        })}
      </div>

      {/* Search and Filters Bar */}
      <div className="flex items-center gap-4 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Property ID (e.g. OP-2026-00001), Owner Name, Mobile, or Location..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-rose-500"
          />
        </div>
        {search && (
          <button
            onClick={() => setSearch('')}
            className="text-xs text-rose-500 font-bold hover:underline"
          >
            Clear Search
          </button>
        )}
      </div>

      {/* Property Inventory Table */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-16 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full mx-auto mb-3"></div>
            <p className="text-xs text-slate-400">Loading {tabInfo.label}...</p>
          </div>
        ) : items.length === 0 ? (
          <div className="p-16 text-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
              <Building2 className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              No Properties in {tabInfo.label}
            </h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              There are currently no listings in this status queue. Click Add Property to register a new unit.
            </p>
            <button
              onClick={() => setViewMode('CREATE')}
              className="mt-2 px-4 py-2 rounded-lg bg-rose-500 text-white text-xs font-bold hover:bg-rose-600 transition-colors inline-flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Add First Property
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 font-bold uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">Property ID & Title</th>
                  <th className="px-4 py-3.5">Type & Price</th>
                  <th className="px-4 py-3.5">Owner & Contact</th>
                  <th className="px-4 py-3.5">Location</th>
                  <th className="px-4 py-3.5">Status & Assignment</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-medium">
                {items.map((prop) => {
                  const typeLabel =
                    prop.property_type === 1 ? 'Rent' : prop.property_type === 2 ? 'Sale' : 'PG';
                  return (
                    <tr
                      key={prop.property_id}
                      className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      {/* ID & Title */}
                      <td className="px-5 py-4">
                        <div className="space-y-1">
                          <span className="font-mono font-extrabold text-slate-900 dark:text-white block">
                            {prop.propertyid_no}
                          </span>
                          <span className="text-slate-600 dark:text-slate-300 font-semibold block line-clamp-1">
                            {prop.title}
                          </span>
                        </div>
                      </td>

                      {/* Type & Price */}
                      <td className="px-4 py-4">
                        <div className="space-y-1">
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                            {typeLabel}
                          </span>
                          <div className="font-bold text-rose-600 dark:text-rose-400">
                            {formatPrice(prop.expected_price)}
                          </div>
                        </div>
                      </td>

                      {/* Owner & Contact */}
                      <td className="px-4 py-4">
                        <div className="space-y-0.5">
                          <span className="text-slate-900 dark:text-white font-semibold block">
                            {prop.source_owner_name || 'N/A'}
                          </span>
                          <span className="text-slate-400 text-[11px] flex items-center gap-1 font-mono">
                            <Phone className="w-3 h-3 text-slate-400" />
                            {prop.source_owner_mobile || 'N/A'}
                          </span>
                        </div>
                      </td>

                      {/* Location */}
                      <td className="px-4 py-4">
                        <div className="text-slate-600 dark:text-slate-400 text-[11px] line-clamp-2 max-w-xs flex items-start gap-1">
                          <MapPin className="w-3 h-3 flex-shrink-0 text-slate-400 mt-0.5" />
                          <span>{prop.sublocality_address || prop.location || 'Alwar, Rajasthan'}</span>
                        </div>
                      </td>

                      {/* Status & Assignment */}
                      <td className="px-4 py-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {prop.is_active === 1 ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                                Live
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-500/10 text-slate-500 border border-slate-500/20">
                                Offline
                              </span>
                            )}
                            {prop.verified_status === 1 && (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-600 border border-blue-500/20">
                                Verified
                              </span>
                            )}
                            {prop.sold_status === 1 && (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-600 border border-purple-500/20">
                                Sold
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-400 flex items-center gap-1">
                            <UserCheck className="w-3 h-3 text-slate-400" />
                            {prop.assigned_user_id > 0
                              ? `Assigned (User #${prop.assigned_user_id})`
                              : 'Unassigned Staff'}
                          </div>
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Assign Staff Button */}
                          <button
                            type="button"
                            onClick={() => setAssignModalProp(prop)}
                            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300"
                            title="Assign Telecaller / Field Staff"
                          >
                            <UserCheck className="w-3.5 h-3.5" />
                          </button>

                          {/* Quick Verify & Live toggle */}
                          {prop.is_active === 0 ? (
                            <button
                              type="button"
                              onClick={() =>
                                handleQuickStatusChange(
                                  prop.property_id,
                                  { is_active: 1, verified_status: 1 },
                                  `Property ${prop.propertyid_no} is now LIVE on portal!`
                                )
                              }
                              className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100"
                              title="Make Live on Portal"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() =>
                                handleQuickStatusChange(
                                  prop.property_id,
                                  { is_active: 0 },
                                  `Property ${prop.propertyid_no} set to Offline.`
                                )
                              }
                              className="p-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 hover:bg-amber-100"
                              title="Deactivate / Offline"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          )}

                          {/* Edit Details */}
                          <button
                            type="button"
                            onClick={() => {
                              setEditingId(prop.property_id);
                              setViewMode('EDIT');
                            }}
                            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-blue-600 dark:text-blue-400"
                            title="Edit Property Listing"
                          >
                            <Edit className="w-3.5 h-3.5" />
                          </button>

                          {/* Soft Delete or Restore */}
                          {prop.recyclebin_status === 1 ? (
                            <button
                              type="button"
                              onClick={() =>
                                handleQuickStatusChange(
                                  prop.property_id,
                                  { recyclebin_status: 0, delete_request_sent: 0 },
                                  `Property ${prop.propertyid_no} restored from Recycle Bin!`
                                )
                              }
                              className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100"
                              title="Restore Property"
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() =>
                                handleQuickStatusChange(
                                  prop.property_id,
                                  { recyclebin_status: 1, delete_request_sent: 1 },
                                  `Property ${prop.propertyid_no} moved to Recycle Bin.`
                                )
                              }
                              className="p-1.5 rounded-lg hover:bg-red-50 text-red-500 hover:text-red-700"
                              title="Move to Recycle Bin"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Staff Assignment Modal */}
      {assignModalProp && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl max-w-md w-full p-6 space-y-4 animate-scale-up">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-rose-500" />
                Assign Staff / Telecaller
              </h3>
              <button
                onClick={() => setAssignModalProp(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400">
              Assign property{' '}
              <span className="font-mono font-bold text-slate-900 dark:text-white">
                {assignModalProp.propertyid_no}
              </span>{' '}
              to an operational staff member for follow-up and verification.
            </p>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Select Telecaller / Staff Member
              </label>
              <select
                value={selectedStaffId}
                onChange={(e) => setSelectedStaffId(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs focus:ring-2 focus:ring-rose-500"
              >
                <option value={1}>Gopal Saini (Lead Telecaller - EMP-0001)</option>
                <option value={2}>Priya Sharma (Verification Executive - EMP-0002)</option>
                <option value={3}>Rahul Meena (Alwar Franchise Manager - EMP-0003)</option>
              </select>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setAssignModalProp(null)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={updatingStatus}
                onClick={() =>
                  handleQuickStatusChange(
                    assignModalProp.property_id,
                    { assigned_user_id: selectedStaffId },
                    `Property successfully assigned to Staff #${selectedStaffId}`
                  )
                }
                className="px-5 py-2 rounded-xl bg-rose-500 hover:bg-rose-600 text-white font-bold text-xs shadow-md transition-all flex items-center gap-1.5"
              >
                {updatingStatus ? 'Assigning...' : 'Confirm Assignment'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PropertyHub;
