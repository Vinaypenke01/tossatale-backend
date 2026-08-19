# Phase 6 — Analytics, Trending, Recommendations, Caching & Audit Logs

## Scope
Daily story/writer/platform analytics aggregation, trending score calculation via Celery Beat, recommendation engine, Redis caching, audit logs, and full production optimization.

---

## Apps to Create / Extend
- `apps/analytics/`
- `apps/audit_logs/`

---

## 6A — Analytics Models

### `apps/analytics/models.py` (§16)

**DailyStoryAnalytics** (§16.1)
```
Table: daily_story_analytics
- id (UUID)
- story (FK → Story), date (DateField)
- views, unique_views, likes, unlikes, shares, bookmarks (Integer)
- new_likes_count, new_bookmarks_count (Integer)
- avg_reading_duration (Decimal — seconds)
- completion_rate (Decimal — %)
- country_breakdown (JSONField — e.g. {"IN": 42, "US": 10})
- device_breakdown (JSONField — e.g. {"mobile": 50, "desktop": 30})
- traffic_source_breakdown (JSONField)
- Unique: story + date
```

**DailyWriterAnalytics** (§16.2)
```
Table: daily_writer_analytics
- id, writer (FK → WriterProfile), date
- total_views, total_unique_views, total_likes, total_shares
- new_followers, stories_submitted, stories_published
- Unique: writer + date
```

**DailyPlatformAnalytics** (§16.3)
```
Table: daily_platform_analytics
- id, date (DateField, unique)
- total_page_views, unique_visitors
- new_users, new_writers
- total_stories_published, total_likes, total_shares
- newsletter_subscriptions
- top_stories (JSONField — top 10 story IDs and titles)
- top_categories (JSONField)
- country_breakdown, device_breakdown (JSONField)
```

---

### `apps/analytics/services.py` — AnalyticsService (§39, §45)

```python
AnalyticsService.aggregate_story_day(story_id, date)
AnalyticsService.aggregate_writer_day(writer_id, date)
AnalyticsService.aggregate_platform_day(date)
AnalyticsService.get_story_analytics(story, days=30)
AnalyticsService.get_writer_analytics(writer, days=30)
AnalyticsService.get_platform_overview(days=30)
AnalyticsService.export_story_analytics_csv(story)
AnalyticsService.export_writer_analytics_csv(writer)
AnalyticsService.export_platform_analytics_csv(date_from, date_to)
```

**Aggregation method:**
- Runs nightly at 01:00 AM via Celery Beat
- Groups StoryView / StoryLike / StoryShare records by date
- Saves into DailyStoryAnalytics
- Uses `update_or_create(story=story, date=date, defaults={...})`

---

### Analytics API Endpoints (§29, §30)

**Writer:**
```
GET /api/v1/writer/analytics/overview/
GET /api/v1/writer/analytics/stories/
GET /api/v1/writer/analytics/stories/{id}/?days=30
```

**Admin:**
```
GET /api/v1/admin/analytics/overview/                — Platform summary
GET /api/v1/admin/analytics/stories/                 — All story analytics
GET /api/v1/admin/analytics/stories/{id}/?days=30
GET /api/v1/admin/analytics/writers/
GET /api/v1/admin/analytics/writers/{id}/?days=30
GET /api/v1/admin/analytics/platform/?days=30
GET /api/v1/admin/analytics/platform/export/         — CSV download
```

---

## 6B — Trending Score Calculation (§40)

### Algorithm (§40.2)

**Trending Score Formula:**
```
score = (views_7d * 1.0)
      + (likes_7d * 2.0)
      + (shares_7d * 3.0)
      + (bookmarks_7d * 1.5)
      + recency_bonus
      + verified_writer_bonus

recency_bonus = max(0, 100 - days_since_published * 10)
verified_writer_bonus = 20 if writer.is_verified else 0
```

### Celery Beat Task

```python
# Runs every 4 hours
@shared_task
def calculate_trending_scores():
    stories = Story.objects.filter(status="PUBLISHED")
    for story in stories:
        score = TrendingService.calculate_score(story)
        story.trending_score = score
        story.save(update_fields=["trending_score"])
    # Cache top 10 trending
    top = Story.objects.filter(status="PUBLISHED").order_by("-trending_score")[:10]
    cache.set("trending_stories", StoryListSerializer(top, many=True).data, 60*60*4)
```

---

## 6C — Recommendation Engine (§41)

### `apps/analytics/services.py` — RecommendationService

```python
RecommendationService.get_recommendations(user, limit=6)
```

**Algorithm (§41 — content-based filtering):**
1. Get top 3 categories from user's recently read stories
2. Get stories in those categories not yet read by user
3. Sort by trending_score DESC
4. If insufficient results, fall back to global trending

```python
def get_recommendations(user, limit=6):
    recently_read_ids = RecentlyRead.objects.filter(user=user) \
        .values_list("story_id", flat=True)[:20]
    
    top_categories = Story.objects.filter(id__in=recently_read_ids) \
        .values("category_id") \
        .annotate(count=Count("id")) \
        .order_by("-count")[:3] \
        .values_list("category_id", flat=True)
    
    if top_categories:
        recommendations = Story.objects.filter(
            status="PUBLISHED",
            category_id__in=top_categories,
        ).exclude(id__in=recently_read_ids) \
         .order_by("-trending_score")[:limit]
    else:
        recommendations = Story.objects.filter(status="PUBLISHED") \
            .order_by("-trending_score")[:limit]
    
    return recommendations
```

---

## 6D — Audit Logs (§47)

### `apps/audit_logs/models.py`

**AuditLog**
```
Table: audit_logs
- id (UUID)
- actor (FK → User) — Who performed the action
- action (Enum: CREATE, UPDATE, DELETE, APPROVE, REJECT, PUBLISH, ARCHIVE, VERIFY, etc.)
- object_type (CharField — model name e.g. "Story", "WriterProfile")
- object_id (CharField — UUID of target record)
- object_repr (CharField — Human-readable label, e.g. story title)
- changes (JSONField — diff of changed fields: {"before": {...}, "after": {...}})
- ip_address, user_agent
- created_at
```

### `apps/audit_logs/services.py` — AuditLogService

```python
AuditLogService.log(actor, action, obj, changes=None, request=None)
```

> Call this from every service method that performs admin actions.
> The service layer is the correct place per §4.3. Views must not create audit logs directly.

### Audit Log API Endpoints (§30)

```
GET /api/v1/admin/audit-logs/               — Paginated list
GET /api/v1/admin/audit-logs/{id}/          — Detail
```

**Filters:**
```
?actor=admin@email.com
?action=REJECT
?object_type=Story
?object_id=<uuid>
?date_from=2025-01-01&date_to=2025-12-31
```

---

## 6E — Redis Caching Strategy (§46)

| Cache Key | TTL | Invalidated When |
|---|---|---|
| `homepage` | 15 min | Any homepage section updated |
| `trending_stories` | 4 hours | `calculate_trending_scores` runs |
| `public_writer_{slug}` | 30 min | Writer profile updated |
| `public_story_{slug}` | 30 min | Story updated/published |
| `categories_list` | 1 hour | Category created/updated |
| `site_settings` | 1 hour | SiteSettings saved |
| `platform_analytics_overview` | 1 hour | Daily aggregation runs |

**Usage Pattern:**
```python
def get_homepage():
    cached = cache.get("homepage")
    if cached:
        return cached
    data = HomepageService.build()
    cache.set("homepage", data, 60 * 15)
    return data
```

---

## 6F — Celery Beat Schedule Summary (§45)

Add to Django admin → Celery Beat → Periodic Tasks, or set programmatically:

```python
# config/celery.py — beat_schedule
app.conf.beat_schedule = {
    "calculate-trending-scores": {
        "task": "apps.analytics.tasks.calculate_trending_scores",
        "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours
    },
    "aggregate-daily-story-analytics": {
        "task": "apps.analytics.tasks.aggregate_daily_analytics",
        "schedule": crontab(minute=0, hour=1),      # 1 AM daily
    },
    "aggregate-daily-writer-analytics": {
        "task": "apps.analytics.tasks.aggregate_writer_analytics",
        "schedule": crontab(minute=30, hour=1),     # 1:30 AM daily
    },
    "aggregate-daily-platform-analytics": {
        "task": "apps.analytics.tasks.aggregate_platform_analytics",
        "schedule": crontab(minute=0, hour=2),      # 2 AM daily
    },
    "publish-scheduled-stories": {
        "task": "apps.stories.tasks.publish_scheduled_stories",
        "schedule": crontab(minute="*/15"),         # Every 15 minutes
    },
    "cleanup-expired-sessions": {
        "task": "apps.accounts.tasks.cleanup_expired_sessions",
        "schedule": crontab(minute=0, hour=3),      # 3 AM daily
    },
}
```

---

## 6G — Production Optimization Checklist (§48)

- [ ] `select_related` and `prefetch_related` on all nested FK queries
- [ ] `only()` or `defer()` to limit heavy field fetching
- [ ] `.count()` not `len()` on QuerySets
- [ ] DB index coverage on all filter/order fields
- [ ] `bulk_create()` for batch inserts
- [ ] `update_fields` on every `.save()` call
- [ ] Redis cache warming for homepage on deploy
- [ ] Connection pooling configured (`CONN_MAX_AGE=600` in production settings)
- [ ] Cloudinary signed URLs with expiry for private media
- [ ] `gunicorn` with 4 workers on Railway

---

## Testing Checklist (§48)

- [ ] `test_daily_story_aggregation`
- [ ] `test_aggregate_writer_day`
- [ ] `test_aggregate_platform_day`
- [ ] `test_trending_score_calculation`
- [ ] `test_trending_score_with_recency_bonus`
- [ ] `test_trending_score_verified_writer_bonus`
- [ ] `test_recommendation_by_category`
- [ ] `test_recommendation_fallback_to_trending`
- [ ] `test_recommendation_excludes_already_read`
- [ ] `test_audit_log_created_on_approve`
- [ ] `test_audit_log_created_on_reject`
- [ ] `test_audit_log_created_on_verify_writer`
- [ ] `test_homepage_cache_hit`
- [ ] `test_homepage_cache_invalidated_on_section_update`
- [ ] `test_trending_cache_populated`
- [ ] `test_analytics_export_csv`
- [ ] `test_scheduled_story_published`
- [ ] `test_expired_sessions_cleaned_up`
