import logging
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.properties import Property

logger = logging.getLogger(__name__)


async def process_property_expiries(db: AsyncSession) -> Dict[str, Any]:
    """Scans all live listings whose validity has passed and deactivates them."""
    now = datetime.now(timezone.utc)
    stmt = select(Property).where(
        and_(
            Property.is_live == True,
            Property.expires_at <= now,
        )
    )
    res = await db.execute(stmt)
    expired_listings = res.scalars().all()

    for prop in expired_listings:
        prop.is_live = False
        logger.info("Property %s expired and marked not live.", prop.property_id)

    if expired_listings:
        await db.commit()

    return {"expired_count": len(expired_listings)}
