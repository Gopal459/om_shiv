import React, { useState } from 'react';
import { X, Upload, FileSpreadsheet, AlertCircle, CheckCircle2, Copy } from 'lucide-react';

interface ImportLeadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImported: () => void;
}

const SAMPLE_CSV = `contact_name,mobile,email,lead_type,rating,indv_property_address,lead_remark
Ramesh Verma,9829011111,ramesh@example.com,BUY,1,Vaishali Nagar Jaipur,Interested in 3 BHK
Sunita Agarwal,9829022222,sunita@example.com,RENT,2,Mansarovar Jaipur,Looking for furnished apartment
Deepak Sharma,9829033333,deepak@example.com,PG,3,Jagatpura Jaipur,Single room with food`;

export const ImportLeadModal: React.FC<ImportLeadModalProps> = ({
  isOpen,
  onClose,
  onImported,
}) => {
  const [csvText, setCsvText] = useState('');
  const [parsedRows, setParsedRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  if (!isOpen) return null;

  const handleParse = (text: string) => {
    setCsvText(text);
    setError('');
    setSuccess('');

    if (!text.trim()) {
      setParsedRows([]);
      return;
    }

    try {
      const lines = text.trim().split(/\r?\n/).filter(line => line.trim().length > 0);
      if (lines.length < 2) {
        setParsedRows([]);
        return;
      }

      const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
      const rows = [];

      for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(',').map(p => p.trim());
        if (parts.length >= 2) {
          const rowObj: any = {};
          headers.forEach((h, idx) => {
            rowObj[h] = parts[idx] || '';
          });

          // Standardize fields
          rows.push({
            contact_name: rowObj.contact_name || rowObj.name || rowObj['client name'] || `Lead ${i}`,
            mobile: rowObj.mobile || rowObj.phone || rowObj['contact'] || '',
            email: rowObj.email || null,
            lead_type: (rowObj.lead_type || rowObj.type || 'BUY').toUpperCase(),
            rating: parseInt(rowObj.rating || '3', 10) || 3,
            indv_property_address: rowObj.indv_property_address || rowObj.address || rowObj.location || null,
            lead_remark: rowObj.lead_remark || rowObj.remarks || 'Imported from CSV',
          });
        }
      }

      setParsedRows(rows);
    } catch (err) {
      setError('Failed to parse CSV format. Please verify columns.');
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        handleParse(content);
      };
      reader.readAsText(file);
    }
  };

  const handleImportSubmit = async () => {
    if (parsedRows.length === 0) {
      setError('Please paste or upload at least 1 valid lead row');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/v1/leads/import-bulk', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ leads: parsedRows }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Bulk import failed');
      }

      setSuccess(`Successfully imported ${data.imported_count || parsedRows.length} leads into pipeline!`);
      setTimeout(() => {
        onImported();
        onClose();
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'Network error during bulk import');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
      <div className="relative w-full max-w-3xl bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-blue-500/10 text-blue-500 border border-blue-500/20">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Bulk Excel / CSV Lead Import
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Import leads from 99acres, MagicBricks, Meta campaigns, or offline sheets
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 custom-scrollbar">
          {error && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900/60 text-xs font-semibold text-rose-700 dark:text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-900/60 text-xs font-semibold text-emerald-700 dark:text-emerald-300 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{success}</span>
            </div>
          )}

          {/* Upload Drop Area */}
          <div className="border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-2xl p-6 text-center hover:border-blue-500/60 transition-colors">
            <Upload className="w-8 h-8 mx-auto text-slate-400 mb-2" />
            <p className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
              Select or Drag & Drop CSV / Excel File
            </p>
            <p className="text-[11px] text-slate-400 mb-3">
              Supports .csv with headers: contact_name, mobile, email, lead_type, rating, address
            </p>
            <label className="inline-flex items-center px-4 py-2 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-bold text-xs border border-blue-200 dark:border-blue-800 cursor-pointer hover:bg-blue-100 transition-colors">
              <span>Choose CSV File</span>
              <input type="file" accept=".csv,text/csv" onChange={handleFileUpload} className="hidden" />
            </label>
          </div>

          {/* Paste CSV Data Directly */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                Or Paste CSV Raw Text
              </label>
              <button
                type="button"
                onClick={() => handleParse(SAMPLE_CSV)}
                className="text-[11px] font-bold text-blue-500 hover:underline flex items-center gap-1"
              >
                <Copy className="w-3 h-3" />
                <span>Load Sample Data</span>
              </button>
            </div>
            <textarea
              rows={4}
              value={csvText}
              onChange={(e) => handleParse(e.target.value)}
              placeholder="contact_name,mobile,email,lead_type,rating,indv_property_address,lead_remark..."
              className="w-full px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-mono text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          {/* Parsed Preview Table */}
          {parsedRows.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-300">
                <span>Preview Ready Leads ({parsedRows.length} Detected)</span>
                <span className="text-emerald-500 text-[11px]">Valid Format</span>
              </div>
              <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden max-h-48 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800 text-slate-500 border-b border-slate-200 dark:border-slate-700">
                    <tr>
                      <th className="p-2">#</th>
                      <th className="p-2">Client Name</th>
                      <th className="p-2">Mobile</th>
                      <th className="p-2">Type</th>
                      <th className="p-2">Rating</th>
                      <th className="p-2">Locality</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {parsedRows.slice(0, 10).map((r, i) => (
                      <tr key={i} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                        <td className="p-2 text-slate-400">{i + 1}</td>
                        <td className="p-2 font-semibold text-slate-900 dark:text-white">{r.contact_name}</td>
                        <td className="p-2 font-mono">{r.mobile}</td>
                        <td className="p-2 font-bold text-rose-500">{r.lead_type}</td>
                        <td className="p-2">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-800">
                            {r.rating === 1 ? 'Hot' : r.rating === 2 ? 'Warm' : 'Cold'}
                          </span>
                        </td>
                        <td className="p-2 text-slate-400 truncate max-w-xs">{r.indv_property_address || 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {parsedRows.length > 10 && (
                <p className="text-[11px] text-slate-400 text-center">
                  Showing first 10 of {parsedRows.length} total rows...
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end gap-3 bg-slate-50/50 dark:bg-slate-950/40">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleImportSubmit}
            disabled={loading || parsedRows.length === 0}
            className="px-6 py-2.5 rounded-xl bg-[#291BB0] hover:bg-[#1f138e] text-white text-xs font-bold shadow-md shadow-[#291BB0]/20 transition-all disabled:opacity-50 flex items-center gap-2 cursor-pointer"
          >
            {loading ? 'Importing Leads...' : `Import ${parsedRows.length} Leads`}
          </button>
        </div>
      </div>
    </div>
  );
};
