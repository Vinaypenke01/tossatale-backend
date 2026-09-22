"""
apps/notifications/views.py — Views for Notifications API
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import ProgrammingError, OperationalError

from common.responses import success_response
from common.pagination import StandardResultsSetPagination
from common.exceptions import ResourceNotFoundError
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        try:
            qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")
            unread_only = request.query_params.get("unread_only", "").lower() in ["true", "1"]
            if unread_only:
                qs = qs.filter(is_read=False)

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(qs, request)
            serializer = NotificationSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except (ProgrammingError, OperationalError):
            return success_response(data={"count": 0, "next": None, "previous": None, "results": []})


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        except (ProgrammingError, OperationalError):
            count = 0
        return success_response(data={"unread_count": count})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notif = Notification.objects.filter(id=pk, recipient=request.user).first()
        except (ProgrammingError, OperationalError):
            notif = None

        if not notif:
            raise ResourceNotFoundError("Notification not found.")

        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save(update_fields=["is_read", "read_at"])
        return success_response(
            data=NotificationSerializer(notif).data,
            message="Notification marked as read."
        )


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            count = Notification.objects.filter(
                recipient=request.user, is_read=False
            ).update(is_read=True, read_at=timezone.now())
        except (ProgrammingError, OperationalError):
            count = 0

        return success_response(
            data={"marked_read": count},
            message=f"{count} notifications marked as read."
        )


class NotificationClearAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            count, _ = Notification.objects.filter(recipient=request.user).delete()
        except (ProgrammingError, OperationalError):
            count = 0

        return success_response(
            data={"cleared_count": count},
            message=f"{count} notifications cleared."
        )

    def delete(self, request):
        return self.post(request)


class NotificationDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            notif = Notification.objects.filter(id=pk, recipient=request.user).first()
        except (ProgrammingError, OperationalError):
            notif = None

        if not notif:
            raise ResourceNotFoundError("Notification not found.")

        notif.delete()
        return success_response(message="Notification dismissed.")

