"""
Common — Custom Exceptions
All service-layer exceptions per §35.
Views convert these into standardized HTTP responses.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class ServiceValidationError(APIException):
    """Raised when a service method receives invalid data or business rule is violated."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("A validation error occurred.")
    default_code = "VALIDATION_ERROR"


class PermissionDeniedError(APIException):
    """Raised when a user lacks the required role or permission."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("You do not have permission to perform this action.")
    default_code = "PERMISSION_DENIED"


class ResourceNotFoundError(APIException):
    """Raised when a requested resource does not exist."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("The requested resource was not found.")
    default_code = "NOT_FOUND"


class InvalidStateTransitionError(APIException):
    """Raised when a workflow state transition is not allowed (e.g. approving an already-published story)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("This action is not allowed in the current state.")
    default_code = "INVALID_STATE_TRANSITION"


class DuplicateResourceError(APIException):
    """Raised when creating a duplicate record (e.g. liking a story twice)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = _("This resource already exists.")
    default_code = "DUPLICATE_RESOURCE"


class AuthenticationError(APIException):
    """Raised for authentication failures."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("Authentication failed.")
    default_code = "AUTHENTICATION_ERROR"


class InactiveUserError(APIException):
    """Raised when an inactive user attempts to authenticate."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("Your account has been deactivated.")
    default_code = "INACTIVE_USER"


class EmailNotVerifiedError(APIException):
    """Raised when an unverified user attempts to authenticate."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("Your email address is not verified. A verification code has been sent to your email.")
    default_code = "EMAIL_NOT_VERIFIED"


class WriterGoogleAuthBlockedError(APIException):
    """Raised when a Writer attempts to log in via Google OAuth."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("Google login is not supported for Writer accounts. Please sign in with your email and password.")
    default_code = "WRITER_GOOGLE_LOGIN_BLOCKED"


class ModerationFailedError(APIException):
    """Raised when content fails moderation checks."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = _("Content failed moderation checks.")
    default_code = "MODERATION_FAILED"


class PublishingError(APIException):
    """Raised when publishing requirements are not met."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = _("Publishing requirements are not met.")
    default_code = "PUBLISHING_ERROR"


class ExternalServiceError(APIException):
    """Raised when an external service (Cloudinary, Brevo, Google) fails."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("An external service is unavailable. Please try again.")
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
        error_code = getattr(exc, "default_code", getattr(response, "status_text", "ERROR"))
        detail = getattr(exc, "detail", None)
        message = str(detail) if detail is not None else str(exc)

        # Flatten nested detail for serializer errors
        errors = {}
        if isinstance(detail, dict):
            message = "Validation error."
            errors = detail
        elif isinstance(detail, list):
            message = str(detail[0]) if detail else "An error occurred."
        elif hasattr(response, "data") and isinstance(response.data, dict) and "detail" in response.data:
            message = str(response.data["detail"])

        response.data = {
            "success": False,
            "message": message,
            "errors": errors,
            "error_code": str(error_code).upper() if error_code else "ERROR",
        }

    return response
