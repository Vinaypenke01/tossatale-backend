"""
apps/contacts/views.py — Contact Form Views and Admin Management per §21
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils import timezone

from common.permissions import IsAdmin
from common.responses import success_response, created_response
from common.exceptions import ServiceValidationError
from common.pagination import StandardResultsSetPagination
from apps.contacts.models import ContactMessage


class PublicContactFormView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ip = request.META.get("REMOTE_ADDR", "unknown")
        cache_key = f"contact_rate_{ip}"
        submissions = cache.get(cache_key, 0)

        if submissions >= 3:
            raise ServiceValidationError("Maximum submission limit reached (3 per hour). Please try again later.")

        name = request.data.get("name", "").strip()
        email = request.data.get("email", "").strip()
        subject = request.data.get("subject", "").strip()
        message = request.data.get("message", "").strip()

        if not name or not email or not message:
            raise ServiceValidationError("Name, email, and message are required.")

        msg = ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject or "General Inquiry",
            message=message,
            ip_address=ip,
            status="NEW",
        )

        # Update rate count in Redis with 1-hour expiration (3600 seconds)
        cache.set(cache_key, submissions + 1, 3600)

        # Dispatch confirmation email via Resend
        try:
            from common.services.email_service import EmailService
            EmailService.send_contact_confirmation_email(
                to_email=email,
                sender_name=name,
                inquiry_type=subject or "General Inquiry",
            )
        except Exception as exc:
            import logging
            logging.getLogger("apps.contacts").warning("Failed to send contact confirmation: %s", exc)

        return created_response(
            data={"id": str(msg.id)},
            message="Thank you for contacting Tossatale! We will get back to you shortly."
        )


class AdminContactMessageListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = ContactMessage.objects.all()
        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.upper())

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        data = [
            {
                "id": str(m.id),
                "name": m.name,
                "email": m.email,
                "subject": m.subject,
                "message": m.message,
                "status": m.status,
                "created_at": m.created_at,
            }
            for m in page
        ]
        return paginator.get_paginated_response(data)


class AdminContactMessageResolveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        msg = get_object_or_404(ContactMessage, pk=pk)
        msg.status = "RESOLVED"
        msg.resolved_by = request.user
        msg.resolved_at = timezone.now()
        msg.save()
        return success_response(message="Contact message marked as RESOLVED.")
