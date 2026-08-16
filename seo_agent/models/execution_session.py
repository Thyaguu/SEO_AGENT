"""Execution Session and Fix Task models.

This module defines models for managing execution sessions, iteration histories,
and structured fix tasks across the Review -> Fix Task -> Execution loop.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from pydantic import ConfigDict, Field

from seo_agent.models.base import BasePydanticModel

if TYPE_CHECKING:
    from seo_agent.models.task import ExecutionResult


class FixTask(BasePydanticModel):
    """Structured task representing a review fix request.

    This model decouples the orchestration layer from specific model prompts,
    passing structured fix requirements (file path, proposed content, review feedback)
    to the ExecutionAgent/OpenCode adapter.

    Attributes:
        task_id: Unique task identifier.
        file_path: Target file path to be fixed.
        current_proposed_content: The latest in-memory proposed file content.
        review_feedback: Message describing the review failure issue.
        suggestions: Optional suggestions for fixing the issue.
        repository_context: Additional metadata/context for the task.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    task_id: str
    file_path: str
    current_proposed_content: str | None = None
    review_feedback: str = ""
    suggestions: str | None = None
    repository_context: dict[str, Any] = Field(default_factory=dict)


class ExecutionIteration(BasePydanticModel):
    """Historical record of a single execution and review attempt.

    Kept exclusively for auditing, metrics, and debugging.
    ApprovedChangesApplier never iterates over history.

    Attributes:
        iteration_number: Iteration sequence index (1-based).
        execution_result: ExecutionResult produced during this attempt.
        review_result: ValidationResult produced by ReviewValidator during this attempt.
        timestamp: Timestamp of when iteration completed.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    iteration_number: int
    execution_result: Any
    review_result: Any | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionSession(BasePydanticModel):
    """Manages active execution state and audit history across review retry attempts.

    Maintains exactly ONE active current_execution_result (replaced on each attempt)
    while storing prior attempts in history for audit/metrics.
    """

    current_execution_result: Any | None = None
    history: list[ExecutionIteration] = Field(default_factory=list)

    def record_attempt(
        self,
        execution_result: Any,
        review_result: Any | None = None,
    ) -> None:
        """Archive the attempt into history and set as current_execution_result.

        Args:
            execution_result: The ExecutionResult from the attempt.
            review_result: The review result from the attempt.
        """
        iteration = ExecutionIteration(
            iteration_number=len(self.history) + 1,
            execution_result=execution_result,
            review_result=review_result,
        )
        self.history.append(iteration)
        self.current_execution_result = execution_result

    @property
    def iteration_count(self) -> int:
        """Total number of execution attempts recorded."""
        return len(self.history)
