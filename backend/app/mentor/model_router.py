"""
Model router — decides which LLM provider/model to use per hint level.

AGENTS.md constraint #7: ALL LLM calls MUST go through this router.
No code path calls provider SDKs directly.

Routing rules (per PRD Section 11):
  Level 1: template-based (no LLM call at all for very common patterns)
  Level 2: cheap hosted model (gpt-4o-mini class)
  Level 3: cheap model with richer context
  Level 4: frontier model (gpt-4o class)
  Code review: frontier model
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class HintTier(IntEnum):
    CHEAP = 1     # levels 1-2
    FRONTIER = 2  # levels 3-4 and code review


def get_tier_for_hint_level(level: int) -> HintTier:
    """Return which model tier to use for the given hint level."""
    if level <= 2:
        return HintTier.CHEAP
    return HintTier.FRONTIER


@dataclass
class ModelConfig:
    provider: str
    model: str
    max_tokens: int
    temperature: float


def get_model_config(tier: HintTier) -> ModelConfig:
    """Return the model configuration for a given tier."""
    if tier == HintTier.CHEAP:
        return ModelConfig(
            provider=settings.cheap_llm_provider,
            model=settings.cheap_llm_model,
            max_tokens=512,
            temperature=0.4,
        )
    return ModelConfig(
        provider=settings.frontier_llm_provider,
        model=settings.frontier_llm_model,
        max_tokens=1024,
        temperature=0.3,
    )


async def call_llm(
    messages: list[dict[str, str]],
    tier: HintTier,
    hint_level: int | None = None,
) -> tuple[str, str, int]:
    """
    Route an LLM call to the appropriate provider.

    Returns:
        (response_text, model_used, tokens_used)

    AGENTS.md constraint #7: this is the single call site for all LLM interactions.
    """
    config = get_model_config(tier)
    logger.info(
        "model_router.call",
        provider=config.provider,
        model=config.model,
        hint_level=hint_level,
        tier=tier.name,
    )

    if config.provider == "openai":
        return await _call_openai(messages, config)
    elif config.provider == "anthropic":
        return await _call_anthropic(messages, config)
    else:
        raise ValueError(f"Unknown LLM provider: {config.provider!r}")


async def _call_openai(
    messages: list[dict[str, str]], config: ModelConfig
) -> tuple[str, str, int]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=config.model,
        messages=messages,  # type: ignore[arg-type]
        max_tokens=config.max_tokens,
        temperature=config.temperature,
    )
    text = resp.choices[0].message.content or ""
    tokens = resp.usage.total_tokens if resp.usage else 0
    return text, config.model, tokens


async def _call_anthropic(
    messages: list[dict[str, str]], config: ModelConfig
) -> tuple[str, str, int]:
    import anthropic

    # Anthropic API uses system message separately
    system_msg = ""
    anthropic_messages: list[dict[str, str]] = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            anthropic_messages.append({"role": m["role"], "content": m["content"]})

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=config.model,
        max_tokens=config.max_tokens,
        system=system_msg,
        messages=anthropic_messages,  # type: ignore[arg-type]
    )
    text = resp.content[0].text if resp.content else ""
    tokens = resp.usage.input_tokens + resp.usage.output_tokens
    return text, config.model, tokens
