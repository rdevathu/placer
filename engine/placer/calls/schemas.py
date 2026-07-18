"""Structured result of one outbound Placer call.

``CallResult`` is the frozen shape every call handler consumes, regardless of
whether the call was simulated (LLM role-play) or, later, a real Twilio call.
"""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field


class CallResult(BaseModel):
    """What came back from one phone conversation."""

    transcript: str = Field(
        description=(
            "Compact realistic transcript, 8-16 turns, each line prefixed "
            "'Placer:' or with the callee's role/name."
        )
    )
    outcome: str = Field(
        description="One-line outcome summary, e.g. 'Bed available; referral via portal'."
    )
    answers: Dict[str, str] = Field(
        default_factory=dict,
        description="Each question Placer asked, keyed verbatim, with a concise honest answer.",
    )
    follow_up_needed: bool = Field(
        default=False,
        description="True if the callee could not resolve everything on this call.",
    )
    notes: str = Field(
        default="",
        description="Anything material not captured in the answers (conditions, caveats, names).",
    )
