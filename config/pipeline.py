"""
Pipeline configuration module.

Defines settings for CI/CD pipeline integration.
Supports multiple providers: GitHub Actions, GitLab CI, Azure DevOps, Jenkins.

Note: Provider-specific validation (ensuring required fields are present for
the selected provider) should be performed by the pipeline service layer,
not in this configuration module.
"""

from enum import Enum

from pydantic import Field

from .base import BaseConfig


class PipelineProvider(str, Enum):
    """Supported CI/CD pipeline providers."""

    GITHUB_ACTIONS = "github-actions"
    GITLAB_CI = "gitlab-ci"
    AZURE_DEVOPS = "azure-devops"
    JENKINS = "jenkins"
    NONE = "none"


class PipelineSettings(BaseConfig):
    """Settings for CI/CD pipeline integration."""

    model_config = BaseConfig.model_config | {"env_prefix": "CICD_"}

    enabled: bool = Field(
        default=True,
        description="Enable CI/CD pipeline triggering",
    )
    provider: PipelineProvider = Field(
        default=PipelineProvider.GITHUB_ACTIONS,
        description="CI/CD provider to use",
    )
    trigger_on_commit: bool = Field(
        default=True,
        description="Trigger pipeline on successful Git commit",
    )
    wait_for_completion: bool = Field(
        default=False,
        description="Wait for pipeline to complete before returning",
    )
    timeout: int = Field(
        default=600,
        ge=1,
        description="Pipeline wait timeout in seconds",
    )

    # GitHub Actions
    github_token: str = Field(
        default="",
        description="GitHub personal access token",
    )
    github_repo: str = Field(
        default="",
        description="GitHub repository in format 'owner/repo'",
    )
    github_workflow_id: str = Field(
        default="",
        description="GitHub Actions workflow file name",
    )

    # GitLab CI
    gitlab_token: str = Field(
        default="",
        description="GitLab personal access token",
    )
    gitlab_project_id: int | None = Field(
        default=None,
        description="GitLab project ID",
    )
    gitlab_pipeline_id: int | None = Field(
        default=None,
        description="GitLab pipeline ID to trigger",
    )

    # Azure DevOps
    azure_devops_token: str = Field(
        default="",
        description="Azure DevOps personal access token",
    )
    azure_organization: str = Field(
        default="",
        description="Azure DevOps organization name",
    )
    azure_project: str = Field(
        default="",
        description="Azure DevOps project name",
    )
    azure_pipeline_id: int | None = Field(
        default=None,
        description="Azure DevOps pipeline ID",
    )

    # Jenkins
    jenkins_url: str = Field(
        default="",
        description="Jenkins server URL",
    )
    jenkins_user: str = Field(
        default="",
        description="Jenkins username",
    )
    jenkins_token: str = Field(
        default="",
        description="Jenkins API token",
    )
    jenkins_job_name: str = Field(
        default="",
        description="Jenkins job name to trigger",
    )