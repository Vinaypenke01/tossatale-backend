"""
apps/writers — Writer Service Layer
All writer business logic per §4.3 and §32.
"""
import logging
from django.db import transaction
from django.utils import timezone

from apps.writers.models import WriterProfile
from apps.accounts.models import User
from apps.accounts.constants import UserRole
from common.exceptions import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ServiceValidationError,
)
from common.utils import generate_unique_slug

logger = logging.getLogger("apps.writers")


class WriterService:
    """
    WriterService — handles all writer lifecycle operations per §32.
    """

    @staticmethod
    def create_writer(user: User, data: dict) -> WriterProfile:
        """
        Create a writer profile for a user. Called when an Admin approves a writer application.
        """
        if user.role != UserRole.WRITER:
            raise ServiceValidationError("User must have WRITER role to create a writer profile.")

        slug = generate_unique_slug(WriterProfile, user.get_full_name())

        with transaction.atomic():
            profile = WriterProfile.objects.create(
                user=user,
                slug=slug,
                bio=data.get("bio", ""),
                profile_photo=data.get("profile_photo", ""),
                website_url=data.get("website_url", ""),
                facebook_url=data.get("facebook_url", ""),
                instagram_url=data.get("instagram_url", ""),
                x_url=data.get("x_url", ""),
                linkedin_url=data.get("linkedin_url", ""),
                youtube_url=data.get("youtube_url", ""),
            )

        logger.info("WriterProfile created for user: %s", user.email)
        return profile

    @staticmethod
    @transaction.atomic
    def update_writer(profile: WriterProfile, data: dict) -> WriterProfile:
        """Update writable writer profile fields."""
        if "name" in data and data["name"]:
            full_name = data["name"].strip()
            parts = full_name.split(" ", 1)
            profile.user.first_name = parts[0]
            profile.user.last_name = parts[1] if len(parts) > 1 else ""
            profile.user.display_name = full_name
            profile.user.save(update_fields=["first_name", "last_name", "display_name"])

        allowed = {
            "gender", "bio", "profile_photo", "website_url",
            "facebook_url", "instagram_url", "x_url",
            "linkedin_url", "youtube_url",
        }
        for field, value in data.items():
            if field in allowed:
                setattr(profile, field, value)
        profile.save()
        return profile

    @staticmethod
    def activate_writer(profile: WriterProfile, admin_user: User) -> WriterProfile:
        """Admin activates a writer account."""
        if not admin_user.is_admin:
            raise PermissionDeniedError("Only admins can activate writers.")
        profile.is_active = True
        profile.save(update_fields=["is_active", "updated_at"])
        logger.info("Writer activated: %s by %s", profile.slug, admin_user.email)
        return profile

    @staticmethod
    def deactivate_writer(profile: WriterProfile, admin_user: User) -> WriterProfile:
        """Admin deactivates a writer. Existing published stories remain visible."""
        if not admin_user.is_admin:
            raise PermissionDeniedError("Only admins can deactivate writers.")
        profile.is_active = False
        profile.save(update_fields=["is_active", "updated_at"])
        logger.info("Writer deactivated: %s by %s", profile.slug, admin_user.email)
        return profile

    @staticmethod
    def verify_writer(profile: WriterProfile, admin_user: User) -> WriterProfile:
        """
        Grant verification badge to a writer. Admin-only per §24.
        """
        if not admin_user.is_admin:
            raise PermissionDeniedError("Only admins can verify writers.")

        if not profile.is_active:
            raise ServiceValidationError("Cannot verify an inactive writer.")

        with transaction.atomic():
            profile.is_verified = True
            profile.verified_at = timezone.now()
            profile.verified_by = admin_user
            profile.save(update_fields=["is_verified", "verified_at", "verified_by", "updated_at"])

            # Create notification
            from apps.notifications.services import NotificationService
            from common.constants import NotificationType
            NotificationService.create(
                recipient=profile.user,
                notification_type=NotificationType.WRITER_VERIFIED,
                title="You've been verified!",
                message="Your writer profile has been verified by the Tossatale team.",
            )

            # Queue verification email
            from apps.notifications.tasks import send_writer_verification_email
            send_writer_verification_email.delay(str(profile.user.id))

        logger.info("Writer verified: %s by Admin %s", profile.slug, admin_user.email)
        return profile

    @staticmethod
    def unverify_writer(profile: WriterProfile, admin_user: User) -> WriterProfile:
        """Revoke verification badge. Admin-only."""
        if not admin_user.is_admin:
            raise PermissionDeniedError("Only admins can unverify writers.")

        profile.is_verified = False
        profile.save(update_fields=["is_verified", "updated_at"])

        logger.info("Writer unverified: %s by Admin %s", profile.slug, admin_user.email)
        return profile

    @staticmethod
    def update_writer_statistics(profile: WriterProfile) -> None:
        """
        Recalculate and cache writer-level statistics.
        Called via background task after engagement events.
        """
        from django.db.models import Sum
        from apps.stories.models import Story
        from common.constants import StoryStatus

        published_stories = Story.objects.filter(
            writer=profile, status=StoryStatus.PUBLISHED
        )

        stats = published_stories.aggregate(
            total_reads=Sum("views_count"),
            total_likes=Sum("likes_count"),
            total_shares=Sum("shares_count"),
        )

        profile.total_stories = published_stories.count()
        profile.total_reads = stats["total_reads"] or 0
        profile.total_likes = stats["total_likes"] or 0
        profile.total_shares = stats["total_shares"] or 0
        profile.save(update_fields=[
            "total_stories", "total_reads", "total_likes", "total_shares", "updated_at"
        ])
