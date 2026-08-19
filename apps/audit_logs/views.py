"""
apps/audit_logs/views.py — Admin Audit Log View per §30 & §47
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from common.permissions import IsAdmin
from common.pagination import StandardResultsSetPagination
from common.responses import success_response
from apps.audit_logs.models import AuditLog


class AdminAuditLogListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = AuditLog.objects.select_related("actor").all()

        actor_param = request.query_params.get("actor")
        action_param = request.query_params.get("action")
        obj_type_param = request.query_params.get("object_type")
        obj_id_param = request.query_params.get("object_id")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if actor_param:
            queryset = queryset.filter(actor__email__icontains=actor_param)
        if action_param:
            queryset = queryset.filter(action=action_param.upper())
        if obj_type_param:
            queryset = queryset.filter(object_type__iexact=obj_type_param)
        if obj_id_param:
            queryset = queryset.filter(object_id=obj_id_param)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        data = [
            {
                "id": str(log.id),
                "actor_email": log.actor.email if log.actor else "System",
                "action": log.action,
                "object_type": log.object_type,
                "object_id": log.object_id,
                "object_repr": log.object_repr,
                "changes": log.changes,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
            }
            for log in page
        ]
        return paginator.get_paginated_response(data)
