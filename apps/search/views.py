"""
apps/search/views.py — Unified Multi-Model Search View per §27 & §38
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db.models import Q

from common.responses import success_response
from common.utils import get_engagement_context
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

        try:
            page = max(1, int(request.query_params.get("page", 1) or 1))
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = min(50, max(1, int(request.query_params.get("page_size", 9) or 9)))
        except (ValueError, TypeError):
            page_size = 9

        offset = (page - 1) * page_size

        # 1. Base querysets across all models
        story_qs = Story.objects.filter(status="PUBLISHED")
        if query:
            story_qs = story_qs.filter(
                Q(title__icontains=query)
                | Q(subtitle__icontains=query)
                | Q(plain_text_content__icontains=query)
                | Q(content__icontains=query)
                | Q(seo_title__icontains=query)
                | Q(seo_description__icontains=query)
                | Q(writer__user__first_name__icontains=query)
                | Q(writer__user__last_name__icontains=query)
                | Q(writer__user__display_name__icontains=query)
                | Q(writer__slug__icontains=query)
                | Q(category__name__icontains=query)
                | Q(category__slug__icontains=query)
                | Q(story_tags__tag__name__icontains=query)
                | Q(story_tags__tag__slug__icontains=query)
            ).distinct()
        if category_filter:
            story_qs = story_qs.filter(
                Q(category__slug__iexact=category_filter) | Q(category__name__iexact=category_filter)
            )

        writer_qs = WriterProfile.objects.filter(is_active=True)
        if query:
            writer_qs = writer_qs.filter(
                Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__display_name__icontains=query)
                | Q(user__email__icontains=query)
                | Q(bio__icontains=query)
                | Q(tagline__icontains=query)
                | Q(author_title__icontains=query)
                | Q(location__icontains=query)
                | Q(slug__icontains=query)
            ).distinct()
        else:
            writer_qs = writer_qs.order_by("-is_verified", "-total_published_stories")

        cat_qs = Category.objects.filter(is_active=True)
        if query:
            cat_qs = cat_qs.filter(
                Q(name__icontains=query) | Q(description__icontains=query) | Q(slug__icontains=query)
            )

        blog_qs = Blog.objects.filter(status="PUBLISHED")
        if query:
            blog_qs = blog_qs.filter(
                Q(title__icontains=query)
                | Q(subtitle__icontains=query)
                | Q(plain_text_content__icontains=query)
                | Q(content__icontains=query)
                | Q(seo_title__icontains=query)
                | Q(seo_description__icontains=query)
                | Q(category__name__icontains=query)
                | Q(blog_tags__tag__name__icontains=query)
            ).distinct()

        series_qs = StorySeries.objects.filter(status="PUBLISHED")
        if query:
            series_qs = series_qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(writer__user__first_name__icontains=query)
                | Q(writer__user__last_name__icontains=query)
                | Q(writer__user__display_name__icontains=query)
                | Q(writer__slug__icontains=query)
            ).distinct()

        # Compute accurate counts for all tabs across entire database
        counts = {
            "stories": story_qs.count(),
            "writers": writer_qs.count(),
            "categories": cat_qs.count(),
            "blogs": blog_qs.count(),
            "series": series_qs.count(),
        }
        counts["total"] = sum(counts.values())

        results = {"counts": counts}

        # 2. Serialize requested model(s)
        if search_type in ["all", "story", "stories"]:
            if sort_by == "newest":
                story_qs = story_qs.order_by("-published_at")
            elif sort_by == "popular":
                story_qs = story_qs.order_by("-views_count", "-published_at")
            elif sort_by == "likes":
                story_qs = story_qs.order_by("-likes_count", "-published_at")
            else:
                story_qs = story_qs.order_by("-trending_score", "-views_count", "-published_at")

            stories = story_qs.select_related("writer", "writer__user", "category").prefetch_related("story_tags__tag", "reviews")[offset : offset + page_size]
            context = {"request": request, **get_engagement_context(request)}
            results["stories"] = StoryListSerializer(stories, many=True, context=context).data

        if search_type in ["all", "writer", "writers"]:
            writers = writer_qs.select_related("user")[offset : offset + page_size]
            results["writers"] = WriterProfileSerializer(writers, many=True).data

        if search_type in ["all", "category", "categories"]:
            results["categories"] = CategorySerializer(cat_qs[offset : offset + page_size], many=True).data

        if search_type in ["all", "blog", "blogs"]:
            blogs = blog_qs.select_related("category").order_by("-published_at")[offset : offset + page_size]
            results["blogs"] = BlogSerializer(blogs, many=True).data

        if search_type in ["all", "series"]:
            series = series_qs.select_related("writer").order_by("-created_at")[offset : offset + page_size]
            results["series"] = StorySeriesSerializer(series, many=True).data

        # Determine target active count for pagination metadata
        active_key = search_type if search_type in counts else "stories"
        if active_key in ["story", "stories"]:
            active_count = counts["stories"]
        elif active_key in ["writer", "writers"]:
            active_count = counts["writers"]
        elif active_key in ["category", "categories"]:
            active_count = counts["categories"]
        elif active_key in ["blog", "blogs"]:
            active_count = counts["blogs"]
        elif active_key in ["series"]:
            active_count = counts["series"]
        else:
            active_count = counts["stories"]

        total_pages = max(1, (active_count + page_size - 1) // page_size) if active_count > 0 else 1

        results["pagination"] = {
            "page": page,
            "page_size": page_size,
            "total_count": active_count,
            "total_pages": total_pages,
        }

        return success_response(data=results)
