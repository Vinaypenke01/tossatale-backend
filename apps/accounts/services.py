"""
apps/accounts — Auth & User Service Layer
Contains ALL business logic, workflow logic, and database operations.
Views must only call these methods per §4.3.
"""
import hashlib
import logging
from datetime import timedelta
from typing import Any

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
    WriterGoogleAuthBlockedError,
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
    def register(data: dict, request=None) -> dict:
        """
        Register a new reader or writer account.
        Returns token pair + user profile data.
        """
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        role_str = str(data.get("role", "USER")).upper()

        if not email or not password:
            raise ServiceValidationError("Email and password are required.")

        if len(password) < 8:
            raise ServiceValidationError("Password must be at least 8 characters long.")

        if User.objects.filter(email__iexact=email).exists():
            raise ServiceValidationError("An account with this email address already exists.")

        # Determine user role
        role = UserRole.WRITER if role_str in ["WRITER", "AUTHOR"] else UserRole.USER

        consent = bool(data.get("consent") or data.get("terms_accepted"))
        if role == UserRole.WRITER and not consent:
            raise ServiceValidationError("You must agree to the Terms of Service, Privacy Policy, and Writer Guidelines to register.")

        # Enforce maintenance mode — block registrations during maintenance
        from apps.settings_config.models import SiteSettings
        site_settings = SiteSettings.get_solo()
        if site_settings.maintenance_mode:
            raise AuthenticationError(
                "Tossatale is currently under maintenance. New registrations are temporarily disabled."
            )

        now = timezone.now()
        with transaction.atomic():  # type: ignore[attr-defined]
            user = User.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                display_name=f"{first_name} {last_name}".strip() or email.split("@")[0],
                role=role,
                auth_provider=AuthProvider.EMAIL,
                is_active=True,
                is_email_verified=False,
                consent_given=consent,
                consent_given_at=now if consent else None,
                terms_accepted=consent,
                terms_accepted_at=now if consent else None,
            )
            user.set_password(password)
            user.save()

            NotificationPreference.objects.create(user=user)

            if role == UserRole.WRITER:
                from apps.writers.services import WriterService
                WriterService.create_writer(user, {
                    "bio": data.get("bio", ""),
                    "website_url": data.get("website_url", ""),
                })

        user.last_activity_at = timezone.now()
        user.save(update_fields=["last_activity_at"])

        # If registering as a writer, enforce email OTP verification
        if role == UserRole.WRITER:
            import random
            from django.core.cache import cache
            from common.services.email_service import EmailService

            otp = f"{random.randint(100000, 999999)}"
            cache_key = f"reg_otp_{email}"
            cache.set(cache_key, otp, 600)  # 10 minutes

            try:
                EmailService.send_registration_otp_email(
                    to_email=user.email,
                    otp_code=otp,
                    user_name=user.first_name or "Storyteller",
                )
            except Exception as exc:
                logger.warning("Failed to send writer registration OTP email to %s: %s", user.email, exc)

            logger.info("Writer registered pending OTP verification: %s", user.email)
            return {
                "requires_otp": True,
                "email": user.email,
                "role": user.role,
                "message": "Writer account registered. Please enter the 6-digit verification code sent to your email.",
            }

        tokens = AuthService._generate_token_pair(user)
        AuthService._create_session(user, tokens["refresh"], request)

        from apps.accounts.serializers import UserMeSerializer
        logger.info("User registered: %s (role=%s)", user.email, user.role)
        return {
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "user": UserMeSerializer(user).data,
        }

    @staticmethod
    def verify_registration_otp(email: str, otp: str, request=None) -> dict:
        """
        Verify the 6-digit OTP sent to a newly registered writer.
        On success, marks email verified, logs them in, and returns JWT tokens.
        """
        import logging
        from django.core.cache import cache

        email = (email or "").strip().lower()
        otp_clean = otp.strip() if otp else ""

        if not email or not otp_clean:
            raise ServiceValidationError("Email and 6-digit verification code are required.")

        cache_key = f"reg_otp_{email}"
        cached_otp = cache.get(cache_key)

        if not cached_otp or str(cached_otp).strip() != otp_clean:
            raise ServiceValidationError("Invalid or expired verification code. Please check the code or request a new one.")

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ServiceValidationError("Account not found.")

        user.is_email_verified = True
        user.last_activity_at = timezone.now()
        user.save(update_fields=["is_email_verified", "last_activity_at"])

        cache.delete(cache_key)

        tokens = AuthService._generate_token_pair(user)
        AuthService._create_session(user, tokens["refresh"], request)

        from apps.accounts.serializers import UserMeSerializer
        logger.info("Writer email verified & logged in: %s", user.email)
        return {
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "user": UserMeSerializer(user).data,
            "message": "Writer account activated successfully!",
        }

    @staticmethod
    def resend_registration_otp(email: str) -> dict:
        """
        Resend a fresh 6-digit registration OTP to the writer's email.
        """
        import random
        from django.core.cache import cache
        from common.services.email_service import EmailService

        email = email.strip().lower()
        if not email:
            raise ServiceValidationError("Email address is required.")

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return {"message": f"If an account with {email} exists, an activation code has been sent."}

        if user.is_email_verified:
            return {"message": "Account is already verified. You can sign in directly."}

        otp = f"{random.randint(100000, 999999)}"
        cache_key = f"reg_otp_{email}"
        cache.set(cache_key, otp, 600)  # 10 minutes

        try:
            EmailService.send_registration_otp_email(
                to_email=user.email,
                otp_code=otp,
                user_name=user.first_name or "Storyteller",
            )
        except Exception as exc:
            logger.warning("Failed to resend registration OTP email: %s", exc)

        return {"message": f"Verification code sent to {email}"}

    @staticmethod
    def email_login(email: str, password: str, request=None) -> dict:
        """
        Authenticate user with email + password.
        Validates whether writer accounts have completed OTP verification.
        Returns token pair.
        """
        from common.exceptions import EmailNotVerifiedError

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

        # Enforce OTP validation for writer registration
        if user.role == UserRole.WRITER and not user.is_email_verified:
            # Automatically dispatch a fresh OTP so user can verify immediately
            import random
            from django.core.cache import cache
            from common.services.email_service import EmailService

            otp = f"{random.randint(100000, 999999)}"
            cache_key = f"reg_otp_{user.email.lower()}"
            cache.set(cache_key, otp, 600)

            try:
                EmailService.send_registration_otp_email(
                    to_email=user.email,
                    otp_code=otp,
                    user_name=user.first_name or "Storyteller",
                )
            except Exception as exc:
                logger.warning("Failed to dispatch registration OTP on login: %s", exc)

            raise EmailNotVerifiedError(
                "Your writer account requires email verification. A 6-digit activation code has been sent to your email."
            )

        # Update last activity
        user.last_activity_at = timezone.now()
        user.save(update_fields=["last_activity_at"])

        tokens = AuthService._generate_token_pair(user)
        AuthService._create_session(user, tokens["refresh"], request)

        from apps.accounts.serializers import UserMeSerializer
        logger.info("User logged in: %s", user.email)
        return {
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "user": UserMeSerializer(user).data,
        }

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

        with transaction.atomic():  # type: ignore[attr-defined]
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                if existing_user.role in [UserRole.WRITER, UserRole.ADMIN]:
                    raise WriterGoogleAuthBlockedError(
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

    verify_google_token = google_login

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """Rotate refresh token and return a new access token."""
        try:
            token = RefreshToken(refresh_token)  # type: ignore[arg-type]
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
            token = RefreshToken(refresh_token)  # type: ignore[arg-type]
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
        send_password_reset_email.delay(str(user.id))  # type: ignore[union-attr]

    @staticmethod
    def reset_password(token: str, new_password: str) -> None:
        """Validate reset token and set new password."""
        # Token validation logic handled via Django's password reset tokens
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode

        raise ServiceValidationError("Password reset via token not yet implemented. Coming in Phase 2.")

    @staticmethod
    def upgrade_reader_to_writer(user: Any, data: dict, request=None) -> dict:
        """
        Migrate an existing Reader account (role == USER) into a Writer account.
        - Mandatory pen_name
        - Mandatory password (especially for Google-authenticated readers who have no password)
        - Creates WriterProfile
        - Promotes user.role to WRITER
        - Returns fresh token pair + updated user profile
        """
        if user.role != UserRole.USER:
            if user.role == UserRole.WRITER:
                raise ServiceValidationError("This account is already registered as a Writer.")
            raise ServiceValidationError("Only Reader accounts can be upgraded to Writer.")

        pen_name = (data.get("pen_name") or "").strip()
        if not pen_name:
            raise ServiceValidationError("Pen Name is required to create your Writer account.")

        password = data.get("password") or ""
        if not password or len(password) < 8:
            raise ServiceValidationError("A password of at least 8 characters is required for your Writer account.")

        confirm_migration = bool(data.get("confirm_reader_migration"))
        if not confirm_migration:
            raise ServiceValidationError("You must confirm that your reader account will be converted into a writer account.")

        from apps.writers.models import WriterProfile
        from common.utils import generate_unique_slug

        slug = generate_unique_slug(WriterProfile, pen_name)

        with transaction.atomic():  # type: ignore[attr-defined]
            # Update user password and credentials
            user.set_password(password)
            user.role = UserRole.WRITER
            user.display_name = pen_name
            name_parts = pen_name.split(" ", 1)
            if not user.first_name:
                user.first_name = name_parts[0]
            if len(name_parts) > 1 and not user.last_name:
                user.last_name = name_parts[1]
            user.terms_accepted = True
            user.terms_accepted_at = timezone.now()
            user.is_email_verified = True  # Already verified as reader
            user.save()

            # Create WriterProfile
            profile, created = WriterProfile.all_objects.get_or_create(
                user=user,
                defaults={
                    "slug": slug,
                    "bio": (data.get("bio") or "").strip(),
                    "gender": data.get("gender", "OTHER"),
                    "is_active": True,
                }
            )
            # If profile existed but was inactive, reactivate it
            if not created and not profile.is_active:
                profile.is_active = True
                profile.slug = slug
                profile.save(update_fields=["is_active", "slug"])

        tokens = AuthService._generate_token_pair(user)
        AuthService._create_session(user, tokens["refresh"], request)

        from apps.accounts.serializers import UserMeSerializer
        user_data = UserMeSerializer(user).data
        user_data["writer_profile"] = {
            "slug": profile.slug,
            "pen_name": pen_name,
        }

        logger.info("Reader %s successfully upgraded to Writer (slug=%s)", user.email, slug)

        return {
            "tokens": tokens,
            "user": user_data,
            "message": "Account successfully upgraded to Writer! Welcome to tossatale Writer Studio.",
            "redirect_url": "/writer",
        }

    @staticmethod
    def migrate_reader_credentials(data: dict, request=None) -> dict:
        """
        For a logged-out reader who wants to migrate to writer.
        Takes email, current password, pen_name, new_password, and confirm_reader_migration.
        """
        email = (data.get("email") or "").strip().lower()
        current_password = data.get("current_password") or ""
        pen_name = (data.get("pen_name") or "").strip()
        new_password = data.get("new_password") or current_password
        confirm_migration = bool(data.get("confirm_reader_migration"))

        if not email or not current_password:
            raise ServiceValidationError("Email and current reader password are required.")

        user = authenticate(request=request, username=email, password=current_password)
        if not user:
            raise AuthenticationError("Invalid email or password.")

        return AuthService.upgrade_reader_to_writer(
            user=user,
            data={
                "pen_name": pen_name,
                "password": new_password,
                "bio": data.get("bio", ""),
                "gender": data.get("gender", "OTHER"),
                "confirm_reader_migration": confirm_migration,
            },
            request=request
        )


class UserService:
    """Handles User profile CRUD operations."""

    @staticmethod
    def get_profile(user: User) -> User:
        return user

    @staticmethod
    def update_profile(user: User, data: dict) -> User:
        allowed_fields = {"first_name", "last_name", "display_name", "profile_photo"}
        changed = []
        for field, value in data.items():
            if field in allowed_fields and getattr(user, field) != value:
                setattr(user, field, value)
                changed.append(field)
        user.save()

        # Update associated WriterProfile if exists, or create for admin
        raw_slug = data.get("writer_slug", "")
        clean_slug = str(raw_slug).strip().lower().lstrip("@") if raw_slug else ""

        if hasattr(user, "writer_profile") and user.writer_profile:
            wp = user.writer_profile
            wp_changed = False
            if "bio" in data and wp.bio != data["bio"]:
                wp.bio = data["bio"]
                wp_changed = True
            if "writer_bio" in data and wp.bio != data["writer_bio"]:
                wp.bio = data["writer_bio"]
                wp_changed = True
            if clean_slug and wp.slug != clean_slug:
                from common.utils import generate_unique_slug
                from django.utils.text import slugify
                base_slug = str(slugify(clean_slug) or "writer")
                final_slug = generate_unique_slug(wp.__class__, base_slug, instance_id=wp.id)
                wp.slug = final_slug
                wp_changed = True
                changed.append("writer_slug")
            if wp_changed:
                wp.save()
                changed.append("bio")
        elif getattr(user, "role", "") in ["ADMIN", "WRITER"] and (clean_slug or data.get("bio") or data.get("writer_bio")):
            from apps.writers.models import WriterProfile
            from common.utils import generate_unique_slug
            from django.utils.text import slugify
            base_title = clean_slug or user.get_full_name() or user.display_name or user.email.split("@")[0]
            base_slug = str(slugify(str(base_title)) or "writer")
            final_slug = generate_unique_slug(WriterProfile, base_slug)
            WriterProfile.objects.create(
                user=user,
                slug=final_slug,
                bio=data.get("bio", "") or data.get("writer_bio", ""),
                is_active=True,
            )
            changed.append("writer_profile_created")

        if getattr(user, "role", "") == "ADMIN" or getattr(user, "is_staff", False):
            from apps.audit_logs.services import AuditLogService
            from common.constants import AuditAction
            AuditLogService.log(
                actor=user,
                action=AuditAction.UPDATE,
                obj=user,
                changes={"updated_fields": changed or list(data.keys())},
            )

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
