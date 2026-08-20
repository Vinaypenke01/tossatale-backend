"""
apps/accounts — Auth & User Views
Views handle: authentication, permissions, query params, calling services, and returning responses.
No direct database operations per §4.4.
"""
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.serializers import (
    AdminUserDetailSerializer,
    AdminUserListSerializer,
    ForgotPasswordSerializer,
    GoogleLoginSerializer,
    LoginSerializer,
    LogoutSerializer,
    NotificationPreferenceSerializer,
    ResetPasswordSerializer,
    UserMeSerializer,
    UserProfileUpdateSerializer,
)
from apps.accounts.services import AuthService, UserService
from common.exceptions import ResourceNotFoundError
from common.pagination import StandardPagination
from common.permissions import IsAdmin
from common.responses import created_response, no_content_response, success_response

User = get_user_model()


# ──────────────────────────────────────────────────────────────────────────────
# Authentication Views
# ──────────────────────────────────────────────────────────────────────────────

class LoginView(APIView):
    """POST /api/v1/auth/login/"""
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = AuthService.email_login(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            request=request,
        )
        return success_response(data=tokens, message="Login successful.")


class GoogleLoginView(APIView):
    """POST /api/v1/auth/google/"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = AuthService.google_login(
            id_token=serializer.validated_data["id_token"],
            request=request,
        )
        return success_response(data=tokens, message="Google login successful.")


class RefreshTokenView(APIView):
    """POST /api/v1/auth/refresh/"""
    permission_classes = [AllowAny]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            from common.exceptions import ServiceValidationError
            raise ServiceValidationError({"refresh": "This field is required."})
        tokens = AuthService.refresh_access_token(refresh)
        return success_response(data=tokens, message="Token refreshed.")


class LogoutView(APIView):
    """POST /api/v1/auth/logout/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.logout(request.user, serializer.validated_data["refresh"])
        return no_content_response()


class LogoutAllView(APIView):
    """POST /api/v1/auth/logout-all/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        AuthService.logout_all(request.user)
        return no_content_response()


class ForgotPasswordView(APIView):
    """POST /api/v1/auth/forgot-password/"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.request_password_reset(serializer.validated_data["email"])
        return success_response(message="If that email exists, a reset link has been sent.")


class PasswordSendOTPView(APIView):
    """POST /api/v1/auth/password/send-otp/"""
    permission_classes = [AllowAny]

    def post(self, request):
        import random
        from django.core.cache import cache
        from django.core.mail import send_mail
        from django.conf import settings

        email = request.data.get("email", "").strip()
        if not email and request.user.is_authenticated:
            email = request.user.email

        if not email:
            return success_response(message="Please provide an email address.")

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            # Do not reveal whether user exists
            return success_response(message="If that email exists, an OTP has been sent.")

        otp = f"{random.randint(100000, 999999)}"
        cache_key = f"pwd_otp_{email.lower()}"
        cache.set(cache_key, otp, 600)  # 10 minutes

        # Dispatch branded HTML email via Resend API
        try:
            from common.services.email_service import EmailService
            user_name = user.first_name or user.display_name or "Storyteller"
            EmailService.send_password_reset_otp_email(
                to_email=email,
                otp_code=otp,
                user_name=user_name,
            )
        except Exception as exc:
            import logging
            logging.getLogger("apps.accounts").warning("Failed to dispatch OTP email: %s", exc)

        data = {"message": f"Verification OTP sent to {email}"}
        # In DEBUG / local environment, return debug_otp for testing
        if getattr(settings, "DEBUG", True):
            data["debug_otp"] = otp

        return success_response(data=data, message=f"Verification OTP sent to {email}")


class PasswordResetWithOTPView(APIView):
    """POST /api/v1/auth/password/reset-with-otp/"""
    permission_classes = [AllowAny]

    def post(self, request):
        from django.core.cache import cache
        from common.exceptions import ServiceValidationError

        email = request.data.get("email", "").strip()
        if not email and request.user.is_authenticated:
            email = request.user.email

        otp = request.data.get("otp", "").strip()
        new_password = request.data.get("new_password", "").strip()

        if not email or not otp or not new_password:
            raise ServiceValidationError("Email, OTP verification code, and new password are required.")

        if len(new_password) < 8:
            raise ServiceValidationError("Password must be at least 8 characters long.")

        cache_key = f"pwd_otp_{email.lower()}"
        cached_otp = cache.get(cache_key)

        if not cached_otp or str(cached_otp).strip() != str(otp).strip():
            raise ServiceValidationError("Invalid or expired OTP verification code. Please request a new one.")

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise ServiceValidationError("Account not found.")

        user.set_password(new_password)
        user.save()
        cache.delete(cache_key)

        return success_response(message="Password has been updated successfully. You can now sign in with your new password.")


class ResetPasswordView(APIView):
    """POST /api/v1/auth/reset-password/"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.reset_password(
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )
        return success_response(message="Password reset successfully.")


class MeView(APIView):
    """GET /api/v1/auth/me/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return success_response(data=serializer.data, message="Profile retrieved.")


# ──────────────────────────────────────────────────────────────────────────────
# Reader (User) Views
# ──────────────────────────────────────────────────────────────────────────────

class UserProfileView(APIView):
    """GET/PATCH /api/v1/user/profile/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return success_response(data=serializer.data)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = UserService.update_profile(request.user, serializer.validated_data)
        return success_response(
            data=UserMeSerializer(user).data,
            message="Profile updated.",
        )


class NotificationPreferenceView(APIView):
    """GET/PATCH /api/v1/user/notification-preferences/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs = UserService.get_notification_preferences(request.user)
        serializer = NotificationPreferenceSerializer(prefs)
        return success_response(data=serializer.data)

    def patch(self, request):
        serializer = NotificationPreferenceSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        prefs = UserService.update_notification_preferences(
            request.user, serializer.validated_data
        )
        return success_response(
            data=NotificationPreferenceSerializer(prefs).data,
            message="Preferences updated.",
        )


# ──────────────────────────────────────────────────────────────────────────────
# Admin User Management Views
# ──────────────────────────────────────────────────────────────────────────────

class AdminUserListView(generics.ListAPIView):
    """GET /api/v1/admin/users/"""
    permission_classes = [IsAdmin]
    serializer_class = AdminUserListSerializer
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["role", "is_active", "is_email_verified", "auth_provider"]
    search_fields = ["email", "first_name", "last_name", "display_name"]
    ordering_fields = ["created_at", "last_login", "email"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return User.objects.all()


class AdminUserDetailView(APIView):
    """GET/PATCH /api/v1/admin/users/{id}/"""
    permission_classes = [IsAdmin]

    def _get_user(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise ResourceNotFoundError("User not found.")

    def get(self, request, pk):
        user = self._get_user(pk)
        serializer = AdminUserDetailSerializer(user)
        return success_response(data=serializer.data)

    def patch(self, request, pk):
        user = self._get_user(pk)
        serializer = AdminUserDetailSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="User updated.")


class AdminUserActivateView(APIView):
    """POST /api/v1/admin/users/{id}/activate/"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise ResourceNotFoundError("User not found.")
        UserService.activate(user)
        return success_response(message="User activated.")


class AdminUserDisableView(APIView):
    """POST /api/v1/admin/users/{id}/disable/"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            raise ResourceNotFoundError("User not found.")
        UserService.deactivate(user)
        return success_response(message="User disabled.")
