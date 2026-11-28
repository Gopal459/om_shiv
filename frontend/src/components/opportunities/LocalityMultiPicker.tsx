import React, { useCallback, useEffect, useRef, useState } from 'react';
import { MapPin, Plus, X } from 'lucide-react';
import { OpportunityLocationInput } from '../../types/opportunities';

// ── Google Maps singleton loader ───────────────────────────
let gmapsPromise: Promise<void> | null = null;

function loadGoogleMaps(apiKey: string): Promise<void> {
  if (gmapsPromise) return gmapsPromise;
  gmapsPromise = new Promise<void>((resolve, reject) => {
    if (typeof window !== 'undefined' && (window as any).google?.maps?.places) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => {
      gmapsPromise = null;
      reject(new Error('Google Maps failed to load'));
    };
    document.head.appendChild(script);
  });
  return gmapsPromise;
}

// ── Preset cities ──────────────────────────────────────────
const PRESET_CITIES: { label: string; locality_name: string }[] = [
  { label: 'Alwar Bypass', locality_name: 'Alwar Bypass' },
  { label: 'Vaishali Nagar, Alwar', locality_name: 'Vaishali Nagar, Alwar' },
  { label: 'Tijara Road, Alwar', locality_name: 'Tijara Road, Alwar' },
  { label: 'Bhiwadi', locality_name: 'Bhiwadi' },
  { label: 'Neemrana', locality_name: 'Neemrana' },
  { label: 'Mansarovar, Jaipur', locality_name: 'Mansarovar, Jaipur' },
];

// ── Default blank row ──────────────────────────────────────
function blankRow(): OpportunityLocationInput {
  return { locality_name: '', latitude: null, longitude: null, radius_km: 10 };
}

// ── Props ──────────────────────────────────────────────────
interface LocalityMultiPickerProps {
  value: OpportunityLocationInput[];
  onChange: (locs: OpportunityLocationInput[]) => void;
  disabled?: boolean;
}

// ── Main component ─────────────────────────────────────────
const LocalityMultiPicker: React.FC<LocalityMultiPickerProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  const [mapsReady, setMapsReady] = useState(false);
  const [mapsError, setMapsError] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const autocompleteRefs = useRef<any[]>([]);

  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined;
  const hasMapsKey = typeof apiKey === 'string' && apiKey.trim().length > 0;

  // Load Google Maps if key is available
  useEffect(() => {
    if (!hasMapsKey) return;
    loadGoogleMaps(apiKey!.trim())
      .then(() => setMapsReady(true))
      .catch(() => setMapsError(true));
  }, [hasMapsKey, apiKey]);

  // Attach Places Autocomplete to each search input
  const attachAutocomplete = useCallback(
    (index: number) => {
      if (!mapsReady || disabled) return;
      const inputEl = inputRefs.current[index];
      if (!inputEl) return;
      if (autocompleteRefs.current[index]) return; // already attached

      const ac = new (window as any).google.maps.places.Autocomplete(inputEl, {
        types: ['(cities)'],
        componentRestrictions: { country: 'in' },
        fields: ['name', 'geometry'],
      });

      ac.addListener('place_changed', () => {
        const place = ac.getPlace();
        const loc = place?.geometry?.location;
        const rows = [...value];
        rows[index] = {
          ...rows[index],
          locality_name: place.name ?? rows[index].locality_name,
          latitude: loc ? loc.lat() : rows[index].latitude,
          longitude: loc ? loc.lng() : rows[index].longitude,
        };
        onChange(rows);
      });

      autocompleteRefs.current[index] = ac;
    },
    [mapsReady, disabled, value, onChange]
  );

  useEffect(() => {
    if (!mapsReady) return;
    value.forEach((_, i) => attachAutocomplete(i));
  }, [mapsReady, value.length, attachAutocomplete]);

  // ── Handlers ───────────────────────────────────────────────
  const addRow = () => {
    if (disabled) return;
    onChange([...value, blankRow()]);
  };

  const removeRow = (index: number) => {
    if (disabled) return;
    autocompleteRefs.current.splice(index, 1);
    inputRefs.current.splice(index, 1);
    onChange(value.filter((_, i) => i !== index));
  };

  const updateField = (
    index: number,
    field: keyof OpportunityLocationInput,
    raw: string
  ) => {
    if (disabled) return;
    const rows = [...value];
    if (field === 'locality_name') {
      rows[index] = { ...rows[index], locality_name: raw };
    } else if (field === 'radius_km') {
      rows[index] = { ...rows[index], radius_km: parseInt(raw, 10) || 10 };
    } else if (field === 'latitude') {
      rows[index] = { ...rows[index], latitude: raw === '' ? null : parseFloat(raw) };
    } else if (field === 'longitude') {
      rows[index] = { ...rows[index], longitude: raw === '' ? null : parseFloat(raw) };
    }
    onChange(rows);
  };

  const addPreset = (preset: { locality_name: string }) => {
    if (disabled) return;
    // Don't add duplicates
    if (value.some((v) => v.locality_name === preset.locality_name)) return;
    onChange([
      ...value,
      {
        locality_name: preset.locality_name,
        latitude: null,
        longitude: null,
        radius_km: 10,
      },
    ]);
  };

  // ── Render ─────────────────────────────────────────────────
  return (
    <div className="space-y-3">
      {/* Preset city chips */}
      <div className="flex flex-wrap gap-2">
        {PRESET_CITIES.map((city) => {
          const isAdded = value.some((v) => v.locality_name === city.locality_name);
          return (
            <button
              key={city.label}
              type="button"
              disabled={disabled || isAdded}
              onClick={() => addPreset(city)}
              className={`px-3 py-1 text-xs font-medium rounded-full border transition-all ${
                isAdded
                  ? 'bg-[#291BB0]/10 text-[#291BB0] border-[#291BB0]/30 dark:bg-indigo-500/20 dark:text-indigo-300 dark:border-indigo-400/30 cursor-default'
                  : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-[#291BB0] hover:text-[#291BB0] dark:hover:text-indigo-300'
              } disabled:opacity-50`}
            >
              {isAdded ? '✓ ' : '+ '}
              {city.label}
            </button>
          );
        })}
      </div>

      {hasMapsKey && mapsError && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Google Maps autocomplete unavailable — using manual entry.
        </p>
      )}

      {/* Rows */}
      <div className="space-y-3">
        {value.map((loc, index) => (
          <div
            key={index}
            className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 space-y-2"
          >
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-[#291BB0] dark:text-indigo-400 flex-shrink-0" />
              <div className="flex-1 relative">
                <input
                  ref={(el) => {
                    inputRefs.current[index] = el;
                    if (el && mapsReady) attachAutocomplete(index);
                  }}
                  type="text"
                  placeholder="Locality / Area name"
                  value={loc.locality_name}
                  disabled={disabled}
                  onChange={(e) => updateField(index, 'locality_name', e.target.value)}
                  className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#291BB0]/40 focus:border-[#291BB0] dark:focus:border-indigo-400 disabled:opacity-50"
                />
              </div>
              {!disabled && (
                <button
                  type="button"
                  onClick={() => removeRow(index)}
                  className="p-1 text-gray-400 hover:text-[#F04B42] transition-colors"
                  title="Remove"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Optional lat/lng + radius */}
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                  Latitude (opt.)
                </label>
                <input
                  type="number"
                  step="any"
                  placeholder="e.g. 27.56"
                  value={loc.latitude ?? ''}
                  disabled={disabled}
                  onChange={(e) => updateField(index, 'latitude', e.target.value)}
                  className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-[#291BB0]/40 disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                  Longitude (opt.)
                </label>
                <input
                  type="number"
                  step="any"
                  placeholder="e.g. 76.60"
                  value={loc.longitude ?? ''}
                  disabled={disabled}
                  onChange={(e) => updateField(index, 'longitude', e.target.value)}
                  className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-[#291BB0]/40 disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                  Radius (km)
                </label>
                <input
                  type="number"
                  min={1}
                  max={200}
                  value={loc.radius_km}
                  disabled={disabled}
                  onChange={(e) => updateField(index, 'radius_km', e.target.value)}
                  className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-[#291BB0]/40 disabled:opacity-50"
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add row button */}
      {!disabled && (
        <button
          type="button"
          onClick={addRow}
          className="flex items-center gap-1.5 text-sm text-[#291BB0] dark:text-indigo-400 hover:underline"
        >
          <Plus className="h-4 w-4" />
          Add Locality
        </button>
      )}
    </div>
  );
};

export default LocalityMultiPicker;
