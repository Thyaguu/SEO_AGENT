"""Project-wide constants.

This module contains all constant values used across the project.
Constants are grouped by category for easy maintenance.
"""

from enum import Enum


class LogLevel(str, Enum):
    """Standard log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ExecutionStatus(str, Enum):
    """Status values for workflow execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ReviewDecision(str, Enum):
    """Review decision outcomes."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


# Retry configuration
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1.0
RETRY_BACKOFF_MULTIPLIER = 2.0

# SEO configuration
MAX_SEO_PAGES_PER_COMMIT = 10
DEFAULT_META_DESCRIPTION_LENGTH = 160
DEFAULT_META_TITLE_LENGTH = 60

# File size limits (in bytes)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_SITEMAP_URLS = 50000

# Timeout values (in seconds)
DEFAULT_TIMEOUT = 30.0
LONG_RUNNING_TIMEOUT = 300.0

# Git configuration
DEFAULT_BRANCH_NAME = "main"
COMMIT_MESSAGE_PREFIX = "feat: SEO improvements"

# Framework identifiers
FRAMEWORK_REACT = "react"
FRAMEWORK_NEXTJS = "nextjs"
FRAMEWORK_VUE = "vue"
FRAMEWORK_NUXT = "nuxt"
FRAMEWORK_ANGULAR = "angular"
FRAMEWORK_DJANGO = "django"
FRAMEWORK_FLASK = "flask"
FRAMEWORK_EXPRESS = "express"
FRAMEWORK_GATSBY = "gatsby"
FRAMEWORK_HTML = "html"

# Supported frameworks list
SUPPORTED_FRAMEWORKS = [
    FRAMEWORK_REACT,
    FRAMEWORK_NEXTJS,
    FRAMEWORK_VUE,
    FRAMEWORK_NUXT,
    FRAMEWORK_ANGULAR,
    FRAMEWORK_DJANGO,
    FRAMEWORK_FLASK,
    FRAMEWORK_EXPRESS,
    FRAMEWORK_GATSBY,
    FRAMEWORK_HTML,
]