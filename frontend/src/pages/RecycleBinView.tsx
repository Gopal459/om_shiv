import React, { useState, useEffect } from 'react';
import { Trash2, RotateCcw, AlertTriangle, Check, RefreshCw, ShieldAlert, ArrowLeft } from 'lucide-react';

export const RecycleBinView: React.FC = () => {
  const [recycled, setRecycled] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState('');
  const [error, setError] = useState('');

  const fetchRecycleBin = async () => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/v1/admin/recycle-bin', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        setRecycled(data);
      }
    } catch (err: any) {
      setError('Failed to fetch recycle bin listings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecycleBin();
  }, []);

  const handleRestore = async (propertyId: string) => {
    setActionMsg('');
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/admin/properties/${propertyId}/recycle-bin-restore`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('Failed to restore property');
      setActionMsg(`Property ${propertyId} restored successfully!`);
      fetchRecycleBin();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Trash2 className="w-5 h-5 text-rose-500" />
            Recycle Bin & Owner Ad Requests
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Safeguards deleted properties from accidental data loss with instant 1-click restoration.
          </p>
        </div>

        <button
          onClick={fetchRecycleBin}
          disabled={loading}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-xs text-slate-700 dark:text-slate-300 font-semibold border border-slate-200 dark:border-slate-700 transition-colors shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {actionMsg && (
        <div className="p-3 bg-emerald-50 dark:bg-green-950/80 border border-emerald-200 dark:border-green-700/60 rounded-xl text-emerald-800 dark:text-green-300 text-xs flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-600 dark:text-green-400 flex-shrink-0" />
          <span>{actionMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-50 dark:bg-red-950/80 border border-rose-200 dark:border-red-700/60 rounded-xl text-rose-800 dark:text-red-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Recycled Listings Table */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
            Soft-Deleted Inventory ({recycled.length})
          </span>
          <span className="text-[11px] text-slate-500 dark:text-slate-400">
            Auto-Purge Safeguard Active (30 Days Retention)
          </span>
        </div>

        {recycled.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs space-y-2">
            <Trash2 className="w-8 h-8 text-slate-300 dark:text-slate-700 mx-auto" />
            <p className="font-medium text-slate-600 dark:text-slate-400">
              {loading ? 'Loading recycle bin...' : 'No properties in recycle bin. All inventory is active or archived.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="p-4">Property Code</th>
                  <th className="p-4">Title</th>
                  <th className="p-4">Recycled Date</th>
                  <th className="p-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-800 dark:text-slate-200">
                {recycled.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td className="p-4 font-mono font-bold text-rose-500 dark:text-rose-400">
                      {item.property_id}
                    </td>
                    <td className="p-4 font-semibold text-slate-900 dark:text-white">{item.title}</td>
                    <td className="p-4 text-slate-500 dark:text-slate-400">
                      {item.recycled_at ? new Date(item.recycled_at).toLocaleString() : 'N/A'}
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => handleRestore(item.property_id || item.id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        Restore 1-Click
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default RecycleBinView;
