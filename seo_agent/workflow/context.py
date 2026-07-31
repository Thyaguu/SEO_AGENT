"""Workflow execution context.

This module provides the WorkflowContext class that holds all shared state
during workflow execution. It acts as a data container that flows between
stages, allowing each stage to read required data and write produced data.

The context is created at workflow start and passed through all stages
until completion or failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from seo_agent.models.repository import (
    DiscoveredPage,
    FrameworkInfo,
    PageInfo,
    RepositoryInfo,
)
from seo_agent.models.review import ReviewResult
from seo_agent.models.seo_input import NormalizedSEOEntry, SEOInputCollection
from seo_agent.models.task import ExecutionPlan, ExecutionResult
from seo_agent.workflow.stages import StageTransition, WorkflowStage

if TYPE_CHECKING:
    from seo_agent.models.workflow import WorkflowCheckpoint


@dataclass
class WorkflowContext:
    """Workflow execution context.

    This class holds all state shared between workflow stages. It is created
    at workflow initialization and updated as each stage executes.

    The context tracks:
    - Repository information (path, framework, pages)
    - Execution data (plan, results)
    - Review feedback
    - Stage transitions and timing
    - Errors and configuration

    Attributes:
        repository_path: Path to the repository being processed.
        stage: Current workflow stage.
        stage_started_at: When the current stage started.
        transitions: History of stage transitions.
        repository_info: Repository analysis results.
        framework_info: Detected framework information.
        pages: Discovered pages.
        page_info: Detailed page information with metadata.
        execution_plan: AI-generated execution plan.
        execution_result: Results from execution agent.
        review_result: Results from review engine.
        keywords: Target keywords for SEO optimization.
        checkpoints: Saved workflow checkpoints.
        errors: Errors encountered during execution.
        config: Additional configuration values.
        metadata: Arbitrary metadata for extensibility.
    """

    repository_path: Path
    stage: WorkflowStage = WorkflowStage.INITIALIZED
    stage_started_at: datetime = field(default_factory=datetime.utcnow)

    # Stage transition history
    transitions: list[StageTransition] = field(default_factory=list)

    # Repository data
    repository_info: RepositoryInfo | None = None
    framework_info: FrameworkInfo | None = None
    pages: list[DiscoveredPage] = field(default_factory=list)
    page_info: list[PageInfo] = field(default_factory=list)

    # Execution data
    execution_plan: ExecutionPlan | None = None
    execution_result: ExecutionResult | None = None
    review_result: ReviewResult | None = None

    # Keywords for SEO
    keywords: list[str] = field(default_factory=list)

    # External SEO Input Data (CSV / JSON)
    seo_input: SEOInputCollection | None = None

    # Checkpointing
    checkpoints: list[WorkflowCheckpoint] = field(default_factory=list)

    # Errors
    errors: list[str] = field(default_factory=list)

    # Configuration and metadata
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_seo_entry_for_page(self, route_or_path: str) -> NormalizedSEOEntry | None:
        """Find a matching normalized SEO entry for a given route or file path.

        Matches by exact route, URL path, file name, or page path stem.
        """
        if not self.seo_input or not self.seo_input.records:
            return None

        clean_target = str(route_or_path).lower().strip("/")
        target_basename = Path(clean_target).name

        for entry in self.seo_input.records:
            candidates = [
                entry.page_path,
                entry.url,
            ]
            for cand in candidates:
                if not cand:
                    continue
                clean_cand = str(cand).lower().strip("/")
                cand_basename = Path(clean_cand).name

                if clean_target == clean_cand or target_basename == cand_basename:
                    return entry
                if clean_target.endswith(clean_cand) or clean_cand.endswith(clean_target):
                    return entry

        return None

    def update_stage(self, new_stage: WorkflowStage) -> None:
        """Update the current stage.

        Records the transition and updates timing.

        Args:
            new_stage: The new workflow stage.
        """
        from seo_agent.workflow.stages import create_transition

        transition = create_transition(
            from_stage=self.stage,
            to_stage=new_stage,
            success=True,
        )
        self.transitions.append(transition)
        self.stage = new_stage
        self.stage_started_at = datetime.utcnow()

    def record_failure(self, error: str) -> None:
        """Record a failure and transition to FAILED stage.

        Args:
            error: Error message describing the failure.
        """
        from seo_agent.workflow.stages import create_transition

        self.errors.append(error)
        transition = create_transition(
            from_stage=self.stage,
            to_stage=WorkflowStage.FAILED,
            success=False,
            error=error,
        )
        self.transitions.append(transition)
        self.stage = WorkflowStage.FAILED
        self.stage_started_at = datetime.utcnow()

    def add_error(self, error: str) -> None:
        """Add an error message without changing stage.

        Args:
            error: Error message to record.
        """
        self.errors.append(error)

    def get_stage_duration(self) -> float:
        """Get duration of current stage in seconds.

        Returns:
            Seconds since the current stage started.
        """
        delta = datetime.utcnow() - self.stage_started_at
        return delta.total_seconds()

    def get_total_duration(self) -> float:
        """Get total workflow duration in seconds.

        Returns:
            Seconds since the first transition, or 0 if no transitions.
        """
        if not self.transitions:
            return 0.0
        first = self.transitions[0].timestamp
        last = self.stage_started_at
        return (last - first).total_seconds()

    def has_errors(self) -> bool:
        """Check if any errors have been recorded.

        Returns:
            True if errors exist, False otherwise.
        """
        return len(self.errors) > 0

    def get_error_summary(self) -> str | None:
        """Get a summary of all errors.

        Returns:
            Formatted error summary, or None if no errors.
        """
        if not self.errors:
            return None
        return "; ".join(self.errors)

    def is_complete(self) -> bool:
        """Check if workflow has completed (success or failure).

        Returns:
            True if in COMPLETED or FAILED stage.
        """
        return self.stage in (WorkflowStage.COMPLETED, WorkflowStage.FAILED)

    def is_successful(self) -> bool:
        """Check if workflow completed successfully.

        Returns:
            True if in COMPLETED stage with no errors.
        """
        return self.stage == WorkflowStage.COMPLETED and not self.has_errors()

    def set_repository_info(self, info: RepositoryInfo) -> None:
        """Set repository information.

        Args:
            info: Repository information from scanner.
        """
        self.repository_info = info

    def set_framework_info(self, info: FrameworkInfo) -> None:
        """Set framework information.

        Args:
            info: Detected framework information.
        """
        self.framework_info = info

    def set_pages(self, pages: list[DiscoveredPage]) -> None:
        """Set discovered pages.

        Args:
            pages: List of discovered pages.
        """
        self.pages = pages

    def set_page_info(self, info: list[PageInfo]) -> None:
        """Set detailed page information.

        Args:
            info: List of page info with metadata.
        """
        self.page_info = info
        if self.repository_info:
            self.repository_info = replace(self.repository_info, pages=tuple(info))

    def set_execution_plan(self, plan: ExecutionPlan) -> None:
        """Set execution plan.

        Args:
            plan: AI-generated execution plan.
        """
        self.execution_plan = plan

    def set_execution_result(self, result: ExecutionResult) -> None:
        """Set execution result.

        Args:
            result: Results from execution agent.
        """
        self.execution_result = result

    def set_review_result(self, result: ReviewResult) -> None:
        """Set review result.

        Args:
            result: Results from review engine.
        """
        self.review_result = result

    def set_keywords(self, keywords: list[str]) -> None:
        """Set target keywords.

        Args:
            keywords: Keywords for SEO optimization.
        """
        self.keywords = keywords

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the workflow context.

        Returns:
            Dictionary with workflow summary.
        """
        return {
            "repository_path": str(self.repository_path),
            "current_stage": self.stage.value,
            "stage_duration": self.get_stage_duration(),
            "total_duration": self.get_total_duration(),
            "transition_count": len(self.transitions),
            "error_count": len(self.errors),
            "has_repository_info": self.repository_info is not None,
            "has_framework_info": self.framework_info is not None,
            "page_count": len(self.page_info),
            "has_execution_plan": self.execution_plan is not None,
            "has_execution_result": self.execution_result is not None,
            "has_review_result": self.review_result is not None,
            "keyword_count": len(self.keywords),
            "is_complete": self.is_complete(),
            "is_successful": self.is_successful(),
        }

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String describing the context state.
        """
        return (
            f"WorkflowContext(path={self.repository_path}, "
            f"stage={self.stage.value}, "
            f"errors={len(self.errors)}, "
            f"transitions={len(self.transitions)})"
        )