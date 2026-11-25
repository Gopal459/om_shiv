import React, { useState, useEffect } from 'react';
import { Sliders, Plus, Check, AlertCircle, RefreshCw } from 'lucide-react';

export const DynamicMastersEditor: React.FC = () => {
  const [schema, setSchema] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState<string>('AREA_UNITS');

  // Form to add new option
  const [newCode, setNewCode] = useState('');
  const [newLabel, setNewLabel] = useState('');
  const [displayOrder, setDisplayOrder] = useState<number>(10);
  const [categories, setCategories] = useState<string>(''); // comma-separated e.g. "3" for agri
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  const fetchSchema = async () => {
    setLoading(true);
    try {
      const res = await fetch('/v1/public/property-schema');
      if (res.ok) {
        const data = await res.json();
        setSchema(data);
        if (!selectedGroup && Object.keys(data).length > 0) {
          setSelectedGroup(Object.keys(data)[0]);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchema();
  }, []);

  const handleCreateOption = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setMsg('');

    try {
      const token = localStorage.getItem('access_token');
      const applicableList = categories
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0)
        .map(Number);

      const res = await fetch('/v1/admin/property-master/options', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          group_code: selectedGroup,
          code: newCode.toUpperCase(),
          label: newLabel,
          display_order: displayOrder,
          applicable_categories: applicableList,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to add option');

      setMsg(`Option '${newLabel}' added successfully!`);
      setNewCode('');
      setNewLabel('');
      setCategories('');
      fetchSchema();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const groupKeys = Object.keys(schema);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-emerald-500" />
            Dynamic Property Master Tables
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            100% Dynamic options configured from database (zero hardcoded frontend enums).
          </p>
        </div>

        <button
          onClick={fetchSchema}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-xs text-slate-700 dark:text-slate-300 font-semibold border border-slate-200 dark:border-slate-700 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Schema
        </button>
      </div>

      {/* Main Grid: Group Selector & Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Group Tabs */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 space-y-1 shadow-sm">
          <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider px-3 pb-2">
            Master Groups
          </div>
          {groupKeys.map((group) => (
            <button
              key={group}
              onClick={() => setSelectedGroup(group)}
              className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-between ${
                selectedGroup === group
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/30'
                  : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <span>{group}</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold ${
                  selectedGroup === group
                    ? 'bg-emerald-700 text-white'
                    : 'bg-slate-100 dark:bg-slate-950/60 text-slate-600 dark:text-slate-400'
                }`}
              >
                {schema[group]?.length || 0}
              </span>
            </button>
          ))}
        </div>

        {/* Right Columns: Active Options List & Add Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Active Options Table */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3">
              Configured Options for{' '}
              <span className="text-emerald-600 dark:text-emerald-400 font-mono">{selectedGroup}</span>
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 font-bold">
                    <th className="pb-2">Code</th>
                    <th className="pb-2">Label</th>
                    <th className="pb-2">Display Order</th>
                    <th className="pb-2">Scoped Categories</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-800 dark:text-slate-200">
                  {schema[selectedGroup]?.map((opt: any) => (
                    <tr key={opt.code} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                      <td className="py-2.5 font-mono text-slate-500 dark:text-slate-400">{opt.code}</td>
                      <td className="py-2.5 font-semibold text-slate-900 dark:text-white">{opt.label}</td>
                      <td className="py-2.5 text-slate-500 dark:text-slate-400">{opt.display_order}</td>
                      <td className="py-2.5">
                        {opt.applicable_categories && opt.applicable_categories.length > 0 ? (
                          <span className="px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 text-[10px] border border-blue-200 dark:border-blue-800 font-medium">
                            Category IDs: {opt.applicable_categories.join(', ')}
                          </span>
                        ) : (
                          <span className="text-[10px] text-slate-400">All Categories</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Add Option Form */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3 flex items-center gap-1.5">
              <Plus className="w-4 h-4 text-emerald-500" />
              Add Dynamic Option to{' '}
              <span className="text-emerald-600 dark:text-emerald-400 font-mono">{selectedGroup}</span>
            </h3>

            {msg && (
              <div className="mb-3 p-2.5 bg-emerald-50 dark:bg-green-950/80 border border-emerald-200 dark:border-green-700/60 rounded-lg text-emerald-800 dark:text-green-300 text-xs flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-600 dark:text-green-400 flex-shrink-0" />
                <span>{msg}</span>
              </div>
            )}
            {error && (
              <div className="mb-3 p-2.5 bg-rose-50 dark:bg-red-950/80 border border-rose-200 dark:border-red-700/60 rounded-lg text-rose-800 dark:text-red-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 dark:text-red-400 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleCreateOption} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Option Code (e.g. BIGHA, EAST)
                </label>
                <input
                  type="text"
                  required
                  value={newCode}
                  onChange={(e) => setNewCode(e.target.value)}
                  placeholder="CODE_UPPERCASE"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white uppercase focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Human Label (e.g. Bigha)
                </label>
                <input
                  type="text"
                  required
                  value={newLabel}
                  onChange={(e) => setNewLabel(e.target.value)}
                  placeholder="e.g. Bigha"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Display Order
                </label>
                <input
                  type="number"
                  required
                  value={displayOrder}
                  onChange={(e) => setDisplayOrder(Number(e.target.value))}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Category IDs (Optional, e.g. 3 for Agri)
                </label>
                <input
                  type="text"
                  value={categories}
                  onChange={(e) => setCategories(e.target.value)}
                  placeholder="e.g. 3 or leave blank for all"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 focus:outline-none"
                />
              </div>

              <div className="sm:col-span-2 pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs uppercase tracking-wider rounded-lg shadow-md transition-colors"
                >
                  {submitting ? 'Saving...' : 'Save Dynamic Option'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
export default DynamicMastersEditor;
