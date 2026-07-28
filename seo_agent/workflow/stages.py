"""Pipeline stage definitions.

This module defines the workflow stages and provides utilities for
stage transitions and validation. The stages represent the ordered
steps in the SEO agent pipeline.

Stage Order:
    INITIALIZED -> SCANNING -> FRAMEWORK_DETECTION -> PAGE_DISCOVERY
                -> METADATA_EXTRACTION -> PLANNING -> EXECUTION
                -> REVIEW -> SEO_UPDATE -> GIT -> COMPLETED

Errors can occur at any stage and transition to FAILED.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class WorkflowStage(Enum):
    """Stages in the SEO agent workflow pipeline.

    Each stage represents a distinct phase of execution. Stages are
    executed in order, with transitions controlled by the orchestrator.

    Attributes:
        INITIALIZED: Workflow has been created, ready to start.
        SCANNING: Repository filesystem is being scanned.
        FRAMEWORK_DETECTION: Framework type is being detected.
        PAGE_DISCOVERY: Pages/routes are being discovered.
        METADATA_EXTRACTION: Existing page metadata is being extracted.
        PLANNING: Planning agent is creating execution plan.
        EXECUTION: Execution agent is performing file operations.
        REVIEW: Review engine is validating changes.
        SEO_UPDATE: SEO operations (sitemap, robots, metadata).
        GIT: Git operations (commit, push).
        COMPLETED: Workflow finished successfully.
        FAILED: Workflow encountered an error.
    """

    INITIALIZED = "initialized"
    SCANNING = "scanning"
    FRAMEWORK_DETECTION = "framework_detection"
    PAGE_DISCOVERY = "page_discovery"
    METADATA_EXTRACTION = "metadata_extraction"
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"
    SEO_UPDATE = "seo_update"
    GIT = "git"
    COMPLETED = "completed"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal stage."""
        return self in (WorkflowStage.COMPLETED, WorkflowStage.FAILED)

    @property
    def is_execution(self) -> bool:
        """Check if this is an execution stage (AI agent involved)."""
        return self in (WorkflowStage.PLANNING, WorkflowStage.EXECUTION)

    @property
    def display_name(self) -> str:
        """Human-readable stage name."""
        return self.name.replace("_", " ").title()

    @property
    def description(self) -> str:
        """Description of what happens in this stage."""
        descriptions = {
            WorkflowStage.INITIALIZED: "Workflow initialized and ready to start",
            WorkflowStage.SCANNING: "Scanning repository filesystem",
            WorkflowStage.FRAMEWORK_DETECTION: "Detecting framework type",
            WorkflowStage.PAGE_DISCOVERY: "Discovering pages and routes",
            WorkflowStage.METADATA_EXTRACTION: "Extracting existing page metadata",
            WorkflowStage.PLANNING: "Creating execution plan with AI",
            WorkflowStage.EXECUTION: "Executing planned tasks with AI",
            WorkflowStage.REVIEW: "Reviewing and validating changes",
            WorkflowStage.SEO_UPDATE: "Updating SEO files (sitemap, robots)",
            WorkflowStage.GIT: "Performing Git operations",
            WorkflowStage.COMPLETED: "Workflow completed successfully",
            WorkflowStage.FAILED: "Workflow failed",
        }
        return descriptions.get(self, "")


# Valid stage transitions: from_stage -> tuple of valid next stages
STAGE_TRANSITIONS: dict[WorkflowStage, tuple[WorkflowStage, ...]] = {
    WorkflowStage.INITIALIZED: (WorkflowStage.SCANNING, WorkflowStage.FAILED),
    WorkflowStage.SCANNING: (WorkflowStage.FRAMEWORK_DETECTION, WorkflowStage.FAILED),
    WorkflowStage.FRAMEWORK_DETECTION: (WorkflowStage.PAGE_DISCOVERY, WorkflowStage.FAILED),
    WorkflowStage.PAGE_DISCOVERY: (WorkflowStage.METADATA_EXTRACTION, WorkflowStage.FAILED),
    WorkflowStage.METADATA_EXTRACTION: (WorkflowStage.PLANNING, WorkflowStage.FAILED),
    WorkflowStage.PLANNING: (WorkflowStage.EXECUTION, WorkflowStage.FAILED),
    WorkflowStage.EXECUTION: (WorkflowStage.REVIEW, WorkflowStage.FAILED),
    WorkflowStage.REVIEW: (WorkflowStage.SEO_UPDATE, WorkflowStage.FAILED),
    WorkflowStage.SEO_UPDATE: (WorkflowStage.GIT, WorkflowStage.FAILED),
    WorkflowStage.GIT: (WorkflowStage.COMPLETED, WorkflowStage.FAILED),
    WorkflowStage.COMPLETED: tuple(),
    WorkflowStage.FAILED: tuple(),
}


@dataclass(frozen=True)
class StageInfo:
    """Information about a workflow stage.

    Attributes:
        stage: The stage enum value.
        name: Human-readable stage name.
        description: Description of the stage.
        can_retry: Whether this stage can be retried on failure.
        required_data: Data that must be present before entering stage.
        produced_data: Data that this stage produces.
    """

    stage: WorkflowStage
    name: str
    description: str
    can_retry: bool = True
    required_data: tuple[str, ...] = tuple()
    produced_data: tuple[str, ...] = tuple()


# Stage metadata for all stages
STAGE_INFO: dict[WorkflowStage, StageInfo] = {
    WorkflowStage.INITIALIZED: StageInfo(
        stage=WorkflowStage.INITIALIZED,
        name="Initialized",
        description="Workflow has been created and initialized",
        can_retry=False,
        required_data=tuple(),
        produced_data=("repository_path", "configuration"),
    ),
    WorkflowStage.SCANNING: StageInfo(
        stage=WorkflowStage.SCANNING,
        name="Repository Scanning",
        description="Scanning the repository filesystem to understand structure",
        can_retry=True,
        required_data=("repository_path",),
        produced_data=("file_list", "scan_options"),
    ),
    WorkflowStage.FRAMEWORK_DETECTION: StageInfo(
        stage=WorkflowStage.FRAMEWORK_DETECTION,
        name="Framework Detection",
        description="Detecting the framework type and configuration",
        can_retry=True,
        required_data=("repository_path", "file_list"),
        produced_data=("framework_info",),
    ),
    WorkflowStage.PAGE_DISCOVERY: StageInfo(
        stage=WorkflowStage.PAGE_DISCOVERY,
        name="Page Discovery",
        description="Discovering all pages and routes in the repository",
        can_retry=True,
        required_data=("repository_path", "framework_info"),
        produced_data=("discovered_pages",),
    ),
    WorkflowStage.METADATA_EXTRACTION: StageInfo(
        stage=WorkflowStage.METADATA_EXTRACTION,
        name="Metadata Extraction",
        description="Extracting existing SEO metadata from discovered pages",
        can_retry=True,
        required_data=("discovered_pages",),
        produced_data=("page_info",),
    ),
    WorkflowStage.PLANNING: StageInfo(
        stage=WorkflowStage.PLANNING,
        name="Planning",
        description="AI planning agent creates execution plan based on keywords and pages",
        can_retry=True,
        required_data=("page_info", "keywords"),
        produced_data=("execution_plan",),
    ),
    WorkflowStage.EXECUTION: StageInfo(
        stage=WorkflowStage.EXECUTION,
        name="Execution",
        description="AI execution agent performs file operations",
        can_retry=True,
        required_data=("execution_plan", "page_info"),
        produced_data=("execution_result",),
    ),
    WorkflowStage.REVIEW: StageInfo(
        stage=WorkflowStage.REVIEW,
        name="Review",
        description="Review engine validates changes and provides feedback",
        can_retry=True,
        required_data=("execution_result",),
        produced_data=("review_result",),
    ),
    WorkflowStage.SEO_UPDATE: StageInfo(
        stage=WorkflowStage.SEO_UPDATE,
        name="SEO Update",
        description="Updating sitemap, robots.txt, and metadata",
        can_retry=True,
        required_data=("execution_result", "page_info"),
        produced_data=("sitemap_updated", "robots_updated"),
    ),
    WorkflowStage.GIT: StageInfo(
        stage=WorkflowStage.GIT,
        name="Git Operations",
        description="Performing Git commit and push operations",
        can_retry=True,
        required_data=("execution_result",),
        produced_data=("commit_sha",),
    ),
    WorkflowStage.COMPLETED: StageInfo(
        stage=WorkflowStage.COMPLETED,
        name="Completed",
        description="Workflow completed successfully",
        can_retry=False,
        required_data=tuple(),
        produced_data=tuple(),
    ),
    WorkflowStage.FAILED: StageInfo(
        stage=WorkflowStage.FAILED,
        name="Failed",
        description="Workflow failed with an error",
        can_retry=False,
        required_data=tuple(),
        produced_data=tuple(),
    ),
}


def get_next_stage(
    current_stage: WorkflowStage,
    success: bool = True,
) -> WorkflowStage:
    """Get the next stage in the workflow.

    Args:
        current_stage: The current workflow stage.
        success: Whether the current stage completed successfully.

    Returns:
        The next workflow stage.

    Raises:
        ValueError: If no valid transition exists.
    """
    if success:
        valid_next = STAGE_TRANSITIONS.get(current_stage, tuple())
        # For stages with multiple valid next stages, return the primary path
        if WorkflowStage.REVIEW in valid_next:
            return WorkflowStage.SEO_UPDATE
        if valid_next:
            return valid_next[0]
    else:
        return WorkflowStage.FAILED

    raise ValueError(f"No valid transition from stage: {current_stage}")


def can_transition(
    from_stage: WorkflowStage,
    to_stage: WorkflowStage,
) -> bool:
    """Check if a stage transition is valid.

    Args:
        from_stage: The source stage.
        to_stage: The target stage.

    Returns:
        True if the transition is valid, False otherwise.
    """
    valid_next = STAGE_TRANSITIONS.get(from_stage, tuple())
    return to_stage in valid_next


def get_stage_info(stage: WorkflowStage) -> StageInfo:
    """Get information about a stage.

    Args:
        stage: The stage to get info for.

    Returns:
        StageInfo for the stage.
    """
    return STAGE_INFO.get(stage, StageInfo(
        stage=stage,
        name=stage.display_name,
        description=stage.description,
    ))


def get_stage_order() -> tuple[WorkflowStage, ...]:
    """Get the stages in execution order.

    Returns:
        Tuple of stages in the order they should be executed.
        Excludes INITIALIZED (initial state marker) and terminal stages.
    """
    return tuple(s for s in WorkflowStage if not s.is_terminal and s != WorkflowStage.INITIALIZED)


def get_execution_stages() -> tuple[WorkflowStage, ...]:
    """Get only the stages that involve execution (AI agents).

    Returns:
        Tuple of execution stages.
    """
    return tuple(s for s in WorkflowStage if s.is_execution)


@dataclass(frozen=True)
class StageTransition:
    """Represents a stage transition event.

    Attributes:
        from_stage: The stage being transitioned from.
        to_stage: The stage being transitioned to.
        timestamp: When the transition occurred.
        success: Whether the transition was due to successful completion.
        error: Error message if transition was due to failure.
    """

    from_stage: WorkflowStage
    to_stage: WorkflowStage
    timestamp: "datetime"
    success: bool = True
    error: str | None = None


def create_transition(
    from_stage: WorkflowStage,
    to_stage: WorkflowStage,
    success: bool = True,
    error: str | None = None,
) -> StageTransition:
    """Create a new stage transition.

    Args:
        from_stage: The stage being transitioned from.
        to_stage: The stage being transitioned to.
        success: Whether the transition was due to successful completion.
        error: Error message if transition was due to failure.

    Returns:
        A new StageTransition instance.
    """
    from datetime import datetime as dt
    return StageTransition(
        from_stage=from_stage,
        to_stage=to_stage,
        timestamp=dt.utcnow(),
        success=success,
        error=error,
    )