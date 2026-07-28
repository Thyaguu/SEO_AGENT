"""Branch and commit operations.

This module provides operations for modifying Git state, including
branch creation, checkout, staging, committing, and rollback operations.

Usage:
    operations = GitOperations()
    result = operations.create_feature_branch(repo, "feature/new-feature")
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from git import Repo

from seo_agent.core.exceptions import GitError
from seo_agent.core.logging import get_logger
from seo_agent.core.result import Failure, Result, Success
from seo_agent.git.models import GitCommitResult

if TYPE_CHECKING:
    from git import Repo

logger = get_logger(__name__)


class GitOperations:
    """Operations for modifying Git state.

    This class provides methods for branch management, committing changes,
    and state restoration. All operations return Result types for explicit
    error handling.
    """

    def create_feature_branch(
        self, repo: Repo, branch_name: str, base_branch: str | None = None
    ) -> Result[str, GitError]:
        """Create a new feature branch.

        Args:
            repo: The Git repository.
            branch_name: Name for the new branch.
            base_branch: Branch to base new branch on. Defaults to current HEAD.

        Returns:
            Success with branch name if created successfully.
            Failure with GitError if branch already exists or creation fails.
        """
        try:
            if branch_name in [b.name for b in repo.branches]:
                return Failure(
                    GitError(
                        f"Branch already exists: {branch_name}",
                        details={"branch": branch_name},
                    )
                )

            if base_branch:
                base = repo.branches[base_branch]
                new_branch = repo.create_head(branch_name, base)
            else:
                new_branch = repo.create_head(branch_name)

            new_branch.checkout()
            logger.info(f"Created and checked out branch: {branch_name}")
            return Success(branch_name)

        except Exception as e:
            return Failure(GitError(f"Failed to create branch: {e}"))

    def checkout_branch(
        self, repo: Repo, branch_name: str, create_if_missing: bool = False
    ) -> Result[str, GitError]:
        """Checkout an existing branch or optionally create it.

        Args:
            repo: The Git repository.
            branch_name: Name of the branch to checkout.
            create_if_missing: If True, create branch if it doesn't exist.

        Returns:
            Success with branch name if checkout successful.
            Failure with GitError if branch doesn't exist or checkout fails.
        """
        try:
            if branch_name not in [b.name for b in repo.branches]:
                if create_if_missing:
                    return self.create_feature_branch(repo, branch_name)
                return Failure(
                    GitError(
                        f"Branch does not exist: {branch_name}",
                        details={"branch": branch_name},
                    )
                )

            branch = repo.branches[branch_name]
            branch.checkout()
            logger.info(f"Checked out branch: {branch_name}")
            return Success(branch_name)

        except Exception as e:
            return Failure(GitError(f"Failed to checkout branch: {e}"))

    def stage_files(
        self, repo: Repo, file_paths: list[str] | str | None = None
    ) -> Result[list[str], GitError]:
        """Stage files for commit.

        Args:
            repo: The Git repository.
            file_paths: Files to stage. If None, stage all modified files.
                If an empty list is passed, a validation error is returned
                (use None to stage all changes instead).

        Returns:
            Success with list of staged file paths.
            Failure with GitError if staging fails or file_paths is empty.
        """
        try:
            if file_paths is None:
                repo.git.add("-A")
                staged = repo.untracked_files + [
                    d.a_path for d in repo.index.diff(None)
                ]
            elif isinstance(file_paths, str):
                repo.git.add(file_paths)
                staged = [file_paths]
            elif len(file_paths) == 0:
                return Failure(
                    GitError(
                        "stage_files called with an empty list. "
                        "Pass None to stage all changes, or provide explicit file paths.",
                        details={"file_paths": []},
                    )
                )
            else:
                for path in file_paths:
                    repo.git.add(path)
                staged = list(file_paths)

            logger.info(f"Staged {len(staged)} file(s)")
            return Success(staged)

        except Exception as e:
            return Failure(GitError(f"Failed to stage files: {e}"))

    def create_commit(
        self,
        repo: Repo,
        message: str,
        author_name: str | None = None,
        author_email: str | None = None,
    ) -> Result[str, GitError]:
        """Create a commit with the staged changes.

        Args:
            repo: The Git repository.
            message: Commit message.
            author_name: Optional author name override.
            author_email: Optional author email override.

        Returns:
            Success with commit hash if commit successful.
            Failure with GitError if no changes staged or commit fails.
        """
        try:
            if not repo.is_dirty(index=True, working_tree=False):
                return Failure(
                    GitError("No changes to commit. Stage files first.")
                )

            if author_name or author_email:
                env = {}
                if author_name:
                    env["GIT_AUTHOR_NAME"] = author_name
                    env["GIT_COMMITTER_NAME"] = author_name
                if author_email:
                    env["GIT_AUTHOR_EMAIL"] = author_email
                    env["GIT_COMMITTER_EMAIL"] = author_email

                import os

                old_env = {k: os.environ.get(k) for k in env if os.environ.get(k)}
                os.environ.update(env)

                try:
                    commit = repo.index.commit(message)
                finally:
                    for k, v in old_env.items():
                        if v is None:
                            os.environ.pop(k, None)
                        else:
                            os.environ[k] = v
            else:
                commit = repo.index.commit(message)

            logger.info(f"Created commit: {commit.hexsha[:8]} - {message}")
            return Success(commit.hexsha)

        except Exception as e:
            return Failure(GitError(f"Failed to create commit: {e}"))

    def rollback_changes(
        self, repo: Repo, file_paths: list[str] | None = None
    ) -> Result[bool, GitError]:
        """Rollback changes to specified files or all files.

        This restores files to their state at the last commit (HEAD).
        Use with caution as this discards uncommitted changes.

        Args:
            repo: The Git repository.
            file_paths: Files to rollback. If None, rollback all files.

        Returns:
            Success with True if rollback successful.
            Failure with GitError if rollback fails.
        """
        try:
            if file_paths is None:
                repo.git.checkout("--", ".")
            else:
                for path in file_paths:
                    repo.git.checkout("--", path)

            logger.info(f"Rolled back changes to {len(file_paths) if file_paths else 'all files'}")
            return Success(True)

        except Exception as e:
            return Failure(GitError(f"Failed to rollback changes: {e}"))

    def restore_working_tree(
        self, repo: Repo, *, force: bool = False
    ) -> Result[bool, GitError]:
        """Discard all uncommitted changes in the working tree.

        This is a more thorough cleanup than rollback_changes, removing
        both staged and unstaged changes as well as untracked files and
        directories.

        .. warning::
            This operation permanently destroys all uncommitted changes.
            It is irreversible and cannot be undone.

        Args:
            repo: The Git repository.
            force: Must be explicitly set to True to execute the destructive
                operations. Defaults to False (safe). When False, the
                method returns a Failure without modifying any state.

        Returns:
            Success with True if working tree was restored.
            Failure with GitError if force is not True or if the operation fails.
        """
        if not force:
            return Failure(
                GitError(
                    "restore_working_tree requires force=True to execute. "
                    "This operation permanently discards all uncommitted changes. "
                    "Set force=True if you intend to reset the working tree.",
                    details={"force": force},
                )
            )

        try:
            repo.git.reset("--hard")
            repo.git.clean("-fd")
            logger.warning("Restored working tree to last commit (force=True)")
            return Success(True)

        except Exception as e:
            return Failure(GitError(f"Failed to restore working tree: {e}"))

    def push_branch(
        self,
        repo: Repo,
        remote: str = "origin",
        branch_name: str | None = None,
        set_upstream: bool = True,
    ) -> Result[str, GitError]:
        """Push a branch to a remote repository.

        Args:
            repo: The Git repository.
            remote: Name of the remote to push to.
            branch_name: Branch to push. Defaults to current branch.
            set_upstream: If True, set up tracking relationship.

        Returns:
            Success with remote ref if push successful.
            Failure with GitError if push fails.
        """
        try:
            if branch_name is None:
                if repo.head.is_detached:
                    return Failure(
                        GitError("Cannot push: HEAD is detached")
                    )
                branch_name = repo.active_branch.name

            if remote not in [r.name for r in repo.remotes]:
                return Failure(
                    GitError(
                        f"Remote '{remote}' not found",
                        details={"remote": remote, "available": [r.name for r in repo.remotes]},
                    )
                )

            push_kwargs = []
            if set_upstream:
                push_kwargs.append("--set-upstream")

            push_ref = f"{remote}/{branch_name}" if set_upstream else branch_name
            push_kwargs.append(push_ref)

            repo.git.push(remote, branch_name, *push_kwargs)

            logger.info(f"Pushed branch '{branch_name}' to '{remote}'")
            return Success(f"{remote}/{branch_name}")

        except Exception as e:
            return Failure(GitError(f"Failed to push branch: {e}"))

    def commit_seo_changes(
        self,
        repository_path: Path,
        commit_message: str = "Apply AI SEO updates",
    ) -> Result[GitCommitResult, GitError]:
        """Commit and push SEO-related changes for a repository.

        High-level workflow that orchestrates branch creation, staging,
        committing, and pushing of AI-generated SEO updates, returning a
        structured ``GitCommitResult`` describing the outcome.

        This method is idempotent:
        - If the branch already exists, it is checked out instead of failing.
        - If there are no changes to commit, a no-op GitCommitResult is returned.
        - If push fails (e.g. no remote configured), the commit is still
          considered successful and the remote_ref is set to "local-only".

        Args:
            repository_path: Filesystem path to the target Git repository.
            commit_message: Commit message to use for the SEO changes.

        Returns:
            Success with a ``GitCommitResult`` containing the branch name,
            commit hash, and remote reference on a successful workflow.
            Failure with ``GitError`` if any step of the workflow fails.
        """
        # Open the repository at ``repository_path``.
        try:
            repo = Repo(repository_path, search_parent_directories=False)
        except Exception as e:
            return Failure(
                GitError(
                    f"Failed to open repository at {repository_path}: {e}",
                    details={"repository_path": str(repository_path)},
                )
            )

        # Generate a timestamped SEO feature branch name.
        branch_name = f"feature/seo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create or checkout the SEO feature branch (idempotent).
        branch_result = self.create_feature_branch(repo, branch_name)
        if isinstance(branch_result, Failure):
            # Branch may already exist — try to check it out instead.
            checkout_result = self.checkout_branch(repo, branch_name)
            if isinstance(checkout_result, Failure):
                return Failure(
                    GitError(
                        f"Failed to create or checkout SEO branch '{branch_name}': {branch_result.error}",
                        details={"repository_path": str(repository_path)},
                    )
                )
            logger.info(f"Branch '{branch_name}' already exists, checked out")

        # Stage all SEO-modified files.
        stage_result = self.stage_files(repo, file_paths=None)
        if isinstance(stage_result, Failure):
            return Failure(
                GitError(
                    f"Failed to stage SEO changes: {stage_result.error}",
                    details={"repository_path": str(repository_path)},
                )
            )

        # If there are no changes to commit, return a no-op success.
        if not repo.is_dirty(index=True, working_tree=False):
            logger.info("No changes to commit — repository already up to date")
            head_sha = repo.head.commit.hexsha if repo.head.is_valid() else "no-commit"
            return Success(
                GitCommitResult(
                    branch_name=branch_name,
                    commit_hash=head_sha,
                    remote_ref="no-changes",
                )
            )

        # Create the commit using ``commit_message``.
        commit_result = self.create_commit(repo, commit_message)
        if isinstance(commit_result, Failure):
            return Failure(
                GitError(
                    f"Failed to create SEO commit: {commit_result.error}",
                    details={"repository_path": str(repository_path)},
                )
            )
        commit_hash = commit_result.value

        # Push the branch to the remote. If push fails (e.g. no remote
        # configured for a local-only repo), treat it as non-fatal.
        push_result = self.push_branch(repo, branch_name=branch_name)
        if isinstance(push_result, Failure):
            logger.warning(
                f"Push failed for branch '{branch_name}': {push_result.error}. "
                f"Commit {commit_hash[:8]} was created locally."
            )
            remote_ref = "local-only"
        else:
            remote_ref = push_result.value

        return Success(
            GitCommitResult(
                branch_name=branch_name,
                commit_hash=commit_hash,
                remote_ref=remote_ref,
            )
        )

    def _open_repo_and_create_seo_branch(
        self, repository_path: Path
    ) -> Result[tuple[Repo, str], GitError]:
        """Open the repository and create/checkout an SEO feature branch.

        Helper that performs the first part of ``commit_seo_changes``:
        opens the ``Repo`` at ``repository_path`` and creates a new
        feature branch named ``feature/seo_<YYYYMMDD>_<HHMMSS>`` based
        on the current HEAD, then checks it out.

        Args:
            repository_path: Filesystem path to the target Git repository.

        Returns:
            Success with a tuple of ``(Repo, branch_name)`` on success.
            Failure with ``GitError`` if the repo cannot be opened or the
            branch cannot be created.
        """
        try:
            repo = Repo(repository_path, search_parent_directories=False)
        except Exception as e:
            return Failure(
                GitError(
                    f"Failed to open repository at {repository_path}: {e}",
                    details={"repository_path": str(repository_path)},
                )
            )

        branch_name = f"feature/seo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        branch_result = self.create_feature_branch(repo, branch_name)

        if isinstance(branch_result, Failure):
            return Failure(
                GitError(
                    f"Failed to create SEO branch: {branch_result.error}",
                    details={"repository_path": str(repository_path)},
                )
            )

        return Success((repo, branch_name))

    def _open_repo_and_create_seo_branch(
        self, repository_path: Path
    ) -> Result[tuple[Repo, str], GitError]:
        """Open the repository and create/checkout an SEO feature branch.

        Helper that performs the first part of ``commit_seo_changes``:
        opens the ``Repo`` at ``repository_path`` and creates a new
        feature branch named ``feature/seo_<YYYYMMDD>_<HHMMSS>`` based
        on the current HEAD, then checks it out.

        Args:
            repository_path: Filesystem path to the target Git repository.

        Returns:
            Success with a tuple of ``(Repo, branch_name)`` on success.
            Failure with ``GitError`` if the repo cannot be opened or the
            branch cannot be created.
        """
        try:
            repo = Repo(repository_path, search_parent_directories=True)
        except Exception as e:
            return Failure(
                GitError(
                    f"Failed to open repository at {repository_path}: {e}",
                    details={"repository_path": str(repository_path)},
                )
            )

        branch_name = f"feature/seo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        branch_result = self.create_feature_branch(repo, branch_name)

        if isinstance(branch_result, Failure):
            return Failure(
                GitError(
                    f"Failed to create SEO branch: {branch_result.error}",
                    details={"repository_path": str(repository_path)},
                )
            )

        return Success((repo, branch_name))