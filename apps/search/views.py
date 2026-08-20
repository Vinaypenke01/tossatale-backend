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
        sort_by = request.query_params.get("sort", "relevance")
        category_filter = request.query_params.get("category", "").strip()

        results = {}

        # 1. Stories
        if search_type in ["all", "story", "stories"]:
            story_qs = Story.objects.filter(status="PUBLISHED")
            if query:
                story_qs = story_qs.filter(
                    Q(title__icontains=query)
                    | Q(subtitle__icontains=query)
                    | Q(plain_text_content__icontains=query)
                    | Q(writer__user__first_name__icontains=query)
                    | Q(writer__user__last_name__icontains=query)
                    | Q(writer__user__display_name__icontains=query)
                    | Q(writer__slug__icontains=query)
                    | Q(category__name__icontains=query)
                    | Q(story_tags__tag__name__icontains=query)
                ).distinct()
            if category_filter:
                story_qs = story_qs.filter(
                    Q(category__slug__iexact=category_filter) | Q(category__name__iexact=category_filter)
                )

            if sort_by == "newest":
                story_qs = story_qs.order_by("-published_at")
            elif sort_by == "popular":
                story_qs = story_qs.order_by("-views_count", "-published_at")
            elif sort_by == "likes":
                story_qs = story_qs.order_by("-likes_count", "-published_at")
            else:
                story_qs = story_qs.order_by("-trending_score", "-views_count", "-published_at")

            stories = story_qs.select_related("writer", "writer__user", "category")[:24]
            results["stories"] = StoryListSerializer(stories, many=True, context={"request": request}).data

        # 2. Writers
        if search_type in ["all", "writer", "writers"]:
            writer_qs = WriterProfile.objects.filter(is_active=True)
            if query:
                writer_qs = writer_qs.filter(
                    Q(user__first_name__icontains=query)
                    | Q(user__last_name__icontains=query)
                    | Q(user__display_name__icontains=query)
                    | Q(user__email__icontains=query)
                    | Q(bio__icontains=query)
                    | Q(slug__icontains=query)
                ).distinct()
            else:
                writer_qs = writer_qs.order_by("-is_verified", "-total_published_stories")

            writer_qs = writer_qs.select_related("user")[:18]
            results["writers"] = WriterProfileSerializer(writer_qs, many=True).data

        # 3. Categories
        if search_type in ["all", "category", "categories"]:
            cat_qs = Category.objects.filter(is_active=True)
            if query:
                cat_qs = cat_qs.filter(
                    Q(name__icontains=query) | Q(description__icontains=query) | Q(slug__icontains=query)
                )
            results["categories"] = CategorySerializer(cat_qs[:12], many=True).data

        # 4. Blogs
        if search_type in ["all", "blog", "blogs"]:
            blog_qs = Blog.objects.filter(status="PUBLISHED")
            if query:
                blog_qs = blog_qs.filter(
                    Q(title__icontains=query) | Q(subtitle__icontains=query) | Q(plain_text_content__icontains=query)
                )
            blog_qs = blog_qs.select_related("category").order_by("-published_at")[:12]
            results["blogs"] = BlogSerializer(blog_qs, many=True).data

        # 5. Series
        if search_type in ["all", "series"]:
            series_qs = StorySeries.objects.filter(status="PUBLISHED")
            if query:
                series_qs = series_qs.filter(
                    Q(title__icontains=query) | Q(description__icontains=query)
                )
            series_qs = series_qs.select_related("writer").order_by("-created_at")[:12]
            results["series"] = StorySeriesSerializer(series_qs, many=True).data

        # Calculate counts
        counts = {
            "stories": len(results.get("stories", [])),
            "writers": len(results.get("writers", [])),
            "categories": len(results.get("categories", [])),
            "blogs": len(results.get("blogs", [])),
            "series": len(results.get("series", [])),
        }
        counts["total"] = sum(counts.values())
        results["counts"] = counts

        return success_response(data=results)
