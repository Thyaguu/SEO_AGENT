"""API middleware - request/response processing.

This module provides middleware components for the FastAPI application.
Middleware processes requests and responses globally, enabling cross-cutting
concerns like logging, request ID tracking, and CORS handling.

The middleware does NOT contain business logic - it only handles
infrastructure concerns like timing, logging, and request context.
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from seo_agent.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    This middleware logs incoming requests and outgoing responses
    with timing information. It helps with debugging and monitoring
    API performance.

    Attributes:
        app: The ASGI application.

    Example:
        >>> app.add_middleware(RequestLoggingMiddleware)
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process the request and log details.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The HTTP response.
        """
        # Extract request information
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        client_host = request.client.host if request.client else "unknown"

        # Log incoming request
        logger.info(
            f"Request started: method={method}, path={path}, "
            f"query_params={query_params}, client_host={client_host}"
        )

        # Track timing
        start_time = time.perf_counter()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log response
            logger.info(
                f"Request completed: method={method}, path={path}, "
                f"status_code={response.status_code}, duration_ms={round(duration_ms, 2)}"
            )

            # Add timing header
            response.headers["X-Process-Time-Ms"] = str(round(duration_ms, 2))

            return response

        except Exception as e:
            # Calculate duration even on error
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                f"Request failed: method={method}, path={path}, "
                f"error={str(e)}, duration_ms={round(duration_ms, 2)}"
            )
            raise


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking requests with unique IDs.

    This middleware assigns a unique request ID to each incoming request
    and includes it in the response headers. This helps with tracing
    requests through logs and debugging distributed systems.

    Attributes:
        app: The ASGI application.

    Example:
        >>> app.add_middleware(RequestIDMiddleware)
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process the request with request ID tracking.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The HTTP response with request ID header.
        """
        # Get or generate request ID
        # Check header first (for proxied requests)
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            # Generate new ID
            import uuid
            request_id = str(uuid.uuid4())

        # Store in request state for access in route handlers
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


def create_cors_config() -> dict:
    """Create CORS configuration for the API.

    Returns:
        Dictionary with CORS configuration.
    """
    return {
        "allow_origins": ["*"],  # Configure appropriately for production
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }