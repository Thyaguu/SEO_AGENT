"""FastAPI application entry point.

This module creates and configures the FastAPI application with all
middleware, routes, exception handlers, and lifecycle events.

The application is designed to be consumed by n8n workflows for
triggering SEO optimization tasks.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.errors import ServerErrorMiddleware

from seo_agent import __version__
from seo_agent.api import routes, health
from seo_agent.api.exception_handlers import (
    add_exception_handlers,
)
from seo_agent.api.middleware import (
    RequestLoggingMiddleware,
    RequestIDMiddleware,
    create_cors_config,
)
from seo_agent.core.logging import configure_logging, get_logger
from seo_agent.api.dependencies import register_services

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler.

    This function is called on application startup and shutdown.
    Use it for initializing and cleaning up resources.

    Args:
        app: The FastAPI application instance.

    Yields:
        None
    """
    # Configure logging
    configure_logging()

    # Startup
    logger.info(f"Starting SEO Agent API: version={__version__}")

    # Initialize dependency injection container
    register_services()

    yield

    # Shutdown
    logger.info(f"Shutting down SEO Agent API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    This function creates a fully configured FastAPI application with:
    - CORS middleware
    - Request logging middleware
    - Request ID middleware
    - Exception handlers
    - Health check routes
    - Main API routes

    Returns:
        A configured FastAPI application instance.
    """
    # Create the application
    app = FastAPI(
        title="SEO Agent API",
        description=(
            "AI-powered SEO optimization platform. "
            "This API provides endpoints for analyzing repositories, "
            "generating SEO-optimized pages, and managing content."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    cors_config = create_cors_config()
    app.add_middleware(
        CORSMiddleware,
        **cors_config,
    )

    # Add request ID middleware
    app.add_middleware(RequestIDMiddleware)

    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Add server error middleware for unhandled exceptions
    app.add_middleware(ServerErrorMiddleware, debug=False)

    # Register exception handlers
    add_exception_handlers(app)

    # Include routers
    app.include_router(health.router)
    app.include_router(routes.router)

    # Root endpoint
    @app.get(
        "/",
        tags=["Root"],
        summary="Root endpoint",
        description="Returns basic information about the API.",
    )
    async def root() -> dict[str, str]:
        """Root endpoint returning API information.

        Returns:
            Dictionary with API name and version.
        """
        return {
            "name": "SEO Agent API",
            "version": __version__,
            "docs": "/docs",
        }

    logger.info(f"SEO Agent API created: version={__version__}")

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn for development
    uvicorn.run(
        "seo_agent.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )