import React, { useEffect, useState } from 'react';
import { Sliders, Shield, History, Save, CheckCircle } from 'lucide-react';

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
      <div>
        <h2 className="text-2xl font-bold text-slate-900">Dynamic System Settings & Audit Ledger</h2>
        <p className="text-sm text-slate-500">
          Runtime configuration parameters governed by immutable audit logging
        </p>
      </div>

      {message && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
          {message}
        </div>
      )}

      {/* Category Pills */}
      <div className="flex flex-wrap gap-2">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold ${
              selectedCategory === cat
                ? 'bg-slate-900 text-white'
                : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Settings Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center gap-2 font-bold text-sm text-slate-800">
          <Sliders className="w-4 h-4 text-green-600" /> Configurable System Settings ({filtered.length})
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase">
              <tr>
                <th className="p-3">Key / Purpose</th>
                <th className="p-3">Category</th>
                <th className="p-3">Current Value</th>
                <th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((s) => {
                const isEditing = editingKey === s.key;
                return (
                  <tr key={s.key} className="hover:bg-slate-50/50">
                    <td className="p-3">
                      <span className="font-mono font-bold text-slate-900">{s.key}</span>
                      <p className="text-slate-500 text-[11px] mt-0.5">{s.description}</p>
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded bg-slate-100 font-semibold text-slate-600">
                        {s.category}
                      </span>
                    </td>
                    <td className="p-3 font-mono">
                      {isEditing ? (
                        <div className="space-y-2">
                          <input
                            type="text"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="w-full border border-slate-300 rounded p-1 text-xs"
                          />
                          <input
                            type="text"
                            required
                            placeholder="Mandatory business reason..."
                            value={editReason}
                            onChange={(e) => setEditReason(e.target.value)}
                            className="w-full border border-amber-300 bg-amber-50 rounded p-1 text-xs"
                          />
                        </div>
                      ) : (
                        <span className="font-bold text-slate-800">
                          {typeof s.value === 'object' ? JSON.stringify(s.value) : String(s.value)}
                        </span>
                      )}
                    </td>
                    <td className="p-3">
                      {isEditing ? (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleSaveSetting(s.key)}
                            className="px-2.5 py-1 bg-green-600 text-white font-bold rounded hover:bg-green-700"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingKey(null)}
                            className="px-2 py-1 bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => {
                            setEditingKey(s.key);
                            setEditValue(s.value);
                            setEditReason('');
                          }}
                          className="text-green-700 hover:underline font-semibold"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Log Stream */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
        <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
          <History className="w-4 h-4 text-slate-600" /> Recent Audit Ledger Entries
        </h3>
        <div className="divide-y divide-slate-100 text-xs">
          {auditLogs.map((log) => (
            <div key={log.id} className="py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <span className="font-bold text-slate-800">{log.entity_name}</span> /{' '}
                <span className="font-mono text-slate-600">{log.entity_id}</span> :{' '}
                <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold">{log.action}</span>
                <p className="text-slate-500 text-[11px] mt-0.5">
                  Changed by <strong className="text-slate-700">{log.performed_by}</strong> • {new Date(log.timestamp).toLocaleString()}
                </p>
              </div>
              <div className="font-mono text-[11px] text-slate-600 bg-slate-50 p-1.5 rounded border border-slate-100">
                {JSON.stringify(log.new_state || log.new_values)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
export default SettingsEditor;
