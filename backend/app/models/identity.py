from __future__ import annotations
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
import uuid

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Dialect-safe JSON type that uses native JSONB on PostgreSQL and JSON on SQLite
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    roles: Mapped[List["Role"]] = relationship("Role", back_populates="department", cascade="all, delete-orphan", lazy="selectin")
    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="department", lazy="selectin")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    permissions: Mapped[Dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    department: Mapped["Department"] = relationship("Department", back_populates="roles", lazy="selectin")
    employees: Mapped[List["Employee"]] = relationship("Employee", back_populates="role", lazy="selectin")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    mobile: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    role_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    reporting_to: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
    )
    leave_approver: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("employees.employee_id", ondelete="SET NULL"),
        nullable=True,
    )
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    handled_categories: Mapped[List[str]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    budget_min_cr: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    budget_max_cr: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_on_leave: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    join_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="employees", lazy="selectin")
    role: Mapped[Optional["Role"]] = relationship("Role", back_populates="employees", lazy="selectin")
    auth_sessions: Mapped[List["AuthSession"]] = relationship("AuthSession", back_populates="employee", cascade="all, delete-orphan", lazy="selectin")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=True,
    )
    mobile: Mapped[str] = mapped_column(String(15), index=True, nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), default="WHATSAPP", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    session_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    employee: Mapped[Optional["Employee"]] = relationship("Employee", back_populates="auth_sessions", lazy="selectin")
