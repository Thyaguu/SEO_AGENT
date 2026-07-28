"""Health check endpoints.

This module provides health check endpoints for monitoring the API service.
Health checks are used by load balancers and orchestration systems (like n8n)
to determine if the service is healthy and ready to receive requests.

The health endpoints do NOT contain business logic - they only report
on the operational status of the service infrastructure.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from seo_agent.api.dependencies import (
    Container,
    FrameworkDetectorDep,
    GitOperationsDep,
    MetadataOptimizerDep,
    OpenCodeAdapterDep,
    RepositoryScannerDep,
    ReviewValidatorDep,
    RobotsServiceDep,
    SEOPageGeneratorDep,
    SitemapServiceDep,
    WorkflowOrchestratorDep,
    get_container,
)
from seo_agent.core.logging import get_logger

logger = get_logger(__name__)

# Create health router
router = APIRouter(prefix="/health", tags=["Health"])


def _get_service_status(container: Container) -> dict[str, bool]:
    """Check the status of all registered services.

    This function attempts to verify that each registered service
    can be resolved from the container. A service is considered
    healthy if it can be instantiated without errors.

    Args:
        container: The dependency injection container.

    Returns:
        Dictionary mapping service names to their availability status.
    """
    services: dict[str, bool] = {}
    service_getters = {
        "repository_scanner": lambda: container.resolve(RepositoryScannerDep),
        "framework_detector": lambda: container.resolve(FrameworkDetectorDep),
        "git_operations": lambda: container.resolve(GitOperationsDep),
        "opencode_adapter": lambda: container.resolve(OpenCodeAdapterDep),
        "planner": lambda: container.resolve(
            "seo_agent.agents.planning.planner.Planner"
        ),
        "execution_agent": lambda: container.resolve(
            "seo_agent.agents.execution.executor.ExecutionAgent"
        ),
        "review_validator": lambda: container.resolve(ReviewValidatorDep),
        "seo_page_generator": lambda: container.resolve(SEOPageGeneratorDep),
        "sitemap_service": lambda: container.resolve(SitemapServiceDep),
        "robots_service": lambda: container.resolve(RobotsServiceDep),
        "metadata_optimizer": lambda: container.resolve(MetadataOptimizerDep),
        "workflow_orchestrator": lambda: container.resolve(WorkflowOrchestratorDep),
    }

    for name, getter in service_getters.items():
        try:
            getter()
            services[name] = True
        except Exception as e:
            logger.warning(f"Service {name} unavailable: {e}")
            services[name] = False

    return services


@router.get(
    "",
    summary="Basic health check",
    description="Returns the basic health status of the API service.",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
    },
)
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint.

    This endpoint returns a simple health status. It does not check
    external dependencies or services. Use /health/ready for a
    comprehensive readiness check.

    Returns:
        Dictionary with status and timestamp.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/ready",
    summary="Readiness check",
    description="Returns the readiness status including all service dependencies.",
    responses={
        200: {
            "description": "Service is ready",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ready",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "services": {
                            "repository_scanner": True,
                            "framework_detector": True,
                            "git_operations": True,
                            "opencode_adapter": True,
                            "planning_agent": True,
                            "execution_agent": True,
                            "review_validator": True,
                            "seo_page_generator": True,
                            "sitemap_service": True,
                            "robots_service": True,
                            "metadata_optimizer": True,
                            "workflow_orchestrator": True,
                        },
                    }
                }
            },
        },
        503: {
            "description": "Service is not ready",
            "content": {
                "application/json": {
                    "example": {
                        "status": "not_ready",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "services": {
                            "repository_scanner": True,
                            "framework_detector": False,
                        },
                    }
                }
            },
        },
    },
)
async def readiness_check(
    container: Container = Depends(get_container),
) -> dict[str, Any]:
    """Readiness check endpoint.

    This endpoint verifies that all registered services are available
    and can be resolved from the dependency injection container. It
    provides a comprehensive view of service health.

    Use this endpoint for load balancer health checks and orchestration
    systems that need to verify the service is fully operational.

    Args:
        container: The dependency injection container.

    Returns:
        Dictionary with status, timestamp, and service availability.
    """
    services = _get_service_status(container)
    all_healthy = all(services.values())

    return {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }


@router.get(
    "/live",
    summary="Liveness check",
    description="Returns the liveness status of the API service.",
    responses={
        200: {
            "description": "Service is alive",
            "content": {
                "application/json": {
                    "example": {
                        "status": "alive",
                        "timestamp": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
    },
)
async def liveness_check() -> dict[str, Any]:
    """Liveness check endpoint.

    This endpoint is used by Kubernetes and other orchestration systems
    to determine if the service process is alive. It should return quickly
    without checking external dependencies.

    Returns:
        Dictionary with status and timestamp.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }