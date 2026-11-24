import os
import uuid
import math
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.blog_service import BlogService
from app.services.ai_blog_service import AIBlogGeneratorService
from app.schemas.blog_schemas import (
    BlogCreate,
    BlogUpdate,
    BlogResponse,
    BlogListResponse,
    BlogToggleRequest,
    BlogCategoryCreate,
    BlogCategoryUpdate,
    BlogCategoryResponse,
    BlogTagCreate,
    BlogTagResponse,
    BlogAuthorCreate,
    BlogAuthorUpdate,
    BlogAuthorResponse,
    BlogCommentCreate,
    BlogCommentResponse,
    AIBlogGenerateRequest,
    AIBlogGenerateResponse,
)

router = APIRouter()

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
BLOG_UPLOAD_DIR = os.path.join("uploads", "blogs")
os.makedirs(BLOG_UPLOAD_DIR, exist_ok=True)


def _format_blog_response(blog: Any, categories_map: Dict[int, str] = {}, tags_map: Dict[int, str] = {}, author: Optional[Any] = None) -> Dict[str, Any]:
    cat_ids = [int(c.strip()) for c in (blog.blog_category or "").split(",") if c.strip().isdigit()]
    tag_ids = [int(t.strip()) for t in (blog.tags_id or "").split(",") if t.strip().isdigit()]

    return {
        "blog_id": blog.blog_id,
        "blog_category": blog.blog_category,
        "category_ids": cat_ids,
        "category_names": [categories_map[c] for c in cat_ids if c in categories_map],
        "blog_title": blog.blog_title,
        "blog_title_hindi": blog.blog_title_hindi,
        "slug": blog.slug,
        "author_name": blog.author_name,
        "author_details": author,
        "blog_date": blog.blog_date,
        "short_description": blog.short_description,
        "description": blog.description,
        "description_hindi": blog.description_hindi,
        "tags_id": blog.tags_id,
        "tag_ids": tag_ids,
        "tag_names": [tags_map[t] for t in tag_ids if t in tags_map],
        "image": blog.image,
        "meta_title": blog.meta_title,
        "meta_keyword": blog.meta_keyword,
        "meta_description": blog.meta_description,
        "status": blog.status,
        "feature": blog.feature,
        "homepage_status": blog.homepage_status,
        "total_view": blog.total_view,
        "created_date": blog.created_date,
        "modified_date": blog.modified_date,
    }


# ==================== AI Blog Generator Agent ====================
@router.post("/ai-generate", response_model=AIBlogGenerateResponse, status_code=status.HTTP_200_OK)
async def generate_blog_with_ai(
    req: AIBlogGenerateRequest,
) -> AIBlogGenerateResponse:
    """Uses OpenAI LLM to automatically generate a complete real estate blog article with rich HTML content and SEO metadata."""
    return await AIBlogGeneratorService.generate_blog(req)


# ==================== Media Uploads ====================
@router.post("/upload-image", status_code=status.HTTP_200_OK)
async def upload_blog_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Uploads featured or body blog image to uploads/blogs/."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Only PNG, JPG, JPEG, and WEBP formats are accepted.",
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 10 MB.",
        )

    unique_filename = f"blog_{uuid.uuid4().hex[:12]}{ext}"
    target_path = os.path.join(BLOG_UPLOAD_DIR, unique_filename)
    with open(target_path, "wb") as f:
        f.write(content)

    public_url = f"/uploads/blogs/{unique_filename}"
    return {
        "status": "success",
        "url": public_url,
        "filename": unique_filename,
        "bytes": len(content),
    }


# ==================== Blog Categories ====================
@router.get("/meta/categories", response_model=List[BlogCategoryResponse])
async def list_blog_categories(
    status_filter: Optional[int] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    return await service.list_categories(status=status_filter)


@router.post("/meta/categories", response_model=BlogCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_blog_category(
    data: BlogCategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    return await service.create_category(data)


@router.put("/meta/categories/{cat_id}", response_model=BlogCategoryResponse)
async def update_blog_category(
    cat_id: int,
    data: BlogCategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    cat = await service.update_category(cat_id, data)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")
    return cat


@router.delete("/meta/categories/{cat_id}")
async def delete_blog_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    deleted = await service.delete_category(cat_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found.")
    return {"success": True}


# ==================== Blog Tags ====================
@router.get("/meta/tags", response_model=List[BlogTagResponse])
async def list_blog_tags(
    status_filter: Optional[int] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    return await service.list_tags(status=status_filter)


@router.post("/meta/tags", response_model=BlogTagResponse, status_code=status.HTTP_201_CREATED)
async def create_blog_tag(
    data: BlogTagCreate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    return await service.create_tag(data)


@router.delete("/meta/tags/{tag_id}")
async def delete_blog_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    deleted = await service.delete_tag(tag_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tag not found.")
    return {"success": True}


# ==================== Blog Authors ====================
@router.get("/meta/authors", response_model=List[BlogAuthorResponse])
async def list_blog_authors(
    status_filter: Optional[int] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    return await service.list_authors(status=status_filter)


@router.post("/meta/authors", response_model=BlogAuthorResponse, status_code=status.HTTP_201_CREATED)
async def create_blog_author(
    data: BlogAuthorCreate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    return await service.create_author(data)


@router.put("/meta/authors/{author_id}", response_model=BlogAuthorResponse)
async def update_blog_author(
    author_id: int,
    data: BlogAuthorUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    author = await service.update_author(author_id, data)
    if not author:
        raise HTTPException(status_code=404, detail="Author not found.")
    return author


@router.delete("/meta/authors/{author_id}")
async def delete_blog_author(
    author_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    deleted = await service.delete_author(author_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Author not found.")
    return {"success": True}


# ==================== Comments Moderation Queue ====================
@router.get("/comments/moderation")
async def list_comments_for_moderation(
    status_filter: Optional[int] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    items, total = await service.list_all_comments_for_moderation(status=status_filter, page=page, limit=limit)
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


@router.patch("/comments/{comm_id}/status")
async def moderate_comment_status(
    comm_id: int,
    body: Dict[str, int],
    db: AsyncSession = Depends(get_db),
):
    status_val = body.get("status", 1)
    service = BlogService(db)
    comment = await service.moderate_comment(comm_id, status_val)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found.")
    return comment


@router.delete("/comments/{comm_id}")
async def delete_comment(
    comm_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    deleted = await service.delete_comment(comm_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Comment not found.")
    return {"success": True}


# ==================== Main Blog Articles ====================
@router.get("", response_model=BlogListResponse)
async def list_blogs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    status_filter: Optional[int] = Query(None, alias="status"),
    feature: Optional[int] = Query(None),
    homepage_status: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    items, total = await service.get_blogs(
        page=page,
        limit=limit,
        search=search,
        category_id=category_id,
        status=status_filter,
        feature=feature,
        homepage_status=homepage_status,
    )

    cats = await service.list_categories()
    tags = await service.list_tags()
    cat_map = {c.blog_category_id: c.name for c in cats}
    tag_map = {t.blog_tag_id: t.name for t in tags}

    formatted = [_format_blog_response(b, cat_map, tag_map) for b in items]

    return {
        "items": formatted,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": math.ceil(total / limit) if total > 0 else 1,
    }


@router.post("", response_model=BlogResponse, status_code=status.HTTP_201_CREATED)
async def create_blog_article(
    data: BlogCreate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    try:
        blog = await service.create_blog(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    cats = await service.list_categories()
    tags = await service.list_tags()
    cat_map = {c.blog_category_id: c.name for c in cats}
    tag_map = {t.blog_tag_id: t.name for t in tags}
    return _format_blog_response(blog, cat_map, tag_map)


@router.get("/{id_or_slug}", response_model=BlogResponse)
async def get_single_blog(
    id_or_slug: str,
    increment_view: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    blog = await service.get_blog_by_id_or_slug(id_or_slug, increment_view=increment_view)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog article not found.")

    cats = await service.list_categories()
    tags = await service.list_tags()
    cat_map = {c.blog_category_id: c.name for c in cats}
    tag_map = {t.blog_tag_id: t.name for t in tags}
    return _format_blog_response(blog, cat_map, tag_map)


@router.put("/{blog_id}", response_model=BlogResponse)
async def update_blog_article(
    blog_id: int,
    data: BlogUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    try:
        blog = await service.update_blog(blog_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    if not blog:
        raise HTTPException(status_code=404, detail="Blog article not found.")

    cats = await service.list_categories()
    tags = await service.list_tags()
    cat_map = {c.blog_category_id: c.name for c in cats}
    tag_map = {t.blog_tag_id: t.name for t in tags}
    return _format_blog_response(blog, cat_map, tag_map)


@router.patch("/{blog_id}/toggle", response_model=BlogResponse)
async def toggle_blog_field(
    blog_id: int,
    body: BlogToggleRequest,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    blog = await service.toggle_blog_field(blog_id, body)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog article not found.")

    cats = await service.list_categories()
    tags = await service.list_tags()
    cat_map = {c.blog_category_id: c.name for c in cats}
    tag_map = {t.blog_tag_id: t.name for t in tags}
    return _format_blog_response(blog, cat_map, tag_map)


@router.delete("/{blog_id}")
async def delete_blog_article(
    blog_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    deleted = await service.delete_blog(blog_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Blog article not found.")
    return {"success": True, "message": "Blog deleted successfully."}


# ==================== Blog Article Comments ====================
@router.get("/{blog_id}/comments", response_model=List[BlogCommentResponse])
async def get_blog_comments(
    blog_id: int,
    all_comments: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    return await service.list_comments_for_blog(blog_id, only_approved=not all_comments)


@router.post("/{blog_id}/comments", response_model=BlogCommentResponse, status_code=status.HTTP_201_CREATED)
async def post_blog_comment(
    blog_id: int,
    data: BlogCommentCreate,
    db: AsyncSession = Depends(get_db),
):
    service = BlogService(db)
    try:
        return await service.add_comment(blog_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
