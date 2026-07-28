"""Git operations package.

This package provides Git integration for the SEO agent, including
repository operations and branch management.

Classes:
    GitClient: Read-only Git repository operations.
    GitOperations: Write operations (branch, commit, push).
    RepositoryStatus: Status information for a Git repository.

Usage:
    from seo_agent.git import GitClient, GitOperations

    client = GitClient()
    result = client.open_repository("/path/to/repo")

    if result.is_success():
        operations = GitOperations()
        operations.create_feature_branch(result.value, "feature/new")
"""

from seo_agent.git.client import GitClient, RepositoryStatus
from seo_agent.git.operations import GitOperations

__all__ = [
    "GitClient",
    "GitOperations",
    "RepositoryStatus",
]