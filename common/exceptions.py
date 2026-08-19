"""
Common — Custom Exceptions
All service-layer exceptions per §35.
Views convert these into standardized HTTP responses.
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class ServiceValidationError(APIException):
    """Raised when a service method receives invalid data or business rule is violated."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A validation error occurred."
    default_code = "VALIDATION_ERROR"


class PermissionDeniedError(APIException):
    """Raised when a user lacks the required role or permission."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "PERMISSION_DENIED"


class ResourceNotFoundError(APIException):
    """Raised when a requested resource does not exist."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "NOT_FOUND"


class InvalidStateTransitionError(APIException):
    """Raised when a workflow state transition is not allowed (e.g. approving an already-published story)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This action is not allowed in the current state."
    default_code = "INVALID_STATE_TRANSITION"


class DuplicateResourceError(APIException):
    """Raised when creating a duplicate record (e.g. liking a story twice)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This resource already exists."
    default_code = "DUPLICATE_RESOURCE"


class AuthenticationError(APIException):
    """Raised for authentication failures."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication failed."
    default_code = "AUTHENTICATION_ERROR"


class InactiveUserError(APIException):
    """Raised when an inactive user attempts to authenticate."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Your account has been deactivated."
    default_code = "INACTIVE_USER"


class ModerationFailedError(APIException):
    """Raised when content fails moderation checks."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Content failed moderation checks."
    default_code = "MODERATION_FAILED"


class PublishingError(APIException):
    """Raised when publishing requirements are not met."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Publishing requirements are not met."
    default_code = "PUBLISHING_ERROR"


class ExternalServiceError(APIException):
    """Raised when an external service (Cloudinary, Brevo, Google) fails."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "An external service is unavailable. Please try again."
    default_code = "EXTERNAL_SERVICE_ERROR"


def custom_exception_handler(exc, context):
    """
    Convert DRF and custom exceptions into Tossatale standard error response format (§34).
    {
        "success": false,
        "message": "...",
        "errors": {},
        "error_code": "..."
    }
    """
    from rest_framework.views import exception_handler
    from rest_framework import status as drf_status

    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, "default_code", "ERROR")
        message = str(exc.detail) if hasattr(exc, "detail") else str(exc)

        # Flatten nested detail for serializer errors
        errors = {}
        if isinstance(exc.detail, dict):
            message = "Validation error."
            errors = exc.detail
        elif isinstance(exc.detail, list):
            message = exc.detail[0] if exc.detail else "An error occurred."

        response.data = {
            "success": False,
            "message": message,
            "errors": errors,
            "error_code": error_code.upper() if isinstance(error_code, str) else "ERROR",
        }

    return response
