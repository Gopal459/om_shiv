from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime


class TblPayingGuestCreate(BaseModel):
    pg_name: Optional[str] = None
    available_category: int = 1  # 1=>Pros, 2=>Students, 3=>Both
    gender: int = 1  # 1=>Boys, 2=>Girls, 3=>Both
    room_type: int = 1  # 1=>Private, 2=>Sharing, 3=>Both
    food_option: int = 2  # 1=>With Food, 2=>Without
    food_type: int = 1  # 1=>Veg, 2=>Non-Veg, 3=>Both
    meal_type: Optional[str] = None
    notice_period: Optional[str] = None
    electrical_charges: Optional[str] = None
    smoking: int = 0
    alcohol: int = 0
    attached_bathroom: int = 0
    attached_balcony: int = 0
    common_area: int = 0
    amenities: Optional[str] = None


class TblPropertyCreateRequest(BaseModel):
    # Core Classification
    property_type: int = Field(..., description="1=>Rent, 2=>Sell, 3=>PG")
    looking_type: int = Field(default=1, description="1=>Res, 2=>Comm, 3=>Agri, 4=>Ind")
    looking_subcat_type: int = Field(default=0)
    looking_subcat_type_value: int = Field(default=0)
    
    # Ownership & Contact
    source_type: int = Field(default=2, description="1=>Broker, 2=>Owner, 3=>Friend & Relative")
    source_owner_name: str = Field(...)
    source_owner_email: Optional[str] = None
    source_owner_mobile: str = Field(...)
    user_id: int = Field(default=0)
    assigned_user_id: int = Field(default=0)
    franchise_id: int = Field(default=0)
    franchiseemember_id: int = Field(default=0)

    # Location
    state_id: int = Field(default=1)
    city_id: int = Field(default=1)
    location_lat: Optional[str] = None
    location_long: Optional[str] = None
    sublocality_address: Optional[str] = None
    location: Optional[str] = None
    nearby_area: Optional[str] = None
    pincode: str = Field(default="0")
    street_no: Optional[str] = None

    # Pricing
    expected_price: float = Field(..., gt=0)
    priceper_unitvalue: float = Field(default=0.0)
    priceperunit_type: int = Field(default=0)
    price_negociable: int = Field(default=0)
    extra_charge_apply: int = Field(default=0)

    # Sale specific
    transaction_type: int = Field(default=0, description="1=>Resale, 2=>New")
    property_ownership: int = Field(default=0, description="1=>Leasehold, 2=>Freehold")
    possession_status: int = Field(default=0, description="1=>Ready, 2=>Under construction")
    construction_age: str = Field(default="0")
    want_tosell: int = Field(default=0)

    # Rent specific
    rentalallow_forid: str = Field(default="0")
    whichpart_torent: int = Field(default=0, description="1=>Complete, 2=>Part")
    floor_torent: int = Field(default=0, description="-1=>Basement, 0=>Ground, etc.")

    # Dimensions & Structure
    area: str = Field(default="0")
    area_unit: int = Field(default=0)
    constructed_area: Optional[str] = None
    constructed_areaunit: int = Field(default=0)
    super_area: Optional[str] = None
    superarea_unit: str = Field(default="0")
    carpet_area: str = Field(default="0")
    carpetarea_unit: str = Field(default="0")
    noof_bhk: int = Field(default=0)
    constructed_floors: int = Field(default=0)
    noof_floors: int = Field(default=0)
    property_which_floors: str = Field(default="0")
    boundary: int = Field(default=0)
    room: int = Field(default=0)
    office: int = Field(default=0)
    kitchen: int = Field(default=0)
    toilet: int = Field(default=0)
    baathroom: int = Field(default=0)
    balcony: int = Field(default=0)
    shade: Optional[str] = None
    machinery_plant: Optional[str] = None
    garage_parking: str = Field(default="0")
    width_facing_road: str = Field(default="0")
    facing: int = Field(default=0)
    flooring: int = Field(default=0)
    corner: int = Field(default=0)
    clu: int = Field(default=0)
    clu_type: int = Field(default=0)

    # Features & Furnishing
    feature_furnished: int = Field(default=0)
    furnished_type: str = Field(default="0")
    featurepowerbackup: int = Field(default=0)
    feature_watersupply: int = Field(default=0)
    feature_lift: int = Field(default=0)
    feature_park: int = Field(default=0)
    feature_ownparking: int = Field(default=0)
    feature_visitparking: int = Field(default=0)
    feature_intercomfac: int = Field(default=0)
    feature_clubhosue: int = Field(default=0)
    feature_swimming: int = Field(default=0)
    feature_fitness: int = Field(default=0)
    feature_gatedcomm: int = Field(default=0)
    feature_security: int = Field(default=0)
    feature_electricityconnection: int = Field(default=0)

    # Nearby
    nearby_atm: int = Field(default=0)
    nearby_childchehe: int = Field(default=0)
    nearby_shoppingmall: int = Field(default=0)
    nearby_hospital: int = Field(default=0)
    nearby_school: int = Field(default=0)
    nearby_multiplex: int = Field(default=0)
    nearby_departmental: int = Field(default=0)

    # Description & Media
    project_name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[str] = None
    images_order: Optional[str] = None
    video: Optional[str] = None

    # PG Details if PG
    pg_details: Optional[TblPayingGuestCreate] = None

    @model_validator(mode="after")
    def validate_conditional_rules(self) -> "TblPropertyCreateRequest":
        # Rule 1: Sale validations (property_type == 2)
        if self.property_type == 2:
            if not self.transaction_type:
                raise ValueError("transaction_type is required for Sale properties (1=Resale, 2=New)")
            
            # Super area vs carpet area
            try:
                c_area = float(self.carpet_area) if self.carpet_area else 0.0
                s_area = float(self.super_area) if self.super_area else 0.0
                if c_area > 0 and s_area > 0 and c_area >= s_area:
                    raise ValueError("carpet_area must be strictly less than super_area")
            except (TypeError, ValueError) as e:
                if "strictly less" in str(e):
                    raise e

        # Rule 2: Rent validations (property_type == 1)
        if self.property_type == 1:
            if not self.rentalallow_forid or self.rentalallow_forid == "0":
                raise ValueError("rentalallow_forid is required for Rent properties")
            if self.whichpart_torent == 2 and self.floor_torent == 0:
                raise ValueError("floor_torent is required when renting part of property")

        # Rule 3: PG validations (property_type == 3)
        if self.property_type == 3:
            if self.pg_details:
                if self.pg_details.food_option == 1 and not (self.pg_details.meal_type and self.pg_details.meal_type.strip()):
                    raise ValueError("meal_type is required when food option is enabled")

        return self


class TblPropertyUpdateRequest(BaseModel):
    property_type: Optional[int] = None
    looking_type: Optional[int] = None
    looking_subcat_type: Optional[int] = None
    source_type: Optional[int] = None
    source_owner_name: Optional[str] = None
    source_owner_email: Optional[str] = None
    source_owner_mobile: Optional[str] = None
    state_id: Optional[int] = None
    city_id: Optional[int] = None
    sublocality_address: Optional[str] = None
    location: Optional[str] = None
    nearby_area: Optional[str] = None
    pincode: Optional[str] = None
    expected_price: Optional[float] = None
    price_negociable: Optional[int] = None
    transaction_type: Optional[int] = None
    property_ownership: Optional[int] = None
    possession_status: Optional[int] = None
    construction_age: Optional[str] = None
    super_area: Optional[str] = None
    carpet_area: Optional[str] = None
    noof_bhk: Optional[int] = None
    project_name: Optional[str] = None
    description: Optional[str] = None
    images: Optional[str] = None
    pg_details: Optional[TblPayingGuestCreate] = None


class TblPropertyStatusUpdateRequest(BaseModel):
    assigned_user_id: Optional[int] = None
    verified_status: Optional[int] = None  # 0=>Unverified, 1=>Verified
    is_active: Optional[int] = None        # 0=>Inactive, 1=>Live
    sold_status: Optional[int] = None      # 0=>Available, 1=>Sold, 2=>Expired
    sold_request_sent: Optional[int] = None
    delete_request_sent: Optional[int] = None
    recyclebin_status: Optional[int] = None
    recyclebin_reason: Optional[str] = None
    live_request_sent: Optional[int] = None


class TblPropertyItem(BaseModel):
    property_id: int
    propertyid_no: str
    property_type: int
    looking_type: int
    looking_subcat_type: int
    title: str
    expected_price: float
    city_id: int
    sublocality_address: Optional[str]
    location: Optional[str]
    source_owner_name: Optional[str]
    source_owner_mobile: Optional[str]
    verified_status: int
    is_active: int
    sold_status: int
    recyclebin_status: int
    assigned_user_id: int
    live_request_sent: int
    delete_request_sent: int
    sold_request_sent: int
    created_date: Optional[str]


class TblPropertyHubListResponse(BaseModel):
    total: int
    tab: str
    page: int
    limit: int
    items: List[Dict[str, Any]]
