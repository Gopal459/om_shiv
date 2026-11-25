from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.leads import Lead, LeadActivity, LeadActionLog


# 12 Pipeline Stages
VALID_STAGES = [
    "NEW",
    "ATTEMPTING",
    "CONNECTED",
    "REQ_CAPTURED",
    "QUALIFIED",
    "MEETING",
    "SITE_VISIT",
    "NEGOTIATION",
    "WON",
    "LOST",
    "NURTURE",
    "AI_DESK",
]

STAGE_ALIASES = {
    "MEETING_PLANNED": "MEETING",
    "SITE_VISIT_PLANNED": "SITE_VISIT",
    "SITE_VISIT_DONE": "SITE_VISIT",
}

# Stages that require mandatory temperature and follow_up_date
COMPULSORY_FOLLOWUP_STAGES = {
    "CONNECTED",
    "REQ_CAPTURED",
    "QUALIFIED",
    "MEETING",
    "SITE_VISIT",
    "NEGOTIATION",
}

VALID_TEMPERATURES = {"HOT", "WARM", "COLD"}

# HTTP status 422
HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)



def normalize_stage(stage_name: Optional[str]) -> str:
    """Normalize stage names and handle common aliases."""
    if not stage_name:
        return "NEW"
    cleaned = stage_name.strip().upper()
    return STAGE_ALIASES.get(cleaned, cleaned)


class PipelineService:
    """Service managing pipeline stage transitions, action logging, and queue views."""

    def validate_stage_transition(
        self,
        current_stage: str,
        target_stage: str,
        temperature: Optional[str] = None,
        follow_up_date: Optional[datetime] = None,
        lost_reason: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> Tuple[str, Optional[str], Optional[datetime]]:
        """
        Validate whether a transition from current_stage to target_stage is allowed,
        and verify all compulsory fields (temperature, follow_up_date, lost_reason).
        """
        now = now or datetime.now(timezone.utc)
        curr = normalize_stage(current_stage)
        target = normalize_stage(target_stage)

        if target not in VALID_STAGES:
            raise HTTPException(
                status_code=HTTP_422,
                detail=f"Invalid pipeline stage: '{target_stage}'. Must be one of {VALID_STAGES}",
            )

        # Terminal state checks
        if curr == "WON" and target != "WON":
            raise HTTPException(
                status_code=HTTP_422,
                detail="Lead is already WON (terminal stage) and cannot be moved backwards",
            )
        if curr == "NEW" and target == "WON":
            raise HTTPException(
                status_code=HTTP_422,
                detail="Cannot jump directly from NEW to WON without qualification or negotiation",
            )

        # Compulsory validation for connected/engaged stages
        norm_temp: Optional[str] = None
        norm_f_date: Optional[datetime] = None

        if target in COMPULSORY_FOLLOWUP_STAGES:
            # 1. Temperature validation
            if not temperature:
                raise HTTPException(
                    status_code=HTTP_422,
                    detail=f"Stage '{target}' requires compulsory temperature (HOT, WARM, COLD)",
                )
            temp_clean = temperature.strip().upper()
            if temp_clean not in VALID_TEMPERATURES:
                raise HTTPException(
                    status_code=HTTP_422,
                    detail=f"Invalid temperature '{temperature}'. Must be HOT, WARM, or COLD",
                )
            norm_temp = temp_clean

            # 2. Follow-up date validation
            if not follow_up_date:
                raise HTTPException(
                    status_code=HTTP_422,
                    detail=f"Stage '{target}' requires compulsory follow_up_date",
                )
            if follow_up_date.tzinfo is None:
                norm_f_date = follow_up_date.replace(tzinfo=timezone.utc)
            else:
                norm_f_date = follow_up_date.astimezone(timezone.utc)

            # Clock skew tolerance: allow up to 2 minutes in past so current-minute selections are accepted
            if norm_f_date < (now - timedelta(minutes=2)):
                raise HTTPException(
                    status_code=HTTP_422,
                    detail="follow_up_date must be a future datetime",
                )

            # Max horizon rules: <= 30 days for HOT/WARM, <= 100 days for COLD
            if norm_temp in ("HOT", "WARM"):
                max_horizon = now + timedelta(days=30)
                if norm_f_date > max_horizon:
                    raise HTTPException(
                        status_code=HTTP_422,
                        detail=f"Follow-up date for {norm_temp} leads cannot exceed 30 days in the future",
                    )
            elif norm_temp == "COLD":
                max_horizon = now + timedelta(days=100)
                if norm_f_date > max_horizon:
                    raise HTTPException(
                        status_code=HTTP_422,
                        detail="Follow-up date for COLD leads cannot exceed 100 days in the future",
                    )
        else:
            if temperature:
                temp_clean = temperature.strip().upper()
                if temp_clean in VALID_TEMPERATURES:
                    norm_temp = temp_clean
            if follow_up_date:
                norm_f_date = (
                    follow_up_date.replace(tzinfo=timezone.utc)
                    if follow_up_date.tzinfo is None
                    else follow_up_date.astimezone(timezone.utc)
                )

        # Compulsory validation for LOST
        if target == "LOST":
            if not lost_reason or not str(lost_reason).strip():
                raise HTTPException(
                    status_code=HTTP_422,
                    detail="Transitioning lead to LOST requires a non-empty lost_reason",
                )

        return target, norm_temp, norm_f_date

    async def log_sales_action(
        self,
        db: AsyncSession,
        lead: Lead,
        action_type: str,
        outcome: Optional[str] = None,
        note: Optional[str] = None,
        next_action: Optional[str] = None,
        stage: Optional[str] = None,
        temperature: Optional[str] = None,
        follow_up_date: Optional[datetime] = None,
        lost_reason: Optional[str] = None,
        actor_id: str = "SYSTEM",
    ) -> Tuple[Lead, LeadActivity]:
        """
        Record a sales action, execute stage transition validations, update the lead entity,
        reset the untouched flag, and append a LeadActivity record.
        """
        now = datetime.now(timezone.utc)
        current_stage = lead.stage
        target_stage = stage or current_stage

        # Ensure lead.follow_up_date is timezone-aware before comparison
        existing_f_date = None
        if lead.follow_up_date:
            existing_f_date = (
                lead.follow_up_date.replace(tzinfo=timezone.utc)
                if lead.follow_up_date.tzinfo is None
                else lead.follow_up_date.astimezone(timezone.utc)
            )

        effective_follow_up_date = follow_up_date or (
            existing_f_date
            if (existing_f_date and existing_f_date > now)
            else None
        )

        validated_stage, valid_temp, valid_f_date = self.validate_stage_transition(
            current_stage=current_stage,
            target_stage=target_stage,
            temperature=temperature or lead.temperature,
            follow_up_date=effective_follow_up_date,
            lost_reason=lost_reason or lead.lost_reason,
            now=now,
        )

        # Update Lead
        lead.stage = validated_stage
        lead.is_untouched = False
        lead.last_contacted_at = now
        lead.updated_at = now

        if valid_temp:
            lead.temperature = valid_temp
        if valid_f_date:
            lead.follow_up_date = valid_f_date
        if lost_reason:
            lead.lost_reason = lost_reason.strip()

        # Create Activity Log
        norm_action_type = action_type.strip().upper() if action_type else "NOTE"
        activity = LeadActivity(
            lead_id=lead.lead_id,
            action_type=norm_action_type,
            outcome=outcome,
            note=note,
            next_action=next_action,
            follow_up_date=lead.follow_up_date,
            stage_before=current_stage,
            stage_after=validated_stage,
            temperature=lead.temperature,
            logged_by=actor_id,
            performed_by=actor_id,
            created_at=now,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(lead)
        await db.refresh(activity)

        return lead, activity


pipeline_service = PipelineService()
