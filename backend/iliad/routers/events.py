"""Event feed — the poll endpoint the agent engine drives from."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Event
from ._common import serialize_many

router = APIRouter(prefix="/events", tags=["events"])


@router.get(
    "",
    summary="Poll the append-only event feed (cursor-based)",
    description=(
        "Returns events with `seq > since`, ordered by `seq` ascending. "
        "Cursor pattern for agents: start with `since=0`, then on each poll "
        "pass the largest `seq` you have seen; an empty list means nothing new. "
        "`seq` is monotonically increasing and never reused (a demo reset "
        "clears the feed and restarts at 1). Each event carries `event_type` "
        "(lowercase-dot, e.g. `order.created`, `order.signed`, "
        "`care_task.updated`, `patient.admitted`), the `actor` that made the "
        "write (`clinician`, or `agent:<name>` when the caller sent an "
        "`X-Actor` header — filter these out to suppress echoes of your own "
        "writes), and a soft `patient_id` / `entity_type` / `entity_id` plus a "
        "small JSON `payload`."
    ),
)
def list_events(
    session: Session = Depends(get_session),
    since: int = Query(0, ge=0, description="Return events with seq strictly greater than this cursor"),
    limit: int = Query(200, le=1000),
    patient_id: Optional[str] = Query(None, description="Only events for this patient"),
    event_type: Optional[str] = Query(None, description="Only events of this type, e.g. 'order.signed'"),
) -> list[dict]:
    stmt = select(Event).where(Event.seq > since)
    if patient_id:
        stmt = stmt.where(Event.patient_id == patient_id)
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    rows = session.exec(stmt.order_by(Event.seq.asc()).limit(limit)).all()
    return serialize_many(rows)
