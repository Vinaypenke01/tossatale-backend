"""
apps/writers — Writer Profile Serializers
"""
from rest_framework import serializers
from apps.writers.models import WriterProfile
from apps.accounts.serializers import UserMeSerializer


class PublicWriterSerializer(serializers.ModelSerializer):
    """Public-facing writer profile representation."""
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()

    class Meta:
        model = WriterProfile
        fields = [
            "id", "slug", "name", "email", "gender",
            "bio", "profile_photo",
            "is_verified", "verified_at",
            "total_stories", "total_reads", "total_likes", "total_shares",
            "social_links", "created_at",
        ]
        read_only_fields = fields

    def get_name(self, obj):
        return obj.user.get_full_name()

    def get_email(self, obj):
        return obj.user.email

    def get_social_links(self, obj):
        return obj.get_social_links()


class WriterProfileUpdateSerializer(serializers.ModelSerializer):
    """Used by writer to update their own profile — PATCH /api/v1/writer/profile/"""
    name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = WriterProfile
        fields = [
            "name", "gender", "bio", "profile_photo",
            "website_url", "facebook_url", "instagram_url",
            "x_url", "linkedin_url", "youtube_url",
        ]


class AdminWriterSerializer(serializers.ModelSerializer):
    """Full writer detail for Admin — includes user info and verification."""
    user = UserMeSerializer(read_only=True)
    social_links = serializers.SerializerMethodField()
    total_stories = serializers.SerializerMethodField()

    class Meta:
        model = WriterProfile
        fields = [
            "id", "slug", "user", "gender",
            "bio", "profile_photo",
            "is_verified", "verified_at", "verified_by",
            "is_active",
            "total_stories", "total_reads", "total_likes", "total_shares",
            "social_links", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "user", "is_verified", "verified_at",
            "verified_by", "total_stories", "total_reads",
            "total_likes", "total_shares", "created_at",
        ]

    def get_social_links(self, obj):
        return obj.get_social_links()

    def get_total_stories(self, obj):
        return obj.stories.count()


class AdminWriterListSerializer(serializers.ModelSerializer):
    """Compact writer list for Admin table view."""
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    total_stories = serializers.SerializerMethodField()

    class Meta:
        model = WriterProfile
        fields = [
            "id", "slug", "name", "email", "role", "gender",
            "is_verified", "is_active",
            "total_stories", "total_reads",
            "created_at",
        ]
        read_only_fields = fields

    def get_name(self, obj):
        return obj.user.get_full_name()

    def get_email(self, obj):
        return obj.user.email

    def get_role(self, obj):
        return obj.user.role

    def get_total_stories(self, obj):
        return obj.stories.count()


WriterProfileSerializer = PublicWriterSerializer
