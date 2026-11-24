import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.properties import (
    Property,
    PropertySequence,
    PropResidentialFlat,
)
from app.models.property_master import PincodeMaster
from app.schemas.property_schemas import PropertyPostRequest, QuickListingRequest

logger = logging.getLogger(__name__)


async def generate_property_id(db: AsyncSession) -> str:
    """Atomically allocates the next 5-digit sequence ID for OP-YYYY-NNNNN."""
    current_year = datetime.now(timezone.utc).year

    # Check for existing sequence row
    stmt = (
        select(PropertySequence)
        .where(PropertySequence.year == current_year)
        .with_for_update()
    )
    result = await db.execute(stmt)
    seq_record = result.scalar_one_or_none()

    if not seq_record:
        # Create sequence record for new year
        seq_record = PropertySequence(year=current_year, last_sequence=1)
        db.add(seq_record)
        await db.flush()
        seq_num = 1
    else:
        seq_record.last_sequence += 1
        seq_num = seq_record.last_sequence

    # Format: OP-YYYY-NNNNN (5 digits zero-padded, unbounded)
    return f"OP-{current_year}-{seq_num:05d}"


async def validate_pincode_serviceable(pincode: str, db: AsyncSession) -> None:
    """Ensures pincode exists in pincode_master and is serviceable."""
    stmt = select(PincodeMaster).where(
        PincodeMaster.pincode == pincode.strip(),
        PincodeMaster.is_serviceable == True,
    )
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Pincode {pincode} does not exist in master registry or is not serviceable.",
        )


async def create_property(
    payload: PropertyPostRequest,
    db: AsyncSession,
    source: str = "PORTAL",
) -> Property:
    """Creates a validated property listing with 5-digit sequence."""
    await validate_pincode_serviceable(payload.pincode, db)
    prop_id = await generate_property_id(db)

    property_obj = Property(
        property_id=prop_id,
        listing_type=payload.listing_type,
        category_code=payload.category_code,
        sub_category_code=payload.sub_category_code,
        title=payload.title,
        description=payload.description,
        pincode=payload.pincode,
        city=payload.city,
        locality=payload.locality,
        latitude=payload.latitude,
        longitude=payload.longitude,
        expected_price=payload.expected_price,
        price_negotiable=payload.price_negotiable,
        owner_name=payload.owner_name,
        owner_mobile=payload.owner_mobile,
        posted_by_role=payload.posted_by_role,
        source=source,
        verified_status=0,
        is_live=False,
    )
    db.add(property_obj)
    await db.flush()

    # If flat details provided, add child flat record
    if payload.flat_details:
        flat = PropResidentialFlat(
            property_id=property_obj.id,
            bhk=payload.flat_details.bhk,
            rooms=payload.flat_details.rooms,
            bathrooms=payload.flat_details.bathrooms,
            balconies=payload.flat_details.balconies,
            super_area=payload.flat_details.super_area,
            carpet_area=payload.flat_details.carpet_area,
            total_floors=payload.flat_details.total_floors,
            property_floor=payload.flat_details.property_floor,
        )
        db.add(flat)

    await db.commit()
    await db.refresh(property_obj)
    return property_obj


async def create_quick_listing(
    payload: QuickListingRequest,
    db: AsyncSession,
) -> Property:
    """Creates an unauthenticated quick listing."""
    await validate_pincode_serviceable(payload.pincode, db)
    prop_id = await generate_property_id(db)

    property_obj = Property(
        property_id=prop_id,
        listing_type=payload.listing_type,
        category_code=payload.category_code,
        sub_category_code=payload.sub_category_code,
        title=payload.title,
        pincode=payload.pincode,
        city=payload.city,
        expected_price=payload.expected_price,
        owner_name=payload.owner_name,
        owner_mobile=payload.owner_mobile,
        source="QUICK_LISTING",
        verified_status=0,
        is_live=False,
    )
    db.add(property_obj)
    await db.commit()
    await db.refresh(property_obj)
    return property_obj


async def create_tbl_property(
    payload: "TblPropertyCreateRequest",
    db: AsyncSession,
) -> "TblProperty":
    """Creates a validated property in tbl_property and tbl_payingguest."""
    from app.models.properties import TblProperty, TblPayingGuest
    import re

    prop_id_code = await generate_property_id(db)
    
    # Generate slug from owner name and property id
    clean_name = re.sub(r'[^a-zA-Z0-9]+', '-', payload.source_owner_name.strip().lower())
    slug = f"{clean_name}-{prop_id_code.lower()}"

    tbl_prop = TblProperty(
        propertyid_no=prop_id_code,
        property_type=payload.property_type,
        looking_type=payload.looking_type,
        looking_subcat_type=payload.looking_subcat_type,
        looking_subcat_type_value=payload.looking_subcat_type_value,
        source_type=payload.source_type,
        source_owner_name=payload.source_owner_name,
        source_owner_email=payload.source_owner_email,
        source_owner_mobile=payload.source_owner_mobile,
        user_id=payload.user_id,
        assigned_user_id=payload.assigned_user_id,
        franchise_id=payload.franchise_id,
        franchiseemember_id=payload.franchiseemember_id,
        state_id=payload.state_id,
        city_id=payload.city_id,
        location_lat=payload.location_lat,
        location_long=payload.location_long,
        sublocality_address=payload.sublocality_address,
        location=payload.location,
        nearby_area=payload.nearby_area,
        pincode=payload.pincode,
        street_no=payload.street_no,
        slug=slug,
        expected_price=payload.expected_price,
        priceper_unitvalue=payload.priceper_unitvalue,
        priceperunit_type=payload.priceperunit_type,
        price_negociable=payload.price_negociable,
        extra_charge_apply=payload.extra_charge_apply,
        transaction_type=payload.transaction_type,
        property_ownership=payload.property_ownership,
        possession_status=payload.possession_status,
        construction_age=payload.construction_age,
        want_tosell=payload.want_tosell,
        rentalallow_forid=payload.rentalallow_forid,
        whichpart_torent=payload.whichpart_torent,
        floor_torent=payload.floor_torent,
        area=payload.area,
        area_unit=payload.area_unit,
        constructed_area=payload.constructed_area,
        constructed_areaunit=payload.constructed_areaunit,
        super_area=payload.super_area,
        superarea_unit=payload.superarea_unit,
        carpet_area=payload.carpet_area,
        carpetarea_unit=payload.carpetarea_unit,
        noof_bhk=payload.noof_bhk,
        constructed_floors=payload.constructed_floors,
        noof_floors=payload.noof_floors,
        property_which_floors=payload.property_which_floors,
        boundary=payload.boundary,
        room=payload.room,
        office=payload.office,
        kitchen=payload.kitchen,
        toilet=payload.toilet,
        baathroom=payload.baathroom,
        balcony=payload.balcony,
        shade=payload.shade,
        machinery_plant=payload.machinery_plant,
        garage_parking=payload.garage_parking,
        width_facing_road=payload.width_facing_road,
        facing=payload.facing,
        flooring=payload.flooring,
        corner=payload.corner,
        clu=payload.clu,
        clu_type=payload.clu_type,
        feature_furnished=payload.feature_furnished,
        furnished_type=payload.furnished_type,
        featurepowerbackup=payload.featurepowerbackup,
        feature_watersupply=payload.feature_watersupply,
        feature_lift=payload.feature_lift,
        feature_park=payload.feature_park,
        feature_ownparking=payload.feature_ownparking,
        feature_visitparking=payload.feature_visitparking,
        feature_intercomfac=payload.feature_intercomfac,
        feature_clubhosue=payload.feature_clubhosue,
        feature_swimming=payload.feature_swimming,
        feature_fitness=payload.feature_fitness,
        feature_gatedcomm=payload.feature_gatedcomm,
        feature_security=payload.feature_security,
        feature_electricityconnection=payload.feature_electricityconnection,
        nearby_atm=payload.nearby_atm,
        nearby_childchehe=payload.nearby_childchehe,
        nearby_shoppingmall=payload.nearby_shoppingmall,
        nearby_hospital=payload.nearby_hospital,
        nearby_school=payload.nearby_school,
        nearby_multiplex=payload.nearby_multiplex,
        nearby_departmental=payload.nearby_departmental,
        project_name=payload.project_name,
        description=payload.description,
        images=payload.images,
        images_order=payload.images_order,
        video=payload.video,
        verified_status=0,
        is_active=0,
        sold_status=0,
        recyclebin_status=0,
        live_request_sent=0,
    )
    db.add(tbl_prop)
    await db.flush()

    # If PG details present, insert into tbl_payingguest
    if payload.property_type == 3 and payload.pg_details:
        pg_row = TblPayingGuest(
            property_id=tbl_prop.property_id,
            pg_name=payload.pg_details.pg_name,
            available_category=payload.pg_details.available_category,
            gender=payload.pg_details.gender,
            room_type=payload.pg_details.room_type,
            food_option=payload.pg_details.food_option,
            food_type=payload.pg_details.food_type,
            meal_type=payload.pg_details.meal_type,
            notice_period=payload.pg_details.notice_period,
            electrical_charges=payload.pg_details.electrical_charges,
            smoking=payload.pg_details.smoking,
            alcohol=payload.pg_details.alcohol,
            attached_bathroom=payload.pg_details.attached_bathroom,
            attached_balcony=payload.pg_details.attached_balcony,
            common_area=payload.pg_details.common_area,
            amenities=payload.pg_details.amenities,
        )
        db.add(pg_row)

    await db.commit()
    await db.refresh(tbl_prop)
    return tbl_prop


async def get_tbl_properties_hub(
    tab: str,
    search: Optional[str],
    page: int,
    limit: int,
    db: AsyncSession,
) -> dict:
    """Fetches paginated tbl_property listings mapped to the 7 sidebar queues."""
    from app.models.properties import TblProperty
    from sqlalchemy import or_, desc, func

    stmt = select(TblProperty)

    # Filter by Tab
    if tab == "new_assign":
        stmt = stmt.where(
            TblProperty.verified_status == 0,
            TblProperty.is_active == 0,
            TblProperty.recyclebin_status == 0,
            TblProperty.delete_request_sent == 0,
        )
    elif tab == "verify_live":
        stmt = stmt.where(
            TblProperty.verified_status == 1,
            TblProperty.is_active == 1,
            TblProperty.recyclebin_status == 0,
            TblProperty.sold_status == 0,
        )
    elif tab == "verification_done":
        stmt = stmt.where(
            TblProperty.verified_status == 1,
            TblProperty.is_active == 0,
            TblProperty.recyclebin_status == 0,
        )
    elif tab == "expired":
        stmt = stmt.where(
            or_(
                TblProperty.sold_status == 2,
                (TblProperty.expiarydate != None) & (TblProperty.expiarydate < datetime.now(timezone.utc)),
            ),
            TblProperty.recyclebin_status == 0,
        )
    elif tab == "deleted":
        stmt = stmt.where(
            or_(
                TblProperty.recyclebin_status == 1,
                TblProperty.delete_request_sent == 1,
            )
        )
    elif tab == "sold":
        stmt = stmt.where(
            or_(
                TblProperty.sold_status == 1,
                TblProperty.sold_request_sent == 1,
            )
        )
    elif tab == "request_live":
        stmt = stmt.where(
            TblProperty.live_request_sent == 1,
            TblProperty.recyclebin_status == 0,
        )

    # Optional search
    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                TblProperty.propertyid_no.ilike(term),
                TblProperty.source_owner_name.ilike(term),
                TblProperty.source_owner_mobile.ilike(term),
                TblProperty.sublocality_address.ilike(term),
                TblProperty.project_name.ilike(term),
            )
        )

    # Total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    # Pagination
    offset = (page - 1) * limit
    stmt = stmt.order_by(desc(TblProperty.property_id)).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    items = []
    for r in rows:
        type_str = "Rent" if r.property_type == 1 else ("Sale" if r.property_type == 2 else "PG")
        title = r.project_name or r.sublocality_address or f"{type_str} Property in Alwar"
        items.append({
            "property_id": r.property_id,
            "propertyid_no": r.propertyid_no,
            "property_type": r.property_type,
            "looking_type": r.looking_type,
            "looking_subcat_type": r.looking_subcat_type,
            "title": title,
            "expected_price": float(r.expected_price),
            "city_id": r.city_id,
            "sublocality_address": r.sublocality_address,
            "location": r.location,
            "source_owner_name": r.source_owner_name,
            "source_owner_mobile": r.source_owner_mobile,
            "verified_status": r.verified_status,
            "is_active": r.is_active,
            "sold_status": r.sold_status,
            "recyclebin_status": r.recyclebin_status,
            "assigned_user_id": r.assigned_user_id,
            "live_request_sent": r.live_request_sent,
            "delete_request_sent": r.delete_request_sent,
            "sold_request_sent": r.sold_request_sent,
            "created_date": r.created_date.isoformat() if r.created_date else None,
            "images": r.images,
        })

    return {
        "total": total,
        "tab": tab,
        "page": page,
        "limit": limit,
        "items": items,
    }


async def get_tbl_property_by_id(property_id: int, db: AsyncSession) -> Optional[dict]:
    """Retrieves full 124-column details + PG details for a property."""
    from app.models.properties import TblProperty, TblPayingGuest
    
    stmt = select(TblProperty).where(TblProperty.property_id == property_id)
    res = await db.execute(stmt)
    prop = res.scalar_one_or_none()
    if not prop:
        return None

    pg_stmt = select(TblPayingGuest).where(TblPayingGuest.property_id == prop.property_id)
    pg_res = await db.execute(pg_stmt)
    pg = pg_res.scalar_one_or_none()

    data = {c.name: getattr(prop, c.name) for c in prop.__table__.columns}
    # Convert datetimes and Decimals
    for k, v in data.items():
        if isinstance(v, datetime):
            data[k] = v.isoformat()
        elif hasattr(v, "__float__"):
            data[k] = float(v)

    if pg:
        pg_data = {c.name: getattr(pg, c.name) for c in pg.__table__.columns}
        for k, v in pg_data.items():
            if isinstance(v, datetime):
                pg_data[k] = v.isoformat()
        data["pg_details"] = pg_data
    else:
        data["pg_details"] = None

    return data


async def update_tbl_property(
    property_id: int,
    payload: "TblPropertyUpdateRequest",
    db: AsyncSession,
) -> Optional[dict]:
    """Updates property fields with conditional logic."""
    from app.models.properties import TblProperty
    stmt = select(TblProperty).where(TblProperty.property_id == property_id)
    prop = (await db.execute(stmt)).scalar_one_or_none()
    if not prop:
        return None

    update_dict = payload.model_dump(exclude_unset=True, exclude={"pg_details"})
    for k, v in update_dict.items():
        if hasattr(prop, k):
            setattr(prop, k, v)
    prop.modified_date = datetime.now(timezone.utc)

    await db.commit()
    return await get_tbl_property_by_id(property_id, db)


async def update_tbl_property_status(
    property_id: int,
    payload: "TblPropertyStatusUpdateRequest",
    db: AsyncSession,
) -> Optional[dict]:
    """Updates status flags (assigned staff, verified, live, sold, recycle)."""
    from app.models.properties import TblProperty
    stmt = select(TblProperty).where(TblProperty.property_id == property_id)
    prop = (await db.execute(stmt)).scalar_one_or_none()
    if not prop:
        return None

    status_dict = payload.model_dump(exclude_unset=True)
    if "assigned_user_id" in status_dict:
        prop.assigned_user_id = status_dict["assigned_user_id"]
        prop.assigned_user_date_time = datetime.now(timezone.utc)
    if "verified_status" in status_dict:
        prop.verified_status = status_dict["verified_status"]
    if "is_active" in status_dict:
        prop.is_active = status_dict["is_active"]
    if "sold_status" in status_dict:
        prop.sold_status = status_dict["sold_status"]
    if "sold_request_sent" in status_dict:
        prop.sold_request_sent = status_dict["sold_request_sent"]
    if "delete_request_sent" in status_dict:
        prop.delete_request_sent = status_dict["delete_request_sent"]
    if "recyclebin_status" in status_dict:
        prop.recyclebin_status = status_dict["recyclebin_status"]
        if status_dict["recyclebin_status"] == 1:
            prop.deleted_at = datetime.now(timezone.utc)
        else:
            prop.deleted_at = None
    if "recyclebin_reason" in status_dict:
        prop.recyclebin_reason = status_dict["recyclebin_reason"]
    if "live_request_sent" in status_dict:
        prop.live_request_sent = status_dict["live_request_sent"]

    prop.modified_date = datetime.now(timezone.utc)
    await db.commit()
    return await get_tbl_property_by_id(property_id, db)
