"""Workflow state models.

This module contains domain models for workflow state management
including workflow status, checkpoints, and state transitions.

All models follow SOLID principles with single responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from seo_agent.models.task import ExecutionPlan, ExecutionResult


class WorkflowStatus(Enum):
    """Status of a workflow execution."""

    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    AWAITING_APPROVAL = "awaiting_approval"


class WorkflowEvent(Enum):
    """Events that can occur in a workflow."""

    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    COMPLETE = "complete"
    FAIL = "fail"
    CANCEL = "cancel"
    APPROVE = "approve"
    REJECT = "reject"
    RETRY = "retry"
    TIMEOUT = "timeout"


class WorkflowStage(Enum):
    """Stages of the SEO agent workflow."""

    INITIALIZATION = "initialization"
    REPOSITORY_ANALYSIS = "repository_analysis"
    KEYWORD_RESEARCH = "keyword_research"
    PAGE_ANALYSIS = "page_analysis"
    SEO_PAGE_GENERATION = "seo_page_generation"
    REVIEW = "review"
    GIT_OPERATIONS = "git_operations"
    PIPELINE_TRIGGER = "pipeline_trigger"
    COMPLETION = "completion"


@dataclass(frozen=True)
class WorkflowCheckpoint:
    """A checkpoint in the workflow for recovery.

    Checkpoints save the current state of execution and allow
    resumption from that point.

    Attributes:
        checkpoint_id: Unique checkpoint identifier.
        stage: Current workflow stage.
        status: Workflow status at checkpoint.
        execution_plan: Serialized execution plan.
        task_states: States of all tasks.
        created_at: When checkpoint was created.
        description: Checkpoint description.
    """

    checkpoint_id: str
    stage: WorkflowStage
    status: WorkflowStatus
    execution_plan: dict[str, Any] = field(default_factory=dict)
    task_states: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    description: str = ""


@dataclass(frozen=True)
class WorkflowTransition:
    """A transition between workflow states.

    Records state transitions for audit and debugging.

    Attributes:
        transition_id: Unique transition identifier.
        from_status: Previous workflow status.
        to_status: New workflow status.
        event: Event that triggered transition.
        timestamp: When transition occurred.
        metadata: Additional transition metadata.
    """

    transition_id: str
    from_status: WorkflowStatus
    to_status: WorkflowStatus
    event: WorkflowEvent
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowState:
    """Complete state of a workflow execution.

    This is the central state object that tracks everything about
    a workflow's execution.

    Attributes:
        workflow_id: Unique workflow identifier.
        request_id: Associated request ID.
        status: Current workflow status.
        current_stage: Current execution stage.
        execution_plan: The execution plan being used.
        execution_result: Results accumulated so far.
        checkpoints: Saved checkpoints for recovery.
        transitions: State transition history.
        current_phase_id: ID of currently executing phase.
        current_task_id: ID of currently executing task.
        created_at: When workflow was created.
        updated_at: When workflow was last updated.
        metadata: Additional workflow metadata.
    """

    workflow_id: str
    request_id: str
    status: WorkflowStatus = WorkflowStatus.INITIALIZED
    current_stage: WorkflowStage = WorkflowStage.INITIALIZATION
    execution_plan: ExecutionPlan | None = None
    execution_result: ExecutionResult | None = None
    checkpoints: tuple[WorkflowCheckpoint, ...] = field(default_factory=tuple)
    transitions: tuple[WorkflowTransition, ...] = field(default_factory=tuple)
    current_phase_id: str | None = None
    current_task_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if workflow is in a terminal state."""
        return self.status in (
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        )

    @property
    def is_running(self) -> bool:
        """Check if workflow is currently running."""
        return self.status == WorkflowStatus.RUNNING

    @property
    def can_pause(self) -> bool:
        """Check if workflow can be paused."""
        return self.status == WorkflowStatus.RUNNING

    @property
    def can_resume(self) -> bool:
        """Check if workflow can be resumed."""
        return self.status == WorkflowStatus.PAUSED

    @property
    def can_cancel(self) -> bool:
        """Check if workflow can be cancelled."""
        return self.status in (
            WorkflowStatus.INITIALIZED,
            WorkflowStatus.RUNNING,
            WorkflowStatus.PAUSED,
            WorkflowStatus.AWAITING_APPROVAL,
        )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate workflow duration in seconds."""
        if self.created_at and self.status.is_terminal:
            # Would need completed_at from execution_result
            return None
        return (datetime.utcnow() - self.created_at).total_seconds()

    def get_latest_checkpoint(self) -> WorkflowCheckpoint | None:
        """Get the most recent checkpoint."""
        if not self.checkpoints:
            return None
        return max(self.checkpoints, key=lambda c: c.created_at)

    def get_transition_history(
        self, from_status: WorkflowStatus | None = None
    ) -> tuple[WorkflowTransition, ...]:
        """Get transition history, optionally filtered by status."""
        if from_status is None:
            return self.transitions
        return tuple(
            t for t in self.transitions if t.from_status == from_status
        )


@dataclass(frozen=True)
class WorkflowBuilder:
    """Builder for creating workflow state.

    Provides a fluent interface for constructing WorkflowState objects.

    Attributes:
        workflow_id: Unique workflow identifier.
        request_id: Associated request ID.
    """

    workflow_id: str
    request_id: str

    _status: WorkflowStatus = field(default=WorkflowStatus.INITIALIZED, repr=False)
    _current_stage: WorkflowStage = field(
        default=WorkflowStage.INITIALIZATION, repr=False
    )
    _execution_plan: ExecutionPlan | None = field(default=None, repr=False)
    _metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def with_status(self, status: WorkflowStatus) -> WorkflowBuilder:
        """Set workflow status."""
        return WorkflowBuilder(
            workflow_id=self.workflow_id,
            request_id=self.request_id,
            _status=status,
            _current_stage=self._current_stage,
            _execution_plan=self._execution_plan,
            _metadata=self._metadata,
        )

    def with_stage(self, stage: WorkflowStage) -> WorkflowBuilder:
        """Set current stage."""
        return WorkflowBuilder(
            workflow_id=self.workflow_id,
            request_id=self.request_id,
            _status=self._status,
            _current_stage=stage,
            _execution_plan=self._execution_plan,
            _metadata=self._metadata,
        )

    def with_execution_plan(self, plan: ExecutionPlan) -> WorkflowBuilder:
        """Set execution plan."""
        return WorkflowBuilder(
            workflow_id=self.workflow_id,
            request_id=self.request_id,
            _status=self._status,
            _current_stage=self._current_stage,
            _execution_plan=plan,
            _metadata=self._metadata,
        )

    def with_metadata(self, **kwargs: Any) -> WorkflowBuilder:
        """Add metadata."""
        new_metadata = dict(self._metadata)
        new_metadata.update(kwargs)
        return WorkflowBuilder(
            workflow_id=self.workflow_id,
            request_id=self.request_id,
            _status=self._status,
            _current_stage=self._current_stage,
            _execution_plan=self._execution_plan,
            _metadata=new_metadata,
        )

    def build(self) -> WorkflowState:
        """Build the WorkflowState object."""
        return WorkflowState(
            workflow_id=self.workflow_id,
            request_id=self.request_id,
            status=self._status,
            current_stage=self._current_stage,
            execution_plan=self._execution_plan,
            metadata=self._metadata,
        )