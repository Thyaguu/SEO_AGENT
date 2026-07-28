"""Custom exception classes for the SEO Agent.

This module defines a hierarchy of exceptions used throughout the project.
All exceptions inherit from SEOAgentError base class for consistent handling.
"""

from typing import Any


class SEOAgentError(Exception):
    """Base exception class for all SEO Agent errors.

    All custom exceptions in the project should inherit from this class.
    This allows for centralized error handling and logging.
    """

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional context.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of the exception."""
        return self.message


class ConfigurationError(SEOAgentError):
    """Raised when configuration is invalid or missing.

    This includes missing environment variables, invalid config values,
    or configuration file issues.
    """
    pass


class RepositoryError(SEOAgentError):
    """Raised when repository operations fail.

    This includes file system errors, path resolution issues,
    and repository state problems.
    """
    pass


class FrameworkDetectionError(SEOAgentError):
    """Raised when framework detection fails.

    This occurs when the repository framework cannot be determined
    or is not supported.
    """
    pass


class ValidationError(SEOAgentError):
    """Raised when input validation fails.

    This includes invalid payloads, malformed data,
    and constraint violations.
    """
    pass


class ExecutionError(SEOAgentError):
    """Raised when task execution fails.

    This includes errors during task processing,
    agent execution, and workflow operations.
    """
    pass


class ReviewError(SEOAgentError):
    """Raised when review operations fails.

    This includes validation failures, approval errors,
    and review timeout issues.
    """
    pass


class GitError(SEOAgentError):
    """Raised when Git operations fail.

    This includes commit failures, branch issues,
    and remote operation errors.
    """
    pass


class IntegrationError(SEOAgentError):
    """Raised when external integration fails.

    This includes OpenCode API errors, n8n communication issues,
    and CI/CD pipeline failures.
    """
    pass


class TimeoutError(SEOAgentError):
    """Raised when operations exceed timeout limits.

    This includes long-running operations that exceed
    configured timeout values.
    """
    pass


class DependencyError(SEOAgentError):
    """Raised when dependency injection or resolution fails.

    This includes missing dependencies, circular dependencies,
    and invalid dependency configurations.
    """
    pass