"""Git client wrapper.

This module provides a Git client that wraps GitPython to offer a safe,
high-level interface for Git operations. It focuses on read operations
and repository introspection without modifying state.

Usage:
    client = GitClient()
    result = client.open_repository("/path/to/repo")
    if result.is_success():
        repo = result.value
        branch = client.get_current_branch(repo)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import git
from git import Repo

from seo_agent.core.exceptions import GitError
from seo_agent.core.logging import get_logger
from seo_agent.core.result import Failure, Result, Success

if TYPE_CHECKING:
    from git import Repo

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RepositoryStatus:
    """Represents the current status of a Git repository.

    Attributes:
        is_clean: True if there are no uncommitted changes.
        is_dirty: True if there are uncommitted changes.
        staged_files: List of files staged for commit.
        modified_files: List of files with uncommitted changes.
        untracked_files: List of untracked files.
        current_branch: Name of the current branch.
    """

    is_clean: bool
    is_dirty: bool
    staged_files: list[str]
    modified_files: list[str]
    untracked_files: list[str]
    current_branch: str


class GitClient:
    """Client for Git repository operations.

    This class provides a safe, high-level interface for Git operations.
    It wraps GitPython to offer a consistent API with proper error handling
    and logging.

    All operations return Result types for explicit error handling.
    """

    def open_repository(self, path: Path | str) -> Result[Repo, GitError]:
        """Open a Git repository at the given path.

        Args:
            path: Path to the repository root.

        Returns:
            Success with Repo instance if path is a valid Git repository.
            Failure with GitError if path is invalid or not a Git repo.
        """
        try:
            path_str = str(path)
            repo = Repo(path_str, search_parent_directories=True)

            if repo.bare:
                return Failure(
                    GitError(f"Repository at {path} is bare and cannot be used"),
                    details={"path": path_str},
                )

            logger.info(f"Opened repository: {path_str}")
            return Success(repo)

        except git.InvalidGitRepositoryError:
            return Failure(
                GitError(
                    f"Path is not a valid Git repository: {path}",
                    details={"path": str(path)},
                )
            )
        except Exception as e:
            return Failure(
                GitError(f"Failed to open repository: {e}", details={"path": str(path)})
            )

    def validate_repository(self, path: Path | str) -> Result[bool, GitError]:
        """Validate that a path is a valid Git repository.

        Args:
            path: Path to validate.

        Returns:
            Success with True if path is a valid Git repository.
            Failure with GitError otherwise.
        """
        result = self.open_repository(path)
        if result.is_success():
            return Success(True)
        return Failure(result.get_error_or_none() or GitError("Unknown error"))

    def get_current_branch(self, repo: Repo) -> Result[str, GitError]:
        """Get the name of the current branch.

        Args:
            repo: The Git repository.

        Returns:
            Success with branch name if on a branch.
            Failure with GitError if in detached HEAD state.
        """
        try:
            if repo.head.is_detached:
                return Failure(
                    GitError(
                        "Cannot get branch name: HEAD is detached",
                        details={"commit": str(repo.head.commit.hexsha)},
                    )
                )

            branch_name = repo.active_branch.name
            return Success(branch_name)

        except TypeError:
            return Failure(
                GitError(
                    "Cannot determine branch: repository may be in unusual state"
                )
            )
        except Exception as e:
            return Failure(GitError(f"Failed to get current branch: {e}"))

    def branch_exists(self, repo: Repo, branch_name: str) -> Result[bool, GitError]:
        """Check if a branch exists in the repository.

        Args:
            repo: The Git repository.
            branch_name: Name of the branch to check.

        Returns:
            Success with True if branch exists, False otherwise.
            Failure with GitError on error.
        """
        try:
            exists = branch_name in [b.name for b in repo.branches]
            return Success(exists)

        except Exception as e:
            return Failure(GitError(f"Failed to check branch existence: {e}"))

    def get_repository_status(self, repo: Repo) -> Result[RepositoryStatus, GitError]:
        """Get the current status of the repository.

        Args:
            repo: The Git repository.

        Returns:
            Success with RepositoryStatus containing current state.
            Failure with GitError on error.
        """
        try:
            status = repo.git.status("--porcelain", "-b")

            staged_files: list[str] = []
            modified_files: list[str] = []
            untracked_files: list[str] = []

            is_dirty = repo.is_dirty()
            is_clean = not is_dirty

            branch_name = self._extract_branch_name(status)

            for line in status.split("\n"):
                if not line.strip():
                    continue

                if line.startswith("##"):
                    continue

                index_status = line[0] if len(line) > 0 else " "
                worktree_status = line[1] if len(line) > 1 else " "
                file_path = line[3:].strip() if len(line) > 3 else ""

                if not file_path:
                    continue

                if index_status == "?" and worktree_status == "?":
                    untracked_files.append(file_path)
                elif index_status == " " and worktree_status == "M":
                    modified_files.append(file_path)
                elif index_status == "M":
                    staged_files.append(file_path)
                    modified_files.append(file_path)
                elif index_status == "D":
                    if index_status == "D":
                        staged_files.append(file_path)
                    modified_files.append(file_path)
                elif worktree_status == "?":
                    untracked_files.append(file_path)

            return Success(
                RepositoryStatus(
                    is_clean=is_clean,
                    is_dirty=is_dirty,
                    staged_files=staged_files,
                    modified_files=modified_files,
                    untracked_files=untracked_files,
                    current_branch=branch_name,
                )
            )

        except Exception as e:
            return Failure(GitError(f"Failed to get repository status: {e}"))

    def list_staged_files(self, repo: Repo) -> Result[list[str], GitError]:
        """List files that are staged for commit.

        Args:
            repo: The Git repository.

        Returns:
            Success with list of staged file paths.
            Failure with GitError on error.
        """
        try:
            staged = repo.index.diff("HEAD")
            staged_files = [d.a_path for d in staged if d.a_path]

            untracked = repo.untracked_files
            all_staged = staged_files + untracked

            return Success(all_staged)

        except Exception as e:
            return Failure(GitError(f"Failed to list staged files: {e}"))

    def list_untracked_files(self, repo: Repo) -> Result[list[str], GitError]:
        """List untracked files in the repository.

        Args:
            repo: The Git repository.

        Returns:
            Success with list of untracked file paths.
            Failure with GitError on error.
        """
        try:
            untracked = repo.untracked_files
            return Success(list(untracked))

        except Exception as e:
            return Failure(GitError(f"Failed to list untracked files: {e}"))

    def _extract_branch_name(self, status_output: str) -> str:
        """Extract branch name from git status output.

        Args:
            status_output: Output from git status -b --porcelain.

        Returns:
            Branch name or "HEAD" if not found.
        """
        for line in status_output.split("\n"):
            if line.startswith("##"):
                parts = line[2:].strip().split("...")
                return parts[0].split()[0] if parts else "HEAD"
        return "HEAD"

    def has_uncommitted_changes(self, repo: Repo) -> Result[bool, GitError]:
        """Check if the repository has uncommitted changes.

        Args:
            repo: The Git repository.

        Returns:
            Success with True if there are uncommitted changes.
            Failure with GitError on error.
        """
        try:
            is_dirty = repo.is_dirty()
            return Success(is_dirty)

        except Exception as e:
            return Failure(GitError(f"Failed to check for changes: {e}"))

    def get_commit_history(
        self, repo: Repo, max_count: int = 10
    ) -> Result[list[str], GitError]:
        """Get recent commit hashes.

        Args:
            repo: The Git repository.
            max_count: Maximum number of commits to return.

        Returns:
            Success with list of commit hashes.
            Failure with GitError on error.
        """
        try:
            commits = list(repo.iter_commits(max_count=max_count))
            return Success([c.hexsha for c in commits])

        except Exception as e:
            return Failure(GitError(f"Failed to get commit history: {e}"))