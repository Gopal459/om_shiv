from typing import Optional, List
from pydantic import BaseModel, Field, model_validator


class FlatDetailsSchema(BaseModel):
    bhk: int = Field(..., ge=1, le=10, description="BHK count")
    rooms: int = Field(..., ge=1, le=10, description="Total room count")
    bathrooms: int = Field(1, ge=1, description="Bathrooms")
    balconies: int = Field(0, ge=0, description="Balconies")
    total_floors: int = Field(1, ge=1, description="Total floors in building")
    property_floor: int = Field(0, ge=0, description="Floor of property")
    super_area: float = Field(..., gt=0, description="Super Built-up Area")
    carpet_area: float = Field(..., gt=0, description="Carpet Area")

    @model_validator(mode="after")
    def validate_flat_rules(self) -> "FlatDetailsSchema":
        # Rule 1: Carpet area strictly less than super area
        if self.carpet_area >= self.super_area:
            raise ValueError("Carpet area must be less than super area")

        # Rule 2: Room count must equal BHK
        if self.rooms != self.bhk:
            raise ValueError("Room count must equal BHK")

        # Rule 3: Property floor cannot exceed total floors
        if self.property_floor > self.total_floors:
            raise ValueError("Property floor cannot exceed total floors")

        return self


class PropertyPostRequest(BaseModel):
    listing_type: int = Field(..., ge=1, le=3, description="1=Rent, 2=Sale, 3=PG")
    category_code: int = Field(..., ge=1, le=4, description="1=Res, 2=Comm, 3=Agri, 4=Ind")
    sub_category_code: int = Field(..., ge=1, description="Sub-category code")

    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    pincode: str = Field(..., min_length=6, max_length=6)
    city: str = Field("Alwar", max_length=100)
    locality: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    expected_price: float = Field(..., gt=0)
    price_negotiable: bool = False

    owner_name: str = Field(..., min_length=2, max_length=150)
    owner_mobile: str = Field(..., min_length=10, max_length=15)
    posted_by_role: str = Field("OWNER", max_length=32)

    flat_details: Optional[FlatDetailsSchema] = None


class QuickListingRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    listing_type: int = Field(..., ge=1, le=3)
    category_code: int = Field(..., ge=1, le=4)
    sub_category_code: int = Field(..., ge=1)
    expected_price: float = Field(..., gt=0)
    pincode: str = Field(..., min_length=6, max_length=6)
    owner_name: str = Field(..., min_length=2, max_length=150)
    owner_mobile: str = Field(..., min_length=10, max_length=15)
    city: str = Field("Alwar", max_length=100)
