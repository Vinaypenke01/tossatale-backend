# Phase 2 — Story Pipeline

## Scope
Story CRUD, draft workflow, submission, Admin approval/rejection, moderation, email notifications, revisions.

---

## Apps to Create
- `apps/stories/`
- `apps/moderation/`

---

## Files to Create

### `apps/stories/models.py`

**Story Model** (§11.1)
```
Table: stories
Fields:
- id (UUID)
- writer (FK → WriterProfile)
- created_by (FK → User)
- title (CharField)
- slug (SlugField, unique)
- subtitle (CharField, nullable)
- content (TextField — rich prose, text-only for writers per §2)
- plain_text_content (TextField — for search and reading time calc)
- category (FK → Category)
- seo_title, seo_description
- status (Enum: DRAFT, PENDING_REVIEW, APPROVED, PUBLISHED, REJECTED, ARCHIVED, SCHEDULED)
- moderation_status (Enum: NOT_REVIEWED, PASSED, FLAGGED, BLOCKED)
- rejection_feedback (TextField, blank)
- submitted_at, reviewed_at, reviewed_by, approved_at, published_at, scheduled_publish_at, archived_at
- is_featured (Boolean)
- allow_comments (Boolean, default True)
- estimated_reading_time (Integer)
- word_count (Integer)
- views_count, likes_count, shares_count, bookmarks_count (BigInteger, default 0)
- trending_score (Decimal)
- created_at, updated_at
```

**StoryTag Model** (§11.2)
```
Table: story_tags
- id, story (FK), tag (FK)
- Unique constraint: story + tag
```

**StoryRevision Model** (§11.3)
```
Table: story_revisions
- id, story (FK), version_number
- title, subtitle, content, category (FK)
- seo_title, seo_description
- edited_by (FK → User), change_summary, created_at
```

**StoryReview Model** (§11.4)
```
Table: story_reviews
- id, story (FK), reviewer (FK → User)
- decision (Enum: APPROVED, REJECTED, CHANGES_REQUESTED)
- feedback, internal_notes, reviewed_at, created_at
```

---

### `apps/stories/serializers.py`

- `StoryCreateSerializer` — writer creates a story (title, content, category, seo fields, tags)
- `StoryUpdateSerializer` — writer updates own draft
- `StoryDetailSerializer` — full story detail (public)
- `StoryListSerializer` — compact story list card
- `AdminStorySerializer` — full admin view including moderation and review history
- `StorySubmitSerializer` — empty body (action only)
- `StoryRejectSerializer` — requires `rejection_feedback` field
- `StoryRevisionSerializer` — read-only revision history

**Validation Rules (§4.2):**
- Title is required
- Content is required (minimum 100 characters)
- Category is required and must be active
- SEO title max 70 characters
- SEO description max 160 characters

---

### `apps/stories/services.py` — StoryService (§22, §32)

```python
StoryService.create_story(writer, data)         # Creates DRAFT, saves revision 1
StoryService.update_story(story, data, user)    # Updates draft, saves new revision
StoryService.delete_story(story, user)          # Soft delete — only DRAFT allowed
StoryService.duplicate_story(story, writer)     # Clone as new DRAFT
StoryService.submit_story(story, writer)        # DRAFT/REJECTED → PENDING_REVIEW (§22.2)
StoryService.approve_story(story, admin)        # PENDING_REVIEW → APPROVED (§22.3)
StoryService.reject_story(story, admin, feedback)   # PENDING_REVIEW → REJECTED (§22.4)
StoryService.publish_story(story, admin)        # APPROVED → PUBLISHED (§22.5)
StoryService.schedule_story(story, admin, dt)   # APPROVED → SCHEDULED
StoryService.archive_story(story, admin)        # PUBLISHED → ARCHIVED (§22.6)
StoryService.feature_story(story, admin)        # Toggle is_featured
StoryService.restore_revision(story, revision_id)
StoryService.calculate_reading_time(text)
StoryService.calculate_word_count(text)
StoryService.generate_unique_slug(title)
```

**Business Rules for submit_story (§22.2):**
1. Story must belong to the logged-in writer
2. Status must be DRAFT or REJECTED
3. Title, content, category, seo_title, seo_description must be present
4. Writer must be active
5. Status changed to PENDING_REVIEW
6. submitted_at set to now
7. Old rejection_feedback cleared
8. Admin notification created
9. Email queued via Celery

**Business Rules for approve_story (§22.3):**
1. Status must be PENDING_REVIEW
2. Admin permission required
3. StoryReview record created
4. Status → APPROVED (or PUBLISHED if direct publish)
5. reviewed_by + reviewed_at set
6. Writer notification created
7. Approval email queued

**Business Rules for reject_story (§22.4):**
1. Status must be PENDING_REVIEW
2. feedback is required (non-empty)
3. StoryReview record created
4. Status → REJECTED
5. rejection_feedback stored
6. Writer notification created
7. Rejection email queued

**Business Rules for publish_story (§22.5):**
1. Status must be APPROVED
2. Unique slug confirmed
3. Status → PUBLISHED
4. published_at set
5. WriterProfile statistics updated
6. Category statistics updated
7. Notification created

---

### `apps/stories/views.py`

**Writer Views** (§29)
```
GET    /api/v1/writer/stories/           — list own stories (filter: status, category, series)
POST   /api/v1/writer/stories/           — create story
GET    /api/v1/writer/stories/{id}/      — get own story
PATCH  /api/v1/writer/stories/{id}/      — update own draft
DELETE /api/v1/writer/stories/{id}/      — delete own draft
POST   /api/v1/writer/stories/{id}/submit/    — submit for review
POST   /api/v1/writer/stories/{id}/duplicate/ — duplicate story
```

**Admin Views** (§30)
```
GET    /api/v1/admin/stories/
POST   /api/v1/admin/stories/
GET    /api/v1/admin/stories/{id}/
PATCH  /api/v1/admin/stories/{id}/
DELETE /api/v1/admin/stories/{id}/
POST   /api/v1/admin/stories/{id}/approve/
POST   /api/v1/admin/stories/{id}/reject/
POST   /api/v1/admin/stories/{id}/publish/
POST   /api/v1/admin/stories/{id}/unpublish/
POST   /api/v1/admin/stories/{id}/archive/
POST   /api/v1/admin/stories/{id}/feature/
POST   /api/v1/admin/stories/{id}/unfeature/
GET    /api/v1/admin/stories/{id}/revisions/
GET    /api/v1/admin/stories/{id}/reviews/

GET    /api/v1/admin/reviews/              — review queue
POST   /api/v1/admin/reviews/{id}/approve/
POST   /api/v1/admin/reviews/{id}/reject/
```

---

### `apps/moderation/services.py` — ModerationService

```python
ModerationService.check_content(text)       # Restricted keyword check
ModerationService.sanitize_text(text)       # Strip disallowed chars
ModerationService.detect_spam(text)         # Basic duplicate/spam detection
```

---

### Celery Tasks (§37, §45)

Add to `apps/notifications/tasks.py`:
```python
send_story_submission_email(story_id)    # To admin(s)
send_story_approval_email(story_id)      # To writer
send_story_rejection_email(story_id)     # To writer with feedback
```

---

### URL Routing

Update `config/urls.py` to add:
```python
path("api/v1/writer/stories/", include("apps.stories.urls.writer")),
path("api/v1/admin/stories/", include("apps.stories.urls.admin_urls")),
path("api/v1/admin/reviews/", include("apps.stories.urls.review")),
```

---

## Database Indexes (§44)

```python
indexes = [
    Index(fields=["slug"]),
    Index(fields=["status"]),
    Index(fields=["published_at"]),
    Index(fields=["writer"]),
    Index(fields=["category"]),
    Index(fields=["is_featured"]),
    Index(fields=["trending_score"]),
    Index(fields=["status", "published_at"]),
    Index(fields=["writer", "status"]),
    Index(fields=["category", "status"]),
]
```

---

## Testing Checklist (§48)

- [ ] `test_create_draft` — writer creates story as DRAFT
- [ ] `test_submit_story` — DRAFT → PENDING_REVIEW
- [ ] `test_submit_rejected_story` — REJECTED → PENDING_REVIEW  
- [ ] `test_submit_invalid_status` — PUBLISHED → submit raises InvalidStateTransitionError
- [ ] `test_approve_story` — PENDING_REVIEW → APPROVED
- [ ] `test_reject_story` — requires feedback, PENDING_REVIEW → REJECTED
- [ ] `test_reject_without_feedback` — raises ServiceValidationError
- [ ] `test_publish_story` — APPROVED → PUBLISHED
- [ ] `test_archive_story` — PUBLISHED → ARCHIVED
- [ ] `test_writer_cannot_approve` — raises PermissionDeniedError
- [ ] `test_email_queued_on_submit` — Celery task triggered
- [ ] `test_email_queued_on_approve` — Celery task triggered
- [ ] `test_email_queued_on_reject` — Celery task triggered
- [ ] `test_revision_created_on_submit`
- [ ] `test_duplicate_story_creates_draft`
