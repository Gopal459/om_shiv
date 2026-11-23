import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.property_master import (
    PropertyMasterGroup,
    PropertyMasterOption,
    PincodeMaster,
)

logger = logging.getLogger(__name__)

# In-memory cache for public schema
_schema_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None


DEFAULT_MASTER_DATA = {
    "FACING": [
        ("EAST", "East", 1, []),
        ("NORTH", "North", 2, []),
        ("NORTH_EAST", "North-East", 3, []),
        ("NORTH_WEST", "North-West", 4, []),
        ("SOUTH", "South", 5, []),
        ("SOUTH_EAST", "South-East", 6, []),
        ("SOUTH_WEST", "South-West", 7, []),
        ("WEST", "West", 8, []),
    ],
    "AREA_UNITS": [
        ("SQFT", "Sq.ft", 1, []),
        ("SQYARD", "Sq.yards", 2, []),
        ("SQMETER", "Sq.meter", 3, []),
        ("ACRE", "Acre", 4, [3, 4]),
        ("BIGHA", "Bigha", 5, [3]),  # Scoped specifically to Agriculture (3)
        ("HECTARE", "Hectare", 6, [3]),
    ],
    "FLOORING": [
        ("VITRIFIED", "Vitrified", 1, []),
        ("MARBLE", "Marble", 2, []),
        ("WOODEN", "Wooden", 3, []),
        ("CERAMIC", "Ceramic", 4, []),
        ("GRANITE", "Granite", 5, []),
        ("MOSAIC", "Mosaic", 6, []),
        ("CEMENT", "Cement", 7, []),
    ],
    "POSSESSION_STATUS": [
        ("READY_TO_MOVE", "Ready to Move", 1, []),
        ("UNDER_CONSTRUCTION", "Under Construction", 2, []),
    ],
    "OWNERSHIP_TYPE": [
        ("FREEHOLD", "Freehold", 1, []),
        ("LEASEHOLD", "Leasehold", 2, []),
        ("POWER_OF_ATTORNEY", "Power of Attorney", 3, []),
        ("COOPERATIVE_SOCIETY", "Co-operative Society", 4, []),
    ],
    "RENT_ALLOWED_FOR": [
        ("ANY", "Any", 1, []),
        ("FAMILY", "Family", 2, []),
        ("BACHELORS", "Bachelors", 3, []),
        ("COMPANY_LEASE", "Company Lease", 4, []),
    ],
    "FURNITURE_ITEMS": [
        ("BEDS", "Beds", 1, []),
        ("WARDROBES", "Wardrobes", 2, []),
        ("TV", "TV", 3, []),
        ("FRIDGE", "Fridge", 4, []),
        ("SOFA", "Sofa", 5, []),
        ("WASHING_MACHINE", "Washing Machine", 6, []),
        ("AC", "AC", 7, []),
        ("DINING_TABLE", "Dining Table", 8, []),
        ("GEYSER", "Geyser", 9, []),
        ("RO_WATER", "RO Water", 10, []),
    ],
    "AMENITIES": [
        ("LIFT", "Lift", 1, []),
        ("SECURITY", "Security / Fire Alarm", 2, []),
        ("PARK", "Park", 3, []),
        ("VISITOR_PARKING", "Visitor Parking", 4, []),
        ("POWER_BACKUP", "Power Backup", 5, []),
        ("WATER_STORAGE", "Water Storage", 6, []),
        ("CLUB_HOUSE", "Club House / Community Center", 7, []),
        ("SWIMMING_POOL", "Swimming Pool", 8, []),
        ("GYM", "Fitness Centre / Gym", 9, []),
    ],
}

DEFAULT_PINCODES = [
    ("301001", "Alwar", "Alwar", "Rajasthan", True),
    ("301019", "Bhiwadi", "Alwar", "Rajasthan", True),
    ("302001", "Jaipur", "Jaipur", "Rajasthan", True),
    ("122001", "Gurgaon", "Gurgaon", "Haryana", True),
]


async def seed_property_masters(db: AsyncSession) -> None:
    """Idempotently seeds all master groups, options, and initial pincodes."""
    for group_code, options in DEFAULT_MASTER_DATA.items():
        stmt = select(PropertyMasterGroup).where(PropertyMasterGroup.code == group_code)
        res = await db.execute(stmt)
        group = res.scalar_one_or_none()
        if not group:
            group = PropertyMasterGroup(code=group_code, name=group_code.replace("_", " ").title())
            db.add(group)
            await db.flush()

        # Seed options for group
        opt_stmt = select(PropertyMasterOption.code).where(PropertyMasterOption.group_id == group.id)
        opt_res = await db.execute(opt_stmt)
        existing_codes = set(opt_res.scalars().all())

        for opt_code, label, order, categories in options:
            if opt_code not in existing_codes:
                opt = PropertyMasterOption(
                    group_id=group.id,
                    code=opt_code,
                    label=label,
                    display_order=order,
                    applicable_categories=categories,
                )
                db.add(opt)

    for pincode, city, district, state, serviceable in DEFAULT_PINCODES:
        p_stmt = select(PincodeMaster).where(PincodeMaster.pincode == pincode)
        p_res = await db.execute(p_stmt)
        if not p_res.scalar_one_or_none():
            pin = PincodeMaster(
                pincode=pincode,
                city=city,
                district=district,
                state=state,
                is_serviceable=serviceable,
            )
            db.add(pin)

    await db.commit()
    clear_schema_cache()


def clear_schema_cache() -> None:
    global _schema_cache
    _schema_cache = None


async def get_property_schema(db: AsyncSession) -> Dict[str, List[Dict[str, Any]]]:
    """Retrieves all active property options grouped by master code."""
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache

    stmt = select(PropertyMasterGroup).where(PropertyMasterGroup.deleted_at.is_(None)).order_by(PropertyMasterGroup.id)
    res = await db.execute(stmt)
    groups = res.scalars().all()

    schema: Dict[str, List[Dict[str, Any]]] = {}
    for g in groups:
        options_list = []
        for opt in g.options:
            if opt.is_active and opt.deleted_at is None:
                options_list.append(
                    {
                        "id": opt.id,
                        "code": opt.code,
                        "label": opt.label,
                        "display_order": opt.display_order,
                        "applicable_categories": opt.applicable_categories,
                    }
                )
        schema[g.code] = options_list

    _schema_cache = schema
    return schema


async def add_master_option(
    db: AsyncSession,
    group_code: str,
    code: str,
    label: str,
    display_order: int = 0,
    applicable_categories: Optional[List[int]] = None,
) -> PropertyMasterOption:
    """Dynamically adds a new option to a master group without hardcoded changes."""
    stmt = select(PropertyMasterGroup).where(PropertyMasterGroup.code == group_code.upper())
    res = await db.execute(stmt)
    group = res.scalar_one_or_none()
    if not group:
        group = PropertyMasterGroup(code=group_code.upper(), name=group_code.replace("_", " ").title())
        db.add(group)
        await db.flush()

    option = PropertyMasterOption(
        group_id=group.id,
        code=code.upper(),
        label=label,
        display_order=display_order,
        applicable_categories=applicable_categories or [],
        is_active=True,
    )
    db.add(option)
    await db.commit()
    await db.refresh(option)
    clear_schema_cache()
    return option


async def get_pincode_details(db: AsyncSession, pincode: str) -> Optional[PincodeMaster]:
    """Validates and retrieves pincode details."""
    stmt = select(PincodeMaster).where(
        and_(PincodeMaster.pincode == pincode.strip(), PincodeMaster.is_serviceable == True)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()
