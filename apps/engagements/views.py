"""
apps/engagements/views.py — Public Story and Reader Dashboard Views
Implements public story APIs, reader engagements (likes, bookmarks, shares, views), and Reader Dashboard per §27 & §28.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, F
from django.core.cache import cache

from common.constants import StoryStatus
from common.responses import success_response, created_response
from common.pagination import StandardResultsSetPagination
from apps.stories.models import Story
from apps.writers.models import WriterProfile
from apps.stories.serializers import StoryListSerializer, StoryDetailSerializer
from apps.engagements.models import StoryLike, StoryBookmark, RecentlyRead
from apps.engagements.serializers import (
    StoryLikeSerializer,
    StoryBookmarkSerializer,
    RecentlyReadSerializer,
    RecordViewSerializer,
    RecordShareSerializer,
)
from apps.engagements.services import EngagementService


# --- Public Story Views ---

class PublicStoryListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Browse published stories with category, tag, writer, series, verified, and ordering filters."""
        queryset = Story.objects.filter(status=StoryStatus.PUBLISHED).select_related("writer", "category").prefetch_related("story_tags__tag")

        search_param = request.query_params.get("search")
        category_param = request.query_params.get("category")
        tag_param = request.query_params.get("tag")
        writer_param = request.query_params.get("writer")
        featured_param = request.query_params.get("is_featured")
        verified_param = request.query_params.get("is_verified")
        ordering_param = request.query_params.get("ordering", "-published_at")

        if search_param:
            queryset = queryset.filter(
                Q(title__icontains=search_param)
                | Q(subtitle__icontains=search_param)
                | Q(plain_text_content__icontains=search_param)
            )
        if category_param:
            queryset = queryset.filter(
                Q(category__slug__iexact=category_param) | Q(category__id__iexact=category_param)
            )
        if tag_param:
            queryset = queryset.filter(
                Q(story_tags__tag__slug__iexact=tag_param) | Q(story_tags__tag__name__iexact=tag_param)
            )
        if writer_param:
            queryset = queryset.filter(writer__slug=writer_param)
        if featured_param is not None:
            queryset = queryset.filter(is_featured=featured_param.lower() in ["true", "1"])
        if verified_param is not None:
            queryset = queryset.filter(writer__is_verified=verified_param.lower() in ["true", "1"])

        # Ordering
        valid_orderings = [
            "-published_at", "published_at",
            "-views_count", "views_count",
            "-likes_count", "likes_count",
            "-trending_score", "trending_score",
            "estimated_reading_time", "-estimated_reading_time",
        ]
        if ordering_param in valid_orderings:
            queryset = queryset.order_by(ordering_param)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = StoryListSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class PublicStoryDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        """Fetch published story details by slug and record view with 1-view-per-day deduplication."""
        story = get_object_or_404(
            Story.objects.select_related("writer", "category").prefetch_related("story_tags__tag"),
            slug=slug,
            status=StoryStatus.PUBLISHED,
        )

        # Record view with strict 1 view per user/IP per day deduplication
        ip_addr = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
        EngagementService.record_view(
            story=story,
            user=request.user if request.user.is_authenticated else None,
            session_id=request.session.session_key or "",
            ip_address=ip_addr,
        )

        return success_response(data=StoryDetailSerializer(story, context={"request": request}).data)


class PublicRelatedStoriesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        """Fetch contextually related stories in the same category or tags."""
        story = get_object_or_404(Story, slug=slug, status=StoryStatus.PUBLISHED)
        related = Story.objects.filter(
            status=StoryStatus.PUBLISHED, category=story.category
        ).exclude(id=story.id).order_by("-views_count")[:6]

        serializer = StoryListSerializer(related, many=True)
        return success_response(data=serializer.data)


class RecordStoryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        story = get_object_or_404(Story, pk=pk, status=StoryStatus.PUBLISHED)
        serializer = RecordViewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        ip_address = request.META.get("REMOTE_ADDR", "")

        view = EngagementService.record_view(
            story=story,
            user=user,
            session_id=serializer.validated_data.get("session_id", ""),
            ip_address=ip_address,
            referrer=serializer.validated_data.get("referrer", ""),
            reading_duration=serializer.validated_data.get("reading_duration", 0),
            completion_percentage=serializer.validated_data.get("completion_percentage", 0.0),
        )

        return success_response(
            data={"is_unique_view": view.is_unique_view},
            message="View recorded."
        )


class RecordStoryShareView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        story = get_object_or_404(Story, pk=pk, status=StoryStatus.PUBLISHED)
        serializer = RecordShareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        ip_address = request.META.get("REMOTE_ADDR", "")

        EngagementService.record_share(
            story=story,
            platform=serializer.validated_data["platform"],
            user=user,
            session_id=serializer.validated_data.get("session_id", ""),
            ip_address=ip_address,
        )

        return success_response(message="Share recorded.")


# --- Reader Dashboard Views ---

class ReaderDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Fetch reader dashboard summary: recently read, liked stories, bookmarks, statistics."""
        user = request.user

        recently_read = RecentlyRead.objects.filter(user=user).select_related("story__writer", "story__category")[:10]
        liked_stories = StoryLike.objects.filter(user=user).select_related("story__writer", "story__category")[:10]
        bookmarks = StoryBookmark.objects.filter(user=user).select_related("story__writer", "story__category")[:10]

        total_read = RecentlyRead.objects.filter(user=user).count()

        return success_response(data={
            "recently_read": RecentlyReadSerializer(recently_read, many=True).data,
            "liked_stories": StoryLikeSerializer(liked_stories, many=True).data,
            "bookmarks": StoryBookmarkSerializer(bookmarks, many=True).data,
            "reading_statistics": {
                "total_stories_read": total_read,
            }
        })


class StoryLikeToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        story = get_object_or_404(Story, pk=pk)
        like = EngagementService.like_story(request.user, story)
        return created_response(
            data={"likes_count": story.likes_count},
            message="Story liked successfully."
        )

    def delete(self, request, pk):
        story = get_object_or_404(Story, pk=pk)
        EngagementService.unlike_story(request.user, story)
        return success_response(
            data={"likes_count": story.likes_count},
            message="Story unliked."
        )


class StoryLikeDismissView(APIView):
    """Tracks when an unauthenticated reader attempts to like a story but dismisses login."""
    permission_classes = [AllowAny]

    def post(self, request, pk):
        story = get_object_or_404(Story, pk=pk)
        attempts = EngagementService.record_unauthenticated_like_attempt(story)
        return success_response(
            data={"unauthenticated_like_attempts": attempts},
            message="Dismissed like attempt recorded."
        )


class StoryBookmarkToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        story = get_object_or_404(Story, pk=pk)
        bookmark = EngagementService.bookmark_story(request.user, story)
        return created_response(
            data={"bookmarks_count": story.bookmarks_count},
            message="Story bookmarked."
        )

    def delete(self, request, pk):
        story = get_object_or_404(Story, pk=pk)
        EngagementService.remove_bookmark(request.user, story)
        return success_response(
            data={"bookmarks_count": story.bookmarks_count},
            message="Bookmark removed."
        )


class ReaderLikedStoriesView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = StoryLike.objects.filter(user=request.user).select_related("story__writer", "story__category")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = StoryLikeSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ReaderBookmarksView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = StoryBookmark.objects.filter(user=request.user).select_related("story__writer", "story__category")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = StoryBookmarkSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ReaderRecentlyReadView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = RecentlyRead.objects.filter(user=request.user).select_related("story__writer", "story__category")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = RecentlyReadSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def delete(self, request):
        """Clear all reading history."""
        RecentlyRead.objects.filter(user=request.user).delete()
        return success_response(message="Reading history cleared.")
