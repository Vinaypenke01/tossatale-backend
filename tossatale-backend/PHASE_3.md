# Phase 3 — Public APIs & Reader Engagement

## Scope
Public story listing, story detail, likes, bookmarks, shares, views, recently read, reader dashboard.

---

## Apps to Create / Extend
- `apps/engagements/` — All reader engagement models and service

---

## Files to Create

### `apps/engagements/models.py`

**StoryLike** (§15.1)
```
Table: story_likes
- id (UUID), user (FK), story (FK), created_at
- Unique: user + story
```

**StoryBookmark** (§15.2)
```
Table: story_bookmarks
- id, user, story, created_at
- Unique: user + story
```

**StoryShare** (§15.3)
```
Table: story_shares
- id, user (nullable), story, platform (Enum), session_id, ip_hash, shared_at
- Platforms: WHATSAPP, FACEBOOK, X, LINKEDIN, COPY_LINK, EMAIL, OTHER
```

**StoryView** (§15.4)
```
Table: story_views
- id, story, user (nullable), session_id, ip_hash
- referrer, traffic_source, device_type, browser, country
- viewed_at, reading_duration (seconds), completion_percentage (Decimal)
- is_unique_view (Boolean)
```

**RecentlyRead** (§15.5)
```
Table: recently_read
- id, user, story, last_read_at, reading_progress (Decimal %), completed (Boolean)
- Unique: user + story
```

---

### `apps/engagements/services.py` — EngagementService (§25, §32)

```python
EngagementService.like_story(user, story)         # Create like, increment counts
EngagementService.unlike_story(user, story)       # Delete like, decrement counts
EngagementService.bookmark_story(user, story)     # Create bookmark
EngagementService.remove_bookmark(user, story)    # Remove bookmark
EngagementService.record_share(story, platform, user=None, session_id=None)
EngagementService.record_view(story, request)     # Async-safe, deduplication
EngagementService.update_recently_read(user, story, progress)
```

**Like Rules (§25):**
- User must be authenticated
- Story must be PUBLISHED
- Cannot like twice → DuplicateResourceError
- On like: story.likes_count += 1, writer.total_likes += 1
- Update daily_story_analytics asynchronously

**View Rules (§25):**
- Avoid duplicate views within configurable time window (default: 30 min)
- Track unique view vs total view separately
- is_unique_view = True if first view by this user/session
- Async processing via Celery where possible

---

### `apps/stories/views.py` — Public Story Views (§27)

```
GET  /api/v1/public/stories/                    — published list
GET  /api/v1/public/stories/{slug}/             — story detail
GET  /api/v1/public/stories/{slug}/related/     — related stories
GET  /api/v1/public/stories/{slug}/series/      — series info
POST /api/v1/public/stories/{id}/view/          — record view (async)
POST /api/v1/public/stories/{id}/share/         — record share
```

**Query Filters (§27):**
```
?search=...
?category=fiction
?tag=memoir
?writer=writer-slug
?series=series-slug
?is_featured=true
?is_verified=true    (filter by verified writer)
?ordering=-published_at
?ordering=views_count
?ordering=-likes_count
?ordering=reading_time
```

---

### Reader Dashboard Views (§28)

```
GET    /api/v1/user/dashboard/             — recently_read, liked, bookmarked, recommended
POST   /api/v1/user/stories/{id}/like/
DELETE /api/v1/user/stories/{id}/like/
GET    /api/v1/user/liked-stories/
POST   /api/v1/user/stories/{id}/bookmark/
DELETE /api/v1/user/stories/{id}/bookmark/
GET    /api/v1/user/bookmarks/
GET    /api/v1/user/recently-read/
DELETE /api/v1/user/recently-read/{id}/
DELETE /api/v1/user/recently-read/clear/
```

---

### Celery Tasks (§45)

Add to `apps/notifications/tasks.py`:
```python
aggregate_daily_story_analytics(story_id)   # Run nightly
update_writer_statistics(writer_id)          # After every view/like/share
```

---

### Reader Dashboard Response Shape (§28)

```json
{
  "recently_read": [...],
  "liked_stories": [...],
  "bookmarks": [...],
  "recommended": [...],
  "reading_statistics": {
    "total_stories_read": 12,
    "total_reading_time_minutes": 94,
    "favorite_category": "Memoir"
  }
}
```

---

## Database Indexes (§44)

```python
# story_views
Index(fields=["story", "viewed_at"])
Index(fields=["user", "story"])

# story_likes
Index(fields=["user", "story"])

# story_bookmarks
Index(fields=["user", "story"])

# recently_read
Index(fields=["user", "last_read_at"])
```

---

## Testing Checklist (§48)

- [ ] `test_like_story` — creates like, increments story.likes_count
- [ ] `test_like_twice` — raises DuplicateResourceError
- [ ] `test_unlike_story` — removes like, decrements counts
- [ ] `test_like_unpublished_story` — raises ServiceValidationError
- [ ] `test_bookmark_story`
- [ ] `test_bookmark_twice` — raises DuplicateResourceError
- [ ] `test_remove_bookmark`
- [ ] `test_record_view_unique` — is_unique_view = True on first view
- [ ] `test_record_view_duplicate` — within 30min window, is_unique_view = False
- [ ] `test_public_story_list` — only PUBLISHED stories returned
- [ ] `test_public_story_filter_by_category`
- [ ] `test_public_story_filter_by_verified_writer`
- [ ] `test_public_story_ordering`
- [ ] `test_recently_read_updated_on_view`
- [ ] `test_reader_dashboard_response_shape`
- [ ] `test_unauthenticated_like` — raises 401
- [ ] `test_unauthenticated_bookmark` — raises 401
