"""
apps/accounts — User, UserSession, NotificationPreference Models
Implements the full User model per §8.
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from common.constants import UserRole, AuthProvider


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", UserRole.USER)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_writer(self, email, password=None, **extra_fields):
        extra_fields["role"] = UserRole.WRITER
        return self.create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields["role"] = UserRole.ADMIN
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["is_email_verified"] = True
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model per §8.1.
    UUID primary key, role-based, supports Google OAuth.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core identity
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    display_name = models.CharField(max_length=150, blank=True)

    # Role
    role = models.CharField(
        max_length=20,
        choices=UserRole.CHOICES,
        default=UserRole.USER,
        db_index=True,
    )

    # Profile
    profile_photo = models.URLField(blank=True)

    # Auth provider
    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.CHOICES,
        default=AuthProvider.EMAIL,
    )
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    # Status flags
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)

    # Activity tracking
    last_activity_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_short_name(self):
        return self.first_name or self.email.split("@")[0]

    # Small domain-level helper properties per §4.1
    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_writer(self):
        return self.role == UserRole.WRITER

    @property
    def is_reader(self):
        return self.role == UserRole.USER


class UserSession(models.Model):
    """
    Tracks active user sessions for multi-device logout and suspicious activity detection.
    Implements §8.2.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    refresh_token_hash = models.CharField(max_length=255, db_index=True)
    device_name = models.CharField(max_length=200, blank=True)
    browser = models.CharField(max_length=200, blank=True)
    operating_system = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_used_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session({self.user.email}, {self.device_name or 'unknown device'})"


class NotificationPreference(models.Model):
    """
    One-to-one notification preferences for each user per §8.3.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    email_notifications = models.BooleanField(default=True)
    story_approval_notifications = models.BooleanField(default=True)
    story_rejection_notifications = models.BooleanField(default=True)
    platform_update_notifications = models.BooleanField(default=True)
    newsletter_notifications = models.BooleanField(default=True)
    new_story_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_preferences"

    def __str__(self):
        return f"NotificationPrefs({self.user.email})"
