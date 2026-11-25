from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, or_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.blogs import (
    TblBlog,
    TblBlogCategory,
    TblBlogAuthor,
    TblBlogTag,
    TblBlogComment,
)
from app.schemas.blog_schemas import (
    BlogCategoryCreate,
    BlogCategoryUpdate,
    BlogTagCreate,
    BlogAuthorCreate,
    BlogAuthorUpdate,
    BlogCreate,
    BlogUpdate,
    BlogToggleRequest,
    BlogCommentCreate,
    generate_slug,
)


class BlogService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== Categories ====================
    async def create_category(self, data: BlogCategoryCreate) -> TblBlogCategory:
        slug = data.slug or generate_slug(data.name)
        # Check slug uniqueness for category
        existing = await self.session.execute(
            select(TblBlogCategory).where(TblBlogCategory.slug == slug)
        )
        if existing.scalar_one_or_none():
            slug = f"{slug}-{int(func.random() * 1000)}"

        category = TblBlogCategory(
            name=data.name,
            slug=slug,
            meta_title=data.meta_title,
            meta_keyword=data.meta_keyword,
            meta_description=data.meta_description,
            status=data.status,
        )
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def list_categories(self, status: Optional[int] = None) -> List[TblBlogCategory]:
        query = select(TblBlogCategory)
        if status is not None:
            query = query.where(TblBlogCategory.status == status)
        query = query.order_by(TblBlogCategory.name.asc())
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def update_category(self, category_id: int, data: BlogCategoryUpdate) -> Optional[TblBlogCategory]:
        category = await self.session.get(TblBlogCategory, category_id)
        if not category:
            return None
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(category, field, val)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def delete_category(self, category_id: int) -> bool:
        category = await self.session.get(TblBlogCategory, category_id)
        if not category:
            return False
        await self.session.delete(category)
        await self.session.commit()
        return True

    # ==================== Tags ====================
    async def create_tag(self, data: BlogTagCreate) -> TblBlogTag:
        slug = data.slug or generate_slug(data.name)
        existing = await self.session.execute(
            select(TblBlogTag).where(or_(TblBlogTag.name == data.name, TblBlogTag.slug == slug))
        )
        found = existing.scalar_one_or_none()
        if found:
            return found

        tag = TblBlogTag(
            name=data.name,
            slug=slug,
            status=data.status,
        )
        self.session.add(tag)
        await self.session.commit()
        await self.session.refresh(tag)
        return tag

    async def list_tags(self, status: Optional[int] = None) -> List[TblBlogTag]:
        query = select(TblBlogTag)
        if status is not None:
            query = query.where(TblBlogTag.status == status)
        query = query.order_by(TblBlogTag.name.asc())
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def delete_tag(self, tag_id: int) -> bool:
        tag = await self.session.get(TblBlogTag, tag_id)
        if not tag:
            return False
        await self.session.delete(tag)
        await self.session.commit()
        return True

    # ==================== Authors ====================
    async def create_author(self, data: BlogAuthorCreate) -> TblBlogAuthor:
        author = TblBlogAuthor(
            author_name=data.author_name,
            description=data.description,
            image=data.image,
            status=data.status,
        )
        self.session.add(author)
        await self.session.commit()
        await self.session.refresh(author)
        return author

    async def list_authors(self, status: Optional[int] = None) -> List[TblBlogAuthor]:
        query = select(TblBlogAuthor)
        if status is not None:
            query = query.where(TblBlogAuthor.status == status)
        query = query.order_by(TblBlogAuthor.author_name.asc())
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def update_author(self, author_id: int, data: BlogAuthorUpdate) -> Optional[TblBlogAuthor]:
        author = await self.session.get(TblBlogAuthor, author_id)
        if not author:
            return None
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(author, field, val)
        await self.session.commit()
        await self.session.refresh(author)
        return author

    async def delete_author(self, author_id: int) -> bool:
        author = await self.session.get(TblBlogAuthor, author_id)
        if not author:
            return False
        await self.session.delete(author)
        await self.session.commit()
        return True

    # ==================== Blogs (Core CRUD) ====================
    async def create_blog(self, data: BlogCreate) -> TblBlog:
        # Check Title Uniqueness
        title_check = await self.session.execute(
            select(TblBlog).where(TblBlog.blog_title == data.blog_title)
        )
        if title_check.scalar_one_or_none():
            raise ValueError(f"Blog article with title '{data.blog_title}' already exists.")

        # Determine Slug
        slug = data.slug or generate_slug(data.blog_title)
        slug_check = await self.session.execute(
            select(TblBlog).where(TblBlog.slug == slug)
        )
        if slug_check.scalar_one_or_none():
            raise ValueError(f"Blog slug '{slug}' already exists.")

        # Validate Author
        author = await self.session.get(TblBlogAuthor, data.author_name)
        if not author:
            # Check if any author exists or create default fallback if needed
            authors = await self.list_authors()
            if not authors:
                default_author = await self.create_author(
                    BlogAuthorCreate(author_name="Editorial Staff", description="Omshiv Editorial Desk", status=1)
                )
                data.author_name = default_author.author_id
            else:
                data.author_name = authors[0].author_id

        # Format Categories and Tags
        cat_str = ",".join(str(c) for c in data.category_ids)
        tag_str = ",".join(str(t) for t in data.tag_ids)

        blog = TblBlog(
            blog_category=cat_str,
            blog_title=data.blog_title,
            blog_title_hindi=data.blog_title_hindi,
            slug=slug,
            author_name=data.author_name,
            short_description=data.short_description,
            description=data.description,
            description_hindi=data.description_hindi,
            tags_id=tag_str,
            image=data.image,
            meta_title=data.meta_title or data.blog_title,
            meta_keyword=data.meta_keyword,
            meta_description=data.meta_description or data.short_description,
            status=data.status,
            feature=data.feature,
            homepage_status=data.homepage_status,
        )
        self.session.add(blog)
        await self.session.commit()
        await self.session.refresh(blog)
        return blog

    async def get_blogs(
        self,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        status: Optional[int] = None,
        feature: Optional[int] = None,
        homepage_status: Optional[int] = None,
    ) -> Tuple[List[TblBlog], int]:
        query = select(TblBlog)
        count_query = select(func.count(TblBlog.blog_id))

        if search:
            search_filter = or_(
                TblBlog.blog_title.ilike(f"%{search}%"),
                TblBlog.blog_title_hindi.ilike(f"%{search}%"),
                TblBlog.short_description.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if category_id is not None:
            cat_pat = f"%{category_id}%"
            query = query.where(TblBlog.blog_category.like(cat_pat))
            count_query = count_query.where(TblBlog.blog_category.like(cat_pat))

        if status is not None:
            query = query.where(TblBlog.status == status)
            count_query = count_query.where(TblBlog.status == status)

        if feature is not None:
            query = query.where(TblBlog.feature == feature)
            count_query = count_query.where(TblBlog.feature == feature)

        if homepage_status is not None:
            query = query.where(TblBlog.homepage_status == homepage_status)
            count_query = count_query.where(TblBlog.homepage_status == homepage_status)

        # Count total
        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        # Paginate
        query = query.order_by(TblBlog.created_date.desc())
        query = query.offset((page - 1) * limit).limit(limit)
        items_res = await self.session.execute(query)
        items = list(items_res.scalars().all())

        return items, total

    async def get_blog_by_id_or_slug(self, id_or_slug: Any, increment_view: bool = False) -> Optional[TblBlog]:
        if isinstance(id_or_slug, int) or (isinstance(id_or_slug, str) and id_or_slug.isdigit()):
            blog_id = int(id_or_slug)
            blog = await self.session.get(TblBlog, blog_id)
        else:
            res = await self.session.execute(select(TblBlog).where(TblBlog.slug == str(id_or_slug)))
            blog = res.scalar_one_or_none()

        if blog and increment_view:
            blog.total_view += 1
            await self.session.commit()
            await self.session.refresh(blog)
        return blog

    async def update_blog(self, blog_id: int, data: BlogUpdate) -> Optional[TblBlog]:
        blog = await self.session.get(TblBlog, blog_id)
        if not blog:
            return None

        # Title uniqueness check
        if data.blog_title and data.blog_title != blog.blog_title:
            check = await self.session.execute(
                select(TblBlog).where(TblBlog.blog_title == data.blog_title, TblBlog.blog_id != blog_id)
            )
            if check.scalar_one_or_none():
                raise ValueError(f"Blog article with title '{data.blog_title}' already exists.")
            blog.blog_title = data.blog_title

        # Slug uniqueness check
        if data.slug and data.slug != blog.slug:
            clean_slug = generate_slug(data.slug)
            check = await self.session.execute(
                select(TblBlog).where(TblBlog.slug == clean_slug, TblBlog.blog_id != blog_id)
            )
            if check.scalar_one_or_none():
                raise ValueError(f"Blog slug '{clean_slug}' already exists.")
            blog.slug = clean_slug

        # Categories
        if data.category_ids is not None:
            blog.blog_category = ",".join(str(c) for c in data.category_ids)

        # Tags
        if data.tag_ids is not None:
            blog.tags_id = ",".join(str(t) for t in data.tag_ids)

        # Direct fields
        direct_fields = [
            "blog_title_hindi",
            "author_name",
            "short_description",
            "description",
            "description_hindi",
            "image",
            "meta_title",
            "meta_keyword",
            "meta_description",
            "status",
            "feature",
            "homepage_status",
        ]
        dump = data.model_dump(exclude_unset=True)
        for f in direct_fields:
            if f in dump and dump[f] is not None:
                setattr(blog, f, dump[f])

        await self.session.commit()
        await self.session.refresh(blog)
        return blog

    async def toggle_blog_field(self, blog_id: int, toggle: BlogToggleRequest) -> Optional[TblBlog]:
        blog = await self.session.get(TblBlog, blog_id)
        if not blog:
            return None
        setattr(blog, toggle.field, toggle.value)
        await self.session.commit()
        await self.session.refresh(blog)
        return blog

    async def delete_blog(self, blog_id: int) -> bool:
        blog = await self.session.get(TblBlog, blog_id)
        if not blog:
            return False
        # Delete associated comments
        await self.session.execute(delete(TblBlogComment).where(TblBlogComment.blog_id == blog_id))
        await self.session.delete(blog)
        await self.session.commit()
        return True

    # ==================== Comments Moderation & Threads ====================
    async def add_comment(self, blog_id: int, data: BlogCommentCreate) -> TblBlogComment:
        blog = await self.session.get(TblBlog, blog_id)
        if not blog:
            raise ValueError(f"Blog {blog_id} not found.")

        # Admin comments automatically approved (status=1); user comments pending (status=0)
        status = 1 if data.comment_by == "admin" else 0

        comment = TblBlogComment(
            blog_id=blog_id,
            comment_id=data.comment_id,
            name=data.name,
            email=data.email,
            comment=data.comment,
            total_like=0,
            status=status,
            comment_by=data.comment_by,
        )
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def moderate_comment(self, comm_id: int, status: int) -> Optional[TblBlogComment]:
        comment = await self.session.get(TblBlogComment, comm_id)
        if not comment:
            return None
        comment.status = status
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def delete_comment(self, comm_id: int) -> bool:
        comment = await self.session.get(TblBlogComment, comm_id)
        if not comment:
            return False
        # Also delete threaded child replies
        await self.session.execute(delete(TblBlogComment).where(TblBlogComment.comment_id == comm_id))
        await self.session.delete(comment)
        await self.session.commit()
        return True

    async def list_comments_for_blog(self, blog_id: int, only_approved: bool = True) -> List[Dict[str, Any]]:
        query = select(TblBlogComment).where(TblBlogComment.blog_id == blog_id)
        if only_approved:
            query = query.where(TblBlogComment.status == 1)
        query = query.order_by(TblBlogComment.created_date.asc())
        res = await self.session.execute(query)
        all_comments = list(res.scalars().all())

        # Build threaded hierarchy
        comment_map: Dict[int, Dict[str, Any]] = {}
        top_level: List[Dict[str, Any]] = []

        for c in all_comments:
            c_dict = {
                "blog_comm_id": c.blog_comm_id,
                "blog_id": c.blog_id,
                "comment_id": c.comment_id,
                "name": c.name,
                "email": c.email,
                "comment": c.comment,
                "total_like": c.total_like,
                "status": c.status,
                "comment_by": c.comment_by,
                "created_date": c.created_date,
                "modified_date": c.modified_date,
                "replies": [],
            }
            comment_map[c.blog_comm_id] = c_dict

        for c in all_comments:
            c_dict = comment_map[c.blog_comm_id]
            if c.comment_id == 0 or c.comment_id not in comment_map:
                top_level.append(c_dict)
            else:
                comment_map[c.comment_id]["replies"].append(c_dict)

        return top_level

    async def list_all_comments_for_moderation(
        self, status: Optional[int] = None, page: int = 1, limit: int = 20
    ) -> Tuple[List[TblBlogComment], int]:
        query = select(TblBlogComment)
        count_query = select(func.count(TblBlogComment.blog_comm_id))

        if status is not None:
            query = query.where(TblBlogComment.status == status)
            count_query = count_query.where(TblBlogComment.status == status)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(TblBlogComment.created_date.desc()).offset((page - 1) * limit).limit(limit)
        res = await self.session.execute(query)
        return list(res.scalars().all()), total
