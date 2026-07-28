"""Git data models.

This module defines dataclasses used to represent Git operation results
and other Git-related state in a structured, type-safe manner.

Usage:
    result = GitCommitResult(
        branch_name="feature/new-feature",
        commit_hash="abc1234567890",
        remote_ref="origin/feature/new-feature",
    )
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GitCommitResult:
    """Result of a successful commit-and-push workflow.

    Attributes:
        branch_name: Name of the branch the commit was created on.
        commit_hash: Full SHA of the created commit.
        remote_ref: Fully-qualified remote reference (e.g. ``origin/<branch>``).
    """

    branch_name: str
    commit_hash: str
    remote_ref: str
