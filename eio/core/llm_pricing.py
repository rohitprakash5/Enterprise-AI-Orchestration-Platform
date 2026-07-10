"""
LLM Token Pricing Reference Table
===================================
Provides per-token cost estimates for model routing and cost tracking.
Update rates as providers change their pricing.

All costs are in USD per 1,000 tokens.
"""

from __future__ import annotations

# cost_per_1k_tokens: {"input": float, "output": float}
LLM_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o":              {"input": 0.005,   "output": 0.015},
    "gpt-4o-mini":         {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo":         {"input": 0.010,   "output": 0.030},
    "gpt-3.5-turbo":       {"input": 0.0005,  "output": 0.0015},
    # Anthropic
    "claude-3-5-sonnet":   {"input": 0.003,   "output": 0.015},
    "claude-3-haiku":      {"input": 0.00025, "output": 0.00125},
    "claude-3-opus":       {"input": 0.015,   "output": 0.075},
    # IBM Granite
    "granite-13b-chat":    {"input": 0.0003,  "output": 0.0006},
    "granite-34b-code":    {"input": 0.0006,  "output": 0.0012},
    # Gemini
    "gemini-1.5-pro":      {"input": 0.0035,  "output": 0.0105},
    "gemini-1.5-flash":    {"input": 0.00035, "output": 0.00105},
    # Ollama (local — no cost)
    "llama3":              {"input": 0.0,     "output": 0.0},
    "llama3:8b":           {"input": 0.0,     "output": 0.0},
    "mistral":             {"input": 0.0,     "output": 0.0},
    "codellama":           {"input": 0.0,     "output": 0.0},
}

# Default fallback if model not in table
DEFAULT_PRICING = {"input": 0.01, "output": 0.03}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate request cost in USD."""
    pricing = LLM_PRICING.get(model, DEFAULT_PRICING)
    return (
        (input_tokens / 1000) * pricing["input"]
        + (output_tokens / 1000) * pricing["output"]
    )


def tokens_to_cost(model: str, tokens: int) -> float:
    """Quick estimate using only total token count (assumes 70% input / 30% output split)."""
    return estimate_cost(model, int(tokens * 0.7), int(tokens * 0.3))
