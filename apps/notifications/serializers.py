"""
apps/notifications/serializers.py — Serializer for In-App Notifications
"""
from rest_framework import serializers
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "object_type",
            "object_id",
            "action_url",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields
