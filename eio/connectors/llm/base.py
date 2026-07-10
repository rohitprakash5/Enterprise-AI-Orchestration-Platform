"""
LLM Provider Abstraction Layer
================================
All LLM providers must implement the LLMProvider ABC.
Switching providers requires only a configuration change (EIO_ACTIVE_LLM).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    role: MessageRole
    content: str


class LLMRequest(BaseModel):
    """Unified request object for all LLM providers."""

    messages: list[Message]
    model: str
    temperature: float = 0.0
    max_tokens: int = 2048
    system_prompt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Unified response object returned by all LLM providers."""

    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddingResponse(BaseModel):
    """Response from an embedding call."""

    embedding: list[float]
    model: str
    provider: str
    input_tokens: int = 0
    cost_usd: float = 0.0


class RoutingContext(BaseModel):
    """
    Populated by the PlannerAgent. Used by ModelRouter to select the
    most appropriate model/provider combination.
    """

    user_query: str
    complexity: str = "medium"          # low | medium | high
    sql_needed: bool = False
    rag_needed: bool = False
    multi_agent: bool = False
    estimated_tokens: int = 1000
    requires_code_gen: bool = False
    sensitive_data: bool = False
    preferred_provider: str | None = None


class RoutingDecision(BaseModel):
    """The model routing decision with full justification."""

    provider: str
    model: str
    reason: str
    estimated_cost_usd: float = 0.0
    estimated_tokens: int = 0
    complexity: str = "medium"
    policy_applied: list[str] = Field(default_factory=list)


class LLMProvider(ABC):
    """
    Abstract base class for all EIO LLM providers.

    Concrete implementations: OpenAIProvider, AnthropicProvider, etc.
    All providers are registered in LLMRegistry and selected via
    the EIO_ACTIVE_LLM environment variable.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short identifier string: 'openai', 'anthropic', 'granite', etc."""

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model name used when not overridden."""

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """List of model names this provider supports."""

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Execute a chat completion request."""

    @abstractmethod
    def embed(self, text: str, model: str | None = None) -> EmbeddingResponse:
        """Generate an embedding vector for the given text."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return {"status": "ok"|"error", "provider": str, "model": str}."""
