import React, { useEffect, useState } from 'react';
import { Sliders, Shield, History, Save, CheckCircle2 } from 'lucide-react';

export const SettingsEditor: React.FC = () => {
  const [settings, setSettings] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<any>('');
  const [editReason, setEditReason] = useState<string>('');
  const [message, setMessage] = useState<string>('');

  const fetchSettings = async () => {
    try {
      const res = await fetch('/v1/settings');
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch('/v1/audit-logs?limit=20');
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data.items || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchSettings();
    fetchAuditLogs();
  }, []);

  const handleSaveSetting = async (key: string) => {
    if (!editReason.trim()) {
      alert('A business reason is mandatory for modifying settings.');
      return;
    }
    try {
      const res = await fetch(`/v1/settings/${key}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          value: editValue,
          reason: editReason,
        }),
      });
      if (res.ok) {
        setMessage(`Setting ${key} updated successfully.`);
        setEditingKey(null);
        setEditReason('');
        fetchSettings();
        fetchAuditLogs();
      }
    } catch (err) {
      alert('Failed to update setting');
    }
  };

  const categories = ['ALL', ...Array.from(new Set(settings.map((s) => s.category)))];
  const filtered = selectedCategory === 'ALL' ? settings : settings.filter((s) => s.category === selectedCategory);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-emerald-500" />
            Dynamic System Settings & Audit Ledger
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Runtime configuration parameters governed by immutable audit logging.
          </p>
        </div>
      </div>

      {message && (
        <div className="p-3 bg-emerald-50 dark:bg-green-950/80 border border-emerald-200 dark:border-green-700/60 rounded-xl text-emerald-800 dark:text-green-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-green-400 flex-shrink-0" />
          <span>{message}</span>
        </div>
      )}

      {/* Category Pills */}
      <div className="flex flex-wrap gap-2">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
              selectedCategory === cat
                ? 'bg-[#291BB0] text-white shadow-sm'
                : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Settings Table Card */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-950/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="p-4">Key / Parameter</th>
                <th className="p-4">Description</th>
                <th className="p-4">Value</th>
                <th className="p-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-800 dark:text-slate-200">
              {filtered.map((setting) => (
                <tr key={setting.key} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="p-4 font-mono font-bold text-emerald-600 dark:text-emerald-400">
                    {setting.key}
                  </td>
                  <td className="p-4 text-slate-600 dark:text-slate-400 max-w-xs">{setting.description}</td>
                  <td className="p-4">
                    {editingKey === setting.key ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-900 dark:text-white"
                        />
                        <input
                          type="text"
                          placeholder="Mandatory reason for audit..."
                          value={editReason}
                          onChange={(e) => setEditReason(e.target.value)}
                          className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-900 dark:text-white"
                        />
                      </div>
                    ) : (
                      <span className="font-mono bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded text-slate-800 dark:text-slate-200">
                        {typeof setting.value === 'object' ? JSON.stringify(setting.value) : String(setting.value)}
                      </span>
                    )}
                  </td>
                  <td className="p-4 text-right">
                    {editingKey === setting.key ? (
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleSaveSetting(setting.key)}
                          className="px-3 py-1 bg-[#291BB0] hover:bg-[#1f138e] text-white font-bold rounded-lg text-xs flex items-center gap-1 shadow-sm"
                        >
                          <Save className="w-3 h-3" /> Save
                        </button>
                        <button
                          onClick={() => setEditingKey(null)}
                          className="px-2 py-1 text-slate-500 hover:text-slate-700 dark:hover:text-white text-xs"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => {
                          setEditingKey(setting.key);
                          setEditValue(typeof setting.value === 'object' ? JSON.stringify(setting.value) : setting.value);
                          setEditReason('');
                        }}
                        className="px-3 py-1 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700"
                      >
                        Edit
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Logs Preview */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
          <History className="w-4 h-4 text-blue-500" />
          Recent Security Audit Trail (Last 20 Events)
        </h3>
        <div className="space-y-2 text-xs">
          {auditLogs.length === 0 ? (
            <p className="text-slate-500 dark:text-slate-400 py-2">No audit events recorded yet.</p>
          ) : (
            auditLogs.map((log) => (
              <div
                key={log.id}
                className="p-3 bg-slate-50 dark:bg-slate-950/60 rounded-xl border border-slate-200 dark:border-slate-800 flex items-center justify-between"
              >
                <div>
                  <span className="font-mono font-bold text-blue-600 dark:text-blue-400 mr-2">{log.action}</span>
                  <span className="text-slate-700 dark:text-slate-300">{log.entity_name}</span>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Reason: {log.reason || 'None specified'}</p>
                </div>
                <span className="text-[10px] text-slate-400">
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsEditor;
