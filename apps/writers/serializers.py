"""
apps/writers — Writer Profile Serializers
"""
from rest_framework import serializers
from apps.writers.models import WriterProfile
from apps.accounts.serializers import UserMeSerializer


def _calculate_writer_stories(writer_profile) -> int:
    from apps.stories.models import Story
    from apps.series.models import StorySeries
    from django.db.models import Q

    # 1. Direct stories linked to writer_profile or user
    direct_stories = Story.objects.filter(
        Q(writer=writer_profile) | Q(created_by=writer_profile.user)
    ).count()

    # 2. Series linked to writer_profile or user
    series_count = StorySeries.objects.filter(
        Q(writer=writer_profile) | Q(created_by=writer_profile.user)
    ).count()

    return max(direct_stories, series_count, writer_profile.total_stories or 0)


def _calculate_writer_reads(writer_profile) -> int:
    from apps.stories.models import Story
    from django.db.models import Sum, Q

    reads = Story.objects.filter(
        Q(writer=writer_profile) | Q(created_by=writer_profile.user)
    ).aggregate(Sum("views_count"))["views_count__sum"] or 0
    return max(reads, writer_profile.total_reads or 0)


def _calculate_writer_likes(writer_profile) -> int:
    from apps.stories.models import Story
    from apps.writers.models import WriterSupport
    from django.db.models import Sum, Q

    story_likes = Story.objects.filter(
        Q(writer=writer_profile) | Q(created_by=writer_profile.user)
    ).aggregate(Sum("likes_count"))["likes_count__sum"] or 0
    direct_supports = WriterSupport.objects.filter(writer=writer_profile).count()

    return max(story_likes + direct_supports, direct_supports, writer_profile.total_likes or 0)


class PublicWriterSerializer(serializers.ModelSerializer):
    """Public-facing writer profile representation."""
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
    total_stories = serializers.SerializerMethodField()
    total_reads = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()
    total_supports = serializers.SerializerMethodField()
    has_supported_today = serializers.SerializerMethodField()

    class Meta:
        model = WriterProfile
        fields = [
            "id", "slug", "name", "email", "gender",
            "bio", "profile_photo", "location", "author_title", "tagline",
            "is_verified", "verified_at",
            "total_stories", "total_reads", "total_likes", "total_supports", "total_shares",
            "has_supported_today",
            "social_links", "created_at",
        ]
        read_only_fields = fields

    def get_name(self, obj):
        return obj.user.get_full_name()

    def get_email(self, obj):
        return obj.user.email

    def get_social_links(self, obj):
        return obj.get_social_links()

    def get_total_stories(self, obj):
        return _calculate_writer_stories(obj)

    def get_total_reads(self, obj):
        return _calculate_writer_reads(obj)

    def get_total_likes(self, obj):
        return _calculate_writer_likes(obj)

    def get_total_supports(self, obj):
        return _calculate_writer_likes(obj)

    def get_has_supported_today(self, obj):
        request = self.context.get("request")
        if not request:
            return False
        from apps.writers.models import WriterSupport
        from django.utils import timezone
        from django.db.models import Q
        import hashlib

        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if request.user and request.user.is_authenticated:
            return WriterSupport.objects.filter(writer=obj, user=request.user, created_at__gte=today_start).exists()

        ip_addr = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
        ip_h = hashlib.sha256(ip_addr.encode("utf-8")).hexdigest() if ip_addr else ""
        session_id = request.headers.get("X-Session-ID") or getattr(request, "session", None) and request.session.session_key or ""

        query = WriterSupport.objects.filter(writer=obj, created_at__gte=today_start)
        if session_id and ip_h:
            return query.filter(Q(session_id=session_id) | Q(ip_hash=ip_h)).exists()
        elif session_id:
            return query.filter(session_id=session_id).exists()
        elif ip_h:
            return query.filter(ip_hash=ip_h).exists()
        return False


class WriterProfileUpdateSerializer(serializers.ModelSerializer):
    """Used by writer to update their own profile — PATCH /api/v1/writer/profile/"""
    name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = WriterProfile
        fields = [
            "name", "gender", "bio", "profile_photo",
            "location", "author_title", "tagline",
            "website_url", "facebook_url", "instagram_url",
            "x_url", "linkedin_url", "youtube_url",
        ]


class AdminWriterSerializer(serializers.ModelSerializer):
    """Full writer detail for Admin — includes user info and verification."""
    user = UserMeSerializer(read_only=True)
    social_links = serializers.SerializerMethodField()
    total_stories = serializers.SerializerMethodField()
    total_reads = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()
    total_supports = serializers.SerializerMethodField()

    class Meta:
        model = WriterProfile
        fields = [
            "id", "slug", "user", "gender",
            "bio", "profile_photo", "location", "author_title", "tagline",
            "is_verified", "verified_at", "verified_by",
            "is_active",
            "total_stories", "total_reads", "total_likes", "total_supports", "total_shares",
            "social_links", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "user", "is_verified", "verified_at",
            "verified_by", "total_stories", "total_reads",
            "total_likes", "total_supports", "total_shares", "created_at",
        ]

    def get_social_links(self, obj):
        return obj.get_social_links()

    def get_total_stories(self, obj):
        return _calculate_writer_stories(obj)

    def get_total_reads(self, obj):
        return _calculate_writer_reads(obj)

    def get_total_likes(self, obj):
        return _calculate_writer_likes(obj)

    def get_total_supports(self, obj):
        return _calculate_writer_likes(obj)


class AdminWriterListSerializer(serializers.ModelSerializer):
    """Compact writer list for Admin table view."""
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    total_stories = serializers.SerializerMethodField()
    total_reads = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()
    total_supports = serializers.SerializerMethodField()

    class Meta:
        model = WriterProfile
        fields = [
            "id", "slug", "name", "email", "role", "gender",
            "location", "author_title", "tagline",
            "is_verified", "is_active",
            "total_stories", "total_reads", "total_likes", "total_supports",
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
        return _calculate_writer_stories(obj)

    def get_total_reads(self, obj):
        return _calculate_writer_reads(obj)

    def get_total_likes(self, obj):
        return _calculate_writer_likes(obj)

    def get_total_supports(self, obj):
        return _calculate_writer_likes(obj)


WriterProfileSerializer = PublicWriterSerializer
