"""OpenCode-specific models.

This module defines models for communicating with the OpenCode API.
These models handle request/response serialization and validation.

All models follow SOLID principles with single responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class OpenCodeModel(str, Enum):
    """Available OpenCode models."""

    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"


class OpenCodeAction(str, Enum):
    """Types of actions OpenCode can perform."""

    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EDIT_FILE = "edit_file"
    CREATE_DIRECTORY = "create_directory"
    LIST_DIRECTORY = "list_directory"
    SEARCH_FILES = "search_files"
    EXECUTE_COMMAND = "execute_command"
    BATCH = "batch"


class OpenCodeStatus(str, Enum):
    """Status of an OpenCode execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class OpenCodeFileEdit:
    """Represents a file edit operation.

    Attributes:
        file_path: Path to the file to edit.
        content: New content for the file.
        old_content: Content to replace (for partial edits).
        is_new: Whether this is a new file.
    """

    file_path: str
    content: str
    old_content: str | None = None
    is_new: bool = False


@dataclass(frozen=True)
class OpenCodeFileRead:
    """Represents a file read operation.

    Attributes:
        file_path: Path to the file to read.
        line_start: Starting line number (1-indexed).
        line_end: Ending line number (1-indexed).
    """

    file_path: str
    line_start: int | None = None
    line_end: int | None = None


@dataclass(frozen=True)
class OpenCodeSearchQuery:
    """Represents a file search query.

    Attributes:
        pattern: Search pattern or regex.
        file_pattern: Glob pattern for files to search.
        case_sensitive: Whether search is case-sensitive.
    """

    pattern: str
    file_pattern: str | None = None
    case_sensitive: bool = False


@dataclass(frozen=True)
class OpenCodeActionRequest:
    """Single action request for OpenCode.

    Attributes:
        action: Type of action to perform.
        file_path: Target file path.
        content: Content for write/edit operations.
        old_content: Content to replace.
        search_query: Search query parameters.
        max_results: Maximum results for search operations.
    """

    action: OpenCodeAction
    file_path: str | None = None
    content: str | None = None
    old_content: str | None = None
    search_query: OpenCodeSearchQuery | None = None
    max_results: int = 100


@dataclass(frozen=True)
class OpenCodeRequest:
    """Complete request for OpenCode execution.

    Attributes:
        request_id: Unique request identifier.
        instructions: Natural language instructions for OpenCode.
        actions: List of specific actions to perform.
        model: OpenCode model to use.
        max_iterations: Maximum number of iterations.
        workspace_path: Path to the workspace.
        temperature: Temperature for generation.
    """

    request_id: str
    instructions: str
    actions: tuple[OpenCodeActionRequest, ...] = field(default_factory=tuple)
    model: OpenCodeModel = OpenCodeModel.CLAUDE_3_5_SONNET
    max_iterations: int = 10
    workspace_path: str | None = None
    temperature: float = 0.7
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True)
class OpenCodeFileChange:
    """Represents a file change result.

    Attributes:
        file_path: Path to the changed file.
        change_type: Type of change (created, modified, deleted).
        diff: Diff of changes made.
        content: New content after change.
    """

    file_path: str
    change_type: str
    diff: str | None = None
    content: str | None = None


@dataclass(frozen=True)
class OpenCodeActionResult:
    """Result of a single action.

    Attributes:
        action: The action that was executed.
        success: Whether action succeeded.
        output: Action output data.
        error: Error message if failed.
        file_changes: Files changed by this action.
    """

    action: OpenCodeAction
    success: bool
    output: dict[str, Any] | None = None
    error: str | None = None
    file_changes: tuple[OpenCodeFileChange, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OpenCodeResponse:
    """Complete response from OpenCode execution.

    Attributes:
        request_id: Associated request ID.
        status: Execution status.
        results: Results of all actions.
        total_iterations: Number of iterations used.
        model: Model used for execution.
        error: Error message if overall execution failed.
        started_at: When execution started.
        completed_at: When execution completed.
    """

    request_id: str
    status: OpenCodeStatus
    results: tuple[OpenCodeActionResult, ...] = field(default_factory=tuple)
    total_iterations: int = 0
    model: OpenCodeModel | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    @property
    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == OpenCodeStatus.COMPLETED

    @property
    def duration_seconds(self) -> float | None:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def all_file_changes(self) -> tuple[OpenCodeFileChange, ...]:
        """Get all file changes from all results."""
        changes = []
        for result in self.results:
            changes.extend(result.file_changes)
        return tuple(changes)


@dataclass(frozen=True)
class OpenCodeExecutionContext:
    """Context for OpenCode execution.

    Attributes:
        workspace_path: Path to the workspace.
        repository_url: Optional repository URL.
        branch: Optional branch name.
        commit_sha: Optional commit SHA.
        environment: Environment variables.
    """

    workspace_path: Path
    repository_url: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    environment: dict[str, str] = field(default_factory=dict)