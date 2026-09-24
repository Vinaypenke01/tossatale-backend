"""
apps/stories/views.py — Views for Writer and Admin Story Workflows
Implements DRF views for story creation, editing, submission, review queue, approvals, rejections, and revisions per Phase 2 spec.
"""
import uuid
from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import Q
from django.utils.text import slugify

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from common.constants import StoryStatus
from common.permissions import IsWriter, IsAdmin, IsAdminOrWriter
from common.responses import success_response, created_response, no_content_response
from common.pagination import StandardResultsSetPagination
from common.exceptions import ResourceNotFoundError, PermissionDeniedError, ServiceValidationError
from common.utils import resolve_category, get_engagement_context
from apps.accounts.constants import UserRole

from apps.categories.models import Category
from apps.writers.models import WriterProfile
from apps.stories.models import Story, StoryRevision, StoryReview, StoryChapter
from apps.stories.serializers import (
    StoryCreateSerializer,
    StoryUpdateSerializer,
    StoryListSerializer,
    StoryDetailSerializer,
    AdminStorySerializer,
    StoryRejectSerializer,
    StoryScheduleSerializer,
    StoryRevisionSerializer,
    StoryReviewSerializer,
    StoryChapterSerializer,
    StoryChapterCreateUpdateSerializer,
)
from apps.stories.services import StoryService, ChapterService


def _get_writer_profile(user):
    """Gets the WriterProfile for a user, auto-creating if missing for writer/admin."""
    user_identifier = (
        getattr(user, "display_name", "")
        or getattr(user, "first_name", "")
        or getattr(user, "email", "writer")
    )
    if "@" in user_identifier:
        user_identifier = user_identifier.split("@")[0]

    writer_slug = slugify(user_identifier) or "writer"
    writer = WriterProfile.objects.filter(user=user).first()
    if not writer:
        if WriterProfile.objects.filter(slug=writer_slug).exists():
            writer_slug = f"{writer_slug}-{user.id}"
        writer, _ = WriterProfile.objects.get_or_create(
            user=user,
            defaults={"slug": writer_slug, "bio": "Tossatale Writer"}
        )
    return writer


class WriterStoryListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """List own stories with optional status, category, and search filters."""
        writer = _get_writer_profile(request.user)
        queryset = (
            Story.objects.filter(writer=writer)
            .select_related("writer", "category")
            .prefetch_related("story_tags__tag", "reviews")
            .order_by("-created_at")
        )

        status_param = request.query_params.get("status")
        category_param = request.query_params.get("category")
        search_param = request.query_params.get("search")

        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        if category_param:
            try:
                val = uuid.UUID(str(category_param))
                queryset = queryset.filter(Q(category__id=val) | Q(category__slug=category_param))
            except (ValueError, AttributeError):
                queryset = queryset.filter(category__slug=category_param)
        if search_param:
            queryset = queryset.filter(
                Q(title__icontains=search_param) | Q(subtitle__icontains=search_param)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        context = {"request": request, **get_engagement_context(request)}
        serializer = StoryListSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create a new story draft for writer."""
        writer = _get_writer_profile(request.user)

        data = request.data.copy()
        category_input = data.get("category")
        category_obj = resolve_category(category_input)

        if not category_obj:
            category_obj = Category.objects.filter(is_active=True).first()
            if not category_obj:
                category_obj = Category.objects.create(
                    name="General",
                    slug="general",
                    description="General stories and essays",
                    category_type="STORY",
                    is_active=True
                )

        if not category_obj.is_active:
            raise ServiceValidationError("The selected category is inactive.")

        data["category_id"] = str(category_obj.id)

        serializer = StoryCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        story = StoryService.create_story(writer, serializer.validated_data)
        attach_story_tags(story, request.data.get("tags") or request.data.get("tag_names"))

        if request.data.get("status") in [StoryStatus.PENDING_REVIEW, "PENDING_REVIEW"]:
            story = StoryService.submit_story(story, writer)

        return created_response(
            data=StoryDetailSerializer(story, context={"request": request, **get_engagement_context(request)}).data,
            message="Story submitted for review successfully." if story.status == StoryStatus.PENDING_REVIEW else "Story draft created successfully."
        )


class WriterStoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]

    def _get_story(self, request, pk):
        writer = _get_writer_profile(request.user)
        story = Story.objects.filter(slug=pk).first()
        if not story:
            try:
                uuid.UUID(str(pk))
                story = Story.objects.filter(id=pk).first()
            except (ValueError, TypeError):
                pass
        if not story:
            raise ResourceNotFoundError("Story not found.")
        if story.writer_id != writer.id and not request.user.is_staff:
            raise PermissionDeniedError("You do not have access to this story.")
        return story

    def get(self, request, pk):
        story = self._get_story(request, pk)
        context = {"request": request, **get_engagement_context(request)}
        return success_response(data=StoryDetailSerializer(story, context=context).data)

    def patch(self, request, pk):
        story = self._get_story(request, pk)
        data = request.data.copy()
        category_input = data.get("category") or data.get("category_slug") or data.get("category_id")
        if category_input:
            cat_obj = resolve_category(category_input)
            if not cat_obj:
                raise ServiceValidationError("Invalid category specified.")
            if not cat_obj.is_active:
                raise ServiceValidationError("The selected category is inactive.")
            data["category_id"] = str(cat_obj.id)

        serializer = StoryUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        updated_story = StoryService.update_story(story, serializer.validated_data, request.user)
        attach_story_tags(updated_story, request.data.get("tags") or request.data.get("tag_names"))

        if request.data.get("status") in [StoryStatus.PENDING_REVIEW, "PENDING_REVIEW"]:
            writer = _get_writer_profile(request.user)
            updated_story = StoryService.submit_story(updated_story, writer)

        context = {"request": request, **get_engagement_context(request)}
        return success_response(
            data=StoryDetailSerializer(updated_story, context=context).data,
            message="Story submitted for review successfully." if updated_story.status == StoryStatus.PENDING_REVIEW else "Story updated successfully."
        )

    def delete(self, request, pk):
        story = self._get_story(request, pk)
        StoryService.delete_story(story, request.user)
        return success_response(message="Story deleted successfully.", status_code=status.HTTP_200_OK)


class WriterStorySubmitView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]

    def post(self, request, pk):
        writer = _get_writer_profile(request.user)
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        submitted_story = StoryService.submit_story(story, writer)
        context = {"request": request, **get_engagement_context(request)}
        return success_response(
            data=StoryDetailSerializer(submitted_story, context=context).data,
            message="Story submitted for review successfully."
        )


class WriterStoryDuplicateView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]

    def post(self, request, pk):
        writer = _get_writer_profile(request.user)
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk, writer=writer)
        cloned_story = StoryService.duplicate_story(story, writer)
        context = {"request": request, **get_engagement_context(request)}
        return created_response(
            data=StoryDetailSerializer(cloned_story, context=context).data,
            message="Story duplicated into a new draft."
        )


# --- Admin Views ---

class AdminStoryListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = (
            Story.objects.all()
            .select_related("writer", "category", "reviewed_by")
            .prefetch_related("story_tags__tag", "reviews", "reviews__reviewer")
            .order_by("-created_at")
        )

        status_param = request.query_params.get("status")
        writer_param = request.query_params.get("writer")
        category_param = request.query_params.get("category")
        moderation_param = request.query_params.get("moderation_status")
        featured_param = request.query_params.get("is_featured")
        search_param = request.query_params.get("search")

        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        if writer_param:
            try:
                val = uuid.UUID(str(writer_param))
                queryset = queryset.filter(Q(writer__id=val) | Q(writer__slug=writer_param))
            except (ValueError, AttributeError):
                queryset = queryset.filter(Q(writer__slug=writer_param) | Q(writer__user__email__iexact=writer_param))
        if category_param:
            try:
                val = uuid.UUID(str(category_param))
                queryset = queryset.filter(Q(category__id=val) | Q(category__slug=category_param))
            except (ValueError, AttributeError):
                queryset = queryset.filter(category__slug=category_param)
        if moderation_param:
            queryset = queryset.filter(moderation_status=moderation_param.upper())
        if featured_param is not None:
            is_feat = featured_param.lower() in ["true", "1"]
            queryset = queryset.filter(is_featured=is_feat)
        if search_param:
            search_query = Q(title__icontains=search_param)
            search_query.add(Q(writer__slug__icontains=search_param), Q.OR)
            search_query.add(Q(writer__user__first_name__icontains=search_param), Q.OR)
            search_query.add(Q(writer__user__display_name__icontains=search_param), Q.OR)
            queryset = queryset.filter(search_query)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AdminStorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create and publish a story directly as Admin."""
        writer = _get_writer_profile(request.user)
        data = request.data.copy()
        category_input = data.get("category")
        category_obj = resolve_category(category_input)

        if not category_obj:
            category_obj = Category.objects.filter(is_active=True).first()
            if not category_obj:
                category_obj = Category.objects.create(
                    name="General",
                    slug="general",
                    description="General stories and essays",
                    category_type="STORY",
                    is_active=True
                )

        if not category_obj.is_active:
            raise ServiceValidationError("The selected category is inactive.")

        data["category_id"] = str(category_obj.id)

        serializer = StoryCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        story = StoryService.create_story(writer, serializer.validated_data)
        attach_story_tags(story, request.data.get("tags") or request.data.get("tag_names"))

        status_req = request.data.get("status")
        if status_req == StoryStatus.PUBLISHED:
            story = StoryService.publish_story(story, request.user)

        return created_response(
            data=AdminStorySerializer(story).data,
            message="Story created/published successfully."
        )


class AdminStoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_story(self, pk):
        story = Story.objects.filter(slug=pk).first()
        if not story:
            try:
                uuid.UUID(str(pk))
                story = Story.objects.filter(id=pk).first()
            except (ValueError, TypeError):
                pass
        if not story:
            raise ResourceNotFoundError("Story not found.")
        return story

    def get(self, request, pk):
        story = self._get_story(pk)
        return success_response(data=AdminStorySerializer(story).data)

    def patch(self, request, pk):
        story = self._get_story(pk)
        data = request.data.copy()
        category_input = data.get("category") or data.get("category_slug") or data.get("category_id")
        if category_input:
            cat_obj = resolve_category(category_input)
            if not cat_obj:
                raise ServiceValidationError("Invalid category specified.")
            if not cat_obj.is_active:
                raise ServiceValidationError("The selected category is inactive.")
            data["category_id"] = str(cat_obj.id)

        serializer = StoryUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        updated_story = StoryService.update_story(story, serializer.validated_data, request.user)
        attach_story_tags(updated_story, request.data.get("tags") or request.data.get("tag_names"))

        status_req = request.data.get("status")
        if status_req == StoryStatus.PUBLISHED and updated_story.status != StoryStatus.PUBLISHED:
            updated_story = StoryService.publish_story(updated_story, request.user)

        return success_response(data=AdminStorySerializer(updated_story).data, message="Story updated.")

    def delete(self, request, pk):
        story = self._get_story(pk)
        story.delete()
        return success_response(message="Story deleted by Admin.")


def attach_story_tags(story, raw_tags):
    if not raw_tags:
        return
    if isinstance(raw_tags, str):
        tag_names = [t.strip() for t in raw_tags.split(",") if t.strip()]
    elif isinstance(raw_tags, list):
        tag_names = [str(t).strip() for t in raw_tags if str(t).strip()]
    else:
        return

    from apps.categories.models import Tag
    from apps.stories.models import StoryTag

    story.story_tags.all().delete()
    for name in tag_names:
        tag_slug = slugify(name) or "tag"
        tag_obj = Tag.objects.filter(Q(slug=tag_slug) | Q(name__iexact=name)).first()
        if not tag_obj:
            tag_obj = Tag.objects.create(name=name, slug=tag_slug, is_active=True)
        StoryTag.objects.get_or_create(story=story, tag=tag_obj)


class AdminReviewQueueView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """Fetches stories currently in the editorial review queue or published."""
        status_param = request.query_params.get("status")
        if status_param and status_param.upper() == "ALL":
            queryset = Story.objects.all()
        elif status_param:
            queryset = Story.objects.filter(
                Q(status__iexact=status_param) | Q(chapters__status__iexact=status_param)
            )
        else:
            queryset = Story.objects.filter(
                Q(status__in=[StoryStatus.PENDING_REVIEW, "SUBMITTED"])
                | Q(chapters__status__iexact="PENDING_REVIEW")
            )

        queryset = (
            queryset.distinct()
            .select_related("writer", "category", "writer__user")
            .prefetch_related("story_tags__tag", "reviews", "reviews__reviewer", "chapters")
            .order_by("-created_at")
        )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AdminStorySerializer(page, many=True)
        response = paginator.get_paginated_response(serializer.data)

        # Include overall queue statistics
        stats = {
            "total_in_queue": Story.objects.filter(
                Q(status__in=[StoryStatus.PENDING_REVIEW, "SUBMITTED"])
                | Q(chapters__status__iexact="PENDING_REVIEW")
            ).distinct().count(),
            "total_rejected": Story.objects.filter(status__iexact="REJECTED").count(),
            "total_published": Story.objects.filter(status__iexact="PUBLISHED").count(),
            "total_submissions": Story.objects.count(),
        }
        if isinstance(response.data, dict):
            if "data" in response.data and isinstance(response.data["data"], dict):
                response.data["data"]["stats"] = stats
            else:
                response.data["stats"] = stats

        return response


class AdminApproveStoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        if story.status != StoryStatus.PENDING_REVIEW and story.status != StoryStatus.APPROVED:
            story.status = StoryStatus.PENDING_REVIEW
            story.save(update_fields=["status", "updated_at"])

        if story.status != StoryStatus.APPROVED:
            story = StoryService.approve_story(story, request.user)

        published_story = StoryService.publish_story(story, request.user)
        cache.delete("homepage")

        return success_response(
            data=AdminStorySerializer(published_story).data,
            message="Story approved and published live successfully."
        )


class AdminRejectStoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        feedback = (
            request.data.get("rejection_feedback")
            or request.data.get("feedback")
            or request.data.get("reason")
            or ""
        ).strip()
        if not feedback:
            raise ServiceValidationError("Rejection feedback is mandatory when rejecting a story.")

        internal_notes = request.data.get("internal_notes", "").strip()

        rejected_story = StoryService.reject_story(
            story,
            request.user,
            feedback=feedback,
            internal_notes=internal_notes
        )

        cache.delete("homepage")
        return success_response(
            data=AdminStorySerializer(rejected_story).data,
            message="Story rejected with feedback sent to writer."
        )


class AdminPublishStoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        if story.status != StoryStatus.APPROVED:
            story.status = StoryStatus.APPROVED
            story.save(update_fields=["status", "updated_at"])
        published_story = StoryService.publish_story(story, request.user)
        cache.delete("homepage")
        return success_response(
            data=AdminStorySerializer(published_story).data,
            message="Story published successfully."
        )


class AdminArchiveStoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        story.status = StoryStatus.ARCHIVED
        story.archived_at = timezone.now()
        story.save(update_fields=["status", "archived_at", "updated_at"])
        return success_response(
            data=AdminStorySerializer(story).data,
            message="Story archived successfully."
        )


class AdminFeatureStoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        is_featured = request.data.get("is_featured", True)
        story.is_featured = is_featured
        story.save(update_fields=["is_featured", "updated_at"])
        return success_response(
            data=AdminStorySerializer(story).data,
            message=f"Story {'featured' if is_featured else 'unfeatured'} successfully."
        )


class AdminStoryRevisionsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        revisions = StoryRevision.objects.filter(story=story).order_by("-version_number")
        serializer = StoryRevisionSerializer(revisions, many=True)
        return success_response(data=serializer.data)


class AdminStoryReviewsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        reviews = StoryReview.objects.filter(story=story).order_by("-reviewed_at")
        serializer = StoryReviewSerializer(reviews, many=True)
        return success_response(data=serializer.data)


def _get_story_for_writer_or_admin(pk, user):
    """Retrieves a story for either an admin (any story) or writer (own story)."""
    if getattr(user, "role", "") == UserRole.ADMIN or getattr(user, "is_staff", False):
        return Story.objects.filter(slug=pk).first() or Story.objects.filter(id=pk).first() or get_object_or_404(Story, pk=pk)
    writer = _get_writer_profile(user)
    return Story.objects.filter(slug=pk, writer=writer).first() or Story.objects.filter(id=pk, writer=writer).first() or get_object_or_404(Story, pk=pk, writer=writer)


class WriterChapterListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrWriter]

    def get(self, request, pk):
        story = _get_story_for_writer_or_admin(pk, request.user)
        chapters = story.chapters.all()
        serializer = StoryChapterSerializer(chapters, many=True)
        return success_response(data=serializer.data)

    def post(self, request, pk):
        story = _get_story_for_writer_or_admin(pk, request.user)
        serializer = StoryChapterCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chapter = ChapterService.create_chapter(story, serializer.validated_data, request.user)
        return created_response(
            data=StoryChapterSerializer(chapter).data,
            message="Chapter created successfully."
        )


class WriterChapterDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrWriter]

    def get(self, request, pk, chapter_pk):
        story = _get_story_for_writer_or_admin(pk, request.user)
        chapter = get_object_or_404(StoryChapter, id=chapter_pk, story=story)
        return success_response(data=StoryChapterSerializer(chapter).data)

    def patch(self, request, pk, chapter_pk):
        story = _get_story_for_writer_or_admin(pk, request.user)
        chapter = get_object_or_404(StoryChapter, id=chapter_pk, story=story)
        serializer = StoryChapterCreateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = ChapterService.update_chapter(chapter, serializer.validated_data, request.user)
        return success_response(
            data=StoryChapterSerializer(updated).data,
            message="Chapter updated successfully."
        )

    def delete(self, request, pk, chapter_pk):
        story = _get_story_for_writer_or_admin(pk, request.user)
        chapter = get_object_or_404(StoryChapter, id=chapter_pk, story=story)
        ChapterService.delete_chapter(chapter, request.user)
        return no_content_response()


class WriterChapterReorderView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrWriter]

    def post(self, request, pk):
        story = _get_story_for_writer_or_admin(pk, request.user)
        ordered_ids = request.data.get("ordered_ids", [])
        if not isinstance(ordered_ids, list) or not ordered_ids:
            raise ServiceValidationError("ordered_ids must be a non-empty list of chapter IDs.")
        chapters = ChapterService.reorder_chapters(story, ordered_ids, request.user)
        return success_response(
            data=StoryChapterSerializer(chapters, many=True).data,
            message="Chapters reordered successfully."
        )


class WriterChapterSubmitView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrWriter]

    def post(self, request, pk, chapter_pk):
        story = _get_story_for_writer_or_admin(pk, request.user)
        chapter = get_object_or_404(StoryChapter, id=chapter_pk, story=story)
        submitted_chapter = ChapterService.submit_chapter(chapter, request.user)
        return success_response(
            data=StoryChapterSerializer(submitted_chapter).data,
            message=f"Chapter {submitted_chapter.order} submitted for editorial review."
        )


class AdminApproveChapterView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk, chapter_pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        chapter = get_object_or_404(StoryChapter, id=chapter_pk, story=story)
        approved_chapter = ChapterService.approve_chapter(chapter, request.user)
        published_chapter = ChapterService.publish_chapter(approved_chapter, request.user)
        return success_response(
            data=StoryChapterSerializer(published_chapter).data,
            message=f"Chapter {published_chapter.order} approved and published live."
        )


class AdminPublishChapterView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk, chapter_pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        chapter = get_object_or_404(StoryChapter, id=chapter_pk, story=story)
        published_chapter = ChapterService.publish_chapter(chapter, request.user)
        return success_response(
            data=StoryChapterSerializer(published_chapter).data,
            message=f"Chapter {published_chapter.order} published live."
        )


class AdminRejectChapterView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk, chapter_pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        chapter = get_object_or_404(StoryChapter, id=chapter_pk, story=story)
        feedback = (
            request.data.get("rejection_feedback")
            or request.data.get("feedback")
            or request.data.get("reason")
            or ""
        ).strip()
        if not feedback:
            raise ServiceValidationError("Rejection feedback is mandatory when rejecting a chapter.")

        rejected_chapter = ChapterService.reject_chapter(chapter, request.user, feedback=feedback)
        return success_response(
            data=StoryChapterSerializer(rejected_chapter).data,
            message=f"Chapter {rejected_chapter.order} rejected with feedback."
        )


class PublicStoryChaptersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug, order=None):
        story = get_object_or_404(Story, slug=slug, status=StoryStatus.PUBLISHED)
        # Ensure chapters have consecutive 1-indexed order
        ChapterService.normalize_chapter_orders(story)

        # For a published story, retrieve all active non-rejected chapters ordered sequentially
        qs = story.chapters.exclude(status=StoryStatus.REJECTED).order_by("order", "created_at")

        if order is not None:
            chapter = qs.filter(order=order).first()
            if not chapter:
                chapters_list = list(qs)
                if 1 <= order <= len(chapters_list):
                    chapter = chapters_list[order - 1]
            if not chapter:
                raise Http404("Chapter not found.")
            return success_response(data=StoryChapterSerializer(chapter).data)
        return success_response(data=StoryChapterSerializer(qs, many=True).data)


class WriterActiveSeriesView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrWriter]

    def get(self, request):
        """Returns the writer's currently active ongoing multi-chapter series with its chapters."""
        writer = _get_writer_profile(request.user)
        story = StoryService.get_active_series_for_writer(writer)
        if not story:
            return success_response(data=None, message="No active ongoing series found.")
        context = {"request": request, **get_engagement_context(request)}
        serializer = StoryDetailSerializer(story, context=context)
        return success_response(data=serializer.data)


class WriterSeriesListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrWriter]

    def get(self, request):
        """Returns all multi-chapter series authored by this writer."""
        writer = _get_writer_profile(request.user)
        series_qs = StoryService.get_all_series_for_writer(writer)
        context = {"request": request, **get_engagement_context(request)}
        serializer = StoryListSerializer(series_qs, many=True, context=context)
        return success_response(data=serializer.data)


class WriterSeriesStatusToggleView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrWriter]

    def post(self, request, pk):
        """Toggles or sets the ongoing/completed status of a multi-chapter series."""
        story = _get_story_for_writer_or_admin(pk, request.user)
        new_status = request.data.get("status") or request.data.get("series_status")
        updated = StoryService.toggle_series_status(story, request.user, new_status=new_status)
        context = {"request": request, **get_engagement_context(request)}
        return success_response(
            data=StoryDetailSerializer(updated, context=context).data,
            message=f"Series marked as {updated.series_status.capitalize()}."
        )


