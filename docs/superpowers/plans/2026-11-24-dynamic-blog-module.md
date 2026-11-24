# Dynamic Blog Module CMS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete, enterprise-grade dynamic Blog Management CMS module featuring 100% schema parity with legacy MySQL tables (`tbl_blog`, `tbl_blog_category`, `tbl_blog_author`, `tbl_blog_tags`, `tbl_blog_comments`), bilingual English & Hindi publishing, SEO metadata, category & tag associations, author management, 1-click status/feature/homepage toggles, threaded comments moderation, image uploads, and an executive real-estate admin interface.

**Architecture:**
- **Database Layer**: SQLAlchemy models in `backend/app/models/blogs.py` and dual SQLite/MySQL migration in `backend/app/db/migrations/0008_tbl_blog_schema.py`.
- **API & Service Layer**: Pydantic v2 schemas in `backend/app/schemas/blog_schemas.py`, comprehensive CRUD and business operations in `backend/app/services/blog_service.py`, and REST endpoints in `backend/app/api/v1/endpoints/blogs.py`.
- **Static Media**: Images uploaded to `uploads/blogs/` and served via `/uploads/blogs/`.
- **Frontend Dashboard**: Enterprise React+TypeScript CMS in `frontend/src/pages/BlogManager.tsx`, mounted at `/blogs` in `frontend/src/App.tsx`, featuring 5 dedicated workspaces: Articles List with fast toggles, Bilingual Rich Article Editor, Categories & Tags Editor, Author Profile Manager, and Comment Moderation Queue with threaded admin replies.

**Tech Stack:** FastAPI, SQLAlchemy (Async), SQLite/MySQL, Pydantic v2, Pytest, React 18, TypeScript, TailwindCSS, Lucide-React, Vite.

**Spec:** User-provided specification for 5 tables (`tbl_blog`, `tbl_blog_category`, `tbl_blog_author`, `tbl_blog_tags`, `tbl_blog_comments`), field constraints, bilingual requirements, and admin dashboard screenshots.

---

## Global Constraints
- **Bilingual Content Mandatory**: Every published blog must have English Title (`blog_title`), Hindi Title (`blog_title_hindi`), Short Excerpt (`short_description`), English Content (`description`), and Hindi Content (`description_hindi`).
- **Uniqueness**: `blog_title` and `slug` must be unique across all articles. Auto-slug generator handles transliteration/formatting, and collisions return HTTP 409 Conflict with clear messaging.
- **Relational Integrity**:
  - `blog_category`: Stored as comma-separated category IDs; must validate that at least one valid category is selected.
  - `tags_id`: Stored as comma-separated tag IDs; must validate that at least one valid tag is selected.
  - `author_name`: Stored as integer ID referencing an active `tbl_blog_author.author_id`.
- **Quick Status Controls**: 1-click toggle endpoints for `status` (0=Draft/Inactive, 1=Active), `feature` (0=Normal, 1=Featured), and `homepage_status` (0=Standard, 1=Home Banner).
- **Comment Moderation**: All incoming public comments are created with `status=0` (Pending). Admins can Approve (`status=1`), Reject/Delete, and post threaded replies (`comment_by='admin'`, `comment_id=parent_comment_id`).
- **Media**: Uploaded images validated for format (PNG, JPG, JPEG, WEBP), saved with timestamped filenames in `uploads/blogs/`, and served via `/uploads/blogs/`.
- **Test Integrity**: All 73 existing backend tests must continue passing without regression.

---

## Review Focus
1. **Devanagari UTF-8 Encoding**: Hindi content containing Hindi script (e.g. `जयपुर में रियल एस्टेट निवेश गाइड`) must persist and retrieve cleanly without character corruption or truncation.
2. **Category & Tag Comma-Separated Normalization**: String formatting of `"1,2,5"` must serialize, deserialize, and filter correctly without trailing commas or nulls.
3. **Threaded Comment Tree Building**: When comments are fetched, admin replies (`comment_id=parent_id`) must nest correctly under parent comments and preserve chronological order.
4. **Duplicate Title & Slug Protection**: Attempting to create or update an article with an identical title or slug to an existing article must return HTTP 409 Conflict rather than throwing unhandled database integrity errors.
5. **Image Upload Path Safety**: Image file uploads must prevent directory traversal, only allow approved image extensions, and safely create directory `uploads/blogs/` if not present.

---

### Task 1: Database Migration & SQLAlchemy Models (5 Core Tables)

**Files:**
- Create: `backend/app/db/migrations/0008_tbl_blog_schema.py`
- Modify: `backend/app/db/migrations/runner.py:10-20`
- Create: `backend/app/models/blogs.py`
- Modify: `backend/app/models/__init__.py:1-21`
- Test: `backend/tests/test_blog_models.py`

**Interfaces:**
- Consumes: `app.core.database.Base`, SQLAlchemy AsyncEngine
- Produces:
  - `TblBlog`: Table `tbl_blog` (21 columns matching spec)
  - `TblBlogCategory`: Table `tbl_blog_category` (8 columns matching spec)
  - `TblBlogAuthor`: Table `tbl_blog_author` (7 columns matching spec)
  - `TblBlogTag`: Table `tbl_blog_tags` (7 columns matching spec)
  - `TblBlogComment`: Table `tbl_blog_comments` (10 columns matching spec)

- [x] **Step 1: Write the failing model test**
Create `backend/tests/test_blog_models.py` verifying that all 5 models can be imported, instantiated, and have the correct column definitions and tablenames.

- [x] **Step 2: Run test to verify it fails**
Run: `.venv\Scripts\pytest backend\tests\test_blog_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.blogs'`

- [x] **Step 3: Create Migration `0008_tbl_blog_schema.py` and register in `runner.py`**
Implement the migration defining `tbl_blog`, `tbl_blog_category`, `tbl_blog_author`, `tbl_blog_tags`, and `tbl_blog_comments` with SQLite and MySQL compatibility, and register `app.db.migrations.0008_tbl_blog_schema` in `runner.py`.

- [x] **Step 4: Implement SQLAlchemy models in `backend/app/models/blogs.py`**
Define classes `TblBlog`, `TblBlogCategory`, `TblBlogAuthor`, `TblBlogTag`, `TblBlogComment` extending `Base` with exact column types, defaults, and relationships. Export them in `backend/app/models/__init__.py`.

- [x] **Step 5: Run tests and apply migration to verify it passes**
Run: `.venv\Scripts\pytest backend\tests\test_blog_models.py -v`
Expected: PASS

- [x] **Step 6: Commit**
```bash
git add backend/app/db/migrations/ backend/app/models/ backend/tests/test_blog_models.py
git commit -m "feat(blogs): add database schema migration and sqlalchemy models for blog cms"
```

---

### Task 2: Pydantic Validation Schemas & Blog Service

**Files:**
- Create: `backend/app/schemas/blog_schemas.py`
- Create: `backend/app/services/blog_service.py`
- Test: `backend/tests/test_blog_service.py`

**Interfaces:**
- Consumes: Models from `app.models.blogs`, AsyncSession
- Produces:
  - Pydantic schemas: `BlogCreate`, `BlogUpdate`, `BlogResponse`, `BlogCategoryCreate`, `BlogCategoryResponse`, `BlogTagCreate`, `BlogTagResponse`, `BlogAuthorCreate`, `BlogAuthorResponse`, `BlogCommentCreate`, `BlogCommentResponse`
  - Service functions: `create_blog()`, `get_blogs()`, `get_blog_by_id_or_slug()`, `update_blog()`, `delete_blog()`, `toggle_blog_field()`, `create_category()`, `list_categories()`, `create_tag()`, `list_tags()`, `create_author()`, `list_authors()`, `add_comment()`, `moderate_comment()`, `delete_comment()`

- [x] **Step 1: Write failing service test**
Create `backend/tests/test_blog_service.py` testing creation of category, author, tag, bilingual blog post, slug uniqueness, and comment moderation.

- [x] **Step 2: Run test to verify it fails**
Run: `.venv\Scripts\pytest backend\tests\test_blog_service.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [x] **Step 3: Implement Pydantic Schemas in `backend/app/schemas/blog_schemas.py`**
Define strict validations:
- `blog_title`, `blog_title_hindi`, `short_description`, `description`, `description_hindi`, `meta_title`, `meta_keyword`, `meta_description` required.
- Slug generation helper using alphanumeric characters and hyphens.
- Category & Tag ID list to/from comma-separated string validators.

- [x] **Step 4: Implement Service Business Logic in `backend/app/services/blog_service.py`**
Implement CRUD and business logic methods in `BlogService` class with transaction safety, duplicate slug check, and comment reply threading.

- [x] **Step 5: Run test to verify it passes**
Run: `.venv\Scripts\pytest backend\tests\test_blog_service.py -v`
Expected: PASS

- [x] **Step 6: Commit**
```bash
git add backend/app/schemas/blog_schemas.py backend/app/services/blog_service.py backend/tests/test_blog_service.py
git commit -m "feat(blogs): add pydantic schemas and business service logic for blog cms"
```

---

### Task 3: Blog REST Endpoints, Media Uploads & Main App Registration

**Files:**
- Create: `backend/app/api/v1/endpoints/blogs.py`
- Modify: `backend/app/main.py:65-80`
- Test: `backend/tests/test_blog_api.py`

**Interfaces:**
- Consumes: `BlogService`, `app.db.session.get_db`, `FastAPI`
- Produces:
  - `POST /v1/blogs/upload-image`: Upload blog featured or content image to `uploads/blogs/`
  - `GET /v1/blogs`: List blogs with pagination, search, category, status filters
  - `POST /v1/blogs`: Create blog article with bilingual validations
  - `GET /v1/blogs/{id_or_slug}`: Retrieve single blog detail
  - `PUT /v1/blogs/{id}`: Update blog article
  - `DELETE /v1/blogs/{id}`: Delete blog article
  - `PATCH /v1/blogs/{id}/toggle`: 1-click toggle for `status`, `feature`, or `homepage_status`
  - `GET /v1/blogs/categories`: List categories
  - `POST /v1/blogs/categories`: Create category
  - `PUT /v1/blogs/categories/{id}`: Update category
  - `GET /v1/blogs/tags`: List tags
  - `POST /v1/blogs/tags`: Create tag
  - `GET /v1/blogs/authors`: List authors
  - `POST /v1/blogs/authors`: Create author
  - `GET /v1/blogs/{id}/comments`: Get comments (with threaded replies)
  - `POST /v1/blogs/{id}/comments`: Post a comment
  - `PATCH /v1/blogs/comments/{id}/status`: Moderate comment (Approve/Reject)
  - `DELETE /v1/blogs/comments/{id}`: Delete comment

- [x] **Step 1: Write comprehensive API test suite**
Create `backend/tests/test_blog_api.py` testing image upload, article lifecycle, duplicate title conflict handling (409), fast status toggles, and threaded admin comments.

- [x] **Step 2: Run test to verify it fails**
Run: `.venv\Scripts\pytest backend\tests\test_blog_api.py -v`
Expected: FAIL with 404 Not Found or import error.

- [x] **Step 3: Implement endpoints in `backend/app/api/v1/endpoints/blogs.py` and register router in `main.py`**
Create router with all endpoints and mount at `/v1/blogs` in `backend/app/main.py`. Ensure `uploads/blogs` directory is created on startup.

- [x] **Step 4: Run test to verify it passes**
Run: `.venv\Scripts\pytest backend\tests\test_blog_api.py -v`
Expected: PASS

- [x] **Step 5: Run full test suite to guarantee 0 regressions**
Run: `.venv\Scripts\pytest backend\tests -q`
Expected: All 73+ tests pass.

- [x] **Step 6: Commit**
```bash
git add backend/app/api/v1/endpoints/blogs.py backend/app/main.py backend/tests/test_blog_api.py
git commit -m "feat(blogs): implement blog api endpoints, image upload and router registration"
```

---

### Task 4: Frontend Executive Blog Manager CMS UI

**Files:**
- Create: `frontend/src/pages/BlogManager.tsx`
- Modify: `frontend/src/App.tsx:13, 66, 120`
- Modify: `frontend/src/layouts/AdminLayout.tsx` (ensure active tab styling)

**Interfaces:**
- Consumes: REST endpoints at `/v1/blogs`, `/v1/blogs/upload-image`, `/v1/blogs/categories`, `/v1/blogs/tags`, `/v1/blogs/authors`, `/v1/blogs/comments`
- Produces:
  - Interactive Tab 1: **Articles Hub** (live search, filter by category/status, KPI cards, table with 1-click status/feature/home switches, view count, edit & delete buttons)
  - Interactive Tab 2: **Write / Edit Article** (bilingual English/Hindi inputs, automatic slug generator with override, category & tag multi-select badges, author select, featured image drag-and-drop / upload preview, SEO meta tags section with character counters)
  - Interactive Tab 3: **Categories & Tags** (category manager with SEO fields, tag chip generator)
  - Interactive Tab 4: **Authors** (author list & creation modal with photo upload and bio)
  - Interactive Tab 5: **Comments Moderation** (pending moderation tab vs approved tab, 1-click approve, reject, delete, and threaded inline admin reply form)

- [x] **Step 1: Create `frontend/src/pages/BlogManager.tsx`**
Build the complete, responsive, modern blog management page styled cleanly with Tailwind CSS, supporting dark/light mode, real-time feedback toasts, and modal dialogs.

- [x] **Step 2: Update `frontend/src/App.tsx` routing**
Replace `<ModuleHub ...>` placeholder at path `/blogs` with `<BlogManager />`.

- [x] **Step 3: Verify frontend compilation and TypeScript safety**
Run: `cd frontend; bun run build`
Expected: Zero TypeScript errors, successful production bundle.

- [x] **Step 4: Commit**
```bash
git add frontend/src/pages/BlogManager.tsx frontend/src/App.tsx
git commit -m "feat(frontend): create modern dynamic blog manager cms interface"
```

---

### Task 5: End-to-End Verification & Documentation

**Files:**
- Verify: Backend test suite and API responses
- Verify: Frontend production build & dev server
- Update: Task progress artifact

- [x] **Step 1: Execute complete backend test suite**
Run: `.venv\Scripts\pytest backend\tests -v`
Expected: 100% green tests with 0 failures.

- [x] **Step 2: Execute frontend production build**
Run: `cd frontend; bun run build`
Expected: Successful build with 0 errors.

- [x] **Step 3: Verify live endpoints via curl/powershell**
Perform live check of `/v1/blogs`, `/v1/blogs/categories`, `/v1/blogs/tags`, `/v1/blogs/authors`.

- [x] **Step 4: Final commit and branch review**
```bash
git status
git log -n 3
```
