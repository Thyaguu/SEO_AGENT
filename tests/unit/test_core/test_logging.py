"""Unit tests for seo_agent.core.logging."""

import io
import logging
import sys

import pytest

from seo_agent.core.logging import (
    _is_sensitive,
    bind_context,
    configure_logging,
    get_logger,
    log_function_call,
    reset_loggers,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_logger_registry():
    """Reset logger registry before and after each test."""
    reset_loggers()
    yield
    reset_loggers()


@pytest.fixture
def mock_stdout():
    """Create a StringIO mock for stdout."""
    return io.StringIO()


@pytest.fixture
def capture_logging(mock_stdout, monkeypatch):
    """Capture logging output to mock stdout."""
    monkeypatch.setattr(sys, "stdout", mock_stdout)
    return mock_stdout


# =============================================================================
# TestConfigureLogging
# =============================================================================


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_logging_sets_root_logger_level(self, monkeypatch):
        """configure_logging sets the root logger level."""
        configure_logging(level="DEBUG")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_logging_adds_handler(self, monkeypatch):
        """configure_logging adds a StreamHandler to root logger."""
        configure_logging(level="INFO")
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_configure_logging_with_debug_level(self, monkeypatch):
        """configure_logging works with DEBUG level."""
        configure_logging(level="DEBUG")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_logging_with_info_level(self, monkeypatch):
        """configure_logging works with INFO level."""
        configure_logging(level="INFO")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_configure_logging_with_warning_level(self, monkeypatch):
        """configure_logging works with WARNING level."""
        configure_logging(level="WARNING")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_configure_logging_with_error_level(self, monkeypatch):
        """configure_logging works with ERROR level."""
        configure_logging(level="ERROR")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR

    def test_configure_logging_with_critical_level(self, monkeypatch):
        """configure_logging works with CRITICAL level."""
        configure_logging(level="CRITICAL")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.CRITICAL

    def test_configure_logging_invalid_level_defaults_to_info(self, monkeypatch):
        """configure_logging with invalid level defaults to INFO."""
        configure_logging(level="INVALID")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_configure_logging_removes_existing_handlers(self, monkeypatch):
        """configure_logging removes existing handlers before adding new."""
        # Add a handler before configure_logging
        extra_handler = logging.StreamHandler()
        extra_handler.setLevel(logging.DEBUG)
        root_logger = logging.getLogger()
        root_logger.addHandler(extra_handler)
        initial_count = len(root_logger.handlers)

        configure_logging(level="INFO")

        # Should have same number of handlers (replaced, not added)
        assert len(root_logger.handlers) == initial_count

    def test_configure_logging_sets_text_formatter_by_default(self, monkeypatch):
        """configure_logging sets text formatter when format_json=False."""
        configure_logging(level="INFO", format_json=False)
        root_logger = logging.getLogger()
        formatter = root_logger.handlers[0].formatter
        assert formatter is not None
        # Text formatter contains asctime placeholder
        fmt_string = formatter._fmt
        assert "%(asctime)s" in fmt_string

    def test_configure_logging_sets_json_formatter_when_requested(self, monkeypatch):
        """configure_logging sets JSON formatter when format_json=True."""
        configure_logging(level="INFO", format_json=True)
        root_logger = logging.getLogger()
        formatter = root_logger.handlers[0].formatter
        assert formatter is not None
        # JSON formatter contains time and level
        fmt_string = formatter._fmt
        assert "time" in fmt_string
        assert "level" in fmt_string


# =============================================================================
# TestGetLogger
# =============================================================================


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger_instance(self):
        """get_logger returns a logging.Logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_uses_provided_name(self):
        """get_logger creates logger with the provided name."""
        logger = get_logger("my.custom.module")
        assert logger.name == "my.custom.module"

    def test_get_logger_caches_loggers(self):
        """get_logger returns the same instance for same name."""
        logger1 = get_logger("cached_logger")
        logger2 = get_logger("cached_logger")
        assert logger1 is logger2

    def test_get_logger_different_names_different_instances(self):
        """get_logger returns different instances for different names."""
        logger1 = get_logger("module_one")
        logger2 = get_logger("module_two")
        assert logger1 is not logger2
        assert logger1.name == "module_one"
        assert logger2.name == "module_two"

    def test_get_logger_multiple_calls_same_name(self):
        """Multiple calls with same name return same cached logger."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        logger3 = get_logger("test")
        assert logger1 is logger2 is logger3


# =============================================================================
# TestBindContext
# =============================================================================


class TestBindContext:
    """Tests for bind_context function."""

    def test_bind_context_returns_dict(self):
        """bind_context returns a dictionary."""
        result = bind_context()
        assert isinstance(result, dict)

    def test_bind_context_empty_call_returns_empty_dict(self):
        """bind_context with no args returns empty dict."""
        result = bind_context()
        assert result == {}

    def test_bind_context_single_key_value(self):
        """bind_context returns kwargs as dict."""
        result = bind_context(user_id=123)
        assert result == {"user_id": 123}

    def test_bind_context_multiple_key_values(self):
        """bind_context returns multiple kwargs as dict."""
        result = bind_context(user_id=123, action="login", success=True)
        assert result == {"user_id": 123, "action": "login", "success": True}

    def test_bind_context_preserves_types(self):
        """bind_context preserves value types."""
        result = bind_context(
            string_val="test",
            int_val=42,
            float_val=3.14,
            bool_val=True,
            list_val=[1, 2, 3],
            dict_val={"nested": "value"},
        )
        assert result["string_val"] == "test"
        assert result["int_val"] == 42
        assert result["float_val"] == 3.14
        assert result["bool_val"] is True
        assert result["list_val"] == [1, 2, 3]
        assert result["dict_val"] == {"nested": "value"}


# =============================================================================
# TestLogFunctionCall
# =============================================================================


class TestLogFunctionCall:
    """Tests for log_function_call function."""

    def test_log_function_call_logs_function_name(self, caplog):
        """log_function_call logs the function name."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(logger, "my_function")
        assert "my_function" in caplog.text

    def test_log_function_call_includes_arg_count(self, caplog):
        """log_function_call includes argument count in log."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(logger, "my_function", args=(1, 2, 3))
        assert "arg_count" in caplog.text
        assert "3" in caplog.text

    def test_log_function_call_includes_kwargs(self, caplog):
        """log_function_call includes non-sensitive kwargs in log."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(logger, "my_function", kwargs={"count": 5, "name": "test"})
        assert "count" in caplog.text
        assert "5" in caplog.text
        assert "name" in caplog.text
        assert "test" in caplog.text

    def test_log_function_call_filters_sensitive_kwargs(self, caplog):
        """log_function_call filters out sensitive kwargs."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(
                logger,
                "my_function",
                kwargs={"password": "secret123", "username": "admin"},
            )
        # password should not appear in log
        assert "secret123" not in caplog.text
        # username should appear (not sensitive)
        assert "admin" in caplog.text

    def test_log_function_call_filters_token(self, caplog):
        """log_function_call filters 'token' keyword."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(logger, "auth", kwargs={"api_token": "abc123"})
        assert "abc123" not in caplog.text

    def test_log_function_call_filters_secret(self, caplog):
        """log_function_call filters 'secret' keyword."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(logger, "config", kwargs={"app_secret": "hidden"})
        assert "hidden" not in caplog.text

    def test_log_function_call_filters_api_key(self, caplog):
        """log_function_call filters 'key' keyword."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(logger, "api", kwargs={"api_key": "xyz789"})
        assert "xyz789" not in caplog.text

    def test_log_function_call_filters_auth(self, caplog):
        """log_function_call filters 'auth' keyword."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(logger, "login", kwargs={"auth_token": "token123"})
        assert "token123" not in caplog.text

    def test_log_function_call_with_none_args(self, caplog):
        """log_function_call handles None args gracefully."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(logger, "my_function", args=None)
        assert "my_function" in caplog.text

    def test_log_function_call_with_none_kwargs(self, caplog):
        """log_function_call handles None kwargs gracefully."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(logger, "my_function", kwargs=None)
        assert "my_function" in caplog.text

    def test_log_function_call_empty_args_and_kwargs(self, caplog):
        """log_function_call works with empty args and kwargs."""
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_function_call(logger, "my_function", args=(), kwargs={})
        assert "my_function" in caplog.text


# =============================================================================
# TestIsSensitive
# =============================================================================


class TestIsSensitive:
    """Tests for _is_sensitive function."""

    def test_is_sensitive_detects_password(self):
        """_is_sensitive returns True for 'password'."""
        assert _is_sensitive("password") is True
        assert _is_sensitive("user_password") is True
        assert _is_sensitive("PASSWORD") is True
        assert _is_sensitive("Password") is True

    def test_is_sensitive_detects_token(self):
        """_is_sensitive returns True for 'token'."""
        assert _is_sensitive("token") is True
        assert _is_sensitive("auth_token") is True
        assert _is_sensitive("accessToken") is True
        assert _is_sensitive("TOKEN") is True

    def test_is_sensitive_detects_secret(self):
        """_is_sensitive returns True for 'secret'."""
        assert _is_sensitive("secret") is True
        assert _is_sensitive("app_secret") is True
        assert _is_sensitive("SECRET") is True

    def test_is_sensitive_detects_key(self):
        """_is_sensitive returns True for 'key'."""
        assert _is_sensitive("key") is True
        assert _is_sensitive("api_key") is True
        assert _is_sensitive("secret_key") is True
        assert _is_sensitive("KEY") is True

    def test_is_sensitive_detects_auth(self):
        """_is_sensitive returns True for 'auth'."""
        assert _is_sensitive("auth") is True
        assert _is_sensitive("auth_token") is True
        assert _is_sensitive("AUTH") is True

    def test_is_sensitive_returns_false_for_safe_keys(self):
        """_is_sensitive returns False for non-sensitive keys."""
        assert _is_sensitive("username") is False
        assert _is_sensitive("email") is False
        assert _is_sensitive("name") is False
        assert _is_sensitive("count") is False
        assert _is_sensitive("value") is False
        assert _is_sensitive("data") is False

    def test_is_sensitive_case_insensitive(self):
        """_is_sensitive is case insensitive."""
        assert _is_sensitive("PASSWORD") is True
        assert _is_sensitive("Token") is True
        assert _is_sensitive("Secret") is True
        assert _is_sensitive("ApiKey") is True
        assert _is_sensitive("Auth") is True


# =============================================================================
# TestResetLoggers
# =============================================================================


class TestResetLoggers:
    """Tests for reset_loggers function."""

    def test_reset_loggers_clears_registry(self):
        """reset_loggers clears the logger registry."""
        get_logger("test1")
        get_logger("test2")
        reset_loggers()
        # After reset, getting a logger should create new instance
        logger = get_logger("test1")
        assert logger.name == "test1"

    def test_reset_loggers_allows_fresh_start(self):
        """reset_loggers allows starting fresh with new loggers."""
        logger1 = get_logger("fresh_test")
        reset_loggers()
        logger2 = get_logger("fresh_test")
        # Should be different instances after reset
        assert logger1 is not logger2


# =============================================================================
# TestIntegration
# =============================================================================


class TestLoggingIntegration:
    """Integration tests for logging module."""

    def test_configure_and_get_logger(self, monkeypatch):
        """configure_logging affects loggers returned by get_logger."""
        configure_logging(level="DEBUG")
        logger = get_logger("configured_module")
        # Logger should inherit root logger level
        assert logger.level == logging.DEBUG

    def test_logging_produces_output(self, caplog, monkeypatch):
        """Logging produces expected output."""
        configure_logging(level="INFO")
        logger = get_logger("output_test")
        with caplog.at_level(logging.INFO):
            logger.info("test message", extra_field="value")
        assert "test message" in caplog.text

    def test_logger_name_in_output(self, caplog, monkeypatch):
        """Logger name appears in log output."""
        configure_logging(level="INFO")
        logger = get_logger("named_logger_test")
        with caplog.at_level(logging.INFO):
            logger.info("test")
        assert "named_logger_test" in caplog.text