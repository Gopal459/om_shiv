import React, { useEffect, useState } from 'react';
import { Phone, MessageCircle, Clock, AlertTriangle, Flame, ArrowRight, CheckCircle2 } from 'lucide-react';

interface LeadItem {
  id: number;
  lead_id: string;
  full_name: string;
  mobile: string;
  stage: string;
  temperature: string | null;
  follow_up_date: string | null;
  is_untouched: boolean;
  priority_bucket: string;
}

interface MyWorkProps {
  onSelectLead: (leadId: string) => void;
}

export const MyWork: React.FC<MyWorkProps> = ({ onSelectLead }) => {
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMyWork = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const res = await fetch('/v1/leads/my-work', {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) {
          const data = await res.json();
          setLeads(data.items || []);
        }
      } catch (err) {
        console.error('Failed to load my-work queue', err);
      } finally {
        setLoading(false);
      }
    };
    fetchMyWork();
  }, []);

  const getTemperatureBadge = (temp: string | null) => {
    if (temp === 'HOT') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
          <Flame className="w-3 h-3 mr-1 text-rose-600 dark:text-rose-400" /> HOT
        </span>
      );
    }
    if (temp === 'WARM') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
          WARM
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
        COLD
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            My Daily Work & Inbound Lead Queue
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Prioritized actions: Overdue follow-ups & Untouched incoming leads (3h SLA)
          </p>
        </div>
        <div className="flex gap-2">
          <span className="px-3 py-1 bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-400 font-bold text-xs rounded-full border border-emerald-200 dark:border-emerald-800">
            {leads.length} Active Items
          </span>
        </div>
      </div>

      {loading ? (
        <div className="py-12 text-center text-slate-500 text-xs">Loading prioritized tasks...</div>
      ) : leads.length === 0 ? (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-8 text-center shadow-sm">
          <p className="text-slate-600 dark:text-slate-400 font-medium text-xs">
            All caught up! No overdue or untouched leads requiring escalation.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {leads.map((lead) => (
            <div
              key={lead.lead_id}
              className={`bg-white dark:bg-slate-900 rounded-2xl border p-4 sm:p-5 shadow-sm hover:shadow-md transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                lead.priority_bucket === 'OVERDUE'
                  ? 'border-rose-300 dark:border-rose-900/60 bg-rose-50/20 dark:bg-rose-950/10'
                  : lead.is_untouched
                  ? 'border-amber-300 dark:border-amber-900/60 bg-amber-50/20 dark:bg-amber-950/10'
                  : 'border-slate-200 dark:border-slate-800'
              }`}
            >
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-xs font-bold text-slate-600 dark:text-slate-400">
                    {lead.lead_id}
                  </span>
                  {lead.priority_bucket === 'OVERDUE' && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-rose-600 text-white shadow-xs">
                      <AlertTriangle className="w-3 h-3 mr-1" /> OVERDUE
                    </span>
                  )}
                  {lead.is_untouched && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-500 text-white shadow-xs">
                      <Clock className="w-3 h-3 mr-1" /> UNTOUCHED
                    </span>
                  )}
                  {getTemperatureBadge(lead.temperature)}
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">{lead.full_name}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-2 flex-wrap">
                  <span>
                    Stage: <strong className="text-slate-700 dark:text-slate-300">{lead.stage}</strong>
                  </span>
                  {lead.follow_up_date && (
                    <span>• Next: {new Date(lead.follow_up_date).toLocaleString()}</span>
                  )}
                </p>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <a
                  href={`tel:${lead.mobile}`}
                  className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors shadow-2xs"
                  title="Direct Phone Call"
                >
                  <Phone className="w-4 h-4" />
                </a>
                <a
                  href={`https://wa.me/${lead.mobile}`}
                  target="_blank"
                  rel="noreferrer"
                  className="p-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-sm"
                  title="WhatsApp Chat"
                >
                  <MessageCircle className="w-4 h-4" />
                </a>
                <button
                  onClick={() => onSelectLead(lead.lead_id)}
                  className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 dark:bg-emerald-600 dark:hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1 transition-colors shadow-sm"
                >
                  <span>Log Action</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyWork;
