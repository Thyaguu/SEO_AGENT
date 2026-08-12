"""Dependency injection container for the SEO Agent.

This module provides a simple dependency injection container that manages
service registration and resolution. It follows the principle of dependency
inversion by allowing dependencies to be injected rather than created directly.

Usage:
    from seo_agent.core.dependency_injection import Container, inject

    # Create and configure container
    container = Container()
    container.register(Config, config_instance)
    container.register(Logger, logger_instance)

    # Use decorator for injection
    @inject(container)
    def my_function(config: Config, logger: Logger) -> None:
        logger.info("message")

    # Or resolve manually
    config = container.resolve(Config)
"""

from typing import Any, Callable, TypeVar

from seo_agent.core.exceptions import DependencyError

T = TypeVar("T")


class Container:
    """Simple dependency injection container.

    This container manages service registration and resolution.
    It supports singleton and transient registration modes.
    """

    def __init__(self) -> None:
        """Initialize an empty container."""
        self._factories: dict[type, Callable[[], Any]] = {}
        self._singletons: dict[type, Any] = {}
        self._singleton_registrations: set[type] = set()

    def register(
        self,
        interface: type[T],
        factory: Callable[[], T] | T,
        singleton: bool = True,
    ) -> None:
        """Register a service with the container.

        Args:
            interface: The type/interface to register.
            factory: Either a factory function or an instance.
            singleton: If True, return the same instance on each resolve.

        Raises:
            DependencyError: If interface is already registered.
        """
        if interface in self._factories or interface in self._singletons:
            raise DependencyError(
                f"Interface {interface.__name__} is already registered"
            )

        if callable(factory):
            self._factories[interface] = factory
        else:
            self._singletons[interface] = factory

        if singleton:
            self._singleton_registrations.add(interface)

    def register_singleton(self, interface: type[T], instance: T) -> None:
        """Register a singleton instance.

        Args:
            interface: The type/interface to register.
            instance: The singleton instance.
        """
        self.register(interface, instance, singleton=True)

    def register_transient(self, interface: type[T], factory: Callable[[], T]) -> None:
        """Register a transient factory.

        Args:
            interface: The type/interface to register.
            factory: Factory function to create instances.
        """
        self.register(interface, factory, singleton=False)

    def resolve(self, interface: type[T]) -> T:
        """Resolve a service from the container.

        Args:
            interface: The type to resolve.

        Returns:
            The resolved service instance.

        Raises:
            DependencyError: If the interface is not registered.
        """
        # Check for singleton instance
        if interface in self._singletons:
            return self._singletons[interface]

        # Check for factory
        if interface in self._factories:
            factory = self._factories[interface]
            instance = factory()

            # If singleton, cache the instance
            if interface in self._singleton_registrations:
                self._singletons[interface] = instance

            return instance

        raise DependencyError(f"Interface {interface.__name__} is not registered")

    def is_registered(self, interface: type) -> bool:
        """Check if an interface is registered.

        Args:
            interface: The type to check.

        Returns:
            True if registered, False otherwise.
        """
        return interface in self._factories or interface in self._singletons

    def clear(self) -> None:
        """Clear all registrations.

        This is primarily useful for testing.
        """
        self._factories.clear()
        self._singletons.clear()
        self._singleton_registrations.clear()


# Global container instance
_container: Container | None = None


def get_container() -> Container:
    """Get the global container instance.

    Returns:
        The global Container instance.
    """
    global _container
    if _container is None:
        _container = Container()
    return _container


def set_container(container: Container) -> None:
    """Set the global container instance.

    Args:
        container: The container to use as global instance.
    """
    global _container
    _container = container


def reset_container() -> None:
    """Reset the global container.

    This is primarily useful for testing.
    """
    global _container
    if _container is not None:
        _container.clear()
    _container = None


# Decorator for automatic injection
F = TypeVar("F", bound=Callable[..., Any])


def inject(container: Container) -> Callable[[F], F]:
    """Decorator to inject dependencies into a function.

    Args:
        container: The container to use for resolution.

    Returns:
        Decorator function.

    Example:
        @inject(get_container())
        def my_service(config: Config, logger: Logger) -> None:
            pass
    """
    def decorator(func: F) -> F:
        import functools
        import inspect

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            sig = inspect.signature(func)
            resolved_kwargs = dict(kwargs)

            # Map positional args to parameter names so we don't inject over them
            param_names = list(sig.parameters.keys())
            positional_names = set(param_names[: len(args)])

            for param_name, param in sig.parameters.items():
                if param_name in resolved_kwargs or param_name in positional_names:
                    continue
                if param.annotation != inspect.Parameter.empty:
                    try:
                        resolved_kwargs[param_name] = container.resolve(param.annotation)
                    except DependencyError:
                        continue  # Skip if not registered

            return func(*args, **resolved_kwargs)

        return wrapper  # type: ignore
    return decorator