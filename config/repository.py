"""
Repository configuration module.

Defines settings for repository analysis and scanning.
"""

from pathlib import Path

from pydantic import Field, field_validator

from .base import BaseConfig


class RepositorySettings(BaseConfig):
    """Settings for repository analysis and scanning."""

    model_config = BaseConfig.model_config | {"env_prefix": "REPO_"}

    path: Path | None = Field(
        default=None,
        description="Path to the repository to analyze",
    )
    analysis_depth: int = Field(
        default=3,
        ge=1,
        description="Depth for recursive repository analysis",
    )
    ignore_patterns: list[str] = Field(
        default=[
            "node_modules",
            ".git",
            "__pycache__",
            "*.pyc",
            ".venv",
            "venv",
        ],
        description="Patterns to ignore during analysis",
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1,
        description="Maximum file size to analyze in bytes",
    )

    @field_validator("path", mode="before")
    @classmethod
    def validate_path(cls, v: str | Path | None) -> Path | None:
        """Ensure path is converted to Path object."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return Path(v)
        return v