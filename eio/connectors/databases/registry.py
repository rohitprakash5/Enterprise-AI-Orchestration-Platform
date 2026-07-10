"""
Database Connector Registry
============================
Auto-registration of all database connectors.
Connectors are selected at runtime via EIO_ACTIVE_DB env var.

Usage:
    from eio.connectors.databases.registry import ConnectorRegistry
    connector = ConnectorRegistry.get("sqlite", db_path="...")
"""

from __future__ import annotations

from typing import Any


class ConnectorRegistry:
    """
    Singleton registry mapping connector names to their factory callables.
    Register a connector with the @ConnectorRegistry.register("name") decorator.
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
        """
        Instantiate a connector by name.
        kwargs are forwarded to the connector's __init__.
        """
        key = name.lower()
        if key not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unknown database connector '{name}'. "
                f"Available: {available}. "
                f"Set EIO_ACTIVE_DB to one of the available connectors."
            )
        return cls._registry[key](**kwargs)

    @classmethod
    def available(cls) -> list[str]:
        """Return the list of registered connector names."""
        return list(cls._registry.keys())
