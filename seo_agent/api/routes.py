"""API routes - FastAPI endpoints consumed by n8n workflow.

This module provides the REST API endpoints for the SEO agent.
These endpoints are designed to be consumed by n8n workflows for
triggering SEO optimization tasks.

The routes do NOT contain business logic - they only:
- Validate incoming requests
- Convert requests to domain models
- Delegate to the workflow orchestrator
- Convert responses from domain models

All actual business logic is handled by the workflow orchestrator
and its registered stage handlers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from seo_agent.api.dependencies import (
    WorkflowOrchestratorDep,
    get_container,
)
from seo_agent.api.schemas import (
    ExecutionStatus,
    FileChange,
    PageAnalysisResult,
    ReviewStatus,
    SEOAgentRequest,
    SEOPageResult,
    SEOPayload,
    SEOResponse,
    StageResult,
)
from seo_agent.core.logging import get_logger
from seo_agent.workflow.context import WorkflowContext
from seo_agent.workflow.stages import WorkflowStage

logger = get_logger(__name__)

# Create main router
router = APIRouter(prefix="/seo", tags=["SEO"])


def _request_to_context(request: SEOAgentRequest) -> WorkflowContext:
    """Convert an API request to a workflow context.

    This function transforms the incoming API request into the
    internal workflow context format used by the orchestrator.

    Args:
        request: The validated API request.

    Returns:
        A WorkflowContext instance with the request data.
    """
    # Create the workflow context
    context = WorkflowContext(
        repository_path=Path(request.repository_path),
    )

    # Store SEO payload in context metadata
    context.metadata["seo_payload"] = request.seo_payload
    context.metadata["request_id"] = request.request_id

    # Store configuration options
    context.config["skip_git"] = request.skip_git
    context.config["skip_pipeline"] = request.skip_pipeline
    context.config["max_seo_pages"] = request.max_seo_pages
    context.config["review_attempts"] = request.review_attempts
    context.config["branch_name"] = request.branch_name

    # Extract keywords from SEO payload
    if request.seo_payload.seed_keywords:
        context.keywords = [kw.term for kw in request.seo_payload.seed_keywords]

    return context


def _context_to_response(
    request_id: str,
    context: WorkflowContext,
    started_at: datetime,
) -> SEOResponse:
    """Convert a workflow context to an API response.

    This function transforms the workflow context (after execution)
    into the API response format expected by n8n.

    Args:
        request_id: The original request ID.
        context: The workflow context after execution.
        started_at: When the workflow started.

    Returns:
        A SEOResponse instance with the execution results.
    """
    # Determine overall status
    if context.is_successful():
        status = ExecutionStatus.COMPLETED
    elif context.has_errors():
        status = ExecutionStatus.FAILED
    else:
        status = ExecutionStatus.FAILED

    # Determine review status
    if context.review_result is not None:
        if context.review_result.is_valid:
            review_status = ReviewStatus.APPROVED
        else:
            review_status = ReviewStatus.REJECTED
    else:
        review_status = ReviewStatus.PENDING

    # Calculate duration
    completed_at = datetime.now(timezone.utc)
    duration = (completed_at - started_at).total_seconds()

    # Build stage results from transitions
    stages = []
    for transition in context.transitions:
        error_str = str(transition.error) if transition.error else None
        stage_result = StageResult(
            stage=transition.from_stage.value,
            status="completed" if transition.success else "failed",
            started_at=transition.timestamp,
            completed_at=transition.timestamp,  # Transitions don't have separate end time
            duration_seconds=None,
            message=error_str,
            file_changes=[],
            errors=[error_str] if error_str else [],
        )
        stages.append(stage_result)

    # Build file changes from execution result
    # Derive from current ExecutionResult fields: seo_pages_created,
    # seo_pages_removed, and metadata_updates (no `changes` field exists).
    file_changes: list[FileChange] = []
    if context.execution_result:
        for page in context.execution_result.seo_pages_created:
            file_changes.append(FileChange(
                file_path=page.file_path,
                change_type="created",
            ))
        for file_path in context.execution_result.seo_pages_removed:
            file_changes.append(FileChange(
                file_path=file_path,
                change_type="deleted",
            ))
        for metadata in context.execution_result.metadata_updates:
            # Metadata has no file_path; use canonical_url as a stable identifier.
            file_changes.append(FileChange(
                file_path=metadata.canonical_url,
                change_type="modified",
            ))

    # Build pages generated from execution result
    pages_generated: list[SEOPageResult] = []
    if context.execution_result:
        for page in context.execution_result.seo_pages_created:
            pages_generated.append(SEOPageResult(
                slug=page.slug,
                url=page.metadata.canonical_url,
                file_path=page.file_path,
                keywords_used=page.keywords,
                created=True,
            ))

    # Build pages analyzed from page info
    pages_analyzed: list[PageAnalysisResult] = []
    for page_info in context.page_info:
        # Access canonical through metadata field (PageInfo has no direct canonical)
        # Ensure url is always a string, even if metadata or canonical is None
        if page_info.metadata and page_info.metadata.canonical:
            page_url = page_info.metadata.canonical
        else:
            page_url = ""
        pages_analyzed.append(PageAnalysisResult(
            url=page_url,
            success=True,
        ))

    return SEOResponse(
        request_id=request_id,
        status=status,
        review_status=review_status,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration,
        message=_get_status_message(status, context),
        stages=stages,
        pages_analyzed=pages_analyzed,
        pages_generated=pages_generated,
        file_changes=file_changes,
        errors=[str(err) for err in context.errors],
        warnings=_get_warnings(context),
    )


def _get_status_message(status: ExecutionStatus, context: WorkflowContext) -> str:
    """Get a human-readable status message.

    Args:
        status: The execution status.
        context: The workflow context.

    Returns:
        A status message string.
    """
    if status == ExecutionStatus.COMPLETED:
        return "SEO optimization completed successfully"
    elif status == ExecutionStatus.FAILED:
        if context.errors:
            return f"SEO optimization failed: {context.errors[0]}"
        return "SEO optimization failed"
    else:
        return "SEO optimization completed with unexpected status"


def _get_warnings(context: WorkflowContext) -> list[str]:
    """Extract warnings from the workflow context.

    Args:
        context: The workflow context.

    Returns:
        List of warning messages.
    """
    warnings: list[str] = []

    # Check for skipped operations
    if context.config.get("skip_git"):
        warnings.append("Git operations were skipped")
    if context.config.get("skip_pipeline"):
        warnings.append("CI/CD pipeline trigger was skipped")

    # Check for retry attempts
    # (would need to track this in context)

    return warnings


@router.post(
    "/run",
    response_model=SEOResponse,
    summary="Run SEO optimization",
    description="Triggers the SEO agent workflow to optimize a repository.",
    responses={
        200: {
            "description": "SEO optimization completed",
            "content": {
                "application/json": {
                    "example": {
                        "request_id": "req-123",
                        "status": "success",
                        "review_status": "approved",
                        "started_at": "2024-01-15T10:30:00Z",
                        "completed_at": "2024-01-15T10:35:00Z",
                        "duration_seconds": 300.0,
                        "message": "SEO optimization completed successfully",
                        "stages": [],
                        "pages_analyzed": [],
                        "pages_generated": [],
                        "file_changes": [],
                        "errors": [],
                        "warnings": [],
                    }
                }
            },
        },
        400: {
            "description": "Invalid request",
        },
        500: {
            "description": "Internal server error",
        },
    },
)
async def run_seo_optimization(
    request: SEOAgentRequest,
    http_request: Request,
    orchestrator: WorkflowOrchestratorDep,
) -> SEOResponse:
    """Run SEO optimization workflow.

    This is the main endpoint for triggering SEO optimization.
    It accepts SEO intelligence from n8n and coordinates the
    entire optimization workflow.

    The workflow includes:
    - Repository scanning and framework detection
    - Keyword-based planning
    - Page generation and optimization
    - Review and validation
    - Git operations (optional)

    Args:
        request: The SEO optimization request from n8n.
        http_request: The FastAPI request object.
        orchestrator: The workflow orchestrator dependency.

    Returns:
        SEOResponse with execution results.

    Raises:
        HTTPException: If the workflow fails.
    """
    request_id = request.request_id
    started_at = datetime.now(timezone.utc)

    logger.info(
        "Starting SEO optimization",
        extra={
            "request_id": request_id,
            "repository_path": str(request.repository_path),
            "max_seo_pages": request.max_seo_pages,
        },
    )

    try:
        # Convert request to workflow context
        context = _request_to_context(request)

        # Run the workflow
        result = await orchestrator.run(context)

        # Convert result to response
        if result.is_success():
            logger.info(
                "SEO optimization completed successfully",
                extra={"request_id": request_id},
            )
            return _context_to_response(request_id, context, started_at)
        else:
            error_message = result.get_error_or_none() or "Unknown error"
            logger.error(
                "SEO optimization failed",
                extra={"request_id": request_id, "error": error_message},
            )
            # Return response with failure status
            context.add_error(error_message)
            return _context_to_response(request_id, context, started_at)

    except Exception as e:
        logger.exception(
            "SEO optimization error",
            extra={"request_id": request_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SEO optimization failed: {str(e)}",
        )