"""Domain models package.

This package contains all domain models for the SEO agent, organized
by functional area. All models are frozen dataclasses with slots for
immutability and performance.

Sub-packages:
    seo: SEO data models (keywords, metadata, pages, sitemap, robots)
    repository: Repository analysis models
    api: API request/response models for FastAPI
    review: Review result models
    task: Task and execution models
    workflow: Workflow state models

Example:
    >>> from seo_agent.models import SEOPage, RepositoryInfo, Task
    >>> page = SEOPage(url="https://example.com", ...)
    >>> task = Task(task_id="t1", task_type=TaskType.PAGE_ANALYSIS, ...)
"""

from seo_agent.models.base import BasePydanticModel
from seo_agent.models.seo import (
    ChangeFrequency,
    CompetitorInfo,
    ContentRecommendation,
    FAQItem,
    InternalLink,
    Keyword,
    KeywordType,
    Metadata,
    OpenGraphData,
    RobotsConfig,
    RobotsRule,
    SEOPage,
    SitemapEntry,
    StructuredData,
    TwitterCardData,
)
from seo_agent.models.execution_session import (
    ExecutionIteration,
    ExecutionSession,
    FixTask,
)
from seo_agent.models.repository import (
    FileInfo,
    FrameworkInfo,
    FrameworkType,
    Heading,
    PageAnalysisResult,
    PageInfo,
    PageMetadata,
    PageType,
    RepositoryInfo,
    RepositoryScanOptions,
    RobotsInfo,
    RoutingStrategy,
    SitemapInfo,
)

from seo_agent.models.api import (
    ErrorResponse,
    ExecutionError,
    ExecutionStatusEnum,
    FileChange,
    GitCommitInfo,
    HealthCheckResponse,
    KeywordPayload,
    PageAnalysisResultPayload,
    PipelineInfo,
    PipelineStatusEnum,
    ReviewAttempt,
    ReviewStatusEnum,
    SEOAgentRequest,
    SEOAgentResponse,
    SEOPageResult,
    SEOPayload,
)

from seo_agent.models.review import (
    ContentQualityCheck,
    PageReviewContext,
    ReviewCriteria,
    ReviewDecision,
    ReviewFeedback,
    ReviewResult,
    ReviewSummary,
    SEOQualityCheck,
    ValidationCategory,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

from seo_agent.models.task import (
    ExecutionContext,
    ExecutionPlan,
    ExecutionResult,
    Phase,
    PhaseResult,
    Task,
    TaskBuilder,
    TaskDependency,
    TaskPriority,
    TaskResult,
    TaskStatus,
    TaskType,
)

from seo_agent.models.workflow import (
    WorkflowBuilder,
    WorkflowCheckpoint,
    WorkflowEvent,
    WorkflowStage,
    WorkflowState,
    WorkflowStatus,
    WorkflowTransition,
)

__all__ = [
    "BasePydanticModel",
    # SEO models
    "ChangeFrequency",
    "CompetitorInfo",
    "ContentRecommendation",
    "FAQItem",
    "InternalLink",
    "Keyword",
    "KeywordType",
    "Metadata",
    "OpenGraphData",
    "RobotsConfig",
    "RobotsRule",
    "SEOPage",
    "SitemapEntry",
    "StructuredData",
    "TwitterCardData",
    # Repository models
    "FileInfo",
    "FrameworkInfo",
    "FrameworkType",
    "Heading",
    "PageAnalysisResult",
    "PageInfo",
    "PageMetadata",
    "PageType",
    "RepositoryInfo",
    "RepositoryScanOptions",
    "RobotsInfo",
    "RoutingStrategy",
    "SitemapInfo",
    # API models
    "ErrorResponse",
    "ExecutionError",
    "ExecutionStatusEnum",
    "FileChange",
    "GitCommitInfo",
    "HealthCheckResponse",
    "KeywordPayload",
    "PageAnalysisResultPayload",
    "PipelineInfo",
    "PipelineStatusEnum",
    "ReviewAttempt",
    "ReviewStatusEnum",
    "SEOAgentRequest",
    "SEOAgentResponse",
    "SEOPageResult",
    "SEOPayload",
    # Review models
    "ContentQualityCheck",
    "PageReviewContext",
    "ReviewCriteria",
    "ReviewDecision",
    "ReviewFeedback",
    "ReviewResult",
    "ReviewSummary",
    "SEOQualityCheck",
    "ValidationCategory",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
    # Task models
    "ExecutionContext",
    "ExecutionPlan",
    "ExecutionResult",
    "Phase",
    "PhaseResult",
    "Task",
    "TaskBuilder",
    "TaskDependency",
    "TaskPriority",
    "TaskResult",
    "TaskStatus",
    "TaskType",
    # Workflow models
    "WorkflowBuilder",
    "WorkflowCheckpoint",
    "WorkflowEvent",
    "WorkflowStage",
    "WorkflowState",
    "WorkflowStatus",
    "WorkflowTransition",
    "ExecutionSession",
    "ExecutionIteration",
    "FixTask",
]