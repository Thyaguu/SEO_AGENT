"""OpenCode response adapter.

This module provides an adapter that converts between domain models
and OpenCode API requests/responses. It follows the adapter pattern
to provide a clean interface for the rest of the application.

The adapter is responsible for:
- Converting domain tasks to OpenCode requests
- Converting OpenCode responses to domain results
- Handling any necessary data transformations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from seo_agent.core.result import Failure, Result, Success
from seo_agent.integrations.opencode.models import (
    OpenCodeAction,
    OpenCodeActionRequest,
)

if TYPE_CHECKING:
    from seo_agent.integrations.opencode.models import (
        OpenCodeRequest,
        OpenCodeResponse,
        OpenCodeStatus,
        OpenCodeFileChange,
        OpenCodeModel,
    )
    from seo_agent.models.task import Task, TaskType, TaskStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileEditResult:
    """Result of a file edit operation.

    Attributes:
        file_path: Path to the edited file.
        success: Whether the edit succeeded.
        content: New content for the file (if available).
        diff: Diff of changes made.
        error: Error message if failed.
    """

    file_path: str
    success: bool
    content: str | None = None
    diff: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class PageGenerationResult:
    """Result of a page generation operation.

    Attributes:
        file_path: Path to the generated page.
        success: Whether generation succeeded.
        content: Generated content.
        metadata: Generated metadata.
        error: Error message if failed.
    """

    file_path: str
    success: bool
    content: str | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None


@dataclass(frozen=True)
class OpenCodeExecutionResult:
    """Complete execution result from OpenCode adapter.

    Attributes:
        request_id: Associated request ID.
        success: Overall success status.
        file_edits: Results of file edit operations.
        page_generations: Results of page generation operations.
        error: Error message if overall execution failed.
        iterations_used: Number of iterations used.
        duration_seconds: Execution duration.
    """

    request_id: str
    success: bool
    file_edits: tuple[FileEditResult, ...] = field(default_factory=tuple)
    page_generations: tuple[PageGenerationResult, ...] = field(default_factory=tuple)
    error: str | None = None
    iterations_used: int = 0
    duration_seconds: float | None = None


class OpenCodeAdapter:
    """Adapter for OpenCode API integration.

    This adapter converts between domain models and OpenCode API
    requests/responses, providing a clean interface for the rest
    of the application.

    The adapter handles:
    - Task-to-request conversion
    - Response-to-result conversion
    - Error handling and normalization
    """

    def __init__(self, client: Any) -> None:
        """Initialize the adapter.

        Args:
            client: OpenCode API client instance.
        """
        self._client = client
        logger.debug("Initialized OpenCode adapter")

    def create_file_edit_request(
        self,
        file_path: str,
        content: str,
        old_content: str | None = None,
    ) -> OpenCodeActionRequest:
        """Create a file edit action request.

        Args:
            file_path: Path to the file to edit.
            content: New content for the file.
            old_content: Content to replace (for partial edits).

        Returns:
            OpenCodeActionRequest for the file edit.
        """
        from seo_agent.integrations.opencode.models import OpenCodeAction, OpenCodeSearchQuery

        return OpenCodeActionRequest(
            action=OpenCodeAction.EDIT_FILE,
            file_path=file_path,
            content=content,
            old_content=old_content,
        )

    def create_file_write_request(
        self,
        file_path: str,
        content: str,
    ) -> OpenCodeActionRequest:
        """Create a file write action request.

        Args:
            file_path: Path to the file to write.
            content: Content to write.

        Returns:
            OpenCodeActionRequest for the file write.
        """
        from seo_agent.integrations.opencode.models import OpenCodeAction

        return OpenCodeActionRequest(
            action=OpenCodeAction.WRITE_FILE,
            file_path=file_path,
            content=content,
        )

    def create_batch_request(
        self,
        request_id: str,
        instructions: str,
        actions: list[OpenCodeActionRequest],
        workspace_path: str | None = None,
        model: str | None = None,
    ) -> OpenCodeRequest:
        """Create a batch request with multiple actions.

        Args:
            request_id: Unique request identifier.
            instructions: Natural language instructions.
            actions: List of actions to perform.
            workspace_path: Optional workspace path.
            model: Optional model override.

        Returns:
            OpenCodeRequest for batch execution.
        """
        from seo_agent.integrations.opencode.models import (
            OpenCodeRequest,
            OpenCodeModel,
        )

        return OpenCodeRequest(
            request_id=request_id,
            instructions=instructions,
            actions=tuple(actions),
            workspace_path=workspace_path,
            model=OpenCodeModel(model) if model else OpenCodeModel.CLAUDE_3_5_SONNET,
        )

    def execute_file_edits(
        self,
        request_id: str,
        edits: list[tuple[str, str, str | None]],
        instructions: str,
        workspace_path: str | None = None,
    ) -> Result[OpenCodeExecutionResult, str]:
        """Execute multiple file edits.

        Args:
            request_id: Unique request identifier.
            edits: List of (file_path, content, old_content) tuples.
            instructions: Natural language instructions.
            workspace_path: Optional workspace path.

        Returns:
            Result containing execution result or error.
        """
        actions = []
        for file_path, content, old_content in edits:
            action = self.create_file_edit_request(file_path, content, old_content)
            actions.append(action)

        request = self.create_batch_request(
            request_id=request_id,
            instructions=instructions,
            actions=actions,
            workspace_path=workspace_path,
        )

        result = self._client.execute(request)
        return self._convert_response_to_result(result)

    def execute_page_generation(
        self,
        request_id: str,
        file_path: str,
        content: str,
        instructions: str,
        workspace_path: str | None = None,
    ) -> Result[OpenCodeExecutionResult, str]:
        """Execute a page generation operation.

        Args:
            request_id: Unique request identifier.
            file_path: Path where the page should be generated.
            content: Initial content for the page.
            instructions: Natural language instructions for generation.
            workspace_path: Optional workspace path.

        Returns:
            Result containing execution result or error.
        """
        action = self.create_file_write_request(file_path, content)

        request = self.create_batch_request(
            request_id=request_id,
            instructions=instructions,
            actions=[action],
            workspace_path=workspace_path,
        )

        result = self._client.execute(request)
        return self._convert_response_to_result(result)

    def execute_simple(
        self,
        request_id: str,
        instructions: str,
        workspace_path: str | None = None,
    ) -> Result[OpenCodeExecutionResult, str]:
        """Execute a simple instruction without specific file operations.

        Args:
            request_id: Unique request identifier.
            instructions: Natural language instructions.
            workspace_path: Optional workspace path.

        Returns:
            Result containing execution result or error.
        """
        result = self._client.execute_simple(
            instructions=instructions,
            workspace_path=workspace_path,
        )
        return self._convert_response_to_result(result)

    def _convert_response_to_result(
        self,
        response_result: Result[OpenCodeResponse, str],
    ) -> Result[OpenCodeExecutionResult, str]:
        """Convert an OpenCode response to an execution result.

        Args:
            response_result: Result from the OpenCode client.

        Returns:
            Result containing execution result or error.
        """
        if response_result.is_failure():
            return Failure(response_result.get_error_or_none() or "Unknown error")

        response = response_result.unwrap()

        # Convert file changes to results
        file_edits = []
        page_generations = []

        for action_result in response.results:
            for file_change in action_result.file_changes:
                if action_result.action.value == "write_file":
                    page_generations.append(
                        PageGenerationResult(
                            file_path=file_change.file_path,
                            success=action_result.success,
                            content=file_change.content,
                            error=action_result.error,
                        )
                    )
                else:
                    file_edits.append(
                        FileEditResult(
                            file_path=file_change.file_path,
                            success=action_result.success,
                            content=file_change.content,
                            diff=file_change.diff,
                            error=action_result.error,
                        )
                    )

        execution_result = OpenCodeExecutionResult(
            request_id=response.request_id,
            success=response.is_success,
            file_edits=tuple(file_edits),
            page_generations=tuple(page_generations),
            error=response.error,
            iterations_used=response.total_iterations,
            duration_seconds=response.duration_seconds,
        )

        if response.is_success:
            return Success(execution_result)
        else:
            return Failure(response.error or "Execution failed")

    def convert_task_to_request(
        self,
        task: Task,
        workspace_path: str,
    ) -> Result[OpenCodeRequest, str]:
        """Convert a domain task to an OpenCode request.

        Args:
            task: The domain task to convert.
            workspace_path: Path to the workspace.

        Returns:
            Result containing the OpenCode request or error.
        """
        from seo_agent.integrations.opencode.models import (
            OpenCodeRequest,
            OpenCodeModel,
            OpenCodeAction,
        )

        task_type = task.task_type
        input_data = task.input_data

        # Map task types to instructions
        instructions = self._generate_instructions(task_type, input_data)
        if instructions is None:
            return Failure(f"Unsupported task type: {task_type}")

        # Build actions based on task type
        actions = self._build_actions_for_task(task_type, input_data)

        request = OpenCodeRequest(
            request_id=task.task_id,
            instructions=instructions,
            actions=tuple(actions),
            workspace_path=workspace_path,
        )

        return Success(request)

    def _generate_instructions(
        self,
        task_type: TaskType,
        input_data: dict[str, Any],
    ) -> str | None:
        """Generate instructions for a task type.

        Args:
            task_type: Type of task.
            input_data: Task input data.

        Returns:
            Generated instructions or None if unsupported.
        """
        from seo_agent.models.task import TaskType

        if "fix_task" in input_data and isinstance(input_data["fix_task"], dict):
            ft = input_data["fix_task"]
            fp = ft.get("file_path", "unknown")
            feedback = ft.get("review_feedback", "")
            suggestions = ft.get("suggestions", "")
            prop_content = ft.get("current_proposed_content")

            instr = f"Fix the review failure issue in '{fp}': {feedback}."
            if suggestions:
                instr += f" Suggestion: {suggestions}."
            if prop_content:
                instr += f"\n\n[PREVIOUS PROPOSED CONTENT FOR '{fp}']:\n{prop_content}"
            return instr

        instructions_map = {
            TaskType.METADATA_UPDATE: (
                f"Update the metadata for the page at {input_data.get('file_path', 'unknown')}. "
                f"Title: {input_data.get('title', '')}. "
                f"Description: {input_data.get('description', '')}. "
                f"Keywords: {', '.join(input_data.get('keywords', []))}."
            ),
            TaskType.SEO_PAGE_GENERATION: (
                f"Generate an SEO-optimized page at {input_data.get('file_path', 'unknown')}. "
                f"Topic: {input_data.get('topic', '')}. "
                f"Keywords: {', '.join(input_data.get('keywords', []))}."
            ),
            TaskType.SITEMAP_UPDATE: (
                f"Update the sitemap at {input_data.get('sitemap_path', 'unknown')} "
                f"to include: {', '.join(input_data.get('urls', []))}."
            ),
            TaskType.ROBOTS_UPDATE: (
                f"Update the robots.txt at {input_data.get('robots_path', 'unknown')} "
                f"with rules: {input_data.get('rules', [])}."
            ),
        }

        return instructions_map.get(task_type)

    def _build_opencode_actions(
        self,
        task_type: TaskType,
        input_data: dict[str, Any],
    ) -> list[OpenCodeActionRequest]:
        """Build OpenCode actions for a task.

        Args:
            task_type: Type of task.
            input_data: Task input data.

        Returns:
            List of OpenCode action requests.
        """
        from seo_agent.integrations.opencode.models import OpenCodeAction

        actions = []

        if task_type.value in ("metadata_update", "seo_page_generation"):
            file_path = input_data.get("file_path")
            content = input_data.get("content", "")

            if task_type.value == "seo_page_generation" and not content and file_path:
                kw = input_data.get("primary_keyword", "SEO Solutions")
                content = (
                    f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
                    f"    <meta charset=\"UTF-8\">\n"
                    f"    <title>{kw} | Enterprise SEO Solutions</title>\n"
                    f"    <meta name=\"description\" content=\"Comprehensive guide and enterprise services for {kw}.\">\n"
                    f"    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
                    f"</head>\n<body>\n"
                    f"    <header>\n        <h1>{kw}</h1>\n    </header>\n"
                    f"    <main>\n"
                    f"        <section>\n"
                    f"            <h2>Overview</h2>\n"
                    f"            <p>Welcome to our dedicated page for {kw}. Streamline your enterprise workflow with specialized solutions.</p>\n"
                    f"        </section>\n"
                    f"    </main>\n"
                    f"</body>\n</html>"
                )

            if file_path:
                actions.append(
                    OpenCodeActionRequest(
                        action=OpenCodeAction.WRITE_FILE,
                        file_path=file_path,
                        content=content,
                    )
                )

        return actions

    def health_check(self) -> Result[bool, str]:
        """Check if the OpenCode service is healthy.

        Returns:
            Result indicating service health.
        """
        return self._client.health_check()