"""Consolidated workflow and domain enums for SEO Agent.

This module aggregates all domain, workflow, task, review, and integration Enums
in a single location while maintaining 100% backward compatibility and exact
enum identity with legacy definitions.
"""

from __future__ import annotations

from seo_agent.api.schemas import (
    ExecutionStatus,
    ReviewStatus,
)
from seo_agent.integrations.opencode.models import (
    OpenCodeAction,
    OpenCodeModel,
    OpenCodeStatus,
)
from seo_agent.models.api import (
    ExecutionStatusEnum,
    PipelineStatusEnum,
    ReviewStatusEnum,
)
from seo_agent.models.repository import (
    FrameworkType,
    PageType,
    RoutingStrategy,
)
from seo_agent.models.review import (
    ReviewDecision,
    ValidationCategory,
    ValidationSeverity,
)
from seo_agent.models.seo import (
    ChangeFrequency,
    KeywordType,
)
from seo_agent.models.task import (
    Complexity,
    TaskPriority,
    TaskStatus,
    TaskType,
)
from seo_agent.models.workflow import (
    WorkflowEvent,
    WorkflowStatus,
)
from seo_agent.workflow.stages import (
    WorkflowStage,
)

__all__ = [
    # Workflow stages & statuses
    "WorkflowStage",
    "WorkflowStatus",
    "WorkflowEvent",
    # Repository enums
    "FrameworkType",
    "RoutingStrategy",
    "PageType",
    # Task enums
    "TaskStatus",
    "TaskPriority",
    "Complexity",
    "TaskType",
    # Review enums
    "ReviewDecision",
    "ValidationSeverity",
    "ValidationCategory",
    # SEO enums
    "KeywordType",
    "ChangeFrequency",
    # API & Schema enums
    "ExecutionStatus",
    "ReviewStatus",
    "ExecutionStatusEnum",
    "ReviewStatusEnum",
    "PipelineStatusEnum",
    # OpenCode integration enums
    "OpenCodeModel",
    "OpenCodeAction",
    "OpenCodeStatus",
]
