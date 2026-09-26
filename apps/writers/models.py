"""
apps/writers — Writer Profile Model
Implements §9 WriterProfile schema.
"""
import uuid
from django.db import models
from django.conf import settings
from common.models import BaseModel, ActiveManager


class WriterProfile(BaseModel):
    """
    Writer profile linked to a User account.
    Only Admin can set is_verified per §9 rules.

    ⚠️ MANAGER BEHAVIOR:
        `WriterProfile.objects`     → ActiveManager (filters is_active=True by default)
        `WriterProfile.all_objects` → Standard Manager (returns all records including inactive)

    Admin views and background tasks requiring all writer records should use `WriterProfile.all_objects`.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="writer_profile",
    )
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    bio = models.TextField(blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other")],
        default="OTHER",
        blank=True,
    )
    profile_photo = models.URLField(blank=True)
    location = models.CharField(max_length=255, blank=True, default="India")
    author_title = models.CharField(max_length=255, blank=True, default="tossatale author")
    tagline = models.CharField(max_length=255, blank=True, default="Storyteller")
    website_url = models.URLField(blank=True)

    # Social links
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    x_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    # Verification — Admin only per §9 and §24
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_writers",
    )

    # Account status
    is_active = models.BooleanField(default=True, db_index=True)

    # Cached statistics (updated by background tasks)
    total_stories = models.PositiveIntegerField(default=0)
    total_published_stories = models.PositiveIntegerField(default=0)
    total_reads = models.BigIntegerField(default=0)
    total_likes = models.BigIntegerField(default=0)
    total_shares = models.BigIntegerField(default=0)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "writer_profiles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_verified"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"WriterProfile({self.name})"

    @property
    def name(self):
        if self.user:
            return self.user.get_full_name() or getattr(self.user, "display_name", "") or self.user.email.split("@")[0]
        return "Writer"

    @property
    def pen_name(self):
        return self.name

    # Domain helpers per §4.1
    @property
    def is_published(self):
        return self.is_active

    @property
    def can_be_edited(self):
        return self.is_active

    def get_social_links(self) -> dict:
        links = {}
        for field in ["website_url", "facebook_url", "instagram_url", "x_url", "linkedin_url", "youtube_url"]:
            val = getattr(self, field)
            if val:
                links[field] = val
        return links


class WriterSupport(models.Model):
    """
    Tracks reader support given to a writer.
    Enforces 1 support per user / IP / session per writer per day.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    writer = models.ForeignKey(
        WriterProfile,
        on_delete=models.CASCADE,
        related_name="supports",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="writer_supports",
        db_index=True,
    )
    session_id = models.CharField(max_length=255, blank=True, db_index=True)
    ip_hash = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "writer_supports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["writer", "created_at"]),
            models.Index(fields=["user", "writer", "created_at"]),
            models.Index(fields=["ip_hash", "writer", "created_at"]),
        ]

    def __str__(self):
        return f"WriterSupport({self.writer.slug}, user={self.user_id or self.ip_hash})"

