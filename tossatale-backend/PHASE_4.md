# Phase 4 — Story Series, Writer Verification, Blogs, Videos & Search

## Scope
Story Series with ordering, Blogs module (image-supported), Videos module (YouTube), full-text search, writer verification badge.

---

## Apps to Create / Extend
- `apps/series/`
- `apps/blogs/`
- `apps/videos/`
- `apps/search/`

---

## 4A — Story Series

### `apps/series/models.py` (§12)

**StorySeries**
```
Table: story_series
- id (UUID), title, slug (unique), description
- writer (FK → WriterProfile), created_by (FK → User)
- status (Enum: DRAFT, PUBLISHED, UNPUBLISHED, COMPLETED, ARCHIVED)
- total_stories, completed_stories (Integer)
- is_featured (Boolean)
- published_at, created_at, updated_at
```

**StorySeriesItem** (§12.2)
```
Table: story_series_items
- id, series (FK), story (FK)
- sequence_number (PositiveInteger)
- item_status (Enum: UPCOMING, PUBLISHED, COMPLETED)
- expected_publish_date, created_at, updated_at
- Unique: series + story
- Unique: series + sequence_number
```

---

### `apps/series/services.py` — StorySeriesService (§23, §32)

```python
StorySeriesService.create_series(admin, data)
StorySeriesService.update_series(series, data)
StorySeriesService.delete_series(series, admin)
StorySeriesService.publish_series(series, admin)
StorySeriesService.unpublish_series(series, admin)
StorySeriesService.archive_series(series, admin)
StorySeriesService.assign_story(series, story, admin)      # Prevent duplicate
StorySeriesService.remove_story(series, story, admin)
StorySeriesService.reorder_stories(series, items, admin)   # Must use db transaction (§23)
StorySeriesService.update_series_progress(series)
```

**Reorder Request Format (§23):**
```json
{
  "items": [
    {"story_id": "uuid-1", "sequence_number": 1},
    {"story_id": "uuid-2", "sequence_number": 2}
  ]
}
```

**Reorder Rules:**
1. Validate all story IDs belong to the series
2. No duplicate sequence numbers
3. Entire update must be wrapped in `transaction.atomic()`
4. Create audit log after reorder

---

### Series API Endpoints (§27, §29, §30)

**Public:**
```
GET /api/v1/public/series/
GET /api/v1/public/series/{slug}/
GET /api/v1/public/series/{slug}/stories/
```

**Writer:**
```
GET /api/v1/writer/series/
GET /api/v1/writer/series/{id}/
GET /api/v1/writer/series/{id}/stories/
```

**Admin:**
```
GET    /api/v1/admin/series/
POST   /api/v1/admin/series/
GET    /api/v1/admin/series/{id}/
PATCH  /api/v1/admin/series/{id}/
DELETE /api/v1/admin/series/{id}/
POST   /api/v1/admin/series/{id}/publish/
POST   /api/v1/admin/series/{id}/unpublish/
POST   /api/v1/admin/series/{id}/archive/
POST   /api/v1/admin/series/{id}/assign-story/
DELETE /api/v1/admin/series/{id}/remove-story/{story_id}/
POST   /api/v1/admin/series/{id}/reorder/
```

---

## 4B — Blogs Module

### `apps/blogs/models.py` (§13)

**Blog**
```
Table: blogs
- id (UUID), author (FK → User), title, slug
- subtitle, content (RichText/HTML — image-supported unlike stories)
- plain_text_content (for search)
- cover_image (URL via Cloudinary), featured_image (URL)
- category (FK → Category)
- seo_title, seo_description
- status (Enum: DRAFT, PUBLISHED, SCHEDULED, ARCHIVED)
- is_featured, reading_time, word_count
- views_count, likes_count, shares_count
- published_at, scheduled_publish_at, archived_at
- created_at, updated_at
```

**BlogTag**
```
Table: blog_tags
- id, blog (FK), tag (FK)
- Unique: blog + tag
```

> ⚠️ Blogs support images (Cloudinary). Writer stories do NOT. This is per §2 and §13.

---

### Blog API Endpoints (§27, §30)

**Public:**
```
GET /api/v1/public/blogs/
GET /api/v1/public/blogs/{slug}/
GET /api/v1/public/blogs/{slug}/related/
```

**Admin:**
```
GET    /api/v1/admin/blogs/
POST   /api/v1/admin/blogs/
GET    /api/v1/admin/blogs/{id}/
PATCH  /api/v1/admin/blogs/{id}/
DELETE /api/v1/admin/blogs/{id}/
POST   /api/v1/admin/blogs/{id}/publish/
POST   /api/v1/admin/blogs/{id}/archive/
POST   /api/v1/admin/blogs/{id}/feature/
```

---

## 4C — Videos Module

### `apps/videos/models.py` (§14)

**Video**
```
Table: videos
- id (UUID), title, slug
- youtube_url (URLField — validated)
- youtube_video_id (auto-extracted, CharField)
- embed_url (auto-generated from video_id)
- thumbnail_url (Cloudinary or YouTube default)
- description, category (FK → Category)
- duration (Integer — seconds)
- is_featured, is_active, published_at
- created_by (FK → User), created_at, updated_at
```

**Auto-generation rules (§14):**
- `youtube_video_id` extracted via `common.utils.extract_youtube_id()`
- `embed_url` generated via `common.utils.build_youtube_embed_url()`
- YouTube URL must be validated on save

---

### Video API Endpoints (§27, §30)

**Public:**
```
GET /api/v1/public/videos/
GET /api/v1/public/videos/{slug}/
```

**Admin:**
```
GET    /api/v1/admin/videos/
POST   /api/v1/admin/videos/
GET    /api/v1/admin/videos/{id}/
PATCH  /api/v1/admin/videos/{id}/
DELETE /api/v1/admin/videos/{id}/
POST   /api/v1/admin/videos/{id}/activate/
POST   /api/v1/admin/videos/{id}/deactivate/
POST   /api/v1/admin/videos/{id}/feature/
```

---

## 4D — Search Module

### `apps/search/views.py` (§27, §38)

**Endpoint:**
```
GET /api/v1/public/search/?q=friendship&type=story
```

**Search Types:**
- `story` — title, subtitle, plain_text_content
- `blog` — title, subtitle, plain_text_content
- `writer` — name, bio
- `category` — name
- `series` — title, description

**Implementation (§38 — Initial Version):**
```python
# PostgreSQL full-text search
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity

# On Story model
Story.objects.annotate(
    rank=SearchRank(SearchVector("title", "plain_text_content"), SearchQuery(q))
).filter(rank__gte=0.1).order_by("-rank")
```

**Searchable Fields per model:**
```python
# stories/models.py
search_vector = SearchVectorField(null=True)  # Updated on save via signal

# Index on indexed searchable fields
GinIndex(fields=["search_vector"])
```

---

## Testing Checklist (§48)

- [ ] `test_create_series`
- [ ] `test_assign_story_to_series`
- [ ] `test_assign_duplicate_story` — raises DuplicateResourceError
- [ ] `test_reorder_stories` — atomic transaction
- [ ] `test_reorder_duplicate_sequence` — raises ServiceValidationError
- [ ] `test_series_progress_update`
- [ ] `test_blog_publish`
- [ ] `test_blog_image_upload`
- [ ] `test_video_youtube_id_extraction`
- [ ] `test_video_embed_url_generation`
- [ ] `test_video_invalid_url` — raises ServiceValidationError
- [ ] `test_search_stories_by_keyword`
- [ ] `test_search_writers_by_name`
- [ ] `test_search_empty_query`
- [ ] `test_search_type_filter`
- [ ] `test_writer_verification_badge`
- [ ] `test_unverify_writer`
