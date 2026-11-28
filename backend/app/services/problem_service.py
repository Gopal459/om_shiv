from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.callbacks import PROBLEM_STATUSES
from app.models.identity import Employee
from app.models.inquiries import WebsiteInquiry
from app.models.leads import Lead
from app.models.properties import Property
from app.services.intake_service import intake_service

PROBLEM_VIEW_ALL_ROLES = {"SUPER_ADMIN", "MD", "SALES_MANAGER", "VERIFICATION_OFFICER"}


class ProblemService:
    """Service managing Report A Problem triage, scoping, conversion, and XLS export."""

    def has_problem_view_all(self, emp: Optional[Employee]) -> bool:
        """Return True for roles allowed to view/triage all PROBLEM_REPORT inquiries."""
        if not emp or not emp.role:
            return False
        role_code = (emp.role.code or "").upper()
        if role_code in PROBLEM_VIEW_ALL_ROLES:
            return True

        perms = emp.role.permissions or {}
        if isinstance(perms, dict):
            all_perms = perms.get("all") or []
            lead_perms = perms.get("leads") or []
            prop_perms = perms.get("properties") or []
            if "*" in all_perms or "all.*" in all_perms:
                return True
            if "view_all" in lead_perms or "*" in lead_perms or "leads.view_all" in lead_perms:
                return True
            if "verify" in prop_perms or "*" in prop_perms or "properties.verify" in prop_perms:
                return True
            if (
                perms.get("leads.view_all") is True
                or perms.get("properties.verify") is True
                or perms.get("all.*") is True
            ):
                return True
        elif isinstance(perms, (list, tuple, set)):
            if any(p in perms for p in ("leads.view_all", "properties.verify", "all.*", "*")):
                return True
        return False

    def _scope_filters(self, actor: Employee) -> List[Any]:
        filters: List[Any] = [
            WebsiteInquiry.inquiry_type == "PROBLEM_REPORT",
            WebsiteInquiry.deleted_at.is_(None),
        ]
        if not self.has_problem_view_all(actor):
            filters.append(WebsiteInquiry.assigned_to == actor.employee_id)
        return filters

    async def _get_scoped_problem(
        self, db: AsyncSession, actor: Employee, inquiry_id: int
    ) -> WebsiteInquiry:
        stmt = select(WebsiteInquiry).where(
            WebsiteInquiry.id == inquiry_id,
            WebsiteInquiry.inquiry_type == "PROBLEM_REPORT",
            WebsiteInquiry.deleted_at.is_(None),
        )
        inquiry = (await db.execute(stmt)).scalar_one_or_none()
        if not inquiry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem report #{inquiry_id} not found",
            )
        if not self.has_problem_view_all(actor) and inquiry.assigned_to != actor.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this problem report.",
            )
        return inquiry

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

    async def _property_title_maps(
        self, db: AsyncSession, inquiries: List[WebsiteInquiry]
    ) -> Tuple[Dict[str, str], Dict[int, str]]:
        codes: set[str] = set()
        prop_ids: set[int] = set()
        for inq in inquiries:
            details = inq.details if isinstance(inq.details, dict) else {}
            code = inq.related_property_code or details.get("property_code") or details.get("related_property_code")
            if isinstance(code, str) and code.strip():
                codes.add(code.strip())
            raw_pid = details.get("property_id")
            if raw_pid is not None:
                try:
                    prop_ids.add(int(raw_pid))
                except (TypeError, ValueError):
                    pass

        by_code: Dict[str, str] = {}
        by_id: Dict[int, str] = {}
        if codes:
            res = await db.execute(
                select(Property.property_id, Property.title).where(Property.property_id.in_(sorted(codes)))
            )
            by_code = {p_code: p_title for p_code, p_title in res.all()}
        if prop_ids:
            res = await db.execute(
                select(Property.id, Property.title).where(Property.id.in_(sorted(prop_ids)))
            )
            by_id = {pid: p_title for pid, p_title in res.all()}
        return by_code, by_id

    def _serialize_problem(
        self,
        inq: WebsiteInquiry,
        *,
        emp_names: Dict[str, str],
        prop_by_code: Dict[str, str],
        prop_by_id: Dict[int, str],
    ) -> Dict[str, Any]:
        details = inq.details if isinstance(inq.details, dict) else None
        prop_code = inq.related_property_code
        if not prop_code and details:
            raw_code = details.get("property_code") or details.get("related_property_code")
            if isinstance(raw_code, str) and raw_code.strip():
                prop_code = raw_code.strip()

        prop_title: Optional[str] = prop_by_code.get(prop_code or "")
        if not prop_title and details and details.get("property_id") is not None:
            try:
                prop_title = prop_by_id.get(int(details["property_id"]))
            except (TypeError, ValueError):
                prop_title = None

        return {
            "id": inq.id,
            "inquiry_type": inq.inquiry_type,
            "full_name": inq.full_name,
            "mobile": inq.mobile,
            "email": inq.email,
            "details": details,
            "status": inq.status,
            "assigned_to": inq.assigned_to,
            "assigned_to_name": emp_names.get(inq.assigned_to or ""),
            "related_property_code": prop_code,
            "property_title": prop_title,
            "resolution_remark": inq.resolution_remark,
            "resolved_by": inq.resolved_by,
            "resolved_by_name": emp_names.get(inq.resolved_by or ""),
            "resolved_at": inq.resolved_at.isoformat() if inq.resolved_at else None,
            "is_converted": inq.is_converted,
            "converted_lead_id": inq.converted_lead_id,
            "converted_by_emp_id": inq.converted_by_emp_id,
            "converted_at": inq.converted_at.isoformat() if inq.converted_at else None,
            "created_at": inq.created_at.isoformat() if inq.created_at else None,
            "updated_at": inq.updated_at.isoformat() if inq.updated_at else None,
        }

    async def list_problems(
        self,
        db: AsyncSession,
        actor: Employee,
        *,
        status_filter: str = "ALL",
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        base = self._scope_filters(actor)

        async def _count_status(target_status: Optional[str] = None) -> int:
            conds = list(base)
            if target_status is not None:
                conds.append(WebsiteInquiry.status == target_status)
            stmt = select(func.count(WebsiteInquiry.id)).where(and_(*conds))
            return int((await db.execute(stmt)).scalar() or 0)

        counts = {
            "all": await _count_status(),
            "new": await _count_status("NEW"),
            "in_review": await _count_status("IN_REVIEW"),
            "resolved": await _count_status("RESOLVED"),
            "rejected": await _count_status("REJECTED"),
        }

        conditions = list(base)
        norm_status = (status_filter or "ALL").strip().upper()
        if norm_status != "ALL":
            if norm_status not in PROBLEM_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid problem status filter: {status_filter}",
                )
            conditions.append(WebsiteInquiry.status == norm_status)

        if search and search.strip():
            term = f"%{search.strip()}%"
            conditions.append(
                or_(
                    WebsiteInquiry.full_name.ilike(term),
                    WebsiteInquiry.mobile.ilike(term),
                    WebsiteInquiry.email.ilike(term),
                    WebsiteInquiry.related_property_code.ilike(term),
                    WebsiteInquiry.resolution_remark.ilike(term),
                )
            )

        where_clause = and_(*conditions)
        total = int(
            (await db.execute(select(func.count(WebsiteInquiry.id)).where(where_clause))).scalar()
            or 0
        )

        rows_stmt = (
            select(WebsiteInquiry)
            .where(where_clause)
            .order_by(desc(WebsiteInquiry.created_at), desc(WebsiteInquiry.id))
            .offset(offset)
            .limit(limit)
        )
        rows = list((await db.execute(rows_stmt)).scalars().all())

        emp_names = await self._employee_name_map(
            db, [r.assigned_to for r in rows] + [r.resolved_by for r in rows]
        )
        prop_by_code, prop_by_id = await self._property_title_maps(db, rows)
        items = [
            self._serialize_problem(
                r, emp_names=emp_names, prop_by_code=prop_by_code, prop_by_id=prop_by_id
            )
            for r in rows
        ]
        return {"total": total, "counts": counts, "items": items}

    async def update_problem_triage(
        self,
        db: AsyncSession,
        actor: Employee,
        inquiry_id: int,
        *,
        status_val: Optional[str] = None,
        assigned_to: Optional[str] = None,
        resolution_remark: Optional[str] = None,
    ) -> Dict[str, Any]:
        inquiry = await self._get_scoped_problem(db, actor, inquiry_id)

        if status_val is not None:
            norm_status = status_val.strip().upper()
            if norm_status not in PROBLEM_STATUSES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid problem status: {status_val}",
                )
            inquiry.status = norm_status
            if norm_status in ("RESOLVED", "REJECTED"):
                inquiry.resolved_at = datetime.now(timezone.utc)
                inquiry.resolved_by = actor.employee_id
            else:
                inquiry.resolved_at = None
                inquiry.resolved_by = None

        if assigned_to is not None:
            clean_emp = assigned_to.strip()
            if clean_emp:
                emp = (
                    await db.execute(
                        select(Employee).where(
                            Employee.employee_id == clean_emp,
                            Employee.is_active.is_(True),
                            Employee.deleted_at.is_(None),
                        )
                    )
                ).scalar_one_or_none()
                if not emp:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Assignee '{clean_emp}' not found or inactive.",
                    )
                inquiry.assigned_to = emp.employee_id
            else:
                inquiry.assigned_to = None

        if resolution_remark is not None:
            inquiry.resolution_remark = resolution_remark.strip() or None

        inquiry.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(inquiry)

        emp_names = await self._employee_name_map(db, [inquiry.assigned_to, inquiry.resolved_by])
        prop_by_code, prop_by_id = await self._property_title_maps(db, [inquiry])
        return self._serialize_problem(
            inquiry, emp_names=emp_names, prop_by_code=prop_by_code, prop_by_id=prop_by_id
        )

    async def convert_problem_to_lead(
        self,
        db: AsyncSession,
        actor: Employee,
        inquiry_id: int,
        *,
        assigned_to: Optional[str] = None,
        lead_type: str = "BUYER",
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
    ) -> Lead:
        inquiry = await self._get_scoped_problem(db, actor, inquiry_id)

        target_assignee: Optional[str] = inquiry.assigned_to or actor.employee_id
        if isinstance(assigned_to, str) and assigned_to.strip():
            clean_emp = assigned_to.strip()
            emp = (
                await db.execute(
                    select(Employee).where(
                        Employee.employee_id == clean_emp,
                        Employee.is_active.is_(True),
                        Employee.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if not emp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Assignee '{clean_emp}' not found or inactive.",
                )
            target_assignee = emp.employee_id

        return await intake_service.convert_inquiry_to_lead(
            db=db,
            inquiry_id=inquiry.id,
            assigned_to=target_assignee,
            lead_type=lead_type,
            budget_min=budget_min,
            budget_max=budget_max,
            converted_by_emp_id=actor.employee_id,
        )

    async def export_problems_xls(
        self,
        db: AsyncSession,
        actor: Employee,
        *,
        status_filter: str = "ALL",
        search: Optional[str] = None,
    ) -> str:
        result = await self.list_problems(
            db,
            actor,
            status_filter=status_filter,
            search=search,
            limit=5000,
            offset=0,
        )
        headers = [
            "Problem ID",
            "Reporter Name",
            "Mobile",
            "Email",
            "Status",
            "Property Code",
            "Property Title",
            "Assigned To",
            "Details",
            "Resolution Remark",
            "Resolved By",
            "Resolved At",
            "Converted Lead ID",
            "Created Date",
        ]
        header_cells = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
        rows_html: List[str] = []
        for item in result["items"]:
            details_val = item.get("details")
            if isinstance(details_val, dict):
                details_text = details_val.get("description") or details_val.get("message") or json.dumps(details_val)
            else:
                details_text = str(details_val or "")

            vals = [
                f"PRB-{item['id']}",
                item.get("full_name") or "",
                item.get("mobile") or "",
                item.get("email") or "",
                item.get("status") or "",
                item.get("related_property_code") or "",
                item.get("property_title") or "",
                item.get("assigned_to_name") or item.get("assigned_to") or "Unassigned",
                details_text,
                item.get("resolution_remark") or "",
                item.get("resolved_by_name") or item.get("resolved_by") or "",
                item.get("resolved_at") or "",
                item.get("converted_lead_id") or "",
                item.get("created_at") or "",
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


problem_service = ProblemService()
