"""
apps/search/views.py — Unified Multi-Model Search View per §27 & §38
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db.models import Q

from common.responses import success_response
from apps.stories.models import Story
from apps.stories.serializers import StoryListSerializer
from apps.blogs.models import Blog
from apps.blogs.serializers import BlogSerializer
from apps.writers.models import WriterProfile
from apps.writers.serializers import WriterProfileSerializer
from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer
from apps.series.models import StorySeries
from apps.series.serializers import StorySeriesSerializer


class UnifiedSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        search_type = request.query_params.get("type", "all").lower()

        if not query:
            return success_response(data={
                "stories": [], "blogs": [], "writers": [], "categories": [], "series": []
            })

        results = {}

        if search_type in ["all", "story"]:
            stories = Story.objects.filter(
                status="PUBLISHED"
            ).filter(
                Q(title__icontains=query) | Q(subtitle__icontains=query) | Q(plain_text_content__icontains=query)
            ).select_related("writer", "category")[:10]
            results["stories"] = StoryListSerializer(stories, many=True).data

        if search_type in ["all", "blog"]:
            blogs = Blog.objects.filter(
                status="PUBLISHED"
            ).filter(
                Q(title__icontains=query) | Q(subtitle__icontains=query) | Q(plain_text_content__icontains=query)
            ).select_related("category")[:10]
            results["blogs"] = BlogSerializer(blogs, many=True).data

        if search_type in ["all", "writer"]:
            writers = WriterProfile.objects.filter(
                Q(pen_name__icontains=query) | Q(bio__icontains=query)
            )[:10]
            results["writers"] = WriterProfileSerializer(writers, many=True).data

        if search_type in ["all", "category"]:
            categories = Category.objects.filter(
                is_active=True
            ).filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )[:10]
            results["categories"] = CategorySerializer(categories, many=True).data

        if search_type in ["all", "series"]:
            series_qs = StorySeries.objects.filter(
                status="PUBLISHED"
            ).filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            ).select_related("writer")[:10]
            results["series"] = StorySeriesSerializer(series_qs, many=True).data

        return success_response(data=results)
