"""
Application configuration module.

Defines top-level application settings and exposes the singleton Settings object.
"""

from pydantic import Field

from .base import BaseConfig, get_settings
from .api import APISettings
from .git import GitSettings
from .logging import LoggingSettings
from .opencode import OpenCodeSettings
from .pipeline import PipelineSettings
from .repository import RepositorySettings
from .seo import SEOSettings


class AppSettings(BaseConfig):
    """Top-level application settings."""

    model_config = BaseConfig.model_config | {"env_prefix": "APP_"}

    name: str = Field(
        default="SEO AI Agent",
        description="Application name",
    )
    version: str = Field(
        default="1.0.0",
        description="Application version",
    )
    environment: str = Field(
        default="development",
        description="Deployment environment (development, staging, production)",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )


class Settings(BaseConfig):
    """
    Root settings class that aggregates all configuration modules.

    This is the single entry point for accessing configuration throughout
    the application. Access nested settings via attributes:

        from config import settings

        api_port = settings.api.port
        git_branch = settings.git.default_branch
        seo_limit = settings.seo.page_limit

    For fresh instances (e.g., in tests), use:

        from config.base import get_settings

        settings = get_settings()
    """

    app: AppSettings = Field(default_factory=AppSettings)
    api: APISettings = Field(default_factory=APISettings)
    opencode: OpenCodeSettings = Field(default_factory=OpenCodeSettings)
    git: GitSettings = Field(default_factory=GitSettings)
    repository: RepositorySettings = Field(default_factory=RepositorySettings)
    seo: SEOSettings = Field(default_factory=SEOSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)


# Module-level singleton instance
# Import this in other modules: from config import settings
settings = Settings()

__all__ = ["Settings", "settings", "get_settings"]