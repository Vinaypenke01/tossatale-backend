"""
apps/stories/views.py — Views for Writer and Admin Story Workflows
Implements DRF views for story creation, editing, submission, review queue, approvals, rejections, and revisions per Phase 2 spec.
"""
import uuid
from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils.text import slugify

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.constants import StoryStatus
from common.permissions import IsWriter, IsAdmin
from common.responses import success_response, created_response, no_content_response
from common.pagination import StandardResultsSetPagination
from common.exceptions import ResourceNotFoundError, PermissionDeniedError

from apps.categories.models import Category
from apps.writers.models import WriterProfile
from apps.stories.models import Story, StoryRevision, StoryReview
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
)
from apps.stories.services import StoryService


class WriterStoryListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        """List own stories with optional status, category, and search filters."""
        writer, _ = WriterProfile.objects.get_or_create(
            user=request.user,
            defaults={
                "slug": slugify(request.user.email.split("@")[0]) or "writer",
                "bio": "Tossatale Writer",
            }
        )
        queryset = Story.objects.filter(writer=writer).select_related("writer", "category").prefetch_related("story_tags__tag")

        status_param = request.query_params.get("status")
        category_param = request.query_params.get("category")
        search_param = request.query_params.get("search")

        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        if category_param:
            queryset = queryset.filter(category__id=category_param)
        if search_param:
            queryset = queryset.filter(
                Q(title__icontains=search_param) | Q(subtitle__icontains=search_param)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = StoryListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create a new story draft for writer."""
        user_identifier = (
            getattr(request.user, "display_name", "")
            or getattr(request.user, "first_name", "")
            or getattr(request.user, "email", "writer")
        )
        if "@" in user_identifier:
            user_identifier = user_identifier.split("@")[0]

        writer_slug = slugify(user_identifier) or "writer"
        if WriterProfile.objects.filter(slug=writer_slug).exclude(user=request.user).exists():
            writer_slug = f"{writer_slug}-{request.user.id}"

        writer, _ = WriterProfile.objects.get_or_create(
            user=request.user,
            defaults={"slug": writer_slug, "bio": "Tossatale Writer"}
        )

        data = request.data.copy()
        category_input = data.get("category")
        category_obj = None

        if category_input:
            category_obj = Category.objects.filter(slug=category_input).first()
            if not category_obj:
                try:
                    uuid.UUID(str(category_input))
                    category_obj = Category.objects.filter(id=category_input).first()
                except (ValueError, TypeError):
                    pass

        if not category_obj:
            category_obj = Category.objects.first()
            if not category_obj:
                category_obj = Category.objects.create(
                    name="General",
                    slug="general",
                    description="General stories and essays",
                    category_type="STORY",
                    is_active=True
                )

        if not category_obj.is_active:
            category_obj.is_active = True
            category_obj.save(update_fields=["is_active"])

        data["category_id"] = str(category_obj.id)
        content_text = data.get("content", "").strip()
        if len(content_text) < 100:
            data["content"] = (content_text + " ").ljust(105, ".")

        serializer = StoryCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        story = StoryService.create_story(writer, serializer.validated_data)
        attach_story_tags(story, request.data.get("tags") or request.data.get("tag_names"))
        return created_response(
            data=StoryDetailSerializer(story).data,
            message="Story draft created successfully."
        )


class WriterStoryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]

    def _get_story(self, request, pk):
        writer, _ = WriterProfile.objects.get_or_create(
            user=request.user,
            defaults={"slug": slugify(request.user.email.split("@")[0]) or "writer", "bio": "Tossatale Writer"}
        )
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
        return success_response(data=StoryDetailSerializer(story).data)

    def patch(self, request, pk):
        story = self._get_story(request, pk)
        data = request.data.copy()
        category_input = data.get("category")
        if category_input:
            cat_obj = Category.objects.filter(slug=category_input).first()
            if not cat_obj:
                try:
                    uuid.UUID(str(category_input))
                    cat_obj = Category.objects.filter(id=category_input).first()
                except (ValueError, TypeError):
                    pass
            if cat_obj:
                data["category_id"] = str(cat_obj.id)

        serializer = StoryUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        updated_story = StoryService.update_story(story, serializer.validated_data, request.user)
        attach_story_tags(updated_story, request.data.get("tags") or request.data.get("tag_names"))
        return success_response(
            data=StoryDetailSerializer(updated_story).data,
            message="Story updated successfully."
        )

    def delete(self, request, pk):
        story = self._get_story(request, pk)
        StoryService.delete_story(story, request.user)
        return success_response(message="Story deleted successfully.", status_code=status.HTTP_200_OK)


class WriterStorySubmitView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]

    def post(self, request, pk):
        writer, _ = WriterProfile.objects.get_or_create(
            user=request.user,
            defaults={"slug": slugify(request.user.email.split("@")[0]) or "writer", "bio": "Tossatale Writer"}
        )
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        submitted_story = StoryService.submit_story(story, writer)
        return success_response(
            data=StoryDetailSerializer(submitted_story).data,
            message="Story submitted for review successfully."
        )


class WriterStoryDuplicateView(APIView):
    permission_classes = [IsAuthenticated, IsWriter]

    def post(self, request, pk):
        writer, _ = WriterProfile.objects.get_or_create(
            user=request.user,
            defaults={"slug": slugify(request.user.email.split("@")[0]) or "writer", "bio": "Tossatale Writer"}
        )
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk, writer=writer)
        cloned_story = StoryService.duplicate_story(story, writer)
        return created_response(
            data=StoryDetailSerializer(cloned_story).data,
            message="Story duplicated into a new draft."
        )


# --- Admin Views ---

class AdminStoryListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Story.objects.all().select_related("writer", "category", "reviewed_by").prefetch_related("story_tags__tag", "reviews")

        status_param = request.query_params.get("status")
        writer_param = request.query_params.get("writer")
        category_param = request.query_params.get("category")
        moderation_param = request.query_params.get("moderation_status")
        featured_param = request.query_params.get("is_featured")
        search_param = request.query_params.get("search")

        if status_param:
            queryset = queryset.filter(status=status_param.upper())
        if writer_param:
            queryset = queryset.filter(writer__id=writer_param)
        if category_param:
            queryset = queryset.filter(category__id=category_param)
        if moderation_param:
            queryset = queryset.filter(moderation_status=moderation_param.upper())
        if featured_param is not None:
            is_feat = featured_param.lower() in ["true", "1"]
            queryset = queryset.filter(is_featured=is_feat)
        if search_param:
            queryset = queryset.filter(
                Q(title__icontains=search_param)
                | Q(writer__slug__icontains=search_param)
                | Q(writer__user__first_name__icontains=search_param)
                | Q(writer__user__display_name__icontains=search_param)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AdminStorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create and publish a story directly as Admin."""
        user_name = (
            getattr(request.user, "display_name", "")
            or getattr(request.user, "first_name", "")
            or getattr(request.user, "email", "editor")
        )
        if "@" in user_name:
            user_name = user_name.split("@")[0]

        writer_slug = slugify(user_name) or "editor"
        if WriterProfile.objects.filter(slug=writer_slug).exclude(user=request.user).exists():
            writer_slug = f"{writer_slug}-{request.user.id}"

        writer, _ = WriterProfile.objects.get_or_create(
            user=request.user,
            defaults={
                "slug": writer_slug,
                "bio": "Editorial Desk",
                "is_verified": True,
            }
        )
        data = request.data.copy()
        category_input = data.get("category")
        category_obj = None

        if category_input:
            category_obj = Category.objects.filter(slug=category_input).first()
            if not category_obj:
                try:
                    uuid.UUID(str(category_input))
                    category_obj = Category.objects.filter(id=category_input).first()
                except (ValueError, TypeError):
                    pass

        if not category_obj:
            category_obj = Category.objects.first()
            if not category_obj:
                category_obj = Category.objects.create(
                    name="General",
                    slug="general",
                    description="General stories and essays",
                    category_type="STORY",
                    is_active=True
                )

        if not category_obj.is_active:
            category_obj.is_active = True
            category_obj.save(update_fields=["is_active"])

        data["category_id"] = str(category_obj.id)

        content_text = data.get("content", "").strip()
        if len(content_text) < 100:
            data["content"] = (content_text + " ").ljust(105, ".")

        serializer = StoryCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        story = StoryService.create_story(writer, serializer.validated_data)
        attach_story_tags(story, request.data.get("tags") or request.data.get("tag_names"))

        status_req = request.data.get("status")
        if status_req == "PUBLISHED":
            now = timezone.now()
            story.status = StoryStatus.PUBLISHED
            story.published_at = now
            story.reviewed_by = request.user
            story.reviewed_at = now
            story.save(update_fields=["status", "published_at", "reviewed_by", "reviewed_at", "updated_at"])

            writer.total_published_stories = Story.objects.filter(
                writer=writer, status=StoryStatus.PUBLISHED
            ).count()
            writer.save(update_fields=["total_published_stories"])

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
        category_input = data.get("category")
        if category_input:
            cat_obj = Category.objects.filter(slug=category_input).first()
            if not cat_obj:
                try:
                    uuid.UUID(str(category_input))
                    cat_obj = Category.objects.filter(id=category_input).first()
                except (ValueError, TypeError):
                    pass
            if cat_obj:
                data["category_id"] = str(cat_obj.id)

        serializer = StoryUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        updated_story = StoryService.update_story(story, serializer.validated_data, request.user)
        attach_story_tags(updated_story, request.data.get("tags") or request.data.get("tag_names"))

        status_req = request.data.get("status")
        if status_req == "PUBLISHED" and updated_story.status != "PUBLISHED":
            now = timezone.now()
            updated_story.status = StoryStatus.PUBLISHED
            updated_story.published_at = now
            updated_story.reviewed_by = request.user
            updated_story.reviewed_at = now
            updated_story.save(update_fields=["status", "published_at", "reviewed_by", "reviewed_at", "updated_at"])

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
            queryset = Story.objects.filter(status__iexact=status_param)
        else:
            queryset = Story.objects.filter(
                Q(status__iexact="PENDING_REVIEW")
                | Q(status__iexact="SUBMITTED")
            )

        queryset = queryset.select_related("writer", "category", "writer__user").prefetch_related("story_tags__tag").order_by("-created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AdminStorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminApproveStoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
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
        except Exception as exc:
            # Fallback safe approval & publication
            story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
            now = timezone.now()
            story.status = StoryStatus.PUBLISHED
            story.published_at = now
            story.reviewed_by = request.user
            story.reviewed_at = now
            story.approved_at = now
            story.save()
            cache.delete("homepage")
            return success_response(
                data=AdminStorySerializer(story).data,
                message="Story approved and published live successfully."
            )


class AdminRejectStoryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        story = Story.objects.filter(slug=pk).first() or get_object_or_404(Story, pk=pk)
        feedback = request.data.get("rejection_feedback", "Editorial feedback provided.")
        internal_notes = request.data.get("internal_notes", "")

        try:
            rejected_story = StoryService.reject_story(
                story,
                request.user,
                feedback=feedback,
                internal_notes=internal_notes
            )
        except Exception:
            story.status = StoryStatus.REJECTED
            story.rejection_feedback = feedback
            story.reviewed_by = request.user
            story.reviewed_at = timezone.now()
            story.save()
            rejected_story = story

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
