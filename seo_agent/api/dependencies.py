"""FastAPI dependency injection utilities.

This module provides dependency injection utilities for the API layer.
All services are registered in the DI container and provided via FastAPI
dependency injection. The API layer delegates all business logic to
services registered here.

Services are registered as singletons where appropriate for performance,
and as transient where new instances are needed per request.

Usage:
    from seo_agent.api.dependencies import get_workflow_orchestrator

    @app.post("/seo/run")
    async def run_seo_workflow(
        orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator),
    ):
        ...
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from seo_agent.core.dependency_injection import Container, get_container
from seo_agent.core.logging import get_logger

# Import service classes at runtime (not just for type checking)
# These are needed for type aliases and DI registration
from seo_agent.agents.execution.executor import ExecutionAgent
from seo_agent.agents.planning.planner import Planner
from seo_agent.git.operations import GitOperations
from seo_agent.integrations.opencode.adapter import OpenCodeAdapter
from seo_agent.integrations.opencode.client import OpenCodeClient
from seo_agent.repository.framework_detector import FrameworkDetector
from seo_agent.repository.metadata_parser import MetadataParser
from seo_agent.repository.page_discovery import PageDiscovery
from seo_agent.repository.scanner import RepositoryScanner
from seo_agent.review.validator import ReviewValidator
from seo_agent.seo.metadata_optimizer import MetadataOptimizer
from seo_agent.seo.robots import RobotsService
from seo_agent.seo.seo_page_generator import SEOPageGenerator
from seo_agent.seo.sitemap import SitemapService
from seo_agent.workflow.orchestrator import (
    OrchestratorConfig,
    WorkflowOrchestrator,
    create_orchestrator,
)

logger = get_logger(__name__)


def _get_container() -> Container:
    """Get the global DI container.

    Returns:
        The global dependency injection container.
    """
    return get_container()


def register_services() -> None:
    """Register all services in the DI container.

    This function should be called once during application startup
    to register all services in the container. Services are registered
    as singletons where appropriate for performance.

    The function is idempotent - calling it multiple times is safe.
    """
    container = get_container()

    # Skip if already registered
    if container.is_registered(WorkflowOrchestrator):
        logger.debug("Services already registered, skipping")
        return

    logger.info("Registering services in DI container")

    # Create OpenCode client and adapter (only if API key is configured)
    opencode_adapter = None
    try:
        from config import settings
        if settings.opencode.api_key:
            opencode_client = OpenCodeClient(
                base_url=str(settings.opencode.base_url),
                api_key=settings.opencode.api_key,
                timeout=settings.opencode.timeout,
            )
            opencode_adapter = OpenCodeAdapter(client=opencode_client)
            logger.info("OpenCode client initialized successfully")
        else:
            logger.warning("OpenCode API key not configured - OpenCode adapter will not be available")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenCode client: {e}")

    # Register infrastructure services (singletons)
    # Note: We pass instances, not classes, because register_singleton expects instances
    container.register_singleton(RepositoryScanner, RepositoryScanner())
    container.register_singleton(FrameworkDetector, FrameworkDetector())
    container.register_singleton(PageDiscovery, PageDiscovery())
    container.register_singleton(MetadataParser, MetadataParser())
    container.register_singleton(GitOperations, GitOperations())
    if opencode_adapter:
        container.register_singleton(OpenCodeAdapter, opencode_adapter)

    # Register agent services (singletons)
    container.register_singleton(Planner, Planner())
    if opencode_adapter:
        container.register_singleton(ExecutionAgent, ExecutionAgent(adapter=opencode_adapter))
    container.register_singleton(ReviewValidator, ReviewValidator())

    # Register SEO services (singletons)
    container.register_singleton(SEOPageGenerator, SEOPageGenerator(container=container))
    container.register_singleton(SitemapService, SitemapService(container=container))
    container.register_singleton(RobotsService, RobotsService(container=container))
    container.register_singleton(MetadataOptimizer, MetadataOptimizer(container=container))

    # Resolve services for orchestrator configuration
    repository_scanner = container.resolve(RepositoryScanner)
    framework_detector = container.resolve(FrameworkDetector)
    page_discovery = container.resolve(PageDiscovery)
    metadata_parser = container.resolve(MetadataParser)
    planner = container.resolve(Planner)
    # Only resolve ExecutionAgent if it was registered (requires OpenCode adapter)
    execution_agent = container.resolve(ExecutionAgent) if container.is_registered(ExecutionAgent) else None
    review_validator = container.resolve(ReviewValidator)
    git_operations = container.resolve(GitOperations)
    seo_page_generator = container.resolve(SEOPageGenerator)
    sitemap_service = container.resolve(SitemapService)
    robots_service = container.resolve(RobotsService)

    # Create and configure orchestrator with all stage handlers
    config = OrchestratorConfig(max_retries=3, continue_on_review_failure=False)
    orchestrator = create_orchestrator(
        config=config,
        repository_scanner=repository_scanner,
        framework_detector=framework_detector,
        page_discovery=page_discovery,
        metadata_parser=metadata_parser,
        planning_agent=planner,
        execution_agent=execution_agent,
        review_engine=review_validator,
        git_service=git_operations,
        seo_service=seo_page_generator,
        sitemap_service=sitemap_service,
        robots_service=robots_service,
    )

    # Register orchestrator (singleton)
    container.register_singleton(WorkflowOrchestrator, orchestrator)

    logger.info("All services registered successfully")


# Service dependency functions for FastAPI
# These functions retrieve services from the DI container


def get_repository_scanner(
    container: Annotated[Container, Depends(_get_container)],
) -> RepositoryScanner:
    """Get the repository scanner service.

    Args:
        container: The DI container.

    Returns:
        The RepositoryScanner instance.
    """
    return container.resolve(RepositoryScanner)


def get_framework_detector(
    container: Annotated[Container, Depends(_get_container)],
) -> FrameworkDetector:
    """Get the framework detector service.

    Args:
        container: The DI container.

    Returns:
        The FrameworkDetector instance.
    """
    return container.resolve(FrameworkDetector)


def get_git_operations(
    container: Annotated[Container, Depends(_get_container)],
) -> GitOperations:
    """Get the Git operations service.

    Args:
        container: The DI container.

    Returns:
        The GitOperations instance.
    """
    return container.resolve(GitOperations)


def get_opencode_adapter(
    container: Annotated[Container, Depends(_get_container)],
) -> OpenCodeAdapter:
    """Get the OpenCode adapter service.

    Args:
        container: The DI container.

    Returns:
        The OpenCodeAdapter instance.
    """
    return container.resolve(OpenCodeAdapter)


def get_planner(
    container: Annotated[Container, Depends(_get_container)],
) -> Planner:
    """Get the planner service.

    Args:
        container: The DI container.

    Returns:
        The Planner instance.
    """
    return container.resolve(Planner)


def get_execution_agent(
    container: Annotated[Container, Depends(_get_container)],
) -> ExecutionAgent:
    """Get the execution agent service.

    Args:
        container: The DI container.

    Returns:
        The ExecutionAgent instance.
    """
    return container.resolve(ExecutionAgent)


def get_review_validator(
    container: Annotated[Container, Depends(_get_container)],
) -> ReviewValidator:
    """Get the review validator service.

    Args:
        container: The DI container.

    Returns:
        The ReviewValidator instance.
    """
    return container.resolve(ReviewValidator)


def get_seo_page_generator(
    container: Annotated[Container, Depends(_get_container)],
) -> SEOPageGenerator:
    """Get the SEO page generator service.

    Args:
        container: The DI container.

    Returns:
        The SEOPageGenerator instance.
    """
    return container.resolve(SEOPageGenerator)


def get_sitemap_service(
    container: Annotated[Container, Depends(_get_container)],
) -> SitemapService:
    """Get the sitemap service.

    Args:
        container: The DI container.

    Returns:
        The SitemapService instance.
    """
    return container.resolve(SitemapService)


def get_robots_service(
    container: Annotated[Container, Depends(_get_container)],
) -> RobotsService:
    """Get the robots service.

    Args:
        container: The DI container.

    Returns:
        The RobotsService instance.
    """
    return container.resolve(RobotsService)


def get_metadata_optimizer(
    container: Annotated[Container, Depends(_get_container)],
) -> MetadataOptimizer:
    """Get the metadata optimizer service.

    Args:
        container: The DI container.

    Returns:
        The MetadataOptimizer instance.
    """
    return container.resolve(MetadataOptimizer)


def get_workflow_orchestrator(
    container: Annotated[Container, Depends(_get_container)],
) -> WorkflowOrchestrator:
    """Get the workflow orchestrator service.

    Args:
        container: The DI container.

    Returns:
        The WorkflowOrchestrator instance.
    """
    return container.resolve(WorkflowOrchestrator)


# Type aliases for cleaner dependency injection
RepositoryScannerDep = Annotated[RepositoryScanner, Depends(get_repository_scanner)]
FrameworkDetectorDep = Annotated[FrameworkDetector, Depends(get_framework_detector)]
GitOperationsDep = Annotated[GitOperations, Depends(get_git_operations)]
OpenCodeAdapterDep = Annotated[OpenCodeAdapter, Depends(get_opencode_adapter)]
PlannerDep = Annotated[Planner, Depends(get_planner)]
ExecutionAgentDep = Annotated[ExecutionAgent, Depends(get_execution_agent)]
ReviewValidatorDep = Annotated[ReviewValidator, Depends(get_review_validator)]
SEOPageGeneratorDep = Annotated[SEOPageGenerator, Depends(get_seo_page_generator)]
SitemapServiceDep = Annotated[SitemapService, Depends(get_sitemap_service)]
RobotsServiceDep = Annotated[RobotsService, Depends(get_robots_service)]
MetadataOptimizerDep = Annotated[MetadataOptimizer, Depends(get_metadata_optimizer)]
WorkflowOrchestratorDep = Annotated[WorkflowOrchestrator, Depends(get_workflow_orchestrator)]