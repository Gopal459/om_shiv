import pytest
from sqlalchemy import inspect
from app.models.blogs import (
    TblBlog,
    TblBlogCategory,
    TblBlogAuthor,
    TblBlogTag,
    TblBlogComment,
)


def test_blog_models_metadata():
    """Verify table names and key columns match the legacy MySQL schema specification."""
    assert TblBlog.__tablename__ == "tbl_blog"
    assert TblBlogCategory.__tablename__ == "tbl_blog_category"
    assert TblBlogAuthor.__tablename__ == "tbl_blog_author"
    assert TblBlogTag.__tablename__ == "tbl_blog_tags"
    assert TblBlogComment.__tablename__ == "tbl_blog_comments"

    # Verify TblBlog columns
    blog_cols = {c.name for c in TblBlog.__table__.columns}
    expected_blog_cols = {
        "blog_id",
        "blog_category",
        "blog_title",
        "blog_title_hindi",
        "slug",
        "author_name",
        "blog_date",
        "short_description",
        "description",
        "description_hindi",
        "tags_id",
        "image",
        "meta_title",
        "meta_keyword",
        "meta_description",
        "status",
        "feature",
        "homepage_status",
        "total_view",
        "created_date",
        "modified_date",
    }
    assert expected_blog_cols.issubset(blog_cols)

    # Verify TblBlogCategory columns
    cat_cols = {c.name for c in TblBlogCategory.__table__.columns}
    expected_cat_cols = {
        "blog_category_id",
        "name",
        "slug",
        "meta_title",
        "meta_keyword",
        "meta_description",
        "status",
        "created_date",
        "modified_date",
    }
    assert expected_cat_cols.issubset(cat_cols)

    # Verify TblBlogAuthor columns
    author_cols = {c.name for c in TblBlogAuthor.__table__.columns}
    expected_author_cols = {
        "author_id",
        "author_name",
        "description",
        "status",
        "image",
        "created_date",
        "modified_date",
    }
    assert expected_author_cols.issubset(author_cols)

    # Verify TblBlogTag columns
    tag_cols = {c.name for c in TblBlogTag.__table__.columns}
    expected_tag_cols = {
        "blog_tag_id",
        "name",
        "slug",
        "status",
        "created_date",
        "modified_date",
    }
    assert expected_tag_cols.issubset(tag_cols)

    # Verify TblBlogComment columns
    comm_cols = {c.name for c in TblBlogComment.__table__.columns}
    expected_comm_cols = {
        "blog_comm_id",
        "blog_id",
        "comment_id",
        "name",
        "email",
        "comment",
        "total_like",
        "status",
        "comment_by",
        "created_date",
        "modified_date",
    }
    assert expected_comm_cols.issubset(comm_cols)
