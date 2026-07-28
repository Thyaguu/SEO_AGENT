"""
Logging configuration module.

Defines settings for application logging.
"""

from enum import Enum
from typing import Literal

from pydantic import Field

from .base import BaseConfig


class LogFormat(str, Enum):
    """Supported log output formats."""

    JSON = "json"
    CONSOLE = "console"
    TEXT = "text"


class LogOutput(str, Enum):
    """Supported log output destinations."""

    STDOUT = "stdout"
    STDERR = "stderr"
    FILE = "file"


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LoggingSettings(BaseConfig):
    """Settings for application logging."""

    model_config = BaseConfig.model_config | {"env_prefix": "LOG_"}

    level: LogLevel = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    format: LogFormat = Field(
        default=LogFormat.JSON,
        description="Log output format",
    )
    output: LogOutput = Field(
        default=LogOutput.STDOUT,
        description="Log output destination",
    )
    file_path: str | None = Field(
        default=None,
        description="Path to log file when output is FILE",
    )
    max_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1,
        description="Maximum log file size in bytes before rotation",
    )
    backup_count: int = Field(
        default=5,
        ge=0,
        description="Number of backup log files to keep",
    )
    include_timestamp: bool = Field(
        default=True,
        description="Include timestamp in log output",
    )
    include_module: bool = Field(
        default=True,
        description="Include module name in log output",
    )
    include_function: bool = Field(
        default=True,
        description="Include function name in log output",
    )
    include_line: bool = Field(
        default=True,
        description="Include line number in log output",
    )