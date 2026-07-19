"""Thin client for the Bland AI outbound-calling API.

Placer uses this to actually place the phone calls behind its care tasks —
calling SNFs for bed availability, calling family for preferences, etc. See
https://docs.bland.ai. Kept to httpx (already a dependency); the endpoint is a
single ``POST /v1/calls`` authenticated with the raw API key in an
``authorization`` header (no ``Bearer`` prefix — Bland's convention).

The gating policy (who Placer may call without a human in the loop) and the
demo force-number live in the caller (``routers/calls.py`` + ``config``); this
module only knows how to dial.
"""

from __future__ import annotations

from typing import Optional

import httpx

from . import config


class BlandError(RuntimeError):
    """Raised when Bland is unconfigured or rejects/aborts the call request."""


def place_call(
    *,
    phone_number: str,
    task: str,
    voice: Optional[str] = None,
    first_sentence: Optional[str] = None,
    max_duration: Optional[int] = None,
    metadata: Optional[dict] = None,
    record: bool = True,
    timeout: float = 30.0,
) -> dict:
    """Queue an outbound call via Bland and return the parsed JSON response.

    ``phone_number`` must already be E.164 (``+1...``). Raises ``BlandError`` if
    no API key is configured or Bland returns a non-2xx / ``status == "error"``.
    """
    if not config.BLAND_API_KEY:
        raise BlandError(
            "BLAND_API_KEY is not configured. Add it to backend/.env "
            "(see .env.example) before placing calls."
        )

    payload: dict = {"phone_number": phone_number, "task": task, "record": record}
    if voice:
        payload["voice"] = voice
    if first_sentence:
        payload["first_sentence"] = first_sentence
    if max_duration is not None:
        payload["max_duration"] = max_duration
    if metadata:
        payload["metadata"] = metadata

    try:
        resp = httpx.post(
            f"{config.BLAND_BASE_URL}/v1/calls",
            headers={"authorization": config.BLAND_API_KEY},
            json=payload,
            timeout=timeout,
        )
    except httpx.HTTPError as exc:  # network / timeout
        raise BlandError(f"Could not reach Bland: {exc}") from exc

    try:
        data = resp.json()
    except ValueError:
        data = {}

    if resp.status_code >= 400 or data.get("status") == "error":
        message = data.get("message") or data.get("errors") or resp.text
        raise BlandError(f"Bland rejected the call ({resp.status_code}): {message}")

    return data


def get_call(call_id: str, timeout: float = 30.0) -> dict:
    """Fetch a call's status/result from Bland. ``GET /v1/calls/{id}``.

    Used to poll for completion so Placer can act on the transcript without a
    reachable webhook (Bland's cloud can't reach a localhost demo)."""
    if not config.BLAND_API_KEY:
        raise BlandError("BLAND_API_KEY is not configured.")
    try:
        resp = httpx.get(
            f"{config.BLAND_BASE_URL}/v1/calls/{call_id}",
            headers={"authorization": config.BLAND_API_KEY},
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        raise BlandError(f"Could not reach Bland: {exc}") from exc
    try:
        return resp.json()
    except ValueError:
        return {}
