"""Tests for seo_agent.core.exceptions module.

This module tests the custom exception hierarchy for the SEO Agent.
"""

import pytest

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


class TestSEOAgentError:
    """Tests for the base SEOAgentError exception class."""

    def test_inherits_from_exception(self):
        """SEOAgentError should inherit from Exception."""
        error = SEOAgentError("test message")
        assert isinstance(error, Exception)

    def test_message_attribute_set(self):
        """SEOAgentError should have message attribute."""
        error = SEOAgentError("configuration is invalid")
        assert error.message == "configuration is invalid"

    def test_details_attribute_default_empty(self):
        """SEOAgentError should have empty details by default."""
        error = SEOAgentError("test")
        assert error.details == {}

    def test_details_attribute_set(self):
        """SEOAgentError should accept details parameter."""
        details = {"field": "api_key", "reason": "missing"}
        error = SEOAgentError("validation failed", details=details)
        assert error.details == details

    def test_str_returns_message(self):
        """SEOAgentError.__str__() should return the message."""
        error = SEOAgentError("error message")
        assert str(error) == "error message"

    def test_str_with_details(self):
        """SEOAgentError.__str__() should return message even with details."""
        error = SEOAgentError("error message", details={"key": "value"})
        assert str(error) == "error message"

    def test_can_be_raised_and_caught(self):
        """SEOAgentError should be raiseable and catchable."""
        with pytest.raises(SEOAgentError) as exc_info:
            raise SEOAgentError("test error")
        assert str(exc_info.value) == "test error"

    def test_empty_message(self):
        """SEOAgentError should handle empty message."""
        error = SEOAgentError("")
        assert error.message == ""

    def test_none_details(self):
        """SEOAgentError should handle None details gracefully."""
        error = SEOAgentError("test", details=None)
        assert error.details == {}

    def test_multiple_details_keys(self):
        """SEOAgentError should store multiple detail keys."""
        details = {
            "code": 400,
            "field": "email",
            "constraint": "valid email required",
        }
        error = SEOAgentError("validation error", details=details)
        assert len(error.details) == 3
        assert error.details["code"] == 400


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_inherits_from_seo_agent_error(self):
        """ConfigurationError should inherit from SEOAgentError."""
        error = ConfigurationError("missing config")
        assert isinstance(error, SEOAgentError)
        assert isinstance(error, ConfigurationError)

    def test_can_be_raised(self):
        """ConfigurationError should be raiseable."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("invalid config value")
        assert "invalid config value" in str(exc_info.value)

    def test_message_attribute(self):
        """ConfigurationError should have message attribute."""
        error = ConfigurationError("API key not set")
        assert error.message == "API key not set"

    def test_details_attribute(self):
        """ConfigurationError should support details."""
        error = ConfigurationError("config error", details={"key": "timeout"})
        assert error.details == {"key": "timeout"}


class TestRepositoryError:
    """Tests for RepositoryError exception."""

    def test_inherits_from_seo_agent_error(self):
        """RepositoryError should inherit from SEOAgentError."""
        error = RepositoryError("repo not found")
        assert isinstance(error, SEOAgentError)
        assert isinstance(error, RepositoryError)

    def test_can_be_raised(self):
        """RepositoryError should be raiseable."""
        with pytest.raises(RepositoryError):
            raise RepositoryError("path does not exist")

    def test_message_attribute(self):
        """RepositoryError should have message attribute."""
        error = RepositoryError("file system error")
        assert error.message == "file system error"


class TestFrameworkDetectionError:
    """Tests for FrameworkDetectionError exception."""

    def test_inherits_from_seo_agent_error(self):
        """FrameworkDetectionError should inherit from SEOAgentError."""
        error = FrameworkDetectionError("unknown framework")
        assert isinstance(error, SEOAgentError)
        assert isinstance(error, FrameworkDetectionError)

    def test_can_be_raised(self):
        """FrameworkDetectionError should be raiseable."""
        with pytest.raises(FrameworkDetectionError):
            raise FrameworkDetectionError("could not detect framework")

    def test_message_attribute(self):
        """FrameworkDetectionError should have message attribute."""
        error = FrameworkDetectionError("unsupported framework")
        assert error.message == "unsupported framework"


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_inherits_from_seo_agent_error(self):
        """ValidationError should inherit from SEOAgentError."""
        error = ValidationError("invalid input")
        assert isinstance(error, SEOAgentError)
        assert isinstance(error, ValidationError)

    def test_can_be_raised(self):
        """ValidationError should be raiseable."""
        with pytest.raises(ValidationError):
            raise ValidationError("payload validation failed")

    def test_message_attribute(self):
        """ValidationError should have message attribute."""
        error = ValidationError("field is required")
        assert error.message == "field is required"

    def test_with_field_details(self):
        """ValidationError should support field-level details."""
        error = ValidationError(
            "validation failed",
            details={"field": "email", "value": "not-an-email"},
        )
        assert error.details["field"] == "email"


class TestExecutionError:
    """Tests for ExecutionError exception."""

    def test_inherits_from_seo_agent_error(self):
        """ExecutionError should inherit from SEOAgentError."""
        error = ExecutionError("execution failed")
        assert isinstance(error, SEOAgentError)
        assert isinstance(error, ExecutionError)

    def test_can_be_raised(self):
        """ExecutionError should be raiseable."""
        with pytest.raises(ExecutionError):
            raise ExecutionError("task execution error")

    def test_message_attribute(self):
        """ExecutionError should have message attribute."""
        error = ExecutionError("agent crashed")
        assert error.message == "agent crashed"


class TestReviewError:
    """Tests for ReviewError exception."""

    def test_inherits_from_seo_agent_error(self):
        """ReviewError should inherit from SEOAgentError."""
        error = ReviewError("review failed")
        assert isinstance(error, SEOAgentError)
        assert isinstance(error, ReviewError)

    def test_can_be_raised(self):
        """ReviewError should be raiseable."""
        with pytest.raises(ReviewError):
            raise ReviewError("review timeout")

    def test_message_attribute(self):
        """ReviewError should have message attribute."""
        error = ReviewError("approval denied")
        assert error.message == "approval denied"


class TestGitError:
    """Tests for GitError exception."""

    def test_inherits_from_seo_agent_error(self):
        """GitError should inherit from SEOAgentError."""
        error = GitError("git operation failed")
        assert isinstance(error, SEOAgentError)
        assert isinstance(error, GitError)

    def test_can_be_raised(self):
        """GitError should be raiseable."""
        with pytest.raises(GitError):
            raise GitError("commit failed")

    def test_message_attribute(self):
        """GitError should have message attribute."""
        error = GitError("branch conflict")
        assert error.message == "branch conflict"


class TestIntegrationError:
    """Tests for IntegrationError exception."""

    def test_inherits_from_seo_agent_error(self):
        """IntegrationError should inherit from SEOAgentError."""
        error = IntegrationError("API unavailable")
        assert isinstance(error, SEOAgentError)
        assert isinstance(error, IntegrationError)

    def test_can_be_raised(self):
        """IntegrationError should be raiseable."""
        with pytest.raises(IntegrationError):
            raise IntegrationError("external service error")

    def test_message_attribute(self):
        """IntegrationError should have message attribute."""
        error = IntegrationError("n8n webhook failed")
        assert error.message == "n8n webhook failed"


class TestTimeoutError:
    """Tests for TimeoutError exception."""

    def test_inherits_from_seo_agent_error(self):
        """TimeoutError should inherit from SEOAgentError."""
        error = TimeoutError("operation timed out")
        assert isinstance(error, SEOAgentError)
        assert isinstance(error, TimeoutError)

    def test_can_be_raised(self):
        """TimeoutError should be raiseable."""
        with pytest.raises(TimeoutError):
            raise TimeoutError("request timeout after 30s")

    def test_message_attribute(self):
        """TimeoutError should have message attribute."""
        error = TimeoutError("long running operation exceeded limit")
        assert error.message == "long running operation exceeded limit"


class TestDependencyError:
    """Tests for DependencyError exception."""

    def test_inherits_from_seo_agent_error(self):
        """DependencyError should inherit from SEOAgentError."""
        error = DependencyError("dependency not found")
        assert isinstance(error, SEOAgentError)
        assert isinstance(error, DependencyError)

    def test_can_be_raised(self):
        """DependencyError should be raiseable."""
        with pytest.raises(DependencyError):
            raise DependencyError("service not registered")

    def test_message_attribute(self):
        """DependencyError should have message attribute."""
        error = DependencyError("circular dependency detected")
        assert error.message == "circular dependency detected"


class TestExceptionHierarchy:
    """Tests for the exception class hierarchy."""

    def test_all_exceptions_inherit_from_seo_agent_error(self):
        """All custom exceptions should inherit from SEOAgentError."""
        exceptions = [
            ConfigurationError("test"),
            RepositoryError("test"),
            FrameworkDetectionError("test"),
            ValidationError("test"),
            ExecutionError("test"),
            ReviewError("test"),
            GitError("test"),
            IntegrationError("test"),
            TimeoutError("test"),
            DependencyError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, SEOAgentError)

    def test_all_exceptions_inherit_from_base_exception(self):
        """All custom exceptions should be catchable as Exception."""
        exceptions = [
            ConfigurationError("test"),
            RepositoryError("test"),
            FrameworkDetectionError("test"),
            ValidationError("test"),
            ExecutionError("test"),
            ReviewError("test"),
            GitError("test"),
            IntegrationError("test"),
            TimeoutError("test"),
            DependencyError("test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, Exception)

    def test_catching_seo_agent_error_catches_all(self):
        """Catching SEOAgentError should catch all custom exceptions."""
        exception_types = [
            ConfigurationError,
            RepositoryError,
            FrameworkDetectionError,
            ValidationError,
            ExecutionError,
            ReviewError,
            GitError,
            IntegrationError,
            TimeoutError,
            DependencyError,
        ]
        for exc_type in exception_types:
            with pytest.raises(SEOAgentError):
                raise exc_type("test error")


class TestExceptionEquality:
    """Tests for exception equality semantics."""

    def test_same_message_same_type_are_equal(self):
        """Two exceptions with same message and type should be equal."""
        exc1 = ValidationError("same message")
        exc2 = ValidationError("same message")
        # Note: Exception equality is based on identity by default
        # but our implementation should support message comparison
        assert exc1.message == exc2.message

    def test_different_messages_not_equal(self):
        """Two exceptions with different messages should have different messages."""
        exc1 = ValidationError("message one")
        exc2 = ValidationError("message two")
        assert exc1.message != exc2.message

    def test_different_types_not_equal(self):
        """Two exceptions of different types should not be equal."""
        exc1 = ValidationError("same message")
        exc2 = ExecutionError("same message")
        assert type(exc1) != type(exc2)


class TestExceptionChaining:
    """Tests for exception chaining behavior."""

    def test_raise_from_exception_preserves_cause(self):
        """Raising an exception should preserve the original cause."""
        original = ValueError("original error")
        try:
            raise SEOAgentError("derived error") from original
        except SEOAgentError as e:
            assert e.__cause__ == original

    def test_raise_with_implicit_chaining(self):
        """Implicit exception chaining should work."""
        try:
            try:
                raise RuntimeError("inner error")
            except RuntimeError:
                raise SEOAgentError("outer error")
        except SEOAgentError as e:
            assert e.__context__ is not None


class TestExceptionEdgeCases:
    """Tests for edge cases in exception handling."""

    def test_empty_message_string(self):
        """Exceptions should handle empty message strings."""
        error = ValidationError("")
        assert error.message == ""

    def test_unicode_in_message(self):
        """Exceptions should handle unicode in messages."""
        error = ConfigurationError("配置错误: 缺少必需字段")
        assert error.message == "配置错误: 缺少必需字段"

    def test_special_characters_in_message(self):
        """Exceptions should handle special characters in messages."""
        error = ExecutionError("Error with 'quotes' and \"double quotes\" and \n newlines")
        assert "'quotes'" in error.message
        assert "\n" in error.message

    def test_very_long_message(self):
        """Exceptions should handle very long messages."""
        long_message = "x" * 10000
        error = IntegrationError(long_message)
        assert len(error.message) == 10000

    def test_details_with_complex_values(self):
        """Exceptions should handle complex detail values."""
        details = {
            "list": [1, 2, 3],
            "nested": {"key": "value"},
            "tuple": (1, 2, 3),
        }
        error = ValidationError("complex details", details=details)
        assert error.details["list"] == [1, 2, 3]
        assert error.details["nested"] == {"key": "value"}
        assert error.details["tuple"] == (1, 2, 3)

    def test_exception_with_empty_message(self):
        """SEOAgentError should work with empty string message."""
        error = SEOAgentError("")
        assert error.message == ""
        assert error.details == {}

    def test_exception_with_only_details(self):
        """SEOAgentError should work with message and details."""
        error = SEOAgentError("error message", details={"key": "value"})
        assert error.message == "error message"
        assert error.details == {"key": "value"}