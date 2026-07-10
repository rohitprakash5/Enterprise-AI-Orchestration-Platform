"""
LLM Connectors Package
========================
Auto-registers all LLM providers into the LLMRegistry on import.

Provider selection (EIO_ACTIVE_LLM env var):
  mock     — deterministic canned responses, zero dependencies  (default when no key)
  gpt_oss  — openai/gpt-oss-20b via HuggingFace (local GPU or HF Endpoint)
  openai   — OpenAI GPT-4o via API key           (set when key available)
  anthropic / granite / gemini / ollama — stubs, wire when needed

Embeddings: sentence-transformers/all-MiniLM-L6-v2 (CPU, real semantic similarity)
            used by mock, gpt_oss, and as fallback for openai offline mode.
"""

from eio.connectors.llm.gptoss_provider import GptOssProvider
from eio.connectors.llm.mock_provider import MockLLMProvider
from eio.connectors.llm.openai_provider import OpenAIProvider
from eio.connectors.llm.registry import LLMRegistry
from eio.connectors.llm.router import ModelRouter
from eio.connectors.llm.stubs import AnthropicProvider, GeminiProvider, GraniteProvider, OllamaProvider

LLMRegistry.register("openai")(OpenAIProvider)
LLMRegistry.register("mock")(MockLLMProvider)
LLMRegistry.register("gpt_oss")(GptOssProvider)
LLMRegistry.register("anthropic")(AnthropicProvider)
LLMRegistry.register("granite")(GraniteProvider)
LLMRegistry.register("gemini")(GeminiProvider)
LLMRegistry.register("ollama")(OllamaProvider)

__all__ = ["LLMRegistry", "ModelRouter", "OpenAIProvider", "MockLLMProvider", "GptOssProvider"]
