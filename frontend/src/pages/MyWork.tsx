import React, { useEffect, useState } from 'react';
import { Phone, MessageCircle, Clock, AlertTriangle, Flame, ArrowRight } from 'lucide-react';

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
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-800">
          <Flame className="w-3 h-3 mr-1 text-red-600" /> HOT
        </span>
      );
    }
    if (temp === 'WARM') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800">
          WARM
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">
        COLD
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">My Daily Work Queue</h2>
          <p className="text-sm text-slate-500">
            Prioritized actions: Overdue follow-ups & Untouched incoming leads
          </p>
        </div>
        <div className="flex gap-2">
          <span className="px-3 py-1 bg-green-100 text-green-800 font-semibold text-xs rounded-full">
            {leads.length} Active Items
          </span>
        </div>
      </div>

      {loading ? (
        <div className="py-12 text-center text-slate-500">Loading prioritized tasks...</div>
      ) : leads.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
          <p className="text-slate-600 font-medium">All caught up! No overdue or untouched leads.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {leads.map((lead) => (
            <div
              key={lead.lead_id}
              className={`bg-white rounded-xl border p-4 shadow-sm hover:shadow-md transition-shadow flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                lead.priority_bucket === 'OVERDUE'
                  ? 'border-red-300 bg-red-50/20'
                  : lead.is_untouched
                  ? 'border-amber-300 bg-amber-50/20'
                  : 'border-slate-200'
              }`}
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-slate-600">
                    {lead.lead_id}
                  </span>
                  {lead.priority_bucket === 'OVERDUE' && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-red-600 text-white">
                      <AlertTriangle className="w-3 h-3 mr-1" /> OVERDUE
                    </span>
                  )}
                  {lead.is_untouched && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-500 text-white">
                      <Clock className="w-3 h-3 mr-1" /> UNTOUCHED
                    </span>
                  )}
                  {getTemperatureBadge(lead.temperature)}
                </div>
                <h3 className="text-lg font-bold text-slate-900">{lead.full_name}</h3>
                <p className="text-sm text-slate-500 flex items-center gap-2">
                  <span>Stage: <strong className="text-slate-700">{lead.stage}</strong></span>
                  {lead.follow_up_date && (
                    <span>• Next: {new Date(lead.follow_up_date).toLocaleString()}</span>
                  )}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={`tel:${lead.mobile}`}
                  className="p-2.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 flex items-center justify-center"
                  title="Direct Phone Call"
                >
                  <Phone className="w-4 h-4" />
                </a>
                <a
                  href={`https://wa.me/${lead.mobile}`}
                  target="_blank"
                  rel="noreferrer"
                  className="p-2.5 rounded-lg bg-green-600 text-white hover:bg-green-700 flex items-center justify-center shadow-sm"
                  title="WhatsApp Chat"
                >
                  <MessageCircle className="w-4 h-4" />
                </a>
                <button
                  onClick={() => onSelectLead(lead.lead_id)}
                  className="px-3.5 py-2 rounded-lg bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 flex items-center"
                >
                  Log Action <ArrowRight className="w-3.5 h-3.5 ml-1" />
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
