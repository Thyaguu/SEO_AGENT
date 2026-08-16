"""Task and execution models.

This module contains domain models for task management and execution
planning including tasks, execution plans, and results.

All models follow SOLID principles with single responsibility.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from pydantic import ConfigDict, Field, PrivateAttr

from seo_agent.models.base import BasePydanticModel

from seo_agent.models.seo import SEOPage, Metadata
from seo_agent.models.repository import RepositoryInfo


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Priority level for tasks."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class Complexity(Enum):
    """Complexity level for tasks.

    Used to estimate execution time and resource requirements.
    """

    TRIVIAL = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    COMPLEX = 5


class TaskType(Enum):
    """Types of tasks in the SEO agent."""

    REPOSITORY_ANALYSIS = "repository_analysis"
    KEYWORD_RESEARCH = "keyword_research"
    PAGE_ANALYSIS = "page_analysis"
    METADATA_UPDATE = "metadata_update"
    SEO_PAGE_GENERATION = "seo_page_generation"
    SEO_PAGE_REMOVAL = "seo_page_removal"
    SITEMAP_UPDATE = "sitemap_update"
    ROBOTS_UPDATE = "robots_update"
    INTERNAL_LINKING = "internal_linking"
    REVIEW = "review"
    GIT_COMMIT = "git_commit"
    PIPELINE_TRIGGER = "pipeline_trigger"
    VALIDATION = "validation"


class TaskDependency(BasePydanticModel):
    """Represents a dependency on another task.

    Attributes:
        task_id: ID of the dependent task.
        dependency_type: Type of dependency (must_complete, must_succeed).
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
    dependency_type: str = "must_complete"


class Task(BasePydanticModel):
    """Represents a single executable task.

    Tasks are the atomic units of work in the SEO agent execution.

    Attributes:
        task_id: Unique identifier for the task.
        task_type: Type of task to execute.
        description: Human-readable task description.
        status: Current task status.
        priority: Task priority level.
        dependencies: Tasks that must complete before this one.
        input_data: Input data required for task execution.
        output_data: Output data from task execution.
        error: Error message if task failed.
        started_at: When task execution started.
        completed_at: When task execution completed.
        retry_count: Number of times task was retried.
        max_retries: Maximum retry attempts allowed.
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
    task_type: TaskType
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: tuple[TaskDependency, ...] = ()
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3

    @property
    def is_complete(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.SKIPPED,
            TaskStatus.CANCELLED,
        )

    @property
    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return (
            self.status == TaskStatus.FAILED
            and self.retry_count < self.max_retries
        )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class Phase(BasePydanticModel):
    """A phase containing multiple tasks.

    Phases group related tasks and can have their own status.

    Attributes:
        phase_id: Unique identifier for the phase.
        name: Phase name.
        description: Phase description.
        tasks: Tasks in this phase.
        status: Current phase status.
        started_at: When phase started.
        completed_at: When phase completed.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    phase_id: str
    name: str
    description: str
    tasks: tuple[Task, ...] = ()
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def is_complete(self) -> bool:
        """Check if all tasks in phase are complete."""
        return all(t.is_complete for t in self.tasks)

    @property
    def completed_count(self) -> int:
        """Count of completed tasks."""
        return sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        """Count of failed tasks."""
        return sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)


class ExecutionPlan(BasePydanticModel):
    """Complete execution plan for SEO agent.

    The execution plan organizes tasks into phases and defines
    the order of execution.

    Attributes:
        request_id: Associated request ID.
        phases: Ordered list of execution phases.
        estimated_duration_seconds: Estimated total execution time.
        created_at: When plan was created.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    request_id: str
    phases: tuple[Phase, ...] = ()
    estimated_duration_seconds: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def all_tasks(self) -> tuple[Task, ...]:
        """Get all tasks across all phases."""
        return tuple(task for phase in self.phases for task in phase.tasks)

    @property
    def total_tasks(self) -> int:
        """Count total tasks."""
        return sum(len(p.tasks) for p in self.phases)

    @property
    def completed_tasks(self) -> int:
        """Count completed tasks."""
        return sum(p.completed_count for p in self.phases)

    @property
    def failed_tasks(self) -> int:
        """Count failed tasks."""
        return sum(p.failed_count for p in self.phases)

    @property
    def progress_percentage(self) -> float:
        """Calculate overall progress percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100

    def get_task(self, task_id: str) -> Task | None:
        """Find a task by ID."""
        for task in self.all_tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_phase(self, phase_id: str) -> Phase | None:
        """Find a phase by ID."""
        for phase in self.phases:
            if phase.phase_id == phase_id:
                return phase
        return None


class TaskResult(BasePydanticModel):
    """Result of executing a single task.

    Attributes:
        task_id: The task that was executed.
        success: Whether task succeeded.
        output: Task output data.
        error: Error message if failed.
        duration_seconds: Task execution duration.
        executed_at: When task was executed.
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
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0
    executed_at: datetime = Field(default_factory=datetime.utcnow)


class PhaseResult(BasePydanticModel):
    """Result of executing a phase.

    Attributes:
        phase_id: The phase that was executed.
        success: Whether all tasks in phase succeeded.
        task_results: Results of individual tasks.
        duration_seconds: Phase execution duration.
        executed_at: When phase was executed.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    phase_id: str
    success: bool
    task_results: tuple[TaskResult, ...] = ()
    duration_seconds: float = 0.0
    executed_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionResult(BasePydanticModel):
    """Complete result of executing the SEO agent.

    Attributes:
        request_id: Associated request ID.
        success: Whether execution succeeded overall.
        plan: The execution plan that was used.
        phase_results: Results of each phase.
        repository_info: Repository analysis results.
        seo_pages_created: SEO pages that were created.
        seo_pages_removed: SEO pages that were removed.
        metadata_updates: Metadata updates that were made.
        total_duration_seconds: Total execution duration.
        started_at: When execution started.
        completed_at: When execution completed.
        errors: List of errors encountered.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    request_id: str
    success: bool
    plan: ExecutionPlan | None = None
    phase_results: tuple[PhaseResult, ...] = ()
    repository_info: RepositoryInfo | None = None
    seo_pages_created: tuple[SEOPage, ...] = ()
    seo_pages_removed: tuple[str, ...] = ()
    metadata_updates: tuple[Metadata, ...] = ()
    total_duration_seconds: float = 0.0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    errors: tuple[str, ...] = ()

    @property
    def pages_created_count(self) -> int:
        """Count of SEO pages created."""
        return len(self.seo_pages_created)

    @property
    def pages_removed_count(self) -> int:
        """Count of SEO pages removed."""
        return len(self.seo_pages_removed)

    @property
    def metadata_updates_count(self) -> int:
        """Count of metadata updates."""
        return len(self.metadata_updates)

    @property
    def completed_tasks(self) -> int:
        """Count of completed tasks across all phases."""
        count = 0
        for pr in self.phase_results:
            count += sum(1 for tr in getattr(pr, "task_results", []) if getattr(tr, "success", False))
        return count

    @property
    def failed_tasks(self) -> int:
        """Count of failed tasks across all phases."""
        count = 0
        for pr in self.phase_results:
            count += sum(1 for tr in getattr(pr, "task_results", []) if not getattr(tr, "success", False))
        return count

    @property
    def skipped_tasks(self) -> int:
        """Count of skipped tasks across all phases."""
        count = 0
        for pr in self.phase_results:
            count += sum(1 for tr in getattr(pr, "task_results", []) if getattr(tr, "status", None) == TaskStatus.SKIPPED)
        return count

    @property
    def total_tasks(self) -> int:
        """Total task count across all phases or plan."""
        if self.plan and hasattr(self.plan, "total_tasks"):
            return self.plan.total_tasks
        return self.completed_tasks + self.failed_tasks + self.skipped_tasks

    @property
    def overall_status(self) -> str:
        """Overall status label."""
        if not self.success or self.failed_tasks > 0:
            return "FAILED" if self.completed_tasks == 0 else "PARTIAL SUCCESS"
        return "SUCCESS"

    @property
    def execution_time(self) -> float:
        """Execution time in seconds."""
        return self.total_duration_seconds


class ExecutionContext(BasePydanticModel):
    """Context passed to task executors.

    This object is passed to all task executors and provides
    access to shared resources and state.

    Attributes:
        request_id: Associated request ID.
        repository_path: Path to the repository.
        repository_info: Cached repository analysis.
        seo_payload: SEO intelligence from n8n.
        execution_result: Current execution result being built.
        skip_git: Whether to skip Git operations.
        skip_pipeline: Whether to skip CI/CD pipeline.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=False,
        extra="ignore",
    )

    request_id: str
    repository_path: str
    repository_info: RepositoryInfo | None = None
    seo_payload: dict[str, Any] = Field(default_factory=dict)
    execution_result: ExecutionResult | None = None
    skip_git: bool = False
    skip_pipeline: bool = False


class TaskBuilder(BasePydanticModel):
    """Builder for creating tasks with fluent interface.

    This class provides a convenient way to construct Task objects
    with common defaults.

    Attributes:
        task_id: Unique task identifier.
        task_type: Type of task.
        description: Task description.
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
    task_type: TaskType
    description: str
    _priority: TaskPriority = PrivateAttr(default=TaskPriority.NORMAL)
    _dependencies: list[TaskDependency] = PrivateAttr(default_factory=list)
    _input_data: dict[str, Any] = PrivateAttr(default_factory=dict)
    _max_retries: int = PrivateAttr(default=3)

    def with_priority(self, priority: TaskPriority) -> TaskBuilder:
        """Set task priority."""
        tb = TaskBuilder(
            task_id=self.task_id,
            task_type=self.task_type,
            description=self.description,
        )
        tb._priority = priority
        tb._dependencies = list(self._dependencies)
        tb._input_data = dict(self._input_data)
        tb._max_retries = self._max_retries
        return tb

    def with_dependency(self, task_id: str) -> TaskBuilder:
        """Add a task dependency."""
        new_deps = list(self._dependencies)
        new_deps.append(TaskDependency(task_id=task_id))
        tb = TaskBuilder(
            task_id=self.task_id,
            task_type=self.task_type,
            description=self.description,
        )
        tb._priority = self._priority
        tb._dependencies = new_deps
        tb._input_data = dict(self._input_data)
        tb._max_retries = self._max_retries
        return tb

    def with_input(self, **kwargs: Any) -> TaskBuilder:
        """Add input data."""
        new_input = dict(self._input_data)
        new_input.update(kwargs)
        tb = TaskBuilder(
            task_id=self.task_id,
            task_type=self.task_type,
            description=self.description,
        )
        tb._priority = self._priority
        tb._dependencies = list(self._dependencies)
        tb._input_data = new_input
        tb._max_retries = self._max_retries
        return tb

    def with_max_retries(self, max_retries: int) -> TaskBuilder:
        """Set maximum retry attempts."""
        tb = TaskBuilder(
            task_id=self.task_id,
            task_type=self.task_type,
            description=self.description,
        )
        tb._priority = self._priority
        tb._dependencies = list(self._dependencies)
        tb._input_data = dict(self._input_data)
        tb._max_retries = max_retries
        return tb

    def build(self) -> Task:
        """Build the Task object."""
        return Task(
            task_id=self.task_id,
            task_type=self.task_type,
            description=self.description,
            priority=self._priority,
            dependencies=tuple(self._dependencies),
            input_data=self._input_data,
            max_retries=self._max_retries,
        )