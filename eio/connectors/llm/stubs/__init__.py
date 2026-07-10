"""
LLM Provider Stubs
====================
Stub providers for all supported LLM vendors.
Each raises NotImplementedError with implementation instructions.
"""

from __future__ import annotations

from typing import Any

from eio.connectors.llm.base import (
    EmbeddingResponse,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)


def _not_implemented(provider: str, package: str, env_var: str) -> None:
    raise NotImplementedError(
        f"{provider} LLM provider is not yet implemented.\n"
        f"  1. Install the SDK: pip install {package}\n"
        f"  2. Set {env_var} in your .env file\n"
        f"  3. Implement the provider in eio/connectors/llm/{provider.lower()}_provider.py\n"
        f"     by subclassing LLMProvider and registering with @LLMRegistry.register('{provider.lower()}')"
    )


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider stub. Implement using anthropic SDK."""
    @property
    def provider_name(self) -> str: return "anthropic"
    @property
    def default_model(self) -> str: return "claude-3-5-sonnet"
    @property
    def available_models(self) -> list[str]: return ["claude-3-5-sonnet", "claude-3-haiku", "claude-3-opus"]
    def complete(self, request: LLMRequest) -> LLMResponse: _not_implemented("Anthropic", "anthropic", "ANTHROPIC_API_KEY")  # type: ignore
    def embed(self, text: str, model: str | None = None) -> EmbeddingResponse: _not_implemented("Anthropic", "anthropic", "ANTHROPIC_API_KEY")  # type: ignore
    def health_check(self) -> dict[str, Any]: return {"status": "stub", "provider": "anthropic"}


class GraniteProvider(LLMProvider):
    """IBM Granite via watsonx.ai provider stub. Implement using ibm-watsonx-ai SDK."""
    @property
    def provider_name(self) -> str: return "granite"
    @property
    def default_model(self) -> str: return "granite-13b-chat"
    @property
    def available_models(self) -> list[str]: return ["granite-13b-chat", "granite-34b-code"]
    def complete(self, request: LLMRequest) -> LLMResponse: _not_implemented("Granite", "ibm-watsonx-ai", "WATSONX_API_KEY")  # type: ignore
    def embed(self, text: str, model: str | None = None) -> EmbeddingResponse: _not_implemented("Granite", "ibm-watsonx-ai", "WATSONX_API_KEY")  # type: ignore
    def health_check(self) -> dict[str, Any]: return {"status": "stub", "provider": "granite"}


class GeminiProvider(LLMProvider):
    """Google Gemini provider stub. Implement using google-generativeai SDK."""
    @property
    def provider_name(self) -> str: return "gemini"
    @property
    def default_model(self) -> str: return "gemini-1.5-pro"
    @property
    def available_models(self) -> list[str]: return ["gemini-1.5-pro", "gemini-1.5-flash"]
    def complete(self, request: LLMRequest) -> LLMResponse: _not_implemented("Gemini", "google-generativeai", "GOOGLE_API_KEY")  # type: ignore
    def embed(self, text: str, model: str | None = None) -> EmbeddingResponse: _not_implemented("Gemini", "google-generativeai", "GOOGLE_API_KEY")  # type: ignore
    def health_check(self) -> dict[str, Any]: return {"status": "stub", "provider": "gemini"}


class OllamaProvider(LLMProvider):
    """Ollama (local) provider stub. Implement using ollama Python SDK or httpx."""
    @property
    def provider_name(self) -> str: return "ollama"
    @property
    def default_model(self) -> str: return "llama3"
    @property
    def available_models(self) -> list[str]: return ["llama3", "llama3:8b", "mistral", "codellama"]
    def complete(self, request: LLMRequest) -> LLMResponse: _not_implemented("Ollama", "ollama", "OLLAMA_BASE_URL")  # type: ignore
    def embed(self, text: str, model: str | None = None) -> EmbeddingResponse: _not_implemented("Ollama", "ollama", "OLLAMA_BASE_URL")  # type: ignore
    def health_check(self) -> dict[str, Any]: return {"status": "stub", "provider": "ollama"}
