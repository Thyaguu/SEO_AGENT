"""Unit tests for seo_agent.core.types."""

import asyncio
from typing import Any, Awaitable, Callable, Dict

import pytest

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


# =============================================================================
# TestTypeAliases
# =============================================================================


class TestTypeAliases:
    """Tests for type alias definitions."""

    def test_validator_fn_is_callable(self):
        """ValidatorFn is a callable type."""
        def validator(value: Any) -> bool:
            return isinstance(value, str)
        assert callable(validator)
        assert validator("test") is True
        assert validator(123) is False

    def test_async_validator_fn_is_coroutine_function(self):
        """AsyncValidatorFn is a coroutine function."""
        async def async_validator(value: Any) -> bool:
            return isinstance(value, str)
        assert asyncio.iscoroutinefunction(async_validator)

    def test_cleanup_fn_is_callable_returning_none(self):
        """CleanupFn is a callable that returns None."""
        def cleanup() -> None:
            pass
        assert callable(cleanup)
        result = cleanup()
        assert result is None

    def test_async_cleanup_fn_is_coroutine_returning_none(self):
        """AsyncCleanupFn is a coroutine that returns None."""
        async def async_cleanup() -> None:
            pass
        assert asyncio.iscoroutinefunction(async_cleanup)

    def test_factory_fn_is_callable(self):
        """FactoryFn is a callable."""
        def factory() -> str:
            return "created"
        assert callable(factory)
        assert factory() == "created"

    def test_async_factory_fn_is_coroutine_function(self):
        """AsyncFactoryFn is a coroutine function."""
        async def async_factory() -> str:
            return "created"
        assert asyncio.iscoroutinefunction(async_factory)

    def test_str_dict_is_dict(self):
        """StrDict is a dict type."""
        d: StrDict = {"key": "value", "number": 42}
        assert isinstance(d, dict)
        assert d["key"] == "value"

    def test_immutable_dict_is_dict(self):
        """ImmutableDict is a dict type."""
        d: ImmutableDict = {"immutable": True}
        assert isinstance(d, dict)
        assert d["immutable"] is True


# =============================================================================
# TestValidatorFn
# =============================================================================


class TestValidatorFn:
    """Tests for ValidatorFn type alias usage."""

    def test_validator_returns_bool(self):
        """Validator functions return boolean."""
        def is_positive(value: Any) -> bool:
            return isinstance(value, (int, float)) and value > 0

        assert is_positive(5) is True
        assert is_positive(-1) is False
        assert is_positive("string") is False

    def test_validator_with_complex_logic(self):
        """Validators can have complex logic."""
        def is_valid_email(value: Any) -> bool:
            if not isinstance(value, str):
                return False
            return "@" in value and "." in value.split("@")[-1]

        assert is_valid_email("test@example.com") is True
        assert is_valid_email("invalid") is False
        assert is_valid_email(123) is False

    def test_validator_chaining(self):
        """Validators can be composed."""
        def is_string(value: Any) -> bool:
            return isinstance(value, str)

        def is_non_empty(value: Any) -> bool:
            return bool(value)

        def is_valid_username(value: Any) -> bool:
            return is_string(value) and is_non_empty(value)

        assert is_valid_username("admin") is True
        assert is_valid_username("") is False
        assert is_valid_username(123) is False


# =============================================================================
# TestAsyncValidatorFn
# =============================================================================


class TestAsyncValidatorFn:
    """Tests for AsyncValidatorFn type alias usage."""

    def test_async_validator_returns_awaitable(self):
        """Async validators return awaitable."""
        async def validate(value: Any) -> bool:
            return isinstance(value, str)

        result = validate("test")
        assert asyncio.iscoroutine(result)

    @pytest.mark.asyncio
    async def test_async_validator_awaited(self):
        """Async validators can be awaited."""
        async def validate(value: Any) -> bool:
            await asyncio.sleep(0)  # Simulate async operation
            return isinstance(value, str)

        result = await validate("test")
        assert result is True

    @pytest.mark.asyncio
    async def test_async_validator_with_db_check(self):
        """Async validators can perform async operations."""
        async def validate_exists(value: Any) -> bool:
            # Simulate async check (e.g., database lookup)
            await asyncio.sleep(0)
            return value in {"allowed1", "allowed2"}

        assert await validate_exists("allowed1") is True
        assert await validate_exists("not_allowed") is False


# =============================================================================
# TestCleanupFn
# =============================================================================


class TestCleanupFn:
    """Tests for CleanupFn type alias usage."""

    def test_cleanup_fn_executes(self):
        """Cleanup functions execute without error."""
        executed = False

        def cleanup() -> None:
            nonlocal executed
            executed = True

        cleanup()
        assert executed is True

    def test_cleanup_fn_can_modify_state(self):
        """Cleanup functions can modify external state."""
        state = {"open": True}

        def cleanup() -> None:
            state["open"] = False

        cleanup()
        assert state["open"] is False

    def test_cleanup_fn_multiple_cleanups(self):
        """Multiple cleanup functions can be chained."""
        results = []

        def cleanup1() -> None:
            results.append("cleanup1")

        def cleanup2() -> None:
            results.append("cleanup2")

        cleanup1()
        cleanup2()
        assert results == ["cleanup1", "cleanup2"]


# =============================================================================
# TestAsyncCleanupFn
# =============================================================================


class TestAsyncCleanupFn:
    """Tests for AsyncCleanupFn type alias usage."""

    def test_async_cleanup_fn_returns_coroutine(self):
        """Async cleanup functions return coroutines."""
        async def cleanup() -> None:
            pass

        result = cleanup()
        assert asyncio.iscoroutine(result)
        # Cleanup the coroutine to avoid warning
        result.close()

    @pytest.mark.asyncio
    async def test_async_cleanup_fn_awaits(self):
        """Async cleanup functions can be awaited."""
        executed = False

        async def cleanup() -> None:
            nonlocal executed
            await asyncio.sleep(0)
            executed = True

        await cleanup()
        assert executed is True

    @pytest.mark.asyncio
    async def test_async_cleanup_fn_can_close_resources(self):
        """Async cleanup can close async resources."""
        connections_closed = []

        async def close_connection(name: str) -> None:
            await asyncio.sleep(0)
            connections_closed.append(name)

        await close_connection("conn1")
        await close_connection("conn2")
        assert connections_closed == ["conn1", "conn2"]


# =============================================================================
# TestFactoryFn
# =============================================================================


class TestFactoryFn:
    """Tests for FactoryFn type alias usage."""

    def test_factory_creates_instances(self):
        """Factory functions create instances."""
        class Service:
            def __init__(self, config: str):
                self.config = config

        def create_service() -> Service:
            return Service("default")

        service = create_service()
        assert isinstance(service, Service)
        assert service.config == "default"

    def test_factory_with_parameters(self):
        """Factory functions can accept parameters."""
        def create_greeting(name: str) -> str:
            return f"Hello, {name}!"

        result = create_greeting("World")
        assert result == "Hello, World!"

    def test_factory_returns_typed_value(self):
        """Factory functions return correctly typed values."""
        def create_list() -> list:
            return [1, 2, 3]

        result = create_list()
        assert isinstance(result, list)
        assert result == [1, 2, 3]


# =============================================================================
# TestAsyncFactoryFn
# =============================================================================


class TestAsyncFactoryFn:
    """Tests for AsyncFactoryFn type alias usage."""

    def test_async_factory_returns_coroutine(self):
        """Async factory functions return coroutines."""
        async def create() -> str:
            return "result"

        result = create()
        assert asyncio.iscoroutine(result)
        result.close()

    @pytest.mark.asyncio
    async def test_async_factory_creates_async_resource(self):
        """Async factories can create async resources."""
        class AsyncResource:
            def __init__(self, name: str):
                self.name = name

        async def create_resource(name: str) -> AsyncResource:
            await asyncio.sleep(0)
            return AsyncResource(name)

        resource = await create_resource("test")
        assert isinstance(resource, AsyncResource)
        assert resource.name == "test"

    @pytest.mark.asyncio
    async def test_async_factory_with_db_connection(self):
        """Async factories can create database connections."""
        async def create_connection(url: str) -> dict:
            await asyncio.sleep(0)
            return {"url": url, "connected": True}

        conn = await create_connection("postgresql://localhost")
        assert conn["connected"] is True


# =============================================================================
# TestStrDict
# =============================================================================


class TestStrDict:
    """Tests for StrDict type alias usage."""

    def test_str_dict_accepts_string_keys(self):
        """StrDict accepts string keys."""
        d: StrDict = {"key": "value"}
        assert "key" in d

    def test_str_dict_accepts_any_values(self):
        """StrDict accepts any value type."""
        d: StrDict = {
            "string": "value",
            "number": 42,
            "list": [1, 2, 3],
            "dict": {"nested": True},
            "none": None,
        }
        assert d["string"] == "value"
        assert d["number"] == 42
        assert d["list"] == [1, 2, 3]
        assert d["dict"] == {"nested": True}
        assert d["none"] is None

    def test_str_dict_can_be_empty(self):
        """StrDict can be empty."""
        d: StrDict = {}
        assert len(d) == 0

    def test_str_dict_supports_dict_operations(self):
        """StrDict supports standard dict operations."""
        d: StrDict = {"a": 1, "b": 2}
        d["c"] = 3
        assert d == {"a": 1, "b": 2, "c": 3}
        del d["a"]
        assert d == {"b": 2, "c": 3}


# =============================================================================
# TestImmutableDict
# =============================================================================


class TestImmutableDict:
    """Tests for ImmutableDict type alias usage."""

    def test_immutable_dict_is_dict_type(self):
        """ImmutableDict is a dict type."""
        d: ImmutableDict = {"key": "value"}
        assert isinstance(d, dict)

    def test_immutable_dict_accepts_string_keys(self):
        """ImmutableDict accepts string keys."""
        d: ImmutableDict = {"key": "value"}
        assert "key" in d

    def test_immutable_dict_accepts_any_values(self):
        """ImmutableDict accepts any value type."""
        d: ImmutableDict = {
            "string": "value",
            "number": 42,
            "bool": True,
        }
        assert d["string"] == "value"
        assert d["number"] == 42
        assert d["bool"] is True

    def test_immutable_dict_can_be_empty(self):
        """ImmutableDict can be empty."""
        d: ImmutableDict = {}
        assert len(d) == 0


# =============================================================================
# TestTypeCompatibility
# =============================================================================


class TestTypeCompatibility:
    """Tests for type alias compatibility."""

    def test_validator_fn_assignable_to_callable(self):
        """ValidatorFn is assignable to Callable."""
        def validator(value: Any) -> bool:
            return True

        fn: Callable[[Any], bool] = validator
        assert fn("test") is True

    def test_str_dict_assignable_to_dict(self):
        """StrDict is assignable to dict."""
        d: StrDict = {"key": "value"}
        base_dict: Dict[str, Any] = d
        assert base_dict == {"key": "value"}

    def test_immutable_dict_assignable_to_dict(self):
        """ImmutableDict is assignable to dict."""
        d: ImmutableDict = {"key": "value"}
        base_dict: Dict[str, Any] = d
        assert base_dict == {"key": "value"}

    def test_factory_fn_return_type(self):
        """FactoryFn can return various types."""
        def create_int() -> int:
            return 42

        def create_str() -> str:
            return "hello"

        fn_int: FactoryFn[int] = create_int
        fn_str: FactoryFn[str] = create_str

        assert fn_int() == 42
        assert fn_str() == "hello"


# =============================================================================
# TestAsyncPatterns
# =============================================================================


class TestAsyncPatterns:
    """Tests for async type alias patterns."""

    @pytest.mark.asyncio
    async def test_async_validator_in_async_context(self):
        """AsyncValidatorFn works in async context."""
        async def validate(value: Any) -> bool:
            await asyncio.sleep(0)
            return isinstance(value, str)

        validator: AsyncValidatorFn = validate
        result = await validator("test")
        assert result is True

    @pytest.mark.asyncio
    async def test_async_factory_in_async_context(self):
        """AsyncFactoryFn works in async context."""
        async def create() -> dict:
            await asyncio.sleep(0)
            return {"created": True}

        factory: AsyncFactoryFn[dict] = create
        result = await factory()
        assert result == {"created": True}

    @pytest.mark.asyncio
    async def test_async_cleanup_in_async_context(self):
        """AsyncCleanupFn works in async context."""
        cleaned = False

        async def cleanup() -> None:
            nonlocal cleaned
            await asyncio.sleep(0)
            cleaned = True

        cleanup_fn: AsyncCleanupFn = cleanup
        await cleanup_fn()
        assert cleaned is True