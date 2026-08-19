"""
apps/accounts — Auth & User Serializers
Handles request deserialization, response formatting, and field-level validation.
Business logic belongs in AuthService / UserService per §4.2.
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User, NotificationPreference


# ──────────────────────────────────────────────────────────────────────────────
# Auth Serializers
# ──────────────────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(
        help_text="Google ID token obtained from the frontend after user consent."
    )


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(data["new_password"])
        return data


class TokenPairSerializer(serializers.Serializer):
    """Response serializer for successful login — returns access + refresh tokens."""
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


# ──────────────────────────────────────────────────────────────────────────────
# User Serializers
# ──────────────────────────────────────────────────────────────────────────────

class UserMeSerializer(serializers.ModelSerializer):
    """Minimal user info returned from GET /auth/me/"""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "display_name", "role", "profile_photo",
            "auth_provider", "is_email_verified", "is_active",
            "last_login", "created_at",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH /user/profile/ — only writable user fields."""
    class Meta:
        model = User
        fields = ["first_name", "last_name", "display_name", "profile_photo"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "email_notifications",
            "story_approval_notifications",
            "story_rejection_notifications",
            "platform_update_notifications",
            "newsletter_notifications",
            "new_story_notifications",
        ]


# ──────────────────────────────────────────────────────────────────────────────
# Admin User Serializers
# ──────────────────────────────────────────────────────────────────────────────

class AdminUserListSerializer(serializers.ModelSerializer):
    """Compact user representation for Admin user management."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "role",
            "is_active", "is_email_verified", "auth_provider",
            "last_login", "created_at",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()


class AdminUserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "display_name", "role", "profile_photo",
            "auth_provider", "google_id",
            "is_email_verified", "is_active", "is_staff",
            "last_login", "last_activity_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "email", "auth_provider", "google_id", "created_at", "updated_at"]

    def get_full_name(self, obj):
        return obj.get_full_name()
