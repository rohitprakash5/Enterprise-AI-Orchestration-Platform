"""
LLM Provider Registry
======================
Auto-registration of all LLM providers.
Providers are selected at runtime via EIO_ACTIVE_LLM env var.
"""

from __future__ import annotations

from typing import Any


class LLMRegistry:
    """
    Singleton registry mapping provider names to their factory callables.
    Register a provider with the @LLMRegistry.register("name") decorator.
    """

    _registry: dict[str, type] = {}

    @classmethod
    def register(cls, name: str):
        """Class decorator to register a provider under a string key."""
        def decorator(provider_class: type) -> type:
            cls._registry[name.lower()] = provider_class
            return provider_class
        return decorator

    @classmethod
    def get(cls, name: str, **kwargs: Any):
        """Instantiate a provider by name, forwarding kwargs to __init__."""
        key = name.lower()
        if key not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unknown LLM provider '{name}'. "
                f"Available: {available}. "
                f"Set EIO_ACTIVE_LLM to one of the available providers."
            )
        return cls._registry[key](**kwargs)

    @classmethod
    def available(cls) -> list[str]:
        return list(cls._registry.keys())
