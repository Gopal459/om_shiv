"""AI Agent Control Center & Safety Admin REST API (Task 17).

Exposes admin management endpoints for:
  - Listing all AI agents with operating modes (DISABLED / SHADOW / LIVE),
    active state, rate limits, and execution metrics.
  - Toggling any agent between Active (LIVE or SHADOW) and Inactive (DISABLED)
    with zero server restart and full immutable AuditLog trail.
  - Reviewing, approving, and rejecting Human-in-the-Loop (HITL) staged actions.
  - Inspecting execution & shadow logs with automatic PII masking.
  - Managing customer TRAI/DPDP communication consent (opt-in / opt-out).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.ai_agents import (
    AIAgentConfig,
    AIAgentExecutionLog,
    AIApprovalQueue,
    CustomerConsent,
)
from app.models.settings import AuditLog
from app.services.ai.safety_guardrails import (
    SafetyGuardrailsService,
    _get_phone_variants,
    _normalize_phone,
)
from app.services.ai.tools import AIToolRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ai", tags=["ai-admin"])
security = HTTPBearer(auto_error=False)

VALID_MODES = {"DISABLED", "SHADOW", "LIVE"}

# Canonical catalog of all 13 AI Agent configurations wired into Omshiv CRM
DEFAULT_AI_AGENTS: List[Dict[str, Any]] = [
    {
        "agent_name": "property_search",
        "display_name": "AI Property Search Agent",
        "mode": "SHADOW",
        "rate_limit_per_hour": 30,
        "requires_hitl": False,
        "is_customer_facing": True,
        "extra_config": {
            "category": "Conversational",
            "channel": "WhatsApp / Web Chat",
            "description": "Understands buyer inquiries in English, Hindi & Hinglish and searches live verified properties with Indian pricing (Lakh/Cr).",
        },
    },
    {
        "agent_name": "lead_qualification",
        "display_name": "AI Lead Qualification Agent",
        "mode": "SHADOW",
        "rate_limit_per_hour": 30,
        "requires_hitl": True,
        "is_customer_facing": False,
        "extra_config": {
            "category": "Intelligence",
            "channel": "CRM / Chat / Transcript",
            "description": "Scores leads 0-100 (HOT/WARM/COLD), extracts budget/BHK/locality, and routes LOST proposals to HITL approvals.",
        },
    },
    {
        "agent_name": "customer_support",
        "display_name": "AI Customer Support Agent",
        "mode": "SHADOW",
        "rate_limit_per_hour": 25,
        "requires_hitl": False,
        "is_customer_facing": True,
        "extra_config": {
            "category": "Conversational",
            "channel": "Support / Chat",
            "description": "Answers verified property & policy FAQs and escalates legal disputes, fraud claims, or human requests immediately.",
        },
    },
    {
        "agent_name": "site_visit_agent",
        "display_name": "AI Site Visit Booking Agent",
        "mode": "SHADOW",
        "rate_limit_per_hour": 15,
        "requires_hitl": False,
        "is_customer_facing": True,
        "extra_config": {
            "category": "Scheduling",
            "channel": "WhatsApp / Voice",
            "description": "Checks daily slot availability (10:00-17:00), prevents double-booking, and schedules property site visits.",
        },
    },
    {
        "agent_name": "sales_assistant",
        "display_name": "AI Sales Assistant Copilot",
        "mode": "SHADOW",
        "rate_limit_per_hour": 40,
        "requires_hitl": True,
        "is_customer_facing": False,
        "extra_config": {
            "category": "Intelligence",
            "channel": "Internal CRM Copilot",
            "description": "Generates executive lead briefings, drafts personalized follow-ups, and stages sensitive stage overrides for manager review.",
        },
    },
    {
        "agent_name": "document_processing",
        "display_name": "AI Document Processing Agent (OCR)",
        "mode": "SHADOW",
        "rate_limit_per_hour": 20,
        "requires_hitl": False,
        "is_customer_facing": False,
        "extra_config": {
            "category": "Intelligence",
            "channel": "Property Verification PDF/Image",
            "description": "Extracts Khasra No., Plot Area, Seller, Registry Date & DLC rates from scanned Pattas/Registries and flags missing 90A approvals.",
        },
    },
    {
        "agent_name": "whatsapp_agent",
        "display_name": "AI WhatsApp Agent",
        "mode": "SHADOW",
        "rate_limit_per_hour": 10,
        "requires_hitl": False,
        "is_customer_facing": True,
        "extra_config": {
            "category": "Conversational",
            "channel": "DoubleTick WhatsApp",
            "description": "24x7 automated WhatsApp assistant with instant STOP/BAND KARO opt-out detection and hourly anti-spam caps.",
        },
    },
    {
        "agent_name": "meta_lead_agent",
        "display_name": "Meta Lead Ads Agent",
        "mode": "SHADOW",
        "rate_limit_per_hour": 50,
        "requires_hitl": False,
        "is_customer_facing": False,
        "extra_config": {
            "category": "Capture",
            "channel": "Facebook / Meta Lead Ads",
            "description": "Captures Meta Lead Ads instantaneously, deduplicates by mobile/idempotency key, logs consent, and triggers qualification.",
        },
    },
    {
        "agent_name": "instagram_agent",
        "display_name": "Instagram Direct & Ads Agent",
        "mode": "SHADOW",
        "rate_limit_per_hour": 50,
        "requires_hitl": False,
        "is_customer_facing": False,
        "extra_config": {
            "category": "Capture",
            "channel": "Instagram DM / Lead Ads",
            "description": "Extracts phone numbers from Instagram DMs, prevents duplicate leads, logs consent, and starts qualification.",
        },
    },
    {
        "agent_name": "followup_journey_agent",
        "display_name": "AI Follow-Up & Post-Visit Nurturing",
        "mode": "SHADOW",
        "rate_limit_per_hour": 10,
        "requires_hitl": False,
        "is_customer_facing": True,
        "extra_config": {
            "category": "Nurturing",
            "channel": "WhatsApp Cadence (Day 0-30)",
            "description": "Runs Day 0/1/3/7/15/30 nurturing and analyzes post-visit feedback with 24h anti-spam cooldown and terminal-stage skip.",
        },
    },
    {
        "agent_name": "new_property_alert_agent",
        "display_name": "New Property Alert Agent",
        "mode": "SHADOW",
        "rate_limit_per_hour": 10,
        "requires_hitl": False,
        "is_customer_facing": True,
        "extra_config": {
            "category": "Scheduling",
            "channel": "WhatsApp Broadcast",
            "description": "Matches newly verified live properties to buyers by city/budget with 7-day duplicate suppression and TRAI consent check.",
        },
    },
    {
        "agent_name": "voice_calling_agent",
        "display_name": "AI Voice Calling Agent (Exotel)",
        "mode": "SHADOW",
        "rate_limit_per_hour": 5,
        "requires_hitl": False,
        "is_customer_facing": True,
        "extra_config": {
            "category": "Scheduling",
            "channel": "Exotel Telephony",
            "description": "Places outbound calls under strict TRAI gates (09:00-21:00 IST, VOICE opt-in) and qualifies call transcripts.",
        },
    },
    {
        "agent_name": "ai_scheduler",
        "display_name": "Async Background Scheduler & PII Purge",
        "mode": "SHADOW",
        "rate_limit_per_hour": 60,
        "requires_hitl": False,
        "is_customer_facing": False,
        "extra_config": {
            "category": "Nurturing",
            "channel": "Internal Cron Workers",
            "description": "Orchestrates nurturing cycles, alert retries, daytime call retries, and 90-day DPDP PII log purging.",
        },
    },
]


# ---------------------------------------------------------------------------
# Helpers & Dependencies
# ---------------------------------------------------------------------------

def get_actor_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Extract authenticated employee_id from Bearer JWT, falling back to ADMIN_SYSTEM."""
    if credentials and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            sub = payload.get("sub")
            if sub:
                return str(sub)
        except Exception:
            pass
    return "ADMIN_SYSTEM"


async def ensure_default_ai_agents(db: AsyncSession) -> List[AIAgentConfig]:
    """Seed any missing default AI agent configs idempotently and return all configs."""
    existing_res = await db.execute(select(AIAgentConfig))
    existing_map = {cfg.agent_name: cfg for cfg in existing_res.scalars().all()}

    added = False
    now = datetime.now(timezone.utc)
    for spec in DEFAULT_AI_AGENTS:
        if spec["agent_name"] not in existing_map:
            cfg = AIAgentConfig(
                agent_name=spec["agent_name"],
                display_name=spec["display_name"],
                mode=spec["mode"],
                rate_limit_per_hour=spec["rate_limit_per_hour"],
                requires_hitl=spec["requires_hitl"],
                is_customer_facing=spec["is_customer_facing"],
                extra_config=spec["extra_config"],
                created_at=now,
                updated_at=now,
            )
            db.add(cfg)
            existing_map[spec["agent_name"]] = cfg
            added = True

    if added:
        await db.commit()
        for cfg in existing_map.values():
            await db.refresh(cfg)

    # Return in canonical order first, then any custom agents alphabetically
    ordered: List[AIAgentConfig] = []
    seen = set()
    for spec in DEFAULT_AI_AGENTS:
        name = spec["agent_name"]
        if name in existing_map:
            ordered.append(existing_map[name])
            seen.add(name)
    for name in sorted(existing_map.keys()):
        if name not in seen:
            ordered.append(existing_map[name])
    return ordered


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class AgentPatchRequest(BaseModel):
    mode: Optional[str] = Field(
        None,
        description="Operating mode: DISABLED, SHADOW, or LIVE",
    )
    is_active: Optional[bool] = Field(
        None,
        description="Convenience active/inactive switch. False -> DISABLED; True -> target_mode or LIVE.",
    )
    active_mode: Optional[str] = Field(
        default="LIVE",
        description="Target mode when is_active=True (LIVE or SHADOW, defaults to LIVE).",
    )
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=1000)
    requires_hitl: Optional[bool] = None
    reason: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    review_note: Optional[str] = Field(None, max_length=500)


class ConsentToggleRequest(BaseModel):
    mobile: str = Field(..., min_length=8, max_length=20)
    channel: str = Field(default="WHATSAPP")
    reason: Optional[str] = Field(None, max_length=255)


# ---------------------------------------------------------------------------
# Agent Config & Toggle Endpoints
# ---------------------------------------------------------------------------

@router.get("/agents", summary="List all AI agents with operating status and metrics")
async def list_ai_agents(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Return all configured AI agents (auto-seeding defaults on first request)."""
    configs = await ensure_default_ai_agents(db)

    # Aggregate execution counts per agent
    log_stats_stmt = select(
        AIAgentExecutionLog.agent_name,
        AIAgentExecutionLog.status,
        func.count(AIAgentExecutionLog.id),
    ).group_by(AIAgentExecutionLog.agent_name, AIAgentExecutionLog.status)
    stat_rows = (await db.execute(log_stats_stmt)).all()

    metrics: Dict[str, Dict[str, int]] = {}
    for agent_name, log_status, cnt in stat_rows:
        bucket = metrics.setdefault(
            agent_name,
            {"total_runs": 0, "success_runs": 0, "shadow_runs": 0, "blocked_runs": 0},
        )
        bucket["total_runs"] += int(cnt or 0)
        if log_status == "SUCCESS":
            bucket["success_runs"] += int(cnt or 0)
        elif log_status == "SHADOW_LOGGED":
            bucket["shadow_runs"] += int(cnt or 0)
        elif log_status and log_status.startswith("BLOCKED"):
            bucket["blocked_runs"] += int(cnt or 0)

    pending_approvals_count = (
        await db.execute(
            select(func.count(AIApprovalQueue.id)).where(AIApprovalQueue.status == "PENDING")
        )
    ).scalar() or 0

    default_meta = {s["agent_name"]: s["extra_config"] for s in DEFAULT_AI_AGENTS}

    items = []
    active_count = 0
    live_count = 0
    shadow_count = 0
    disabled_count = 0

    for cfg in configs:
        mode_upper = (cfg.mode or "SHADOW").upper()
        is_active = mode_upper != "DISABLED"
        if mode_upper == "LIVE":
            live_count += 1
            active_count += 1
        elif mode_upper == "SHADOW":
            shadow_count += 1
            active_count += 1
        else:
            disabled_count += 1

        meta = cfg.extra_config if isinstance(cfg.extra_config, dict) and cfg.extra_config else default_meta.get(cfg.agent_name, {})
        agent_metrics = metrics.get(
            cfg.agent_name,
            {"total_runs": 0, "success_runs": 0, "shadow_runs": 0, "blocked_runs": 0},
        )

        items.append(
            {
                "id": cfg.id,
                "agent_name": cfg.agent_name,
                "display_name": cfg.display_name,
                "mode": mode_upper,
                "is_active": is_active,
                "rate_limit_per_hour": cfg.rate_limit_per_hour,
                "requires_hitl": bool(cfg.requires_hitl),
                "is_customer_facing": bool(cfg.is_customer_facing),
                "category": meta.get("category", "General"),
                "channel": meta.get("channel", "CRM"),
                "description": meta.get("description", ""),
                "metrics": agent_metrics,
                "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
            }
        )

    return {
        "agents": items,
        "summary": {
            "total": len(items),
            "active": active_count,
            "live": live_count,
            "shadow": shadow_count,
            "disabled": disabled_count,
            "pending_approvals": int(pending_approvals_count),
        },
    }


@router.patch(
    "/agents/{agent_name}",
    summary="Update AI agent operating mode (Active/Inactive/Shadow/Live) or rate limit",
)
async def update_ai_agent(
    agent_name: str,
    payload: AgentPatchRequest,
    request: Request,
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Toggle an AI agent active/inactive or change mode (DISABLED / SHADOW / LIVE)."""
    await ensure_default_ai_agents(db)

    res = await db.execute(
        select(AIAgentConfig).where(AIAgentConfig.agent_name == agent_name)
    )
    cfg = res.scalar_one_or_none()
    if not cfg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI agent '{agent_name}' not found.",
        )

    old_state = {
        "mode": cfg.mode,
        "rate_limit_per_hour": cfg.rate_limit_per_hour,
        "requires_hitl": cfg.requires_hitl,
    }

    target_mode: Optional[str] = None
    if payload.mode is not None:
        candidate = payload.mode.strip().upper()
        if candidate not in VALID_MODES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid mode '{payload.mode}'. Must be one of {sorted(VALID_MODES)}.",
            )
        target_mode = candidate
    elif payload.is_active is not None:
        if not payload.is_active:
            target_mode = "DISABLED"
        else:
            preferred = (payload.active_mode or "LIVE").strip().upper()
            target_mode = preferred if preferred in {"LIVE", "SHADOW"} else "LIVE"

    now = datetime.now(timezone.utc)
    if target_mode is not None:
        cfg.mode = target_mode
    if payload.rate_limit_per_hour is not None:
        cfg.rate_limit_per_hour = payload.rate_limit_per_hour
    if payload.requires_hitl is not None:
        cfg.requires_hitl = payload.requires_hitl
    cfg.updated_at = now

    new_state = {
        "mode": cfg.mode,
        "rate_limit_per_hour": cfg.rate_limit_per_hour,
        "requires_hitl": cfg.requires_hitl,
        "reason": payload.reason,
    }

    audit = AuditLog(
        id=str(uuid.uuid4()),
        entity_name="AIAgentConfig",
        entity_id=cfg.agent_name,
        action="UPDATE_AI_AGENT_CONFIG",
        old_state=old_state,
        new_state=new_state,
        performed_by=actor,
        ip_address=request.client.host if request.client else None,
        timestamp=now,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(cfg)

    return {
        "success": True,
        "agent_name": cfg.agent_name,
        "display_name": cfg.display_name,
        "mode": cfg.mode,
        "is_active": cfg.mode != "DISABLED",
        "rate_limit_per_hour": cfg.rate_limit_per_hour,
        "requires_hitl": bool(cfg.requires_hitl),
        "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Human-in-the-Loop (HITL) Approval Queue Endpoints
# ---------------------------------------------------------------------------

@router.get("/approvals", summary="List HITL staged approval requests")
async def list_ai_approvals(
    status_filter: Optional[str] = Query(default="PENDING", alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """List AIApprovalQueue entries filtered by status (PENDING, APPROVED, REJECTED, or ALL)."""
    stmt = select(AIApprovalQueue).order_by(AIApprovalQueue.requested_at.desc()).limit(limit)
    if status_filter and status_filter.upper() != "ALL":
        stmt = stmt.where(func.upper(AIApprovalQueue.status) == status_filter.upper())

    rows = (await db.execute(stmt)).scalars().all()
    items = [
        {
            "id": row.id,
            "agent_name": row.agent_name,
            "lead_id": row.lead_id,
            "action_type": row.action_type,
            "proposed_payload": row.proposed_payload or {},
            "status": row.status,
            "requested_at": row.requested_at.isoformat() if row.requested_at else None,
            "reviewed_by": row.reviewed_by,
            "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
            "review_note": row.review_note,
        }
        for row in rows
    ]
    return {"approvals": items, "total": len(items)}


@router.post("/approvals/{approval_id}/approve", summary="Approve and execute staged AI action")
async def approve_ai_action(
    approval_id: str,
    body: ApprovalDecisionRequest = ApprovalDecisionRequest(),
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Approve a PENDING HITL item and execute its CRM mutation safely."""
    tools = AIToolRegistry(db)
    ok = await tools.execute_approved_action(
        approval_id=approval_id,
        reviewer_id=actor,
        review_note=body.review_note,
        db=db,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval item not found or is no longer PENDING.",
        )
    return {"success": True, "approval_id": approval_id, "status": "APPROVED", "reviewed_by": actor}


@router.post("/approvals/{approval_id}/reject", summary="Reject staged AI action without mutating lead")
async def reject_ai_action(
    approval_id: str,
    body: ApprovalDecisionRequest = ApprovalDecisionRequest(),
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Reject a PENDING HITL item leaving CRM records untouched."""
    tools = AIToolRegistry(db)
    ok = await tools.reject_staged_action(
        approval_id=approval_id,
        reviewer_id=actor,
        review_note=body.review_note,
        db=db,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval item not found or is no longer PENDING.",
        )
    return {"success": True, "approval_id": approval_id, "status": "REJECTED", "reviewed_by": actor}


# ---------------------------------------------------------------------------
# Execution & Shadow Audit Logs (PII Masked)
# ---------------------------------------------------------------------------

@router.get("/logs", summary="Query AI execution and shadow logs with PII masking")
async def list_ai_logs(
    agent_name: Optional[str] = Query(default=None),
    lead_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return recent AIAgentExecutionLog records with mobile/email PII masked."""
    stmt = select(AIAgentExecutionLog).order_by(AIAgentExecutionLog.created_at.desc()).limit(limit)
    if agent_name:
        stmt = stmt.where(AIAgentExecutionLog.agent_name == agent_name)
    if lead_id:
        stmt = stmt.where(AIAgentExecutionLog.lead_id == lead_id)
    if status_filter:
        stmt = stmt.where(AIAgentExecutionLog.status == status_filter)

    rows = (await db.execute(stmt)).scalars().all()
    guardrails = SafetyGuardrailsService(db)

    logs = [
        {
            "id": row.id,
            "agent_name": row.agent_name,
            "lead_id": row.lead_id,
            "channel": row.channel,
            "mode": row.mode,
            "trigger_event": row.trigger_event,
            "input_summary": guardrails.mask_pii(row.input_summary) if row.input_summary else None,
            "output_response": guardrails.mask_pii(row.output_response) if row.output_response else None,
            "tools_called": row.tools_called or [],
            "status": row.status,
            "approval_id": row.approval_id,
            "error_message": guardrails.mask_pii(row.error_message) if row.error_message else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    return {"logs": logs, "total": len(logs)}


# ---------------------------------------------------------------------------
# Consent Management Endpoints
# ---------------------------------------------------------------------------

@router.get("/consent/{mobile}", summary="Inspect customer communication consent status across channels")
async def get_customer_consent(
    mobile: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Check current opt-in/opt-out state for a customer mobile number."""
    variants = _get_phone_variants(mobile)
    if not variants:
        variants = [mobile]

    stmt = (
        select(CustomerConsent)
        .where(CustomerConsent.mobile.in_(variants))
        .order_by(CustomerConsent.updated_at.desc(), CustomerConsent.id.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    by_channel: Dict[str, Any] = {}
    for row in rows:
        ch = (row.channel or "WHATSAPP").upper()
        if ch not in by_channel:
            by_channel[ch] = {
                "channel": ch,
                "is_opted_in": bool(row.is_opted_in),
                "consent_source": row.consent_source,
                "opt_out_reason": row.opt_out_reason,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }

    return {
        "mobile": _normalize_phone(mobile) or mobile,
        "channels": by_channel,
    }


@router.post("/consent/opt-out", summary="Manually opt-out a customer from an AI communication channel")
async def manual_opt_out(
    body: ConsentToggleRequest,
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Revoke customer communication consent immediately."""
    guardrails = SafetyGuardrailsService(db)
    consent = await guardrails.register_consent(
        mobile=body.mobile,
        channel=body.channel,
        is_opted_in=False,
        source=f"ADMIN:{actor}",
        reason=body.reason or "Manual admin opt-out",
    )
    return {
        "success": True,
        "mobile": consent.mobile,
        "channel": consent.channel,
        "is_opted_in": consent.is_opted_in,
    }


@router.post("/consent/opt-in", summary="Manually opt-in a customer for an AI communication channel")
async def manual_opt_in(
    body: ConsentToggleRequest,
    actor: str = Depends(get_actor_from_token),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Record explicit customer communication opt-in."""
    guardrails = SafetyGuardrailsService(db)
    consent = await guardrails.register_consent(
        mobile=body.mobile,
        channel=body.channel,
        is_opted_in=True,
        source=f"ADMIN:{actor}",
        reason=body.reason,
    )
    return {
        "success": True,
        "mobile": consent.mobile,
        "channel": consent.channel,
        "is_opted_in": consent.is_opted_in,
    }
