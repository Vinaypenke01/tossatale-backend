"""
apps/analytics/tasks.py — Celery tasks for periodic analytics aggregation and trending scores
"""
import logging
from datetime import date, timedelta
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("apps.analytics")


@shared_task
def calculate_trending_scores():
    """Calculates trending score for all published stories every 4 hours per §40."""
    try:
        from apps.analytics.services import TrendingService
        top_stories = TrendingService.update_all_trending_scores()
        logger.info("Updated trending scores for published stories. Top 10 cached.")
        return len(top_stories)
    except Exception as exc:
        logger.error("Failed to update trending scores: %s", exc)
        raise exc


@shared_task
def aggregate_daily_analytics():
    """Runs daily at 1:00 AM to aggregate story analytics for yesterday per §45."""
    try:
        from apps.stories.models import Story
        from apps.analytics.services import AnalyticsService

        yesterday = date.today() - timedelta(days=1)
        stories = Story.objects.filter(status="PUBLISHED")
        count = 0

        for story in stories:
            AnalyticsService.aggregate_story_day(story, yesterday)
            count += 1

        logger.info("Aggregated daily story analytics for %d stories on %s.", count, yesterday)
        return count
    except Exception as exc:
        logger.error("Failed daily story analytics aggregation: %s", exc)
        raise exc


@shared_task
def aggregate_platform_analytics():
    """Runs daily at 2:00 AM to aggregate platform-wide analytics for yesterday per §45."""
    try:
        from apps.analytics.services import AnalyticsService
        yesterday = date.today() - timedelta(days=1)
        AnalyticsService.aggregate_platform_day(yesterday)
        logger.info("Aggregated daily platform analytics for %s.", yesterday)
    except Exception as exc:
        logger.error("Failed daily platform analytics aggregation: %s", exc)
        raise exc
