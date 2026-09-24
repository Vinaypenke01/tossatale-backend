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

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.CharField(required=False, default="USER")
    bio = serializers.CharField(required=False, allow_blank=True)
    website_url = serializers.URLField(required=False, allow_blank=True)
    consent = serializers.BooleanField(required=False, default=False)
    terms_accepted = serializers.BooleanField(required=False, default=False)


class ReaderToWriterUpgradeSerializer(serializers.Serializer):
    pen_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    bio = serializers.CharField(required=False, allow_blank=True, default="")
    gender = serializers.CharField(required=False, default="OTHER")
    confirm_reader_migration = serializers.BooleanField(required=True)

    def validate_confirm_reader_migration(self, value):
        if not value:
            raise serializers.ValidationError("You must confirm that your reader account will be converted to a writer account.")
        return value


class ReaderMigrateUnauthenticatedSerializer(serializers.Serializer):
    email = serializers.EmailField()
    current_password = serializers.CharField(write_only=True)
    pen_name = serializers.CharField(max_length=150)
    new_password = serializers.CharField(write_only=True, min_length=8, required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True, default="")
    gender = serializers.CharField(required=False, default="OTHER")
    confirm_reader_migration = serializers.BooleanField(required=True)

    def validate_confirm_reader_migration(self, value):
        if not value:
            raise serializers.ValidationError("You must confirm that your reader account will be converted to a writer account.")
        return value


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

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs["new_password"])
        return attrs


class TokenPairSerializer(serializers.Serializer):
    """Response serializer for successful login — returns access + refresh tokens."""
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


# ──────────────────────────────────────────────────────────────────────────────
# User Serializers
# ──────────────────────────────────────────────────────────────────────────────

class UserMeSerializer(serializers.ModelSerializer):
    """Minimal user info returned from GET /auth/me/ and GET /user/profile/"""
    full_name = serializers.SerializerMethodField()
    writer_slug = serializers.SerializerMethodField()
    writer_id = serializers.SerializerMethodField()
    writer_bio = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "display_name", "role", "profile_photo", "writer_slug", "writer_id", "writer_bio",
            "auth_provider", "is_email_verified", "is_active",
            "last_login", "created_at",
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_writer_slug(self, obj):
        if hasattr(obj, "writer_profile") and obj.writer_profile:
            return obj.writer_profile.slug
        return None

    def get_writer_id(self, obj):
        if hasattr(obj, "writer_profile") and obj.writer_profile:
            return str(obj.writer_profile.id)
        return None

    def get_writer_bio(self, obj):
        if hasattr(obj, "writer_profile") and obj.writer_profile:
            return obj.writer_profile.bio
        return ""


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH /user/profile/ — only writable user fields."""
    bio = serializers.CharField(required=False, allow_blank=True)
    writer_bio = serializers.CharField(required=False, allow_blank=True)
    writer_slug = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "display_name", "profile_photo", "bio", "writer_bio", "writer_slug"]


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
