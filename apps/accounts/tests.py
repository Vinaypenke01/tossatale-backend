"""
apps/accounts/tests.py — Auth, registration, and user session test suite
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="reader@tossatale.com",
            password="StrongPassword123!",
            first_name="Alice",
            last_name="Reader",
        )

    def test_login_success(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "reader@tossatale.com", "password": "StrongPassword123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("tokens", data.get("data", {}))
        self.assertIn("access", data["data"]["tokens"])
        self.assertIn("refresh", data["data"]["tokens"])

    def test_login_invalid_credentials(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "reader@tossatale.com", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_flow(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "email": "newuser@tossatale.com",
                "password": "NewUserPassword123!",
                "first_name": "Bob",
                "last_name": "Smith",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="newuser@tossatale.com").exists())

    def test_reader_upgrade_to_writer_success(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/auth/upgrade-to-writer/",
            {
                "pen_name": "Alice Novelist",
                "password": "NewWriterPassword123!",
                "bio": "Writing evocative fiction.",
                "confirm_reader_migration": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["data"]["user"]["role"], "WRITER")
        self.assertEqual(data["data"]["redirect_url"], "/writer")

        # Verify DB state
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "WRITER")
        self.assertTrue(self.user.check_password("NewWriterPassword123!"))
        self.assertTrue(hasattr(self.user, "writer_profile"))
        self.assertEqual(self.user.writer_profile.slug, "alice-novelist")

    def test_upgrade_fails_without_password(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/auth/upgrade-to-writer/",
            {
                "pen_name": "Alice Novelist",
                "password": "short",
                "confirm_reader_migration": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upgrade_fails_without_confirmation(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/auth/upgrade-to-writer/",
            {
                "pen_name": "Alice Novelist",
                "password": "NewWriterPassword123!",
                "confirm_reader_migration": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_migrated_writer_cannot_use_google_login(self):
        from apps.accounts.services import AuthService
        from common.exceptions import WriterGoogleAuthBlockedError
        # Promote user to WRITER
        self.user.role = "WRITER"
        self.user.save()

        with self.assertRaises(WriterGoogleAuthBlockedError):
            # Mock Google payload returning this user's email
            from unittest.mock import patch
            with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
                mock_verify.return_value = {
                    "sub": "google-12345",
                    "email": self.user.email,
                    "given_name": "Alice",
                    "family_name": "Reader",
                }
                AuthService.google_login("mock-token")

