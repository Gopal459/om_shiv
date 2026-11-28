import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  Badge,
  CheckCircle2,
  Home,
  Loader2,
  Lock,
  MapPin,
  Phone,
  Tag,
  X,
} from 'lucide-react';
import {
  RelatedPropertiesResponse,
  RelatedPropertyItem,
  authHeaders,
} from '../../types/opportunities';
import { OpportunitySummary, OpportunityDetail } from '../../types/opportunities';

const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

function formatPrice(price: number | null | undefined): string {
  if (!price || price === 0) return '—';
  if (price >= 10_000_000) return `₹${(price / 10_000_000).toFixed(2)} Cr`;
  if (price >= 100_000) return `₹${(price / 100_000).toFixed(2)} L`;
  return `₹${price.toLocaleString('en-IN')}`;
}

interface RelatedPropertiesModalProps {
  isOpen: boolean;
  onClose: () => void;
  opportunity: OpportunitySummary | OpportunityDetail | null;
  onSelectForDeal?: (prop: RelatedPropertyItem) => void;
}

const RelatedPropertiesModal: React.FC<RelatedPropertiesModalProps> = ({
  isOpen,
  onClose,
  opportunity,
  onSelectForDeal,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<RelatedPropertiesResponse | null>(null);

  useEffect(() => {
    if (!isOpen || !opportunity) {
      setData(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    fetch(
      `${API_BASE}/v1/opportunities/${opportunity.opportunity_id}/related-properties`,
      { headers: authHeaders(false) }
    )
      .then(async (res) => {
        const json = await res.json();
        if (!res.ok) {
          const detail = json?.detail;
          throw new Error(
            typeof detail === 'string' ? detail : JSON.stringify(detail)
          );
        }
        return json as RelatedPropertiesResponse;
      })
      .then(setData)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to load matching properties');
      })
      .finally(() => setLoading(false));
  }, [isOpen, opportunity]);

  if (!isOpen) return null;

  const handleBackdrop = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={handleBackdrop}
    >
      <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden border border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-[#291BB0]/5 to-transparent dark:from-indigo-500/10">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Matching Properties
            </h2>
            {opportunity && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {opportunity.contact_name} — {opportunity.opportunity_code ?? `#${opportunity.opportunity_id}`}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loading && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-[#291BB0] dark:text-indigo-400" />
              <span className="ml-3 text-gray-500 dark:text-gray-400">
                Running match engine…
              </span>
            </div>
          )}

          {!loading && error && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-[#F04B42]/10 border border-[#F04B42]/30 text-[#F04B42]">
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          {!loading && !error && data && data.restricted_reason && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 text-amber-700 dark:text-amber-400">
              <Lock className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium">Access Restricted</p>
                <p className="text-sm">{data.restricted_reason}</p>
              </div>
            </div>
          )}

          {!loading && !error && data && !data.restricted_reason && data.count === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400 dark:text-gray-500">
              <Home className="h-12 w-12 mb-3 opacity-30" />
              <p className="text-base font-medium text-gray-500 dark:text-gray-400">No matching properties found</p>
              <p className="text-sm mt-1">Try adjusting budget, BHK, or locality filters.</p>
            </div>
          )}

          {!loading && !error && data && !data.restricted_reason && data.items.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Found <strong className="text-gray-800 dark:text-gray-200">{data.count}</strong> matching{' '}
                {data.count === 1 ? 'property' : 'properties'}
              </p>

              {data.items.map((prop) => (
                <div
                  key={prop.property_id}
                  className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 space-y-3 hover:border-[#291BB0]/40 dark:hover:border-indigo-400/40 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                          {prop.project_name ?? prop.propertyid_no ?? `Property #${prop.property_id}`}
                        </span>
                        {prop.distance_km !== null && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-[#291BB0]/10 text-[#291BB0] dark:bg-indigo-500/20 dark:text-indigo-300 border border-[#291BB0]/20">
                            <MapPin className="h-3 w-3" />
                            {prop.distance_km} km
                          </span>
                        )}
                        {prop.is_exclusive === 1 && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-200 dark:border-amber-700">
                            Exclusive
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-1.5 mt-1 text-xs text-gray-500 dark:text-gray-400">
                        <MapPin className="h-3 w-3" />
                        {[prop.sublocality_address, prop.location, prop.pincode]
                          .filter(Boolean)
                          .join(', ') || '—'}
                      </div>
                    </div>

                    <div className="text-right flex-shrink-0">
                      <div className="text-base font-bold text-[#291BB0] dark:text-indigo-400">
                        {formatPrice(prop.expected_price)}
                      </div>
                      {prop.price_negociable === 1 && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">Negotiable</span>
                      )}
                    </div>
                  </div>

                  {/* Details row */}
                  <div className="flex flex-wrap gap-3 text-xs text-gray-600 dark:text-gray-400">
                    {prop.noof_bhk != null && prop.noof_bhk > 0 && (
                      <span className="flex items-center gap-1">
                        <Home className="h-3 w-3" />
                        {prop.noof_bhk} BHK
                      </span>
                    )}
                    {prop.area != null && prop.area > 0 && (
                      <span className="flex items-center gap-1">
                        <Tag className="h-3 w-3" />
                        {prop.area} {prop.area_unit ?? ''}
                      </span>
                    )}
                    {prop.match_reasons.length > 0 && (
                      <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        {prop.match_reasons.join(' · ')}
                      </span>
                    )}
                  </div>

                  {/* Owner info */}
                  {!prop.owner_masked && (prop.source_owner_name || prop.source_owner_mobile) && (
                    <div className="flex items-center gap-4 pt-1 border-t border-gray-200 dark:border-gray-700">
                      {prop.source_owner_name && (
                        <span className="text-xs text-gray-700 dark:text-gray-300">
                          👤 {prop.source_owner_name}
                        </span>
                      )}
                      {prop.source_owner_mobile && (
                        <a
                          href={`tel:${prop.source_owner_mobile}`}
                          className="flex items-center gap-1 text-xs text-[#291BB0] dark:text-indigo-400 hover:underline"
                        >
                          <Phone className="h-3 w-3" />
                          {prop.source_owner_mobile}
                        </a>
                      )}
                    </div>
                  )}
                  {prop.owner_masked && (
                    <div className="flex items-center gap-1.5 pt-1 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-400 dark:text-gray-500">
                      <Lock className="h-3 w-3" />
                      Owner details managed by Omshiv
                    </div>
                  )}

                  {/* Select for Deal */}
                  {onSelectForDeal && (
                    <div className="flex justify-end pt-1">
                      <button
                        type="button"
                        onClick={() => onSelectForDeal(prop)}
                        className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-[#291BB0] hover:bg-[#1f14a0] text-white transition-colors"
                      >
                        Select for Deal Schedule
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default RelatedPropertiesModal;
