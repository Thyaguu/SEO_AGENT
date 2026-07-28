"""Type definitions and type aliases for the SEO Agent.

This module provides shared type definitions used across the project.
Types here are infrastructure-level and do not contain business logic.
"""

from typing import Any, Callable, Coroutine, TypeVar

# Generic type variable for callable return types
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
U = TypeVar("U")

# Type alias for synchronous validators
ValidatorFn = Callable[[Any], bool]

# Type alias for asynchronous validators
AsyncValidatorFn = Callable[[Any], Coroutine[Any, Any, bool]]

# Type alias for cleanup functions
CleanupFn = Callable[[], None]

# Type alias for async cleanup functions
AsyncCleanupFn = Callable[[], Coroutine[Any, Any, None]]

# Type alias for any callable that returns T
FactoryFn = Callable[..., T]

# Type alias for async factory functions
AsyncFactoryFn = Callable[..., Coroutine[Any, Any, T]]

# Type alias for dictionary with string keys
StrDict = dict[str, Any]

# Type alias for immutable dictionary
ImmutableDict = dict[str, Any]