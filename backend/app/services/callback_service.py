from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.callbacks import (
    CALLBACK_STATUSES,
    DISQUALIFIED_REASONS,
    CallbackActivity,
    CallbackRescheduleLog,
    TblCallback,
)
from app.models.identity import Employee, Role
from app.models.inquiries import WebsiteInquiry
from app.models.leads import Lead, LeadActivity, TblLead
from app.models.properties import Property
from app.services.intake_service import get_next_lead_id, normalize_phone

IST = timezone(timedelta(hours=5, minutes=30))
VIEW_ALL_ROLES = {"SUPER_ADMIN", "MD", "SALES_MANAGER"}
CLOSED_TERMINAL_STATUSES = (5, 6)
LOCKING_STATUSES = (2, 3, 5, 6)


def _ensure_utc(dt: datetime) -> datetime:
    """Normalize a naive or timezone-aware datetime to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_agg_datetime(value: Any) -> Optional[datetime]:
    """Normalize aggregate datetime values returned by SQLite or PostgreSQL."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return _ensure_utc(value)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _ensure_utc(parsed)
    return None


def _ist_today_bounds_utc(now_utc: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """Compute IST day start/end converted to UTC for consistent SQL filtering."""
    now = _ensure_utc(now_utc or datetime.now(timezone.utc))
    now_ist = now.astimezone(IST)
    start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    end_ist = now_ist.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start_ist.astimezone(timezone.utc), end_ist.astimezone(timezone.utc)


def _clean_mobile_digits(raw_mobile: str) -> str:
    digits = re.sub(r"\D", "", (raw_mobile or "").strip())
    if not digits:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid mobile number is required.",
        )
    return digits


class CallbackService:
    """Service managing Request A Callback intake, round-robin routing, state machine & conversion."""

    def has_view_all(self, emp: Optional[Employee]) -> bool:
        """Return True if employee holds SUPER_ADMIN/MD/SALES_MANAGER or leads.view_all / all.*."""
        if not emp or not emp.role:
            return False
        role_code = (emp.role.code or "").upper()
        if role_code in VIEW_ALL_ROLES:
            return True

        perms = emp.role.permissions or {}
        if isinstance(perms, dict):
            all_perms = perms.get("all") or []
            lead_perms = perms.get("leads") or []
            if "*" in all_perms or "all.*" in all_perms:
                return True
            if "view_all" in lead_perms or "*" in lead_perms or "leads.view_all" in lead_perms:
                return True
            if perms.get("leads.view_all") is True or perms.get("all.*") is True:
                return True
        elif isinstance(perms, (list, tuple, set)):
            if "leads.view_all" in perms or "all.*" in perms or "*" in perms:
                return True
        return False

    async def _pick_round_robin_telecaller(self, db: AsyncSession) -> Optional[str]:
        """Select next active TELECALLER deterministically by fewest callbacks & oldest last assignment."""
        emp_stmt = (
            select(Employee.employee_id)
            .join(Role, Employee.role_id == Role.id)
            .where(
                Role.code == "TELECALLER",
                Role.is_active.is_(True),
                Role.deleted_at.is_(None),
                Employee.is_active.is_(True),
                Employee.is_on_leave.is_(False),
                Employee.deleted_at.is_(None),
            )
        )
        candidate_ids = list((await db.execute(emp_stmt)).scalars().all())
        if not candidate_ids:
            return None

        stats_stmt = (
            select(
                TblCallback.assigned_user_id,
                func.count(TblCallback.callback_id),
                func.max(TblCallback.created_date),
            )
            .where(
                TblCallback.deleted_at.is_(None),
                TblCallback.assigned_user_id.in_(candidate_ids),
            )
            .group_by(TblCallback.assigned_user_id)
        )
        stats: Dict[str, Tuple[int, Optional[datetime]]] = {cid: (0, None) for cid in candidate_ids}
        for emp_id, total_count, latest_dt in (await db.execute(stats_stmt)).all():
            if emp_id in stats:
                stats[emp_id] = (int(total_count or 0), _parse_agg_datetime(latest_dt))

        epoch_min = datetime.min.replace(tzinfo=timezone.utc)

        def _sort_key(emp_id: str) -> Tuple[int, int, datetime, str]:
            count, latest = stats[emp_id]
            return (count, 0 if latest is None else 1, latest or epoch_min, emp_id)

        return min(candidate_ids, key=_sort_key)

    def _serialize_callback(
        self,
        cb: TblCallback,
        *,
        assigned_user_name: Optional[str] = None,
        property_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "callback_id": cb.callback_id,
            "lead_unique_id": cb.lead_unique_id,
            "name": cb.name,
            "mobile_number": cb.mobile_number,
            "phone_code": cb.phone_code,
            "message": cb.message,
            "property_id": cb.property_id,
            "property_code": cb.property_code,
            "property_title": property_title,
            "assigned_user_id": cb.assigned_user_id,
            "assigned_user_name": assigned_user_name,
            "lead_status": cb.lead_status,
            "status_label": CALLBACK_STATUSES.get(cb.lead_status, "Unknown"),
            "calls_status": cb.calls_status,
            "lead_open": cb.lead_open,
            "disqualified_reason": cb.disqualified_reason,
            "disqualified_reason_label": DISQUALIFIED_REASONS.get(cb.disqualified_reason),
            "current_update": cb.current_update,
            "last_remark": cb.last_remark,
            "followup_datetime": cb.followup_datetime.isoformat() if cb.followup_datetime else None,
            "opportunity_converted": cb.opportunity_converted,
            "lead_converted": cb.lead_converted,
            "converted_lead_id": cb.converted_lead_id,
            "website_inquiry_id": cb.website_inquiry_id,
            "created_date": cb.created_date.isoformat() if cb.created_date else None,
            "modified_date": cb.modified_date.isoformat() if cb.modified_date else None,
        }

    def _scope_filters(self, actor: Employee) -> List[Any]:
        filters: List[Any] = [TblCallback.deleted_at.is_(None)]
        if not self.has_view_all(actor):
            filters.append(TblCallback.assigned_user_id == actor.employee_id)
        return filters

    def _tab_filters(self, tab: str, now_utc: datetime) -> List[Any]:
        today_start_utc, today_end_utc = _ist_today_bounds_utc(now_utc)
        normalized_tab = (tab or "new").strip().lower()
        if normalized_tab == "new":
            return [TblCallback.lead_status == 0]
        if normalized_tab == "today":
            return [
                TblCallback.followup_datetime.is_not(None),
                TblCallback.followup_datetime >= today_start_utc,
                TblCallback.followup_datetime <= today_end_utc,
                TblCallback.lead_open == 1,
            ]
        if normalized_tab == "open":
            return [TblCallback.lead_open == 1]
        if normalized_tab == "missing":
            return [
                TblCallback.followup_datetime.is_not(None),
                TblCallback.followup_datetime < now_utc,
                TblCallback.lead_open == 1,
                TblCallback.lead_status.notin_(list(LOCKING_STATUSES)),
            ]
        if normalized_tab == "converted":
            return [TblCallback.lead_status == 5]
        if normalized_tab == "converted_property":
            return [TblCallback.lead_status == 6]
        return []

    async def _get_scoped_callback(
        self, db: AsyncSession, actor: Employee, callback_id: int
    ) -> TblCallback:
        stmt = select(TblCallback).where(
            TblCallback.callback_id == callback_id,
            TblCallback.deleted_at.is_(None),
        )
        cb = (await db.execute(stmt)).scalar_one_or_none()
        if not cb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Callback #{callback_id} not found",
            )
        if not self.has_view_all(actor) and cb.assigned_user_id != actor.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this callback.",
            )
        return cb

    def _ensure_open_for_mutation(self, cb: TblCallback, action_phrase: str) -> None:
        if cb.lead_open == 0 or cb.lead_status in CLOSED_TERMINAL_STATUSES or cb.lead_converted == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This Callback is closed so you cannot {action_phrase}.",
            )

    async def _employee_name_map(
        self, db: AsyncSession, employee_ids: List[Optional[str]]
    ) -> Dict[str, str]:
        clean_ids = sorted({eid for eid in employee_ids if eid})
        if not clean_ids:
            return {}
        res = await db.execute(
            select(Employee.employee_id, Employee.name).where(Employee.employee_id.in_(clean_ids))
        )
        return {emp_id: emp_name for emp_id, emp_name in res.all()}

    async def _get_active_employee(
        self, db: AsyncSession, employee_id: str, *, label: str = "Target assignee"
    ) -> Employee:
        clean_id = (employee_id or "").strip()
        emp = (
            await db.execute(
                select(Employee).where(
                    Employee.employee_id == clean_id,
                    Employee.is_active.is_(True),
                    Employee.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{label} '{clean_id}' not found or inactive.",
            )
        return emp

    async def create_callback(
        self,
        db: AsyncSession,
        *,
        name: str,
        mobile_number: str,
        phone_code: str = "+91",
        message: Optional[str] = None,
        property_id: Optional[int] = None,
        property_code: Optional[str] = None,
        assigned_user_id: Optional[str] = None,
        website_inquiry_id: Optional[int] = None,
        actor_emp_id: Optional[str] = None,
        enforce_caller_scope: bool = False,
    ) -> TblCallback:
        clean_name = (name or "").strip()
        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer name is required.",
            )
        clean_mobile = _clean_mobile_digits(mobile_number)
        clean_code = (phone_code or "+91").strip() or "+91"

        target_assignee = assigned_user_id.strip() if isinstance(assigned_user_id, str) and assigned_user_id.strip() else None

        if enforce_caller_scope and actor_emp_id:
            actor_res = await db.execute(
                select(Employee).where(
                    Employee.employee_id == actor_emp_id,
                    Employee.deleted_at.is_(None),
                )
            )
            actor = actor_res.scalar_one_or_none()
            if actor and not self.has_view_all(actor):
                target_assignee = actor.employee_id

        if target_assignee is not None:
            valid_assignee = await self._get_active_employee(
                db, target_assignee, label="Assigned telecaller"
            )
            target_assignee = valid_assignee.employee_id
        else:
            target_assignee = await self._pick_round_robin_telecaller(db)

        cb = TblCallback(
            name=clean_name,
            mobile_number=clean_mobile,
            phone_code=clean_code,
            message=message.strip() if isinstance(message, str) and message.strip() else None,
            property_id=property_id,
            property_code=property_code.strip() if isinstance(property_code, str) and property_code.strip() else None,
            assigned_user_id=target_assignee,
            website_inquiry_id=website_inquiry_id,
        )
        db.add(cb)
        await db.flush()

        cb.lead_unique_id = f"WEB{cb.callback_id}"

        activity = CallbackActivity(
            callback_id=cb.callback_id,
            action_type="RECEIVED",
            title="Received",
            status_before=None,
            status_after=0,
            remark=cb.message or "Inbound callback request received",
            performed_by=actor_emp_id or "SYSTEM",
        )
        db.add(activity)
        await db.commit()
        await db.refresh(cb)
        return cb

    async def get_dashboard_counts(self, db: AsyncSession, actor: Employee) -> Dict[str, int]:
        now_utc = datetime.now(timezone.utc)
        base = self._scope_filters(actor)

        async def _count(extra: List[Any]) -> int:
            stmt = select(func.count(TblCallback.callback_id)).where(and_(*base, *extra))
            return int((await db.execute(stmt)).scalar() or 0)

        return {
            "new_calls": await _count(self._tab_filters("new", now_utc)),
            "today_calls": await _count(self._tab_filters("today", now_utc)),
            "open_calls": await _count(self._tab_filters("open", now_utc)),
            "missing_calls": await _count(self._tab_filters("missing", now_utc)),
            "converted_leads": await _count(self._tab_filters("converted", now_utc)),
            "all_calls": await _count([]),
            "converted_property": await _count(self._tab_filters("converted_property", now_utc)),
        }

    async def list_callbacks(
        self,
        db: AsyncSession,
        actor: Employee,
        *,
        tab: str = "new",
        search: Optional[str] = None,
        sort_by: str = "created_date",
        order_by: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        now_utc = datetime.now(timezone.utc)
        conditions = self._scope_filters(actor) + self._tab_filters(tab, now_utc)

        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append(
                or_(
                    TblCallback.name.ilike(term),
                    TblCallback.mobile_number.ilike(term),
                    TblCallback.lead_unique_id.ilike(term),
                    TblCallback.property_code.ilike(term),
                    TblCallback.message.ilike(term),
                )
            )

        sort_map = {
            "created_date": TblCallback.created_date,
            "followup_datetime": TblCallback.followup_datetime,
            "name": TblCallback.name,
            "callback_id": TblCallback.callback_id,
        }
        sort_col = sort_map.get(sort_by, TblCallback.created_date)
        order_fn = asc if (order_by or "desc").lower() == "asc" else desc

        where_clause = and_(*conditions)
        total_stmt = select(func.count(TblCallback.callback_id)).where(where_clause)
        total = int((await db.execute(total_stmt)).scalar() or 0)

        rows_stmt = (
            select(TblCallback)
            .where(where_clause)
            .order_by(order_fn(sort_col), desc(TblCallback.callback_id))
            .offset(offset)
            .limit(limit)
        )
        rows = list((await db.execute(rows_stmt)).scalars().all())
        name_map = await self._employee_name_map(db, [r.assigned_user_id for r in rows])

        items = [
            self._serialize_callback(r, assigned_user_name=name_map.get(r.assigned_user_id or ""))
            for r in rows
        ]
        return total, items

    async def get_callback_detail(
        self, db: AsyncSession, actor: Employee, callback_id: int
    ) -> Dict[str, Any]:
        cb = await self._get_scoped_callback(db, actor, callback_id)

        resched_stmt = (
            select(CallbackRescheduleLog)
            .where(CallbackRescheduleLog.callback_id == cb.callback_id)
            .order_by(desc(CallbackRescheduleLog.created_at), desc(CallbackRescheduleLog.id))
        )
        resched_rows = list((await db.execute(resched_stmt)).scalars().all())

        act_stmt = (
            select(CallbackActivity)
            .where(CallbackActivity.callback_id == cb.callback_id)
            .order_by(desc(CallbackActivity.created_at), desc(CallbackActivity.id))
        )
        act_rows = list((await db.execute(act_stmt)).scalars().all())

        emp_ids = [cb.assigned_user_id] + [r.rescheduled_by for r in resched_rows] + [
            a.performed_by for a in act_rows
        ]
        name_map = await self._employee_name_map(db, emp_ids)

        property_title: Optional[str] = None
        if cb.property_id:
            prop = (
                await db.execute(select(Property).where(Property.id == cb.property_id))
            ).scalar_one_or_none()
            if prop:
                property_title = prop.title
        elif cb.property_code:
            prop = (
                await db.execute(select(Property).where(Property.property_id == cb.property_code))
            ).scalar_one_or_none()
            if prop:
                property_title = prop.title

        detail = self._serialize_callback(
            cb,
            assigned_user_name=name_map.get(cb.assigned_user_id or ""),
            property_title=property_title,
        )
        detail["reschedule_history"] = [
            {
                "id": r.id,
                "callback_id": r.callback_id,
                "old_followup_datetime": r.old_followup_datetime.isoformat()
                if r.old_followup_datetime
                else None,
                "new_followup_datetime": r.new_followup_datetime.isoformat(),
                "current_update": r.current_update,
                "remark": r.remark,
                "rescheduled_by": r.rescheduled_by,
                "rescheduled_by_name": name_map.get(r.rescheduled_by or "") or r.rescheduled_by,
                "created_at": r.created_at.isoformat(),
            }
            for r in resched_rows
        ]
        detail["activities"] = [
            {
                "id": a.id,
                "callback_id": a.callback_id,
                "action_type": a.action_type,
                "title": a.title,
                "status_before": a.status_before,
                "status_after": a.status_after,
                "remark": a.remark,
                "performed_by": a.performed_by,
                "performed_by_name": name_map.get(a.performed_by or "") or a.performed_by,
                "created_at": a.created_at.isoformat(),
            }
            for a in act_rows
        ]
        return detail

    async def log_callback_call(
        self,
        db: AsyncSession,
        actor: Employee,
        callback_id: int,
        *,
        remark: Optional[str] = None,
    ) -> Dict[str, Any]:
        cb = await self._get_scoped_callback(db, actor, callback_id)
        cb.calls_status = 1
        clean_remark = remark.strip() if isinstance(remark, str) and remark.strip() else None
        if clean_remark:
            cb.last_remark = clean_remark

        activity = CallbackActivity(
            callback_id=cb.callback_id,
            action_type="CALL_LOG",
            title="Call Logged",
            status_before=cb.lead_status,
            status_after=cb.lead_status,
            remark=clean_remark or "Call connected",
            performed_by=actor.employee_id,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(cb)

        name_map = await self._employee_name_map(db, [cb.assigned_user_id])
        return self._serialize_callback(cb, assigned_user_name=name_map.get(cb.assigned_user_id or ""))

    async def reschedule_callback(
        self,
        db: AsyncSession,
        actor: Employee,
        callback_id: int,
        *,
        current_update: str,
        remark: str,
        followup_datetime: datetime,
    ) -> Dict[str, Any]:
        cb = await self._get_scoped_callback(db, actor, callback_id)
        self._ensure_open_for_mutation(cb, "reschedule it")

        clean_remark = (remark or "").strip()
        if not clean_remark:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remark is required for rescheduling.",
            )

        new_dt = _ensure_utc(followup_datetime)
        if new_dt <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Schedule Date and Time should be greater than the current date and time.",
            )

        old_dt = _ensure_utc(cb.followup_datetime) if cb.followup_datetime else None
        clean_update = (current_update or "").strip() or None

        log_entry = CallbackRescheduleLog(
            callback_id=cb.callback_id,
            old_followup_datetime=old_dt,
            new_followup_datetime=new_dt,
            current_update=clean_update,
            remark=clean_remark,
            rescheduled_by=actor.employee_id,
        )
        db.add(log_entry)

        cb.followup_datetime = new_dt
        cb.current_update = clean_update
        cb.last_remark = clean_remark

        activity = CallbackActivity(
            callback_id=cb.callback_id,
            action_type="RESCHEDULED",
            title="Rescheduled",
            status_before=cb.lead_status,
            status_after=cb.lead_status,
            remark=f"{clean_update}: {clean_remark}" if clean_update else clean_remark,
            performed_by=actor.employee_id,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(cb)

        name_map = await self._employee_name_map(db, [cb.assigned_user_id])
        return self._serialize_callback(cb, assigned_user_name=name_map.get(cb.assigned_user_id or ""))

    async def change_callback_status(
        self,
        db: AsyncSession,
        actor: Employee,
        callback_id: int,
        *,
        lead_status: int,
        remark: str,
        disqualified_reason: Optional[int] = None,
        calls_status: Optional[int] = None,
    ) -> Dict[str, Any]:
        cb = await self._get_scoped_callback(db, actor, callback_id)
        self._ensure_open_for_mutation(cb, "change its status")

        if lead_status == 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use Convert to Lead to mark a callback as Converted to Lead.",
            )
        if lead_status not in CALLBACK_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid callback status: {lead_status}",
            )

        clean_remark = (remark or "").strip()
        if not clean_remark:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remark is required when changing callback status.",
            )

        if lead_status == 2:
            if disqualified_reason is None or disqualified_reason not in DISQUALIFIED_REASONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A valid disqualified_reason (1..7) is required when marking Disqualified.",
                )
            cb.disqualified_reason = disqualified_reason
        else:
            cb.disqualified_reason = 0

        status_before = cb.lead_status
        cb.lead_status = lead_status
        cb.last_remark = clean_remark
        if calls_status is not None:
            cb.calls_status = calls_status

        if lead_status in (2, 3, 6):
            cb.lead_open = 0
        if lead_status == 6:
            cb.lead_converted = 1

        activity = CallbackActivity(
            callback_id=cb.callback_id,
            action_type="STATUS_CHANGED",
            title=f"Status Changed to {CALLBACK_STATUSES[lead_status]}",
            status_before=status_before,
            status_after=lead_status,
            remark=clean_remark,
            performed_by=actor.employee_id,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(cb)

        name_map = await self._employee_name_map(db, [cb.assigned_user_id])
        return self._serialize_callback(cb, assigned_user_name=name_map.get(cb.assigned_user_id or ""))

    async def transfer_callback(
        self,
        db: AsyncSession,
        actor: Employee,
        callback_id: int,
        *,
        assigned_user_id: str,
        remark: str,
    ) -> Dict[str, Any]:
        cb = await self._get_scoped_callback(db, actor, callback_id)
        self._ensure_open_for_mutation(cb, "transfer it")

        target_emp = await self._get_active_employee(
            db, assigned_user_id, label="Target assignee"
        )

        clean_remark = (remark or "").strip()
        if not clean_remark:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remark is required for transferring a callback.",
            )

        status_before = cb.lead_status
        cb.assigned_user_id = target_emp.employee_id
        cb.lead_status = 0
        cb.calls_status = 0
        cb.last_remark = clean_remark

        activity = CallbackActivity(
            callback_id=cb.callback_id,
            action_type="TRANSFERRED",
            title="Transferred",
            status_before=status_before,
            status_after=0,
            remark=f"Transferred to {target_emp.name} ({target_emp.employee_id}): {clean_remark}",
            performed_by=actor.employee_id,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(cb)

        return self._serialize_callback(cb, assigned_user_name=target_emp.name)

    async def reopen_callback(
        self,
        db: AsyncSession,
        actor: Employee,
        callback_id: int,
        *,
        remark: Optional[str] = None,
    ) -> Dict[str, Any]:
        cb = await self._get_scoped_callback(db, actor, callback_id)
        if cb.lead_status in CLOSED_TERMINAL_STATUSES or cb.lead_converted == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Converted callbacks cannot be reopened.",
            )
        if cb.lead_open == 1 or cb.lead_status not in (2, 3):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only closed Disqualified or Solved callbacks can be reopened.",
            )

        status_before = cb.lead_status
        cb.lead_open = 1
        cb.lead_status = 1
        cb.disqualified_reason = 0
        clean_remark = remark.strip() if isinstance(remark, str) and remark.strip() else None
        if clean_remark:
            cb.last_remark = clean_remark

        activity = CallbackActivity(
            callback_id=cb.callback_id,
            action_type="REOPENED",
            title="Reopened",
            status_before=status_before,
            status_after=1,
            remark=clean_remark or "Callback reopened",
            performed_by=actor.employee_id,
        )
        db.add(activity)
        await db.commit()
        await db.refresh(cb)

        name_map = await self._employee_name_map(db, [cb.assigned_user_id])
        return self._serialize_callback(cb, assigned_user_name=name_map.get(cb.assigned_user_id or ""))

    async def convert_callback_to_lead(
        self,
        db: AsyncSession,
        actor: Employee,
        callback_id: int,
        *,
        customer_type: str,
        name: str,
        email: Optional[str],
        mobile: str,
        alternate_mobile: Optional[str],
        address: str,
        refer_by_relation: Optional[str],
        refer_by_name: Optional[str],
        refer_by_mobile: Optional[str],
        source: str,
        assigned_to: Optional[str],
    ) -> Dict[str, Any]:
        cb = await self._get_scoped_callback(db, actor, callback_id)
        self._ensure_open_for_mutation(cb, "convert it to a lead")

        linked_inquiry: Optional[WebsiteInquiry] = None
        if cb.website_inquiry_id:
            linked_inquiry = (
                await db.execute(
                    select(WebsiteInquiry).where(WebsiteInquiry.id == cb.website_inquiry_id)
                )
            ).scalar_one_or_none()
            if linked_inquiry and linked_inquiry.is_converted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Website inquiry #{linked_inquiry.id} is already converted to lead {linked_inquiry.converted_lead_id}",
                )

        explicit_assignee = (
            assigned_to.strip()
            if isinstance(assigned_to, str) and assigned_to.strip()
            else None
        )
        if explicit_assignee is not None:
            valid_assignee = await self._get_active_employee(
                db, explicit_assignee, label="Assignee"
            )
            final_assignee = valid_assignee.employee_id
        else:
            final_assignee = cb.assigned_user_id or actor.employee_id

        lead_id = await get_next_lead_id(db)
        norm_mobile = normalize_phone(mobile or cb.mobile_number)
        clean_name = (name or cb.name).strip()
        lead_type = (customer_type or "BUY").strip().upper()
        clean_source = (source or "Website Callback").strip()
        clean_address = address.strip() if isinstance(address, str) and address.strip() else None

        new_lead = Lead(
            lead_id=lead_id,
            full_name=clean_name,
            mobile=norm_mobile,
            email=email.strip() if isinstance(email, str) and email.strip() else None,
            lead_type=lead_type,
            source=clean_source,
            related_listing_id=cb.property_code,
            assigned_to=final_assignee,
            stage="NEW",
            preferred_locality=clean_address[:100] if clean_address else None,
            is_untouched=True,
            is_duplicate=False,
            is_test=False,
        )
        db.add(new_lead)

        tbl_lead = TblLead(
            lead_unique_id=lead_id,
            contact_name=clean_name,
            mobile=norm_mobile,
            email=new_lead.email,
            address=clean_address,
            lead_table_name=lead_type,
            lead_source_id=4,
            property_id=cb.property_id or 0,
            property_idno=cb.property_code,
            indv_property_address=clean_address,
            reference_relation_by=refer_by_relation,
            refer_by_name=refer_by_name,
            refer_by_mobile=refer_by_mobile,
            alternate_contact_mobile=alternate_mobile,
            lead_remark=cb.last_remark or cb.message,
            calls_status=cb.calls_status,
            lead_status=0,
            stage=1,
            lead_open=1,
            rating=3,
            create_by=actor.employee_id,
        )
        db.add(tbl_lead)
        await db.flush()

        lead_activity = LeadActivity(
            lead_id=lead_id,
            action_type="CONVERSION",
            outcome="Callback Converted",
            note=f"Converted from Callback {cb.lead_unique_id}",
            logged_by=actor.employee_id,
            performed_by=actor.employee_id,
        )
        db.add(lead_activity)

        status_before = cb.lead_status
        cb.lead_status = 5
        cb.lead_converted = 1
        cb.lead_open = 0
        cb.converted_lead_id = lead_id

        cb_activity = CallbackActivity(
            callback_id=cb.callback_id,
            action_type="CONVERTED",
            title="Converted to Lead",
            status_before=status_before,
            status_after=5,
            remark=f"Converted to Lead {lead_id}",
            performed_by=actor.employee_id,
        )
        db.add(cb_activity)

        if linked_inquiry:
            linked_inquiry.is_converted = True
            linked_inquiry.converted_lead_id = lead_id
            linked_inquiry.converted_by_emp_id = actor.employee_id
            linked_inquiry.converted_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(cb)

        name_map = await self._employee_name_map(db, [cb.assigned_user_id])
        return {
            "lead_id": lead_id,
            "tbl_lead_id": tbl_lead.leads_id,
            "callback": self._serialize_callback(
                cb, assigned_user_name=name_map.get(cb.assigned_user_id or "")
            ),
        }

    async def export_callbacks_xls(
        self,
        db: AsyncSession,
        actor: Employee,
        *,
        tab: str = "all",
        search: Optional[str] = None,
        sort_by: str = "created_date",
        order_by: str = "desc",
    ) -> str:
        _, items = await self.list_callbacks(
            db,
            actor,
            tab=tab,
            search=search,
            sort_by=sort_by,
            order_by=order_by,
            limit=5000,
            offset=0,
        )
        headers = [
            "Request ID",
            "Customer Name",
            "Phone Code",
            "Mobile Number",
            "Status",
            "Call Connected",
            "Open State",
            "Assigned To",
            "Current Update",
            "Last Remark",
            "Follow-up Datetime",
            "Property Code",
            "Converted Lead ID",
            "Created Date",
        ]
        header_cells = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
        rows_html: List[str] = []
        for item in items:
            vals = [
                item.get("lead_unique_id") or "",
                item.get("name") or "",
                item.get("phone_code") or "+91",
                item.get("mobile_number") or "",
                item.get("status_label") or "",
                "Yes" if item.get("calls_status") == 1 else "No",
                "Open" if item.get("lead_open") == 1 else "Closed",
                item.get("assigned_user_name") or item.get("assigned_user_id") or "Unassigned",
                item.get("current_update") or "",
                item.get("last_remark") or "",
                item.get("followup_datetime") or "",
                item.get("property_code") or "",
                item.get("converted_lead_id") or "",
                item.get("created_date") or "",
            ]
            cells = "".join(f"<td>{html.escape(str(v))}</td>" for v in vals)
            rows_html.append(f"<tr>{cells}</tr>")

        return (
            "<html><head><meta charset='UTF-8'></head><body>"
            "<table border='1'>"
            f"<thead><tr>{header_cells}</tr></thead>"
            f"<tbody>{''.join(rows_html)}</tbody>"
            "</table></body></html>"
        )


callback_service = CallbackService()
