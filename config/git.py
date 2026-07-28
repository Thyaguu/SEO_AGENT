"""
Git configuration module.

Defines settings for Git operations including branch management and commits.
"""

from pydantic import Field

from .base import BaseConfig


class GitSettings(BaseConfig):
    """Settings for Git operations."""

    model_config = BaseConfig.model_config | {"env_prefix": "GIT_"}

    default_branch: str = Field(
        default="main",
        description="Default branch name for the repository",
    )
    commit_author_name: str = Field(
        default="SEO AI Agent",
        description="Author name for Git commits",
    )
    commit_author_email: str = Field(
        default="seo-agent@example.com",
        description="Author email for Git commits",
    )
    push_changes: bool = Field(
        default=True,
        description="Whether to push changes after commit",
    )
    create_branch: bool = Field(
        default=True,
        description="Whether to create a new branch for changes",
    )
    branch_prefix: str = Field(
        default="seo/",
        description="Prefix for SEO-related branches",
    )