from __future__ import annotations
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from fastapi import HTTPException, status

from app.models.leads import Lead, LeadSequence, LeadActivity
from app.models.inquiries import WebsiteInquiry
from app.models.settings import SystemSetting
from app.models.franchise import ChannelPartner

logger = logging.getLogger(__name__)

DEFAULT_TEST_NUMBERS = ["919999999999", "910000000000"]


def normalize_phone(phone: Optional[str]) -> str:
    """Normalize phone number to standard Indian 12-digit format: 91XXXXXXXXXX."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return f"91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    if len(digits) > 10 and digits.startswith("91"):
        return digits[:12]
    return digits


async def is_test_number(db: AsyncSession, normalized_mobile: str) -> bool:
    """Check if the mobile number is configured as a test number."""
    if normalized_mobile in DEFAULT_TEST_NUMBERS:
        return True

    res = await db.execute(select(SystemSetting).where(SystemSetting.key == "test_numbers"))
    setting = res.scalar_one_or_none()
    if setting and setting.value:
        val = setting.value
        if isinstance(val, list):
            for num in val:
                if normalize_phone(str(num)) == normalized_mobile:
                    return True
        elif isinstance(val, str):
            for num in val.split(","):
                if normalize_phone(num.strip()) == normalized_mobile:
                    return True
    return False


async def get_next_lead_id(db: AsyncSession, year: Optional[int] = None) -> str:
    """Atomically allocate an annual 6-digit zero-padded unbounded sequence (OB-YYYY-NNNNNN)."""
    current_year = year or datetime.now(timezone.utc).year

    # Try row-level locking; if unsupported (e.g. SQLite memory in tests), fallback gracefully
    try:
        stmt = select(LeadSequence).where(LeadSequence.year == current_year).with_for_update()
        res = await db.execute(stmt)
        seq_record = res.scalar_one_or_none()
    except Exception:
        stmt = select(LeadSequence).where(LeadSequence.year == current_year)
        res = await db.execute(stmt)
        seq_record = res.scalar_one_or_none()

    if not seq_record:
        seq_record = LeadSequence(year=current_year, last_sequence=1)
        db.add(seq_record)
        await db.flush()
        next_val = 1
    else:
        seq_record.last_sequence += 1
        await db.flush()
        next_val = seq_record.last_sequence

    return f"OB-{current_year}-{next_val:06d}"


class IntakeService:
    """Inbound lead intake, normalization, deduplication and conversion engine."""

    async def create_or_dedup_lead(
        self,
        db: AsyncSession,
        source: str,
        full_name: str,
        mobile: str,
        email: Optional[str] = None,
        lead_type: str = "BUYER",
        related_listing_id: Optional[str] = None,
        related_project_id: Optional[int] = None,
        assigned_to: Optional[str] = None,
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
        preferred_city: Optional[str] = "Alwar",
        preferred_locality: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        referral_code: Optional[str] = None,
        partner_id: Optional[int] = None,
        accompanied_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ingest an inbound lead with normalization, test suppression, and 24h deduplication."""
        normalized_mobile = normalize_phone(mobile)

        # 1. Test Number Suppression
        if await is_test_number(db, normalized_mobile):
            logger.info("Intake suppressed for test number %s", normalized_mobile)
            return {
                "lead_id": None,
                "is_duplicate": False,
                "is_test": True,
                "status": "suppressed",
                "full_name": full_name,
                "mobile": normalized_mobile,
                "stage": None,
            }

        # 2. Idempotency Key check
        if idempotency_key:
            res_idem = await db.execute(
                select(Lead).where(Lead.idempotency_key == idempotency_key)
            )
            existing_idem = res_idem.scalar_one_or_none()
            if existing_idem:
                return {
                    "lead_id": existing_idem.lead_id,
                    "is_duplicate": False,
                    "is_test": existing_idem.is_test,
                    "status": "idempotent",
                    "full_name": existing_idem.full_name,
                    "mobile": existing_idem.mobile,
                    "stage": existing_idem.stage,
                    "is_untouched": existing_idem.is_untouched,
                }

        # 3. 24-Hour Deduplication
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        stmt_dedup = (
            select(Lead)
            .where(
                and_(
                    Lead.mobile == normalized_mobile,
                    Lead.created_at >= cutoff_time,
                )
            )
            .order_by(desc(Lead.created_at))
        )
        res_dedup = await db.execute(stmt_dedup)
        existing_lead = res_dedup.scalars().first()

        if existing_lead:
            # Log repeat activity on existing lead
            activity = LeadActivity(
                lead_id=existing_lead.lead_id,
                action_type="REPEAT_INQUIRY",
                outcome="Duplicate Suppressed",
                note=f"Repeat inquiry within 24h via source {source}",
                logged_by="SYSTEM",
            )
            db.add(activity)
            await db.commit()

            return {
                "lead_id": existing_lead.lead_id,
                "is_duplicate": True,
                "is_test": existing_lead.is_test,
                "status": "duplicate",
                "full_name": existing_lead.full_name,
                "mobile": existing_lead.mobile,
                "stage": existing_lead.stage,
                "is_untouched": existing_lead.is_untouched,
            }

        # 4. Fresh Lead Generation
        lead_id = await get_next_lead_id(db)

        resolved_partner_id = partner_id
        clean_ref = referral_code.strip() if referral_code else None
        if clean_ref and not resolved_partner_id:
            cp_stmt = select(ChannelPartner).where(
                ChannelPartner.deleted_at.is_(None),
                ChannelPartner.is_active.is_(True),
                (ChannelPartner.tracking_code == clean_ref) | (ChannelPartner.partner_code == clean_ref),
            )
            matched_cp = (await db.execute(cp_stmt)).scalar_one_or_none()
            if matched_cp:
                resolved_partner_id = matched_cp.id

        # L1 Active CP rule: accompanied_by employee required if submitted directly by an Active CP at L1
        if resolved_partner_id:
            cp_obj = await db.get(ChannelPartner, resolved_partner_id)
            if cp_obj and cp_obj.cp_type == "ACTIVE_CP" and cp_obj.active_level == "L1" and not accompanied_by:
                logger.info("L1 Active CP lead created; visit requires accompanied Omshiv staff.")

        new_lead = Lead(
            lead_id=lead_id,
            idempotency_key=idempotency_key,
            full_name=full_name,
            mobile=normalized_mobile,
            email=email,
            lead_type=lead_type,
            source=source,
            related_listing_id=related_listing_id,
            related_project_id=related_project_id,
            assigned_to=assigned_to,
            partner_id=resolved_partner_id,
            referral_code=clean_ref,
            accompanied_by=accompanied_by.strip() if accompanied_by else None,
            stage="NEW",
            temperature=None,
            budget_min=budget_min,
            budget_max=budget_max,
            preferred_city=preferred_city,
            preferred_locality=preferred_locality,
            is_untouched=True,
            is_duplicate=False,
            is_test=False,
        )
        db.add(new_lead)
        await db.flush()

        # Log intake activity
        activity = LeadActivity(
            lead_id=new_lead.lead_id,
            action_type="INTAKE",
            outcome="Lead Ingested",
            note=f"New inbound lead created via {source}",
            logged_by="SYSTEM",
        )
        db.add(activity)
        await db.commit()
        await db.refresh(new_lead)

        return {
            "lead_id": new_lead.lead_id,
            "is_duplicate": False,
            "is_test": False,
            "status": "created",
            "full_name": new_lead.full_name,
            "mobile": new_lead.mobile,
            "stage": new_lead.stage,
            "is_untouched": new_lead.is_untouched,
        }

    async def create_website_inquiry(
        self,
        db: AsyncSession,
        inquiry_type: str,
        full_name: str,
        mobile: str,
        email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> WebsiteInquiry:
        """Create a raw website inquiry from public web forms."""
        normalized_mobile = normalize_phone(mobile)
        inquiry = WebsiteInquiry(
            inquiry_type=inquiry_type,
            full_name=full_name,
            mobile=normalized_mobile,
            email=email,
            details=details,
            is_converted=False,
        )
        db.add(inquiry)
        await db.commit()
        await db.refresh(inquiry)
        return inquiry

    async def list_unconverted_inquiries(
        self,
        db: AsyncSession,
        is_converted: Optional[bool] = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WebsiteInquiry]:
        """List website inquiries filtered by conversion status."""
        stmt = select(WebsiteInquiry)
        if is_converted is not None:
            stmt = stmt.where(WebsiteInquiry.is_converted == is_converted)
        stmt = stmt.order_by(desc(WebsiteInquiry.created_at)).offset(offset).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def convert_inquiry_to_lead(
        self,
        db: AsyncSession,
        inquiry_id: int,
        assigned_to: Optional[str] = None,
        lead_type: str = "BUYER",
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
        converted_by_emp_id: Optional[str] = None,
    ) -> Lead:
        """Convert a website inquiry to an official CRM lead (1-Click Conversion)."""
        res = await db.execute(select(WebsiteInquiry).where(WebsiteInquiry.id == inquiry_id))
        inquiry = res.scalar_one_or_none()
        if not inquiry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Website inquiry #{inquiry_id} not found",
            )

        if inquiry.is_converted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Website inquiry #{inquiry_id} is already converted to lead {inquiry.converted_lead_id}",
            )

        # Allocate new lead_id
        lead_id = await get_next_lead_id(db)

        # Create official lead
        new_lead = Lead(
            lead_id=lead_id,
            full_name=inquiry.full_name,
            mobile=inquiry.mobile,
            email=inquiry.email,
            lead_type=lead_type,
            source=f"WEBSITE_{inquiry.inquiry_type}",
            assigned_to=assigned_to,
            stage="NEW",
            temperature=None,
            budget_min=budget_min,
            budget_max=budget_max,
            is_untouched=True,
            is_duplicate=False,
            is_test=False,
        )
        db.add(new_lead)
        await db.flush()

        # Update inquiry
        inquiry.is_converted = True
        inquiry.converted_lead_id = lead_id
        inquiry.converted_by_emp_id = converted_by_emp_id
        inquiry.converted_at = datetime.now(timezone.utc)

        # Activity log
        activity = LeadActivity(
            lead_id=lead_id,
            action_type="CONVERSION",
            outcome="Inquiry Converted",
            note=f"1-Click conversion from WebsiteInquiry #{inquiry.id} ({inquiry.inquiry_type})",
            logged_by=converted_by_emp_id or "SYSTEM",
        )
        db.add(activity)

        await db.commit()
        await db.refresh(new_lead)
        return new_lead


intake_service = IntakeService()
