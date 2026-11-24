import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_blog_api_complete_suite(auth_client_md: AsyncClient):
    client = auth_client_md

    # 1. Test Image Upload
    file_content = b"fake-png-binary-data-for-testing"
    files = {"file": ("banner.png", io.BytesIO(file_content), "image/png")}
    upload_res = await client.post("/v1/blogs/upload-image", files=files)
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert "url" in upload_data
    assert upload_data["url"].startswith("/uploads/blogs/")

    # 2. Create Category
    cat_res = await client.post(
        "/v1/blogs/meta/categories",
        json={
            "name": "NCR Growth Corridor",
            "slug": "ncr-growth-corridor",
            "meta_title": "NCR Growth Corridor Real Estate",
            "meta_keyword": "ncr, alwar, rewari",
            "meta_description": "Analysis of NCR developments.",
            "status": 1,
        },
    )
    assert cat_res.status_code == 201
    cat_data = cat_res.json()
    cat_id = cat_data["blog_category_id"]

    # 3. Create Tag
    tag_res = await client.post(
        "/v1/blogs/meta/tags",
        json={"name": "Investment Tips", "slug": "investment-tips", "status": 1},
    )
    assert tag_res.status_code == 201
    tag_id = tag_res.json()["blog_tag_id"]

    # 4. Create Author
    author_res = await client.post(
        "/v1/blogs/meta/authors",
        json={
            "author_name": "Pooja Singhal",
            "description": "Head of Property Research at Propira Omshiv.",
            "image": "/uploads/authors/pooja.png",
            "status": 1,
        },
    )
    assert author_res.status_code == 201
    author_id = author_res.json()["author_id"]

    # 5. Create Bilingual Blog
    blog_payload = {
        "blog_title": "Bhiwadi & Neemrana Industrial Growth 2026",
        "blog_title_hindi": "भिवाड़ी और नीमराना औद्योगिक विकास 2026",
        "slug": "bhiwadi-neemrana-industrial-growth-2026",
        "author_name": author_id,
        "category_ids": [cat_id],
        "tag_ids": [tag_id],
        "short_description": "Industrial expansion driving housing demand in Delhi-Jaipur highway belt.",
        "description": "Comprehensive report covering RIICO industrial plots and rental yields.",
        "description_hindi": "रीको औद्योगिक भूखंडों और किराये की उपज को कवर करने वाली व्यापक रिपोर्ट।",
        "image": upload_data["url"],
        "meta_title": "Bhiwadi & Neemrana Real Estate Outlook 2026",
        "meta_keyword": "bhiwadi, neemrana, riico, industrial plots",
        "meta_description": "Property outlook and market forecasts for NCR borders.",
        "status": 1,
        "feature": 1,
        "homepage_status": 1,
    }
    create_res = await client.post("/v1/blogs", json=blog_payload)
    assert create_res.status_code == 201
    blog_data = create_res.json()
    blog_id = blog_data["blog_id"]
    assert blog_data["blog_title"] == "Bhiwadi & Neemrana Industrial Growth 2026"
    assert blog_data["blog_title_hindi"] == "भिवाड़ी और नीमराना औद्योगिक विकास 2026"

    # 6. Test Duplicate Title Protection (409 Conflict)
    dup_res = await client.post("/v1/blogs", json=blog_payload)
    assert dup_res.status_code == 409

    # 7. List Blogs
    list_res = await client.get("/v1/blogs?page=1&limit=10")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(b["blog_id"] == blog_id for b in list_data["items"])

    # 8. Get Single Blog By Slug
    single_res = await client.get("/v1/blogs/bhiwadi-neemrana-industrial-growth-2026")
    assert single_res.status_code == 200
    assert single_res.json()["blog_id"] == blog_id

    # 9. 1-Click Toggle (feature off)
    toggle_res = await client.patch(
        f"/v1/blogs/{blog_id}/toggle", json={"field": "feature", "value": 0}
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["feature"] == 0

    # 10. Post Public Comment (status 0 pending)
    comm_res = await client.post(
        f"/v1/blogs/{blog_id}/comments",
        json={
            "name": "Anil Goyal",
            "email": "anil@goyalgroup.in",
            "comment": "Are there residential plots available near Neemrana Japanese Zone?",
            "comment_by": "user",
        },
    )
    assert comm_res.status_code == 201
    comm_id = comm_res.json()["blog_comm_id"]
    assert comm_res.json()["status"] == 0

    # 11. Admin Moderate Comment (Approve status=1)
    mod_res = await client.patch(
        f"/v1/blogs/comments/{comm_id}/status", json={"status": 1}
    )
    assert mod_res.status_code == 200
    assert mod_res.json()["status"] == 1

    # 12. Admin Threaded Reply
    reply_res = await client.post(
        f"/v1/blogs/{blog_id}/comments",
        json={
            "name": "Propira Team",
            "email": "contact@propira.com",
            "comment": "Yes, gated townships like Eldeco and Ashiana have ready inventory.",
            "comment_id": comm_id,
            "comment_by": "admin",
        },
    )
    assert reply_res.status_code == 201
    assert reply_res.json()["comment_id"] == comm_id

    # 13. Fetch Threaded Comments for Blog
    threaded_res = await client.get(f"/v1/blogs/{blog_id}/comments")
    assert threaded_res.status_code == 200
    threads = threaded_res.json()
    assert len(threads) >= 1
    assert threads[0]["name"] == "Anil Goyal"
    assert len(threads[0]["replies"]) >= 1
    assert threads[0]["replies"][0]["name"] == "Propira Team"
