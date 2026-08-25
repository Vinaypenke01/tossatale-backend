"""
apps/engagements/services.py — EngagementService
Core service layer handling story likes, bookmarks, shares, view deduplication, and recently read history per §25.
"""
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache

from common.constants import StoryStatus
from common.exceptions import (
    ServiceValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from django.db.models import F
from apps.writers.models import WriterProfile
from apps.stories.models import Story
from apps.engagements.models import StoryLike, StoryBookmark, StoryShare, StoryView, RecentlyRead


class EngagementService:

    @staticmethod
    def hash_ip(ip_address: str) -> str:
        if not ip_address:
            return ""
        return hashlib.sha256(ip_address.encode("utf-8")).hexdigest()

    @classmethod
    @transaction.atomic
    def like_story(cls, user, story: Story) -> StoryLike:
        """Likes a story, preventing duplicate likes."""
        if story.status != StoryStatus.PUBLISHED:
            raise ServiceValidationError("Only published stories can be liked.")

        existing = StoryLike.objects.filter(user=user, story=story).first()
        if existing:
            return existing

        like = StoryLike.objects.create(user=user, story=story)

        # Atomic increment counts
        Story.objects.filter(id=story.id).update(
            likes_count=F("likes_count") + 1,
            updated_at=timezone.now()
        )
        story.refresh_from_db(fields=["likes_count"])

        if story.writer_id:
            WriterProfile.objects.filter(id=story.writer_id).update(
                total_likes=F("total_likes") + 1
            )

        cache.delete("homepage")

        return like

    @classmethod
    @transaction.atomic
    def unlike_story(cls, user, story: Story):
        """Removes a like from a story."""
        try:
            like = StoryLike.objects.get(user=user, story=story)
        except StoryLike.DoesNotExist:
            raise ResourceNotFoundError("Like record not found.")

        like.delete()

        Story.objects.filter(id=story.id).update(
            likes_count=F("likes_count") - 1,
            updated_at=timezone.now()
        )
        story.refresh_from_db(fields=["likes_count"])

        if story.writer_id:
            WriterProfile.objects.filter(id=story.writer_id).update(
                total_likes=F("total_likes") - 1
            )

        cache.delete("homepage")

    @classmethod
    @transaction.atomic
    def bookmark_story(cls, user, story: Story) -> StoryBookmark:
        """Bookmarks a story for a reader."""
        if story.status != StoryStatus.PUBLISHED:
            raise ServiceValidationError("Only published stories can be bookmarked.")

        existing = StoryBookmark.objects.filter(user=user, story=story).first()
        if existing:
            return existing

        bookmark = StoryBookmark.objects.create(user=user, story=story)

        Story.objects.filter(id=story.id).update(
            bookmarks_count=F("bookmarks_count") + 1,
            updated_at=timezone.now()
        )
        story.refresh_from_db(fields=["bookmarks_count"])

        return bookmark

    @classmethod
    @transaction.atomic
    def remove_bookmark(cls, user, story: Story):
        """Removes a bookmarked story."""
        try:
            bookmark = StoryBookmark.objects.get(user=user, story=story)
        except StoryBookmark.DoesNotExist:
            raise ResourceNotFoundError("Bookmark not found.")

        bookmark.delete()

        Story.objects.filter(id=story.id).update(
            bookmarks_count=F("bookmarks_count") - 1,
            updated_at=timezone.now()
        )
        story.refresh_from_db(fields=["bookmarks_count"])

    @classmethod
    @transaction.atomic
    def record_share(cls, story: Story, platform: str, user=None, session_id: str = "", ip_address: str = "") -> StoryShare:
        """Tracks a social share event."""
        ip_h = cls.hash_ip(ip_address)
        share = StoryShare.objects.create(
            story=story,
            user=user if user and user.is_authenticated else None,
            platform=platform,
            session_id=session_id,
            ip_hash=ip_h,
        )

        Story.objects.filter(id=story.id).update(
            shares_count=F("shares_count") + 1,
            updated_at=timezone.now()
        )
        story.refresh_from_db(fields=["shares_count"])

        return share

    @classmethod
    @transaction.atomic
    def record_view(
        cls,
        story: Story,
        user=None,
        session_id: str = "",
        ip_address: str = "",
        referrer: str = "",
        reading_duration: int = 0,
        completion_percentage: float = 0.0,
    ) -> StoryView:
        """
        Records a story view with strict 1 view per user per day deduplication.
        If user/IP opened the story today, no additional view count is added.
        If opened tomorrow (new calendar day or >24h), +1 view is added.
        """
        ip_h = cls.hash_ip(ip_address)
        now = timezone.now()
        # Today's start in current timezone (calendar day)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Determine if unique view today
        is_unique = True
        if user and user.is_authenticated:
            if StoryView.objects.filter(story=story, user=user, viewed_at__gte=day_start).exists():
                is_unique = False
        elif session_id or ip_h:
            query = StoryView.objects.filter(story=story, viewed_at__gte=day_start)
            if session_id:
                query = query.filter(session_id=session_id)
            elif ip_h:
                query = query.filter(ip_hash=ip_h)
            if query.exists():
                is_unique = False

        view = StoryView.objects.create(
            story=story,
            user=user if user and user.is_authenticated else None,
            session_id=session_id,
            ip_hash=ip_h,
            referrer=referrer[:500],
            reading_duration=reading_duration,
            completion_percentage=completion_percentage,
            is_unique_view=is_unique,
        )

        # Increment counters ONLY if this is the first view today
        if is_unique:
            Story.objects.filter(id=story.id).update(
                views_count=F("views_count") + 1,
                updated_at=timezone.now()
            )
            story.refresh_from_db(fields=["views_count"])

            if story.writer_id:
                WriterProfile.objects.filter(id=story.writer_id).update(
                    total_reads=F("total_reads") + 1
                )

        # Update reader history if authenticated
        if user and user.is_authenticated:
            cls.update_recently_read(user, story, completion_percentage)

        return view

    @classmethod
    def record_unauthenticated_like_attempt(cls, story: Story) -> int:
        """
        Increments the count of users who attempted to like the story
        without being logged in and dismissed the login prompt.
        """
        story.unauthenticated_like_attempts = (story.unauthenticated_like_attempts or 0) + 1
        story.save(update_fields=["unauthenticated_like_attempts", "updated_at"])
        return story.unauthenticated_like_attempts

    @classmethod
    def update_recently_read(cls, user, story: Story, progress: float = 0.0) -> RecentlyRead:
        """Updates reading history for a reader."""
        completed = progress >= 95.0
        record, created = RecentlyRead.objects.update_or_create(
            user=user,
            story=story,
            defaults={
                "reading_progress": progress,
                "completed": completed,
                "last_read_at": timezone.now(),
            },
        )
        return record
