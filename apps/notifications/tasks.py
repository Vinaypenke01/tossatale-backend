"""
apps/notifications — Celery Tasks
Email notifications are queued here and sent asynchronously per §37 and §45.
"""
import logging
from celery import shared_task

logger = logging.getLogger("apps.notifications")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_writer_verification_email(self, user_id: str):
    """
    Send verification email to a writer whose profile was verified by Admin.
    """
    try:
        from django.contrib.auth import get_user_model
        from django.core.mail import send_mail
        from django.conf import settings

        User = get_user_model()
        user = User.objects.get(pk=user_id)

        send_mail(
            subject="You're now a Verified Writer on Tossatale",
            message=(
                f"Hi {user.get_short_name()},\n\n"
                "Congratulations! Your Tossatale writer profile has been verified. "
                "A verified badge will now appear alongside your stories.\n\n"
                "Keep writing,\nThe Tossatale Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Verification email sent to %s", user.email)
    except Exception as exc:
        logger.error("Failed to send verification email: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(self, user_id: str):
    """Send password reset link email."""
    try:
        from django.contrib.auth import get_user_model
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.core.mail import send_mail
        from django.conf import settings

        User = get_user_model()
        user = User.objects.get(pk=user_id)

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
        )
        logger.info("Password reset email sent to %s", user.email)
    except Exception as exc:
        logger.error("Failed to send password reset email: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_story_submission_email(self, story_id: str):
    """Notify admins when a new story is submitted for review."""
    try:
        from django.contrib.auth import get_user_model
        from django.core.mail import send_mail
        from django.conf import settings
        from apps.stories.models import Story

        story = Story.objects.select_related("writer__user", "category").get(pk=story_id)
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
            logger.info("Story submission notification sent to admins for story %s", story_id)
    except Exception as exc:
        logger.warning("Notification email skipped or failed: %s", exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_story_approval_email(self, story_id: str):
    """Notify writer when their story is approved."""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        from apps.stories.models import Story

        story = Story.objects.select_related("writer__user").get(pk=story_id)
        user = story.writer.user

        send_mail(
            subject=f"Your story '{story.title}' has been approved!",
            message=(
                f"Hi {user.get_short_name()},\n\n"
                f"Great news! Your story '{story.title}' has been approved by our editorial team.\n\n"
                "Thank you for sharing your story with Tossatale!\n\nThe Tossatale Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        logger.info("Story approval email sent to writer for story %s", story_id)
    except Exception as exc:
        logger.warning("Story approval email failed or skipped: %s", exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_story_rejection_email(self, story_id: str):
    """Notify writer when their story requires changes or is rejected."""
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        from apps.stories.models import Story

        story = Story.objects.select_related("writer__user").get(pk=story_id)
        user = story.writer.user

        send_mail(
            subject=f"Update regarding your story '{story.title}'",
            message=(
                f"Hi {user.get_short_name()},\n\n"
                f"Our editorial team reviewed your story '{story.title}' and requested changes before it can be published.\n\n"
                f"Editorial Feedback:\n{story.rejection_feedback}\n\n"
                "You can edit your draft and submit it again for review anytime.\n\nThe Tossatale Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        logger.info("Story rejection feedback email sent to writer for story %s", story_id)
    except Exception as exc:
        logger.warning("Story rejection email failed or skipped: %s", exc)
