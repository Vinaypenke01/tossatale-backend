"""
apps/analytics/services.py — Analytics, Trending Engine, and Recommendation Services per §39, §40, §41
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum
from django.core.cache import cache

from apps.stories.models import Story
from apps.writers.models import WriterProfile
from apps.engagements.models import StoryView, StoryLike, StoryShare, StoryBookmark, RecentlyRead
from apps.analytics.models import DailyStoryAnalytics, DailyWriterAnalytics, DailyPlatformAnalytics


class TrendingService:
    """
    Calculates dynamic trending score for stories per §40.2.
    Formula:
      score = (views_7d * 1.0) + (likes_7d * 2.0) + (shares_7d * 3.0) + (bookmarks_7d * 1.5)
              + recency_bonus + verified_writer_bonus
    """

    @classmethod
    def calculate_score(cls, story: Story) -> float:
        now = timezone.now()
        start_7d = now - timedelta(days=7)

        views_7d = StoryView.objects.filter(story=story, viewed_at__gte=start_7d).count()
        likes_7d = StoryLike.objects.filter(story=story, created_at__gte=start_7d).count()
        shares_7d = StoryShare.objects.filter(story=story, shared_at__gte=start_7d).count()
        bookmarks_7d = StoryBookmark.objects.filter(story=story, created_at__gte=start_7d).count()

        # Recency bonus: max(0, 100 - days_since_published * 10)
        days_since_pub = 0
        if story.published_at:
            days_since_pub = max(0, (now - story.published_at).days)
        recency_bonus = max(0, 100 - (days_since_pub * 10))

        # Verified writer bonus: 20 if verified
        verified_bonus = 20.0 if (story.writer and story.writer.is_verified) else 0.0

        score = (
            (views_7d * 1.0)
            + (likes_7d * 2.0)
            + (shares_7d * 3.0)
            + (bookmarks_7d * 1.5)
            + recency_bonus
            + verified_bonus
        )
        return round(score, 2)

    @classmethod
    def update_all_trending_scores(cls):
        """Updates trending scores for all published stories and caches top 10 in Redis."""
        published_stories = Story.objects.filter(status="PUBLISHED")
        for story in published_stories:
            score = cls.calculate_score(story)
            story.trending_score = score
            story.save(update_fields=["trending_score"])

        top = Story.objects.filter(status="PUBLISHED").order_by("-trending_score")[:10]
        top_data = [
            {
                "id": str(s.id),
                "title": s.title,
                "slug": s.slug,
                "trending_score": float(s.trending_score),
                "writer_name": s.writer.pen_name,
            }
            for s in top
        ]
        # Cache trending stories in Redis for 4 hours (14,400 seconds)
        cache.set("trending_stories", top_data, 14400)
        return top_data


class RecommendationService:
    """
    Content-based recommendation engine per §41.
    Matches top read categories in reader's history to unread trending stories.
    """

    @classmethod
    def get_recommendations(cls, user, limit: int = 6):
        if not user or not user.is_authenticated:
            return Story.objects.filter(status="PUBLISHED").order_by("-trending_score")[:limit]

        # 1. Get user's recently read story IDs
        read_story_ids = list(
            RecentlyRead.objects.filter(user=user).values_list("story_id", flat=True)[:20]
        )

        # 2. Get top 3 categories from user's history
        top_categories = list(
            Story.objects.filter(id__in=read_story_ids)
            .values("category_id")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")[:3]
            .values_list("category_id", flat=True)
        )

        # 3. Query unread stories in those categories ordered by trending_score
        recommendations = []
        if top_categories:
            recommendations = list(
                Story.objects.filter(
                    status="PUBLISHED", category_id__in=top_categories
                ).exclude(id__in=read_story_ids).order_by("-trending_score")[:limit]
            )

        # 4. Fallback to global trending if recommendations count < limit
        if len(recommendations) < limit:
            needed = limit - len(recommendations)
            existing_ids = [s.id for s in recommendations] + read_story_ids
            fallback = list(
                Story.objects.filter(status="PUBLISHED")
                .exclude(id__in=existing_ids)
                .order_by("-trending_score")[:needed]
            )
            recommendations.extend(fallback)

        return recommendations[:limit]


class AnalyticsService:
    """
    Aggregates daily statistics for stories, writers, and platform overview.
    """

    @classmethod
    def aggregate_story_day(cls, story: Story, date):
        views_qs = StoryView.objects.filter(story=story, viewed_at__date=date)
        views_cnt = views_qs.count()
        unique_cnt = views_qs.filter(is_unique_view=True).count()
        likes_cnt = StoryLike.objects.filter(story=story, created_at__date=date).count()
        shares_cnt = StoryShare.objects.filter(story=story, shared_at__date=date).count()
        bookmarks_cnt = StoryBookmark.objects.filter(story=story, created_at__date=date).count()

        DailyStoryAnalytics.objects.update_or_create(
            story=story,
            date=date,
            defaults={
                "views": views_cnt,
                "unique_views": unique_cnt,
                "likes": likes_cnt,
                "shares": shares_cnt,
                "bookmarks": bookmarks_cnt,
            },
        )

    @classmethod
    def aggregate_platform_day(cls, date):
        views = StoryView.objects.filter(viewed_at__date=date).count()
        unique_vis = StoryView.objects.filter(viewed_at__date=date, is_unique_view=True).count()
        published_cnt = Story.objects.filter(published_at__date=date).count()
        likes_cnt = StoryLike.objects.filter(created_at__date=date).count()

        DailyPlatformAnalytics.objects.update_or_create(
            date=date,
            defaults={
                "total_page_views": views,
                "unique_visitors": unique_vis,
                "total_stories_published": published_cnt,
                "total_likes": likes_cnt,
            },
        )
