import React, { useState } from 'react';
import {
  Flame,
  Phone,
  MessageSquare,
  Search,
  Filter,
  ArrowRight,
  Eye,
  Trash2,
  Calendar,
  MapPin,
} from 'lucide-react';
import { KanbanLeadItem } from './LeadKanbanBoard';

interface LeadTableViewProps {
  leads: KanbanLeadItem[];
  onSelectLead: (leadId: string) => void;
  loading?: boolean;
}

export const LeadTableView: React.FC<LeadTableViewProps> = ({
  leads,
  onSelectLead,
  loading = false,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');

  const filtered = leads.filter((l) => {
    const matchesSearch =
      l.contact_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.mobile.includes(searchTerm) ||
      l.lead_unique_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.property_address && l.property_address.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesType =
      selectedType === 'ALL' || l.lead_type.toUpperCase() === selectedType.toUpperCase();

    return matchesSearch && matchesType;
  });

  const getStatusBadge = (status: number, stage: number) => {
    if (status === 0) {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">
          New Intake
        </span>
      );
    }
    if (status === 1 && stage in [2, 3]) {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300">
          Site Visit
        </span>
      );
    }
    if (status === 1) {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300">
          In Progress
        </span>
      );
    }
    if (status === 4) {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-teal-100 dark:bg-teal-950 text-teal-700 dark:text-teal-300">
          Qualified
        </span>
      );
    }
    if (status === 5) {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
          Deal Closed
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300">
        Disqualified
      </span>
    );
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden space-y-4 p-5">
      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search leads by name, mobile, lead ID, or locality..."
            className="w-full pl-10 pr-4 py-2.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20"
          />
        </div>

        {/* Type Filter Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {['ALL', 'BUY', 'RENT', 'PG'].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setSelectedType(t)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                selectedType === t
                  ? 'bg-[#291BB0] text-white shadow-xs'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200'
              }`}
            >
              {t === 'ALL' ? 'All Types' : t}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-100 dark:border-slate-800">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 dark:bg-slate-950/70 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800 font-bold">
            <tr>
              <th className="p-3">Request ID</th>
              <th className="p-3">Customer Details</th>
              <th className="p-3">Type</th>
              <th className="p-3">Pipeline Status</th>
              <th className="p-3">Rating</th>
              <th className="p-3">Property Requirement</th>
              <th className="p-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {loading ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-400">
                  Loading lead records...
                </td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-400">
                  No matching leads found.
                </td>
              </tr>
            ) : (
              filtered.map((lead) => (
                <tr
                  key={lead.lead_unique_id}
                  onClick={() => onSelectLead(lead.lead_unique_id)}
                  className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 cursor-pointer transition-colors"
                >
                  <td className="p-3 font-mono font-bold text-slate-900 dark:text-white">
                    {lead.lead_unique_id}
                  </td>
                  <td className="p-3">
                    <div className="font-bold text-slate-900 dark:text-white">
                      {lead.contact_name}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      +91 {lead.mobile.replace(/\D/g, '').slice(-10)}
                    </div>
                  </td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        lead.lead_type === 'BUY'
                          ? 'bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300'
                          : lead.lead_type === 'RENT'
                          ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300'
                          : 'bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300'
                      }`}
                    >
                      {lead.lead_type}
                    </span>
                  </td>
                  <td className="p-3">{getStatusBadge(lead.lead_status, lead.stage)}</td>
                  <td className="p-3">
                    {lead.rating === 1 ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-500">
                        <Flame className="w-3.5 h-3.5" /> Hot
                      </span>
                    ) : lead.rating === 2 ? (
                      <span className="text-[11px] font-bold text-amber-500">Warm</span>
                    ) : (
                      <span className="text-[11px] font-bold text-slate-400">Cold</span>
                    )}
                  </td>
                  <td className="p-3 max-w-xs truncate text-slate-600 dark:text-slate-300">
                    <div>{lead.property_address || 'Alwar / Jaipur'}</div>
                    {lead.deal_final_price && lead.deal_final_price > 0 ? (
                      <div className="text-[10px] font-semibold text-emerald-600">
                        ₹ {lead.deal_final_price.toLocaleString('en-IN')}
                      </div>
                    ) : null}
                  </td>
                  <td className="p-3 text-right">
                    <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                      <a
                        href={`tel:${lead.mobile}`}
                        title="Call"
                        className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100"
                      >
                        <Phone className="w-3 h-3" />
                      </a>
                      <a
                        href={`https://wa.me/${lead.mobile.replace(/\D/g, '')}`}
                        target="_blank"
                        rel="noreferrer"
                        title="WhatsApp"
                        className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100"
                      >
                        <MessageSquare className="w-3 h-3" />
                      </a>
                      <button
                        type="button"
                        onClick={() => onSelectLead(lead.lead_unique_id)}
                        className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200"
                      >
                        <Eye className="w-3 h-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
        <span>Showing {filtered.length} leads</span>
        <span>Real-time sync</span>
      </div>
    </div>
  );
};
