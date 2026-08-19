"""
apps/stories/services.py — StoryService
Central service layer for story CRUD, draft workflows, reviews, approvals, rejections, revisions, and status transitions per §22 and Phase 2 spec.
"""
import math
import re
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction

from common.constants import StoryStatus, ModerationStatus, ReviewDecision, NotificationType
from common.exceptions import (
    ServiceValidationError,
    PermissionDeniedError,
    InvalidStateTransitionError,
    ResourceNotFoundError,
)
from apps.stories.models import Story, StoryTag, StoryRevision, StoryReview
from apps.categories.models import Category, Tag
from apps.moderation.services import ModerationService
from apps.notifications.models import Notification


class StoryService:

    @staticmethod
    def strip_html(text: str) -> str:
        """Strips HTML tags to generate plain text content."""
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", clean).strip()

    @classmethod
    def calculate_word_count(cls, text: str) -> int:
        plain = cls.strip_html(text)
        return len(plain.split()) if plain else 0

    @classmethod
    def calculate_reading_time(cls, text: str) -> int:
        """Calculates reading time in minutes assuming 200 words per minute."""
        words = cls.calculate_word_count(text)
        return max(1, math.ceil(words / 200)) if words > 0 else 0

    @classmethod
    def generate_unique_slug(cls, title: str, instance_id=None) -> str:
        base_slug = slugify(title) or "story"
        slug = base_slug
        counter = 1
        qs = Story.objects.filter(slug=slug)
        if instance_id:
            qs = qs.exclude(id=instance_id)

        while qs.exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
            qs = Story.objects.filter(slug=slug)
            if instance_id:
                qs = qs.exclude(id=instance_id)
        return slug

    @classmethod
    @transaction.atomic
    def create_story(cls, writer, data: dict) -> Story:
        """
        Creates a new Story in DRAFT status and initializes revision v1.
        """
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
        category_id = data.get("category_id")

        if not title:
            raise ServiceValidationError("Title is required.")
        if not content or len(content) < 100:
            raise ServiceValidationError("Content is required and must be at least 100 characters.")

        # Moderation check
        ModerationService.check_content(title)
        ModerationService.check_content(content)
        sanitized_content = ModerationService.sanitize_text(content)

        category = Category.objects.get(id=category_id)
        slug = cls.generate_unique_slug(title)
        plain_text = cls.strip_html(sanitized_content)
        word_cnt = cls.calculate_word_count(sanitized_content)
        user_rt = data.get("reading_time") or data.get("estimated_reading_time")
        read_time = int(user_rt) if user_rt and int(user_rt) > 0 else cls.calculate_reading_time(sanitized_content)

        story = Story.objects.create(
            writer=writer,
            created_by=writer.user,
            title=title,
            slug=slug,
            subtitle=data.get("subtitle", "").strip() or None,
            content=sanitized_content,
            plain_text_content=plain_text,
            category=category,
            seo_title=data.get("seo_title", "")[:70],
            seo_description=data.get("seo_description", "")[:160],
            allow_comments=data.get("allow_comments", True),
            estimated_reading_time=read_time,
            word_count=word_cnt,
            status=StoryStatus.DRAFT,
            moderation_status=ModerationStatus.PASSED,
        )

        # Attach tags
        tag_ids = data.get("tag_ids", [])
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            for tag in tags:
                StoryTag.objects.create(story=story, tag=tag)

        # Save initial revision
        StoryRevision.objects.create(
            story=story,
            version_number=1,
            title=story.title,
            subtitle=story.subtitle,
            content=story.content,
            category=story.category,
            seo_title=story.seo_title,
            seo_description=story.seo_description,
            edited_by=writer.user,
            change_summary="Initial draft created",
        )

        return story

    @classmethod
    @transaction.atomic
    def update_story(cls, story: Story, data: dict, user) -> Story:
        """
        Updates an existing story draft and logs a new revision version.
        """
        if story.status not in [StoryStatus.DRAFT, StoryStatus.REJECTED]:
            raise InvalidStateTransitionError("Only DRAFT or REJECTED stories can be edited.")

        if "title" in data:
            title = data["title"].strip()
            if not title:
                raise ServiceValidationError("Title cannot be empty.")
            ModerationService.check_content(title)
            story.title = title
            story.slug = cls.generate_unique_slug(title, instance_id=story.id)

        if "content" in data:
            content = data["content"].strip()
            if len(content) < 100:
                raise ServiceValidationError("Content must be at least 100 characters long.")
            ModerationService.check_content(content)
            sanitized = ModerationService.sanitize_text(content)
            story.content = sanitized
            story.plain_text_content = cls.strip_html(sanitized)
            story.word_count = cls.calculate_word_count(sanitized)
            user_rt = data.get("reading_time") or data.get("estimated_reading_time")
            story.estimated_reading_time = int(user_rt) if user_rt and int(user_rt) > 0 else cls.calculate_reading_time(sanitized)

        if "subtitle" in data:
            story.subtitle = data["subtitle"].strip() or None

        if "category_id" in data:
            story.category = Category.objects.get(id=data["category_id"])

        if "seo_title" in data:
            story.seo_title = data["seo_title"][:70]

        if "seo_description" in data:
            story.seo_description = data["seo_description"][:160]

        if "allow_comments" in data:
            story.allow_comments = data["allow_comments"]

        story.save()

        # Update tags if passed
        if "tag_ids" in data:
            story.story_tags.all().delete()
            tags = Tag.objects.filter(id__in=data["tag_ids"])
            for tag in tags:
                StoryTag.objects.create(story=story, tag=tag)

        # Create next revision snapshot
        latest_rev = story.revisions.first()
        next_ver = (latest_rev.version_number + 1) if latest_rev else 1

        StoryRevision.objects.create(
            story=story,
            version_number=next_ver,
            title=story.title,
            subtitle=story.subtitle,
            content=story.content,
            category=story.category,
            seo_title=story.seo_title,
            seo_description=story.seo_description,
            edited_by=user,
            change_summary=data.get("change_summary", f"Updated version {next_ver}"),
        )

        return story

    @classmethod
    def delete_story(cls, story: Story, user):
        """Soft/hard delete — only allowed for DRAFT stories."""
        if story.status != StoryStatus.DRAFT:
            raise InvalidStateTransitionError("Only DRAFT stories can be deleted.")
        story.delete()

    @classmethod
    @transaction.atomic
    def duplicate_story(cls, story: Story, writer) -> Story:
        """Clones an existing story into a new DRAFT."""
        new_title = f"{story.title} (Copy)"
        new_slug = cls.generate_unique_slug(new_title)

        new_story = Story.objects.create(
            writer=writer,
            created_by=writer.user,
            title=new_title,
            slug=new_slug,
            subtitle=story.subtitle,
            content=story.content,
            plain_text_content=story.plain_text_content,
            category=story.category,
            seo_title=story.seo_title,
            seo_description=story.seo_description,
            allow_comments=story.allow_comments,
            estimated_reading_time=story.estimated_reading_time,
            word_count=story.word_count,
            status=StoryStatus.DRAFT,
            moderation_status=story.moderation_status,
        )

        for st in story.story_tags.all():
            StoryTag.objects.create(story=new_story, tag=st.tag)

        StoryRevision.objects.create(
            story=new_story,
            version_number=1,
            title=new_story.title,
            subtitle=new_story.subtitle,
            content=new_story.content,
            category=new_story.category,
            seo_title=new_story.seo_title,
            seo_description=new_story.seo_description,
            edited_by=writer.user,
            change_summary="Duplicated from original story",
        )

        return new_story

    @classmethod
    @transaction.atomic
    def submit_story(cls, story: Story, writer) -> Story:
        """
        Transitions story from DRAFT or REJECTED to PENDING_REVIEW per §22.2.
        """
        if story.writer_id != writer.id:
            raise PermissionDeniedError("You can only submit your own story.")

        if story.status not in [StoryStatus.DRAFT, StoryStatus.REJECTED]:
            raise InvalidStateTransitionError(
                f"Cannot submit story with status '{story.status}'. Must be DRAFT or REJECTED."
            )

        if not story.title or not story.content or len(story.content) < 100:
            raise ServiceValidationError("Story title and content (min 100 chars) are required for submission.")

        if not story.category or not story.category.is_active:
            raise ServiceValidationError("An active category must be selected before submitting.")

        story.status = StoryStatus.PENDING_REVIEW
        story.submitted_at = timezone.now()
        story.rejection_feedback = ""  # Clear old feedback
        story.save(update_fields=["status", "submitted_at", "rejection_feedback", "updated_at"])

        # Queue async email task
        from apps.notifications.tasks import send_story_submission_email
        send_story_submission_email.delay(str(story.id))

        return story

    @classmethod
    @transaction.atomic
    def approve_story(cls, story: Story, admin) -> Story:
        """
        Approves a PENDING_REVIEW story per §22.3.
        """
        if story.status != StoryStatus.PENDING_REVIEW:
            raise InvalidStateTransitionError(f"Cannot approve story in state '{story.status}'.")

        now = timezone.now()
        story.status = StoryStatus.APPROVED
        story.reviewed_by = admin
        story.reviewed_at = now
        story.approved_at = now
        story.save(update_fields=["status", "reviewed_by", "reviewed_at", "approved_at", "updated_at"])

        # Create review log
        StoryReview.objects.create(
            story=story,
            reviewer=admin,
            decision=ReviewDecision.APPROVED,
            feedback="Story approved for publication.",
            reviewed_at=now,
        )

        # Notify writer
        Notification.objects.create(
            user=story.writer.user,
            notification_type=NotificationType.STORY_APPROVED,
            title="Story Approved!",
            message=f"Your story '{story.title}' has been approved by our editorial team.",
            target_url=f"/writer/stories/{story.id}",
        )

        # Queue async approval email
        from apps.notifications.tasks import send_story_approval_email
        send_story_approval_email.delay(str(story.id))

        return story

    @classmethod
    @transaction.atomic
    def reject_story(cls, story: Story, admin, feedback: str, internal_notes: str = "") -> Story:
        """
        Rejects a PENDING_REVIEW story requiring feedback per §22.4.
        """
        if story.status != StoryStatus.PENDING_REVIEW:
            raise InvalidStateTransitionError(f"Cannot reject story in state '{story.status}'.")

        feedback_text = feedback.strip() if feedback else ""
        if not feedback_text:
            raise ServiceValidationError("Rejection feedback is mandatory when rejecting a story.")

        now = timezone.now()
        story.status = StoryStatus.REJECTED
        story.reviewed_by = admin
        story.reviewed_at = now
        story.rejection_feedback = feedback_text
        story.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_feedback", "updated_at"])

        # Create review log
        StoryReview.objects.create(
            story=story,
            reviewer=admin,
            decision=ReviewDecision.REJECTED,
            feedback=feedback_text,
            internal_notes=internal_notes,
            reviewed_at=now,
        )

        # Notify writer
        Notification.objects.create(
            user=story.writer.user,
            notification_type=NotificationType.STORY_REJECTED,
            title="Story Review Feedback",
            message=f"Your story '{story.title}' needs revisions: {feedback_text[:100]}...",
            target_url=f"/writer/stories/{story.id}",
        )

        # Queue async rejection email
        from apps.notifications.tasks import send_story_rejection_email
        send_story_rejection_email.delay(str(story.id))

        return story

    @classmethod
    @transaction.atomic
    def publish_story(cls, story: Story, admin) -> Story:
        """
        Publishes an APPROVED story per §22.5.
        """
        if story.status != StoryStatus.APPROVED:
            raise InvalidStateTransitionError("Only APPROVED stories can be published.")

        now = timezone.now()
        story.status = StoryStatus.PUBLISHED
        story.published_at = now
        story.save(update_fields=["status", "published_at", "updated_at"])

        # Update writer stats
        writer = story.writer
        writer.total_published_stories = Story.objects.filter(
            writer=writer, status=StoryStatus.PUBLISHED
        ).count()
        writer.save(update_fields=["total_published_stories"])

        # Notify writer
        Notification.objects.create(
            user=writer.user,
            notification_type=NotificationType.STORY_PUBLISHED,
            title="Story Published!",
            message=f"Your story '{story.title}' is now live on Tossatale!",
            target_url=f"/stories/{story.slug}",
        )

        return story

    @classmethod
    def schedule_story(cls, story: Story, admin, publish_dt) -> Story:
        """Schedules an approved story for future publication."""
        if story.status != StoryStatus.APPROVED:
            raise InvalidStateTransitionError("Only APPROVED stories can be scheduled.")
        if publish_dt <= timezone.now():
            raise ServiceValidationError("Scheduled time must be in the future.")

        story.status = StoryStatus.SCHEDULED
        story.scheduled_publish_at = publish_dt
        story.save(update_fields=["status", "scheduled_publish_at", "updated_at"])
        return story

    @classmethod
    def archive_story(cls, story: Story, admin) -> Story:
        """Archives a published or approved story per §22.6."""
        if story.status not in [StoryStatus.PUBLISHED, StoryStatus.APPROVED]:
            raise InvalidStateTransitionError("Only PUBLISHED or APPROVED stories can be archived.")

        story.status = StoryStatus.ARCHIVED
        story.archived_at = timezone.now()
        story.save(update_fields=["status", "archived_at", "updated_at"])
        return story

    @classmethod
    def feature_story(cls, story: Story, admin, is_featured: bool) -> Story:
        """Toggles is_featured status on a story."""
        story.is_featured = is_featured
        story.save(update_fields=["is_featured", "updated_at"])
        return story

    @classmethod
    @transaction.atomic
    def restore_revision(cls, story: Story, revision_id: str, user) -> Story:
        """Restores content and title from a specific StoryRevision."""
        if story.status not in [StoryStatus.DRAFT, StoryStatus.REJECTED]:
            raise InvalidStateTransitionError("Revisions can only be restored on DRAFT or REJECTED stories.")

        try:
            rev = StoryRevision.objects.get(id=revision_id, story=story)
        except StoryRevision.DoesNotExist:
            raise ResourceNotFoundError("Story revision not found.")

        story.title = rev.title
        story.subtitle = rev.subtitle
        story.content = rev.content
        story.plain_text_content = cls.strip_html(rev.content)
        story.seo_title = rev.seo_title
        story.seo_description = rev.seo_description
        if rev.category:
            story.category = rev.category
        story.word_count = cls.calculate_word_count(rev.content)
        story.estimated_reading_time = cls.calculate_reading_time(rev.content)
        story.save()

        # Log new revision for restore action
        latest_rev = story.revisions.first()
        next_ver = (latest_rev.version_number + 1) if latest_rev else 1
        StoryRevision.objects.create(
            story=story,
            version_number=next_ver,
            title=story.title,
            subtitle=story.subtitle,
            content=story.content,
            category=story.category,
            seo_title=story.seo_title,
            seo_description=story.seo_description,
            edited_by=user,
            change_summary=f"Restored from version {rev.version_number}",
        )

        return story
