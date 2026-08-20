"""Auth URL routes — /api/v1/auth/"""
from django.urls import path
from apps.accounts.views import (
    LoginView,
    GoogleLoginView,
    RefreshTokenView,
    LogoutView,
    LogoutAllView,
    ForgotPasswordView,
    PasswordSendOTPView,
    PasswordResetWithOTPView,
    ResetPasswordView,
    MeView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("google/", GoogleLoginView.as_view(), name="auth-google"),
    path("refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("logout-all/", LogoutAllView.as_view(), name="auth-logout-all"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("password/send-otp/", PasswordSendOTPView.as_view(), name="auth-password-send-otp"),
    path("password/reset-with-otp/", PasswordResetWithOTPView.as_view(), name="auth-password-reset-with-otp"),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("me/", MeView.as_view(), name="auth-me"),
]
