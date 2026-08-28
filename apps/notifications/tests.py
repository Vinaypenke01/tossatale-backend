"""
apps/notifications/tests.py — Notification service & API test suite
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from common.constants import NotificationType

User = get_user_model()


class NotificationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="notifuser@tossatale.com",
            password="Password123!",
            first_name="Notif",
            last_name="User",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_and_fetch_notifications(self):
        NotificationService.create(
            recipient=self.user,
            notification_type=NotificationType.SYSTEM_NOTIFICATION,
            title="Welcome to Tossatale",
            message="Your account is active.",
        )

        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get("data", {}).get("results", data.get("data", []))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Welcome to Tossatale")
        self.assertFalse(results[0]["is_read"])

    def test_mark_all_read(self):
        NotificationService.create(
            recipient=self.user,
            notification_type=NotificationType.SYSTEM_NOTIFICATION,
            title="Alert 1",
            message="Message 1",
        )
        NotificationService.create(
            recipient=self.user,
            notification_type=NotificationType.SYSTEM_NOTIFICATION,
            title="Alert 2",
            message="Message 2",
        )

        unread_resp = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(unread_resp.json()["data"]["unread_count"], 2)

        mark_resp = self.client.post("/api/v1/notifications/mark-all-read/")
        self.assertEqual(mark_resp.status_code, status.HTTP_200_OK)

        unread_after = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(unread_after.json()["data"]["unread_count"], 0)
