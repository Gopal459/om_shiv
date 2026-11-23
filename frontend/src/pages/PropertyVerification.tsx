import React, { useEffect, useState } from 'react';
import { CheckCircle2, PhoneCall, FileText, RefreshCw, Trash2, ArrowUpRight } from 'lucide-react';

export const PropertyVerification: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'VERIFY' | 'RECYCLE'>('VERIFY');
  const [properties, setProperties] = useState<any[]>([]);
  const [recycleBin, setRecycleBin] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProp, setSelectedProp] = useState<any>(null);
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">7-Step Property Verification</h2>
          <p className="text-sm text-slate-500">
            Telephonic verification, legal document review, and portal go-live
          </p>
        </div>
        <div className="flex bg-slate-200 p-1 rounded-lg text-xs font-bold">
          <button
            onClick={() => setActiveTab('VERIFY')}
            className={`px-4 py-1.5 rounded-md ${
              activeTab === 'VERIFY' ? 'bg-white shadow text-slate-900' : 'text-slate-600'
            }`}
          >
            Verification Queue
          </button>
          <button
            onClick={() => setActiveTab('RECYCLE')}
            className={`px-4 py-1.5 rounded-md flex items-center gap-1 ${
              activeTab === 'RECYCLE' ? 'bg-white shadow text-slate-900' : 'text-slate-600'
            }`}
          >
            <Trash2 className="w-3.5 h-3.5" /> Recycle Bin
          </button>
        </div>
      </div>

      {message && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
          {message}
        </div>
      )}

      {activeTab === 'VERIFY' ? (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
          <h3 className="text-lg font-bold text-slate-900">7-Step Verification Workflow Overview</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-bold text-slate-800">Step 1-2: Ingest & Assign</span>
              <p className="text-slate-500 mt-1">Listing received via portal/quick post. Telecaller assigned.</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-bold text-slate-800">Step 3: Phone Verification</span>
              <p className="text-slate-500 mt-1">Price confirmed with owner. Physical visit scheduled.</p>
            </div>
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-bold text-slate-800">Step 4-5: Docs & Photos</span>
              <p className="text-slate-500 mt-1">Title deed, utility bill, and geotagged photos uploaded.</p>
            </div>
            <div className="p-3 bg-green-50 rounded-lg border border-green-200">
              <span className="font-bold text-green-800">Step 6-7: Senior Go-Live</span>
              <p className="text-green-700 mt-1">Checklist confirmed. Listed live with 90-day timer.</p>
            </div>
          </div>

          <div className="border-t pt-4">
            <h4 className="text-sm font-bold text-slate-800 mb-2">Manager Approval Checklist</h4>
            <div className="space-y-2 text-sm text-slate-700">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={areaConfirmed}
                  onChange={(e) => setAreaConfirmed(e.target.checked)}
                  className="rounded text-green-600"
                />
                Super Area vs. Carpet Area mathematically verified ($Carpet &lt; Super$)
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={photosGenuine}
                  onChange={(e) => setPhotosGenuine(e.target.checked)}
                  className="rounded text-green-600"
                />
                Property photos genuine, watermark applied, and coordinates mapped
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={ownershipConfirmed}
                  onChange={(e) => setOwnershipConfirmed(e.target.checked)}
                  className="rounded text-green-600"
                />
                Ownership documents (Title Deed / Khasra / Electricity Bill) reviewed
              </label>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h3 className="text-lg font-bold text-slate-900 mb-4">Recycle Bin (Soft Deleted Listings)</h3>
          {recycleBin.length === 0 ? (
            <p className="text-slate-500 text-sm">Recycle bin is empty.</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {recycleBin.map((p) => (
                <div key={p.property_id} className="py-3 flex items-center justify-between">
                  <div>
                    <span className="font-mono text-xs font-bold text-slate-600">{p.property_id}</span>
                    <h4 className="font-bold text-slate-800">{p.title}</h4>
                    <p className="text-xs text-slate-400">Recycled: {new Date(p.recycled_at).toLocaleString()}</p>
                  </div>
                  <button
                    onClick={() => handleRestore(p.property_id)}
                    className="px-3 py-1.5 rounded-lg bg-green-600 text-white font-semibold text-xs hover:bg-green-700 flex items-center gap-1"
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
