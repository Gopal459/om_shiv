import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.blog_schemas import (
    BlogCategoryCreate,
    BlogTagCreate,
    BlogAuthorCreate,
    BlogCreate,
    BlogUpdate,
    BlogToggleRequest,
    BlogCommentCreate,
)
from app.services.blog_service import BlogService


@pytest.mark.asyncio
async def test_blog_service_full_lifecycle(db_session: AsyncSession):
    service = BlogService(db_session)

    # 1. Create Category
    cat = await service.create_category(
        BlogCategoryCreate(
            name="Market Insights",
            slug="market-insights",
            meta_title="Market Insights in Alwar & Jaipur",
            meta_keyword="real estate, alwar, jaipur",
            meta_description="Latest trends in Rajasthan real estate.",
            status=1,
        )
    )
    assert cat.blog_category_id is not None
    assert cat.name == "Market Insights"

    # 2. Create Tag
    tag = await service.create_tag(
        BlogTagCreate(name="Property Guide", slug="property-guide", status=1)
    )
    assert tag.blog_tag_id is not None
    assert tag.name == "Property Guide"

    # 3. Create Author
    author = await service.create_author(
        BlogAuthorCreate(
            author_name="Vikram Sharma",
            description="Senior Real Estate Analyst with 15+ years experience in NCR & Rajasthan.",
            image="/uploads/authors/vikram.jpg",
            status=1,
        )
    )
    assert author.author_id is not None

    # 4. Create Bilingual Blog Post
    blog_data = BlogCreate(
        blog_title="Top 5 Investment Localities in Alwar 2026",
        blog_title_hindi="अलवर में 2026 में निवेश के लिए शीर्ष 5 इलाके",
        slug="top-5-investment-localities-alwar-2026",
        author_name=author.author_id,
        category_ids=[cat.blog_category_id],
        tag_ids=[tag.blog_tag_id],
        short_description="An overview of booming sectors near Delhi-Mumbai Expressway.",
        description="Detailed analysis of commercial and residential plot appreciation.",
        description_hindi="दिल्ली-मुंबई एक्सप्रेसवे के पास वाणिज्यिक और आवासीय भूखंडों का विस्तृत विश्लेषण।",
        image="/uploads/blogs/alwar_investment_2026.jpg",
        meta_title="Best Real Estate Investment in Alwar 2026",
        meta_keyword="alwar property, real estate investment",
        meta_description="Discover high-growth property corridors in Alwar.",
        status=1,
        feature=1,
        homepage_status=1,
    )
    created_blog = await service.create_blog(blog_data)
    assert created_blog.blog_id is not None
    assert created_blog.blog_title == "Top 5 Investment Localities in Alwar 2026"
    assert created_blog.blog_title_hindi == "अलवर में 2026 में निवेश के लिए शीर्ष 5 इलाके"
    assert str(cat.blog_category_id) in created_blog.blog_category

    # 5. Test Duplicate Title / Slug Prevention
    with pytest.raises(ValueError, match="already exists"):
        await service.create_blog(blog_data)

    # 6. Test 1-Click Fast Field Toggles
    updated_blog = await service.toggle_blog_field(
        created_blog.blog_id, BlogToggleRequest(field="feature", value=0)
    )
    assert updated_blog.feature == 0

    # 7. Test Comments and Threaded Admin Reply
    user_comment = await service.add_comment(
        created_blog.blog_id,
        BlogCommentCreate(
            name="Rahul Verma",
            email="rahul@example.com",
            comment="What is the average price per sq yard in Tijara Road?",
            comment_by="user",
        ),
    )
    assert user_comment.blog_comm_id is not None
    assert user_comment.status == 0  # Pending by default

    # Admin approves user comment
    approved_comment = await service.moderate_comment(user_comment.blog_comm_id, 1)
    assert approved_comment.status == 1

    # Admin posts threaded reply
    admin_reply = await service.add_comment(
        created_blog.blog_id,
        BlogCommentCreate(
            name="Admin Support",
            email="admin@omshiv.com",
            comment="Current rates on Tijara Road range from Rs 18,000 to Rs 35,000 per sq yard.",
            comment_id=user_comment.blog_comm_id,
            comment_by="admin",
        ),
    )
    assert admin_reply.comment_id == user_comment.blog_comm_id
    assert admin_reply.comment_by == "admin"
    assert admin_reply.status == 1  # Admin replies auto-approved

    # 8. Test list comments with threaded hierarchy
    threaded = await service.list_comments_for_blog(created_blog.blog_id, only_approved=True)
    assert len(threaded) == 1
    assert threaded[0]["name"] == "Rahul Verma"
    assert len(threaded[0]["replies"]) == 1
    assert threaded[0]["replies"][0]["name"] == "Admin Support"
