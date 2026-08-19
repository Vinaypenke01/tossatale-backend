"""
apps/newsletters/views.py — Newsletter Subscription & Double Opt-in Views
"""
import csv
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from common.permissions import IsAdmin
from common.responses import success_response, created_response
from common.exceptions import ServiceValidationError
from apps.newsletters.models import NewsletterSubscription


class SubscribeNewsletterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            raise ServiceValidationError("Email address is required.")

        sub, created = NewsletterSubscription.objects.get_or_create(
            email=email,
            defaults={"is_verified": False, "verification_sent_at": timezone.now()}
        )

        if not created and sub.is_verified:
            return success_response(message="You are already subscribed to the Tossatale newsletter!")

        sub.verification_sent_at = timezone.now()
        sub.save()

        # In production Celery task sends double opt-in email with verification token
        verify_url = f"/api/v1/public/newsletter/verify/?token={sub.verification_token}"

        return created_response(
            data={"email": sub.email, "verify_url": verify_url},
            message="Verification email sent! Please check your inbox to confirm your subscription."
        )


class VerifyNewsletterView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            raise ServiceValidationError("Verification token is required.")

        sub = get_object_or_404(NewsletterSubscription, verification_token=token)
        sub.is_verified = True
        sub.verified_at = timezone.now()
        sub.save()

        return success_response(message="Your newsletter subscription has been confirmed! Welcome to Tossatale.")


class UnsubscribeNewsletterView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            raise ServiceValidationError("Unsubscribe token is required.")

        sub = get_object_or_404(NewsletterSubscription, unsubscribe_token=token)
        sub.unsubscribed_at = timezone.now()
        sub.is_verified = False
        sub.save()

        return success_response(message="You have been unsubscribed from the Tossatale newsletter.")


class AdminExportNewsletterCSVView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="verified_subscribers.csv"'

        writer = csv.writer(response)
        writer.writerow(["Email", "Verified At", "Subscribed Date"])

        subs = NewsletterSubscription.objects.filter(is_verified=True, unsubscribed_at__isnull=True)
        for s in subs:
            writer.writerow([s.email, s.verified_at, s.created_at])

        return response
