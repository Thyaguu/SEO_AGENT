"""
SEO AI Agent Configuration Package.

This package provides strongly-typed configuration management using pydantic-settings.
All configuration values are loaded from environment variables.

Usage:
    from config import settings

    # Access nested settings
    api_port = settings.api.port
    git_branch = settings.git.default_branch
    seo_limit = settings.seo.page_limit

    # For fresh instances (e.g., in tests):
    from config.base import get_settings
    settings = get_settings()

Modules:
    base: Base configuration classes and utilities
    api: FastAPI server settings
    opencode: OpenCode execution agent settings
    git: Git operations settings
    repository: Repository analysis settings
    seo: SEO-specific settings
    logging: Logging configuration
    pipeline: CI/CD pipeline settings
    settings: Root settings aggregator (singleton)
"""

from config.base import get_settings
from config.settings import Settings, settings

__all__ = ["Settings", "settings", "get_settings"]