"""Focused unit tests for migrated task and execution domain Pydantic models.

Tests construction, defaults, optional fields, enum fields, nested models,
fluent builder API, calculated properties, dynamic payload dicts, serialization,
deserialization, frozen immutability, and backward compatibility helpers.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
import pytest
from pydantic import ValidationError

from seo_agent.models.enums import TaskPriority, TaskStatus, TaskType
from seo_agent.models.task import (
    Complexity,
    ExecutionContext,
    ExecutionPlan,
    ExecutionResult,
    Phase,
    PhaseResult,
    Task,
    TaskBuilder,
    TaskDependency,
    TaskResult,
)


def test_task_dependency_and_task_construction():
    """Test TaskDependency and Task model construction, defaults, and properties."""
    dep = TaskDependency(task_id="task_001")
    assert dep.task_id == "task_001"
    assert dep.dependency_type == "must_complete"

    task = Task(
        task_id="task_002",
        task_type=TaskType.METADATA_UPDATE,
        description="Update meta tags",
        dependencies=(dep,),
        input_data={"page_path": "about.html"},
    )

    assert task.task_id == "task_002"
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.NORMAL
    assert task.input_data["page_path"] == "about.html"
    assert task.is_complete is False

    with pytest.raises(ValidationError):
        task.status = TaskStatus.COMPLETED


def test_task_builder_fluent_interface():
    """Test TaskBuilder fluent construction of Task objects."""
    task = (
        TaskBuilder("task_003", TaskType.SEO_PAGE_GENERATION, "Generate landing page")
        .with_priority(TaskPriority.HIGH)
        .with_dependency("task_002")
        .with_input(keyword="Recruitment Software", volume=10000)
        .with_max_retries(5)
        .build()
    )

    assert task.task_id == "task_003"
    assert task.task_type == TaskType.SEO_PAGE_GENERATION
    assert task.priority == TaskPriority.HIGH
    assert len(task.dependencies) == 1
    assert task.dependencies[0].task_id == "task_002"
    assert task.input_data["keyword"] == "Recruitment Software"
    assert task.max_retries == 5


def test_phase_and_execution_plan_properties():
    """Test Phase and ExecutionPlan calculated properties and task lookups."""
    t1 = Task("t1", TaskType.KEYWORD_RESEARCH, "Research", status=TaskStatus.COMPLETED)
    t2 = Task("t2", TaskType.PAGE_ANALYSIS, "Analysis", status=TaskStatus.FAILED)

    phase = Phase(
        phase_id="p1",
        name="Discovery Phase",
        description="Initial scan",
        tasks=(t1, t2),
    )

    assert phase.completed_count == 1
    assert phase.failed_count == 1
    assert phase.is_complete is True

    plan = ExecutionPlan(
        request_id="req_777",
        phases=(phase,),
        estimated_duration_seconds=15.0,
    )

    assert plan.total_tasks == 2
    assert plan.completed_tasks == 1
    assert plan.failed_tasks == 1
    assert plan.progress_percentage == 50.0
    assert plan.get_task("t1") == t1
    assert plan.get_phase("p1") == phase


def test_execution_result_properties_and_aggregation():
    """Test ExecutionResult aggregate task counts and status calculation."""
    t1 = Task("t1", TaskType.METADATA_UPDATE, "Update", status=TaskStatus.COMPLETED)
    plan = ExecutionPlan(request_id="req_888", phases=(Phase("p1", "Phase 1", "P1", tasks=(t1,)),))

    tr1 = TaskResult(task_id="t1", success=True)
    pr1 = PhaseResult(phase_id="p1", success=True, task_results=(tr1,))

    res = ExecutionResult(
        request_id="req_888",
        success=True,
        plan=plan,
        phase_results=(pr1,),
        total_duration_seconds=12.5,
    )

    assert res.success is True
    assert res.completed_tasks == 1
    assert res.failed_tasks == 0
    assert res.overall_status == "SUCCESS"
    assert res.execution_time == 12.5


def test_dataclasses_asdict_and_is_dataclass_compatibility():
    """Test dataclasses.asdict() and is_dataclass() compatibility on Task models."""
    dep = TaskDependency(task_id="t_dep")
    assert is_dataclass(dep)

    d = asdict(dep)
    assert isinstance(d, dict)
    assert d["task_id"] == "t_dep"
    assert d["dependency_type"] == "must_complete"
