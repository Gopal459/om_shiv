import logging
from datetime import datetime, timezone, time
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.leads import Lead, LeadActivity
from app.models.identity import Employee
from app.services.settings_service import get_system_setting

logger = logging.getLogger(__name__)


def is_quiet_hours(start_str: str, end_str: str, check_time: Optional[datetime] = None) -> bool:
    """Checks whether the given UTC/local time falls inside the configured quiet hours window."""
    current_time = (check_time or datetime.now(timezone.utc)).time()
    try:
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        start = time(sh, sm)
        end = time(eh, em)
    except Exception:
        # Default fallback 21:00 to 09:00
        start = time(21, 0)
        end = time(9, 0)

    if start <= end:
        return start <= current_time <= end
    else:
        # Over midnight window (e.g. 21:00 to 09:00)
        return current_time >= start or current_time <= end


async def process_sla_escalations(
    db: AsyncSession,
    bypass_quiet_hours: bool = False,
) -> Dict[str, Any]:
    """
    Automated SLA Escalation Worker:
    1. Checks quiet hours window (e.g. 21:00 to 09:00) unless bypassed.
    2. Identifies untouched leads (stage == 'NEW', is_untouched == True).
    3. Untouched > 3h (sla_untouched_hours): sends reminder to assigned sales rep.
    4. Untouched > 24h (sla_escalation_hours): escalates to rep's reporting manager.
    5. HOT leads untouched > 3h: triggers immediate escalation to reporting manager.
    """
    quiet_enabled = await get_system_setting("quiet_hours_enabled", db)
    if quiet_enabled is None:
        quiet_enabled = True

    quiet_start = await get_system_setting("quiet_hours_start", db) or "21:00"
    quiet_end = await get_system_setting("quiet_hours_end", db) or "09:00"

    now = datetime.now(timezone.utc)
    in_quiet = is_quiet_hours(quiet_start, quiet_end, now)

    if quiet_enabled and in_quiet and not bypass_quiet_hours:
        logger.info("SLA worker running during quiet hours (%s - %s). Notifications suppressed.", quiet_start, quiet_end)
        return {
            "quiet_hours_active": True,
            "notifications_suppressed": True,
            "reminders_sent": 0,
            "escalations_sent": 0,
            "hot_escalations_sent": 0,
        }

    untouched_hours = float(await get_system_setting("sla_untouched_hours", db) or 3)
    escalation_hours = float(await get_system_setting("sla_escalation_hours", db) or 24)

    # Query all untouched active leads
    stmt = (
        select(Lead)
        .where(
            and_(
                Lead.is_untouched == True,
                Lead.stage == "NEW",
                Lead.is_duplicate == False,
                Lead.is_test == False,
            )
        )
    )
    result = await db.execute(stmt)
    untouched_leads = result.scalars().all()

    reminders_sent = 0
    escalations_sent = 0
    hot_escalations_sent = 0

    for lead in untouched_leads:
        timer_start = lead.untouched_timer_start or lead.created_at
        if timer_start.tzinfo is None:
            timer_start = timer_start.replace(tzinfo=timezone.utc)

        elapsed_hours = (now - timer_start).total_seconds() / 3600.0

        # Case 1: Untouched > escalation_hours (24h) -> Escalate to Reporting Manager
        if elapsed_hours >= escalation_hours:
            activity = LeadActivity(
                lead_id=lead.lead_id,
                action_type="SLA_MANAGER_ESCALATION",
                outcome="ESCALATED",
                note=f"Lead untouched for {elapsed_hours:.1f} hours (> {escalation_hours}h). Escalated to reporting manager.",
                performed_by="SYSTEM",
                stage_before=lead.stage,
                stage_after=lead.stage,
            )
            db.add(activity)
            escalations_sent += 1

        # Case 2: HOT lead untouched > untouched_hours (3h) -> Immediate Manager Alert
        elif lead.temperature == "HOT" and elapsed_hours >= untouched_hours:
            activity = LeadActivity(
                lead_id=lead.lead_id,
                action_type="SLA_HOT_LEAD_ESCALATION",
                outcome="ESCALATED",
                note=f"HOT Lead untouched for {elapsed_hours:.1f} hours (> {untouched_hours}h). Priority alert dispatched to manager.",
                performed_by="SYSTEM",
                stage_before=lead.stage,
                stage_after=lead.stage,
            )
            db.add(activity)
            hot_escalations_sent += 1

        # Case 3: Untouched > untouched_hours (3h) -> Reminder to Assigned Rep
        elif elapsed_hours >= untouched_hours:
            activity = LeadActivity(
                lead_id=lead.lead_id,
                action_type="SLA_UNTOUCHED_REMINDER",
                outcome="REMINDER_SENT",
                note=f"Lead untouched for {elapsed_hours:.1f} hours (> {untouched_hours}h). Reminder sent to assigned representative.",
                performed_by="SYSTEM",
                stage_before=lead.stage,
                stage_after=lead.stage,
            )
            db.add(activity)
            reminders_sent += 1

    if reminders_sent or escalations_sent or hot_escalations_sent:
        await db.commit()

    return {
        "quiet_hours_active": in_quiet,
        "notifications_suppressed": False,
        "untouched_leads_scanned": len(untouched_leads),
        "reminders_sent": reminders_sent,
        "escalations_sent": escalations_sent,
        "hot_escalations_sent": hot_escalations_sent,
    }
