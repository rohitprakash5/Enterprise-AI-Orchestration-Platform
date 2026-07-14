"""
IBM ICA (Intelligent Client Advisor) LLM Provider
====================================================
Connects to the IBM ICA nextgen-beta API which exposes pre-built agents
via an OpenAI-compatible /agents/chat/completions endpoint.

Each ICA agent is identified by its UUID (``agent_id``). The provider
wraps the OpenAI-compatible chat completions call so the rest of the
EIO platform can use any ICA agent transparently.

Configuration (set in .env):
    EIO_ACTIVE_LLM=ica
    ICA_API_KEY=<your Bearer token>
    ICA_BASE_URL=https://api.nextgen-beta.ica.ibm.com/ica/v1
    ICA_DEFAULT_AGENT_ID=<agent UUID to use as default>

To target a specific agent at runtime, set ``metadata["ica_agent_id"]``
on the LLMRequest, or pass the agent UUID as the ``model`` field directly.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from eio.connectors.llm.base import (
    EmbeddingResponse,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)
from eio.core.llm_pricing import estimate_cost

# ---------------------------------------------------------------------------
# Agent catalogue extracted from GET /agents/models (2025-06-04)
# key = agent UUID, value = (display_name, base_model_id)
# ---------------------------------------------------------------------------
# Last synced: GET /agents  (2025-07 live response — 37 agents)
# key = agent UUID, value = (display_name_exact_from_api, base_model_id)
ICA_AGENT_CATALOGUE: dict[str, tuple[str, str]] = {
    "02e9b2bd-acd8-4001-b440-38398589ae8a": ("PlantUML diagram creator",                                                          "meta-llama/llama-4-maverick-17b-128e-instruct-fp8"),
    "fb668f5d-f521-4222-8f4f-b3322be6bd43": ("Image Generator",                                                                   "gpt-5.1-chat-gus"),
    "92ab6124-60cd-42a6-9d62-d7ea413f2b6e": ("Process Flow Diagram Agent",                                                        "gpt-5.1-chat-gus"),
    "d7ac3864-09a7-4fe1-9828-0904e4ef9f58": ("Prompt Generator",                                                                  "gpt-5.1-chat-gus"),
    "1bf8d13e-d252-485a-a5dd-8bfba9c60a92": ("Agent Translate.",                                                                  "ibm/granite-4-h-small"),
    "33cda11d-184b-414e-9050-e12f184e245a": ("Analyze Logs and Identify Errors and Recommend Solutions",                          "claude-sonnet-3-7"),
    "09398556-663a-447a-9c68-603fdaa7b83f": ("Language translator agent",                                                         "gpt-5.1-chat-gus"),
    "e7890fb8-d38b-4b1a-a068-5bf195cb37ac": ("BASISAssistant",                                                                    "claude-sonnet-3-7"),
    "d464de5e-01b5-461a-94df-d6d0e34a3cfe": ("Internet Researcher",                                                               "gpt-5.1-chat-gus"),
    "1b473159-4357-4300-beea-420fcd2e95bf": ("Excel Builder",                                                                     "gpt-5.1-chat-gus"),
    "4a387cdb-0c48-45c4-952c-103f7e78d819": ("Blog Creator",                                                                      "meta-llama/llama-4-maverick-17b-128e-instruct-fp8"),
    "70852bb7-7386-4a54-9e31-2af43183f3dd": ("Market Research Agent",                                                             "gpt-5.1-chat-gus"),
    "8a9c8368-8057-4c76-8e83-11c9dff8c1f7": ("Generate User Persona",                                                             "ibm/granite-4-h-small"),
    "33980371-b340-4b45-8def-1298054c718d": ("Internet Fact Checker",                                                             "meta-llama/llama-4-maverick-17b-128e-instruct-fp8"),
    "b7702938-10ed-45a6-972d-53720a9121e2": ("Image Generator 2.0",                                                               "gemini-2.5-flash"),
    "a9bb5fb0-9564-4715-9166-9065da375766": ("AI Governance in Action A02: Strategic Alignment Agent",                            "claude-sonnet-4-5"),
    "790b01dc-c053-470a-9b08-c50bdbf7cb76": ("Generate Interview Questionnaire (Agent)",                                          "gpt-5.1-chat-gus"),
    "59354143-dd30-4f27-95d7-a4f800b6b8ef": ("Estimate User Story Complexity (Agent)",                                            "gpt-5.1-chat-gus"),
    "eaa58f34-80c5-4d32-bc87-45f15ccbc6bc": ("AI Governance in Action A05: Layers of Effect Assistant",                          "claude-sonnet-4-5"),
    "322c1369-81b3-460b-bd6a-af06f49a0d1a": ("AI Governance in Action A01: Backstory Generation",                                "claude-sonnet-4-5"),
    "3cf5e811-ea7c-4041-b749-0a5052f43947": ("FT Controls Initiative Recommendations Generator",                                  "claude-sonnet-4-5"),
    "91824904-2c7b-40a2-8935-a2c382ca83b1": ("FT Sustainability Pain Point Generator",                                            "claude-sonnet-4-5"),
    "7f156b76-4c67-4cb1-bc3a-f407bd513f42": ("Extract Pain Points from User Research Data (Agent)",                               "gpt-5.1-chat-gus"),
    "10231cb4-f7e9-429c-8352-81b18b0dcf26": ("FT Supply Chain Finance Initiative Recommendations Generator",                      "claude-sonnet-4-5"),
    "5a78225a-124a-4b0f-81ba-75be6da79282": ("FT Controls Pain Point Generator",                                                  "claude-sonnet-4-5"),
    "460fe658-0d54-45c4-b4fd-dbb5545c29b5": ("FT Sustainability Disclosure Assistant",                                            "claude-sonnet-4-5"),
    "2e594baf-65a2-4c64-a030-968ef710232d": ("FT Sustainability Initiative Recommendations Generator",                            "claude-sonnet-4-5"),
    "7a54bfa5-bc43-439e-ba72-c463a3510d00": ("Generate Manual Test Cases and Steps from Requirements or User Stories (Agent)",    "gpt-5.1-chat-gus"),
    "c94d1efa-0e3c-4126-871c-1e49de37d5c7": ("FT Supply Chain Finance Pain Point Generator",                                      "claude-sonnet-4-5"),
    "eb4d7a7e-274f-4036-a61f-1c1b88ba5d23": ("Analyze Logs and Identify Errors and Recommend Solutions",                         "claude-sonnet-4-5"),
    "8970a835-0324-4305-8133-c5046f32b46d": ("Generate Test Cases",                                                               "gpt-5.1-chat-gus"),
    "c0a9a0e2-6224-4a31-87b9-55f495525b74": ("Generate User Stories",                                                             "gpt-5.1-chat-gus"),
    "be80526a-ebc3-4046-8fea-0025c6c1e415": ("Generate Manual Test Cases based on User Story (Agent)",                            "gpt-5.1-chat-gus"),
    "027c17e7-5405-4bd4-b7d8-c4c39359ab6a": ("Generate Golden Thread (Agent)",                                                    "gpt-5.1-chat-gus"),
    "241f8e4f-9b3e-45cb-ac99-713de8d26bf3": ("Deck, Doc & Excel Generator",                                                      "claude-sonnet-4-5"),
    "5be26b56-1690-46cf-b278-1f35b5938a7a": ("Chart Creation Agent PUBLIC",                                                       "gemini-3.1-pro-preview"),
    "d6b2274e-4c40-415b-912b-9bdc915b0b46": ("Draw.IO Agent",                                                                     "claude-sonnet-4-6"),
}

# Convenience: name → UUID lookup (lower-cased name for fuzzy matching)
_AGENT_NAME_TO_ID: dict[str, str] = {
    name.lower(): uid for uid, (name, _) in ICA_AGENT_CATALOGUE.items()
}


def resolve_agent_id(model_or_name: str) -> str:
    """
    Accept either a raw UUID (pass-through) or a human-readable agent name
    and return the ICA agent UUID. Raises ValueError when not found.
    """
    # Already looks like a UUID
    if len(model_or_name) == 36 and model_or_name.count("-") == 4:
        return model_or_name
    # Case-insensitive name match
    key = model_or_name.lower().strip()
    if key in _AGENT_NAME_TO_ID:
        return _AGENT_NAME_TO_ID[key]
    raise ValueError(
        f"ICA agent '{model_or_name}' not found. "
        f"Pass the UUID directly or use one of: {list(_AGENT_NAME_TO_ID.keys())}"
    )


class ICAProvider(LLMProvider):
    """
    IBM ICA provider.

    Wraps the OpenAI-compatible ``POST /agents/chat/completions`` endpoint.
    The ``model`` field of LLMRequest should be an ICA agent UUID or the
    display name from ICA_AGENT_CATALOGUE.

    Fallback behaviour
    ------------------
    If ICA fails for any reason (token expired, network error, rate limit,
    5xx), AND ``OPENAI_API_KEY`` is set in the environment, the request is
    automatically retried against OpenAI gpt-4o.  The LLMResponse will carry
    ``provider="openai_fallback"`` so the trace makes the fallback visible.

    Set ``ICA_DISABLE_OPENAI_FALLBACK=true`` to turn this off entirely.

    Embeddings are NOT supported natively by ICA; this provider raises
    NotImplementedError for embed() so the orchestrator falls back to the
    local sentence-transformers embedder.
    """

    _BASE_URL = "https://api.nextgen-beta.ica.ibm.com/ica/v1"
    # Pick a general-purpose default — Internet Researcher backed by gpt-5.1-chat-gus
    _DEFAULT_AGENT_ID = "d464de5e-01b5-461a-94df-d6d0e34a3cfe"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_agent_id: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._api_key = api_key or os.environ["ICA_API_KEY"]
        self._base_url = (base_url or os.getenv("ICA_BASE_URL") or self._BASE_URL).rstrip("/")
        self._default_agent_id = (
            default_agent_id
            or os.getenv("ICA_DEFAULT_AGENT_ID")
            or self._DEFAULT_AGENT_ID
        )
        self._timeout = timeout
        self._http = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )

    # ------------------------------------------------------------------
    # LLMProvider properties
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "ica"

    @property
    def default_model(self) -> str:
        return self._default_agent_id

    @property
    def available_models(self) -> list[str]:
        return list(ICA_AGENT_CATALOGUE.keys())

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def complete(self, request: LLMRequest) -> LLMResponse:
        try:
            return self._complete_via_ica(request)
        except Exception as ica_exc:
            import logging
            logger = logging.getLogger(__name__)
            # Check whether fallback is allowed
            fallback_disabled = os.getenv("ICA_DISABLE_OPENAI_FALLBACK", "").lower() == "true"
            openai_key = os.getenv("OPENAI_API_KEY", "").strip()
            if fallback_disabled or not openai_key:
                # No fallback configured — re-raise the original error
                raise
            logger.warning(
                f"ICA call failed ({ica_exc}). "
                f"Falling back to OpenAI gpt-4o (personal API key)."
            )
            return self._complete_via_openai_fallback(request, openai_key, ica_error=str(ica_exc))

    def _complete_via_ica(self, request: LLMRequest) -> LLMResponse:
        """Make the actual ICA API call."""
        # Resolve agent: metadata override → request.model → provider default
        raw_model = (
            request.metadata.get("ica_agent_id")
            or request.model
            or self._default_agent_id
        )
        agent_id = resolve_agent_id(raw_model)
        display_name, base_model = ICA_AGENT_CATALOGUE.get(agent_id, (agent_id, "unknown"))

        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for msg in request.messages:
            messages.append({"role": msg.role.value, "content": msg.content})

        payload: dict[str, Any] = {
            "model": agent_id,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        start = time.perf_counter()
        resp = self._http.post("/agents/chat/completions", json=payload)
        latency_ms = (time.perf_counter() - start) * 1000

        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        content_text: str = choice.get("message", {}).get("content") or ""
        finish_reason: str = choice.get("finish_reason") or "stop"

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return LLMResponse(
            content=content_text,
            model=agent_id,
            provider=self.provider_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=estimate_cost(base_model, input_tokens, output_tokens),
            latency_ms=round(latency_ms, 2),
            finish_reason=finish_reason,
            metadata={"ica_agent_name": display_name, "ica_base_model": base_model},
        )

    @staticmethod
    def _complete_via_openai_fallback(
        request: LLMRequest,
        api_key: str,
        ica_error: str,
    ) -> LLMResponse:
        """OpenAI gpt-4o fallback — only called when ICA fails."""
        from openai import OpenAI
        from eio.core.llm_pricing import estimate_cost as _cost

        client = OpenAI(api_key=api_key)
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for msg in request.messages:
            messages.append({"role": msg.role.value, "content": msg.content})

        start = time.perf_counter()
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,  # type: ignore[arg-type]
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        usage = resp.usage
        input_tokens  = usage.prompt_tokens     if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model="gpt-4o",
            provider="openai_fallback",          # visible in the trace
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=_cost("gpt-4o", input_tokens, output_tokens),
            latency_ms=round(latency_ms, 2),
            finish_reason=resp.choices[0].finish_reason or "stop",
            metadata={"fallback_reason": ica_error, "original_provider": "ica"},
        )

    def embed(self, text: str, model: str | None = None) -> EmbeddingResponse:
        """
        ICA does not expose a native embeddings endpoint.
        The orchestrator will automatically fall back to the local
        sentence-transformers embedder when this raises NotImplementedError.
        """
        raise NotImplementedError(
            "ICA provider does not support embeddings natively. "
            "Use EIO_ACTIVE_LLM=mock or gpt_oss for embedding tasks, "
            "or configure a dedicated embedding model."
        )

    def health_check(self) -> dict[str, Any]:
        try:
            resp = self._http.get("/agents/models")
            resp.raise_for_status()
            count = len(resp.json().get("data", []))
            return {
                "status": "ok",
                "provider": self.provider_name,
                "model": self._default_agent_id,
                "agents_available": count,
            }
        except Exception as exc:
            return {
                "status": "error",
                "provider": self.provider_name,
                "detail": str(exc),
            }
