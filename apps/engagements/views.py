"""
apps/engagements/views.py — Public Story and Reader Dashboard Views
Implements public story APIs, reader engagements (likes, bookmarks, shares, views), and Reader Dashboard per §27 & §28.
"""
import uuid
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum, F
from django.core.cache import cache

from common.constants import StoryStatus
from common.responses import success_response, created_response
from common.pagination import StandardResultsSetPagination
from common.utils import get_engagement_context
from apps.stories.models import Story
from apps.writers.models import WriterProfile
from apps.stories.serializers import StoryListSerializer, StoryDetailSerializer
from apps.engagements.models import StoryLike, StoryBookmark, StoryView, RecentlyRead
from apps.engagements.serializers import (
    StoryLikeSerializer,
    StoryBookmarkSerializer,
    RecentlyReadSerializer,
    RecordViewSerializer,
    RecordShareSerializer,
)
from apps.engagements.services import EngagementService


def _get_story_by_pk_or_slug(pk, status_filter=None):
    """Resolves a story by UUID primary key or alphanumeric slug."""
    qs = Story.objects.all()
    if status_filter:
        qs = qs.filter(status=status_filter)
    try:
        val = uuid.UUID(str(pk))
        story = qs.filter(id=val).first()
        if story:
            return story
    except (ValueError, AttributeError):
        pass
    return get_object_or_404(qs, slug=pk)


# --- Public Story Views ---

class PublicStoryListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Browse published stories with category, tag, writer, series, verified, and ordering filters."""
        queryset = Story.objects.filter(status=StoryStatus.PUBLISHED).select_related("writer", "category").prefetch_related("story_tags__tag", "reviews")

        search_param = request.query_params.get("search")
        category_param = request.query_params.get("category")
        tag_param = request.query_params.get("tag")
        writer_param = request.query_params.get("writer")
        featured_param = request.query_params.get("is_featured")
        verified_param = request.query_params.get("is_verified")
        ordering_param = request.query_params.get("ordering", "-published_at")

        if search_param:
            search_q = Q(title__icontains=search_param) | Q(subtitle__icontains=search_param)
            search_q.add(Q(plain_text_content__icontains=search_param), Q.OR)
            queryset = queryset.filter(search_q)
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
        context = {"request": request, **get_engagement_context(request)}
        serializer = StoryListSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)


class PublicStoryDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        """Fetch published story details by slug and record view with 1-view-per-day deduplication."""
        story = get_object_or_404(
            Story.objects.select_related("writer", "category").prefetch_related("story_tags__tag", "reviews"),
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

        context = {"request": request, **get_engagement_context(request)}
        return success_response(data=StoryDetailSerializer(story, context=context).data)


class PublicRelatedStoriesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        """Fetch contextually related stories in the same category or tags."""
        story = get_object_or_404(Story, slug=slug, status=StoryStatus.PUBLISHED)
        related = Story.objects.filter(
            status=StoryStatus.PUBLISHED, category=story.category
        ).exclude(id=story.id).select_related("writer", "category").prefetch_related("story_tags__tag", "reviews").order_by("-views_count")[:6]

        context = {"request": request, **get_engagement_context(request)}
        serializer = StoryListSerializer(related, many=True, context=context)
        return success_response(data=serializer.data)


class RecordStoryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        story = _get_story_by_pk_or_slug(pk, status_filter=StoryStatus.PUBLISHED)
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
        story = _get_story_by_pk_or_slug(pk, status_filter=StoryStatus.PUBLISHED)
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
        context = {"request": request, **get_engagement_context(request)}

        recently_read = RecentlyRead.objects.filter(user=user).select_related("story__writer", "story__category").prefetch_related("story__story_tags__tag", "story__reviews")[:10]
        liked_stories = StoryLike.objects.filter(user=user).select_related("story__writer", "story__category").prefetch_related("story__story_tags__tag", "story__reviews")[:10]
        bookmarks = StoryBookmark.objects.filter(user=user).select_related("story__writer", "story__category").prefetch_related("story__story_tags__tag", "story__reviews")[:10]

        total_read = RecentlyRead.objects.filter(user=user).count()
        total_liked = StoryLike.objects.filter(user=user).count()
        total_bookmarked = StoryBookmark.objects.filter(user=user).count()

        total_duration_secs = StoryView.objects.filter(user=user).aggregate(total=Sum("reading_duration"))["total"] or 0
        if total_duration_secs > 0:
            hours_read = round(total_duration_secs / 3600, 1)
        elif total_read > 0:
            total_duration_mins = RecentlyRead.objects.filter(user=user).aggregate(total=Sum("story__estimated_reading_time"))["total"] or 0
            hours_read = round(total_duration_mins / 60, 1)
        else:
            hours_read = 0.0

        stats = {
            "total_stories_read": total_read,
            "recently_read_count": total_read,
            "total_liked_stories": total_liked,
            "total_bookmarked_stories": total_bookmarked,
            "hours_read": hours_read,
        }

        return success_response(data={
            "stats": stats,
            "recently_read": RecentlyReadSerializer(recently_read, many=True, context=context).data,
            "liked_stories": StoryLikeSerializer(liked_stories, many=True, context=context).data,
            "bookmarks": StoryBookmarkSerializer(bookmarks, many=True, context=context).data,
            "reading_statistics": {
                "total_stories_read": total_read,
                "total_liked_stories": total_liked,
                "total_bookmarked_stories": total_bookmarked,
                "hours_read": hours_read,
            }
        })


class StoryLikeToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        story = _get_story_by_pk_or_slug(pk)
        like = EngagementService.like_story(request.user, story)
        return created_response(
            data={"likes_count": story.likes_count},
            message="Story liked successfully."
        )

    def delete(self, request, pk):
        story = _get_story_by_pk_or_slug(pk)
        EngagementService.unlike_story(request.user, story)
        return success_response(
            data={"likes_count": story.likes_count},
            message="Story unliked."
        )


class StoryLikeDismissView(APIView):
    """Tracks when an unauthenticated reader attempts to like a story but dismisses login."""
    permission_classes = [AllowAny]

    def post(self, request, pk):
        story = _get_story_by_pk_or_slug(pk)
        attempts = EngagementService.record_unauthenticated_like_attempt(story)
        return success_response(
            data={"unauthenticated_like_attempts": attempts},
            message="Dismissed like attempt recorded."
        )


class StoryBookmarkToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        story = _get_story_by_pk_or_slug(pk)
        bookmark = EngagementService.bookmark_story(request.user, story)
        return created_response(
            data={"bookmarks_count": story.bookmarks_count},
            message="Story bookmarked."
        )

    def delete(self, request, pk):
        story = _get_story_by_pk_or_slug(pk)
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
