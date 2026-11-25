from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.settings import SystemSetting, AuditLog

logger = logging.getLogger(__name__)

# Master catalogue of default dynamic settings (~90 business settings)
DEFAULT_SETTINGS: List[Dict[str, Any]] = [
    # SLA Category
    {
        "key": "sla_untouched_hours",
        "value": 3,
        "data_type": "INT",
        "category": "SLA",
        "description": "Hours before an untouched lead triggers SLA breach warning",
    },
    {
        "key": "sla_escalation_hours",
        "value": 24,
        "data_type": "INT",
        "category": "SLA",
        "description": "Hours before uncontacted lead escalates to MD/Sales Head",
    },
    {
        "key": "sla_warning_threshold_minutes",
        "value": 30,
        "data_type": "INT",
        "category": "SLA",
        "description": "Minutes before SLA breach to send proactive alert to advisor",
    },
    {
        "key": "sla_first_call_target_minutes",
        "value": 15,
        "data_type": "INT",
        "category": "SLA",
        "description": "Target response time for inbound enquiry first call",
    },
    {
        "key": "sla_site_visit_followup_hours",
        "value": 2,
        "data_type": "INT",
        "category": "SLA",
        "description": "Hours after site visit completion to submit follow-up feedback",
    },
    {
        "key": "sla_unassigned_lead_alert_minutes",
        "value": 10,
        "data_type": "INT",
        "category": "SLA",
        "description": "Minutes before unassigned intake lead alerts front desk",
    },
    {
        "key": "sla_escalation_level_1_hours",
        "value": 3,
        "data_type": "INT",
        "category": "SLA",
        "description": "Hours untouched to escalate to Team Lead / Manager",
    },
    {
        "key": "sla_escalation_level_2_hours",
        "value": 12,
        "data_type": "INT",
        "category": "SLA",
        "description": "Hours untouched to escalate to Department Head",
    },
    {
        "key": "sla_escalation_level_3_hours",
        "value": 24,
        "data_type": "INT",
        "category": "SLA",
        "description": "Hours untouched to escalate to Managing Director (MD)",
    },
    # NOTIFICATION & MESSAGING Category
    {
        "key": "quiet_hours_start",
        "value": "21:00",
        "data_type": "STRING",
        "category": "NOTIFICATION",
        "description": "Daily quiet hours start time (24-hour format HH:MM)",
    },
    {
        "key": "quiet_hours_end",
        "value": "09:00",
        "data_type": "STRING",
        "category": "NOTIFICATION",
        "description": "Daily quiet hours end time (24-hour format HH:MM)",
    },
    {
        "key": "quiet_hours_enabled",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "NOTIFICATION",
        "description": "Enforce quiet hours queueing on all automated WhatsApp/SMS notifications",
    },
    {
        "key": "doubletick_low_balance_threshold",
        "value": 500,
        "data_type": "INT",
        "category": "NOTIFICATION",
        "description": "DoubleTick WhatsApp wallet low balance alert threshold in INR",
    },
    {
        "key": "doubletick_api_timeout_seconds",
        "value": 5,
        "data_type": "INT",
        "category": "NOTIFICATION",
        "description": "Timeout in seconds for DoubleTick API requests",
    },
    {
        "key": "whatsapp_template_namespace",
        "value": "omshiv_crm",
        "data_type": "STRING",
        "category": "NOTIFICATION",
        "description": "Approved Meta WhatsApp template namespace identifier",
    },
    {
        "key": "whatsapp_lead_welcome_template",
        "value": "lead_welcome_v1",
        "data_type": "STRING",
        "category": "NOTIFICATION",
        "description": "Template name for inbound lead instant welcome message",
    },
    {
        "key": "whatsapp_site_visit_scheduled_template",
        "value": "visit_scheduled_v1",
        "data_type": "STRING",
        "category": "NOTIFICATION",
        "description": "Template name for confirmed site visit notification",
    },
    {
        "key": "whatsapp_escalation_alert_template",
        "value": "sla_escalation_alert_v1",
        "data_type": "STRING",
        "category": "NOTIFICATION",
        "description": "Internal template for notifying managers of SLA breaches",
    },
    {
        "key": "sms_fallback_enabled",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "NOTIFICATION",
        "description": "Automatically dispatch SMS OTP if WhatsApp delivery fails",
    },
    {
        "key": "sms_sender_id",
        "value": "OMSHIV",
        "data_type": "STRING",
        "category": "NOTIFICATION",
        "description": "DLT approved 6-character SMS sender ID header",
    },
    # SECURITY Category
    {
        "key": "otp_expiry_seconds",
        "value": 300,
        "data_type": "INT",
        "category": "SECURITY",
        "description": "Login OTP validity duration in seconds (5 minutes default)",
    },
    {
        "key": "otp_max_attempts",
        "value": 3,
        "data_type": "INT",
        "category": "SECURITY",
        "description": "Maximum failed OTP verification attempts before session lock",
    },
    {
        "key": "otp_max_resend_per_hour",
        "value": 5,
        "data_type": "INT",
        "category": "SECURITY",
        "description": "Max OTP generation requests permitted per mobile number per hour",
    },
    {
        "key": "session_expiry_days",
        "value": 30,
        "data_type": "INT",
        "category": "SECURITY",
        "description": "Staff login session validity duration in days",
    },
    {
        "key": "jwt_access_token_expire_minutes",
        "value": 43200,
        "data_type": "INT",
        "category": "SECURITY",
        "description": "JWT access token lifespan in minutes",
    },
    {
        "key": "rate_limit_auth_requests_per_minute",
        "value": 10,
        "data_type": "INT",
        "category": "SECURITY",
        "description": "Maximum login attempts per IP per minute",
    },
    {
        "key": "rate_limit_lead_intake_per_minute",
        "value": 30,
        "data_type": "INT",
        "category": "SECURITY",
        "description": "Maximum public lead submissions per IP per minute",
    },
    {
        "key": "audit_log_retention_days",
        "value": 365,
        "data_type": "INT",
        "category": "SECURITY",
        "description": "Retention period in days for immutable audit logs before archiving",
    },
    # ROUTING & ASSIGNMENT Category
    {
        "key": "lead_routing_mode",
        "value": "STRICT_RULES_TABLE",
        "data_type": "STRING",
        "category": "ROUTING",
        "description": "Routing algorithm mode (STRICT_RULES_TABLE, ROUND_ROBIN, HYBRID)",
    },
    {
        "key": "lead_auto_assignment_enabled",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "ROUTING",
        "description": "Enable automated instant rule-based lead assignment",
    },
    {
        "key": "round_robin_fallback_enabled",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "ROUTING",
        "description": "Fallback to round-robin within team if no specific rule matches",
    },
    {
        "key": "partner_lead_protection_days",
        "value": 90,
        "data_type": "INT",
        "category": "ROUTING",
        "description": "Channel partner lead ownership protection period in days",
    },
    {
        "key": "lead_dedup_window_days",
        "value": 30,
        "data_type": "INT",
        "category": "ROUTING",
        "description": "Window in days to link duplicate enquiries to existing open lead",
    },
    {
        "key": "lead_cooldown_reassignment_days",
        "value": 14,
        "data_type": "INT",
        "category": "ROUTING",
        "description": "Days lead remains untouchable by other advisors after unqualification",
    },
    {
        "key": "lead_max_active_per_executive",
        "value": 50,
        "data_type": "INT",
        "category": "ROUTING",
        "description": "Maximum active open leads assigned to a single sales executive",
    },
    {
        "key": "assignment_workload_balancing_enabled",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "ROUTING",
        "description": "Skip executives at max lead capacity during round-robin distribution",
    },
    {
        "key": "assignment_prefer_last_advisor",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "ROUTING",
        "description": "Route returning customer to their previously assigned advisor",
    },
    {
        "key": "assignment_zone_strict_matching",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "ROUTING",
        "description": "Strictly prioritize advisors specializing in lead's requested locality",
    },
    # FINANCIAL & COMMISSION Category
    {
        "key": "commission_primary_pct",
        "value": 1.0,
        "data_type": "FLOAT",
        "category": "FINANCIAL",
        "description": "Default commission percentage on primary builder project sales",
    },
    {
        "key": "commission_secondary_pct",
        "value": 2.0,
        "data_type": "FLOAT",
        "category": "FINANCIAL",
        "description": "Default commission percentage on secondary / resale property sales",
    },
    {
        "key": "commission_commercial_pct",
        "value": 2.0,
        "data_type": "FLOAT",
        "category": "FINANCIAL",
        "description": "Default commission percentage on commercial property transactions",
    },
    {
        "key": "commission_plot_pct",
        "value": 2.0,
        "data_type": "FLOAT",
        "category": "FINANCIAL",
        "description": "Default commission percentage on residential plot/land transactions",
    },
    {
        "key": "commission_rent_days_equivalent",
        "value": 15,
        "data_type": "INT",
        "category": "FINANCIAL",
        "description": "Standard rental brokerage fee represented in days of monthly rent",
    },
    {
        "key": "rent_agreement_fee_flat",
        "value": 500,
        "data_type": "INT",
        "category": "FINANCIAL",
        "description": "Flat documentation and e-stamp fee in INR for rent agreements",
    },
    {
        "key": "tax_tds_percentage",
        "value": 5.0,
        "data_type": "FLOAT",
        "category": "FINANCIAL",
        "description": "TDS percentage deducted on partner commission payouts",
    },
    {
        "key": "tax_gst_percentage",
        "value": 18.0,
        "data_type": "FLOAT",
        "category": "FINANCIAL",
        "description": "GST percentage applied on agency brokerage service invoices",
    },
    {
        "key": "payout_min_threshold_inr",
        "value": 1000,
        "data_type": "INT",
        "category": "FINANCIAL",
        "description": "Minimum accumulated commission balance required to trigger payout",
    },
    {
        "key": "payout_cycle_day_of_month",
        "value": 10,
        "data_type": "INT",
        "category": "FINANCIAL",
        "description": "Day of month when channel partner commission disbursements process",
    },
    {
        "key": "brokerage_round_off_decimals",
        "value": 2,
        "data_type": "INT",
        "category": "FINANCIAL",
        "description": "Decimal places used for financial and commission calculations",
    },
    # RENT Category
    {
        "key": "rent_routing_threshold_inr",
        "value": 25000,
        "data_type": "INT",
        "category": "RENT",
        "description": "Monthly rent threshold separating direct contact reveal vs CP assignment",
    },
    {
        "key": "direct_tenant_daily_limit",
        "value": 5,
        "data_type": "INT",
        "category": "RENT",
        "description": "Maximum direct tenant number reveals per day per unverified web user",
    },
    {
        "key": "rent_security_deposit_default_months",
        "value": 2,
        "data_type": "INT",
        "category": "RENT",
        "description": "Standard security deposit required in multiples of monthly rent",
    },
    {
        "key": "rent_lock_in_period_months",
        "value": 11,
        "data_type": "INT",
        "category": "RENT",
        "description": "Standard agreement lock-in duration in months",
    },
    {
        "key": "rent_escalation_clause_annual_pct",
        "value": 5.0,
        "data_type": "FLOAT",
        "category": "RENT",
        "description": "Standard annual rent escalation rate percentage",
    },
    {
        "key": "rent_inspection_advance_notice_days",
        "value": 2,
        "data_type": "INT",
        "category": "RENT",
        "description": "Days of advance notice required before routine landlord property visit",
    },
    # MATCHING & AI Category
    {
        "key": "matching_auto_dispatch_requires_approval",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "MATCHING",
        "description": "Require advisor 1-tap approval before dispatching AI property matches",
    },
    {
        "key": "matching_min_budget_tolerance_pct",
        "value": 10.0,
        "data_type": "FLOAT",
        "category": "MATCHING",
        "description": "Lower budget tolerance percentage when searching buyer property matches",
    },
    {
        "key": "matching_max_budget_tolerance_pct",
        "value": 15.0,
        "data_type": "FLOAT",
        "category": "MATCHING",
        "description": "Upper budget tolerance percentage when searching buyer property matches",
    },
    {
        "key": "matching_default_radius_km",
        "value": 5.0,
        "data_type": "FLOAT",
        "category": "MATCHING",
        "description": "Default search radius in km around preferred micro-market",
    },
    {
        "key": "matching_min_score_threshold",
        "value": 70,
        "data_type": "INT",
        "category": "MATCHING",
        "description": "Minimum compatibility score (0-100) to consider a property a viable match",
    },
    {
        "key": "matching_max_daily_recommendations_per_buyer",
        "value": 3,
        "data_type": "INT",
        "category": "MATCHING",
        "description": "Maximum match cards sent to a buyer per day to prevent spam",
    },
    {
        "key": "ai_calling_provider",
        "value": "bland_ai",
        "data_type": "STRING",
        "category": "MATCHING",
        "description": "Active AI voice agent vendor adapter (bland_ai, retell, elevenlabs)",
    },
    {
        "key": "ai_voice_speed",
        "value": 1.0,
        "data_type": "FLOAT",
        "category": "MATCHING",
        "description": "Speech rate multiplier for outbound AI voice qualification calls",
    },
    {
        "key": "ai_call_recording_enabled",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "MATCHING",
        "description": "Record AI voice qualification calls for audit and training review",
    },
    # PROPERTY & PUBLIC PORTAL Category
    {
        "key": "default_public_price_mode",
        "value": "BAND",
        "data_type": "STRING",
        "category": "PROPERTY",
        "description": "Default public pricing display mode (BAND, EXACT, ON_REQUEST)",
    },
    {
        "key": "featured_listing_max_count",
        "value": 12,
        "data_type": "INT",
        "category": "PROPERTY",
        "description": "Maximum number of curated featured listings displayed on homepage",
    },
    {
        "key": "watermark_enabled",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "PROPERTY",
        "description": "Automatically apply Omshiv Buildvision watermark to property media",
    },
    {
        "key": "watermark_text",
        "value": "Omshiv Buildvision & Propira",
        "data_type": "STRING",
        "category": "PROPERTY",
        "description": "Watermark overlay label applied to property photographs",
    },
    {
        "key": "photo_upload_max_count",
        "value": 25,
        "data_type": "INT",
        "category": "PROPERTY",
        "description": "Maximum number of photographs permitted per property listing",
    },
    {
        "key": "video_upload_max_size_mb",
        "value": 100,
        "data_type": "INT",
        "category": "PROPERTY",
        "description": "Maximum video walkthrough upload size in megabytes",
    },
    {
        "key": "property_verification_sla_hours",
        "value": 48,
        "data_type": "INT",
        "category": "PROPERTY",
        "description": "Hours within which field team must verify self-posted listings",
    },
    {
        "key": "property_listing_validity_days",
        "value": 180,
        "data_type": "INT",
        "category": "PROPERTY",
        "description": "Days before an active listing prompts owner for availability re-confirmation",
    },
    {
        "key": "allow_unverified_public_search",
        "value": False,
        "data_type": "BOOLEAN",
        "category": "PROPERTY",
        "description": "Display unverified listings in public portal search results",
    },
    {
        "key": "default_area_unit",
        "value": "SQFT",
        "data_type": "STRING",
        "category": "PROPERTY",
        "description": "Primary area unit for display across listings (SQFT, SQYD, BIGHA)",
    },
    {
        "key": "supported_area_units",
        "value": ["SQFT", "SQYD", "BIGHA", "GAJ", "ACRE"],
        "data_type": "JSON",
        "category": "PROPERTY",
        "description": "Master list of accepted land and floor measurement units",
    },
    # CHANNEL PARTNER Category
    {
        "key": "cp_tier_associate_min_deals",
        "value": 0,
        "data_type": "INT",
        "category": "CHANNEL_PARTNER",
        "description": "Deals required for Associate partner tier",
    },
    {
        "key": "cp_tier_partner_min_deals",
        "value": 3,
        "data_type": "INT",
        "category": "CHANNEL_PARTNER",
        "description": "Deals required to qualify for Partner tier",
    },
    {
        "key": "cp_tier_premium_min_deals",
        "value": 10,
        "data_type": "INT",
        "category": "CHANNEL_PARTNER",
        "description": "Deals required to qualify for Premium partner tier",
    },
    {
        "key": "cp_kyc_verification_required",
        "value": True,
        "data_type": "BOOLEAN",
        "category": "CHANNEL_PARTNER",
        "description": "Require RERA / Aadhaar / PAN verification before partner deal payout",
    },
    {
        "key": "cp_badge_validity_months",
        "value": 12,
        "data_type": "INT",
        "category": "CHANNEL_PARTNER",
        "description": "Validity period of certified partner badge before renewal audit",
    },
    {
        "key": "cp_referral_bonus_inr",
        "value": 5000,
        "data_type": "INT",
        "category": "CHANNEL_PARTNER",
        "description": "Flat referral bonus paid to partner for recruiting an active partner",
    },
    {
        "key": "cp_show_seller_contact",
        "value": False,
        "data_type": "BOOLEAN",
        "category": "CHANNEL_PARTNER",
        "description": "Strict security policy: Never expose seller phone numbers to CP portal",
    },
    {
        "key": "cp_show_reserve_price",
        "value": False,
        "data_type": "BOOLEAN",
        "category": "CHANNEL_PARTNER",
        "description": "Strict security policy: Never expose minimum reserve price to CP portal",
    },
    # GENERAL & COMPANY Category
    {
        "key": "company_legal_name",
        "value": "Omshiv Buildvision Pvt Ltd",
        "data_type": "STRING",
        "category": "GENERAL",
        "description": "Official registered corporate legal entity name",
    },
    {
        "key": "company_brand_name",
        "value": "Omshiv Buildvision & Propira",
        "data_type": "STRING",
        "category": "GENERAL",
        "description": "Customer-facing marketing brand identity",
    },
    {
        "key": "company_support_email",
        "value": "support@omshiv.com",
        "data_type": "STRING",
        "category": "GENERAL",
        "description": "Corporate customer service and grievance email address",
    },
    {
        "key": "company_support_phone",
        "value": "+919829012345",
        "data_type": "STRING",
        "category": "GENERAL",
        "description": "Primary customer service helpline phone number",
    },
    {
        "key": "company_headquarters_city",
        "value": "Kota",
        "data_type": "STRING",
        "category": "GENERAL",
        "description": "Headquarters municipality and principal place of business",
    },
    {
        "key": "default_state",
        "value": "Rajasthan",
        "data_type": "STRING",
        "category": "GENERAL",
        "description": "Default jurisdiction state for property taxation and contracts",
    },
    {
        "key": "currency_symbol",
        "value": "₹",
        "data_type": "STRING",
        "category": "GENERAL",
        "description": "Primary currency glyph for UI formatting",
    },
    {
        "key": "currency_code",
        "value": "INR",
        "data_type": "STRING",
        "category": "GENERAL",
        "description": "ISO 4217 standard currency code",
    },
    {
        "key": "maintenance_mode",
        "value": False,
        "data_type": "BOOLEAN",
        "category": "GENERAL",
        "description": "Toggle system-wide maintenance mode for scheduled upgrades",
    },
]


async def seed_system_settings(db: AsyncSession) -> int:
    """Idempotently seeds all default system settings into the database."""
    stmt = select(SystemSetting.key)
    res = await db.execute(stmt)
    existing_keys = set(res.scalars().all())

    inserted_count = 0
    now = datetime.now(timezone.utc)
    for setting_dict in DEFAULT_SETTINGS:
        if setting_dict["key"] not in existing_keys:
            setting = SystemSetting(
                key=setting_dict["key"],
                value=setting_dict["value"],
                data_type=setting_dict["data_type"],
                category=setting_dict["category"],
                description=setting_dict["description"],
                updated_by="SYSTEM",
                updated_at=now,
            )
            db.add(setting)
            inserted_count += 1

    if inserted_count > 0:
        await db.commit()
        logger.info(f"Seeded {inserted_count} new system settings into system_settings table")

    return inserted_count


class SettingsService:
    """High-performance service managing dynamic system settings with caching and audit ledger."""

    def __init__(self) -> None:
        self._memory_cache: Dict[str, Any] = {}
        self._memory_cache_all: Optional[List[Dict[str, Any]]] = None

    def clear_cache(self, key: Optional[str] = None) -> None:
        """Clear memory cache for a specific key or all keys."""
        if key:
            self._memory_cache.pop(key, None)
        else:
            self._memory_cache.clear()
        self._memory_cache_all = None

    def _validate_and_cast(self, value: Any, data_type: str) -> Any:
        """Validate value format against data_type and cast cleanly."""
        dt = data_type.upper()
        if dt == "INT":
            if isinstance(value, bool):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid integer value: boolean provided",
                )
            try:
                if isinstance(value, str):
                    val = int(value.strip())
                elif isinstance(value, (int, float)):
                    if isinstance(value, float) and not value.is_integer():
                        raise ValueError()
                    val = int(value)
                else:
                    raise ValueError()
                return val
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid integer value for setting: {value}",
                )

        elif dt in ("FLOAT", "DECIMAL"):
            if isinstance(value, bool):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid numeric value: boolean provided",
                )
            try:
                return float(value)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid numeric value for setting: {value}",
                )

        elif dt == "BOOLEAN":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                s = value.strip().lower()
                if s in ("true", "1", "yes"):
                    return True
                if s in ("false", "0", "no"):
                    return False
            if isinstance(value, int) and value in (0, 1):
                return bool(value)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid boolean value for setting: {value}",
            )

        elif dt == "STRING":
            if not isinstance(value, (str, int, float)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid string value for setting: {value}",
                )
            return str(value)

        elif dt == "JSON":
            if not isinstance(value, (dict, list)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid JSON value for setting: {value}",
                )
            return value

        return value

    async def get_setting(self, db: AsyncSession, key: str, default: Any = None) -> Any:
        """Retrieve setting value with in-memory caching."""
        if key in self._memory_cache:
            return self._memory_cache[key]

        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()
        if setting:
            self._memory_cache[key] = setting.value
            return setting.value
        return default

    async def get_setting_model(self, db: AsyncSession, key: str) -> Optional[SystemSetting]:
        """Retrieve full SystemSetting ORM entity."""
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_settings(
        self, db: AsyncSession, category: Optional[str] = None
    ) -> List[SystemSetting]:
        """Retrieve all settings, optionally filtered by category."""
        stmt = select(SystemSetting)
        if category:
            stmt = stmt.where(SystemSetting.category == category.upper())
        stmt = stmt.order_by(SystemSetting.category, SystemSetting.key)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_setting(
        self,
        db: AsyncSession,
        key: str,
        value: Any,
        performed_by: str,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> SystemSetting:
        """Update a system setting, record an audit ledger entry, and invalidate caches."""
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()

        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found",
            )

        # Validate & cast new value
        validated_value = self._validate_and_cast(value, setting.data_type)

        old_state = {
            "value": setting.value,
            "data_type": setting.data_type,
            "category": setting.category,
        }
        new_state = {
            "value": validated_value,
            "reason": reason,
        }

        # Update setting record
        setting.value = validated_value
        setting.updated_by = performed_by
        setting.updated_at = datetime.now(timezone.utc)

        # Create audit ledger entry
        audit_entry = AuditLog(
            entity_name="system_settings",
            entity_id=key,
            action="UPDATE",
            old_state=old_state,
            new_state=new_state,
            performed_by=performed_by,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit_entry)

        await db.commit()
        await db.refresh(setting)

        # Invalidate cache
        self.clear_cache(key)

        return setting

    async def log_audit_event(
        self,
        db: AsyncSession,
        entity_name: str,
        entity_id: str,
        action: str,
        performed_by: str,
        old_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Record an immutable audit log entry for any CRM entity."""
        audit_entry = AuditLog(
            entity_name=entity_name,
            entity_id=entity_id,
            action=action.upper(),
            old_state=old_state,
            new_state=new_state,
            performed_by=performed_by,
            ip_address=ip_address,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)
        return audit_entry

    async def get_audit_logs(
        self,
        db: AsyncSession,
        entity_name: Optional[str] = None,
        entity_id: Optional[str] = None,
        performed_by: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AuditLog], int]:
        """Query audit log ledger with flexible filters and pagination."""
        stmt = select(AuditLog)
        count_stmt = select(func.count(AuditLog.id))

        if entity_name:
            stmt = stmt.where(AuditLog.entity_name == entity_name)
            count_stmt = count_stmt.where(AuditLog.entity_name == entity_name)
        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
            count_stmt = count_stmt.where(AuditLog.entity_id == entity_id)
        if performed_by:
            stmt = stmt.where(AuditLog.performed_by == performed_by)
            count_stmt = count_stmt.where(AuditLog.performed_by == performed_by)

        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = stmt.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit)
        items_res = await db.execute(stmt)
        items = list(items_res.scalars().all())

        return items, total


settings_service = SettingsService()


async def get_system_setting(key: str, db: AsyncSession, default: Any = None) -> Any:
    """Convenience helper to retrieve a system setting value."""
    return await settings_service.get_setting(db, key, default)

