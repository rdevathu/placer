"""The call layer: one function, ``place_call``, that every worker uses to
"phone" a facility, family member, payer, or vendor.

In ``simulated`` mode (default) the entire short conversation is role-played by
a single ``llm.structured`` call that returns a filled :class:`CallResult`, so
the rest of the engine is already written against the real-call interface.
``twilio`` mode is a post-v1 drop-in behind the same signature.
"""

from __future__ import annotations

import json

from .. import config, llm
from .schemas import CallResult

__all__ = ["CallResult", "CallsDisabled", "place_call"]


class CallsDisabled(RuntimeError):
    """Raised by :func:`place_call` when ``config.PLACE_CALLS`` is off.

    Placer must not fabricate a call's outcome when no real call is placed.
    Workers catch this and *park* the task (pending/attempted) instead of
    writing a communication row, clearing barriers, or inventing results.
    """

_SIM_SYSTEM = (
    "Simulate a realistic short phone call between Placer (hospital discharge "
    "planning AI calling on behalf of County General) and the callee. Generate "
    "a compact realistic transcript (8-16 turns) and honest structured answers. "
    "Ground availability/capability answers in the callee record provided — "
    "e.g. a facility with available_beds > 0 usually has a bed; one with 0 "
    "declines or waitlists. Do not invent guarantees."
)


def place_call(objective: str, questions: list, callee: dict, context: str) -> CallResult:
    """Place one outbound call and return its structured result.

    ``objective`` is the one-line purpose of the call, ``questions`` the list
    Placer needs answered (answers come back keyed by these strings verbatim),
    ``callee`` a dict describing who picks up (facility record, family member,
    payer line...), and ``context`` free-text case background.

    Raises :class:`CallsDisabled` when ``config.PLACE_CALLS`` is off (the
    default) — Placer does not place or simulate calls, so there is no honest
    outcome to return.
    """
    if not config.PLACE_CALLS:
        raise CallsDisabled(objective)
    if config.CALL_MODE == "twilio":
        raise NotImplementedError("twilio mode lands post-v1")
    if config.CALL_MODE != "simulated":
        raise ValueError(f"Unknown CALL_MODE '{config.CALL_MODE}' (expected 'simulated' or 'twilio')")

    numbered = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))
    prompt = (
        f"Objective of the call: {objective}\n\n"
        f"Callee record:\n{json.dumps(callee, indent=2, default=str)}\n\n"
        f"Case context:\n{context}\n\n"
        f"Questions Placer needs answered:\n{numbered}\n\n"
        "Fill the call result. Key `answers` by each question above, verbatim, "
        "with one concise honest answer per question."
    )
    return llm.structured(prompt, CallResult, system=_SIM_SYSTEM)
