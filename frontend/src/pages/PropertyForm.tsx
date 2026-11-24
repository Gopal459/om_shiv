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
  Home,
  KeyRound,
  Users,
  DollarSign,
  FileText,
  Sparkles,
  ExternalLink,
  Copy,
  Info,
  Calendar,
  Phone,
  Mail,
  User,
  CheckCheck,
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

  // Active section for navigation
  const [activeSection, setActiveSection] = useState<'user' | 'location' | 'specs' | 'price' | 'features' | 'media'>('user');

  // Form State
  const [propertyType, setPropertyType] = useState<number>(initialType); // 1=Rent, 2=Sale, 3=PG
  const [lookingType, setLookingType] = useState<number>(1); // 1=Res, 2=Comm, 3=Agri, 4=Ind
  const [subcatType, setSubcatType] = useState<number>(1); // 1=Flat, 2=House, 3=Plot, etc.

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
  const [locationText, setLocationText] = useState('Tijara Road, Bhagwanpura, Alwar');
  const [sublocality, setSublocality] = useState('Alwar Bypass Road');
  const [nearbyArea, setNearbyArea] = useState('Near Cross Point Mall');
  const [pincode, setPincode] = useState('301001');
  const [lat, setLat] = useState('27.5530');
  const [long, setLong] = useState('76.6346');
  const [copiedCoords, setCopiedCoords] = useState(false);

  // Property Details
  const [unitStreet, setUnitStreet] = useState('');
  const [area, setArea] = useState('1200');
  const [areaUnit, setAreaUnit] = useState('Sq.Ft');
  const [boundary, setBoundary] = useState(true);
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
  const [facing, setFacing] = useState(1); // 1=East, 2=West, 3=North, 4=South, etc.
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
  const [images, setImages] = useState<string[]>([
    '/uploads/sample-flat-1.jpg',
    '/uploads/sample-flat-2.jpg',
  ]);
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

  // Carpet area to Super area ratio
  const areaRatio = useMemo(() => {
    const c = parseFloat(carpetArea) || 0;
    const s = parseFloat(superArea) || 0;
    if (s <= 0) return null;
    return Math.round((c / s) * 100);
  }, [carpetArea, superArea]);

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

  const copyCoordinates = () => {
    navigator.clipboard.writeText(`${lat}, ${long}`);
    setCopiedCoords(true);
    setTimeout(() => setCopiedCoords(false), 2000);
  };

  // Form Submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!ownerName.trim()) {
      setError('Owner Name is required.');
      setActiveSection('user');
      return;
    }
    if (!ownerMobile.trim() || ownerMobile.length < 10) {
      setError('Valid 10-digit Owner Mobile is required.');
      setActiveSection('user');
      return;
    }
    const priceNum = parseFloat(expectedPrice);
    if (isNaN(priceNum) || priceNum <= 0) {
      setError('Expected Price must be greater than 0.');
      setActiveSection('price');
      return;
    }

    if (propertyType === 2) {
      const c = parseFloat(carpetArea) || 0;
      const s = parseFloat(superArea) || 0;
      if (c > 0 && s > 0 && c >= s) {
        setError('Carpet area must be strictly less than super area.');
        setActiveSection('specs');
        return;
      }
      if (!transactionType) {
        setError('Transaction Type is required for Sale property.');
        setActiveSection('specs');
        return;
      }
    }

    if (propertyType === 1 && whichPartToRent === 2 && floorToRent === 0) {
      setError('Floor to rent is mandatory when renting some part of property.');
      setActiveSection('specs');
      return;
    }

    if (propertyType === 3 && pgFoodOption === 1 && pgMeals.length === 0) {
      setError('Please select at least one meal type (Breakfast/Lunch/Dinner) when food option is enabled.');
      setActiveSection('specs');
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

      setSuccess(`Property ${data.propertyid_no || 'listing'} successfully saved to inventory!`);
      setTimeout(() => {
        onSuccess(data);
      }, 1200);
    } catch (err: any) {
      setError(err.message || 'An error occurred during submission.');
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    { id: 'user', label: '1. Seller Profile', icon: User },
    { id: 'location', label: '2. Location & Geo', icon: MapPin },
    { id: 'specs', label: '3. Property Specs', icon: Building },
    { id: 'price', label: '4. Commercials', icon: DollarSign },
    { id: 'features', label: '5. Amenities', icon: Sparkles },
    { id: 'media', label: '6. Media Gallery', icon: Camera },
  ];

  if (fetching) {
    return (
      <div className="p-20 text-center">
        <div className="animate-spin w-10 h-10 border-4 border-rose-500 border-t-transparent rounded-full mx-auto mb-4"></div>
        <p className="text-sm font-semibold text-slate-500 dark:text-slate-400">Loading Property Dossier...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* 1. ULTRA-MODERN HEADER DOCK */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 text-white rounded-3xl p-6 sm:p-8 border border-slate-800 shadow-2xl">
        {/* Glow Accent */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-rose-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-rose-400 uppercase">
              <button
                type="button"
                onClick={onBack}
                className="hover:underline flex items-center gap-1 text-slate-400 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Inventory
              </button>
              <span>/</span>
              <span>Propira Engine</span>
              <span>/</span>
              <span className="text-white font-bold">124-Attribute Schema</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
              {propertyId ? 'Edit Property Listing' : 'Register New Property'}
              <span className="text-xs px-3 py-1 rounded-full font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                {propertyType === 2 ? 'For Sale' : propertyType === 1 ? 'For Rent' : 'PG Stay'}
              </span>
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-xl">
              Enterprise property ingestion engine with real-time statutory validation, automatic Indian rupee conversion, and dual-layer database mapping.
            </p>
          </div>

          {/* Segmented Modern Switcher */}
          <div className="flex items-center bg-slate-800/80 backdrop-blur-md p-1.5 rounded-2xl border border-slate-700/60 shadow-inner self-start lg:self-center">
            <button
              type="button"
              onClick={() => setPropertyType(2)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
                propertyType === 2
                  ? 'bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-lg shadow-rose-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Home className="w-3.5 h-3.5" />
              Sell / Buy
            </button>
            <button
              type="button"
              onClick={() => setPropertyType(1)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
                propertyType === 1
                  ? 'bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-lg shadow-rose-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              Rent Property
            </button>
            <button
              type="button"
              onClick={() => setPropertyType(3)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
                propertyType === 3
                  ? 'bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-lg shadow-rose-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              PG Stay
            </button>
          </div>
        </div>

        {/* 2. MODERN HORIZONTAL PROGRESS STEPPER */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mt-8 pt-6 border-t border-slate-800/80">
          {steps.map((s) => {
            const Icon = s.icon;
            const isCurrent = activeSection === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => {
                  setActiveSection(s.id as any);
                  const el = document.getElementById(`section-${s.id}`);
                  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }}
                className={`text-left p-2.5 rounded-xl transition-all border flex items-center gap-2.5 ${
                  isCurrent
                    ? 'bg-rose-500/15 border-rose-500/40 text-rose-300'
                    : 'bg-slate-800/30 border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                    isCurrent ? 'bg-rose-500 text-white' : 'bg-slate-700/60 text-slate-300'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <span className="text-xs font-semibold truncate">{s.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center gap-3 text-red-600 dark:text-red-400 text-sm shadow-sm animate-shake">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="font-medium">{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-emerald-600 dark:text-emerald-400 text-sm shadow-sm">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span className="font-medium">{success}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* ========================================================= */}
        {/* CARD 1: SELLER & CONTACT (USER INFO)                      */}
        {/* ========================================================= */}
        <div
          id="section-user"
          className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6"
        >
          {/* Executive Section Header */}
          <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800/80 pb-5">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-rose-500 to-red-600 text-white flex items-center justify-center shadow-md shadow-rose-500/20">
                <User className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Seller & Ownership Dossier
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Direct owner identity, contact credentials, and lead intake routing.
                </p>
              </div>
            </div>
            <span className="text-xs font-bold px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              Section 01
            </span>
          </div>

          {/* Source Type Selector Chips */}
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 uppercase tracking-wider">
              Posting As / Source Entity
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { id: 2, label: 'Direct Owner', desc: 'Individual or family property owner' },
                { id: 1, label: 'Certified Agent', desc: 'Registered real estate broker or franchisee' },
                { id: 3, label: 'Builder / Developer', desc: 'Authorized construction or project firm' },
              ].map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setSourceType(s.id)}
                  className={`p-3.5 rounded-2xl border text-left transition-all ${
                    sourceType === s.id
                      ? 'border-rose-500 bg-rose-50/50 dark:bg-rose-950/20 shadow-xs'
                      : 'border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900 dark:text-white">{s.label}</span>
                    {sourceType === s.id && (
                      <span className="w-4 h-4 rounded-full bg-rose-500 text-white flex items-center justify-center text-[10px]">
                        ✓
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">{s.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Form Inputs Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                Owner / Contact Name <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  required
                  value={ownerName}
                  onChange={(e) => setOwnerName(e.target.value)}
                  placeholder="e.g. Ramesh Kumar"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                Mobile Number <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-2.5 text-xs font-bold text-slate-400">+91</span>
                <input
                  type="tel"
                  required
                  value={ownerMobile}
                  onChange={(e) => setOwnerMobile(e.target.value)}
                  placeholder="98765 43210"
                  className="w-full pl-12 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all font-mono"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                Email Address (Optional)
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="email"
                  value={ownerEmail}
                  onChange={(e) => setOwnerEmail(e.target.value)}
                  placeholder="ramesh@example.com"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 transition-all"
                />
              </div>
            </div>
          </div>
        </div>

        {/* ========================================================= */}
        {/* CARD 2: LOCATION & GEO-COORDINATES                       */}
        {/* ========================================================= */}
        <div
          id="section-location"
          className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6"
        >
          <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800/80 pb-5">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-600 text-white flex items-center justify-center shadow-md shadow-emerald-500/20">
                <MapPin className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Geo-Location & Address Mapping
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Precise geographic coordinates and localized neighborhood identification.
                </p>
              </div>
            </div>
            <span className="text-xs font-bold px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              Section 02
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">State</label>
              <select
                value={stateName}
                onChange={(e) => setStateName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              >
                <option value="Rajasthan">Rajasthan</option>
                <option value="Haryana">Haryana</option>
                <option value="Delhi">Delhi NCR</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">City</label>
              <select
                value={cityName}
                onChange={(e) => setCityName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              >
                <option value="Alwar">Alwar</option>
                <option value="Bhiwadi">Bhiwadi</option>
                <option value="Neemrana">Neemrana</option>
                <option value="Jaipur">Jaipur</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Pincode</label>
              <input
                type="text"
                value={pincode}
                onChange={(e) => setPincode(e.target.value)}
                placeholder="301001"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Listing Validity</label>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={expireDate}
                  onChange={(e) => setExpireDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                />
              </div>
            </div>

            <div className="lg:col-span-2">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                Complete Location / Street Address <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                value={locationText}
                onChange={(e) => setLocationText(e.target.value)}
                placeholder="e.g. Tijara Road, Bhagwanpura, Alwar, Rajasthan"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              />
            </div>

            <div className="lg:col-span-2">
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                Prominent Nearby Landmark (Optional)
              </label>
              <input
                type="text"
                value={nearbyArea}
                onChange={(e) => setNearbyArea(e.target.value)}
                placeholder="e.g. 500m from Cross Point Mall, Near Civil Lines"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              />
            </div>
          </div>

          {/* Interactive Coordinates Card */}
          <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-500/5 via-teal-500/5 to-transparent border border-emerald-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                <Compass className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs font-bold text-slate-900 dark:text-white block">
                  Geographic Pinpoint: {lat}° N, {long}° E
                </span>
                <span className="text-[11px] text-slate-500 dark:text-slate-400">
                  Pre-calibrated for Alwar urban zone. Used for map view & radius search.
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={copyCoordinates}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-50 flex items-center gap-1.5 transition-all"
              >
                {copiedCoords ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                {copiedCoords ? 'Copied' : 'Copy'}
              </button>
              <a
                href={`https://www.google.com/maps?q=${lat},${long}`}
                target="_blank"
                rel="noreferrer"
                className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Google Maps
              </a>
            </div>
          </div>
        </div>

        {/* ========================================================= */}
        {/* CARD 3: SPECS & ARCHITECTURAL LAYOUT                      */}
        {/* ========================================================= */}
        <div
          id="section-specs"
          className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6"
        >
          <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800/80 pb-5">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-500 to-indigo-600 text-white flex items-center justify-center shadow-md shadow-blue-500/20">
                <Building className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Architectural Specifications & Layout
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Unit dimensions, room counts, floor position, and ownership terms.
                </p>
              </div>
            </div>
            <span className="text-xs font-bold px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              Section 03
            </span>
          </div>

          {/* Looking Type Grid */}
          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2 uppercase tracking-wider">
              Property Category
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { id: 1, label: 'Residential', icon: Home, desc: 'Apartments, Villas, Floors' },
                { id: 2, label: 'Commercial', icon: Building, desc: 'Shops, Offices, Complexes' },
                { id: 3, label: 'Agricultural', icon: Trees, desc: 'Farms, Farmlands, Bigha' },
                { id: 4, label: 'Industrial', icon: Layers, desc: 'Sheds, Plants, Warehouses' },
              ].map((c) => {
                const Icon = c.icon;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setLookingType(c.id)}
                    className={`p-3.5 rounded-2xl border text-left transition-all ${
                      lookingType === c.id
                        ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/20 shadow-xs'
                        : 'border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 hover:border-slate-300'
                    }`}
                  >
                    <Icon className={`w-5 h-5 mb-1.5 ${lookingType === c.id ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400'}`} />
                    <span className="text-xs font-bold text-slate-900 dark:text-white block">{c.label}</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">{c.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Common Dimensions Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 pt-2">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Sub-Type</label>
              <select
                value={subcatType}
                onChange={(e) => setSubcatType(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                {lookingType === 1 && (
                  <>
                    <option value={1}>Flat / Apartment</option>
                    <option value={2}>Independent House / Villa</option>
                    <option value={3}>Residential Plot / Land</option>
                    <option value={4}>Builder Floor</option>
                  </>
                )}
                {lookingType === 2 && (
                  <>
                    <option value={5}>Commercial Office</option>
                    <option value={6}>Commercial Retail Shop</option>
                    <option value={7}>Commercial Plot</option>
                  </>
                )}
                {lookingType === 3 && (
                  <>
                    <option value={8}>Agricultural Farmland</option>
                    <option value={9}>Farmhouse Land</option>
                  </>
                )}
                {lookingType === 4 && (
                  <>
                    <option value={10}>Industrial Factory / Shed</option>
                    <option value={11}>Industrial Plot</option>
                  </>
                )}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                Unit / Flat / Plot No. <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                value={unitStreet}
                onChange={(e) => setUnitStreet(e.target.value)}
                placeholder="e.g. Flat 302, Tower B"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Total Area</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={area}
                  onChange={(e) => setArea(e.target.value)}
                  className="w-2/3 px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-rose-500"
                />
                <select
                  value={areaUnit}
                  onChange={(e) => setAreaUnit(e.target.value)}
                  className="w-1/3 px-2 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white"
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
            <div className="flex items-center justify-between p-3.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
              <div>
                <span className="text-xs font-bold text-slate-900 dark:text-white block">Boundary Wall</span>
                <span className="text-[11px] text-slate-400">{boundary ? 'Constructed / Fenced' : 'Open Land'}</span>
              </div>
              <button
                type="button"
                onClick={() => setBoundary(!boundary)}
                className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ${
                  boundary ? 'bg-rose-500 justify-end' : 'bg-slate-300 dark:bg-slate-600 justify-start'
                }`}
              >
                <span className="w-4 h-4 rounded-full bg-white shadow-md"></span>
              </button>
            </div>
          </div>

          {/* SALE CONDITIONAL RULES */}
          {propertyType === 2 && (
            <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-200/80 dark:border-slate-800 space-y-4">
              <span className="text-xs font-extrabold text-slate-900 dark:text-white uppercase tracking-wider block">
                Sale Statutory Parameters & Area Compliance
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Transaction Type</label>
                  <div className="flex gap-2">
                    {[
                      { id: 1, label: 'Resale' },
                      { id: 2, label: 'New Booking' },
                    ].map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => setTransactionType(t.id)}
                        className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-all ${
                          transactionType === t.id
                            ? 'bg-rose-500 text-white border-rose-500 shadow-xs'
                            : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Possession Status</label>
                  <div className="flex gap-2">
                    {[
                      { id: 1, label: 'Ready Possession' },
                      { id: 2, label: 'Under Construction' },
                    ].map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => setPossessionStatus(p.id)}
                        className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-all ${
                          possessionStatus === p.id
                            ? 'bg-rose-500 text-white border-rose-500 shadow-xs'
                            : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'
                        }`}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Super Area (Sq.Ft)</label>
                  <input
                    type="number"
                    value={superArea}
                    onChange={(e) => setSuperArea(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold text-slate-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">
                    Carpet Area (Sq.Ft)
                  </label>
                  <input
                    type="number"
                    value={carpetArea}
                    onChange={(e) => setCarpetArea(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold text-slate-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Area Ratio Gauge */}
              {areaRatio !== null && (
                <div className="flex items-center justify-between p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Carpet Efficiency:</span>
                    <span
                      className={`text-xs font-extrabold px-2 py-0.5 rounded-md ${
                        areaRatio < 100
                          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                          : 'bg-red-500/10 text-red-600 dark:text-red-400'
                      }`}
                    >
                      {areaRatio}% of Super Area
                    </span>
                  </div>
                  {areaRatio >= 100 && (
                    <span className="text-[11px] font-bold text-red-600 flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" /> Invalid: Carpet area must be strictly less than Super Area
                    </span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* RENT CONDITIONAL RULES */}
          {propertyType === 1 && (
            <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-200/80 dark:border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Tenant Preference</label>
                <select
                  value={rentalAllowFor}
                  onChange={(e) => setRentalAllowFor(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold"
                >
                  <option value="Family">Family Only</option>
                  <option value="Bachelors">Bachelors (Boys/Girls)</option>
                  <option value="Company">Company Lease</option>
                  <option value="Any">Any / No Restriction</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Lease Scope</label>
                <select
                  value={whichPartToRent}
                  onChange={(e) => setWhichPartToRent(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold"
                >
                  <option value={1}>Entire Property</option>
                  <option value={2}>Specific Floor / Portion</option>
                </select>
              </div>

              {whichPartToRent === 2 && (
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Floor Level</label>
                  <select
                    value={floorToRent}
                    onChange={(e) => setFloorToRent(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold"
                  >
                    <option value={0}>Ground Floor</option>
                    <option value={1}>1st Floor</option>
                    <option value={2}>2nd Floor</option>
                    <option value={-1}>Basement</option>
                  </select>
                </div>
              )}
            </div>
          )}

          {/* PG CONDITIONAL RULES */}
          {propertyType === 3 && (
            <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-200/80 dark:border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">PG Hostel Name</label>
                <input
                  type="text"
                  value={pgName}
                  onChange={(e) => setPgName(e.target.value)}
                  placeholder="e.g. Om Shiv PG & Co-living"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Gender Policy</label>
                <select
                  value={pgGender}
                  onChange={(e) => setPgGender(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold"
                >
                  <option value={1}>Boys Only</option>
                  <option value={2}>Girls Only</option>
                  <option value={3}>Unisex / Both</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5">Food Facility</label>
                <select
                  value={pgFoodOption}
                  onChange={(e) => setPgFoodOption(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold"
                >
                  <option value={1}>Food Included (Mess)</option>
                  <option value={2}>Without Food (Stay Only)</option>
                </select>
              </div>

              {pgFoodOption === 1 && (
                <div className="sm:col-span-3 flex items-center gap-4 pt-2">
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Meals Served:</span>
                  {['Breakfast', 'Lunch', 'Dinner'].map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => handleToggleMeal(m)}
                      className={`px-3 py-1 rounded-lg text-xs font-bold border transition-all ${
                        pgMeals.includes(m)
                          ? 'bg-rose-500 text-white border-rose-500'
                          : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-600'
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* BHK & Society Details for Flats */}
          {(subcatType === 1 || subcatType === 2) && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-2">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Project / Society Name</label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g. Royal Residency, Tijara Road"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">BHK Configuration</label>
                <div className="flex gap-1.5">
                  {[1, 2, 3, 4, 5].map((bhk) => (
                    <button
                      key={bhk}
                      type="button"
                      onClick={() => setNoofBhk(bhk)}
                      className={`flex-1 py-2 rounded-xl text-xs font-bold border transition-all ${
                        noofBhk === bhk
                          ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                          : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      {bhk} {bhk === 5 ? '5+' : 'BHK'}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Bathrooms</label>
                  <input
                    type="number"
                    value={bathrooms}
                    onChange={(e) => setBathrooms(Number(e.target.value))}
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Balconies</label>
                  <input
                    type="number"
                    value={balconies}
                    onChange={(e) => setBalconies(Number(e.target.value))}
                    className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ========================================================= */}
        {/* CARD 4: COMMERCIALS & PRICING                             */}
        {/* ========================================================= */}
        <div
          id="section-price"
          className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6"
        >
          <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800/80 pb-5">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-amber-500 to-orange-600 text-white flex items-center justify-center shadow-md shadow-amber-500/20">
                <DollarSign className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Financial Terms & Pricing Commercials
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Target price, rate formatting, Indian currency words, and negotiation rules.
                </p>
              </div>
            </div>
            <span className="text-xs font-bold px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              Section 04
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Pricing Structure</label>
              <select
                value={priceFormat}
                onChange={(e) => setPriceFormat(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white"
              >
                <option value="Total Price">Total Expected Lump-Sum</option>
                <option value="Sq.Ft">Per Square Foot</option>
                <option value="Ares">Per Ares</option>
                <option value="Bigha">Per Bigha</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Unit Rate (Optional)</label>
              <input
                type="number"
                value={pricePerUnit}
                onChange={(e) => setPricePerUnit(e.target.value)}
                placeholder="45000"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold text-slate-900 dark:text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                Expected Price (₹) <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <span className="absolute left-3.5 top-2.5 font-bold text-rose-500">₹</span>
                <input
                  type="number"
                  required
                  value={expectedPrice}
                  onChange={(e) => setExpectedPrice(e.target.value)}
                  placeholder="4500000"
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-rose-300 dark:border-rose-900/60 bg-rose-50/20 dark:bg-rose-950/10 text-sm font-extrabold text-rose-600 dark:text-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-500"
                />
              </div>
            </div>
          </div>

          {/* Hero Amount In Words Banner (Screenshot 9) */}
          <div className="relative overflow-hidden p-5 rounded-2xl bg-gradient-to-r from-slate-900 to-slate-800 text-white border border-slate-700/80 shadow-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[11px] font-bold text-rose-400 uppercase tracking-wider block mb-1">
                  Indian Currency Amount In Words
                </span>
                <p className="text-base sm:text-lg font-extrabold text-white tracking-wide">
                  {amountInWords}
                </p>
              </div>
              <div className="text-right">
                <span className="text-xs font-mono font-bold px-3 py-1 rounded-lg bg-white/10 text-slate-200">
                  ₹ {parseFloat(expectedPrice || '0').toLocaleString('en-IN')}
                </span>
              </div>
            </div>
          </div>

          {/* Negotiation & Extra Charges Switchers */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div className="flex items-center justify-between p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
              <div>
                <span className="text-xs font-bold text-slate-900 dark:text-white block">Price Negotiability</span>
                <span className="text-[11px] text-slate-400">
                  {priceNegotiable ? 'Open to buyer offers' : 'Strictly fixed pricing'}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setPriceNegotiable(!priceNegotiable)}
                className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ${
                  priceNegotiable ? 'bg-rose-500 justify-end' : 'bg-slate-300 dark:bg-slate-600 justify-start'
                }`}
              >
                <span className="w-4 h-4 rounded-full bg-white shadow-md"></span>
              </button>
            </div>

            <div className="flex items-center justify-between p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
              <div>
                <span className="text-xs font-bold text-slate-900 dark:text-white block">Statutory Extra Charges</span>
                <span className="text-[11px] text-slate-400">
                  {extraCharge ? 'Registry, GST or maintenance apply' : 'All-inclusive price'}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setExtraCharge(!extraCharge)}
                className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ${
                  extraCharge ? 'bg-rose-500 justify-end' : 'bg-slate-300 dark:bg-slate-600 justify-start'
                }`}
              >
                <span className="w-4 h-4 rounded-full bg-white shadow-md"></span>
              </button>
            </div>
          </div>
        </div>

        {/* ========================================================= */}
        {/* CARD 5: FEATURES & AMENITIES                              */}
        {/* ========================================================= */}
        <div
          id="section-features"
          className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6"
        >
          <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800/80 pb-5">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-rose-500 to-pink-600 text-white flex items-center justify-center shadow-md shadow-rose-500/20">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Property Features & Community Amenities
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Road width frontage, cardinal direction, corner plot status, and infrastructure.
                </p>
              </div>
            </div>
            <span className="text-xs font-bold px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              Section 05
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                Facing Road Width <span className="text-rose-500">*</span>
              </label>
              <div className="flex">
                <input
                  type="number"
                  value={roadWidth}
                  onChange={(e) => setRoadWidth(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-l-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold"
                />
                <span className="px-4 py-2.5 rounded-r-xl border border-l-0 border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-xs font-bold text-slate-500 flex items-center">
                  Foot
                </span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
                Cardinal Facing Direction <span className="text-rose-500">*</span>
              </label>
              <select
                value={facing}
                onChange={(e) => setFacing(Number(e.target.value))}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-semibold"
              >
                <option value={1}>East Facing (Sunrise)</option>
                <option value={2}>West Facing</option>
                <option value={3}>North Facing</option>
                <option value={4}>South Facing</option>
                <option value={5}>North-East (Ishan)</option>
                <option value={6}>North-West</option>
                <option value={7}>South-East</option>
                <option value={8}>South-West</option>
              </select>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
              <div>
                <span className="text-xs font-bold text-slate-900 dark:text-white block">Corner Plot Position</span>
                <span className="text-[11px] text-slate-400">{isCorner ? 'Dual Road Access' : 'Single Road Facing'}</span>
              </div>
              <button
                type="button"
                onClick={() => setIsCorner(!isCorner)}
                className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ${
                  isCorner ? 'bg-rose-500 justify-end' : 'bg-slate-300 dark:bg-slate-600 justify-start'
                }`}
              >
                <span className="w-4 h-4 rounded-full bg-white shadow-md"></span>
              </button>
            </div>
          </div>

          {/* Interactive Common Features Grid (Matching Screenshot 9) */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-extrabold text-slate-900 dark:text-white uppercase tracking-wider">
                Common Amenities & Utilities Checklist
              </span>
              <button
                type="button"
                onClick={() => {
                  const allOn = Object.values(features).every(Boolean);
                  setFeatures({
                    waterSupply: !allOn,
                    electricity: !allOn,
                    powerBackup: !allOn,
                    lift: !allOn,
                    park: !allOn,
                    ownParking: !allOn,
                    visitParking: !allOn,
                    intercom: !allOn,
                    clubHouse: !allOn,
                    swimming: !allOn,
                    fitness: !allOn,
                    gatedCommunity: !allOn,
                    security: !allOn,
                  });
                }}
                className="text-xs font-bold text-rose-500 hover:underline"
              >
                Toggle All Amenities
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3.5">
              {[
                { key: 'waterSupply', label: 'Water Supply', icon: Droplets },
                { key: 'electricity', label: 'Electricity Con.', icon: Zap },
                { key: 'powerBackup', label: 'Power Backup', icon: BatteryCharging },
                { key: 'lift', label: 'Lift / Elevator', icon: Layers },
                { key: 'park', label: 'Park / Greenery', icon: Trees },
                { key: 'ownParking', label: 'Covered Parking', icon: Car },
                { key: 'visitParking', label: 'Visitor Parking', icon: Car },
                { key: 'intercom', label: 'Intercom Line', icon: PhoneCall },
                { key: 'clubHouse', label: 'Club House', icon: Building },
                { key: 'swimming', label: 'Swimming Pool', icon: Waves },
                { key: 'fitness', label: 'Fitness Gym', icon: Dumbbell },
                { key: 'security', label: '24x7 Security CCTV', icon: ShieldCheck },
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
                    className={`relative p-4 rounded-2xl border text-center flex flex-col items-center justify-center gap-2.5 transition-all group ${
                      active
                        ? 'border-rose-500/60 bg-rose-50/70 dark:bg-rose-950/25 shadow-sm ring-1 ring-rose-500/20'
                        : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 opacity-60 hover:opacity-100 hover:border-slate-300'
                    }`}
                  >
                    {active && (
                      <span className="absolute top-2 right-2 w-4 h-4 rounded-full bg-rose-500 text-white flex items-center justify-center text-[9px] shadow-xs">
                        ✓
                      </span>
                    )}
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110 ${
                        active
                          ? 'bg-rose-500 text-white shadow-sm shadow-rose-500/30'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-bold text-slate-800 dark:text-slate-200 line-clamp-1">
                      {item.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* ========================================================= */}
        {/* CARD 6: MEDIA & MARKETING DESCRIPTION                     */}
        {/* ========================================================= */}
        <div
          id="section-media"
          className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 shadow-sm p-6 sm:p-8 space-y-6"
        >
          <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800/80 pb-5">
            <div className="flex items-center gap-3.5">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-500 to-indigo-600 text-white flex items-center justify-center shadow-md shadow-purple-500/20">
                <Camera className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Media Gallery & Marketing Narrative
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Upload high-definition photographs and craft compelling listing highlights.
                </p>
              </div>
            </div>
            <span className="text-xs font-bold px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              Section 06
            </span>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">
              Marketing Narrative / Description
            </label>
            <textarea
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide a comprehensive narrative of the property: key highlights, sunlight exposure, quality of construction, nearby schools, market connectivity..."
              className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-800/50 text-xs font-medium text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-rose-500"
            />
          </div>

          {/* High-Tech Photo Upload Box (Matching Screenshot 10 specs) */}
          <div className="p-6 sm:p-8 rounded-3xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-slate-50/40 dark:bg-slate-800/20 text-center space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-rose-50 dark:bg-rose-950/40 text-rose-500 flex items-center justify-center mx-auto shadow-inner">
              <Camera className="w-7 h-7" />
            </div>

            <div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                Upload Property Photographs
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Drag and drop your photographs or enter image resource URLs below.
              </p>
            </div>

            {/* Specifications Chips */}
            <div className="flex flex-wrap items-center justify-center gap-2 max-w-2xl mx-auto pt-1">
              {[
                'Max 10 Photos',
                'Min 10KB Size',
                'Max 2MB per Image',
                'PNG / JPG / JPEG Formats',
                '600 x 400 Recommended Ratio',
              ].map((spec) => (
                <span
                  key={spec}
                  className="px-3 py-1 rounded-full text-[11px] font-semibold bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 shadow-2xs"
                >
                  * {spec}
                </span>
              ))}
            </div>

            {/* Add Image Input Bar */}
            <div className="max-w-lg mx-auto flex gap-2 pt-3">
              <input
                type="text"
                value={newImageUrl}
                onChange={(e) => setNewImageUrl(e.target.value)}
                placeholder="Enter or paste image URL (e.g. /uploads/property-living-room.jpg)"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
              <button
                type="button"
                onClick={handleAddImage}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white font-bold text-xs flex items-center gap-2 shadow-md transition-all flex-shrink-0"
              >
                <Upload className="w-3.5 h-3.5" />
                Add Photo
              </button>
            </div>

            {/* Gallery Grid */}
            {images.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-4 pt-6">
                {images.map((img, idx) => (
                  <div
                    key={idx}
                    className="relative group rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-700 aspect-video bg-slate-100 dark:bg-slate-800 shadow-sm"
                  >
                    <img src={img} alt={`Property ${idx + 1}`} className="w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-slate-950/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleRemoveImage(idx)}
                        className="p-2 rounded-xl bg-red-600 text-white hover:bg-red-700 transition-colors"
                        title="Remove image"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    {idx === 0 && (
                      <span className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-rose-600 text-[9px] font-bold text-white shadow-xs">
                        ★ Primary Cover
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ========================================================= */}
        {/* STICKY BOTTOM ACTION DOCK                                 */}
        {/* ========================================================= */}
        <div className="sticky bottom-4 z-40 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-200 dark:border-slate-800 p-4 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onBack}
              className="px-5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold text-xs transition-colors"
            >
              Cancel & Exit
            </button>
            <span className="text-xs text-slate-500 dark:text-slate-400 hidden sm:inline">
              Form ready for submission (124 columns)
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={loading}
              className="px-8 py-3 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-700 hover:to-rose-700 text-white font-extrabold text-xs shadow-lg shadow-rose-500/25 disabled:opacity-50 transition-all flex items-center gap-2 cursor-pointer"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Validating & Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  {propertyId ? 'Update Property Dossier' : 'Save & Publish Property Listing'}
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default PropertyForm;
