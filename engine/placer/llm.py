"""Shared LLM helpers for the engine's model calls.

All model access goes through these two functions so tests can monkeypatch a
single seam (``placer.llm.structured`` / ``placer.llm.complete``) and so the
model/effort configuration lives in one place. Workers and the brain must not
construct their own anthropic clients.
"""

from __future__ import annotations

from typing import Any, List, Optional, Type, TypeVar

import anthropic

from . import config

T = TypeVar("T")

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def structured(
    prompt: str,
    schema: Type[T],
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 4096,
) -> T:
    """One structured call: returns a validated instance of ``schema`` (a
    Pydantic model). Raises on refusal or parse failure — callers treat any
    exception as "no judgment available" and fall back to safe behavior.
    """
    client = _get_client()
    kwargs: dict = {
        "model": model or config.MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "output_format": schema,
    }
    if system:
        kwargs["system"] = system
    response = client.messages.parse(**kwargs)
    if response.parsed_output is None:
        raise RuntimeError(f"structured call returned no parseable output (stop_reason={response.stop_reason})")
    return response.parsed_output


def complete(
    messages: List[dict],
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 1024,
) -> str:
    """Plain text turn for conversational simulation (e.g. the simulated
    admissions desk on the other end of a 'call'). ``messages`` is a standard
    Messages API list.
    """
    client = _get_client()
    kwargs: dict = {
        "model": model or config.MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""
