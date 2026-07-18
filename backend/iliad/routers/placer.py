"""Placer chat — the per-patient message thread between the care team and Placer.

Placer (the disposition-planning product built on top of Iliad) posts progress
updates and questions here; providers reply in the same thread. There is no
auto-reply: posting a provider message just appends to the thread.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..models import Patient, PlacerMessage
from ..models.base import new_id
from ..schemas import PlacerMessageCreate
from ._common import get_or_404, serialize, serialize_many

router = APIRouter(tags=["placer"])


@router.get(
    "/patients/{patient_id}/placer/messages",
    summary="Read a patient's Placer chat thread",
    description=(
        "Messages between the care team and Placer about this patient, in "
        "chronological (ascending `created_at`) order. `sender` is `placer` "
        "for Placer's updates/questions and `provider` for care-team replies."
    ),
)
def list_messages(
    patient_id: str,
    session: Session = Depends(get_session),
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    get_or_404(session, Patient, patient_id, "Patient")
    stmt = (
        select(PlacerMessage)
        .where(PlacerMessage.patient_id == patient_id)
        .order_by(PlacerMessage.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return serialize_many(session.exec(stmt).all())


@router.post(
    "/patients/{patient_id}/placer/messages",
    status_code=201,
    summary="Post a message to a patient's Placer chat thread",
    description=(
        "Append a message to the thread. `sender` must be `provider` (care "
        "team, the default) or `placer` (the Placer agent). No auto-reply is "
        "generated — Placer responds asynchronously when it next works the "
        "patient."
    ),
)
def create_message(
    patient_id: str,
    body: PlacerMessageCreate,
    session: Session = Depends(get_session),
) -> dict:
    get_or_404(session, Patient, patient_id, "Patient")
    msg = PlacerMessage(
        id=new_id(),
        patient_id=patient_id,
        sender=body.sender.value,
        sender_name=body.sender_name,
        text=body.text,
    )
    session.add(msg)
    session.commit()
    session.refresh(msg)
    return serialize(msg)
