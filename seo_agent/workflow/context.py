"""Workflow execution context.

This module provides the WorkflowContext class that holds all shared state
during workflow execution. It acts as a data container that flows between
stages, allowing each stage to read required data and write produced data.

The context is created at workflow start and passed through all stages
until completion or failure.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any
from pydantic import ConfigDict, Field

from seo_agent.models.base import BasePydanticModel

from seo_agent.models.repository import (
    DiscoveredPage,
    FrameworkInfo,
    PageInfo,
    RepositoryInfo,
)
from seo_agent.models.review import ReviewResult
from seo_agent.review.validator import ValidationResult
from seo_agent.models.seo_input import NormalizedSEOEntry, SEOInputCollection
from seo_agent.models.task import ExecutionPlan, ExecutionResult
from seo_agent.models.workflow import WorkflowCheckpoint
from seo_agent.workflow.stages import StageTransition, WorkflowStage


class WorkflowContext(BasePydanticModel):
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

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    repository_path: Path
    stage: WorkflowStage = WorkflowStage.INITIALIZED
    stage_started_at: datetime = Field(default_factory=datetime.utcnow)

    # Stage transition history
    transitions: list[StageTransition] = Field(default_factory=list)

    # Repository data
    repository_info: RepositoryInfo | None = None
    framework_info: FrameworkInfo | None = None
    pages: list[DiscoveredPage] = Field(default_factory=list)
    page_info: list[PageInfo] = Field(default_factory=list)

    # Execution data
    execution_plan: ExecutionPlan | None = None
    execution_result: ExecutionResult | None = None
    review_result: ValidationResult | ReviewResult | None = None

    # Keywords for SEO
    keywords: list[str] = Field(default_factory=list)

    # External SEO Input Data (CSV / JSON)
    seo_input: SEOInputCollection | None = None

    # Checkpointing
    checkpoints: list[WorkflowCheckpoint] = Field(default_factory=list)

    # Errors
    errors: list[str] = Field(default_factory=list)

    # Configuration and metadata
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

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
                getattr(entry, "page_path", None),
                getattr(entry, "url", None),
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
            True if in COMPLETED stage with no errors and no failed execution tasks.
        """
        if self.stage != WorkflowStage.COMPLETED or self.has_errors():
            return False
        if self.execution_result and (not self.execution_result.success or self.execution_result.failed_tasks > 0):
            return False
        return True

    def get_workflow_status(self) -> str:
        """Calculate overall workflow status ("SUCCESS", "PARTIAL SUCCESS", "FAILED")."""
        if self.stage == WorkflowStage.FAILED or (self.has_errors() and not (self.execution_result and self.execution_result.completed_tasks > 0)):
            return "FAILED"
        if self.execution_result:
            if not self.execution_result.success or self.execution_result.failed_tasks > 0:
                if self.execution_result.completed_tasks > 0:
                    return "PARTIAL SUCCESS"
                return "FAILED"
        if self.stage == WorkflowStage.COMPLETED:
            return "SUCCESS"
        return "IN PROGRESS"

    def add_review_result(self, result: ValidationResult | ReviewResult) -> None:
        """Add/set review result."""
        self.review_result = result

    def get_latest_review_result(self) -> Any | None:
        """Get the latest review result."""
        return self.review_result

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

    def set_review_result(self, result: ValidationResult | ReviewResult) -> None:
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

    def get_modified_file_paths(self) -> list[str]:
        """Get the list of unique files that were actually modified on disk.

        Returns:
            Deduplicated list of normalized repository-relative file paths.
        """
        modified: set[str] = set()

        # 1. Extract from execution results
        if self.execution_result and hasattr(self.execution_result, "phase_results"):
            for pr in self.execution_result.phase_results:
                for tr in getattr(pr, "task_results", []):
                    if getattr(tr, "success", False):
                        out = getattr(tr, "output", {}) or {}
                        if isinstance(out, dict):
                            for key in ("file_path", "target_file", "path"):
                                if key in out and out[key]:
                                    modified.add(str(out[key]))
                            if "modified_files" in out and isinstance(out["modified_files"], (list, tuple)):
                                for f in out["modified_files"]:
                                    if f:
                                        modified.add(str(f))

        # 2. Extract from completed tasks in execution plan
        if self.execution_plan and hasattr(self.execution_plan, "phases"):
            completed_task_ids = set()
            if self.execution_result and hasattr(self.execution_result, "phase_results"):
                for pr in self.execution_result.phase_results:
                    for tr in getattr(pr, "task_results", []):
                        if getattr(tr, "success", False):
                            completed_task_ids.add(getattr(tr, "task_id", ""))

            for phase in self.execution_plan.phases:
                for task in phase.tasks:
                    if task.task_id in completed_task_ids:
                        for key in ("file_path", "target_file", "file"):
                            fp = task.input_data.get(key)
                            if fp:
                                modified.add(str(fp))

        # 3. Extract from SEO pages created
        if self.execution_result:
            for page in getattr(self.execution_result, "seo_pages_created", []):
                fp = getattr(page, "file_path", getattr(page, "route_path", None))
                if fp:
                    modified.add(str(fp))

        # Normalize relative to repository_path
        normalized: set[str] = set()
        repo_path_resolved = self.repository_path.resolve()

        for p_str in modified:
            p = Path(p_str)
            try:
                if p.is_absolute():
                    rel_p = p.resolve().relative_to(repo_path_resolved)
                    normalized.add(str(rel_p))
                else:
                    normalized.add(str(p))
            except ValueError:
                normalized.add(p.name)

        # Fallback to discovered page files if execution completed
        if not normalized and self.is_successful() and (self.page_info or self.pages):
            pages_list = self.page_info if self.page_info else self.pages
            for page_obj in pages_list:
                fp = Path(getattr(page_obj, "file_path", ""))
                try:
                    if fp.is_absolute():
                        rel_p = fp.resolve().relative_to(repo_path_resolved)
                        normalized.add(str(rel_p))
                    elif fp.name:
                        normalized.add(fp.name)
                except ValueError:
                    if fp.name:
                        normalized.add(fp.name)

        # Filter out generated reports/metadata assets to count target project files
        filtered_normalized: set[str] = set()
        for rel_path in normalized:
            p_lower = rel_path.lower()
            if p_lower.startswith("reports/") or p_lower.endswith(".csv") or p_lower in ("sitemap.xml", "robots.txt"):
                continue
            filtered_normalized.add(rel_path)

        return sorted(list(filtered_normalized))

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


WorkflowContext.model_rebuild(_types_namespace={"datetime": datetime})