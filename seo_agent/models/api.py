"""API request/response models.

This module contains Pydantic models for FastAPI request/response validation.
These models handle the interface between the n8n workflow and the SEO agent.

All models follow SOLID principles with single responsibility.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ExecutionStatusEnum(str, Enum):
    """Status of an SEO agent execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReviewStatusEnum(str, Enum):
    """Status of the review phase."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"


class PipelineStatusEnum(str, Enum):
    """Status of CI/CD pipeline execution."""

    NOT_TRIGGERED = "not_triggered"
    TRIGGERED = "triggered"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# Request Models

class KeywordPayload(BaseModel):
    """Keyword data from n8n payload.

    Attributes:
        term: The keyword or phrase.
        type: primary or secondary.
        search_volume: Monthly search volume.
        difficulty: Keyword difficulty score.
        intent: Search intent.
    """

    term: str = Field(..., min_length=1, max_length=200)
    type: str = Field(default="secondary")
    search_volume: int | None = Field(default=None, ge=0)
    difficulty: float | None = Field(default=None, ge=0, le=100)
    intent: str | None = None


class PagePayload(BaseModel):
    """Page information from n8n payload.

    Attributes:
        url: Target URL for the page.
        title: Page title.
        existing_keywords: Keywords already on the page.
        suggested_keywords: Suggested keywords from n8n.
        content_recommendations: Content optimization suggestions.
    """

    url: str = Field(..., description="Target URL for the page")
    title: str | None = Field(default=None, max_length=200)
    existing_keywords: list[str] = Field(default_factory=list)
    suggested_keywords: list[KeywordPayload] = Field(default_factory=list)
    content_recommendations: list[str] = Field(default_factory=list)


class CompetitorPayload(BaseModel):
    """Competitor information from n8n payload.

    Attributes:
        name: Competitor name.
        strengths: List of competitor strengths.
        notes: Additional notes for comparison.
    """

    name: str = Field(..., min_length=1, max_length=200)
    strengths: list[str] = Field(default_factory=list)
    notes: str | None = None


class SEOPayload(BaseModel):
    """Complete SEO intelligence payload from n8n.

    This is the main input model consumed by the SEO agent.
    All SEO intelligence originates from the n8n workflow.

    Attributes:
        target_urls: List of target URLs to optimize.
        seed_keywords: Primary seed keywords.
        keyword_clusters: Grouped keyword clusters.
        competitors: Competitor information.
        search_intent: Search intent analysis.
        priority_pages: Pages that should be prioritized.
    """

    target_urls: list[str] = Field(..., min_length=1)
    seed_keywords: list[KeywordPayload] = Field(default_factory=list)
    keyword_clusters: dict[str, list[str]] = Field(default_factory=dict)
    competitors: list[CompetitorPayload] = Field(default_factory=list)
    search_intent: dict[str, str] = Field(default_factory=dict)
    priority_pages: list[str] = Field(default_factory=list)


class SEOAgentRequest(BaseModel):
    """Main request model for SEO agent execution.

    Attributes:
        request_id: Unique identifier for this request.
        repository_path: Absolute path to the repository.
        seo_payload: Complete SEO intelligence from n8n.
        skip_git: Skip Git operations if True.
        skip_pipeline: Skip CI/CD pipeline if True.
        max_seo_pages: Maximum SEO pages to generate (default 10).
        review_attempts: Maximum review retry attempts (default 3).
        branch_name: Optional branch name for Git operations.
    """

    request_id: str = Field(..., description="Unique request identifier")
    repository_path: str = Field(..., description="Absolute path to repository")
    seo_payload: SEOPayload = Field(..., description="SEO intelligence from n8n")
    skip_git: bool = Field(default=False, description="Skip Git operations")
    skip_pipeline: bool = Field(default=False, description="Skip CI/CD pipeline")
    max_seo_pages: int = Field(default=10, ge=1, le=50)
    review_attempts: int = Field(default=3, ge=1, le=5)
    branch_name: str | None = Field(default=None, max_length=200)

    @field_validator("repository_path")
    @classmethod
    def validate_repository_path(cls, v: str) -> str:
        """Validate repository path is not empty."""
        if not v or not v.strip():
            raise ValueError("repository_path cannot be empty")
        return v.strip()


# Response Models

class FileChange(BaseModel):
    """Represents a file modification.

    Attributes:
        file_path: Path to the file.
        change_type: created, modified, or deleted.
        description: Human-readable change description.
    """

    file_path: str
    change_type: str = Field(..., pattern="^(created|modified|deleted)$")
    description: str | None = None


class PageAnalysisResultPayload(BaseModel):
    """Result of analyzing a single page.

    Attributes:
        url: The page URL.
        success: Whether analysis succeeded.
        metadata_updated: Whether metadata was updated.
        error: Error message if failed.
    """

    url: str
    success: bool = True
    metadata_updated: bool = False
    error: str | None = None


class SEOPageResult(BaseModel):
    """Result of generating an SEO landing page.

    Attributes:
        slug: Page slug.
        url: Full URL of the page.
        file_path: Physical file path.
        keywords_used: Keywords used in the page.
        created: Whether page was newly created.
    """

    slug: str
    url: str
    file_path: str
    keywords_used: list[str] = Field(default_factory=list)
    created: bool = True


class ReviewAttempt(BaseModel):
    """Record of a single review attempt.

    Attributes:
        attempt_number: Which attempt this is (1-indexed).
        decision: approved or rejected.
        feedback: Review feedback if rejected.
        timestamp: When the review occurred.
    """

    attempt_number: int = Field(..., ge=1)
    decision: str = Field(..., pattern="^(approved|rejected)$")
    feedback: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GitCommitInfo(BaseModel):
    """Git commit information.

    Attributes:
        commit_hash: The commit SHA.
        branch: Branch name.
        message: Commit message.
        author: Author name.
        timestamp: Commit timestamp.
    """

    commit_hash: str | None = None
    branch: str | None = None
    message: str | None = None
    author: str | None = None
    timestamp: datetime | None = None


class PipelineInfo(BaseModel):
    """CI/CD pipeline information.

    Attributes:
        pipeline_id: External pipeline identifier.
        status: Current pipeline status.
        url: Link to pipeline execution.
        triggered_at: When pipeline was triggered.
    """

    pipeline_id: str | None = None
    status: PipelineStatusEnum = PipelineStatusEnum.NOT_TRIGGERED
    url: str | None = None
    triggered_at: datetime | None = None


class ExecutionError(BaseModel):
    """Error information in response.

    Attributes:
        error_type: Type/category of error.
        message: Human-readable error message.
        context: Additional context about the error.
        resolution: Suggested resolution if available.
    """

    error_type: str
    message: str
    context: dict[str, Any] | None = None
    resolution: str | None = None


class SEOAgentResponse(BaseModel):
    """Main response model for SEO agent execution.

    This is the structured response returned to n8n after execution.

    Attributes:
        request_id: The request ID from the original request.
        execution_status: Overall execution status.
        review_status: Status of the review phase.
        repository_path: Path to the repository.
        framework_detected: Framework type detected.
        pages_analyzed: Number of pages analyzed.
        pages_with_metadata_updated: Number of pages with updated metadata.
        seo_pages_generated: Number of SEO pages generated.
        seo_pages_removed: Number of SEO pages removed (due to quota).
        files_created: List of created files.
        files_modified: List of modified files.
        files_deleted: List of deleted files.
        review_attempts: List of all review attempts.
        git_commit: Git commit information if committed.
        pipeline: CI/CD pipeline information.
        execution_duration_seconds: Total execution time.
        errors: List of errors encountered.
        completed_at: Completion timestamp.
    """

    request_id: str
    execution_status: ExecutionStatusEnum
    review_status: ReviewStatusEnum
    repository_path: str
    framework_detected: str | None = None
    pages_analyzed: int = 0
    pages_with_metadata_updated: int = 0
    seo_pages_generated: int = 0
    seo_pages_removed: int = 0
    files_created: list[FileChange] = Field(default_factory=list)
    files_modified: list[FileChange] = Field(default_factory=list)
    files_deleted: list[FileChange] = Field(default_factory=list)
    review_attempts: list[ReviewAttempt] = Field(default_factory=list)
    git_commit: GitCommitInfo | None = None
    pipeline: PipelineInfo | None = None
    execution_duration_seconds: float = 0.0
    errors: list[ExecutionError] = Field(default_factory=list)
    completed_at: datetime | None = None


class HealthCheckResponse(BaseModel):
    """Health check endpoint response.

    Attributes:
        status: Service status (healthy, degraded, unhealthy).
        version: API version.
        timestamp: Current server time.
    """

    status: str = Field(..., pattern="^(healthy|degraded|unhealthy)$")
    version: str = Field(default="1.0.0")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response.

    Attributes:
        error_type: Type of error.
        message: Error message.
        request_id: Associated request ID if available.
        details: Additional error details.
    """

    error_type: str
    message: str
    request_id: str | None = None
    details: dict[str, Any] | None = None