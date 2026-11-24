import re
from typing import Optional, List, Literal, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


def generate_slug(text: str) -> str:
    """Creates clean URL slug from title."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s or "blog-article"


# --- Category Schemas ---
class BlogCategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=264)
    slug: Optional[str] = None
    meta_title: Optional[str] = None
    meta_keyword: Optional[str] = None
    meta_description: Optional[str] = None
    status: int = Field(default=1, ge=0, le=1)


class BlogCategoryCreate(BlogCategoryBase):
    pass


class BlogCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    meta_title: Optional[str] = None
    meta_keyword: Optional[str] = None
    meta_description: Optional[str] = None
    status: Optional[int] = None


class BlogCategoryResponse(BlogCategoryBase):
    blog_category_id: int
    slug: str
    created_date: datetime
    modified_date: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Tag Schemas ---
class BlogTagBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=264)
    slug: Optional[str] = None
    status: int = Field(default=1, ge=0, le=1)


class BlogTagCreate(BlogTagBase):
    pass


class BlogTagResponse(BlogTagBase):
    blog_tag_id: int
    slug: str
    created_date: datetime
    modified_date: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Author Schemas ---
class BlogAuthorBase(BaseModel):
    author_name: str = Field(..., min_length=2, max_length=264)
    description: str = Field(..., min_length=5)
    image: str = Field(default="", max_length=264)
    status: int = Field(default=1, ge=0, le=1)


class BlogAuthorCreate(BlogAuthorBase):
    pass


class BlogAuthorUpdate(BaseModel):
    author_name: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    status: Optional[int] = None


class BlogAuthorResponse(BlogAuthorBase):
    author_id: int
    created_date: datetime
    modified_date: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Blog Article Schemas ---
class BlogCreate(BaseModel):
    blog_title: str = Field(..., min_length=3, max_length=264)
    blog_title_hindi: Optional[str] = None
    slug: Optional[str] = None
    author_name: int = Field(..., description="author_id from tbl_blog_author")
    category_ids: List[int] = Field(..., min_length=1, description="At least one category required")
    tag_ids: List[int] = Field(..., min_length=1, description="At least one tag required")
    short_description: str = Field(..., min_length=5)
    description: str = Field(..., min_length=10)
    description_hindi: Optional[str] = None
    image: str = Field(default="", max_length=264)
    meta_title: str = Field(default="")
    meta_keyword: str = Field(default="")
    meta_description: str = Field(default="")
    status: int = Field(default=0, ge=0, le=1)
    feature: int = Field(default=0, ge=0, le=1)
    homepage_status: int = Field(default=0, ge=0, le=1)

    @field_validator("slug", mode="before")
    @classmethod
    def set_slug_if_empty(cls, v: Optional[str], values: Any) -> Optional[str]:
        if not v or not v.strip():
            return None
        return generate_slug(v)


class BlogUpdate(BaseModel):
    blog_title: Optional[str] = None
    blog_title_hindi: Optional[str] = None
    slug: Optional[str] = None
    author_name: Optional[int] = None
    category_ids: Optional[List[int]] = None
    tag_ids: Optional[List[int]] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    description_hindi: Optional[str] = None
    image: Optional[str] = None
    meta_title: Optional[str] = None
    meta_keyword: Optional[str] = None
    meta_description: Optional[str] = None
    status: Optional[int] = None
    feature: Optional[int] = None
    homepage_status: Optional[int] = None


class BlogToggleRequest(BaseModel):
    field: Literal["status", "feature", "homepage_status"]
    value: int = Field(..., ge=0, le=1)


class BlogResponse(BaseModel):
    blog_id: int
    blog_category: str
    category_ids: List[int] = []
    category_names: List[str] = []
    blog_title: str
    blog_title_hindi: Optional[str] = None
    slug: str
    author_name: int
    author_details: Optional[BlogAuthorResponse] = None
    blog_date: datetime
    short_description: str
    description: str
    description_hindi: Optional[str] = None
    tags_id: str
    tag_ids: List[int] = []
    tag_names: List[str] = []
    image: str
    meta_title: str
    meta_keyword: str
    meta_description: str
    status: int
    feature: int
    homepage_status: int
    total_view: int
    created_date: datetime
    modified_date: datetime

    model_config = ConfigDict(from_attributes=True)


class BlogListResponse(BaseModel):
    items: List[BlogResponse]
    total: int
    page: int
    limit: int
    pages: int


# --- Comment Schemas ---
class BlogCommentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=264)
    email: str = Field(..., min_length=5, max_length=264)
    comment: str = Field(..., min_length=3)
    comment_id: int = Field(default=0, description="0 for top-level, or parent comment id for reply")
    comment_by: str = Field(default="user", description="'user' or 'admin'")


class BlogCommentResponse(BaseModel):
    blog_comm_id: int
    blog_id: int
    comment_id: int
    name: str
    email: str
    comment: str
    total_like: int
    status: int
    comment_by: str
    created_date: datetime
    modified_date: datetime
    replies: List["BlogCommentResponse"] = []

    model_config = ConfigDict(from_attributes=True)
