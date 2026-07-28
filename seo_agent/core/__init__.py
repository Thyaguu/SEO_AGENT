"""Shared infrastructure package.

This package contains core infrastructure modules used across the project.
It provides common types, constants, utilities, and patterns that are
independent of any specific business domain.

Exports:
    - Exception classes from exceptions module
    - Result types from result module
    - Type definitions from types module
    - Constants from constants module
    - Logging utilities from logging module
    - Dependency injection from dependency_injection module
    - Utility functions from utils module
"""

from seo_agent.core.constants import (
    COMMIT_MESSAGE_PREFIX,
    DEFAULT_BRANCH_NAME,
    DEFAULT_META_DESCRIPTION_LENGTH,
    DEFAULT_META_TITLE_LENGTH,
    DEFAULT_TIMEOUT,
    FRAMEWORK_ANGULAR,
    FRAMEWORK_DJANGO,
    FRAMEWORK_EXPRESS,
    FRAMEWORK_FLASK,
    FRAMEWORK_GATSBY,
    FRAMEWORK_HTML,
    FRAMEWORK_NEXTJS,
    FRAMEWORK_NUXT,
    FRAMEWORK_REACT,
    FRAMEWORK_VUE,
    LONG_RUNNING_TIMEOUT,
    MAX_FILE_SIZE_BYTES,
    MAX_RETRY_ATTEMPTS,
    MAX_SEO_PAGES_PER_COMMIT,
    MAX_SITEMAP_URLS,
    RETRY_BACKOFF_MULTIPLIER,
    RETRY_DELAY_SECONDS,
    SUPPORTED_FRAMEWORKS,
    ExecutionStatus,
    LogLevel,
    ReviewDecision,
)

from seo_agent.core.dependency_injection import (
    Container,
    get_container,
    inject,
    reset_container,
    set_container,
)

from seo_agent.core.exceptions import (
    ConfigurationError,
    DependencyError,
    ExecutionError,
    FrameworkDetectionError,
    GitError,
    IntegrationError,
    RepositoryError,
    ReviewError,
    SEOAgentError,
    TimeoutError,
    ValidationError,
)

from seo_agent.core.logging import (
    bind_context,
    configure_logging,
    get_logger,
    log_function_call,
    reset_loggers,
)

from seo_agent.core.result import (
    Failure,
    Result,
    from_bool,
    from_exception,
    failure,
    success,
)

from seo_agent.core.types import (
    AsyncCleanupFn,
    AsyncFactoryFn,
    AsyncValidatorFn,
    CleanupFn,
    FactoryFn,
    ImmutableDict,
    StrDict,
    ValidatorFn,
)

from seo_agent.core.utils import (
    clamp,
    compute_file_hash,
    merge_dicts,
    normalize_path,
    remove_prefix,
    remove_suffix,
    safe_get,
    sanitize_filename,
    to_camel_case,
    to_snake_case,
    truncate_string,
)

__all__ = [
    # Constants
    "COMMIT_MESSAGE_PREFIX",
    "DEFAULT_BRANCH_NAME",
    "DEFAULT_META_DESCRIPTION_LENGTH",
    "DEFAULT_META_TITLE_LENGTH",
    "DEFAULT_TIMEOUT",
    "FRAMEWORK_ANGULAR",
    "FRAMEWORK_DJANGO",
    "FRAMEWORK_EXPRESS",
    "FRAMEWORK_FLASK",
    "FRAMEWORK_GATSBY",
    "FRAMEWORK_HTML",
    "FRAMEWORK_NEXTJS",
    "FRAMEWORK_NUXT",
    "FRAMEWORK_REACT",
    "FRAMEWORK_VUE",
    "LONG_RUNNING_TIMEOUT",
    "MAX_FILE_SIZE_BYTES",
    "MAX_RETRY_ATTEMPTS",
    "MAX_SEO_PAGES_PER_COMMIT",
    "MAX_SITEMAP_URLS",
    "RETRY_BACKOFF_MULTIPLIER",
    "RETRY_DELAY_SECONDS",
    "SUPPORTED_FRAMEWORKS",
    "ExecutionStatus",
    "LogLevel",
    "ReviewDecision",
    # Dependency Injection
    "Container",
    "get_container",
    "inject",
    "reset_container",
    "set_container",
    # Exceptions
    "ConfigurationError",
    "DependencyError",
    "ExecutionError",
    "FrameworkDetectionError",
    "GitError",
    "IntegrationError",
    "RepositoryError",
    "ReviewError",
    "SEOAgentError",
    "TimeoutError",
    "ValidationError",
    # Logging
    "bind_context",
    "configure_logging",
    "get_logger",
    "log_function_call",
    "reset_loggers",
    # Result
    "Failure",
    "Result",
    "from_bool",
    "from_exception",
    "failure",
    "success",
    # Types
    "AsyncCleanupFn",
    "AsyncFactoryFn",
    "AsyncValidatorFn",
    "CleanupFn",
    "FactoryFn",
    "ImmutableDict",
    "StrDict",
    "ValidatorFn",
    # Utils
    "clamp",
    "compute_file_hash",
    "merge_dicts",
    "normalize_path",
    "remove_prefix",
    "remove_suffix",
    "safe_get",
    "sanitize_filename",
    "to_camel_case",
    "to_snake_case",
    "truncate_string",
]