"""
apps/writers — Views
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.writers.models import WriterProfile
from apps.writers.serializers import (
    AdminWriterListSerializer,
    AdminWriterSerializer,
    PublicWriterSerializer,
    WriterProfileUpdateSerializer,
)
from apps.writers.services import WriterService
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.accounts.constants import UserRole
from common.exceptions import ResourceNotFoundError, ServiceValidationError
from common.pagination import StandardPagination
from common.permissions import IsAdmin, IsWriter
from common.responses import created_response, success_response
from common.utils import generate_unique_slug

User = get_user_model()


# ──────────────────────────────────────────────────────────────────────────────
# Public Writer Views
# ──────────────────────────────────────────────────────────────────────────────

class PublicWriterListView(generics.ListAPIView):
    """GET /api/v1/public/writers/"""
    serializer_class = PublicWriterSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_verified"]
    search_fields = ["user__first_name", "user__last_name", "bio"]
    ordering_fields = ["total_reads", "total_likes", "created_at"]
    ordering = ["-total_reads"]

    def get_queryset(self):
        return WriterProfile.objects.filter(is_active=True).select_related("user")


class PublicWriterDetailView(APIView):
    """GET /api/v1/public/writers/{slug}/"""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            profile = WriterProfile.objects.select_related("user").get(slug=slug, is_active=True)
        except WriterProfile.DoesNotExist:
            raise ResourceNotFoundError("Writer not found.")
        serializer = PublicWriterSerializer(profile)
        return success_response(data=serializer.data)


class PublicWriterSupportView(APIView):
    """POST /api/v1/public/writers/{slug}/support/"""
    permission_classes = [AllowAny]

    def post(self, request, slug):
        try:
            profile = WriterProfile.objects.select_related("user").get(slug=slug, is_active=True)
        except WriterProfile.DoesNotExist:
            raise ResourceNotFoundError("Writer not found.")

        profile.total_likes = (profile.total_likes or 0) + 1
        profile.save(update_fields=["total_likes"])

        return success_response(
            data={
                "slug": profile.slug,
                "supports_count": profile.total_likes,
                "total_supports": profile.total_likes,
                "is_supported": True,
            },
            message=f"Thank you for supporting {profile.name}!"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Writer Self-Management Views
# ──────────────────────────────────────────────────────────────────────────────

class WriterProfileView(APIView):
    """GET/PATCH /api/v1/writer/profile/"""
    permission_classes = [IsWriter]

    def get(self, request):
        profile, _ = WriterProfile.objects.get_or_create(
            user=request.user,
            defaults={
                "slug": generate_unique_slug(WriterProfile, request.user.get_full_name() or request.user.email.split("@")[0] or "writer"),
                "bio": "Tossatale Storyteller & Writer",
            }
        )
        serializer = PublicWriterSerializer(profile)
        return success_response(data=serializer.data)

    def patch(self, request):
        profile, _ = WriterProfile.objects.get_or_create(
            user=request.user,
            defaults={
                "slug": generate_unique_slug(WriterProfile, request.user.get_full_name() or request.user.email.split("@")[0] or "writer"),
                "bio": "Tossatale Storyteller & Writer",
            }
        )
        serializer = WriterProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = WriterService.update_writer(profile, serializer.validated_data)
        return success_response(
            data=PublicWriterSerializer(updated).data,
            message="Profile updated.",
        )


# ──────────────────────────────────────────────────────────────────────────────
# Admin Writer Management Views
# ──────────────────────────────────────────────────────────────────────────────

class AdminWriterListView(generics.ListAPIView):
    """GET /api/v1/admin/writers/"""
    permission_classes = [IsAdmin]
    serializer_class = AdminWriterListSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_verified", "is_active"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "slug"]
    ordering_fields = ["total_reads", "total_stories", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return WriterProfile.all_objects.filter(is_deleted=False).select_related("user")

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Accurate counts across all active writers (not just current page)
        total_writers = WriterProfile.objects.filter(is_active=True, is_deleted=False).count()
        total_verified = WriterProfile.objects.filter(is_active=True, is_deleted=False, is_verified=True).count()
        total_pending = WriterProfile.objects.filter(is_active=True, is_deleted=False, is_verified=False).count()

        from django.utils import timezone
        import datetime
        one_week_ago = timezone.now() - datetime.timedelta(days=7)
        from apps.stories.models import Story
        from common.constants import StoryStatus
        published_this_week = Story.objects.filter(
            status=StoryStatus.PUBLISHED,
            published_at__gte=one_week_ago
        ).values("writer_id").distinct().count()

        if isinstance(response.data, dict):
            response.data["stats"] = {
                "total_writers": total_writers,
                "total_verified": total_verified,
                "total_pending": total_pending,
                "published_this_week": published_this_week,
            }
        return response


def _get_writer_profile_by_lookup(lookup):
    """Retrieve active (non-deleted) WriterProfile by UUID, slug, or user email."""
    import uuid
    import urllib.parse
    cleaned = urllib.parse.unquote(str(lookup)).strip()
    
    base_qs = WriterProfile.all_objects.filter(is_deleted=False).select_related("user", "verified_by")
    try:
        val = uuid.UUID(cleaned)
        return base_qs.get(pk=val)
    except Exception:
        pass
    try:
        return base_qs.get(slug__iexact=cleaned)
    except WriterProfile.DoesNotExist:
        try:
            return base_qs.get(user__email__iexact=cleaned)
        except WriterProfile.DoesNotExist:
            try:
                return base_qs.get(id=cleaned)
            except Exception:
                raise ResourceNotFoundError("Writer not found.")


class AdminWriterDetailView(APIView):
    """GET/PATCH/DELETE /api/v1/admin/writers/{lookup}/ (UUID or slug)"""
    permission_classes = [IsAdmin]

    def get(self, request, lookup):
        profile = _get_writer_profile_by_lookup(lookup)
        return success_response(data=AdminWriterSerializer(profile).data)

    def patch(self, request, lookup):
        profile = _get_writer_profile_by_lookup(lookup)
        serializer = AdminWriterSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Writer updated.")

    def delete(self, request, lookup):
        profile = _get_writer_profile_by_lookup(lookup)
        user = profile.user
        with transaction.atomic():
            # If the user is only a writer (not staff/admin), delete user which cascades cleanly
            if user and user.role == UserRole.WRITER and not user.is_staff and not user.is_superuser:
                user.delete()
            else:
                profile.delete()
        return success_response(message="Writer deleted successfully.")



class AdminWriterVerifyView(APIView):
    """POST /api/v1/admin/writers/{lookup}/verify/"""
    permission_classes = [IsAdmin]

    def post(self, request, lookup):
        profile = _get_writer_profile_by_lookup(lookup)
        WriterService.verify_writer(profile, request.user)
        return success_response(message="Writer verified successfully.")


class AdminWriterUnverifyView(APIView):
    """POST /api/v1/admin/writers/{lookup}/unverify/"""
    permission_classes = [IsAdmin]

    def post(self, request, lookup):
        profile = _get_writer_profile_by_lookup(lookup)
        WriterService.unverify_writer(profile, request.user)
        return success_response(message="Writer verification revoked.")


class AdminWriterActivateView(APIView):
    """POST /api/v1/admin/writers/{lookup}/activate/"""
    permission_classes = [IsAdmin]

    def post(self, request, lookup):
        profile = _get_writer_profile_by_lookup(lookup)
        WriterService.activate_writer(profile, request.user)
        return success_response(message="Writer activated.")


class AdminWriterDeactivateView(APIView):
    """POST /api/v1/admin/writers/{lookup}/deactivate/"""
    permission_classes = [IsAdmin]

    def post(self, request, lookup):
        profile = _get_writer_profile_by_lookup(lookup)
        WriterService.deactivate_writer(profile, request.user)
        return success_response(message="Writer deactivated.")


class AdminWriterInviteView(APIView):
    """POST /api/v1/admin/writers/invite/ or POST /api/v1/admin/writers/"""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            raise ServiceValidationError({"email": "This field is required."})

        full_name = request.data.get("full_name") or request.data.get("name") or email.split("@")[0].capitalize()
        name_parts = full_name.split(" ", 1)
        first_name = request.data.get("first_name") or name_parts[0]
        last_name = request.data.get("last_name") or (name_parts[1] if len(name_parts) > 1 else "")
        password = request.data.get("password")

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": UserRole.WRITER,
                    "is_email_verified": True,
                    "is_active": request.data.get("is_active", True),
                },
            )
            if created and password:
                user.set_password(password)
                user.save()
            elif not created:
                user.role = UserRole.WRITER
                user.is_email_verified = True
                if password:
                    user.set_password(password)
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
                user.save()

            profile, prof_created = WriterProfile.all_objects.get_or_create(
                user=user,
                defaults={
                    "slug": generate_unique_slug(WriterProfile, full_name or user.get_full_name()),
                    "gender": request.data.get("gender", "OTHER"),
                    "bio": request.data.get("bio", f"Writer profile for {full_name}"),
                    "profile_photo": request.data.get("profile_photo", ""),
                    "website_url": request.data.get("website_url", ""),
                    "facebook_url": request.data.get("facebook_url", ""),
                    "instagram_url": request.data.get("instagram_url", ""),
                    "x_url": request.data.get("x_url", ""),
                    "linkedin_url": request.data.get("linkedin_url", ""),
                    "youtube_url": request.data.get("youtube_url", ""),
                    "is_verified": request.data.get("is_verified", True),
                    "is_active": request.data.get("is_active", True),
                },
            )
            if not prof_created:
                # Update provided fields
                for field in [
                    "gender", "bio", "profile_photo", "website_url", "facebook_url",
                    "instagram_url", "x_url", "linkedin_url", "youtube_url",
                    "is_verified", "is_active",
                ]:
                    if field in request.data:
                        setattr(profile, field, request.data[field])
                profile.save()

        return created_response(
            data=AdminWriterSerializer(profile).data,
            message=f"Writer profile created successfully for {email}.",
        )
