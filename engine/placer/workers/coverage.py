"""Coverage worker: payer benefits verification.

There is no payer-line integration yet, and Placer never invents a payer
verdict — the worker asks the care team to verify benefits (one chat question)
and parks the task as waiting. The payer barrier stays exactly as it is until
a human (or a future real integration) resolves it.
"""

from __future__ import annotations

from sqlmodel import Session

from ..registry import load_pathways
from .common import get_case, get_payload


def verify_benefits(session: Session, task, ehr, worker: str) -> dict:
    """payload {pathway_ids}: ask the team to verify coverage for those levels
    of care. Posts ONE chat question and returns a waiting result — no
    fabricated payer outcome, no barrier changes, no EHR communication."""
    case = get_case(session, task.case_id)
    payload = get_payload(task)
    pathway_ids = payload.get("pathway_ids") or task.pathway_ids or []
    catalog = load_pathways()
    levels = [catalog[p]["name"] for p in pathway_ids if p in catalog] or [
        "the planned discharge disposition"
    ]

    from placer.api.chat import post_message

    post_message(
        session,
        f"[needs a human] Please verify payer benefits/authorization for: "
        f"{', '.join(levels)}. Automated payer verification is not yet integrated, "
        "so Placer cannot confirm coverage itself.",
        case_id=case.id,
        kind="text",
    )
    return {
        "waiting_on": "team",
        "note": "Benefits verification needs a human — no payer integration yet",
        "levels": levels,
        "chat_posted": True,
    }
