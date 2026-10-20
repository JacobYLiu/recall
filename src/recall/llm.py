"""LLM factory. Provider is inferred from whichever API key is set.

Swap providers here only — nodes never import a provider SDK directly.
"""

from __future__ import annotations

import os


def get_llm(model: str | None = None, temperature: float = 0.0):
    """Return a chat model. Raises RuntimeError if no provider key is set."""
    model = model or os.environ.get("RECALL_MODEL", "claude-sonnet-4-5")
    if os.environ.get("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, temperature=temperature)
    if os.environ.get("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, temperature=temperature)
    raise RuntimeError(
        "No model provider key set. Copy .env.example to .env and set "
        "ANTHROPIC_API_KEY or OPENAI_API_KEY."
    )


def llm_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
