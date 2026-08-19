"""
Common — Request Logging Middleware
Logs API request failures and authentication failures per §47.
"""
import logging
import time

logger = logging.getLogger("apps")


class RequestLoggingMiddleware:
    """
    Logs slow requests and 4xx/5xx responses.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = (time.time() - start) * 1000  # ms

        if response.status_code >= 400:
            logger.warning(
                "[%s] %s %s → %s (%.1fms)",
                request.META.get("REMOTE_ADDR", "-"),
                request.method,
                request.path,
                response.status_code,
                duration,
            )
        elif duration > 1000:
            logger.warning(
                "SLOW REQUEST [%s] %s %s → %s (%.1fms)",
                request.META.get("REMOTE_ADDR", "-"),
                request.method,
                request.path,
                response.status_code,
                duration,
            )

        return response
