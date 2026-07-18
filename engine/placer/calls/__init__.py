"""The call layer: one function, ``place_call``, that every worker uses to
"phone" a facility, family member, payer, or vendor.

There is deliberately NO simulation mode — Placer never fabricates a call
outcome. In ``disabled`` mode (default) ``place_call`` raises
:class:`CallingUnavailable` so workers park the task as waiting-on-telephony.
``bland`` mode is the upcoming Bland AI integration behind the same signature.
"""

from __future__ import annotations

from .. import config
from .schemas import CallResult

__all__ = ["CallResult", "CallingUnavailable", "place_call"]


class CallingUnavailable(RuntimeError):
    """No real telephony integration is enabled; the call cannot be placed.

    Workers catch this and return a truthful waiting result — never a
    fabricated outcome.
    """


def place_call(objective: str, questions: list, callee: dict, context: str) -> CallResult:
    """Place one outbound call and return its structured result.

    ``objective`` is the one-line purpose of the call, ``questions`` the list
    Placer needs answered (answers come back keyed by these strings verbatim),
    ``callee`` a dict describing who picks up (facility record, family member,
    payer line...), and ``context`` free-text case background.
    """
    if config.CALL_MODE == "bland":
        raise NotImplementedError("bland integration lands next")
    if config.CALL_MODE == "disabled":
        raise CallingUnavailable(
            "Real call required — calling is not yet enabled (Bland integration pending)"
        )
    raise ValueError(f"Unknown CALL_MODE '{config.CALL_MODE}' (expected 'disabled' or 'bland')")
