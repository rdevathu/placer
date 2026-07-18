"""Communications — the log of calls/messages agents make (family, SNFs, PCPs)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..db import get_session
from ..events import get_actor, record_event
from ..models import Communication
from ..models.base import new_id, utcnow
from ..schemas import CommunicationCreate
from ._common import get_or_404, serialize, serialize_many

router = APIRouter(prefix="/communications", tags=["communications"])


@router.get("", summary="List logged communications")
def list_comms(
    session: Session = Depends(get_session),
    patient_id: Optional[str] = None,
    care_task_id: Optional[str] = None,
    facility_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = select(Communication)
    if patient_id:
        stmt = stmt.where(Communication.patient_id == patient_id)
    if care_task_id:
        stmt = stmt.where(Communication.care_task_id == care_task_id)
    if facility_id:
        stmt = stmt.where(Communication.facility_id == facility_id)
    rows = session.exec(stmt.order_by(Communication.occurred_at.desc()).offset(offset).limit(limit)).all()
    return serialize_many(rows)


@router.get("/{comm_id}", summary="Get one communication")
def get_comm(comm_id: str, session: Session = Depends(get_session)) -> dict:
    return serialize(get_or_404(session, Communication, comm_id, "Communication"))


@router.post(
    "",
    status_code=201,
    summary="Log a communication (e.g. a phone call)",
    description="Record an outbound/inbound call or message with a summary, transcript, and outcome. Used to audit the proactive dispo work.",
)
def create_comm(
    body: CommunicationCreate,
    session: Session = Depends(get_session),
    actor: str = Depends(get_actor),
) -> dict:
    comm = Communication(
        id=new_id(),
        patient_id=body.patient_id,
        care_task_id=body.care_task_id,
        facility_id=body.facility_id,
        direction=body.direction.value,
        modality=body.modality.value,
        party_type=body.party_type.value if body.party_type else None,
        party_name=body.party_name,
        summary=body.summary,
        transcript=body.transcript,
        outcome=body.outcome,
        occurred_at=body.occurred_at or utcnow(),
    )
    session.add(comm)
    record_event(
        session,
        "communication.created",
        patient_id=comm.patient_id,
        actor=actor,
        entity_type="communication",
        entity_id=comm.id,
        payload={"modality": comm.modality, "party_type": comm.party_type, "outcome": comm.outcome},
    )
    session.commit()
    session.refresh(comm)
    return serialize(comm)
