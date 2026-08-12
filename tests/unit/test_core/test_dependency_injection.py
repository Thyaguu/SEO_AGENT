"""Unit tests for seo_agent.core.dependency_injection."""

import pytest

from seo_agent.core.dependency_injection import (
    Container,
    get_container,
    inject,
    reset_container,
    set_container,
)
from seo_agent.core.exceptions import DependencyError


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def container() -> Container:
    """Create a fresh container for each test."""
    return Container()


@pytest.fixture
def reset_global_container():
    """Reset global container before and after test."""
    reset_container()
    yield
    reset_container()


@pytest.fixture
def sample_service():
    """Create a sample service class."""
    class SampleService:
        def __init__(self, value: str = "default"):
            self.value = value

        def get_value(self) -> str:
            return self.value
    return SampleService


@pytest.fixture
def another_service():
    """Create another sample service class."""
    class AnotherService:
        def __init__(self):
            self.name = "another"

        def get_name(self) -> str:
            return self.name
    return AnotherService


# =============================================================================
# TestContainer
# =============================================================================


class TestContainer:
    """Tests for Container class."""

    def test_init_creates_empty_container(self, container: Container):
        """Container initializes with empty registrations."""
        assert container._factories == {}
        assert container._singletons == {}
        assert container._singleton_registrations == set()

    def test_register_with_instance_stores_singleton(
        self, container: Container, sample_service
    ):
        """Registering an instance stores it as a singleton."""
        instance = sample_service()
        container.register(sample_service, instance)
        assert container.is_registered(sample_service)
        assert sample_service in container._singletons

    def test_register_with_factory_stores_factory(
        self, container: Container, sample_service
    ):
        """Registering a callable stores it as a factory."""
        container.register(sample_service, sample_service)
        assert container.is_registered(sample_service)
        assert sample_service in container._factories

    def test_register_singleton_true_adds_to_singleton_registrations(
        self, container: Container, sample_service
    ):
        """Registering with singleton=True marks it for singleton behavior."""
        container.register(sample_service, sample_service, singleton=True)
        assert sample_service in container._singleton_registrations

    def test_register_singleton_false_does_not_add_to_singleton_registrations(
        self, container: Container, sample_service
    ):
        """Registering with singleton=False does not mark it as singleton."""
        container.register(sample_service, sample_service, singleton=False)
        assert sample_service not in container._singleton_registrations

    def test_register_duplicate_raises_error(self, container: Container, sample_service):
        """Registering the same interface twice raises DependencyError."""
        container.register(sample_service, sample_service)
        with pytest.raises(DependencyError) as exc_info:
            container.register(sample_service, sample_service)
        assert sample_service.__name__ in str(exc_info.value)

    def test_register_singleton_method(self, container: Container, sample_service):
        """register_singleton stores instance as singleton."""
        instance = sample_service("test")
        container.register_singleton(sample_service, instance)
        assert container.is_registered(sample_service)
        assert sample_service in container._singletons

    def test_register_transient_method(self, container: Container, sample_service):
        """register_transient stores factory as non-singleton."""
        container.register_transient(sample_service, sample_service)
        assert container.is_registered(sample_service)
        assert sample_service in container._factories
        assert sample_service not in container._singleton_registrations

    def test_resolve_returns_singleton_instance(
        self, container: Container, sample_service
    ):
        """Resolving a singleton returns the same instance each time."""
        instance = sample_service()
        container.register(sample_service, instance)
        resolved1 = container.resolve(sample_service)
        resolved2 = container.resolve(sample_service)
        assert resolved1 is resolved2
        assert resolved1 is instance

    def test_resolve_returns_new_instance_for_transient(
        self, container: Container, sample_service
    ):
        """Resolving a transient returns a new instance each time."""
        container.register(sample_service, sample_service, singleton=False)
        resolved1 = container.resolve(sample_service)
        resolved2 = container.resolve(sample_service)
        assert resolved1 is not resolved2
        assert isinstance(resolved1, sample_service)
        assert isinstance(resolved2, sample_service)

    def test_resolve_calls_factory(self, container: Container, sample_service):
        """Resolving a factory calls it to create instance."""
        container.register(sample_service, sample_service)
        resolved = container.resolve(sample_service)
        assert isinstance(resolved, sample_service)

    def test_resolve_unregistered_raises_error(self, container: Container):
        """Resolving an unregistered interface raises DependencyError."""
        class UnknownService:
            pass
        with pytest.raises(DependencyError) as exc_info:
            container.resolve(UnknownService)
        assert "UnknownService" in str(exc_info.value)

    def test_is_registered_returns_true_for_registered(
        self, container: Container, sample_service
    ):
        """is_registered returns True for registered interfaces."""
        container.register(sample_service, sample_service)
        assert container.is_registered(sample_service) is True

    def test_is_registered_returns_false_for_unregistered(
        self, container: Container
    ):
        """is_registered returns False for unregistered interfaces."""
        class UnregisteredService:
            pass
        assert container.is_registered(UnregisteredService) is False

    def test_clear_removes_all_registrations(self, container: Container, sample_service):
        """clear() removes all registered services."""
        container.register(sample_service, sample_service)
        container.clear()
        assert not container.is_registered(sample_service)
        assert container._factories == {}
        assert container._singletons == {}
        assert container._singleton_registrations == set()


# =============================================================================
# TestGlobalContainer
# =============================================================================


class TestGlobalContainer:
    """Tests for global container functions."""

    def test_get_container_creates_new_container(self, reset_global_container):
        """get_container returns a new container on first call."""
        container = get_container()
        assert isinstance(container, Container)

    def test_get_container_returns_same_instance(self, reset_global_container):
        """get_container returns the same instance on subsequent calls."""
        container1 = get_container()
        container2 = get_container()
        assert container1 is container2

    def test_set_container_replaces_global_container(
        self, reset_global_container, sample_service
    ):
        """set_container replaces the global container."""
        original = get_container()
        new_container = Container()
        new_container.register(sample_service, sample_service)
        set_container(new_container)
        assert get_container() is new_container
        assert get_container() is not original

    def test_reset_container_clears_global_container(
        self, reset_global_container, sample_service
    ):
        """reset_container clears and resets the global container."""
        container = get_container()
        container.register(sample_service, sample_service)
        reset_container()
        new_container = get_container()
        assert new_container is not container
        assert not new_container.is_registered(sample_service)


# =============================================================================
# TestInjectDecorator
# =============================================================================


class TestInjectDecorator:
    """Tests for the inject decorator."""

    def test_inject_decorator_resolves_dependencies(
        self, container: Container, sample_service
    ):
        """inject decorator resolves dependencies from container."""
        instance = sample_service("injected")
        container.register(sample_service, instance)

        @inject(container)
        def my_function(svc: sample_service) -> str:
            return svc.get_value()

        result = my_function()
        assert result == "injected"

    def test_inject_decorator_with_multiple_dependencies(
        self, container: Container, sample_service, another_service
    ):
        """inject decorator resolves multiple dependencies."""
        container.register(sample_service, sample_service("first"))
        container.register(another_service, another_service())

        @inject(container)
        def my_function(svc1: sample_service, svc2: another_service) -> tuple:
            return (svc1.get_value(), svc2.get_name())

        result = my_function()
        assert result == ("first", "another")

    def test_inject_decorator_preserves_function_metadata(
        self, container: Container
    ):
        """inject decorator preserves function name and docstring."""
        @inject(container)
        def my_function() -> None:
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_inject_decorator_with_kwargs(
        self, container: Container, sample_service
    ):
        """inject decorator passes through kwargs."""
        container.register(sample_service, sample_service("injected"))

        @inject(container)
        def my_function(svc: sample_service, extra: str = "default") -> tuple:
            return (svc.get_value(), extra)

        result = my_function(extra="override")
        assert result == ("injected", "override")

    def test_inject_decorator_with_args(
        self, container: Container, sample_service
    ):
        """inject decorator passes through positional args as keyword args."""
        container.register(sample_service, sample_service("injected"))

        @inject(container)
        def my_function(svc: sample_service, extra: str = "default") -> tuple:
            return (svc.get_value(), extra)

        result = my_function(extra="positional")
        assert result == ("injected", "positional")


# =============================================================================
# TestDependencyError
# =============================================================================


class TestDependencyError:
    """Tests for DependencyError in DI context."""

    def test_dependency_error_message(self):
        """DependencyError includes interface name in message."""
        error = DependencyError("Interface Config is already registered")
        assert "Config" in str(error)
        assert "already registered" in str(error)

    def test_dependency_error_can_be_raised_and_caught(self):
        """DependencyError can be raised and caught properly."""
        with pytest.raises(DependencyError):
            raise DependencyError("test error")