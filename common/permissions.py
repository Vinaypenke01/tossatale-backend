"""
Common — Role-Based Permission Classes
Enforces role gates per §6 across all views.
"""
from rest_framework.permissions import BasePermission
from apps.accounts.constants import UserRole


class IsAdmin(BasePermission):
    """Allow only users with ADMIN role."""
    message = "Administrator access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.ADMIN
        )


class IsWriter(BasePermission):
    """Allow only active writers."""
    message = "Writer access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.WRITER
            and request.user.is_active
        )


class IsAdminOrWriter(BasePermission):
    """Allow admins or writers."""
    message = "Admin or writer access required."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.ADMIN, UserRole.WRITER)
            and request.user.is_active
        )


class IsOwnerOrAdmin(BasePermission):
    """Object-level permission: allow only the owner or an admin."""
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        if request.user.role == UserRole.ADMIN:
            return True
        # Check common owner fields
        owner = getattr(obj, "user", None) or getattr(obj, "writer", None)
        if owner is None:
            return False
        user = getattr(owner, "user", owner)
        return user == request.user
