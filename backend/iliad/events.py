"""Event-feed helpers: append an Event row, resolve the request's actor.

Why ``actor`` exists: the downstream agent engine polls ``GET /events`` and
reacts to writes. The engine sends ``X-Actor: agent:<name>`` on its own API
calls, so the events *it* produces carry that actor and can be filtered out
when it polls — echo suppression. Requests without the header (the demo UI, a
clinician, plain curl) default to ``"clinician"``.

Seeding never goes through these helpers (the seed package writes ORM rows
directly), so a fresh reset always starts with an empty feed.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Header
from sqlmodel import Session

from .models import Event


def record_event(
    session: Session,
    event_type: str,
    *,
    patient_id: Optional[str] = None,
    actor: str = "clinician",
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    payload: Optional[dict] = None,
) -> Event:
    """Append an Event to the session. The caller owns the commit, so the
    event lands atomically with the mutation it describes."""
    evt = Event(
        event_type=event_type,
        patient_id=patient_id,
        actor=actor,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
    )
    session.add(evt)
    return evt


def get_actor(x_actor: Optional[str] = Header(None)) -> str:
    """FastAPI dependency: the write's provenance, from the ``X-Actor`` header.

    Agents set ``X-Actor: agent:<name>`` so their writes are distinguishable
    from clinician writes in the event feed (see module docstring — echo
    suppression). Defaults to ``"clinician"`` when absent.
    """
    return x_actor or "clinician"
