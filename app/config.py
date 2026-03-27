"""Application configuration loaded from environment / .env file."""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

_singleton: Config | None = None


class Config(BaseModel):
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    default_provider: Literal["anthropic", "openai"] = "anthropic"
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o"
    disable_llm: bool = False


def get_config() -> Config:
    """Return a singleton Config populated from environment variables."""
    global _singleton
    if _singleton is not None:
        return _singleton

    _singleton = Config(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        default_provider=os.getenv("DEFAULT_PROVIDER", "anthropic"),  # type: ignore[arg-type]
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        disable_llm=os.getenv("DISABLE_LLM", "").lower() in {"1", "true", "yes", "on"},
    )
    return _singleton
