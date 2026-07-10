"""
Storage Connector Registry
============================
Auto-registration of all storage connectors.
Connectors are selected at runtime via EIO_ACTIVE_STORAGE env var.
"""

from __future__ import annotations

from typing import Any


class StorageRegistry:
    """
    Singleton registry mapping connector names to their factory callables.
    Register a connector with the @StorageRegistry.register("name") decorator.
    """

    _registry: dict[str, type] = {}

    @classmethod
    def register(cls, name: str):
        """Class decorator to register a connector under a string key."""
        def decorator(connector_class: type) -> type:
            cls._registry[name.lower()] = connector_class
            return connector_class
        return decorator

    @classmethod
    def get(cls, name: str, **kwargs: Any):
        """Instantiate a connector by name, forwarding kwargs to __init__."""
        key = name.lower()
        if key not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unknown storage connector '{name}'. "
                f"Available: {available}. "
                f"Set EIO_ACTIVE_STORAGE to one of the available connectors."
            )
        return cls._registry[key](**kwargs)

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._registry.keys())
