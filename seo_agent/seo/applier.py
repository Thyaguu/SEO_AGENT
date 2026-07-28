"""Approved Changes Applier Service.

This service is responsible for writing approved file modifications to disk
after the Review stage approves an execution result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from seo_agent.core.logging import get_logger
from seo_agent.core.result import Failure, Result, Success
from seo_agent.models.task import ExecutionResult

logger = get_logger(__name__)


@dataclass(frozen=True)
class ApplicationSummary:
    """Summary of applied file changes.

    Attributes:
        files_written: File paths successfully written to disk.
        skipped_files: File paths skipped (e.g. missing content).
        failed_files: File paths that failed execution or writing.
    """

    files_written: tuple[str, ...] = field(default_factory=tuple)
    skipped_files: tuple[str, ...] = field(default_factory=tuple)
    failed_files: tuple[str, ...] = field(default_factory=tuple)

    @property
    def total_written(self) -> int:
        """Total count of written files."""
        return len(self.files_written)


class ApprovedChangesApplier:
    """Applies approved file changes from an ExecutionResult to the repository filesystem.

    This service separates the Review stage (which validates proposed edits)
    from Filesystem Mutation (which writes approved edits to disk prior to Git commit).
    """

    def apply_changes(
        self,
        execution_result: ExecutionResult,
        repository_path: Path,
    ) -> Result[ApplicationSummary, str]:
        """Apply approved file edits to disk inside repository_path.

        Args:
            execution_result: The approved ExecutionResult containing task outputs.
            repository_path: Target repository root directory.

        Returns:
            Success with ApplicationSummary or Failure with error message.
        """
        if not repository_path.exists():
            return Failure(f"Repository path does not exist: {repository_path}")

        repo_root = repository_path.resolve()
        files_written: list[str] = []
        skipped_files: list[str] = []
        failed_files: list[str] = []

        all_entries = []
        for phase_res in execution_result.phase_results:
            for task_res in phase_res.task_results:
                output = task_res.output or {}
                if "file_edits" in output and isinstance(output["file_edits"], list):
                    all_entries.extend(output["file_edits"])
                if "page_generations" in output and isinstance(output["page_generations"], list):
                    all_entries.extend(output["page_generations"])

        logger.debug(
            f"Applying approved changes: incoming_count={len(all_entries)}, "
            f"files={[e.get('file_path') for e in all_entries if isinstance(e, dict)]}"
        )

        try:
            for phase_res in execution_result.phase_results:
                for task_res in phase_res.task_results:
                    output = task_res.output or {}

                    # Collect edit entries from file_edits and page_generations
                    entries: list[dict[str, Any]] = []
                    if "file_edits" in output and isinstance(output["file_edits"], list):
                        entries.extend(output["file_edits"])
                    if "page_generations" in output and isinstance(output["page_generations"], list):
                        entries.extend(output["page_generations"])

                    for entry in entries:
                        if not isinstance(entry, dict):
                            continue

                        file_path_str = entry.get("file_path")
                        success = entry.get("success", False)
                        content = entry.get("content")

                        if not file_path_str:
                            continue

                        if not success:
                            failed_files.append(file_path_str)
                            continue

                        if content is None:
                            skipped_files.append(file_path_str)
                            continue

                        # Resolve absolute target path safely within repo_root
                        rel_path = Path(file_path_str.lstrip("/"))
                        target_file = (repo_root / rel_path).resolve()

                        # Prevent path traversal outside repository root
                        try:
                            target_file.relative_to(repo_root)
                        except ValueError:
                            logger.error(
                                f"Path traversal attempt blocked: {file_path_str}"
                            )
                            failed_files.append(file_path_str)
                            continue

                        # Create parent directories if necessary and write content
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        target_file.write_text(content, encoding="utf-8")
                        files_written.append(str(target_file))

                        logger.info(f"Applied approved change to file: {target_file}")

            summary = ApplicationSummary(
                files_written=tuple(files_written),
                skipped_files=tuple(skipped_files),
                failed_files=tuple(failed_files),
            )

            logger.debug(
                f"Approved changes applied: written={len(files_written)}, "
                f"skipped={len(skipped_files)}, failed={len(failed_files)}"
            )

            logger.info(
                f"Approved changes applied: {summary.total_written} written, "
                f"{len(summary.skipped_files)} skipped, {len(summary.failed_files)} failed"
            )
            return Success(summary)

        except Exception as e:
            logger.exception(f"Error applying approved changes: {e}")
            return Failure(f"Failed to apply approved changes: {e}")
