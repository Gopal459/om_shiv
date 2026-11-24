from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class TblBlogCategory(Base):
    """Legacy tbl_blog_category table."""
    __tablename__ = "tbl_blog_category"

    blog_category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(264), nullable=False)
    slug: Mapped[str] = mapped_column(String(264), nullable=False, index=True)
    meta_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_keyword: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=>Active, 0=>Inactive
    created_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    modified_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class TblBlogAuthor(Base):
    """Legacy tbl_blog_author table."""
    __tablename__ = "tbl_blog_author"

    author_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_name: Mapped[str] = mapped_column(String(264), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0=>Inactive, 1=>Active
    image: Mapped[str] = mapped_column(String(264), default="", nullable=False)
    created_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    modified_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class TblBlogTag(Base):
    """Legacy tbl_blog_tags table."""
    __tablename__ = "tbl_blog_tags"

    blog_tag_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(264), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(264), unique=True, nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=>Active, 0=>Inactive
    created_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    modified_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class TblBlog(Base):
    """Legacy tbl_blog main table with 21 columns."""
    __tablename__ = "tbl_blog"

    blog_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    blog_category: Mapped[str] = mapped_column(String(264), default="0", nullable=False)  # Comma separated IDs
    blog_title: Mapped[str] = mapped_column(String(264), unique=True, nullable=False)
    blog_title_hindi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(264), unique=True, nullable=False)
    author_name: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # author_id from tbl_blog_author
    blog_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_hindi: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags_id: Mapped[str] = mapped_column(String(264), default="0", nullable=False)  # Comma separated tag IDs
    image: Mapped[str] = mapped_column(String(264), default="", nullable=False)
    meta_title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    meta_keyword: Mapped[str] = mapped_column(Text, default="", nullable=False)
    meta_description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0=>Inactive, 1=>Active
    feature: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=>Featured, 0=>Normal
    homepage_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 1=>Show on home, 0=>No
    total_view: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    modified_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class TblBlogComment(Base):
    """Legacy tbl_blog_comments table with 10 columns."""
    __tablename__ = "tbl_blog_comments"

    blog_comm_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    blog_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    comment_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)  # Parent comment ID
    name: Mapped[str] = mapped_column(String(264), nullable=False)
    email: Mapped[str] = mapped_column(String(264), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    total_like: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0=>Pending, 1=>Approved
    comment_by: Mapped[str] = mapped_column(String(264), default="user", nullable=False)  # 'user' or 'admin'
    created_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    modified_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
