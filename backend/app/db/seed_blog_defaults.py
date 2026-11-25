import asyncio
from sqlalchemy import select
from app.db import engine
from app.db.session import AsyncSessionLocal
from app.models.blogs import TblBlogCategory, TblBlogTag, TblBlogAuthor, TblBlog


async def seed_blog_defaults():
    async with AsyncSessionLocal() as session:
        # 1. Categories
        cat_check = await session.execute(select(TblBlogCategory))
        if not cat_check.scalars().first():
            cats = [
                TblBlogCategory(name="Market Insights & Trends", slug="market-insights-trends", status=1),
                TblBlogCategory(name="Investment Corridors", slug="investment-corridors", status=1),
                TblBlogCategory(name="Legal & Documentation", slug="legal-documentation", status=1),
                TblBlogCategory(name="Home Buying Guide", slug="home-buying-guide", status=1),
                TblBlogCategory(name="Industrial & Commercial", slug="industrial-commercial", status=1),
            ]
            session.add_all(cats)
            await session.commit()
            print("Seeded default blog categories.")

        # 2. Tags
        tag_check = await session.execute(select(TblBlogTag))
        if not tag_check.scalars().first():
            tags = [
                TblBlogTag(name="Alwar Real Estate", slug="alwar-real-estate", status=1),
                TblBlogTag(name="Jaipur Highway", slug="jaipur-highway", status=1),
                TblBlogTag(name="RIICO Industrial", slug="riico-industrial", status=1),
                TblBlogTag(name="Property Valuation", slug="property-valuation", status=1),
                TblBlogTag(name="Delhi-Mumbai Expressway", slug="delhi-mumbai-expressway", status=1),
            ]
            session.add_all(tags)
            await session.commit()
            print("Seeded default blog tags.")

        # 3. Authors
        author_check = await session.execute(select(TblBlogAuthor))
        if not author_check.scalars().first():
            authors = [
                TblBlogAuthor(
                    author_name="Omshiv Editorial Desk",
                    description="Official editorial and real estate research team at Omshiv Buildvision & Propira.",
                    image="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
                    status=1,
                ),
                TblBlogAuthor(
                    author_name="Vikram Sharma",
                    description="Principal Property Consultant specializing in Alwar industrial corridors and residential plots.",
                    image="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150",
                    status=1,
                ),
            ]
            session.add_all(authors)
            await session.commit()
            print("Seeded default blog authors.")

        # 4. Sample Blog
        blog_check = await session.execute(select(TblBlog))
        if not blog_check.scalars().first():
            cat = (await session.execute(select(TblBlogCategory))).scalars().first()
            tag = (await session.execute(select(TblBlogTag))).scalars().first()
            author = (await session.execute(select(TblBlogAuthor))).scalars().first()

            if cat and tag and author:
                sample_blog = TblBlog(
                    blog_category=str(cat.blog_category_id),
                    blog_title="2026 Rajasthan Real Estate Outlook: Why Alwar & Neemrana are Booming",
                    blog_title_hindi="2026 राजस्थान रियल एस्टेट आउटलुक: अलवर और नीमराना में उछाल क्यों है",
                    slug="2026-rajasthan-real-estate-outlook-alwar-neemrana",
                    author_name=author.author_id,
                    short_description="Strategic connectivity to the Delhi-Mumbai Industrial Corridor is driving unprecedented commercial and residential capital appreciation.",
                    description="Comprehensive investment analysis evaluating infrastructure expansion, RIICO land allocations, and high-yield gated townships across Alwar and Neemrana.",
                    description_hindi="दिल्ली-मुंबई औद्योगिक गलियारे से रणनीतिक जुड़ाव अलवर और नीमराना में वाणिज्यिक और आवासीय पूंजी वृद्धि को बढ़ावा दे रहा है।",
                    tags_id=str(tag.blog_tag_id),
                    image="https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800",
                    meta_title="2026 Rajasthan Real Estate Outlook - Propira",
                    meta_keyword="alwar property, neemrana real estate, rajasthan investment",
                    meta_description="Discover why Alwar and Neemrana are leading real estate growth in Rajasthan.",
                    status=1,
                    feature=1,
                    homepage_status=1,
                    total_view=142,
                )
                session.add(sample_blog)
                await session.commit()
                print("Seeded sample bilingual blog post.")


if __name__ == "__main__":
    asyncio.run(seed_blog_defaults())
