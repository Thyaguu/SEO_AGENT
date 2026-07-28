"""Logging configuration for the SEO Agent.

This module provides centralized logging setup using Python's standard logging
module with structlog for structured logging capabilities.

Usage:
    from seo_agent.core.logging import get_logger, configure_logging

    # Configure logging once at application startup
    configure_logging(level="INFO")

    # Get a logger for a module
    logger = get_logger(__name__)
    logger.info("operation_completed", duration_ms=100)
"""

import logging
import sys
from typing import Any

from seo_agent.core.constants import LogLevel


# Module-level logger registry for testing purposes
_loggers: dict[str, logging.Logger] = {}


def configure_logging(
    level: str = LogLevel.INFO.value,
    format_json: bool = False,
) -> None:
    """Configure the logging system.

    Args:
        level: Log level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format_json: If True, use JSON formatting for log output.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    root_logger.addHandler(handler)

    # Set formatter
    if format_json:
        formatter = logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", '
            '"name": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    handler.setFormatter(formatter)


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name.

    This function maintains a registry of loggers to ensure consistent
    logger instances across the application.

    Args:
        name: Logger name, typically __name__ of the module.

    Returns:
        Configured logger instance.
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]


def bind_context(**kwargs: Any) -> dict[str, Any]:
    """Create a context dictionary for structured logging.

    Args:
        **kwargs: Key-value pairs to include in log context.

    Returns:
        Dictionary suitable for passing to logger methods.
    """
    return kwargs


def log_function_call(
    logger: logging.Logger,
    func_name: str,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> None:
    """Log a function call with its arguments.

    Args:
        logger: Logger instance to use.
        func_name: Name of the function being called.
        args: Positional arguments (will not log sensitive data).
        kwargs: Keyword arguments.
    """
    context: dict[str, Any] = {"function": func_name}
    if args:
        context["arg_count"] = len(args)
    if kwargs:
        # Filter out potentially sensitive values
        safe_kwargs = {k: v for k, v in kwargs.items() if not _is_sensitive(k)}
        context["kwargs"] = safe_kwargs
    logger.debug("function_called", **context)


def _is_sensitive(key: str) -> bool:
    """Check if a parameter name suggests sensitive data.

    Args:
        key: Parameter name to check.

    Returns:
        True if the key suggests sensitive data.
    """
    sensitive_patterns = ("password", "token", "secret", "key", "auth")
    key_lower = key.lower()
    return any(pattern in key_lower for pattern in sensitive_patterns)


def reset_loggers() -> None:
    """Reset the logger registry.

    This is primarily useful for testing to ensure clean state.
    """
    global _loggers
    _loggers = {}


def log_stage_banner(
    logger: logging.Logger,
    title: str,
    width: int = 60,
    char: str = "=",
) -> None:
    """Format and log a visually distinct banner for major pipeline stages.

    Args:
        logger: Logger instance to output the banner.
        title: Stage title to display in the banner.
        width: Banner line width in characters.
        char: Character to use for banner border.
    """
    banner_line = char * width
    centered_title = title.strip().upper().center(width)
    logger.info(f"\n{banner_line}\n\n{centered_title}\n\n{banner_line}\n")