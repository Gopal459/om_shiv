import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowLeft,
  Upload,
  Check,
  AlertCircle,
  HelpCircle,
  MapPin,
  Camera,
  Trash2,
  Eye,
  CheckCircle2,
  Droplets,
  Zap,
  BatteryCharging,
  Layers,
  Trees,
  Car,
  ShieldCheck,
  Building,
  Waves,
  Dumbbell,
  PhoneCall,
  Save,
  Compass,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface PropertyFormProps {
  propertyId?: number | null;
  initialType?: number; // 1=Rent, 2=Sale, 3=PG
  onBack: () => void;
  onSuccess: (savedProperty: any) => void;
}

// Convert numbers to Indian Rupees in words (Lakhs, Crores)
function numberToIndianWords(num: number): string {
  if (!num || isNaN(num) || num <= 0) return 'Zero Rupees Only';
  const a = [
    '', 'One ', 'Two ', 'Three ', 'Four ', 'Five ', 'Six ', 'Seven ', 'Eight ', 'Nine ',
    'Ten ', 'Eleven ', 'Twelve ', 'Thirteen ', 'Fourteen ', 'Fifteen ', 'Sixteen ',
    'Seventeen ', 'Eighteen ', 'Nineteen ',
  ];
  const b = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];

  function inWords(n: number): string {
    let str = '';
    if (n > 19) {
      str += b[Math.floor(n / 10)] + (n % 10 !== 0 ? ' ' + a[n % 10] : ' ');
    } else {
      str += a[n];
    }
    return str;
  }

  let words = '';
  const crore = Math.floor(num / 10000000);
  num %= 10000000;
  const lakh = Math.floor(num / 100000);
  num %= 100000;
  const thousand = Math.floor(num / 1000);
  num %= 1000;
  const hundred = Math.floor(num / 100);
  num %= 100;

  if (crore > 0) words += inWords(crore) + 'Crore ';
  if (lakh > 0) words += inWords(lakh) + 'Lakh ';
  if (thousand > 0) words += inWords(thousand) + 'Thousand ';
  if (hundred > 0) words += inWords(hundred) + 'Hundred ';
  if (num > 0) words += inWords(num);

  return words.trim() + ' Rupees Only';
}

export const PropertyForm: React.FC<PropertyFormProps> = ({
  propertyId,
  initialType = 2,
  onBack,
  onSuccess,
}) => {
  const { isDark } = useTheme();

  // Form State
  const [propertyType, setPropertyType] = useState<number>(initialType); // 1=Rent, 2=Sale, 3=PG
  const [lookingType, setLookingType] = useState<number>(1); // 1=Res, 2=Comm, 3=Agri, 4=Ind
  const [subcatType, setSubcatType] = useState<number>(1); // 1=Flat, 2=House, 3=Plot, 4=Commercial, etc.

  // User Info
  const [ownerName, setOwnerName] = useState('');
  const [ownerEmail, setOwnerEmail] = useState('');
  const [ownerMobile, setOwnerMobile] = useState('');
  const [sourceType, setSourceType] = useState<number>(2); // 1=Broker, 2=Owner, 3=Builder

  // Location
  const [postedDate, setPostedDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [expireDate, setExpireDate] = useState(() => {
    const d = new Date();
    d.setMonth(d.getMonth() + 3);
    return d.toISOString().split('T')[0];
  });
  const [stateName, setStateName] = useState('Rajasthan');
  const [cityName, setCityName] = useState('Alwar');
  const [locationText, setLocationText] = useState('');
  const [sublocality, setSublocality] = useState('');
  const [nearbyArea, setNearbyArea] = useState('');
  const [pincode, setPincode] = useState('301001');
  const [lat, setLat] = useState('27.5530');
  const [long, setLong] = useState('76.6346');

  // Property Details
  const [unitStreet, setUnitStreet] = useState('');
  const [area, setArea] = useState('1000');
  const [areaUnit, setAreaUnit] = useState('Sq.Ft');
  const [boundary, setBoundary] = useState(false);
  const [noofBhk, setNoofBhk] = useState(2);
  const [superArea, setSuperArea] = useState('1200');
  const [carpetArea, setCarpetArea] = useState('950');
  const [constructedFloors, setConstructedFloors] = useState(1);
  const [whichFloor, setWhichFloor] = useState('2');
  const [totalFloors, setTotalFloors] = useState(4);
  const [bathrooms, setBathrooms] = useState(2);
  const [balconies, setBalconies] = useState(1);
  const [projectName, setProjectName] = useState('');
  const [transactionType, setTransactionType] = useState(1); // 1=Resale, 2=New
  const [propertyOwnership, setPropertyOwnership] = useState(2); // 1=Leasehold, 2=Freehold
  const [possessionStatus, setPossessionStatus] = useState(1); // 1=Ready, 2=Under construction
  const [constructionAge, setConstructionAge] = useState('0-1 Year');

  // Rent Specific
  const [rentalAllowFor, setRentalAllowFor] = useState('Family');
  const [whichPartToRent, setWhichPartToRent] = useState(1); // 1=Complete, 2=Part
  const [floorToRent, setFloorToRent] = useState(0); // -1=Basement, 0=Ground, 1=1st, etc.

  // PG Specific
  const [pgName, setPgName] = useState('');
  const [pgCategory, setPgCategory] = useState(1); // 1=Professionals, 2=Students, 3=Both
  const [pgGender, setPgGender] = useState(1); // 1=Boys, 2=Girls, 3=Both
  const [pgRoomType, setPgRoomType] = useState(1); // 1=Private, 2=Sharing, 3=Both
  const [pgFoodOption, setPgFoodOption] = useState(2); // 1=With Food, 2=Without Food
  const [pgFoodType, setPgFoodType] = useState(1); // 1=Veg, 2=Non-Veg, 3=Both
  const [pgMeals, setPgMeals] = useState<string[]>(['Breakfast', 'Dinner']);
  const [pgSmoking, setPgSmoking] = useState(false);
  const [pgAlcohol, setPgAlcohol] = useState(false);

  // Price
  const [priceFormat, setPriceFormat] = useState('Total Price');
  const [pricePerUnit, setPricePerUnit] = useState('0');
  const [expectedPrice, setExpectedPrice] = useState<string>('4500000');
  const [priceNegotiable, setPriceNegotiable] = useState(true);
  const [extraCharge, setExtraCharge] = useState(false);

  // Features
  const [roadWidth, setRoadWidth] = useState('40');
  const [facing, setFacing] = useState(1); // 1=East, 2=West, 3=North, 4=South
  const [isCorner, setIsCorner] = useState(false);
  const [features, setFeatures] = useState({
    waterSupply: true,
    electricity: true,
    powerBackup: true,
    lift: false,
    park: true,
    ownParking: true,
    visitParking: false,
    intercom: false,
    clubHouse: false,
    swimming: false,
    fitness: false,
    gatedCommunity: true,
    security: true,
  });

  // Uploads
  const [description, setDescription] = useState('');
  const [images, setImages] = useState<string[]>([]);
  const [newImageUrl, setNewImageUrl] = useState('');

  // UI status
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Computed Amount In Words
  const amountInWords = useMemo(() => {
    const val = parseFloat(expectedPrice) || 0;
    return numberToIndianWords(val);
  }, [expectedPrice]);

  // Load existing property if in Edit mode
  useEffect(() => {
    if (!propertyId) return;

    const fetchProperty = async () => {
      setFetching(true);
      setError('');
      try {
        const token = localStorage.getItem('access_token');
        const res = await fetch(`/v1/properties/tbl/${propertyId}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error('Failed to load property details');
        const data = await res.json();

        setPropertyType(data.property_type || 2);
        setLookingType(data.looking_type || 1);
        setSubcatType(data.looking_subcat_type || 1);
        setOwnerName(data.source_owner_name || '');
        setOwnerEmail(data.source_owner_email || '');
        setOwnerMobile(data.source_owner_mobile || '');
        setSourceType(data.source_type || 2);
        setSublocality(data.sublocality_address || '');
        setLocationText(data.location || '');
        setNearbyArea(data.nearby_area || '');
        setPincode(data.pincode || '301001');
        setLat(data.location_lat || '27.5530');
        setLong(data.location_long || '76.6346');
        setUnitStreet(data.street_no || '');
        setArea(data.area || '1000');
        setExpectedPrice(String(data.expected_price || 0));
        setPriceNegotiable(data.price_negociable === 1);
        setExtraCharge(data.extra_charge_apply === 1);
        setTransactionType(data.transaction_type || 1);
        setPropertyOwnership(data.property_ownership || 2);
        setPossessionStatus(data.possession_status || 1);
        setConstructionAge(data.construction_age || '0-1 Year');
        setSuperArea(data.super_area || '1200');
        setCarpetArea(data.carpet_area || '950');
        setNoofBhk(data.noof_bhk || 2);
        setProjectName(data.project_name || '');
        setRoadWidth(data.width_facing_road || '40');
        setFacing(data.facing || 1);
        setIsCorner(data.corner === 1);
        setBoundary(data.boundary === 1);
        setRentalAllowFor(data.rentalallow_forid || 'Family');
        setWhichPartToRent(data.whichpart_torent || 1);
        setFloorToRent(data.floor_torent || 0);
        setDescription(data.description || '');

        if (data.images) {
          try {
            const parsed = JSON.parse(data.images);
            if (Array.isArray(parsed)) setImages(parsed);
          } catch {
            setImages([data.images]);
          }
        }

        // PG details
        if (data.pg_details) {
          setPgName(data.pg_details.pg_name || '');
          setPgCategory(data.pg_details.available_category || 1);
          setPgGender(data.pg_details.gender || 1);
          setPgRoomType(data.pg_details.room_type || 1);
          setPgFoodOption(data.pg_details.food_option || 2);
          setPgFoodType(data.pg_details.food_type || 1);
          if (data.pg_details.meal_type) {
            setPgMeals(data.pg_details.meal_type.split(',').map((s: string) => s.trim()));
          }
        }

        // Features
        setFeatures({
          waterSupply: data.feature_watersupply === 1,
          electricity: data.feature_electricityconnection === 1,
          powerBackup: data.featurepowerbackup === 1,
          lift: data.feature_lift === 1,
          park: data.feature_park === 1,
          ownParking: data.feature_ownparking === 1,
          visitParking: data.feature_visitparking === 1,
          intercom: data.feature_intercomfac === 1,
          clubHouse: data.feature_clubhosue === 1,
          swimming: data.feature_swimming === 1,
          fitness: data.feature_fitness === 1,
          gatedCommunity: data.feature_gatedcomm === 1,
          security: data.feature_security === 1,
        });
      } catch (err: any) {
        setError(err.message || 'Error loading property');
      } finally {
        setFetching(false);
      }
    };

    fetchProperty();
  }, [propertyId]);

  // Handle Add Image URL simulation / upload
  const handleAddImage = () => {
    if (!newImageUrl.trim()) return;
    if (images.length >= 10) {
      setError('Maximum 10 photos allowed.');
      return;
    }
    setImages((prev) => [...prev, newImageUrl.trim()]);
    setNewImageUrl('');
    setError('');
  };

  const handleRemoveImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleToggleMeal = (meal: string) => {
    setPgMeals((prev) =>
      prev.includes(meal) ? prev.filter((m) => m !== meal) : [...prev, meal]
    );
  };

  // Form Submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Client-side validations
    if (!ownerName.trim()) {
      setError('Owner Name is required.');
      return;
    }
    if (!ownerMobile.trim() || ownerMobile.length < 10) {
      setError('Valid 10-digit Owner Mobile is required.');
      return;
    }
    const priceNum = parseFloat(expectedPrice);
    if (isNaN(priceNum) || priceNum <= 0) {
      setError('Expected Price must be greater than 0.');
      return;
    }

    // Sale specific rule: Carpet < Super Area
    if (propertyType === 2) {
      const c = parseFloat(carpetArea) || 0;
      const s = parseFloat(superArea) || 0;
      if (c > 0 && s > 0 && c >= s) {
        setError('Carpet area must be strictly less than super area.');
        return;
      }
      if (!transactionType) {
        setError('Transaction Type is required for Sale property.');
        return;
      }
    }

    // Rent specific rule: Partial rent requires floor
    if (propertyType === 1 && whichPartToRent === 2 && floorToRent === 0) {
      setError('Floor to rent is mandatory when renting some part of property.');
      return;
    }

    // PG specific rule: Food option requires meal type
    if (propertyType === 3 && pgFoodOption === 1 && pgMeals.length === 0) {
      setError('Please select at least one meal type (Breakfast/Lunch/Dinner) when food option is enabled.');
      return;
    }

    setLoading(true);

    const payload: any = {
      property_type: propertyType,
      looking_type: lookingType,
      looking_subcat_type: subcatType,
      source_type: sourceType,
      source_owner_name: ownerName.trim(),
      source_owner_email: ownerEmail.trim() || null,
      source_owner_mobile: ownerMobile.trim(),
      state_id: 1,
      city_id: 1,
      sublocality_address: sublocality.trim() || unitStreet.trim() || 'Alwar',
      location: locationText.trim() || 'Alwar Bypass',
      nearby_area: nearbyArea.trim() || null,
      pincode: pincode.trim() || '301001',
      street_no: unitStreet.trim() || null,
      location_lat: lat,
      location_long: long,
      expected_price: priceNum,
      priceper_unitvalue: parseFloat(pricePerUnit) || 0,
      price_negociable: priceNegotiable ? 1 : 0,
      extra_charge_apply: extraCharge ? 1 : 0,
      transaction_type: propertyType === 2 ? transactionType : 0,
      property_ownership: propertyOwnership,
      possession_status: possessionStatus,
      construction_age: constructionAge,
      super_area: superArea,
      carpet_area: carpetArea,
      noof_bhk: noofBhk,
      constructed_floors: constructedFloors,
      noof_floors: totalFloors,
      property_which_floors: whichFloor,
      project_name: projectName.trim() || null,
      rentalallow_forid: rentalAllowFor,
      whichpart_torent: whichPartToRent,
      floor_torent: floorToRent,
      boundary: boundary ? 1 : 0,
      width_facing_road: roadWidth,
      facing: facing,
      corner: isCorner ? 1 : 0,
      feature_watersupply: features.waterSupply ? 1 : 0,
      feature_electricityconnection: features.electricity ? 1 : 0,
      featurepowerbackup: features.powerBackup ? 1 : 0,
      feature_lift: features.lift ? 1 : 0,
      feature_park: features.park ? 1 : 0,
      feature_ownparking: features.ownParking ? 1 : 0,
      feature_visitparking: features.visitParking ? 1 : 0,
      feature_intercomfac: features.intercom ? 1 : 0,
      feature_clubhosue: features.clubHouse ? 1 : 0,
      feature_swimming: features.swimming ? 1 : 0,
      feature_fitness: features.fitness ? 1 : 0,
      feature_gatedcomm: features.gatedCommunity ? 1 : 0,
      feature_security: features.security ? 1 : 0,
      description: description.trim() || null,
      images: images.length > 0 ? JSON.stringify(images) : null,
    };

    if (propertyType === 3) {
      payload.pg_details = {
        pg_name: pgName.trim() || 'PG Accommodation',
        available_category: pgCategory,
        gender: pgGender,
        room_type: pgRoomType,
        food_option: pgFoodOption,
        food_type: pgFoodType,
        meal_type: pgMeals.join(', '),
        smoking: pgSmoking ? 1 : 0,
        alcohol: pgAlcohol ? 1 : 0,
      };
    }

    try {
      const token = localStorage.getItem('access_token');
      const url = propertyId ? `/v1/properties/tbl/${propertyId}` : '/v1/properties/create';
      const method = propertyId ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to save property listing');
      }

      setSuccess(`Property ${data.propertyid_no || 'listing'} successfully saved!`);
      setTimeout(() => {
        onSuccess(data);
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'An error occurred during submission.');
    } finally {
      setLoading(false);
    }
  };

  if (fetching) {
    return (
      <div className="p-12 text-center">
        <div className="animate-spin w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full mx-auto mb-4"></div>
        <p className="text-slate-500 dark:text-slate-400">Loading property dossier...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Top Header & Property Type Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white">
              {propertyId ? 'Edit Property Listing' : 'Add New Property Listing'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
              Complete 124-attribute property registration with dynamic validation rules.
            </p>
          </div>
        </div>

        {/* Property Type Pill Selector */}
        <div className="flex items-center bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
          <button
            type="button"
            onClick={() => setPropertyType(2)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              propertyType === 2
                ? 'bg-rose-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            Sell / Buy
          </button>
          <button
            type="button"
            onClick={() => setPropertyType(1)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              propertyType === 1
                ? 'bg-rose-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            Rent Property
          </button>
          <button
            type="button"
            onClick={() => setPropertyType(3)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              propertyType === 3
                ? 'bg-rose-500 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            PG (Paying Guest)
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 flex items-center gap-3 text-red-700 dark:text-red-400 text-sm animate-shake">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/60 flex items-center gap-3 text-emerald-700 dark:text-emerald-400 text-sm">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* CARD 1: USER INFO */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-slate-100 dark:border-slate-800">
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-red-600 text-white text-sm font-bold shadow-xs">
              User Info
              <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center text-[10px]">&gt;</span>
            </span>
          </div>
          <div className="p-5 sm:p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Owner / Contact Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
                placeholder="e.g. Ramesh Kumar"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Owner Email
              </label>
              <input
                type="email"
                value={ownerEmail}
                onChange={(e) => setOwnerEmail(e.target.value)}
                placeholder="e.g. ramesh@example.com"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Owner Mobile <span className="text-red-500">*</span>
              </label>
              <input
                type="tel"
                required
                value={ownerMobile}
                onChange={(e) => setOwnerMobile(e.target.value)}
                placeholder="e.g. 9876543210"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>
          </div>
        </div>

        {/* CARD 2: LOCATION */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-slate-100 dark:border-slate-800">
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-red-600 text-white text-sm font-bold shadow-xs">
              Location
              <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center text-[10px]">&gt;</span>
            </span>
          </div>
          <div className="p-5 sm:p-6 grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Posted Date
              </label>
              <input
                type="date"
                value={postedDate}
                onChange={(e) => setPostedDate(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Expire Date
              </label>
              <input
                type="date"
                value={expireDate}
                onChange={(e) => setExpireDate(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                State
              </label>
              <select
                value={stateName}
                onChange={(e) => setStateName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                <option value="Rajasthan">Rajasthan</option>
                <option value="Haryana">Haryana</option>
                <option value="Delhi">Delhi NCR</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                City
              </label>
              <select
                value={cityName}
                onChange={(e) => setCityName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                <option value="Alwar">Alwar</option>
                <option value="Bhiwadi">Bhiwadi</option>
                <option value="Neemrana">Neemrana</option>
                <option value="Jaipur">Jaipur</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                  Location Address
                </label>
                <span className="text-xs font-bold text-red-500 flex items-center gap-1 cursor-pointer hover:underline">
                  <MapPin className="w-3 h-3" /> Show Map ({lat}, {long})
                </span>
              </div>
              <input
                type="text"
                value={locationText}
                onChange={(e) => setLocationText(e.target.value)}
                placeholder="e.g. Tijara Road, Bhagwanpura, Alwar, Rajasthan"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Near By Area (Optional)
              </label>
              <input
                type="text"
                value={nearbyArea}
                onChange={(e) => setNearbyArea(e.target.value)}
                placeholder="e.g. Near Cross Point Mall"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>
          </div>
        </div>

        {/* CARD 3: PROPERTY DETAIL */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-slate-100 dark:border-slate-800">
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-red-600 text-white text-sm font-bold shadow-xs">
              Property Detail
              <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center text-[10px]">&gt;</span>
            </span>
          </div>
          <div className="p-5 sm:p-6 grid grid-cols-1 md:grid-cols-4 gap-6">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Property Category <span className="text-red-500">*</span>
              </label>
              <select
                value={lookingType}
                onChange={(e) => setLookingType(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                <option value={1}>Residential</option>
                <option value={2}>Commercial</option>
                <option value={3}>Agriculture / Land</option>
                <option value={4}>Industrial</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Sub-Category <span className="text-red-500">*</span>
              </label>
              <select
                value={subcatType}
                onChange={(e) => setSubcatType(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                {lookingType === 1 && (
                  <>
                    <option value={1}>Flat / Apartment</option>
                    <option value={2}>Independent House / Villa</option>
                    <option value={3}>Residential Plot</option>
                    <option value={4}>Builder Floor</option>
                  </>
                )}
                {lookingType === 2 && (
                  <>
                    <option value={5}>Commercial Office</option>
                    <option value={6}>Commercial Shop</option>
                    <option value={7}>Commercial Plot</option>
                  </>
                )}
                {lookingType === 3 && (
                  <>
                    <option value={8}>Agricultural Land</option>
                    <option value={9}>Farmhouse Land</option>
                  </>
                )}
                {lookingType === 4 && (
                  <>
                    <option value={10}>Industrial Shed / Factory</option>
                    <option value={11}>Industrial Plot</option>
                  </>
                )}
              </select>
            </div>

            <div>
              <div className="flex items-center gap-1.5 mb-1.5">
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                  Unit No. / Street Name <span className="text-red-500">*</span>
                </label>
                <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
              </div>
              <input
                type="text"
                required
                value={unitStreet}
                onChange={(e) => setUnitStreet(e.target.value)}
                placeholder="e.g. Tijara Road, Flat 302"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Area & Unit <span className="text-red-500">*</span>
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={area}
                  onChange={(e) => setArea(e.target.value)}
                  className="w-2/3 px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                />
                <select
                  value={areaUnit}
                  onChange={(e) => setAreaUnit(e.target.value)}
                  className="w-1/3 px-2 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-rose-500"
                >
                  <option value="Sq.Ft">Sq.Ft</option>
                  <option value="Sq.Yd">Sq.Yd</option>
                  <option value="Ares">Ares</option>
                  <option value="Bigha">Bigha</option>
                  <option value="Acre">Acre</option>
                </select>
              </div>
            </div>

            {/* Boundary Switch */}
            <div className="flex items-center justify-between p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800">
              <div>
                <span className="text-xs font-bold text-slate-900 dark:text-white block">Boundary Wall</span>
                <span className="text-[11px] text-slate-400">{boundary ? 'Constructed' : 'Open'}</span>
              </div>
              <button
                type="button"
                onClick={() => setBoundary(!boundary)}
                className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ${
                  boundary ? 'bg-red-500 justify-end' : 'bg-slate-300 dark:bg-slate-600 justify-start'
                }`}
              >
                <span className="w-4 h-4 rounded-full bg-white shadow-md"></span>
              </button>
            </div>

            {/* Source Type */}
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Source Type <span className="text-red-500">*</span>
              </label>
              <select
                value={sourceType}
                onChange={(e) => setSourceType(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                <option value={2}>Direct Owner</option>
                <option value={1}>Certified Agent / Broker</option>
                <option value={3}>Builder / Developer</option>
              </select>
            </div>

            {/* CONDITIONAL: SALE SPECIFIC FIELDS */}
            {propertyType === 2 && (
              <>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Transaction Type <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={transactionType}
                    onChange={(e) => setTransactionType(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  >
                    <option value={1}>Resale Property</option>
                    <option value={2}>New Booking / Developer</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Possession Status <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={possessionStatus}
                    onChange={(e) => setPossessionStatus(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  >
                    <option value={1}>Ready Possession</option>
                    <option value={2}>Under Construction</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Super Area (Sq.Ft)
                  </label>
                  <input
                    type="number"
                    value={superArea}
                    onChange={(e) => setSuperArea(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Carpet Area (Sq.Ft) <span className="text-red-500 text-[10px] font-normal">&lt; Super Area</span>
                  </label>
                  <input
                    type="number"
                    value={carpetArea}
                    onChange={(e) => setCarpetArea(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  />
                </div>
              </>
            )}

            {/* CONDITIONAL: RENT SPECIFIC FIELDS */}
            {propertyType === 1 && (
              <>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Rental Allowed For <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={rentalAllowFor}
                    onChange={(e) => setRentalAllowFor(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  >
                    <option value="Family">Family Only</option>
                    <option value="Bachelors">Bachelors (Boys/Girls)</option>
                    <option value="Company">Company Lease</option>
                    <option value="Any">Any / No Restriction</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Which Part to Rent <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={whichPartToRent}
                    onChange={(e) => setWhichPartToRent(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  >
                    <option value={1}>Complete Property</option>
                    <option value={2}>Some Part of Property</option>
                  </select>
                </div>
                {whichPartToRent === 2 && (
                  <div>
                    <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                      Floor to Rent <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={floorToRent}
                      onChange={(e) => setFloorToRent(Number(e.target.value))}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                    >
                      <option value={0}>Ground Floor</option>
                      <option value={1}>1st Floor</option>
                      <option value={2}>2nd Floor</option>
                      <option value={-1}>Basement</option>
                    </select>
                  </div>
                )}
              </>
            )}

            {/* CONDITIONAL: PG SPECIFIC FIELDS */}
            {propertyType === 3 && (
              <>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    PG Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={pgName}
                    onChange={(e) => setPgName(e.target.value)}
                    placeholder="e.g. Om Shiv PG"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Available For
                  </label>
                  <select
                    value={pgGender}
                    onChange={(e) => setPgGender(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  >
                    <option value={1}>Boys</option>
                    <option value={2}>Girls</option>
                    <option value={3}>Both / Unisex</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Room Type
                  </label>
                  <select
                    value={pgRoomType}
                    onChange={(e) => setPgRoomType(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  >
                    <option value={1}>Private Room</option>
                    <option value={2}>Sharing (2-3 Beds)</option>
                    <option value={3}>Both Available</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Food Option
                  </label>
                  <select
                    value={pgFoodOption}
                    onChange={(e) => setPgFoodOption(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  >
                    <option value={1}>With Food Included</option>
                    <option value={2}>Without Food</option>
                  </select>
                </div>
                {pgFoodOption === 1 && (
                  <div className="md:col-span-2 flex items-center gap-4 p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                    <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Meals:</span>
                    {['Breakfast', 'Lunch', 'Dinner'].map((meal) => (
                      <label key={meal} className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={pgMeals.includes(meal)}
                          onChange={() => handleToggleMeal(meal)}
                          className="rounded text-rose-500 focus:ring-rose-400"
                        />
                        {meal}
                      </label>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Flat or House Specifics */}
            {(subcatType === 1 || subcatType === 2) && (
              <>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Project / Society Name
                  </label>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="e.g. Royal Residency"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    No. of BHK
                  </label>
                  <select
                    value={noofBhk}
                    onChange={(e) => setNoofBhk(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  >
                    <option value={1}>1 BHK</option>
                    <option value={2}>2 BHK</option>
                    <option value={3}>3 BHK</option>
                    <option value={4}>4 BHK</option>
                    <option value={5}>5+ BHK</option>
                  </select>
                </div>
              </>
            )}
          </div>
        </div>

        {/* CARD 4: PRICE */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-slate-100 dark:border-slate-800">
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-red-600 text-white text-sm font-bold shadow-xs">
              Price
              <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center text-[10px]">&gt;</span>
            </span>
          </div>
          <div className="p-5 sm:p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                  Select Price Format <span className="text-red-500">*</span>
                </label>
                <select
                  value={priceFormat}
                  onChange={(e) => setPriceFormat(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                >
                  <option value="Total Price">Total Expected Price</option>
                  <option value="Ares">Per Ares</option>
                  <option value="Sq.Ft">Per Sq.Ft</option>
                  <option value="Sq.Yd">Per Sq.Yd</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                  Enter Price According Select Area Unit
                </label>
                <input
                  type="number"
                  value={pricePerUnit}
                  onChange={(e) => setPricePerUnit(e.target.value)}
                  placeholder="e.g. 45000"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                  Expected Price (₹) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  value={expectedPrice}
                  onChange={(e) => setExpectedPrice(e.target.value)}
                  placeholder="e.g. 4500000"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm font-bold text-rose-600 dark:text-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-500"
                />
              </div>
            </div>

            {/* Dynamic Amount in Words Display (Screenshot 9) */}
            <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-center gap-2">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400">Amount In Words :</span>
              <span className="text-xs font-extrabold text-slate-900 dark:text-white tracking-wide">
                {amountInWords}
              </span>
            </div>

            {/* Price Toggles */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
              <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800">
                <div>
                  <span className="text-xs font-bold text-slate-900 dark:text-white block">Price Should Be</span>
                  <span className="text-[11px] text-slate-400">
                    {priceNegotiable ? 'Negotiable' : 'Fixed'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setPriceNegotiable(!priceNegotiable)}
                  className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ${
                    priceNegotiable ? 'bg-red-500 justify-end' : 'bg-slate-300 dark:bg-slate-600 justify-start'
                  }`}
                >
                  <span className="w-4 h-4 rounded-full bg-white shadow-md"></span>
                </button>
              </div>

              <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800">
                <div>
                  <span className="text-xs font-bold text-slate-900 dark:text-white block">Extra Charge</span>
                  <span className="text-[11px] text-slate-400">
                    {extraCharge ? 'Apply' : 'Not Apply'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setExtraCharge(!extraCharge)}
                  className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ${
                    extraCharge ? 'bg-red-500 justify-end' : 'bg-slate-300 dark:bg-slate-600 justify-start'
                  }`}
                >
                  <span className="w-4 h-4 rounded-full bg-white shadow-md"></span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* CARD 5: FEATURES */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-slate-100 dark:border-slate-800">
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-red-600 text-white text-sm font-bold shadow-xs">
              Features
              <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center text-[10px]">&gt;</span>
            </span>
          </div>
          <div className="p-5 sm:p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                  Width Of Facing Road <span className="text-red-500">*</span>
                </label>
                <div className="flex">
                  <input
                    type="number"
                    value={roadWidth}
                    onChange={(e) => setRoadWidth(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-l-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                  />
                  <span className="px-4 py-2.5 rounded-r-xl border border-l-0 border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-xs font-bold text-slate-500 flex items-center">
                    Foot
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                  Facing <span className="text-red-500">*</span>
                </label>
                <select
                  value={facing}
                  onChange={(e) => setFacing(Number(e.target.value))}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                >
                  <option value={1}>East</option>
                  <option value={2}>West</option>
                  <option value={3}>North</option>
                  <option value={4}>South</option>
                  <option value={5}>North-East</option>
                  <option value={6}>North-West</option>
                  <option value={7}>South-East</option>
                  <option value={8}>South-West</option>
                </select>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800">
                <div>
                  <span className="text-xs font-bold text-slate-900 dark:text-white block">Feature: Corner Plot</span>
                  <span className="text-[11px] text-slate-400">{isCorner ? 'Corner Property' : 'Normal'}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setIsCorner(!isCorner)}
                  className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ${
                    isCorner ? 'bg-red-500 justify-end' : 'bg-slate-300 dark:bg-slate-600 justify-start'
                  }`}
                >
                  <span className="w-4 h-4 rounded-full bg-white shadow-md"></span>
                </button>
              </div>
            </div>

            {/* Common Features Grid Matching Screenshot 9 */}
            <div>
              <h4 className="text-center font-bold text-sm text-slate-900 dark:text-white mb-6">
                Common Features
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {[
                  { key: 'waterSupply', label: 'Water Supply', icon: Droplets },
                  { key: 'electricity', label: 'Electricity Connection', icon: Zap },
                  { key: 'powerBackup', label: 'Power Backup', icon: BatteryCharging },
                  { key: 'lift', label: 'Lift', icon: Layers },
                  { key: 'park', label: 'Park', icon: Trees },
                  { key: 'ownParking', label: 'Own Parking', icon: Car },
                  { key: 'visitParking', label: 'Visitor Parking', icon: Car },
                  { key: 'intercom', label: 'Intercom Facility', icon: PhoneCall },
                  { key: 'clubHouse', label: 'Club House', icon: Building },
                  { key: 'swimming', label: 'Swimming Pool', icon: Waves },
                  { key: 'fitness', label: 'Fitness Center / Gym', icon: Dumbbell },
                  { key: 'security', label: 'Security & CCTV', icon: ShieldCheck },
                ].map((item) => {
                  const Icon = item.icon;
                  const active = (features as any)[item.key];
                  return (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() =>
                        setFeatures((prev) => ({
                          ...prev,
                          [item.key]: !active,
                        }))
                      }
                      className={`p-4 rounded-2xl border flex flex-col items-center justify-center text-center gap-2.5 transition-all ${
                        active
                          ? 'border-rose-500/50 bg-rose-50/50 dark:bg-rose-950/20 shadow-xs'
                          : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 opacity-60 hover:opacity-100'
                      }`}
                    >
                      <div className="relative">
                        <div
                          className={`w-12 h-12 rounded-full flex items-center justify-center ${
                            active
                              ? 'bg-rose-100 dark:bg-rose-900/60 text-rose-600 dark:text-rose-400'
                              : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                          }`}
                        >
                          <Icon className="w-6 h-6" />
                        </div>
                        {active && (
                          <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-600 text-white flex items-center justify-center text-[10px]">
                            <Check className="w-3 h-3 stroke-[3]" />
                          </span>
                        )}
                      </div>
                      <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 line-clamp-2">
                        {item.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* CARD 6: UPLOADS & MEDIA */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-slate-100 dark:border-slate-800">
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-red-600 text-white text-sm font-bold shadow-xs">
              Uploads
              <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center text-[10px]">&gt;</span>
            </span>
          </div>
          <div className="p-5 sm:p-6 space-y-6">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                Description
              </label>
              <textarea
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Enter detailed description of property, highlights, neighborhood..."
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>

            {/* Photos Upload Specs (Screenshot 10) */}
            <div className="p-6 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/40 text-center space-y-4">
              <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">Photos</h4>

              <div className="inline-block text-left text-xs space-y-1.5 text-slate-600 dark:text-slate-400">
                <p className="flex items-center gap-1.5 text-red-600 dark:text-red-400 font-medium">
                  <span className="font-bold">*</span> Maximum 10 Photos Can Be Upload.
                </p>
                <p className="flex items-center gap-1.5 text-red-600 dark:text-red-400 font-medium">
                  <span className="font-bold">*</span> Minimum Image Size To Be 10KB.
                </p>
                <p className="flex items-center gap-1.5 text-red-600 dark:text-red-400 font-medium">
                  <span className="font-bold">*</span> Maximum Size To Be 2 MB.
                </p>
                <p className="flex items-center gap-1.5 text-red-600 dark:text-red-400 font-medium">
                  <span className="font-bold">*</span> Accepted File Formats Are Png, Jpg, Jpeg.
                </p>
                <p className="flex items-center gap-1.5 text-red-600 dark:text-red-400 font-medium">
                  <span className="font-bold">*</span> Dimension 600 X 400
                </p>
              </div>

              {/* Add Image URL or File */}
              <div className="max-w-md mx-auto flex gap-2 pt-2">
                <input
                  type="text"
                  value={newImageUrl}
                  onChange={(e) => setNewImageUrl(e.target.value)}
                  placeholder="Paste Image URL (e.g. /uploads/property.jpg)"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs focus:outline-none focus:ring-2 focus:ring-rose-500"
                />
                <button
                  type="button"
                  onClick={handleAddImage}
                  className="px-4 py-2 rounded-xl bg-white dark:bg-slate-900 border border-red-500 text-red-600 dark:text-red-400 font-bold text-xs flex items-center gap-1.5 hover:bg-red-50 dark:hover:bg-red-950/30 transition-all flex-shrink-0"
                >
                  <Camera className="w-4 h-4" />
                  Upload Photos
                </button>
              </div>

              {/* Image Preview Gallery */}
              {images.length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-3 pt-4">
                  {images.map((img, idx) => (
                    <div
                      key={idx}
                      className="relative group rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 aspect-video bg-slate-100 dark:bg-slate-800"
                    >
                      <img src={img} alt={`Property ${idx + 1}`} className="w-full h-full object-cover" />
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleRemoveImage(idx)}
                          className="p-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      {idx === 0 && (
                        <span className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-rose-600 text-[9px] font-bold text-white">
                          Cover
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bottom Actions Bar */}
        <div className="flex items-center justify-end gap-3 pt-4">
          <button
            type="button"
            onClick={onBack}
            className="px-6 py-3 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-bold text-sm hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-8 py-3 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 text-white font-bold text-sm shadow-lg shadow-rose-500/25 hover:from-red-700 hover:to-rose-700 disabled:opacity-50 transition-all flex items-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Saving Property...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {propertyId ? 'Update Property Listing' : 'Save & Submit Property'}
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default PropertyForm;
