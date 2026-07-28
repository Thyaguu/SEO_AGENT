"""
API configuration module.

Defines settings for the FastAPI application server.
"""

from pydantic import Field

from .base import BaseConfig


class APISettings(BaseConfig):
    """Settings for the FastAPI application server."""

    model_config = BaseConfig.model_config | {"env_prefix": "API_"}

    host: str = Field(
        default="0.0.0.0",
        description="Host address to bind the API server to",
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port number for the API server",
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload for development",
    )
    workers: int = Field(
        default=1,
        ge=1,
        description="Number of worker processes",
    )