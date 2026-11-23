import React, { useState } from 'react';
import { X, UserPlus, Flame, Phone, Mail, MapPin, Tag, DollarSign, FileText, CheckCircle2, AlertCircle } from 'lucide-react';

interface CreateLeadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
  defaultType?: string;
}

const LEAD_SOURCES = [
  { id: 1, name: 'Website Inbound Inquiry' },
  { id: 2, name: 'Builder Project Landing' },
  { id: 3, name: 'Franchisee / Agent Direct' },
  { id: 4, name: 'Request a Callback Form' },
  { id: 5, name: 'Report a Problem Form' },
  { id: 6, name: 'Bulk CSV / Portal Import' },
  { id: 7, name: 'Newspaper Advertisement' },
  { id: 8, name: 'Facebook Ad Campaign' },
  { id: 9, name: 'Google Search Ad' },
  { id: 10, name: 'Poster & Hoarding' },
  { id: 11, name: 'Direct Incoming Call' },
  { id: 12, name: 'Office Walk-in' },
  { id: 13, name: 'YouTube Channel' },
  { id: 14, name: 'Instagram Reel / Post' },
  { id: 15, name: 'WhatsApp Business' },
  { id: 16, name: 'Referral / Channel Partner' },
  { id: 17, name: 'MagicBricks Sync' },
  { id: 18, name: '99acres Sync' },
  { id: 19, name: 'Housing.com Sync' },
  { id: 20, name: 'SMS Marketing Blast' },
  { id: 21, name: 'Email Newsletter' },
  { id: 22, name: 'Property Expo / Exhibition' },
  { id: 23, name: 'Telecaller Cold Outreach' },
  { id: 24, name: 'Other Inbound Source' },
];

export const CreateLeadModal: React.FC<CreateLeadModalProps> = ({
  isOpen,
  onClose,
  onCreated,
  defaultType = 'BUY',
}) => {
  const [leadType, setLeadType] = useState<string>(defaultType.toUpperCase());
  const [contactName, setContactName] = useState('');
  const [mobile, setMobile] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [propertyAddress, setPropertyAddress] = useState('');
  const [leadSourceId, setLeadSourceId] = useState<number>(1);
  const [rating, setRating] = useState<number>(3); // 1-Hot, 2-Warm, 3-Cold
  const [dealPrice, setDealPrice] = useState('');
  const [leadRemark, setLeadRemark] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!contactName.trim()) {
      setError('Customer name is required');
      return;
    }
    if (!mobile.trim() || mobile.replace(/\D/g, '').length < 10) {
      setError('Please provide a valid 10-digit mobile number');
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/v1/leads/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          contact_name: contactName.trim(),
          mobile: mobile.trim(),
          email: email.trim() || null,
          address: address.trim() || null,
          lead_type: leadType,
          lead_source_id: leadSourceId,
          rating,
          indv_property_address: propertyAddress.trim() || null,
          lead_remark: leadRemark.trim() || null,
          deal_final_price: dealPrice ? parseFloat(dealPrice) : 0.0,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create lead');
      }

      onCreated();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Network error creating lead');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
      <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-rose-500/10 text-rose-500 border border-rose-500/20">
              <UserPlus className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 dark:text-white">
                Create New Inbound Lead
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Manual intake for walk-ins, direct phone inquiries & campaigns
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

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5 custom-scrollbar">
          {error && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900/60 text-xs font-semibold text-rose-700 dark:text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Property Type Tabs (Buy, Rent, PG) */}
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
              Property Transaction Type *
            </label>
            <div className="grid grid-cols-3 gap-2">
              {['BUY', 'RENT', 'PG'].map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setLeadType(type)}
                  className={`py-2 rounded-xl text-xs font-bold transition-all border ${
                    leadType === type
                      ? 'bg-rose-500 text-white border-rose-500 shadow-sm'
                      : 'bg-slate-50 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {type === 'BUY' ? 'Buy Property' : type === 'RENT' ? 'Rent Property' : 'Paying Guest (PG)'}
                </button>
              ))}
            </div>
          </div>

          {/* Customer Name & Mobile */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Client Full Name *
              </label>
              <input
                type="text"
                required
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                placeholder="e.g. Ramesh Chandra Sharma"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                10-Digit Mobile Number *
              </label>
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-xs font-bold text-slate-400">+91</span>
                <input
                  type="tel"
                  required
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value)}
                  placeholder="9829012345"
                  className="w-full pl-11 pr-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                />
              </div>
            </div>
          </div>

          {/* Email & Client Address */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Email Address (Optional)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ramesh@example.com"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Client Address / City
              </label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="e.g. Alwar / Jaipur"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              />
            </div>
          </div>

          {/* Lead Source (24 Options) & Call Rating */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Lead Source (24 Configured Channels)
              </label>
              <select
                value={leadSourceId}
                onChange={(e) => setLeadSourceId(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              >
                {LEAD_SOURCES.map((src) => (
                  <option key={src.id} value={src.id}>
                    {src.id}. {src.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Call Temperature Rating
              </label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setRating(1)}
                  className={`py-2 px-1.5 rounded-xl text-xs font-bold flex items-center justify-center gap-1 border transition-all ${
                    rating === 1
                      ? 'bg-rose-500 text-white border-rose-500 shadow-sm'
                      : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-rose-600 dark:text-rose-400'
                  }`}
                >
                  <Flame className="w-3.5 h-3.5" /> Hot
                </button>
                <button
                  type="button"
                  onClick={() => setRating(2)}
                  className={`py-2 px-1.5 rounded-xl text-xs font-bold flex items-center justify-center gap-1 border transition-all ${
                    rating === 2
                      ? 'bg-amber-500 text-white border-amber-500 shadow-sm'
                      : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-amber-600 dark:text-amber-400'
                  }`}
                >
                  Warm
                </button>
                <button
                  type="button"
                  onClick={() => setRating(3)}
                  className={`py-2 px-1.5 rounded-xl text-xs font-bold flex items-center justify-center gap-1 border transition-all ${
                    rating === 3
                      ? 'bg-slate-600 text-white border-slate-600 shadow-sm'
                      : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  Cold
                </button>
              </div>
            </div>
          </div>

          {/* Property Requirement & Budget */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Interested Property / Locality Requirement
              </label>
              <input
                type="text"
                value={propertyAddress}
                onChange={(e) => setPropertyAddress(e.target.value)}
                placeholder="e.g. 2 BHK Flat in Vaishali Nagar"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Target Budget (₹)
              </label>
              <input
                type="number"
                value={dealPrice}
                onChange={(e) => setDealPrice(e.target.value)}
                placeholder="e.g. 4500000"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              />
            </div>
          </div>

          {/* Remarks */}
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
              Initial Remarks & Call Notes
            </label>
            <textarea
              rows={3}
              value={leadRemark}
              onChange={(e) => setLeadRemark(e.target.value)}
              placeholder="Client looking for immediate possession, financing needed..."
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
            />
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700 text-white text-xs font-bold shadow-md shadow-rose-500/20 transition-all disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? 'Creating Lead...' : 'Create & Assign Lead'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
