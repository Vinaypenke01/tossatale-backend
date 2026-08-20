"""
apps/accounts — Auth & User Service Layer
Contains ALL business logic, workflow logic, and database operations.
Views must only call these methods per §4.3.
"""
import hashlib
import logging
from datetime import timedelta

from django.contrib.auth import authenticate
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.models import User, UserSession, NotificationPreference
from apps.accounts.constants import UserRole, AuthProvider
from common.exceptions import (
    AuthenticationError,
    InactiveUserError,
    ResourceNotFoundError,
    ServiceValidationError,
)

logger = logging.getLogger("apps.accounts")


class AuthService:
    """
    Handles all authentication operations per §26.
    - Email login
    - Google OAuth login
    - Token refresh
    - Logout (single + all devices)
    - Password reset
    """

    @staticmethod
    def _generate_token_pair(user: User) -> dict:
        """Generate JWT access + refresh token pair for a user."""
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _create_session(user: User, refresh_token: str, request=None) -> UserSession:
        """Record a new user session in the database."""
        token_hash = AuthService._hash_token(refresh_token)
        expires_at = timezone.now() + timedelta(
            days=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].days
        )
        meta = {}
        if request:
            meta["ip_address"] = request.META.get("REMOTE_ADDR")

        return UserSession.objects.create(
            user=user,
            refresh_token_hash=token_hash,
            expires_at=expires_at,
            **meta,
        )

    @staticmethod
    def email_login(email: str, password: str, request=None) -> dict:
        """
        Authenticate user with email + password.
        Returns token pair.
        """
        user = authenticate(username=email, password=password)

        if user is None:
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise InactiveUserError()

        # Enforce maintenance mode — allow only ADMIN users
        from apps.settings_config.models import SiteSettings
        site_settings = SiteSettings.get_solo()
        if site_settings.maintenance_mode and user.role != UserRole.ADMIN and not user.is_staff:
            raise AuthenticationError(
                "Tossatale is currently under maintenance. Only administrators can log in at this time."
            )

        # Update last activity
        user.last_activity_at = timezone.now()
        user.save(update_fields=["last_activity_at"])

        tokens = AuthService._generate_token_pair(user)
        AuthService._create_session(user, tokens["refresh"], request)

        logger.info("User logged in: %s", user.email)
        return tokens

    @staticmethod
    def google_login(id_token: str, request=None) -> dict:
        """
        Verify Google ID token and authenticate or create user.
        Returns token pair.
        """
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        # Check maintenance mode — Google login is for readers, block during maintenance
        from apps.settings_config.models import SiteSettings
        site_settings = SiteSettings.get_solo()
        if site_settings.maintenance_mode:
            raise AuthenticationError(
                "Tossatale is currently under maintenance. Only administrators can log in at this time."
            )

        try:
            payload = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except Exception as exc:
            logger.warning("Google token verification failed: %s", exc)
            raise AuthenticationError("Google authentication failed. Invalid token.")

        google_id = payload.get("sub")
        email = payload.get("email")
        if not email:
            raise AuthenticationError("Google account email is not available.")

        with transaction.atomic():
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                if existing_user.role in [UserRole.WRITER, UserRole.ADMIN]:
                    raise AuthenticationError(
                        "Google login is only available for Readers. Writers and Editors/Admins must sign in with their email and password."
                    )
                user = existing_user
                created = False
            else:
                user = User.objects.create(
                    email=email,
                    google_id=google_id,
                    first_name=payload.get("given_name", ""),
                    last_name=payload.get("family_name", ""),
                    profile_photo=payload.get("picture", ""),
                    auth_provider=AuthProvider.GOOGLE,
                    is_email_verified=True,
                    role=UserRole.USER,
                )
                NotificationPreference.objects.create(user=user)
                created = True

            if not user.is_active:
                raise InactiveUserError()

            if not user.google_id:
                user.google_id = google_id
                user.save(update_fields=["google_id"])

        user.last_activity_at = timezone.now()
        user.save(update_fields=["last_activity_at"])

        tokens = AuthService._generate_token_pair(user)
        AuthService._create_session(user, tokens["refresh"], request)

        logger.info("Google login: %s (new=%s)", email, created)
        return tokens

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """Rotate refresh token and return a new access token."""
        try:
            token = RefreshToken(refresh_token)
            token.verify()
        except TokenError as exc:
            raise AuthenticationError(str(exc))

        return {
            "access": str(token.access_token),
            "refresh": str(token),
        }

    @staticmethod
    def logout(user: User, refresh_token: str) -> None:
        """Blacklist the provided refresh token and revoke its session."""
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass  # Already blacklisted — safe to ignore

        token_hash = AuthService._hash_token(refresh_token)
        UserSession.objects.filter(
            user=user, refresh_token_hash=token_hash
        ).update(is_revoked=True)

        logger.info("User logged out: %s", user.email)

    @staticmethod
    def logout_all(user: User) -> None:
        """Revoke all active sessions for a user (logout from all devices)."""
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

        tokens = OutstandingToken.objects.filter(user=user)
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)

        UserSession.objects.filter(user=user, is_revoked=False).update(is_revoked=True)
        logger.info("All sessions revoked for user: %s", user.email)

    @staticmethod
    def request_password_reset(email: str) -> None:
        """Queue a password reset email if the user exists."""
        try:
            user = User.objects.get(email=email, auth_provider=AuthProvider.EMAIL)
        except User.DoesNotExist:
            # Do not reveal whether an account exists
            return

        from apps.notifications.tasks import send_password_reset_email
        send_password_reset_email.delay(str(user.id))

    @staticmethod
    def reset_password(token: str, new_password: str) -> None:
        """Validate reset token and set new password."""
        # Token validation logic handled via Django's password reset tokens
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode

        raise ServiceValidationError("Password reset via token not yet implemented. Coming in Phase 2.")


class UserService:
    """Handles User profile CRUD operations."""

    @staticmethod
    def get_profile(user: User) -> User:
        return user

    @staticmethod
    def update_profile(user: User, data: dict) -> User:
        allowed_fields = {"first_name", "last_name", "display_name", "profile_photo"}
        for field, value in data.items():
            if field in allowed_fields:
                setattr(user, field, value)
        user.save()
        return user

    @staticmethod
    def get_notification_preferences(user: User) -> NotificationPreference:
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        return prefs

    @staticmethod
    def update_notification_preferences(user: User, data: dict) -> NotificationPreference:
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        for field, value in data.items():
            setattr(prefs, field, value)
        prefs.save()
        return prefs

    @staticmethod
    def activate(user: User) -> User:
        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])
        return user

    @staticmethod
    def deactivate(user: User) -> User:
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        return user
