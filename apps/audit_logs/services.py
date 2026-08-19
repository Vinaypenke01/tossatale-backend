"""
apps/audit_logs/services.py — AuditLogService per §47
"""
from apps.audit_logs.models import AuditLog


class AuditLogService:

    @classmethod
    def log(cls, actor, action: str, obj, changes: dict = None, request=None) -> AuditLog:
        """
        Creates an audit log entry for administrative actions.
        Must be invoked from service methods per §4.3.
        """
        object_type = obj.__class__.__name__
        object_id = str(getattr(obj, "pk", getattr(obj, "id", "")))
        object_repr = str(obj)[:255]

        ip_address = None
        user_agent = ""
        if request:
            ip_address = request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

        log_entry = AuditLog.objects.create(
            actor=actor if actor and actor.is_authenticated else None,
            action=action,
            object_type=object_type,
            object_id=object_id,
            object_repr=object_repr,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return log_entry
