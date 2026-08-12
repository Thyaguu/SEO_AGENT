"""Unit tests for ExecutionAgent task result aggregation and success state propagation."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from seo_agent.agents.execution.executor import ExecutionAgent, ExecutionConfig
from seo_agent.core.result import Success, Failure
from seo_agent.integrations.opencode.adapter import OpenCodeExecutionResult, FileEditResult
from seo_agent.models.task import (
    Task,
    TaskType,
    TaskPriority,
    TaskStatus,
    Phase,
    ExecutionPlan,
    TaskResult,
    PhaseResult,
)


class TestExecutionResultAggregation:
    @pytest.fixture
    def mock_adapter(self):
        adapter = MagicMock()
        return adapter

    @pytest.fixture
    def agent(self, mock_adapter):
        return ExecutionAgent(
            adapter=mock_adapter,
            config=ExecutionConfig(stop_on_critical_failure=False, workspace_path="/tmp/test_ws"),
        )

    def test_opencode_request_success_leads_to_task_success(self, agent, mock_adapter):
        """Test that a successful OpenCode request creates a successful TaskResult."""
        mock_exec_res = OpenCodeExecutionResult(
            request_id="req_001",
            success=True,
            file_edits=(FileEditResult(file_path="page.html", success=True),),
            duration_seconds=1.5,
        )
        mock_adapter.execute_simple.return_value = Success(mock_exec_res)

        task = Task(
            task_id="task-0001",
            task_type=TaskType.INTERNAL_LINKING,
            description="Test task",
            priority=TaskPriority.HIGH,
            input_data={"instructions": "Add internal link", "file_path": "page.html"},
        )

        plan = ExecutionPlan(
            request_id="req_plan_1",
            phases=(
                Phase(
                    phase_id="phase-1",
                    name="Phase 1",
                    description="Testing phase 1",
                    tasks=(task,),
                ),
            ),
        )

        result = agent.execute(plan)
        assert result.is_success()
        exec_res = result.unwrap()
        assert exec_res.success is True
        assert exec_res.failed_tasks == 0
        assert exec_res.completed_tasks == 1
        assert len(exec_res.phase_results) == 1
        assert exec_res.phase_results[0].success is True

    def test_all_tasks_successful_leads_to_execution_success(self, agent, mock_adapter):
        """Test that when all tasks succeed, overall execution is successful."""
        mock_exec_res = OpenCodeExecutionResult(
            request_id="req_002",
            success=True,
            file_edits=(FileEditResult(file_path="index.html", success=True),),
            duration_seconds=1.0,
        )
        mock_adapter.execute_simple.return_value = Success(mock_exec_res)

        task1 = Task(
            task_id="task-0001",
            task_type=TaskType.INTERNAL_LINKING,
            description="Test task 1",
            priority=TaskPriority.HIGH,
            input_data={"instructions": "Edit index.html", "file_path": "index.html"},
        )
        task2 = Task(
            task_id="task-0002",
            task_type=TaskType.INTERNAL_LINKING,
            description="Test task 2",
            priority=TaskPriority.HIGH,
            input_data={"instructions": "Edit about.html", "file_path": "about.html"},
        )

        plan = ExecutionPlan(
            request_id="req_plan_2",
            phases=(
                Phase(
                    phase_id="phase-1",
                    name="Phase 1",
                    description="Phase 1 Description",
                    tasks=(task1, task2),
                ),
            ),
        )

        result = agent.execute(plan)
        assert result.is_success()
        exec_res = result.unwrap()
        assert exec_res.success is True
        assert exec_res.failed_tasks == 0
        assert exec_res.completed_tasks == 2

    def test_one_task_failed_leads_to_execution_failure(self, agent, mock_adapter):
        """Test that when one task fails, execution is marked as failed."""
        mock_adapter.execute_simple.return_value = Failure("OpenCode error: CLI timed out")

        task = Task(
            task_id="task-0001",
            task_type=TaskType.INTERNAL_LINKING,
            description="Test task",
            priority=TaskPriority.HIGH,
            input_data={"instructions": "Edit index.html", "file_path": "index.html"},
        )

        plan = ExecutionPlan(
            request_id="req_plan_3",
            phases=(
                Phase(
                    phase_id="phase-1",
                    name="Phase 1",
                    description="Phase 1 Description",
                    tasks=(task,),
                ),
            ),
        )

        result = agent.execute(plan)
        assert result.is_success()  # Result container succeeds, but ExecutionResult inside has success=False
        exec_res = result.unwrap()
        assert exec_res.success is False
        assert exec_res.failed_tasks == 1
        assert exec_res.completed_tasks == 0

    def test_mixed_success_failure_counts_correctly(self, agent, mock_adapter):
        """Test that mixed task outcomes result in exact completed vs failed counts."""
        res_ok = Success(
            OpenCodeExecutionResult(
                request_id="req_ok",
                success=True,
                file_edits=(FileEditResult(file_path="a.html", success=True),),
            )
        )
        res_fail = Failure("OpenCode failed on b.html")

        mock_adapter.execute_simple.side_effect = [res_ok, res_fail, res_ok]

        t1 = Task(
            task_id="task-0001",
            task_type=TaskType.INTERNAL_LINKING,
            description="Test task 1",
            priority=TaskPriority.LOW,
            input_data={"instructions": "Edit a.html", "file_path": "a.html"},
        )
        t2 = Task(
            task_id="task-0002",
            task_type=TaskType.INTERNAL_LINKING,
            description="Test task 2",
            priority=TaskPriority.LOW,
            input_data={"instructions": "Edit b.html", "file_path": "b.html"},
        )
        t3 = Task(
            task_id="task-0003",
            task_type=TaskType.INTERNAL_LINKING,
            description="Test task 3",
            priority=TaskPriority.LOW,
            input_data={"instructions": "Edit c.html", "file_path": "c.html"},
        )

        plan = ExecutionPlan(
            request_id="req_plan_4",
            phases=(
                Phase(
                    phase_id="phase-1",
                    name="Phase 1",
                    description="Mixed phase",
                    tasks=(t1, t2, t3),
                ),
            ),
        )

        result = agent.execute(plan)
        assert result.is_success()
        exec_res = result.unwrap()
        assert exec_res.success is False
        assert exec_res.completed_tasks == 2
        assert exec_res.failed_tasks == 1
