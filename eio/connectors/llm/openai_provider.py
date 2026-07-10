"""
OpenAI LLM Provider
=====================
Concrete implementation of LLMProvider for OpenAI (GPT-4o, GPT-3.5-turbo, etc.).
Controlled by OPENAI_API_KEY and EIO_ACTIVE_LLM=openai.
"""

from __future__ import annotations

import time
from typing import Any

from openai import OpenAI

from eio.connectors.llm.base import (
    EmbeddingResponse,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)
from eio.core.llm_pricing import estimate_cost


class OpenAIProvider(LLMProvider):
    """
    OpenAI GPT provider.
    Supports GPT-4o, GPT-4o-mini, GPT-4-turbo, GPT-3.5-turbo.
    """

    _DEFAULT_MODEL = "gpt-4o"
    _DEFAULT_EMBED_MODEL = "text-embedding-3-small"
    _AVAILABLE_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

    def __init__(self, api_key: str | None = None, default_model: str | None = None) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = default_model or self._DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return self._model

    @property
    def available_models(self) -> list[str]:
        return self._AVAILABLE_MODELS

    def complete(self, request: LLMRequest) -> LLMResponse:
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for msg in request.messages:
            messages.append({"role": msg.role.value, "content": msg.content})

        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=request.model or self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0
        model_used = response.model or request.model

        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=model_used,
            provider=self.provider_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=estimate_cost(model_used, input_tokens, output_tokens),
            latency_ms=round(latency_ms, 2),
            finish_reason=response.choices[0].finish_reason or "stop",
        )

    def embed(self, text: str, model: str | None = None) -> EmbeddingResponse:
        embed_model = model or self._DEFAULT_EMBED_MODEL
        start = time.perf_counter()
        response = self._client.embeddings.create(
            input=text,
            model=embed_model,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        return EmbeddingResponse(
            embedding=response.data[0].embedding,
            model=embed_model,
            provider=self.provider_name,
            input_tokens=input_tokens,
            cost_usd=estimate_cost(embed_model, input_tokens, 0),
        )

    def health_check(self) -> dict[str, Any]:
        try:
            self._client.models.list()
            return {"status": "ok", "provider": self.provider_name, "model": self._model}
        except Exception as exc:
            return {"status": "error", "provider": self.provider_name, "detail": str(exc)}
