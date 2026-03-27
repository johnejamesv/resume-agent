"""Thin LLM abstraction over official Anthropic and OpenAI SDKs."""
from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

from app.config import get_config

T = TypeVar("T", bound=BaseModel)


def available_providers() -> list[str]:
    """Return the configured providers that can currently be used."""
    cfg = get_config()
    if cfg.disable_llm:
        return []

    providers: list[str] = []
    if cfg.anthropic_api_key:
        providers.append("anthropic")
    if cfg.openai_api_key:
        providers.append("openai")
    return providers


def llm_available(provider: str | None = None) -> bool:
    """Return True when the requested provider, or any provider, is usable."""
    providers = available_providers()
    if provider is None:
        return bool(providers)
    return provider in providers


def resolve_provider(provider: str | None = None) -> str:
    """Pick the requested provider if possible, otherwise fall back to any available one."""
    cfg = get_config()
    requested = provider or cfg.default_provider

    if llm_available(requested):
        return requested

    providers = available_providers()
    if providers:
        return providers[0]

    raise RuntimeError(
        "No LLM provider is available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
        "or rely on deterministic fallbacks."
    )


async def complete(
    prompt: str, system: str | None = None, temperature: float = 0.7,
    provider: str | None = None, model: str | None = None,
) -> str:
    """Send a single prompt and return the text response."""
    cfg = get_config()
    prov = resolve_provider(provider)
    if prov == "anthropic":
        return await _complete_anthropic(prompt, system, temperature, model or cfg.anthropic_model)
    if prov == "openai":
        return await _complete_openai(prompt, system, temperature, model or cfg.openai_model)
    raise ValueError(f"Unknown provider: {prov}")


async def complete_structured(
    prompt: str, response_model: type[T], system: str | None = None,
    temperature: float = 0.7, provider: str | None = None, model: str | None = None,
) -> T:
    """Send a prompt and parse the response as JSON into *response_model*."""
    schema_hint = json.dumps(response_model.model_json_schema(), indent=2)
    full_prompt = f"{prompt}\n\nRespond with ONLY valid JSON matching this schema:\n{schema_hint}"
    raw = await complete(full_prompt, system=system, temperature=temperature,
                         provider=provider, model=model)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    return response_model.model_validate_json(text)


# -- Provider implementations ------------------------------------------------

async def _complete_anthropic(
    prompt: str, system: str | None, temperature: float, model: str,
) -> str:
    import anthropic

    cfg = get_config()
    if not cfg.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    client = anthropic.AsyncAnthropic(api_key=cfg.anthropic_api_key)
    kwargs: dict = dict(
        model=model,
        max_tokens=4096,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system

    response = await client.messages.create(**kwargs)
    return response.content[0].text


async def _complete_openai(
    prompt: str, system: str | None, temperature: float, model: str,
) -> str:
    import openai

    cfg = get_config()
    if not cfg.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    client = openai.AsyncOpenAI(api_key=cfg.openai_api_key)
    response = await client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content or ""
