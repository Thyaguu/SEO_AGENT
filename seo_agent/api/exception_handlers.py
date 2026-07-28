"""Exception handlers for FastAPI error responses.

This module maps SEOAgentError subclasses to appropriate HTTP status codes
and formats error responses consistently for n8n workflow consumption.

Mapping:
    - 400: ValidationError, RepositoryError, ConfigurationError, FrameworkDetectionError
    - 500: ExecutionError, ReviewError, GitError, IntegrationError, TimeoutError, DependencyError

Usage:
    app = FastAPI()
    add_exception_handlers(app)

    # Or use the handler directly:
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request, exc):
        return await seo_agent_exception_handler(request, exc)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from seo_agent.core.exceptions import (
    ConfigurationError,
    DependencyError,
    ExecutionError,
    FrameworkDetectionError,
    GitError,
    IntegrationError,
    RepositoryError,
    ReviewError,
    SEOAgentError,
    TimeoutError,
    ValidationError,
)

if TYPE_CHECKING:
    from seo_agent.core.logging import Logger

# Status code mapping for SEOAgentError subclasses
_ERROR_STATUS_MAP: dict[type[SEOAgentError], int] = {
    # 400: Input validation and configuration errors
    ValidationError: status.HTTP_400_BAD_REQUEST,
    RepositoryError: status.HTTP_400_BAD_REQUEST,
    ConfigurationError: status.HTTP_400_BAD_REQUEST,
    FrameworkDetectionError: status.HTTP_400_BAD_REQUEST,
    # 500: Internal processing errors
    ExecutionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ReviewError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    GitError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    IntegrationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    TimeoutError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    DependencyError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _get_status_code(exc: SEOAgentError) -> int:
    """Get HTTP status code for an exception.

    Args:
        exc: The SEOAgentError instance.

    Returns:
        HTTP status code integer.
    """
    # Check exact type match first
    if type(exc) in _ERROR_STATUS_MAP:
        return _ERROR_STATUS_MAP[type(exc)]

    # Check inheritance hierarchy
    for exc_type, code in _ERROR_STATUS_MAP.items():
        if isinstance(exc, exc_type):
            return code

    # Default to 500 for unknown SEOAgentError subclasses
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle RequestValidationError and return formatted JSON response.

    This handler ensures that Pydantic validation errors are returned
    as consistent JSON responses instead of FastAPI's default HTML.

    Args:
        request: The FastAPI request object.
        exc: The caught RequestValidationError instance.

    Returns:
        JSONResponse with validation error details and 422 status code.
    """
    from seo_agent.core.logging import get_logger

    logger: Logger = get_logger(__name__)

    # Log the validation error
    logger.warning(
        f"Request validation failed: error_type=RequestValidationError, "
        f"path={request.url.path}, method={request.method}"
    )

    # Build error response matching the SEOAgentError format
    errors = exc.errors()
    error_messages = [
        {
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in errors
    ]

    error_response = {
        "error": {
            "type": "RequestValidationError",
            "message": "Request validation failed",
            "details": error_messages,
        }
    }

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response,
        headers={"X-Error-Type": "RequestValidationError"},
    )


async def seo_agent_exception_handler(
    request: Request,
    exc: SEOAgentError,
) -> JSONResponse:
    """Handle SEOAgentError exceptions and return formatted JSON response.

    This handler is registered with FastAPI to catch all SEOAgentError
    subclasses and format them consistently for API responses.

    Args:
        request: The FastAPI request object.
        exc: The caught SEOAgentError instance.

    Returns:
        JSONResponse with error details and appropriate status code.
    """
    # Import logger here to avoid circular imports
    from seo_agent.core.logging import get_logger

    logger: Logger = get_logger(__name__)

    # Get status code based on exception type
    status_code = _get_status_code(exc)

    # Log the error with context
    logger.error(
        f"API request error: error_type={type(exc).__name__}, "
        f"error_message={exc.message}, status_code={status_code}, "
        f"path={request.url.path}, method={request.method}, details={exc.details}"
    )

    # Build error response
    error_response = {
        "error": {
            "type": type(exc).__name__,
            "message": exc.message,
            "details": exc.details if exc.details else None,
        }
    }

    return JSONResponse(
        status_code=status_code,
        content=error_response,
        headers={"X-Error-Type": type(exc).__name__},
    )


def add_exception_handlers(app: "FastAPIApp") -> None:
    """Register exception handlers with a FastAPI application.

    This function adds all SEOAgentError handlers to the provided
    FastAPI app instance.

    Args:
        app: FastAPI application instance.
    """
    # Import here to avoid circular imports
    from fastapi import FastAPI

    # Type alias for the app parameter
    FastAPIApp = FastAPI

    # Register the generic SEOAgentError handler
    app.add_exception_handler(SEOAgentError, seo_agent_exception_handler)

    # Register RequestValidationError handler for consistent JSON responses
    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,
    )

    # Optionally register specific handlers for more granular control
    # The generic handler above already handles these, but explicit
    # registration allows for custom behavior per exception type
    app.add_exception_handler(ValidationError, seo_agent_exception_handler)
    app.add_exception_handler(RepositoryError, seo_agent_exception_handler)
    app.add_exception_handler(ConfigurationError, seo_agent_exception_handler)
    app.add_exception_handler(FrameworkDetectionError, seo_agent_exception_handler)
    app.add_exception_handler(ExecutionError, seo_agent_exception_handler)
    app.add_exception_handler(ReviewError, seo_agent_exception_handler)
    app.add_exception_handler(GitError, seo_agent_exception_handler)
    app.add_exception_handler(IntegrationError, seo_agent_exception_handler)
    app.add_exception_handler(TimeoutError, seo_agent_exception_handler)
    app.add_exception_handler(DependencyError, seo_agent_exception_handler)