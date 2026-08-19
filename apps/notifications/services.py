"""
apps/notifications — Service
"""
import logging
from apps.notifications.models import Notification

logger = logging.getLogger("apps.notifications")


class NotificationService:

    @staticmethod
    def create(recipient, notification_type: str, title: str, message: str,
               sender=None, object_type: str = "", object_id: str = "",
               action_url: str = "") -> Notification:
        return Notification.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            object_type=object_type,
            object_id=str(object_id),
            action_url=action_url,
        )

    @staticmethod
    def mark_read(notification: Notification) -> Notification:
        from django.utils import timezone
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
        return notification

    @staticmethod
    def mark_all_read(user) -> int:
        from django.utils import timezone
        return Notification.objects.filter(
            recipient=user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
