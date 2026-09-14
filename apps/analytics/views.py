"""
apps/analytics/views.py — Analytics Views for Writer & Admin per §29 & §30
"""
import csv
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Sum

from common.permissions import IsWriter, IsAdmin
from common.responses import success_response
from apps.writers.models import WriterProfile
from apps.stories.models import Story
from apps.stories.serializers import StoryListSerializer
from apps.analytics.models import DailyPlatformAnalytics
from apps.analytics.services import RecommendationService


class WriterAnalyticsOverviewView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]

    def get(self, request):
        from common.utils import generate_unique_slug
        writer, _ = WriterProfile.objects.get_or_create(
            user=request.user,
            defaults={
                "slug": generate_unique_slug(WriterProfile, request.user.get_full_name() or request.user.email.split("@")[0] or "writer"),
                "bio": "Tossatale Storyteller & Writer",
            }
        )
        stories = Story.objects.filter(writer=writer)

        total_views = stories.aggregate(total=Sum("views_count"))["total"] or 0
        total_likes = stories.aggregate(total=Sum("likes_count"))["total"] or 0
        total_shares = stories.aggregate(total=Sum("shares_count"))["total"] or 0
        total_bookmarks = stories.aggregate(total=Sum("bookmarks_count"))["total"] or 0

        published_stories = stories.filter(status="PUBLISHED").order_by("-views_count")[:10]

        return success_response(data={
            "summary": {
                "total_stories": stories.count(),
                "published_stories": stories.filter(status="PUBLISHED").count(),
                "draft_stories": stories.filter(status="DRAFT").count(),
                "in_review_stories": stories.filter(status="SUBMITTED").count(),
                "total_views": total_views,
                "total_likes": total_likes,
                "total_shares": total_shares,
                "total_bookmarks": total_bookmarks,
            },
            "top_stories": StoryListSerializer(published_stories, many=True, context={"request": request}).data,
        })


from django.db.models import Sum, Count, Q
from common.utils import get_engagement_context


class AdminAnalyticsOverviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        total_stories = Story.objects.filter(status="PUBLISHED").count()
        total_views = Story.objects.aggregate(total=Sum("views_count"))["total"] or 0
        total_likes = Story.objects.aggregate(total=Sum("likes_count"))["total"] or 0
        total_bookmarks = Story.objects.aggregate(total=Sum("bookmarks_count"))["total"] or 0
        total_shares = Story.objects.aggregate(total=Sum("shares_count"))["total"] or 0
        total_unauth_likes = Story.objects.aggregate(total=Sum("unauthenticated_like_attempts"))["total"] or 0
        total_writers = WriterProfile.objects.filter(is_active=True, is_deleted=False, user__is_active=True).count()

        # Category readership breakdown
        from apps.categories.models import Category
        categories = Category.objects.filter(category_type="STORY", is_active=True).annotate(
            story_count=Count("stories", filter=Q(stories__status="PUBLISHED")),
            total_views=Sum("stories__views_count", filter=Q(stories__status="PUBLISHED")),
            total_likes=Sum("stories__likes_count", filter=Q(stories__status="PUBLISHED"))
        ).order_by("-total_views")

        category_breakdown = [
            {
                "id": str(c.id),
                "name": c.name,
                "slug": c.slug,
                "story_count": c.story_count,
                "total_views": c.total_views or 0,
                "total_likes": c.total_likes or 0,
            }
            for c in categories if (c.story_count > 0 or (c.total_views or 0) > 0)
        ]

        context = {"request": request, **get_engagement_context(request)}
        all_stories_qs = Story.objects.all().select_related("writer", "writer__user", "category").prefetch_related("story_tags__tag", "reviews").order_by("-views_count", "-likes_count")

        recent_daily = DailyPlatformAnalytics.objects.all().order_by("-date")[:30]

        data = {
            "platform_summary": {
                "total_published_stories": total_stories,
                "total_views": total_views,
                "total_likes": total_likes,
                "total_bookmarks": total_bookmarks,
                "total_shares": total_shares,
                "total_unauthenticated_like_attempts": total_unauth_likes,
                "total_writers": total_writers,
            },
            "category_breakdown": category_breakdown,
            "all_stories": StoryListSerializer(all_stories_qs, many=True, context=context).data,
            "top_stories": StoryListSerializer(all_stories_qs.filter(status="PUBLISHED")[:10], many=True, context=context).data,
            "recent_daily_history": [
                {
                    "date": str(d.date),
                    "page_views": d.total_page_views,
                    "unique_visitors": d.unique_visitors,
                    "stories_published": d.total_stories_published,
                    "likes": d.total_likes,
                }
                for d in recent_daily
            ]
        }
        return success_response(data=data)


class AdminAnalyticsExportCSVView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="platform_analytics.csv"'

        writer = csv.writer(response)
        writer.writerow(["Date", "Page Views", "Unique Visitors", "Stories Published", "Total Likes"])

        records = DailyPlatformAnalytics.objects.all().order_by("-date")
        for r in records:
            writer.writerow([r.date, r.total_page_views, r.unique_visitors, r.total_stories_published, r.total_likes])

        return response
