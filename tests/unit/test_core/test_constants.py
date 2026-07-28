"""Unit tests for seo_agent.core.constants."""

import pytest

from seo_agent.core.constants import (
    COMMIT_MESSAGE_PREFIX,
    DEFAULT_BRANCH_NAME,
    DEFAULT_META_DESCRIPTION_LENGTH,
    DEFAULT_META_TITLE_LENGTH,
    DEFAULT_TIMEOUT,
    ExecutionStatus,
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
    LogLevel,
    MAX_FILE_SIZE_BYTES,
    MAX_RETRY_ATTEMPTS,
    MAX_SEO_PAGES_PER_COMMIT,
    MAX_SITEMAP_URLS,
    RETRY_BACKOFF_MULTIPLIER,
    RETRY_DELAY_SECONDS,
    ReviewDecision,
    SUPPORTED_FRAMEWORKS,
)


# =============================================================================
# TestLogLevel
# =============================================================================


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_log_level_debug_value(self):
        """LogLevel.DEBUG has correct value."""
        assert LogLevel.DEBUG.value == "DEBUG"

    def test_log_level_info_value(self):
        """LogLevel.INFO has correct value."""
        assert LogLevel.INFO.value == "INFO"

    def test_log_level_warning_value(self):
        """LogLevel.WARNING has correct value."""
        assert LogLevel.WARNING.value == "WARNING"

    def test_log_level_error_value(self):
        """LogLevel.ERROR has correct value."""
        assert LogLevel.ERROR.value == "ERROR"

    def test_log_level_critical_value(self):
        """LogLevel.CRITICAL has correct value."""
        assert LogLevel.CRITICAL.value == "CRITICAL"

    def test_log_level_is_string_enum(self):
        """LogLevel inherits from str."""
        assert isinstance(LogLevel.DEBUG, str)
        assert isinstance(LogLevel.INFO, str)

    def test_log_level_all_values_exist(self):
        """All expected log levels exist."""
        expected = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        actual = {level.value for level in LogLevel}
        assert actual == expected


# =============================================================================
# TestExecutionStatus
# =============================================================================


class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_execution_status_pending_value(self):
        """ExecutionStatus.PENDING has correct value."""
        assert ExecutionStatus.PENDING.value == "pending"

    def test_execution_status_in_progress_value(self):
        """ExecutionStatus.IN_PROGRESS has correct value."""
        assert ExecutionStatus.IN_PROGRESS.value == "in_progress"

    def test_execution_status_completed_value(self):
        """ExecutionStatus.COMPLETED has correct value."""
        assert ExecutionStatus.COMPLETED.value == "completed"

    def test_execution_status_failed_value(self):
        """ExecutionStatus.FAILED has correct value."""
        assert ExecutionStatus.FAILED.value == "failed"

    def test_execution_status_cancelled_value(self):
        """ExecutionStatus.CANCELLED has correct value."""
        assert ExecutionStatus.CANCELLED.value == "cancelled"

    def test_execution_status_retrying_value(self):
        """ExecutionStatus.RETRYING has correct value."""
        assert ExecutionStatus.RETRYING.value == "retrying"

    def test_execution_status_is_string_enum(self):
        """ExecutionStatus inherits from str."""
        assert isinstance(ExecutionStatus.PENDING, str)

    def test_execution_status_all_values_exist(self):
        """All expected execution statuses exist."""
        expected = {
            "pending",
            "in_progress",
            "completed",
            "failed",
            "cancelled",
            "retrying",
        }
        actual = {status.value for status in ExecutionStatus}
        assert actual == expected


# =============================================================================
# TestReviewDecision
# =============================================================================


class TestReviewDecision:
    """Tests for ReviewDecision enum."""

    def test_review_decision_approved_value(self):
        """ReviewDecision.APPROVED has correct value."""
        assert ReviewDecision.APPROVED.value == "approved"

    def test_review_decision_rejected_value(self):
        """ReviewDecision.REJECTED has correct value."""
        assert ReviewDecision.REJECTED.value == "rejected"

    def test_review_decision_needs_revision_value(self):
        """ReviewDecision.NEEDS_REVISION has correct value."""
        assert ReviewDecision.NEEDS_REVISION.value == "needs_revision"

    def test_review_decision_is_string_enum(self):
        """ReviewDecision inherits from str."""
        assert isinstance(ReviewDecision.APPROVED, str)

    def test_review_decision_all_values_exist(self):
        """All expected review decisions exist."""
        expected = {"approved", "rejected", "needs_revision"}
        actual = {decision.value for decision in ReviewDecision}
        assert actual == expected


# =============================================================================
# TestRetryConfiguration
# =============================================================================


class TestRetryConfiguration:
    """Tests for retry-related constants."""

    def test_max_retry_attempts(self):
        """MAX_RETRY_ATTEMPTS is 3."""
        assert MAX_RETRY_ATTEMPTS == 3

    def test_retry_delay_seconds(self):
        """RETRY_DELAY_SECONDS is 1.0."""
        assert RETRY_DELAY_SECONDS == 1.0

    def test_retry_backoff_multiplier(self):
        """RETRY_BACKOFF_MULTIPLIER is 2.0."""
        assert RETRY_BACKOFF_MULTIPLIER == 2.0

    def test_retry_values_are_positive(self):
        """Retry values are positive numbers."""
        assert MAX_RETRY_ATTEMPTS > 0
        assert RETRY_DELAY_SECONDS > 0
        assert RETRY_BACKOFF_MULTIPLIER > 0


# =============================================================================
# TestSEOConfiguration
# =============================================================================


class TestSEOConfiguration:
    """Tests for SEO-related constants."""

    def test_max_seo_pages_per_commit(self):
        """MAX_SEO_PAGES_PER_COMMIT is 10."""
        assert MAX_SEO_PAGES_PER_COMMIT == 10

    def test_default_meta_description_length(self):
        """DEFAULT_META_DESCRIPTION_LENGTH is 160."""
        assert DEFAULT_META_DESCRIPTION_LENGTH == 160

    def test_default_meta_title_length(self):
        """DEFAULT_META_TITLE_LENGTH is 60."""
        assert DEFAULT_META_TITLE_LENGTH == 60

    def test_seo_values_are_positive(self):
        """SEO values are positive numbers."""
        assert MAX_SEO_PAGES_PER_COMMIT > 0
        assert DEFAULT_META_DESCRIPTION_LENGTH > 0
        assert DEFAULT_META_TITLE_LENGTH > 0


# =============================================================================
# TestFileSizeLimits
# =============================================================================


class TestFileSizeLimits:
    """Tests for file size limit constants."""

    def test_max_file_size_bytes(self):
        """MAX_FILE_SIZE_BYTES is 10 MB."""
        assert MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024
        assert MAX_FILE_SIZE_BYTES == 10_485_760

    def test_max_sitemap_urls(self):
        """MAX_SITEMAP_URLS is 50000."""
        assert MAX_SITEMAP_URLS == 50000

    def test_file_size_values_are_positive(self):
        """File size values are positive."""
        assert MAX_FILE_SIZE_BYTES > 0
        assert MAX_SITEMAP_URLS > 0


# =============================================================================
# TestTimeoutValues
# =============================================================================


class TestTimeoutValues:
    """Tests for timeout-related constants."""

    def test_default_timeout(self):
        """DEFAULT_TIMEOUT is 30.0 seconds."""
        assert DEFAULT_TIMEOUT == 30.0

    def test_long_running_timeout(self):
        """LONG_RUNNING_TIMEOUT is 300.0 seconds."""
        assert LONG_RUNNING_TIMEOUT == 300.0

    def test_long_running_timeout_greater_than_default(self):
        """LONG_RUNNING_TIMEOUT is greater than DEFAULT_TIMEOUT."""
        assert LONG_RUNNING_TIMEOUT > DEFAULT_TIMEOUT

    def test_timeout_values_are_positive(self):
        """Timeout values are positive numbers."""
        assert DEFAULT_TIMEOUT > 0
        assert LONG_RUNNING_TIMEOUT > 0


# =============================================================================
# TestGitConfiguration
# =============================================================================


class TestGitConfiguration:
    """Tests for Git-related constants."""

    def test_default_branch_name(self):
        """DEFAULT_BRANCH_NAME is 'main'."""
        assert DEFAULT_BRANCH_NAME == "main"

    def test_commit_message_prefix(self):
        """COMMIT_MESSAGE_PREFIX is 'feat: SEO improvements'."""
        assert COMMIT_MESSAGE_PREFIX == "feat: SEO improvements"

    def test_default_branch_name_is_string(self):
        """DEFAULT_BRANCH_NAME is a string."""
        assert isinstance(DEFAULT_BRANCH_NAME, str)

    def test_commit_message_prefix_is_string(self):
        """COMMIT_MESSAGE_PREFIX is a string."""
        assert isinstance(COMMIT_MESSAGE_PREFIX, str)


# =============================================================================
# TestFrameworkIdentifiers
# =============================================================================


class TestFrameworkIdentifiers:
    """Tests for framework identifier constants."""

    def test_framework_react(self):
        """FRAMEWORK_REACT is 'react'."""
        assert FRAMEWORK_REACT == "react"

    def test_framework_nextjs(self):
        """FRAMEWORK_NEXTJS is 'nextjs'."""
        assert FRAMEWORK_NEXTJS == "nextjs"

    def test_framework_vue(self):
        """FRAMEWORK_VUE is 'vue'."""
        assert FRAMEWORK_VUE == "vue"

    def test_framework_nuxt(self):
        """FRAMEWORK_NUXT is 'nuxt'."""
        assert FRAMEWORK_NUXT == "nuxt"

    def test_framework_angular(self):
        """FRAMEWORK_ANGULAR is 'angular'."""
        assert FRAMEWORK_ANGULAR == "angular"

    def test_framework_django(self):
        """FRAMEWORK_DJANGO is 'django'."""
        assert FRAMEWORK_DJANGO == "django"

    def test_framework_flask(self):
        """FRAMEWORK_FLASK is 'flask'."""
        assert FRAMEWORK_FLASK == "flask"

    def test_framework_express(self):
        """FRAMEWORK_EXPRESS is 'express'."""
        assert FRAMEWORK_EXPRESS == "express"

    def test_framework_gatsby(self):
        """FRAMEWORK_GATSBY is 'gatsby'."""
        assert FRAMEWORK_GATSBY == "gatsby"

    def test_framework_html(self):
        """FRAMEWORK_HTML is 'html'."""
        assert FRAMEWORK_HTML == "html"

    def test_all_framework_identifiers_are_strings(self):
        """All framework identifiers are strings."""
        frameworks = [
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
        for fw in frameworks:
            assert isinstance(fw, str)


# =============================================================================
# TestSupportedFrameworks
# =============================================================================


class TestSupportedFrameworks:
    """Tests for SUPPORTED_FRAMEWORKS list."""

    def test_supported_frameworks_is_list(self):
        """SUPPORTED_FRAMEWORKS is a list."""
        assert isinstance(SUPPORTED_FRAMEWORKS, list)

    def test_supported_frameworks_has_10_items(self):
        """SUPPORTED_FRAMEWORKS has 10 items."""
        assert len(SUPPORTED_FRAMEWORKS) == 10

    def test_supported_frameworks_contains_react(self):
        """SUPPORTED_FRAMEWORKS contains 'react'."""
        assert "react" in SUPPORTED_FRAMEWORKS

    def test_supported_frameworks_contains_nextjs(self):
        """SUPPORTED_FRAMEWORKS contains 'nextjs'."""
        assert "nextjs" in SUPPORTED_FRAMEWORKS

    def test_supported_frameworks_contains_vue(self):
        """SUPPORTED_FRAMEWORKS contains 'vue'."""
        assert "vue" in SUPPORTED_FRAMEWORKS

    def test_supported_frameworks_contains_nuxt(self):
        """SUPPORTED_FRAMEWORKS contains 'nuxt'."""
        assert "nuxt" in SUPPORTED_FRAMEWORKS

    def test_supported_frameworks_contains_angular(self):
        """SUPPORTED_FRAMEWORKS contains 'angular'."""
        assert "angular" in SUPPORTED_FRAMEWORKS

    def test_supported_frameworks_contains_django(self):
        """SUPPORTED_FRAMEWORKS contains 'django'."""
        assert "django" in SUPPORTED_FRAMEWORKS

    def test_supported_frameworks_contains_flask(self):
        """SUPPORTED_FRAMEWORKS contains 'flask'."""
        assert "flask" in SUPPORTED_FRAMEWORKS

    def test_supported_frameworks_contains_express(self):
        """SUPPORTED_FRAMEWORKS contains 'express'."""
        assert "express" in SUPPORTED_FRAMEWORKS

    def test_supported_frameworks_contains_gatsby(self):
        """SUPPORTED_FRAMEWORKS contains 'gatsby'."""
        assert "gatsby" in SUPPORTED_FRAMEWORKS

    def test_supported_frameworks_contains_html(self):
        """SUPPORTED_FRAMEWORKS contains 'html'."""
        assert "html" in SUPPORTED_FRAMEWORKS

    def test_supported_frameworks_matches_individual_constants(self):
        """SUPPORTED_FRAMEWORKS matches individual framework constants."""
        expected = [
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
        assert SUPPORTED_FRAMEWORKS == expected

    def test_supported_frameworks_all_strings(self):
        """All items in SUPPORTED_FRAMEWORKS are strings."""
        for fw in SUPPORTED_FRAMEWORKS:
            assert isinstance(fw, str)


# =============================================================================
# TestConstantsIntegration
# =============================================================================


class TestConstantsIntegration:
    """Integration tests for constants module."""

    def test_log_level_can_be_used_as_string(self):
        """LogLevel values can be used as strings."""
        level = LogLevel.INFO
        assert level == "INFO"
        assert level.lower() == "info"

    def test_execution_status_can_be_used_as_string(self):
        """ExecutionStatus values can be used as strings."""
        status = ExecutionStatus.COMPLETED
        assert status == "completed"

    def test_review_decision_can_be_used_as_string(self):
        """ReviewDecision values can be used as strings."""
        decision = ReviewDecision.APPROVED
        assert decision == "approved"

    def test_framework_in_supported_list(self):
        """Framework constants are in SUPPORTED_FRAMEWORKS."""
        assert FRAMEWORK_REACT in SUPPORTED_FRAMEWORKS
        assert FRAMEWORK_DJANGO in SUPPORTED_FRAMEWORKS
        assert FRAMEWORK_HTML in SUPPORTED_FRAMEWORKS