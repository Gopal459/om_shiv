import React, { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCircle2, PhoneCall, FileText, RefreshCw, Trash2, ArrowUpRight, Building2, ShieldCheck } from 'lucide-react';

export const PropertyVerification: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab')?.toUpperCase();

  const activeTab = useMemo<'VERIFY' | 'RECYCLE'>(() => {
    return tabParam === 'RECYCLE' ? 'RECYCLE' : 'VERIFY';
  }, [tabParam]);

  const setActiveTab = (tab: 'VERIFY' | 'RECYCLE') => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (tab === 'VERIFY') {
          next.delete('tab');
        } else {
          next.set('tab', tab.toLowerCase());
        }
        return next;
      },
      { replace: true }
    );
  };
  const [properties, setProperties] = useState<any[]>([]);
  const [recycleBin, setRecycleBin] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  // Approval checklist
  const [areaConfirmed, setAreaConfirmed] = useState(true);
  const [photosGenuine, setPhotosGenuine] = useState(true);
  const [ownershipConfirmed, setOwnershipConfirmed] = useState(true);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await fetch('/v1/admin/recycle-bin');
      if (res.ok) {
        const binData = await res.json();
        setRecycleBin(binData);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [activeTab]);

  const handleApprove = async (propId: string) => {
    try {
      const res = await fetch(`/v1/properties/${propId}/verify-and-approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          area_confirmed: areaConfirmed,
          photos_genuine_confirmed: photosGenuine,
          ownership_confirmed: ownershipConfirmed,
        }),
      });
      if (res.ok) {
        setMessage(`Property ${propId} verified and live for 90 days!`);
        fetchQueue();
      }
    } catch (err: any) {
      setMessage('Failed to approve property');
    }
  };

  const handleRestore = async (propId: string) => {
    try {
      const res = await fetch(`/v1/admin/properties/${propId}/recycle-bin-restore`, {
        method: 'POST',
      });
      if (res.ok) {
        setMessage(`Property ${propId} restored to live inventory!`);
        fetchQueue();
      }
    } catch (err) {
      setMessage('Failed to restore property');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Building2 className="w-5 h-5 text-blue-500" />
            7-Step Property Verification Hub
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Telephonic verification, legal document review, and portal go-live with 90-day expiry timers.
          </p>
        </div>
        <div className="flex bg-slate-100 dark:bg-slate-900 p-1 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-bold">
          <button
            onClick={() => setActiveTab('VERIFY')}
            className={`px-4 py-1.5 rounded-lg transition-all ${
              activeTab === 'VERIFY'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            Verification Workflow
          </button>
          <button
            onClick={() => setActiveTab('RECYCLE')}
            className={`px-4 py-1.5 rounded-lg flex items-center gap-1 transition-all ${
              activeTab === 'RECYCLE'
                ? 'bg-rose-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Trash2 className="w-3.5 h-3.5" /> Recycle Bin
          </button>
        </div>
      </div>

      {message && (
        <div className="p-3 bg-emerald-50 dark:bg-green-950/80 border border-emerald-200 dark:border-green-700/60 rounded-xl text-emerald-800 dark:text-green-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-green-400 flex-shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {activeTab === 'VERIFY' ? (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-6">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            7-Step Verification Workflow Overview
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
            <div className="p-3.5 bg-slate-50 dark:bg-slate-950/60 rounded-xl border border-slate-200 dark:border-slate-800">
              <span className="font-bold text-slate-800 dark:text-slate-200">Step 1-2: Ingest & Assign</span>
              <p className="text-slate-500 dark:text-slate-400 mt-1">Listing received via portal or quick post. Verification officer assigned.</p>
            </div>
            <div className="p-3.5 bg-slate-50 dark:bg-slate-950/60 rounded-xl border border-slate-200 dark:border-slate-800">
              <span className="font-bold text-slate-800 dark:text-slate-200">Step 3: Phone Verification</span>
              <p className="text-slate-500 dark:text-slate-400 mt-1">Price confirmed with owner. Physical visit scheduled.</p>
            </div>
            <div className="p-3.5 bg-slate-50 dark:bg-slate-950/60 rounded-xl border border-slate-200 dark:border-slate-800">
              <span className="font-bold text-slate-800 dark:text-slate-200">Step 4-5: Docs & Photos</span>
              <p className="text-slate-500 dark:text-slate-400 mt-1">Title deed, utility bill, and geotagged photos uploaded.</p>
            </div>
            <div className="p-3.5 bg-emerald-50 dark:bg-green-950/80 rounded-xl border border-emerald-200 dark:border-green-800/60">
              <span className="font-bold text-emerald-800 dark:text-emerald-300">Step 6-7: Senior Go-Live</span>
              <p className="text-emerald-700 dark:text-emerald-400 mt-1">Checklist confirmed. Listed live on website with 90-day timer.</p>
            </div>
          </div>

          <div className="border-t border-slate-200 dark:border-slate-800 pt-5">
            <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-3">
              Manager Verification Checklist
            </h4>
            <div className="space-y-2.5 text-xs text-slate-700 dark:text-slate-300">
              <label className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer">
                <input
                  type="checkbox"
                  checked={areaConfirmed}
                  onChange={(e) => setAreaConfirmed(e.target.checked)}
                  className="rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 dark:border-slate-700"
                />
                <span>Super Area vs. Carpet Area mathematically verified (Carpet Area &lt; Super Area)</span>
              </label>
              <label className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer">
                <input
                  type="checkbox"
                  checked={photosGenuine}
                  onChange={(e) => setPhotosGenuine(e.target.checked)}
                  className="rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 dark:border-slate-700"
                />
                <span>Property photos genuine, watermark applied, and coordinates mapped</span>
              </label>
              <label className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer">
                <input
                  type="checkbox"
                  checked={ownershipConfirmed}
                  onChange={(e) => setOwnershipConfirmed(e.target.checked)}
                  className="rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 dark:border-slate-700"
                />
                <span>Ownership documents (Title Deed / Khasra / Electricity Bill) reviewed</span>
              </label>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Trash2 className="w-4 h-4 text-rose-500" />
            Recycle Bin (Soft Deleted Listings)
          </h3>
          {recycleBin.length === 0 ? (
            <p className="text-slate-500 dark:text-slate-400 text-xs py-4 text-center">
              Recycle bin is empty. All listings are active.
            </p>
          ) : (
            <div className="divide-y divide-slate-200 dark:divide-slate-800">
              {recycleBin.map((p) => (
                <div key={p.property_id} className="py-3.5 flex items-center justify-between">
                  <div>
                    <span className="font-mono text-xs font-bold text-rose-500 dark:text-rose-400">
                      {p.property_id}
                    </span>
                    <h4 className="font-bold text-slate-900 dark:text-white text-xs">{p.title}</h4>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      Recycled: {new Date(p.recycled_at).toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={() => handleRestore(p.property_id)}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1 shadow-sm transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> 1-Click Restore
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PropertyVerification;
