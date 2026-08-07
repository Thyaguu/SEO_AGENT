"""
OpenCode configuration module.

Defines settings for the OpenCode AI execution agent.
"""

from pydantic import Field, HttpUrl

from .base import BaseConfig


class OpenCodeSettings(BaseConfig):
    """Settings for the OpenCode execution agent."""

    model_config = BaseConfig.model_config | {"env_prefix": "OPENCODE_"}

    api_key: str = Field(
        default="",
        description="OpenCode API key for authentication",
    )
    base_url: HttpUrl = Field(
        default="http://127.0.0.1:4096",
        description="OpenCode API base URL",
    )
    timeout: int = Field(
        default=300,
        ge=1,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retry attempts",
    )
    server_startup_timeout: int = Field(
        default=30,
        ge=1,
        description="Maximum time in seconds to wait for OpenCode server startup",
    )