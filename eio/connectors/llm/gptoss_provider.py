"""
GPT-OSS Provider  (openai/gpt-oss-20b  |  openai/gpt-oss-120b)
================================================================
OpenAI's open-weight GPT-OSS models are hosted on Hugging Face at
    https://huggingface.co/openai/gpt-oss-20b
    https://huggingface.co/openai/gpt-oss-120b

This provider supports all three access modes — auto-detected at startup:

╔══════════════════════════════════════════════════════════════════╗
║  Mode                  │ What you need                          ║
╠══════════════════════════════════════════════════════════════════╣
║  1. HF Serverless API  │ Free HF account + HF_TOKEN             ║
║     (recommended now)  │ No download, no GPU, works immediately ║
╠══════════════════════════════════════════════════════════════════╣
║  2. HF Dedicated       │ HF_TOKEN + EIO_GPTOSS_ENDPOINT_URL     ║
║     Endpoint           │ Deploy once on HF; pay per hour        ║
╠══════════════════════════════════════════════════════════════════╣
║  3. Local GPU          │ ≥24 GB VRAM GPU, weights auto-download ║
║     (future / GPU box) │ EIO_ACTIVE_LLM=gpt_oss, no token      ║
╠══════════════════════════════════════════════════════════════════╣
║  4. Mock fallback      │ No token, no GPU — automatic           ║
║     (current machine)  │ Real embeddings, canned text responses ║
╚══════════════════════════════════════════════════════════════════╝

.env quick-start
-----------------
# Option A — HF Serverless (free, no GPU needed):
EIO_ACTIVE_LLM=gpt_oss
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx          # from huggingface.co/settings/tokens

# Option B — HF Dedicated Endpoint:
EIO_ACTIVE_LLM=gpt_oss
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
EIO_GPTOSS_ENDPOINT_URL=https://xxxxxx.us-east-1.aws.endpoints.huggingface.cloud

# Option C — OpenAI API (when key is ready):
EIO_ACTIVE_LLM=openai
OPENAI_API_KEY=sk-...

Switching between A / B / C requires ONLY a .env change — zero code changes.

Embeddings
----------
All modes use sentence-transformers/all-MiniLM-L6-v2 (22 MB, CPU, real semantic
similarity). Downloaded once to ~/.cache/huggingface/ automatically.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from eio.connectors.llm.base import (
    EmbeddingResponse,
    LLMProvider,
    LLMRequest,
    LLMResponse,
)

logger = logging.getLogger(__name__)

# ── Configuration constants ────────────────────────────────────────────────
_DEFAULT_MODEL_ID   = os.getenv("EIO_GPTOSS_MODEL_ID", "openai/gpt-oss-20b")
_ENDPOINT_URL       = os.getenv("EIO_GPTOSS_ENDPOINT_URL", "").strip()
_HF_TOKEN           = os.getenv("HF_TOKEN", "").strip()
_MAX_NEW_TOKENS     = 1024
_TIMEOUT_SECS       = 120

# Minimum free RAM to attempt local weight loading
_MIN_FREE_RAM_GB    = 12.0


# ── Hardware probe ─────────────────────────────────────────────────────────

def _probe_hardware() -> tuple[bool, str]:
    """
    Returns (can_run_locally, reason).
    Checks CUDA VRAM first, then system RAM.
    """
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                vram_gb = torch.cuda.get_device_properties(i).total_memory / 1e9
                if vram_gb >= 20:
                    return True, f"CUDA GPU {i} — {vram_gb:.0f} GB VRAM"
            total_vram = sum(
                torch.cuda.get_device_properties(i).total_memory
                for i in range(torch.cuda.device_count())
            ) / 1e9
            return False, f"Total VRAM {total_vram:.0f} GB < 20 GB required for gpt-oss-20b"
    except Exception:
        pass

    try:
        import ctypes
        class _MEM(ctypes.Structure):
            _fields_ = [
                ("dwLength",               ctypes.c_ulong),
                ("dwMemoryLoad",           ctypes.c_ulong),
                ("ullTotalPhys",           ctypes.c_ulonglong),
                ("ullAvailPhys",           ctypes.c_ulonglong),
                ("ullTotalPageFile",       ctypes.c_ulonglong),
                ("ullAvailPageFile",       ctypes.c_ulonglong),
                ("ullTotalVirtual",        ctypes.c_ulonglong),
                ("ullAvailVirtual",        ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        m = _MEM(); m.dwLength = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        free_gb = m.ullAvailPhys / 1e9
        if free_gb >= _MIN_FREE_RAM_GB:
            return True, f"{free_gb:.1f} GB free RAM"
        return False, f"Only {free_gb:.1f} GB free RAM (need ≥{_MIN_FREE_RAM_GB} GB)"
    except Exception:
        pass

    return False, "Could not determine hardware capabilities"


# ── Sentence-transformer embeddings (shared across all providers) ──────────

_st_model_cache: Any = None
_ST_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"   # 22 MB, CPU-fast, 384-dim


def get_sentence_embedding(text: str, provider_name: str = "local") -> EmbeddingResponse:
    """
    Real semantic embedding using sentence-transformers/all-MiniLM-L6-v2.
    - 22 MB download, cached permanently in ~/.cache/huggingface/
    - Runs on CPU in ~5 ms
    - 384-dimensional cosine-similarity vectors
    - Used for ChromaDB RAG indexing and query retrieval
    """
    global _st_model_cache
    if _st_model_cache is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"[Embed] Loading {_ST_MODEL_ID} (22 MB, one-time download)…")
            _st_model_cache = SentenceTransformer(_ST_MODEL_ID)
            logger.info("[Embed] Embedding model ready")
        except ImportError:
            logger.warning("[Embed] sentence-transformers not installed — using hash embeddings")
            from eio.connectors.llm.mock_provider import _mock_embedding
            return EmbeddingResponse(
                embedding=_mock_embedding(text, 384),
                model="hash-embed-384",
                provider=provider_name,
                input_tokens=len(text.split()),
                cost_usd=0.0,
            )

    start = time.perf_counter()
    vec: list[float] = _st_model_cache.encode(
        text, normalize_embeddings=True, show_progress_bar=False
    ).tolist()
    latency_ms = (time.perf_counter() - start) * 1000
    logger.debug(f"[Embed] {len(vec)}-dim vector in {latency_ms:.1f} ms")

    return EmbeddingResponse(
        embedding=vec,
        model=_ST_MODEL_ID,
        provider=provider_name,
        input_tokens=len(text.split()),
        cost_usd=0.0,
    )


# ── GPT-OSS Provider ───────────────────────────────────────────────────────

class GptOssProvider(LLMProvider):
    """
    GPT-OSS provider with automatic mode selection:

        HF_TOKEN set + EIO_GPTOSS_ENDPOINT_URL set  →  Dedicated Endpoint
        HF_TOKEN set only                            →  HF Serverless API
        No token, GPU available                      →  Local weight loading
        No token, no GPU                             →  Mock fallback

    All modes expose the same LLMProvider interface.
    No other part of the platform needs to know which mode is active.
    """

    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL_ID,
        endpoint_url: str = _ENDPOINT_URL,
        hf_token: str = _HF_TOKEN,
        **_kwargs: Any,
    ) -> None:
        self._model_id    = model_id
        self._endpoint_url = endpoint_url.strip()
        self._hf_token    = hf_token.strip()
        self._pipeline    = None      # set in local mode
        self._tokenizer   = None
        self._hf_client   = None      # set in HF API modes
        self._fallback    = None      # set in mock-fallback mode
        self._mode        = "unset"
        self._note        = ""

        self._select_mode()

    # ── Mode selection ─────────────────────────────────────────────────

    def _select_mode(self) -> None:

        # 1. Dedicated Endpoint ────────────────────────────────────────
        if self._endpoint_url and self._hf_token:
            self._mode = "dedicated_endpoint"
            self._note = f"HF Dedicated Endpoint: {self._endpoint_url}"
            self._init_hf_client(self._endpoint_url)
            logger.info(f"[GptOss] Mode: {self._mode} → {self._note}")
            return

        # 2. HF Serverless API (just a token) ──────────────────────────
        if self._hf_token:
            self._mode = "hf_serverless"
            self._note = f"HF Serverless Inference API → {self._model_id}"
            self._init_hf_client(self._model_id)
            logger.info(f"[GptOss] Mode: {self._mode} → {self._note}")
            return

        # 3. Local GPU ─────────────────────────────────────────────────
        can_load, hw_reason = _probe_hardware()
        if can_load:
            try:
                self._load_local()
                self._mode = "local_gpu"
                self._note = f"Local weights loaded ({hw_reason})"
                logger.info(f"[GptOss] Mode: {self._mode} → {self._note}")
                return
            except Exception as exc:
                logger.warning(f"[GptOss] Local load failed: {exc}")

        # 4. Mock fallback ─────────────────────────────────────────────
        from eio.connectors.llm.mock_provider import MockLLMProvider
        self._fallback = MockLLMProvider()
        self._mode = "mock_fallback"
        self._note = (
            f"Hardware insufficient ({hw_reason}). No HF_TOKEN set. "
            "Running mock provider. To upgrade: set HF_TOKEN=hf_xxx in .env "
            "for HF Serverless API, or set OPENAI_API_KEY for OpenAI."
        )
        logger.warning(f"[GptOss] {self._note}")

    def _init_hf_client(self, model_or_url: str) -> None:
        from huggingface_hub import InferenceClient
        self._hf_client = InferenceClient(
            model=model_or_url,
            token=self._hf_token,
            timeout=_TIMEOUT_SECS,
        )

    def _load_local(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        import torch

        logger.info(f"[GptOss] Downloading/loading {self._model_id} weights…")
        kwargs: dict[str, Any] = {
            "trust_remote_code": True,
            "device_map": "auto",
            "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
        }
        tokenizer = AutoTokenizer.from_pretrained(self._model_id, trust_remote_code=True)
        model     = AutoModelForCausalLM.from_pretrained(self._model_id, **kwargs)
        self._pipeline  = pipeline("text-generation", model=model, tokenizer=tokenizer,
                                   device_map="auto")
        self._tokenizer = tokenizer

    # ── LLMProvider interface ──────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return "gpt_oss"

    @property
    def default_model(self) -> str:
        return self._model_id

    @property
    def available_models(self) -> list[str]:
        return ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]

    def complete(self, request: LLMRequest) -> LLMResponse:
        if self._mode in ("hf_serverless", "dedicated_endpoint"):
            return self._complete_hf_api(request)
        if self._mode == "local_gpu":
            return self._complete_local(request)
        # mock_fallback
        resp = self._fallback.complete(request)  # type: ignore[union-attr]
        return LLMResponse(**{**resp.model_dump(),
                              "provider": "gpt_oss(mock)", "model": self._model_id})

    def embed(self, text: str, model: str | None = None) -> EmbeddingResponse:
        """Real semantic embeddings via sentence-transformers (CPU, 22 MB, no token needed)."""
        return get_sentence_embedding(text, provider_name=self.provider_name)

    def health_check(self) -> dict[str, Any]:
        ok = self._mode not in ("unset",)
        return {
            "status": "ok" if ok else "error",
            "provider": self.provider_name,
            "model": self._model_id,
            "mode": self._mode,
            "note": self._note,
        }

    # ── HF Inference API completion ────────────────────────────────────

    def _complete_hf_api(self, request: LLMRequest) -> LLMResponse:
        """
        Calls the HF InferenceClient.text_generation() endpoint.
        Works for both Serverless and Dedicated Endpoint modes.
        """
        prompt = self._build_prompt(request)
        start = time.perf_counter()
        try:
            result = self._hf_client.text_generation(  # type: ignore[union-attr]
                prompt,
                max_new_tokens=min(request.max_tokens, _MAX_NEW_TOKENS),
                temperature=max(float(request.temperature), 0.01),
                do_sample=request.temperature > 0,
                return_full_text=False,
                stop_sequences=["[USER]", "[SYSTEM]"],
            )
            content = result.strip() if isinstance(result, str) else str(result)
        except Exception as exc:
            logger.error(f"[GptOss] HF API call failed: {exc}")
            # Graceful degradation to mock
            from eio.connectors.llm.mock_provider import MockLLMProvider
            resp = MockLLMProvider().complete(request)
            return LLMResponse(**{**resp.model_dump(),
                                  "provider": "gpt_oss(api-error-fallback)",
                                  "model": self._model_id})

        latency_ms = (time.perf_counter() - start) * 1000
        input_tokens  = len(prompt.split())
        output_tokens = len(content.split())

        return LLMResponse(
            content=content,
            model=self._model_id,
            provider=self.provider_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=0.0,          # HF Serverless has a free tier; Dedicated billed by HF
            latency_ms=round(latency_ms, 2),
            finish_reason="stop",
        )

    # ── Local GPU completion ───────────────────────────────────────────

    def _complete_local(self, request: LLMRequest) -> LLMResponse:
        prompt = self._build_prompt(request)
        start  = time.perf_counter()
        outputs = self._pipeline(  # type: ignore[misc]
            prompt,
            max_new_tokens=request.max_tokens,
            temperature=max(float(request.temperature), 0.01),
            do_sample=request.temperature > 0,
            return_full_text=False,
            pad_token_id=self._tokenizer.eos_token_id,  # type: ignore[union-attr]
        )
        latency_ms = (time.perf_counter() - start) * 1000
        content    = outputs[0]["generated_text"].strip()

        return LLMResponse(
            content=content,
            model=self._model_id,
            provider=self.provider_name,
            input_tokens=len(prompt.split()),
            output_tokens=len(content.split()),
            total_tokens=len(prompt.split()) + len(content.split()),
            cost_usd=0.0,
            latency_ms=round(latency_ms, 2),
            finish_reason="stop",
        )

    # ── Prompt builder ─────────────────────────────────────────────────

    @staticmethod
    def _build_prompt(request: LLMRequest) -> str:
        """
        GPT-OSS uses a simple role-prefixed format (no chat template defined yet).
        Adjust this once an official chat template is published.
        """
        parts: list[str] = []
        if request.system_prompt:
            parts.append(f"[SYSTEM]\n{request.system_prompt.strip()}\n")
        for msg in request.messages:
            role = msg.role.value.upper()
            parts.append(f"[{role}]\n{msg.content.strip()}\n")
        parts.append("[ASSISTANT]\n")
        return "\n".join(parts)


# Keep backward-compatible alias used by mock_provider.py
_sentence_embed = get_sentence_embedding
