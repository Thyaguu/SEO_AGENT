"""Tests for seo_agent.core.result module.

This module tests the Result type pattern for representing success/failure outcomes.
"""

import pytest

from seo_agent.core.result import (
    Failure,
    Success,
    failure,
    from_bool,
    from_exception,
    success,
)


class TestSuccess:
    """Tests for the Success class."""

    def test_is_success_returns_true(self):
        """Success.is_success() should return True."""
        result = Success(value=42)
        assert result.is_success() is True

    def test_is_failure_returns_false(self):
        """Success.is_failure() should return False."""
        result = Success(value="hello")
        assert result.is_failure() is False

    def test_get_or_none_returns_value(self):
        """Success.get_or_none() should return the value."""
        result = Success(value={"key": "value"})
        assert result.get_or_none() == {"key": "value"}

    def test_get_error_or_none_returns_none(self):
        """Success.get_error_or_none() should return None."""
        result = Success(value=3.14)
        assert result.get_error_or_none() is None

    def test_unwrap_returns_value(self):
        """Success.unwrap() should return the value."""
        result = Success(value="test_value")
        assert result.unwrap() == "test_value"

    def test_unwrap_or_returns_value(self):
        """Success.unwrap_or() should return the value, ignoring default."""
        result = Success(value="actual")
        assert result.unwrap_or("default") == "actual"

    def test_value_attribute_accessible(self):
        """Success.value should be accessible as an attribute."""
        result = Success(value=[1, 2, 3])
        assert result.value == [1, 2, 3]

    def test_value_can_be_none(self):
        """Success value can be None."""
        result = Success(value=None)
        assert result.value is None
        assert result.get_or_none() is None

    def test_value_can_be_empty_container(self):
        """Success value can be an empty container."""
        result = Success(value=[])
        assert result.value == []
        assert result.get_or_none() == []

    def test_value_can_be_complex_object(self):
        """Success value can be a complex object."""
        complex_value = {"nested": {"data": [1, 2, 3]}}
        result = Success(value=complex_value)
        assert result.value == complex_value


class TestFailure:
    """Tests for the Failure class."""

    def test_is_success_returns_false(self):
        """Failure.is_success() should return False."""
        result = Failure(error="error")
        assert result.is_success() is False

    def test_is_failure_returns_true(self):
        """Failure.is_failure() should return True."""
        result = Failure(error=42)
        assert result.is_failure() is True

    def test_get_or_none_returns_none(self):
        """Failure.get_or_none() should return None."""
        result = Failure(error="something went wrong")
        assert result.get_or_none() is None

    def test_get_error_or_none_returns_error(self):
        """Failure.get_error_or_none() should return the error."""
        result = Failure(error={"code": 500, "message": "Server error"})
        assert result.get_error_or_none() == {"code": 500, "message": "Server error"}

    def test_unwrap_raises_value_error(self):
        """Failure.unwrap() should raise ValueError with error message."""
        result = Failure(error="division by zero")
        with pytest.raises(ValueError, match="Attempted to unwrap a Failure: division by zero"):
            result.unwrap()

    def test_unwrap_raises_with_complex_error(self):
        """Failure.unwrap() should raise with complex error objects."""
        error_obj = {"code": 404, "details": "Not found"}
        result = Failure(error=error_obj)
        with pytest.raises(ValueError, match="Attempted to unwrap a Failure:"):
            result.unwrap()

    def test_unwrap_or_returns_default(self):
        """Failure.unwrap_or() should return the default value."""
        result = Failure(error="failed")
        assert result.unwrap_or("fallback") == "fallback"

    def test_unwrap_or_with_none_default(self):
        """Failure.unwrap_or() should return None when default is None."""
        result = Failure(error="error")
        assert result.unwrap_or(None) is None

    def test_error_attribute_accessible(self):
        """Failure.error should be accessible as an attribute."""
        result = Failure(error="test_error")
        assert result.error == "test_error"

    def test_error_can_be_none(self):
        """Failure error can be None."""
        result = Failure(error=None)
        assert result.error is None
        assert result.get_error_or_none() is None

    def test_error_can_be_complex_object(self):
        """Failure error can be a complex object."""
        error_obj = Exception("Something broke")
        result = Failure(error=error_obj)
        assert result.error == error_obj


class TestSuccessFactory:
    """Tests for the success() factory function."""

    def test_creates_success_with_value(self):
        """success() should create a Success instance."""
        result = success(42)
        assert isinstance(result, Success)
        assert result.value == 42

    def test_creates_success_with_string(self):
        """success() should handle string values."""
        result = success("hello world")
        assert result.value == "hello world"

    def test_creates_success_with_none(self):
        """success() should handle None values."""
        result = success(None)
        assert result.value is None

    def test_creates_success_with_list(self):
        """success() should handle list values."""
        result = success([1, 2, 3])
        assert result.value == [1, 2, 3]

    def test_creates_success_with_dict(self):
        """success() should handle dict values."""
        result = success({"key": "value"})
        assert result.value == {"key": "value"}


class TestFailureFactory:
    """Tests for the failure() factory function."""

    def test_creates_failure_with_string_error(self):
        """failure() should create a Failure instance with string error."""
        result = failure("error message")
        assert isinstance(result, Failure)
        assert result.error == "error message"

    def test_creates_failure_with_int_error(self):
        """failure() should handle integer errors."""
        result = failure(404)
        assert result.error == 404

    def test_creates_failure_with_dict_error(self):
        """failure() should handle dict errors."""
        result = failure({"code": 500, "msg": "Server error"})
        assert result.error == {"code": 500, "msg": "Server error"}

    def test_creates_failure_with_exception(self):
        """failure() should handle Exception objects."""
        exc = ValueError("invalid value")
        result = failure(exc)
        assert result.error == exc


class TestFromException:
    """Tests for the from_exception() function."""

    def test_converts_exception_to_failure(self):
        """from_exception() should convert an exception to Failure."""
        exc = ValueError("invalid input")
        result = from_exception(exc)
        assert isinstance(result, Failure)
        assert result.error == "invalid input"

    def test_uses_custom_error_message(self):
        """from_exception() should use custom message when provided."""
        exc = RuntimeError("original error")
        result = from_exception(exc, error_msg="Custom error message")
        assert result.error == "Custom error message"

    def test_handles_exception_without_message(self):
        """from_exception() should handle exceptions without message."""
        exc = Exception()
        result = from_exception(exc)
        assert isinstance(result, Failure)
        assert result.error == ""

    def test_handles_keyerror(self):
        """from_exception() should handle KeyError."""
        exc = KeyError("missing_key")
        result = from_exception(exc)
        assert result.error == "'missing_key'"

    def test_handles_type_error(self):
        """from_exception() should handle TypeError."""
        exc = TypeError("expected str, got int")
        result = from_exception(exc)
        assert result.error == "expected str, got int"


class TestFromBool:
    """Tests for the from_bool() function."""

    def test_true_returns_success(self):
        """from_bool() should return Success when value is True."""
        result = from_bool(True, success_val=42, error_val="failed")
        assert isinstance(result, Success)
        assert result.value == 42

    def test_false_returns_failure(self):
        """from_bool() should return Failure when value is False."""
        result = from_bool(False, success_val=42, error_val="failed")
        assert isinstance(result, Failure)
        assert result.error == "failed"

    def test_with_string_values(self):
        """from_bool() should handle string success and error values."""
        result_true = from_bool(True, success_val="ok", error_val="not ok")
        result_false = from_bool(False, success_val="ok", error_val="not ok")
        
        assert result_true.value == "ok"
        assert result_false.error == "not ok"

    def test_with_complex_values(self):
        """from_bool() should handle complex success and error values."""
        success_data = {"status": "ok", "data": [1, 2, 3]}
        error_data = {"status": "error", "code": 500}
        
        result_true = from_bool(True, success_val=success_data, error_val=error_data)
        result_false = from_bool(False, success_val=success_data, error_val=error_data)
        
        assert result_true.value == success_data
        assert result_false.error == error_data


class TestResultEquality:
    """Tests for Result equality semantics."""

    def test_success_with_same_value_are_equal(self):
        """Two Success instances with same value should be equal."""
        result1 = Success(value=42)
        result2 = Success(value=42)
        assert result1 == result2

    def test_success_with_different_values_are_not_equal(self):
        """Two Success instances with different values should not be equal."""
        result1 = Success(value=1)
        result2 = Success(value=2)
        assert result1 != result2

    def test_failure_with_same_error_are_equal(self):
        """Two Failure instances with same error should be equal."""
        result1 = Failure(error="error")
        result2 = Failure(error="error")
        assert result1 == result2

    def test_failure_with_different_errors_are_not_equal(self):
        """Two Failure instances with different errors should not be equal."""
        result1 = Failure(error="error1")
        result2 = Failure(error="error2")
        assert result1 != result2

    def test_success_not_equal_to_failure(self):
        """Success should not equal Failure even with same underlying value."""
        success_result = Success(value="value")
        failure_result = Failure(error="value")
        assert success_result != failure_result

    def test_success_with_none_value_equality(self):
        """Success with None values should be equal."""
        result1 = Success(value=None)
        result2 = Success(value=None)
        assert result1 == result2


class TestResultEdgeCases:
    """Tests for edge cases in Result types."""

    def test_success_with_zero_value(self):
        """Success should handle zero value correctly."""
        result = Success(value=0)
        assert result.value == 0
        assert result.is_success()
        assert result.unwrap() == 0

    def test_success_with_empty_string(self):
        """Success should handle empty string value."""
        result = Success(value="")
        assert result.value == ""
        assert result.unwrap() == ""

    def test_success_with_false_value(self):
        """Success should handle False value correctly."""
        result = Success(value=False)
        assert result.value is False
        assert result.is_success()
        assert result.unwrap() is False
        # Note: get_or_none returns the value, not None
        assert result.get_or_none() is False

    def test_failure_with_false_error(self):
        """Failure should handle False as error correctly."""
        result = Failure(error=False)
        assert result.error is False
        assert result.is_failure()
        assert result.get_error_or_none() is False

    def test_nested_result_like_structure(self):
        """Test handling of nested-like data structures."""
        nested_data = {"result": Success(value=42), "error": None}
        result = Success(value=nested_data)
        assert result.value["result"].value == 42

    def test_very_long_string_value(self):
        """Success should handle very long string values."""
        long_string = "x" * 10000
        result = Success(value=long_string)
        assert result.value == long_string
        assert len(result.unwrap()) == 10000

    def test_unicode_value(self):
        """Success should handle unicode values."""
        result = Success(value="Hello 世界 🌍")
        assert result.value == "Hello 世界 🌍"
        assert result.unwrap() == "Hello 世界 🌍"


class TestResultTypeAnnotations:
    """Tests to verify Result types work correctly with type hints."""

    def test_success_generic_type(self):
        """Success should work with generic type annotations."""
        result: Success[int] = Success(value=42)
        assert result.value == 42

    def test_failure_generic_type(self):
        """Failure should work with generic type annotations."""
        result: Failure[str] = Failure(error="error")
        assert result.error == "error"

    def test_result_union_type(self):
        """Result union type should accept both Success and Failure."""
        def get_result(is_success: bool) -> Success[int] | Failure[str]:
            if is_success:
                return Success(value=42)
            return Failure(error="failed")

        assert get_result(True).is_success()
        assert get_result(False).is_failure()