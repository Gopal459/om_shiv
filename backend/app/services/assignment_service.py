import logging
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.identity import Employee
from app.models.leads import Lead, LeadActivity
from app.services.settings_service import get_system_setting

logger = logging.getLogger(__name__)


async def assign_lead(
    lead: Lead,
    db: AsyncSession,
    category: Optional[str] = None,
) -> Optional[Employee]:
    """
    Assigns an incoming lead to an eligible sales representative using strict rules table
    and round-robin balancing, with leave cover rerouting.
    """
    # 1. Fetch routing mode (default: STRICT_RULES_TABLE)
    routing_mode = await get_system_setting("lead_routing_mode", db) or "STRICT_RULES_TABLE"

    # 2. Query eligible active employees
    stmt = select(Employee).where(Employee.is_active == True)
    result = await db.execute(stmt)
    employees = result.scalars().all()

    if not employees:
        logger.warning("No active employees available for assignment.")
        return None

    # Filter candidates by category and budget
    candidates: List[Employee] = []
    target_category = (category or "").upper()

    # Determine lead budget in Crores for comparison (if budget is in INR, e.g. 5,000,000 = 0.05 Cr)
    lead_budget_cr: Optional[float] = None
    raw_budget = lead.budget_max or lead.budget_min
    if raw_budget:
        if raw_budget > 1000:
            lead_budget_cr = float(raw_budget) / 10000000.0  # 1 Cr = 10,000,000 INR
        else:
            lead_budget_cr = float(raw_budget)

    for emp in employees:
        # Category check
        if target_category and emp.handled_categories:
            emp_categories = [c.upper() for c in emp.handled_categories]
            if target_category not in emp_categories:
                continue

        # Budget check (if employee has budget constraints defined)
        if lead_budget_cr is not None:
            min_cr = float(emp.budget_min_cr) if emp.budget_min_cr is not None else None
            max_cr = float(emp.budget_max_cr) if emp.budget_max_cr is not None else None

            if min_cr is not None and lead_budget_cr < min_cr:
                continue
            if max_cr is not None and lead_budget_cr > max_cr:
                continue

        candidates.append(emp)

    if not candidates:
        # Fallback to all active employees if strict filters produce no candidates
        candidates = list(employees)

    # 3. Round-Robin Selection: find the candidate with the fewest currently assigned leads
    # Query count of leads assigned to each candidate
    candidate_ids = [c.employee_id for c in candidates]
    count_stmt = (
        select(Lead.assigned_to, func.count(Lead.id).label("lead_count"))
        .where(Lead.assigned_to.in_(candidate_ids))
        .group_by(Lead.assigned_to)
    )
    count_res = await db.execute(count_stmt)
    counts_map = {row[0]: row[1] for row in count_res.all()}

    # Sort candidates by lead count ascending, then by employee_id ascending for deterministic round-robin
    candidates.sort(key=lambda c: (counts_map.get(c.employee_id, 0), c.employee_id))
    selected_emp = candidates[0]

    # 4. Leave Cover Check: If candidate is on leave, reroute to leave_approver or reporting manager
    if getattr(selected_emp, "is_on_leave", False):
        backup_id = selected_emp.leave_approver or selected_emp.reporting_to
        if backup_id:
            backup_stmt = select(Employee).where(
                and_(Employee.employee_id == backup_id, Employee.is_active == True)
            )
            backup_res = await db.execute(backup_stmt)
            backup_emp = backup_res.scalar_one_or_none()
            if backup_emp and not getattr(backup_emp, "is_on_leave", False):
                logger.info(
                    "Employee %s is on leave. Rerouting lead %s to backup %s",
                    selected_emp.employee_id,
                    lead.lead_id,
                    backup_emp.employee_id,
                )
                selected_emp = backup_emp

    # 5. Assign lead and record activity
    lead.assigned_to = selected_emp.employee_id
    activity = LeadActivity(
        lead_id=lead.lead_id,
        action_type="LEAD_ASSIGNED",
        outcome="ASSIGNED",
        note=f"Assigned to {selected_emp.name} ({selected_emp.employee_id}) via {routing_mode}",
        performed_by="SYSTEM",
        stage_before=lead.stage,
        stage_after=lead.stage,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(lead)

    return selected_emp
