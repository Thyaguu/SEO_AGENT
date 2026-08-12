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
    logger.debug("function_called %s", context)


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


class ConsoleFormatter:
    """Unified, reusable console formatting utility for workflow stages and banners."""

    DEFAULT_WIDTH: int = 60
    DEFAULT_KEY_WIDTH: int = 22

    @classmethod
    def print_banner(
        cls,
        title: str,
        width: int = DEFAULT_WIDTH,
        char: str = "=",
    ) -> str:
        """Format a centered stage or phase banner."""
        line = char * width
        centered = title.strip().upper().center(width)
        return f"{line}\n{centered}\n{line}"

    @classmethod
    def print_section(
        cls,
        title: str,
        width: int = DEFAULT_WIDTH,
        char: str = "-",
    ) -> str:
        """Format a section header with divider line."""
        line = char * width
        return f"{title}\n{line}"

    @classmethod
    def print_key_value(
        cls,
        key: str,
        value: Any,
        key_width: int = DEFAULT_KEY_WIDTH,
    ) -> str:
        """Format a key/value pair with vertical colon alignment."""
        key_str = str(key)
        val_str = str(value)
        return f"{key_str:<{key_width}} : {val_str}"

    @classmethod
    def print_list(
        cls,
        items: list[Any] | tuple[Any, ...],
        bullet: str = "• ",
    ) -> str:
        """Format a bulleted list of items."""
        formatted = []
        for item in items:
            item_str = str(item)
            if not item_str.startswith("• ") and not item_str.startswith("- "):
                item_str = f"{bullet}{item_str}"
            formatted.append(item_str)
        return "\n".join(formatted)

    @classmethod
    def print_status(
        cls,
        status: str,
        width: int = DEFAULT_WIDTH,
        char: str = "-",
    ) -> str:
        """Format a stage status section."""
        sec = cls.print_section("Status", width=width, char=char)
        return f"{sec}\n{status}"

    @classmethod
    def print_table(
        cls,
        headers: list[str],
        rows: list[list[str]],
        col_widths: list[int] | None = None,
        width: int = DEFAULT_WIDTH,
    ) -> str:
        """Format tabular data cleanly without wrapping lines."""
        if not col_widths:
            col_widths = []
            for col_idx in range(len(headers)):
                max_w = len(headers[col_idx])
                for row in rows:
                    if col_idx < len(row):
                        max_w = max(max_w, len(str(row[col_idx])))
                col_widths.append(max_w + 3)

        header_line = "".join(f"{str(h):<{col_widths[i]}}" for i, h in enumerate(headers)).rstrip()
        divider = "-" * width
        row_lines = []
        for row in rows:
            r_str = "".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(row)).rstrip()
            row_lines.append(r_str)

        return "\n".join([divider, header_line, divider] + row_lines + [divider])

    @classmethod
    def print_summary(
        cls,
        repository: str,
        framework: str,
        pages: int,
        keywords: int,
        tasks_planned: int,
        tasks_executed: int,
        tasks_failed: int = 0,
        files_modified: int = 0,
        files_skipped: int = 0,
        review_score: str = "100/100",
        sitemap: str = "Generated",
        robots: str = "Generated",
        reports: str = "Markdown HTML JSON",
        overall_status: str = "SUCCESS",
        total_duration: float = 0.0,
        width: int = DEFAULT_WIDTH,
        key_width: int = DEFAULT_KEY_WIDTH,
    ) -> str:
        """Format the final workflow execution summary dashboard."""
        banner = cls.print_banner("WORKFLOW EXECUTION SUMMARY", width=width, char="=")
        kv = cls.print_key_value
        lines = [
            banner,
            "",
            kv("Repository", repository, key_width=key_width),
            kv("Framework", framework, key_width=key_width),
            "",
            kv("Pages", pages, key_width=key_width),
            kv("Keywords", keywords, key_width=key_width),
            "",
            kv("Tasks Planned", tasks_planned, key_width=key_width),
            kv("Tasks Executed", tasks_executed, key_width=key_width),
            kv("Tasks Failed", tasks_failed, key_width=key_width),
            kv("Files Modified", files_modified, key_width=key_width),
            kv("Files Skipped", files_skipped, key_width=key_width),
            "",
            kv("Review Score", review_score, key_width=key_width),
            "",
            kv("Sitemap", sitemap, key_width=key_width),
            kv("Robots", robots, key_width=key_width),
            "",
            kv("Reports", reports, key_width=key_width),
            "",
            kv("Overall Status", overall_status, key_width=key_width),
            kv("Total Duration", f"{total_duration:.2f} seconds", key_width=key_width),
            "",
            "=" * width,
        ]
        return "\n".join(lines)

    @classmethod
    def print_stage_report(
        cls,
        stage_name: str,
        input_data: list[tuple[str, str]],
        processing_steps: list[str],
        output_data: list[tuple[str, str]],
        status: str,
        duration_sec: float,
        extra_sections: list[tuple[str, list[str]]] | None = None,
        width: int = DEFAULT_WIDTH,
        key_width: int = DEFAULT_KEY_WIDTH,
    ) -> str:
        """Format a complete structured report for a completed stage."""
        lines = []

        if input_data:
            lines.append(cls.print_section("Input", width=width))
            for k, v in input_data:
                lines.append(cls.print_key_value(k, v, key_width=key_width))
            lines.append("")

        if processing_steps:
            lines.append(cls.print_section("Processing", width=width))
            lines.append(cls.print_list(processing_steps, bullet="• "))
            lines.append("")

        if output_data:
            lines.append(cls.print_section("Output", width=width))
            for k, v in output_data:
                lines.append(cls.print_key_value(k, v, key_width=key_width))
            lines.append("")

        if extra_sections:
            for title, items in extra_sections:
                lines.append(cls.print_section(title, width=width))
                lines.append(cls.print_list(items, bullet="• "))
                lines.append("")

        lines.append(cls.print_section("Status", width=width))
        lines.append(status)
        lines.append("")

        lines.append(cls.print_section("Duration", width=width))
        lines.append(f"{duration_sec:.2f} seconds")

        return "\n".join(lines)


def log_stage_banner(
    logger: logging.Logger,
    title: str,
    width: int = 60,
    char: str = "=",
) -> None:
    """Format and log a visually distinct banner for major pipeline stages."""
    banner_text = ConsoleFormatter.print_banner(title, width=width, char=char)
    logger.info(f"\n{banner_text}\n")


def log_stage_report(
    logger: logging.Logger,
    stage_name: str,
    input_data: list[tuple[str, str]],
    processing_steps: list[str],
    output_data: list[tuple[str, str]],
    status: str,
    duration_sec: float,
    extra_sections: list[tuple[str, list[str]]] | None = None,
) -> None:
    """Format and log a structured report for a workflow stage."""
    report_text = ConsoleFormatter.print_stage_report(
        stage_name=stage_name,
        input_data=input_data,
        processing_steps=processing_steps,
        output_data=output_data,
        status=status,
        duration_sec=duration_sec,
        extra_sections=extra_sections,
    )
    logger.info(f"\n{report_text}\n")