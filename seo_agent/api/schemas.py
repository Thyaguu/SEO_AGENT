"""API request/response schemas - Pydantic v2 models for FastAPI validation.

This module defines the public API contract between the n8n workflow and
the SEO agent. All request/response validation happens here.

The schemas are isolated from domain models to maintain a clean boundary
between the API layer and business logic.

Usage:
    from seo_agent.api.schemas import SEOAgentRequest, SEOResponse

    @app.post("/seo/run")
    async def run_seo(request: SEOAgentRequest) -> SEOResponse:
        ...
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ExecutionStatus(str, Enum):
    """Status of an SEO agent execution.

    Values:
        PENDING: Execution has not started.
        RUNNING: Execution is in progress.
        COMPLETED: Execution finished successfully.
        FAILED: Execution failed.
        CANCELLED: Execution was cancelled.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReviewStatus(str, Enum):
    """Status of the review phase.

    Values:
        PENDING: Review has not started.
        IN_PROGRESS: Review is being performed.
        APPROVED: Review passed, changes approved.
        REJECTED: Review failed, changes rejected.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"


# Request Models


class KeywordPayload(BaseModel):
    """Keyword data from n8n payload.

    Attributes:
        term: The keyword or phrase to target.
        type: Keyword type - "primary" or "secondary".
        search_volume: Monthly search volume estimate.
        difficulty: Keyword difficulty score (0-100).
        intent: Search intent (informational, navigational, transactional, commercial).
    """

    term: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The keyword or phrase to target",
    )
    type: str = Field(
        default="secondary",
        pattern="^(primary|secondary)$",
        description="Keyword type",
    )
    search_volume: int | None = Field(
        default=None,
        ge=0,
        description="Monthly search volume",
    )
    difficulty: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Keyword difficulty score (0-100)",
    )
    intent: str | None = Field(
        default=None,
        max_length=50,
        description="Search intent",
    )


class PagePayload(BaseModel):
    """Page information from n8n payload.

    Attributes:
        url: Target URL for the page.
        title: Current page title.
        existing_keywords: Keywords already present on the page.
        suggested_keywords: Keywords suggested by n8n.
        content_recommendations: Content optimization suggestions.
    """

    url: str = Field(
        ...,
        description="Target URL for the page",
    )
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Current page title",
    )
    existing_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords already on the page",
    )
    suggested_keywords: list[KeywordPayload] = Field(
        default_factory=list,
        description="Keywords suggested by n8n",
    )
    content_recommendations: list[str] = Field(
        default_factory=list,
        description="Content optimization suggestions",
    )


class CompetitorPayload(BaseModel):
    """Competitor information from n8n payload.

    Attributes:
        name: Competitor name or domain.
        strengths: List of competitor strengths.
        notes: Additional notes for analysis.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Competitor name or domain",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Competitor strengths",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Additional notes",
    )


class SEOPayload(BaseModel):
    """Complete SEO intelligence payload from n8n.

    This is the main input model consumed by the SEO agent.
    All SEO intelligence originates from the n8n workflow.

    Attributes:
        target_urls: List of target URLs to optimize.
        seed_keywords: Primary seed keywords for targeting.
        keyword_clusters: Grouped keyword clusters by topic.
        competitors: Competitor information for analysis.
        search_intent: Search intent mapping by keyword.
        priority_pages: Pages that should be prioritized.
    """

    target_urls: list[str] = Field(
        ...,
        min_length=1,
        description="List of target URLs to optimize",
    )
    seed_keywords: list[KeywordPayload] = Field(
        default_factory=list,
        description="Primary seed keywords",
    )
    keyword_clusters: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Grouped keyword clusters by topic",
    )
    competitors: list[CompetitorPayload] = Field(
        default_factory=list,
        description="Competitor information",
    )
    search_intent: dict[str, str] = Field(
        default_factory=dict,
        description="Search intent mapping by keyword",
    )
    priority_pages: list[str] = Field(
        default_factory=list,
        description="Pages that should be prioritized",
    )


class SEOAgentRequest(BaseModel):
    """Main request model for SEO agent execution.

    This is the entry point for the n8n workflow to trigger SEO optimization.

    Attributes:
        request_id: Unique identifier for this request (for tracking).
        repository_path: Absolute path to the repository.
        seo_payload: Complete SEO intelligence from n8n.
        skip_git: Skip Git operations if True.
        skip_pipeline: Skip CI/CD pipeline trigger if True.
        max_seo_pages: Maximum number of SEO pages to generate (1-50).
        review_attempts: Maximum review retry attempts (1-5).
        branch_name: Optional branch name for Git operations.
    """

    request_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique request identifier for tracking",
    )
    repository_path: str = Field(
        ...,
        description="Absolute path to the repository",
    )
    seo_payload: SEOPayload = Field(
        ...,
        description="Complete SEO intelligence from n8n",
    )
    csv_path: str | None = Field(
        default=None,
        description="Optional path to CSV input file",
    )
    csv_content: str | None = Field(
        default=None,
        description="Optional raw CSV content string",
    )
    skip_git: bool = Field(
        default=False,
        description="Skip Git operations if True",
    )
    skip_pipeline: bool = Field(
        default=False,
        description="Skip CI/CD pipeline trigger if True",
    )
    max_seo_pages: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum SEO pages to generate",
    )
    review_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum review retry attempts",
    )
    branch_name: str | None = Field(
        default=None,
        max_length=200,
        description="Optional branch name for Git operations",
    )

    @field_validator("repository_path")
    @classmethod
    def validate_repository_path(cls, v: str) -> str:
        """Validate repository path is not empty or whitespace only.

        Args:
            v: The repository path value.

        Returns:
            The trimmed repository path.

        Raises:
            ValueError: If path is empty or whitespace only.
        """
        if not v or not v.strip():
            raise ValueError("repository_path cannot be empty")
        return v.strip()


# Response Models


class FileChange(BaseModel):
    """Represents a file modification made by the SEO agent.

    Attributes:
        file_path: Path to the modified file.
        change_type: Type of change (created, modified, deleted).
        description: Human-readable description of the change.
    """

    file_path: str = Field(
        ...,
        description="Path to the modified file",
    )
    change_type: str = Field(
        ...,
        pattern="^(created|modified|deleted)$",
        description="Type of change",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable change description",
    )


class PageAnalysisResult(BaseModel):
    """Result of analyzing a single page.

    Attributes:
        url: The page URL that was analyzed.
        success: Whether analysis succeeded.
        metadata_updated: Whether metadata was updated.
        error: Error message if analysis failed.
    """

    url: str = Field(
        ...,
        description="The page URL that was analyzed",
    )
    success: bool = Field(
        default=True,
        description="Whether analysis succeeded",
    )
    metadata_updated: bool = Field(
        default=False,
        description="Whether metadata was updated",
    )
    error: str | None = Field(
        default=None,
        description="Error message if analysis failed",
    )


class SEOPageResult(BaseModel):
    """Result of generating an SEO landing page.

    Attributes:
        slug: Page slug/path.
        url: Full URL of the generated page.
        file_path: Physical file path on disk.
        keywords_used: Keywords used in the page content.
        created: Whether page was newly created.
    """

    slug: str = Field(
        ...,
        description="Page slug/path",
    )
    url: str = Field(
        ...,
        description="Full URL of the generated page",
    )
    file_path: str = Field(
        ...,
        description="Physical file path on disk",
    )
    keywords_used: list[str] = Field(
        default_factory=list,
        description="Keywords used in the page",
    )
    created: bool = Field(
        default=True,
        description="Whether page was newly created",
    )


class StageResult(BaseModel):
    """Result of a single workflow stage.

    Attributes:
        stage: Stage name.
        status: Stage execution status.
        started_at: When the stage started.
        completed_at: When the stage completed.
        duration_seconds: Stage duration in seconds.
        message: Optional status message.
        file_changes: Files modified in this stage.
        errors: Errors encountered in this stage.
    """

    stage: str = Field(
        ...,
        description="Stage name",
    )
    status: str = Field(
        ...,
        description="Stage execution status",
    )
    started_at: datetime = Field(
        ...,
        description="When the stage started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When the stage completed",
    )
    duration_seconds: float | None = Field(
        default=None,
        description="Stage duration in seconds",
    )
    message: str | None = Field(
        default=None,
        description="Optional status message",
    )
    file_changes: list[FileChange] = Field(
        default_factory=list,
        description="Files modified in this stage",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Errors encountered in this stage",
    )


class SEOResponse(BaseModel):
    """Complete response model for SEO agent execution.

    This is the response returned to the n8n workflow after
    SEO optimization completes.

    Attributes:
        request_id: The request ID from the original request.
        status: Overall execution status.
        review_status: Status of the review phase.
        started_at: When execution started.
        completed_at: When execution completed.
        duration_seconds: Total execution duration.
        message: Status message or summary.
        stages: Results of each workflow stage.
        pages_analyzed: Results of page analysis.
        pages_generated: Results of SEO page generation.
        file_changes: All file modifications made.
        errors: Errors encountered during execution.
        warnings: Warnings encountered during execution.
    """

    request_id: str = Field(
        ...,
        description="The request ID from the original request",
    )
    status: ExecutionStatus = Field(
        ...,
        description="Overall execution status",
    )
    review_status: ReviewStatus = Field(
        default=ReviewStatus.PENDING,
        description="Status of the review phase",
    )
    started_at: datetime = Field(
        ...,
        description="When execution started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When execution completed",
    )
    duration_seconds: float | None = Field(
        default=None,
        description="Total execution duration in seconds",
    )
    message: str | None = Field(
        default=None,
        description="Status message or summary",
    )
    stages: list[StageResult] = Field(
        default_factory=list,
        description="Results of each workflow stage",
    )
    pages_analyzed: list[PageAnalysisResult] = Field(
        default_factory=list,
        description="Results of page analysis",
    )
    pages_generated: list[SEOPageResult] = Field(
        default_factory=list,
        description="Results of SEO page generation",
    )
    file_changes: list[FileChange] = Field(
        default_factory=list,
        description="All file modifications made",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Errors encountered during execution",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings encountered during execution",
    )


class ErrorResponse(BaseModel):
    """Error response model for API errors.

    Attributes:
        error: Error type/code.
        message: Human-readable error message.
        details: Additional error details.
        request_id: Associated request ID if available.
        timestamp: When the error occurred.
    """

    error: str = Field(
        ...,
        description="Error type/code",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error details",
    )
    request_id: str | None = Field(
        default=None,
        description="Associated request ID if available",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred",
    )


class HealthResponse(BaseModel):
    """Health check response model.

    Attributes:
        status: Service health status.
        version: Application version.
        timestamp: When the health check was performed.
    """

    status: str = Field(
        ...,
        description="Service health status",
    )
    version: str = Field(
        ...,
        description="Application version",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the health check was performed",
    )


class VersionResponse(BaseModel):
    """Version information response model.

    Attributes:
        version: Application version.
        name: Application name.
    """

    version: str = Field(
        ...,
        description="Application version",
    )
    name: str = Field(
        ...,
        description="Application name",
    )