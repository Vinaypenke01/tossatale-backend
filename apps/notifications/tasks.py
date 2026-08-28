"""
apps/notifications — Email Notification Service Functions
Emails are delivered synchronously/in-memory using EmailService / django.core.mail, respecting user notification preferences.
"""
import logging
from celery import shared_task

logger = logging.getLogger("apps.notifications")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_writer_verification_email(self_or_user_id, user_id=None):
    """
    Send verification email to a writer whose profile was verified by Admin.
    Can be called directly as `send_writer_verification_email(user_id)` or via `.delay(user_id)`.
    """
    target_id = user_id if user_id is not None else self_or_user_id
    try:
        from django.contrib.auth import get_user_model
        from common.services.email_service import EmailService

        User = get_user_model()
        user = User.objects.get(pk=target_id)

        # Check notification preference
        if hasattr(user, "notification_preferences"):
            prefs = user.notification_preferences
            if not prefs.email_notifications or not prefs.platform_update_notifications:
                logger.info("Skipping verification email for %s (opted out).", user.email)
                return

        writer_name = user.get_full_name() or user.display_name or user.get_short_name()
        EmailService.send_writer_verification_email(
            to_email=user.email,
            writer_name=writer_name,
        )
        logger.info("Verification email sent to %s", user.email)
    except Exception as exc:
        logger.warning("Failed to send verification email: %s", exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self_or_user_id, user_id=None):
    """Send password reset link email."""
    target_id = user_id if user_id is not None else self_or_user_id
    try:
        from django.contrib.auth import get_user_model
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.core.mail import send_mail
        from django.conf import settings

        User = get_user_model()
        user = User.objects.get(pk=target_id)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

        send_mail(
            subject="Reset your Tossatale password",
            message=(
                f"Hi {user.get_short_name()},\n\n"
                f"Click the link below to reset your password:\n{reset_url}\n\n"
                "This link expires in 24 hours.\n\nThe Tossatale Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        logger.info("Password reset email sent to %s", user.email)
    except Exception as exc:
        logger.warning("Failed to send password reset email: %s", exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_story_submission_email(self_or_story_id, story_id=None):
    """Notify admins when a new story is submitted for review."""
    target_id = story_id if story_id is not None else self_or_story_id
    try:
        from django.contrib.auth import get_user_model
        from django.core.mail import send_mail
        from django.conf import settings
        from apps.stories.models import Story

        story = Story.objects.select_related("writer__user", "category").get(pk=target_id)
        User = get_user_model()
        admin_emails = list(User.objects.filter(role="ADMIN", is_active=True).values_list("email", flat=True))

        writer_name = getattr(story.writer, "pen_name", None) or getattr(story.writer, "name", "A writer")
        category_name = getattr(story.category, "name", "General") if story.category else "General"

        if admin_emails:
            send_mail(
                subject=f"[Story Submission] {story.title}",
                message=(
                    f"A new story has been submitted by {writer_name}:\n\n"
                    f"Title: {story.title}\n"
                    f"Category: {category_name}\n"
                    f"Word Count: {story.word_count}\n\n"
                    "Log into the Admin Panel to review and approve."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=True,
            )
            logger.info("Story submission notification sent to admins for story %s", target_id)
    except Exception as exc:
        logger.warning("Story submission notification email skipped or failed: %s", exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_story_approval_email(self_or_story_id, story_id=None):
    """Notify writer when their story is approved."""
    target_id = story_id if story_id is not None else self_or_story_id
    try:
        from apps.stories.models import Story
        from common.services.email_service import EmailService

        story = Story.objects.select_related("writer__user").get(pk=target_id)
        user = story.writer.user

        # Check notification preferences
        if hasattr(user, "notification_preferences"):
            prefs = user.notification_preferences
            if not prefs.email_notifications or not prefs.story_approval_notifications:
                logger.info("Skipping approval email for %s (opted out).", user.email)
                return

        writer_name = getattr(story.writer, "pen_name", None) or user.get_short_name() or "Storyteller"

        EmailService.send_editorial_status_email(
            to_email=user.email,
            writer_name=writer_name,
            story_title=story.title,
            status="PUBLISHED",
            feedback="",
        )
        logger.info("Story approval email sent to writer for story %s", target_id)
    except Exception as exc:
        logger.warning("Story approval email failed or skipped: %s", exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_story_rejection_email(self_or_story_id, story_id=None):
    """Notify writer when their story requires changes or is rejected."""
    target_id = story_id if story_id is not None else self_or_story_id
    try:
        from apps.stories.models import Story
        from common.services.email_service import EmailService

        story = Story.objects.select_related("writer__user").get(pk=target_id)
        user = story.writer.user

        # Check notification preferences
        if hasattr(user, "notification_preferences"):
            prefs = user.notification_preferences
            if not prefs.email_notifications or not prefs.story_rejection_notifications:
                logger.info("Skipping rejection feedback email for %s (opted out).", user.email)
                return

        writer_name = getattr(story.writer, "pen_name", None) or user.get_short_name() or "Storyteller"

        EmailService.send_editorial_status_email(
            to_email=user.email,
            writer_name=writer_name,
            story_title=story.title,
            status="REJECTED",
            feedback=story.rejection_feedback or "Please review and revise your draft.",
        )
        logger.info("Story rejection feedback email sent to writer for story %s", target_id)
    except Exception as exc:
        logger.warning("Story rejection email failed or skipped: %s", exc)
