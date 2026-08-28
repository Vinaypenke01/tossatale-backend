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
