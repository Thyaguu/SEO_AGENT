"""Result type for representing success/failure outcomes.

This module provides a Result type similar to Rust's Result or Haskell's Either.
It enables explicit error handling without relying on exceptions for control flow.

Usage:
    def divide(a: float, b: float) -> Result[float, str]:
        if b == 0:
            return Result.failure("Division by zero")
        return Result.success(a / b)

    result = divide(10, 2)
    if result.is_success():
        print(result.value)  # 5.0
"""

from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True, slots=True)
class Success(Generic[T]):
    """Represents a successful outcome containing a value."""

    value: T

    def is_success(self) -> bool:
        """Return True for success."""
        return True

    def is_failure(self) -> bool:
        """Return False for success."""
        return False

    def get_or_none(self) -> T | None:
        """Return the value if success, None otherwise."""
        return self.value

    def get_error_or_none(self) -> None:
        """Return None for success."""
        return None

    def unwrap(self) -> T:
        """Return the value. Raises if failure."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Return the value or default if failure."""
        return self.value


@dataclass(frozen=True, slots=True)
class Failure(Generic[E]):
    """Represents a failed outcome containing an error."""

    error: E

    def is_success(self) -> bool:
        """Return False for failure."""
        return False

    def is_failure(self) -> bool:
        """Return True for failure."""
        return True

    def get_or_none(self) -> None:
        """Return None for failure."""
        return None

    def get_error_or_none(self) -> E | None:
        """Return the error if failure, None otherwise."""
        return self.error

    def unwrap(self) -> Any:
        """Raise ValueError with error message."""
        raise ValueError(f"Attempted to unwrap a Failure: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Return the default value for failure."""
        return default


# Type alias for Result
Result = Union[Success[T], Failure[E]]


def success(value: T) -> Success[T]:
    """Create a successful Result.

    Args:
        value: The success value.

    Returns:
        Success instance containing the value.
    """
    return Success(value=value)


def failure(error: E) -> Failure[E]:
    """Create a failed Result.

    Args:
        error: The error value.

    Returns:
        Failure instance containing the error.
    """
    return Failure(error=error)


def from_exception(error: Exception, error_msg: str | None = None) -> Failure[str]:
    """Create a Failure from an exception.

    Args:
        error: The exception to convert.
        error_msg: Optional custom error message.

    Returns:
        Failure containing the error message.
    """
    msg = error_msg or str(error)
    return Failure(error=msg)


def from_bool(value: bool, success_val: T, error_val: E) -> Result[T, E]:
    """Create Result from a boolean condition.

    Args:
        value: The condition to evaluate.
        success_val: Value to use on success.
        error_val: Value to use on failure.

    Returns:
        Success with success_val if True, Failure with error_val if False.
    """
    if value:
        return Success(value=success_val)
    return Failure(error=error_val)