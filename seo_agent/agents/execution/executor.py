"""Task executor - executes tasks from planning agent.

This module provides the ExecutionAgent class that executes tasks
from an ExecutionPlan using the OpenCode adapter. It handles:
- Task execution in dependency order
- Sequential and parallel execution modes
- Critical failure handling
- Result aggregation

The executor does NOT:
- Create execution plans (Planning Agent responsibility)
- Modify task definitions
- Perform repository scanning
- Call Git operations
- Perform review operations
- Expose HTTP endpoints
- Contain OpenCode HTTP logic (delegated to OpenCodeAdapter)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from unittest import result

from langgraph.func import task

from seo_agent.core.exceptions import ExecutionError
from seo_agent.core.result import Result, Success, Failure
from seo_agent.integrations.opencode.adapter import (
    OpenCodeAdapter,
    OpenCodeExecutionResult,
    FileEditResult,
    PageGenerationResult,
)
from seo_agent.models.seo import SEOPage, Metadata
from seo_agent.models.task import (
    ExecutionPlan,
    ExecutionResult,
    PhaseResult,
    TaskResult,
    Task,
    TaskStatus,
    TaskType,
    Phase,
)

if TYPE_CHECKING:
    from seo_agent.models.repository import RepositoryInfo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutionConfig:
    """Configuration for task execution.

    Attributes:
        stop_on_critical_failure: Stop execution when a critical task fails.
        max_parallel_tasks: Maximum number of tasks to run in parallel.
        continue_on_warning: Continue execution even if tasks produce warnings.
        workspace_path: Optional workspace path override.
    """

    stop_on_critical_failure: bool = True
    max_parallel_tasks: int = 4
    continue_on_warning: bool = True
    workspace_path: str | None = None


@dataclass
class ExecutionSummary:
    """Summary of execution for a single phase.

    Attributes:
        phase_id: The phase being executed.
        tasks_executed: Number of tasks executed.
        tasks_succeeded: Number of tasks that succeeded.
        tasks_failed: Number of tasks that failed.
        tasks_skipped: Number of tasks skipped.
        total_duration_seconds: Total execution duration.
        file_changes: All file modifications made.
        errors: Errors encountered during execution.
        warnings: Warnings encountered during execution.
    """

    phase_id: str
    tasks_executed: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    tasks_skipped: int = 0
    total_duration_seconds: float = 0.0
    file_changes: list[FileEditResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ExecutionAgent:
    """Agent responsible for executing tasks from an ExecutionPlan.

    The ExecutionAgent takes an ExecutionPlan produced by the Planning Agent
    and executes each task using the OpenCode adapter. It handles:
    - Task execution in dependency order
    - Sequential and parallel execution modes
    - Critical failure handling
    - Result aggregation

    The agent delegates actual OpenCode API calls to the OpenCodeAdapter,
    focusing on orchestration and result aggregation.

    Attributes:
        _adapter: OpenCode adapter for API communication.
        _config: Execution configuration.
        _logger: Logger instance.
    """

    def __init__(
        self,
        adapter: OpenCodeAdapter,
        config: ExecutionConfig | None = None,
    ) -> None:
        """Initialize the execution agent.

        Args:
            adapter: OpenCode adapter for API communication.
            config: Optional execution configuration.

        Raises:
            ExecutionError: If adapter is None.
        """
        if adapter is None:
            raise ExecutionError(
                "OpenCode adapter is required",
                details={"reason": "adapter cannot be None"},
            )

        self._adapter = adapter
        self._config = config or ExecutionConfig()
        self._logger = logger

    def execute(self, plan: ExecutionPlan) -> Result[ExecutionResult, ExecutionError]:
        """Execute all tasks in the execution plan.

        This method orchestrates the execution of all phases and tasks
        in the given execution plan. It handles:
        - Phase-by-phase execution
        - Task dependency resolution within phases
        - Critical failure handling
        - Result aggregation

        Args:
            plan: The execution plan to execute.

        Returns:
            Result containing ExecutionResult on success or ExecutionError on failure.
        """
        if plan is None:
            return Failure(
                ExecutionError(
                    "Execution plan is required",
                    details={"reason": "plan cannot be None"},
                )
            )

        if not plan.phases:
            return Failure(
                ExecutionError(
                    "Execution plan has no phases",
                    details={"request_id": plan.request_id},
                )
            )

        self._logger.debug(
            "Starting execution",
            extra={
                "request_id": plan.request_id,
                "total_phases": len(plan.phases),
                "total_tasks": plan.total_tasks,
            },
        )

        self._logger.debug(
            f"execution_plan_diagnostics: request_id={plan.request_id}, "
            f"phases_count={len(plan.phases)}, total_tasks={plan.total_tasks}"
        )

        started_at = datetime.utcnow()
        phase_results: list[PhaseResult] = []
        all_errors: list[str] = []
        seo_pages_created: list[SEOPage] = []
        seo_pages_removed: list[str] = []
        metadata_updates: list[Metadata] = []

        for phase in plan.phases:
            self._logger.debug(
                "Executing phase",
                extra={
                    "phase_id": phase.phase_id,
                    "phase_name": phase.name,
                    "task_count": len(phase.tasks),
                },
            )

            phase_result = self._execute_phase(
                phase=phase,
                request_id=plan.request_id,
            )

            phase_results.append(phase_result)

            if not phase_result.success:
                all_errors.extend(
                    f"[{phase.phase_id}] {err}" for err in self._extract_phase_errors(phase_result)
                )

                # Phase has no 'critical' field; use config flag to determine stop behavior
                if self._config.stop_on_critical_failure:
                    self._logger.warning(
                        "Phase failed, stopping execution",
                        extra={"phase_id": phase.phase_id},
                    )
                    break

            # Aggregate results from phase
            for task_result in phase_result.task_results:
                if task_result.success and task_result.output:
                    self._aggregate_task_output(
                        task_result=task_result,
                        seo_pages_created=seo_pages_created,
                        seo_pages_removed=seo_pages_removed,
                        metadata_updates=metadata_updates,
                    )

        completed_at = datetime.utcnow()
        total_duration = (completed_at - started_at).total_seconds()

        execution_result = ExecutionResult(
            request_id=plan.request_id,
            success=len(all_errors) == 0,
            plan=plan,
            phase_results=tuple(phase_results),
            repository_info=None,
            seo_pages_created=tuple(seo_pages_created),
            seo_pages_removed=tuple(seo_pages_removed),
            metadata_updates=tuple(metadata_updates),
            total_duration_seconds=total_duration,
            started_at=started_at,
            completed_at=completed_at,
            errors=tuple(all_errors),
        )

        self._logger.debug(
            "Execution completed",
            extra={
                "request_id": plan.request_id,
                "success": execution_result.success,
                "total_duration": total_duration,
                "errors_count": len(all_errors),
            },
        )

        return Success(execution_result)

    def _execute_phase(
        self,
        phase: Phase,
        request_id: str,
    ) -> PhaseResult:
        """Execute all tasks in a phase.

        Args:
            phase: The phase to execute.
            request_id: Request ID for OpenCode calls.

        Returns:
            PhaseResult containing results of all tasks.
        """
        started_at = datetime.utcnow()
        task_results: list[TaskResult] = []
        summary = ExecutionSummary(phase_id=phase.phase_id)

        for task in phase.tasks:
            task_result = self._execute_task(
                task=task,
                request_id=request_id,
                summary=summary,
            )
            task_results.append(task_result)

            if task_result.success:
                summary.tasks_succeeded += 1
            else:
                summary.tasks_failed += 1
                summary.errors.append(f"Task {task.task_id}: {task_result.error}")

                if self._config.stop_on_critical_failure and task.priority.value <= 2:
                    self._logger.warning(
                        "Critical task failed, stopping phase",
                        extra={"task_id": task.task_id},
                    )
                    # Mark remaining tasks as skipped
                    remaining_tasks = phase.tasks[len(task_results):]
                    for remaining_task in remaining_tasks:
                        task_results.append(
                            TaskResult(
                                task_id=remaining_task.task_id,
                                success=False,
                                error="Skipped due to critical failure in phase",
                                duration_seconds=0.0,
                            )
                        )
                        summary.tasks_skipped += 1
                    break

        completed_at = datetime.utcnow()
        duration = (completed_at - started_at).total_seconds()

        return PhaseResult(
            phase_id=phase.phase_id,
            success=summary.tasks_failed == 0,
            task_results=tuple(task_results),
            duration_seconds=duration,
            executed_at=completed_at,
        )

    def _execute_task(
        self,
        task: Task,
        request_id: str,
        summary: ExecutionSummary,
    ) -> TaskResult:
        """Execute a single task.

        Args:
            task: The task to execute.
            request_id: Request ID for OpenCode calls.
            summary: Execution summary to update.

        Returns:
            TaskResult from task execution.
        """
        import threading
        import time

        started_at = datetime.utcnow()
        task_id = f"{request_id}_{task.task_id}"

        task_type_str = task.task_type.value if hasattr(task.task_type, "value") else str(task.task_type)
        target_file_str = str(task.input_data.get("file_path") or task.input_data.get("target_files") or "N/A")
        instructions_str = str(task.input_data.get("instructions", ""))
        prompt_preview = instructions_str[:300]
        start_time_str = started_at.strftime("%Y-%m-%d %H:%M:%S UTC")

        print(
            "------------------------------------------------\n"
            f"Task ID: {task.task_id}\n"
            f"Task Type: {task_type_str}\n"
            f"Target File: {target_file_str}\n"
            f"Prompt Length: {len(instructions_str)}\n"
            f"Prompt Preview (first 300 chars):\n{prompt_preview}\n"
            f"Start Time: {start_time_str}\n"
            "------------------------------------------------",
            flush=True,
        )

        stop_event = threading.Event()

        def _monitor_task() -> None:
            t0 = time.time()
            w30_done = False
            w60_done = False
            while not stop_event.is_set():
                elapsed = time.time() - t0
                if elapsed >= 30 and not w30_done:
                    print("WARNING: Task has been running for more than 30 seconds.", flush=True)
                    w30_done = True
                if elapsed >= 60 and not w60_done:
                    print("Current task still running...", flush=True)
                    w60_done = True
                time.sleep(1.0)

        monitor_thread = threading.Thread(target=_monitor_task, daemon=True)
        monitor_thread.start()

        modified_files: list[str] = []
        is_success = False

        try:
            result = self._dispatch_task(task, task_id)
            if result.is_success():
                execution_result = result.unwrap()
                duration = execution_result.duration_seconds or (datetime.utcnow() - started_at).total_seconds()
                is_success = execution_result.success

                modified_files = [edit.file_path for edit in execution_result.file_edits] + [gen.file_path for gen in execution_result.page_generations]

                # Fallback to task input data target files if generic execution result produced no explicit file edit objects
                if not modified_files and execution_result.success:
                    target_file = task.input_data.get("file_path") or task.input_data.get("target_files")
                    if target_file:
                        if isinstance(target_file, (list, tuple)):
                            modified_files = [str(f) for f in target_file if f]
                        else:
                            modified_files = [str(target_file)]

                # Normalize modified file paths relative to workspace path for consistent reporting
                workspace = self._config.workspace_path or task.input_data.get("workspace_path")
                if workspace and modified_files:
                    from pathlib import Path
                    norm_modified = []
                    ws_path = Path(workspace).resolve()
                    for f_str in modified_files:
                        p = Path(f_str)
                        try:
                            if p.is_absolute():
                                rel_p = p.resolve().relative_to(ws_path)
                                norm_modified.append(str(rel_p))
                            else:
                                norm_modified.append(str(p))
                        except ValueError:
                            norm_modified.append(str(p))
                    modified_files = norm_modified

                summary.file_changes.extend(execution_result.file_edits)
                summary.file_changes.extend(execution_result.page_generations)

                output = self._build_task_output(execution_result)
                if isinstance(output, dict):
                    output["modified_files"] = modified_files
                    if modified_files and "file_path" not in output:
                        output["file_path"] = modified_files[0]

                return TaskResult(
                    task_id=task.task_id,
                    success=execution_result.success,
                    output=output,
                    duration_seconds=duration,
                    executed_at=datetime.utcnow(),
                )
            else:
                is_success = False
                error = result.get_error_or_none() or "Unknown error"
                summary.errors.append(f"Task {task.task_id}: {error}")

                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=error,
                    duration_seconds=(datetime.utcnow() - started_at).total_seconds(),
                    executed_at=datetime.utcnow(),
                )

        except Exception as e:
            is_success = False
            error_msg = f"Task execution failed: {str(e)}"
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=error_msg,
                duration_seconds=(datetime.utcnow() - started_at).total_seconds(),
                executed_at=datetime.utcnow(),
            )
        finally:
            stop_event.set()
            monitor_thread.join(timeout=1.0)

            duration_fin = (datetime.utcnow() - started_at).total_seconds()
            status_str = "SUCCESS" if is_success else "FAILED"
            mod_str = ", ".join(modified_files) if modified_files else "None"

            print(
                "------------------------------------------------\n"
                f"Task ID: {task.task_id}\n"
                f"Execution Time: {duration_fin:.2f}s\n"
                f"Status: {status_str}\n"
                f"Files Modified: {mod_str}\n"
                "------------------------------------------------",
                flush=True,
            )

    def _dispatch_task(
        self,
        task: Task,
        request_id: str,
    ) -> Result[OpenCodeExecutionResult, str]:
        """Dispatch task to appropriate OpenCode adapter method.

        Args:
            task: The task to dispatch.
            request_id: Request ID for OpenCode calls.

        Returns:
            Result containing execution result or error.
        """
        task_type = task.task_type
        input_data = task.input_data
        workspace = self._config.workspace_path or input_data.get("workspace_path")

        if task_type == TaskType.SEO_PAGE_GENERATION:
            return self._execute_seo_page_generation(request_id, input_data, workspace)

        elif task_type in (
            TaskType.METADATA_UPDATE,
            TaskType.SITEMAP_UPDATE,
            TaskType.ROBOTS_UPDATE,
            TaskType.INTERNAL_LINKING,
        ):
            return self._execute_generic_task(request_id, input_data, workspace)

        elif task_type == TaskType.SEO_PAGE_REMOVAL:
            return self._execute_file_removal(request_id, input_data, workspace)

        else:
            return self._execute_generic_task(request_id, input_data, workspace)

    def _execute_seo_page_generation(
        self,
        request_id: str,
        input_data: dict[str, Any],
        workspace: str | None,
    ) -> Result[OpenCodeExecutionResult, str]:
        """Execute SEO page generation task.

        Args:
            request_id: Request ID for OpenCode calls.
            input_data: Task input data containing file_path and content.
            workspace: Optional workspace path.

        Returns:
            Result containing execution result or error.
        """
        file_path = input_data.get("file_path")
        content = input_data.get("content", "")
        instructions = input_data.get(
            "instructions",
            "Generate an SEO-optimized page based on the provided content.",
        )

        if not file_path:
            return Failure("file_path is required for SEO page generation")

        return self._adapter.execute_page_generation(
            request_id=request_id,
            file_path=file_path,
            content=content,
            instructions=instructions,
            workspace_path=workspace,
        )

    def _execute_metadata_update(
        self,
        request_id: str,
        input_data: dict[str, Any],
        workspace: str | None,
    ) -> Result[OpenCodeExecutionResult, str]:
        """Execute a metadata update task via AI-generated instructions.

        Unlike _execute_file_edits() which requires pre-computed content,
        metadata updates delegate content generation to OpenCode by sending
        detailed natural-language instructions built from planning context
        (target page, keywords, missing fields).

        Args:
            request_id: Request ID for OpenCode calls.
            input_data: Task input data with target_files, keywords, and
                instructions assembled by the planning agent.
            workspace: Optional workspace path.

        Returns:
            Result containing execution result or error.
        """
        instructions = input_data.get("instructions")
        if not instructions:
            return Failure("No instructions provided for metadata update task")

        return self._adapter.execute_simple(
            request_id=request_id,
            instructions=instructions,
            workspace_path=workspace,
        )

    def _execute_file_edits(
        self,
        request_id: str,
        input_data: dict[str, Any],
        workspace: str | None,
    ) -> Result[OpenCodeExecutionResult, str]:
        """Execute file edit tasks.

        Args:
            request_id: Request ID for OpenCode calls.
            input_data: Task input data containing edits.
            workspace: Optional workspace path.

        Returns:
            Result containing execution result or error.
        """
        edits = input_data.get("edits", [])

        if not edits:
            return Failure("No edits provided for file edit task")

        # Convert edits to the format expected by adapter
        edit_tuples: list[tuple[str, str, str | None]] = []
        for edit in edits:
            file_path = edit.get("file_path")
            content = edit.get("content", "")
            old_content = edit.get("old_content")

            if file_path:
                edit_tuples.append((file_path, content, old_content))

        if not edit_tuples:
            return Failure("No valid edits found")

        instructions = input_data.get(
            "instructions",
            "Apply the requested file modifications.",
        )

        return self._adapter.execute_file_edits(
            request_id=request_id,
            edits=edit_tuples,
            instructions=instructions,
            workspace_path=workspace,
        )

    def _execute_file_removal(
        self,
        request_id: str,
        input_data: dict[str, Any],
        workspace: str | None,
    ) -> Result[OpenCodeExecutionResult, str]:
        """Execute file removal task.

        Args:
            request_id: Request ID for OpenCode calls.
            input_data: Task input data containing file_path.
            workspace: Optional workspace path.

        Returns:
            Result containing execution result or error.
        """
        file_path = input_data.get("file_path")

        if not file_path:
            return Failure("file_path is required for file removal")

        instructions = input_data.get(
            "instructions",
            f"Remove the file: {file_path}",
        )

        return self._adapter.execute_simple(
            request_id=request_id,
            instructions=instructions,
            workspace_path=workspace,
        )

    def _execute_generic_task(
        self,
        request_id: str,
        input_data: dict[str, Any],
        workspace: str | None,
    ) -> Result[OpenCodeExecutionResult, str]:
        """Execute a generic task.

        Args:
            request_id: Request ID for OpenCode calls.
            input_data: Task input data.
            workspace: Optional workspace path.

        Returns:
            Result containing execution result or error.
        """
        instructions = input_data.get(
            "instructions",
            "Execute the requested task.",
        )

        result = self._adapter.execute_simple(
            request_id=request_id,
            instructions=instructions,
            workspace_path=workspace,
        )
        return result

    def _build_task_output(
        self,
        execution_result: OpenCodeExecutionResult,
    ) -> dict[str, Any]:
        """Build task output from execution result.

        Args:
            execution_result: Result from OpenCode execution.

        Returns:
            Dictionary containing task output data.
        """
        output: dict[str, Any] = {
            "success": execution_result.success,
            "iterations_used": execution_result.iterations_used,
            "duration_seconds": execution_result.duration_seconds,
        }

        if execution_result.file_edits:
            output["file_edits"] = [
                {
                    "file_path": edit.file_path,
                    "success": edit.success,
                    "content": edit.content,
                    "diff": edit.diff,
                    "error": edit.error,
                }
                for edit in execution_result.file_edits
            ]

        if execution_result.page_generations:
            output["page_generations"] = [
                {
                    "file_path": gen.file_path,
                    "success": gen.success,
                    "content": gen.content,
                    "error": gen.error,
                }
                for gen in execution_result.page_generations
            ]

        if execution_result.error:
            output["error"] = execution_result.error
        return output

    def _aggregate_task_output(
        self,
        task_result: TaskResult,
        seo_pages_created: list[SEOPage],
        seo_pages_removed: list[str],
        metadata_updates: list[Metadata],
    ) -> None:
        """Aggregate task output into execution result.

        Args:
            task_result: Result from task execution.
            seo_pages_created: List to append created pages to.
            seo_pages_removed: List to append removed pages to.
            metadata_updates: List to append metadata updates to.
        """
        output = task_result.output

        if not output:
            return

        # Extract SEO pages created
        if "pages_created" in output:
            for page_data in output["pages_created"]:
                if isinstance(page_data, SEOPage):
                    seo_pages_created.append(page_data)
                elif isinstance(page_data, dict):
                    seo_pages_created.append(SEOPage(**page_data))

        # Extract SEO pages removed
        if "pages_removed" in output:
            for page_path in output["pages_removed"]:
                if isinstance(page_path, str):
                    seo_pages_removed.append(page_path)

        # Extract metadata updates
        if "metadata_updates" in output:
            for metadata_data in output["metadata_updates"]:
                if isinstance(metadata_data, Metadata):
                    metadata_updates.append(metadata_data)
                elif isinstance(metadata_data, dict):
                    metadata_updates.append(Metadata(**metadata_data))

    def _extract_phase_errors(self, phase_result: PhaseResult) -> list[str]:
        """Extract all errors from a phase result.

        Args:
            phase_result: The phase result to extract errors from.

        Returns:
            List of error messages.
        """
        errors: list[str] = []

        for task_result in phase_result.task_results:
            if not task_result.success and task_result.error:
                errors.append(task_result.error)

        return errors