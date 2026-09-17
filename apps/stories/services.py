"""
apps/stories/services.py — StoryService
Central service layer for story CRUD, draft workflows, reviews, approvals, rejections, revisions, and status transitions per §22 and Phase 2 spec.
"""
import math
import re
from django.utils import timezone
from django.utils.text import slugify
from django.db import models, transaction

from common.constants import StoryStatus, ModerationStatus, ReviewDecision, NotificationType, SeriesStatusType
from common.exceptions import (
    ServiceValidationError,
    PermissionDeniedError,
    InvalidStateTransitionError,
    ResourceNotFoundError,
)
from apps.stories.models import Story, StoryTag, StoryRevision, StoryReview, StoryChapter
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
        base_slug = str(slugify(title) or "story")
        qs = Story.objects.filter(slug__startswith=base_slug)
        if instance_id:
            qs = qs.exclude(id=instance_id)
        existing = set(qs.values_list("slug", flat=True))
        if base_slug not in existing:
            return base_slug
        counter = 1
        while f"{base_slug}-{counter}" in existing:
            counter += 1
        return f"{base_slug}-{counter}"

    @classmethod
    def get_active_series_for_writer(cls, writer, exclude_story_id=None):
        """
        Returns the writer's currently active ongoing multi-chapter story, if one exists.
        """
        qs = Story.objects.filter(
            writer=writer,
            is_multi_chapter=True,
            series_status=SeriesStatusType.ONGOING,
        ).exclude(status=StoryStatus.ARCHIVED)
        if exclude_story_id:
            qs = qs.exclude(id=exclude_story_id)
        return qs.order_by("-created_at").first()

    @classmethod
    def get_all_series_for_writer(cls, writer):
        """
        Returns all multi-chapter stories authored by the writer ordered by creation.
        """
        return Story.objects.filter(
            writer=writer,
            is_multi_chapter=True,
        ).exclude(status=StoryStatus.ARCHIVED).prefetch_related("chapters").order_by("-created_at")

    @classmethod
    def create_story(cls, writer, data: dict) -> Story:
        """
        Creates a new Story in DRAFT status and initializes revision v1.
        """
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
        category_id = data.get("category_id")
        is_multi = bool(data.get("is_multi_chapter", False))
        series_stat = data.get("series_status", SeriesStatusType.ONGOING)

        if is_multi and series_stat == SeriesStatusType.ONGOING:
            active_series = cls.get_active_series_for_writer(writer)
            if active_series:
                raise ServiceValidationError(
                    f"You already have an active series in progress: '{active_series.title}'. "
                    f"Please mark it as Completed before starting a new series."
                )

        if not title:
            raise ServiceValidationError("Title is required.")

        # Moderation check
        ModerationService.check_content(title)
        if content:
            ModerationService.check_content(content)
            sanitized_content = ModerationService.sanitize_text(content)
        else:
            sanitized_content = ""

        category = Category.objects.get(id=category_id) if category_id else Category.objects.filter(is_active=True).first()
        if not category:
            category = Category.objects.create(
                name="General",
                slug="general",
                description="General stories and essays",
                category_type="STORY",
                is_active=True
            )
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
            is_multi_chapter=is_multi,
            series_status=series_stat,
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
            cls._sync_tags_usage(tag_ids)

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

    @staticmethod
    def _sync_tags_usage(tag_ids=None):
        """Updates usage_count for affected tags."""
        if tag_ids:
            for tag in Tag.objects.filter(id__in=tag_ids):
                count = StoryTag.objects.filter(tag=tag).count()
                tag.usage_count = count
                tag.save(update_fields=["usage_count"])

    @classmethod
    def update_story(cls, story, data: dict, user) -> Story:
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
            if content:
                ModerationService.check_content(content)
                sanitized = ModerationService.sanitize_text(content)
            else:
                sanitized = ""
            story.content = sanitized
            story.plain_text_content = cls.strip_html(sanitized)
            story.word_count = cls.calculate_word_count(sanitized)
            user_rt = data.get("reading_time") or data.get("estimated_reading_time")
            story.estimated_reading_time = int(user_rt) if user_rt and int(user_rt) > 0 else cls.calculate_reading_time(sanitized)

        if "is_multi_chapter" in data:
            new_is_multi = bool(data["is_multi_chapter"])
            new_series_stat = data.get("series_status", story.series_status)
            if new_is_multi and new_series_stat == SeriesStatusType.ONGOING:
                active_series = cls.get_active_series_for_writer(story.writer, exclude_story_id=story.id)
                if active_series:
                    raise ServiceValidationError(
                        f"You already have an active series in progress: '{active_series.title}'. "
                        f"Please mark it as Completed before starting a new series."
                    )
            story.is_multi_chapter = new_is_multi

        if "series_status" in data:
            new_stat = data["series_status"]
            if new_stat == SeriesStatusType.ONGOING and story.series_status != SeriesStatusType.ONGOING:
                active_series = cls.get_active_series_for_writer(story.writer, exclude_story_id=story.id)
                if active_series:
                    raise ServiceValidationError(
                        f"You already have an active series in progress: '{active_series.title}'. "
                        f"Please complete your ongoing series before reopening this series."
                    )
            story.series_status = new_stat

        if "subtitle" in data:
            story.subtitle = data["subtitle"].strip() if data.get("subtitle") else ""

        if "category_id" in data:
            story.category = Category.objects.get(id=data["category_id"])

        if "seo_title" in data:
            story.seo_title = data["seo_title"][:70]

        if "seo_description" in data:
            story.seo_description = data["seo_description"][:160]

        story.save(update_fields=[
            "title", "slug", "subtitle", "content", "plain_text_content",
            "word_count", "estimated_reading_time", "is_multi_chapter", "category", "seo_title",
            "seo_description", "allow_comments", "updated_at"
        ])

        # Update tags if passed
        if "tag_ids" in data:
            old_tag_ids = list(story.story_tags.values_list("tag_id", flat=True))
            story.story_tags.all().delete()
            tags = Tag.objects.filter(id__in=data["tag_ids"])
            for tag in tags:
                StoryTag.objects.create(story=story, tag=tag)
            cls._sync_tags_usage(list(set(old_tag_ids + list(data["tag_ids"]))))

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
        tag_ids = list(story.story_tags.values_list("tag_id", flat=True))
        story.delete()
        cls._sync_tags_usage(tag_ids)

    @classmethod
    def duplicate_story(cls, story, writer) -> Story:
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
    def submit_story(cls, story, writer) -> Story:
        """
        Transitions story from DRAFT or REJECTED to PENDING_REVIEW per §22.2.
        Evaluates content moderation status.
        """
        if story.writer_id != writer.id:
            raise PermissionDeniedError("You can only submit your own story.")

        if story.status not in [StoryStatus.DRAFT, StoryStatus.REJECTED]:
            raise InvalidStateTransitionError(
                f"Cannot submit story with status '{story.status}'. Must be DRAFT or REJECTED."
            )

        if not story.title:
            raise ServiceValidationError("Story title is required for submission.")

        if story.is_multi_chapter:
            chapters = list(story.chapters.all())
            if not chapters:
                raise ServiceValidationError("Please write and save at least one chapter before submitting your series.")
            combined_chapter_content = " ".join([c.content for c in chapters if c.content])
            if len(combined_chapter_content.strip()) < 50:
                raise ServiceValidationError("At least one chapter must contain prose content before submitting for review.")
            eval_content = f"{story.subtitle or ''} {combined_chapter_content}"
        else:
            if not story.content or len(str(story.content or "")) < 100:
                raise ServiceValidationError("Story title and content (min 100 chars) are required for submission.")
            eval_content = str(story.content)

        if not story.category or not story.category.is_active:
            raise ServiceValidationError("An active category must be selected before submitting.")

        # Automated moderation evaluation
        mod_result = ModerationService.evaluate_moderation_status(str(story.title or ""), eval_content)
        if not mod_result["passed"]:
            story.moderation_status = ModerationStatus.BLOCKED
            story.save(update_fields=["moderation_status", "updated_at"])
            raise ServiceValidationError("Story blocked by content moderation: " + "; ".join(mod_result.get("flags", [])))

        story.moderation_status = mod_result["status"]
        story.status = StoryStatus.PENDING_REVIEW
        story.submitted_at = timezone.now()
        story.rejection_feedback = ""  # Clear old feedback
        story.save(update_fields=["status", "moderation_status", "submitted_at", "rejection_feedback", "updated_at"])

        # Synchronous/Safe notification email
        try:
            from apps.notifications.tasks import send_story_submission_email
            send_story_submission_email(str(story.id))
        except Exception:
            pass

        return story

    @classmethod
    def approve_story(cls, story, admin) -> Story:
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
            recipient=story.writer.user,
            notification_type=NotificationType.STORY_APPROVED,
            title="Story Approved!",
            message=f"Your story '{story.title}' has been approved by our editorial team.",
            action_url=f"/writer/stories/{story.id}",
        )

        # Synchronous/Safe approval email
        try:
            from apps.notifications.tasks import send_story_approval_email
            send_story_approval_email(str(story.id))
        except Exception:
            pass

        return story

    @classmethod
    def reject_story(cls, story, admin, feedback: str, internal_notes: str = "") -> Story:
        """
        Rejects a PENDING_REVIEW story requiring feedback per §22.4.
        """
        if story.status not in [StoryStatus.PENDING_REVIEW, "SUBMITTED", StoryStatus.APPROVED, StoryStatus.DRAFT, StoryStatus.REJECTED]:
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
            recipient=story.writer.user,
            notification_type=NotificationType.STORY_REJECTED,
            title="Changes Requested / Story Feedback",
            message=f"Editorial feedback for '{story.title}': {feedback_text}",
            action_url=f"/writer/stories/{story.id}",
        )

        # Synchronous/Safe rejection email
        try:
            from apps.notifications.tasks import send_story_rejection_email
            send_story_rejection_email(str(story.id))
        except Exception:
            pass

        return story

    @classmethod
    def publish_story(cls, story, admin) -> Story:
        """
        Publishes a story per §22.5.
        """
        now = timezone.now()
        Story.objects.filter(id=story.id).update(
            status=StoryStatus.PUBLISHED,
            published_at=now,
            reviewed_by=admin,
            reviewed_at=now,
            updated_at=now
        )
        story.refresh_from_db()

        # Update writer stats
        writer = story.writer
        if writer:
            writer.total_published_stories = Story.objects.filter(
                writer=writer, status=StoryStatus.PUBLISHED
            ).count()
            writer.save(update_fields=["total_published_stories"])

        # Notify writer
        if writer and getattr(writer, "user", None):
            Notification.objects.create(
                recipient=writer.user,
                notification_type=NotificationType.STORY_PUBLISHED,
                title="Story Published!",
                message=f"Your story '{story.title}' is now live on Tossatale!",
                action_url=f"/stories/{story.slug}",
            )

        return story

    @classmethod
    def schedule_story(cls, story, admin, publish_dt) -> Story:
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
    def archive_story(cls, story, admin) -> Story:
        """Archives a published or approved story per §22.6."""
        if story.status not in [StoryStatus.PUBLISHED, StoryStatus.APPROVED]:
            raise InvalidStateTransitionError("Only PUBLISHED or APPROVED stories can be archived.")

        story.status = StoryStatus.ARCHIVED
        story.archived_at = timezone.now()
        story.save(update_fields=["status", "archived_at", "updated_at"])
        return story

    @classmethod
    def feature_story(cls, story, admin, is_featured: bool) -> Story:
        """Toggles is_featured status on a story."""
        story.is_featured = is_featured
        story.save(update_fields=["is_featured", "updated_at"])
        return story

    @classmethod
    def restore_revision(cls, story, revision_id: str, user) -> Story:
        """Restores content and title from a specific StoryRevision."""
        if story.status not in [StoryStatus.DRAFT, StoryStatus.REJECTED]:
            raise InvalidStateTransitionError("Revisions can only be restored on DRAFT or REJECTED stories.")

        rev = StoryRevision.objects.filter(id=revision_id, story=story).first()
        if not rev:
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
        story.save(update_fields=[
            "title", "subtitle", "content", "plain_text_content",
            "seo_title", "seo_description", "category", "word_count",
            "estimated_reading_time", "updated_at"
        ])

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

    @classmethod
    def toggle_series_status(cls, story: Story, user, new_status: str | None = None) -> Story:
        """Toggles or sets the series status (ONGOING <-> COMPLETED)."""
        if story.writer.user != user and getattr(user, "role", "") != "ADMIN":
            raise PermissionDeniedError("You do not have permission to modify this series status.")

        target_status = new_status or (
            SeriesStatusType.COMPLETED if story.series_status == SeriesStatusType.ONGOING else SeriesStatusType.ONGOING
        )

        if target_status == SeriesStatusType.ONGOING:
            active_series = cls.get_active_series_for_writer(story.writer, exclude_story_id=story.id)
            if active_series:
                raise ServiceValidationError(
                    f"Cannot set series to Ongoing. You already have an active series in progress: '{active_series.title}'."
                )

        setattr(story, "series_status", target_status)
        story.save(update_fields=["series_status", "updated_at"])
        return story


class ChapterService:

    @classmethod
    def normalize_chapter_orders(cls, story) -> list:
        """Ensures all chapters for a story have sequential 1..N order without gaps or shifts."""
        chapters = list(story.chapters.all().order_by("order", "created_at"))
        if not chapters:
            return []
        needs_update = any(ch.order != i + 1 for i, ch in enumerate(chapters))
        if needs_update:
            with transaction.atomic():  # type: ignore[attr-defined]
                for i, ch in enumerate(chapters):
                    StoryChapter.objects.filter(id=ch.id).update(order=10000 + i)
                for i, ch in enumerate(chapters):
                    StoryChapter.objects.filter(id=ch.id).update(order=i + 1)
            chapters = list(story.chapters.all().order_by("order", "created_at"))
        return chapters

    @classmethod
    def recalculate_story_metrics(cls, story) -> None:
        """Aggregates word count, reading time and chapter count from chapters up to the Story parent."""
        cls.normalize_chapter_orders(story)
        chapters = story.chapters.all()
        total_words = sum(c.word_count for c in chapters)
        total_reading_time = sum(c.estimated_reading_time for c in chapters)
        chapter_count = chapters.count()

        Story.objects.filter(id=story.id).update(
            word_count=total_words,
            estimated_reading_time=total_reading_time,
            chapter_count=chapter_count,
            is_multi_chapter=True,
            updated_at=timezone.now(),
        )

    @classmethod
    def create_chapter(cls, story, data: dict, user) -> StoryChapter:
        """Creates a chapter under a multi-chapter story."""
        if story.writer.user != user and getattr(user, "role", "") != "ADMIN":
            raise PermissionDeniedError("You do not have permission to add chapters to this story.")

        content = data.get("content", "").strip()
        title = data.get("title", "").strip()
        if content:
            ModerationService.check_content(content)
            sanitized_content = ModerationService.sanitize_text(content)
        else:
            sanitized_content = ""

        plain_text = StoryService.strip_html(sanitized_content)
        word_cnt = StoryService.calculate_word_count(sanitized_content)
        user_rt = data.get("estimated_reading_time")
        read_time = int(user_rt) if user_rt and int(user_rt) > 0 else StoryService.calculate_reading_time(sanitized_content)

        # Determine order
        requested_order = data.get("order")
        existing_count = story.chapters.count()
        if requested_order and int(requested_order) > 0:
            order = int(requested_order)
            with transaction.atomic():  # type: ignore[attr-defined]
                story.chapters.filter(order__gte=order).update(order=models.F("order") + 1)
        else:
            order = existing_count + 1

        requested_status = data.get("status") or StoryStatus.DRAFT

        chapter = StoryChapter.objects.create(
            story=story,
            order=order,
            title=title,
            content=sanitized_content,
            plain_text_content=plain_text,
            estimated_reading_time=read_time,
            word_count=word_cnt,
            status=requested_status,
        )

        cls.recalculate_story_metrics(story)

        if requested_status == StoryStatus.PENDING_REVIEW:
            cls.submit_chapter(chapter, user)

        return chapter

    @classmethod
    def update_chapter(cls, chapter, data: dict, user):
        """Updates chapter title, content, reading time, or status."""
        if chapter.story.writer.user != user and getattr(user, "role", "") != "ADMIN":
            raise PermissionDeniedError("You do not have permission to edit this chapter.")

        if "title" in data:
            chapter.title = data["title"].strip()

        if "content" in data:
            content = data["content"].strip()
            if content:
                ModerationService.check_content(content)
                sanitized_content = ModerationService.sanitize_text(content)
            else:
                sanitized_content = ""
            chapter.content = sanitized_content
            chapter.plain_text_content = StoryService.strip_html(sanitized_content)
            chapter.word_count = StoryService.calculate_word_count(sanitized_content)

        if "estimated_reading_time" in data:
            user_rt = data["estimated_reading_time"]
            chapter.estimated_reading_time = int(user_rt) if user_rt is not None and int(user_rt) > 0 else StoryService.calculate_reading_time(str(chapter.content or ""))
        elif "content" in data:
            chapter.estimated_reading_time = StoryService.calculate_reading_time(str(chapter.content or ""))

        if "status" in data:
            new_status = data["status"]
            if new_status == StoryStatus.PENDING_REVIEW:
                chapter.save()
                cls.recalculate_story_metrics(chapter.story)
                return cls.submit_chapter(chapter, user)
            elif new_status == StoryStatus.PUBLISHED and getattr(user, "role", "") == "ADMIN":
                chapter.save()
                cls.recalculate_story_metrics(chapter.story)
                return cls.publish_chapter(chapter, user)
            else:
                chapter.status = new_status

        if "rejection_feedback" in data:
            chapter.rejection_feedback = data["rejection_feedback"]

        chapter.save()
        cls.recalculate_story_metrics(chapter.story)
        return chapter

    @classmethod
    def submit_chapter(cls, chapter, user) -> StoryChapter:
        """Submits a single chapter for editorial review."""
        if chapter.story.writer.user != user and getattr(user, "role", "") != "ADMIN":
            raise PermissionDeniedError("You do not have permission to submit this chapter.")

        if not chapter.content or len(chapter.content.strip()) < 20:
            raise ServiceValidationError("Chapter content must have at least 20 characters before submitting for review.")

        # Run automated moderation
        ModerationService.check_content(f"{chapter.title} {chapter.content}")

        now = timezone.now()
        chapter.status = StoryStatus.PENDING_REVIEW
        chapter.save(update_fields=["status", "updated_at"])

        # If the parent story was DRAFT or REJECTED, elevate parent story to PENDING_REVIEW
        if chapter.story.status in [StoryStatus.DRAFT, StoryStatus.REJECTED]:
            chapter.story.status = StoryStatus.PENDING_REVIEW
            chapter.story.submitted_at = now
            chapter.story.save(update_fields=["status", "submitted_at", "updated_at"])

        return chapter

    @classmethod
    def approve_chapter(cls, chapter, admin) -> StoryChapter:
        """Approves a chapter in editorial review."""
        now = timezone.now()
        chapter.status = StoryStatus.APPROVED
        chapter.save(update_fields=["status", "updated_at"])
        return chapter

    @classmethod
    def publish_chapter(cls, chapter, admin) -> StoryChapter:
        """Publishes an approved or pending chapter to the public."""
        now = timezone.now()
        chapter.status = StoryStatus.PUBLISHED
        chapter.published_at = now
        chapter.save(update_fields=["status", "published_at", "updated_at"])

        # Ensure parent story is also published so public readers can access it
        if chapter.story.status != StoryStatus.PUBLISHED:
            chapter.story.status = StoryStatus.PUBLISHED
            if not chapter.story.published_at:
                chapter.story.published_at = now
            chapter.story.save(update_fields=["status", "published_at", "updated_at"])

        return chapter

    @classmethod
    def reject_chapter(cls, chapter, admin, feedback: str = "") -> StoryChapter:
        """Rejects a chapter with mandatory feedback."""
        feedback_text = (feedback or "").strip()
        if not feedback_text:
            raise ServiceValidationError("Rejection feedback is mandatory when rejecting a chapter.")

        now = timezone.now()
        chapter.status = StoryStatus.REJECTED
        chapter.rejection_feedback = feedback_text
        chapter.save(update_fields=["status", "rejection_feedback", "updated_at"])

        # If parent story was PENDING_REVIEW and all chapters are now REJECTED/DRAFT with no PUBLISHED chapters
        published_exists = chapter.story.chapters.filter(status=StoryStatus.PUBLISHED).exists()
        pending_exists = chapter.story.chapters.filter(status=StoryStatus.PENDING_REVIEW).exists()
        if not published_exists and not pending_exists and chapter.story.status == StoryStatus.PENDING_REVIEW:
            chapter.story.status = StoryStatus.REJECTED
            chapter.story.rejection_feedback = feedback_text
            chapter.story.save(update_fields=["status", "rejection_feedback", "updated_at"])

        return chapter

    @classmethod
    def delete_chapter(cls, chapter, user) -> None:
        """Deletes a chapter and compacts the order sequence of remaining chapters."""
        story = chapter.story
        if story.writer.user != user and getattr(user, "role", "") != "ADMIN":
            raise PermissionDeniedError("You do not have permission to delete this chapter.")

        deleted_order = chapter.order
        with transaction.atomic():  # type: ignore[attr-defined]
            chapter.delete()
            story.chapters.filter(order__gt=deleted_order).update(order=models.F("order") - 1)

        cls.recalculate_story_metrics(story)

    @classmethod
    def reorder_chapters(cls, story, ordered_ids: list, user) -> list:
        """Bulk reorders chapters for a story."""
        if story.writer.user != user and getattr(user, "role", "") != "ADMIN":
            raise PermissionDeniedError("You do not have permission to reorder chapters on this story.")

        chapters = {str(c.id): c for c in story.chapters.all()}
        with transaction.atomic():  # type: ignore[attr-defined]
            # First set to high order to avoid unique_together constraint collision
            for i, cid in enumerate(ordered_ids):
                if str(cid) in chapters:
                    chapters[str(cid)].order = 10000 + i
                    chapters[str(cid)].save(update_fields=["order"])

            for i, cid in enumerate(ordered_ids):
                if str(cid) in chapters:
                    chapters[str(cid)].order = i + 1
                    chapters[str(cid)].save(update_fields=["order"])

        return list(story.chapters.order_by("order"))
