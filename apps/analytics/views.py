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


class AdminAnalyticsOverviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        total_stories = Story.objects.filter(status="PUBLISHED").count()
        total_views = Story.objects.aggregate(total=Sum("views_count"))["total"] or 0
        total_likes = Story.objects.aggregate(total=Sum("likes_count"))["total"] or 0
        total_unauth_likes = Story.objects.aggregate(total=Sum("unauthenticated_like_attempts"))["total"] or 0
        total_writers = WriterProfile.objects.count()

        recent_daily = DailyPlatformAnalytics.objects.all()[:30]

        data = {
            "platform_summary": {
                "total_published_stories": total_stories,
                "total_views": total_views,
                "total_likes": total_likes,
                "total_unauthenticated_like_attempts": total_unauth_likes,
                "total_writers": total_writers,
            },
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
