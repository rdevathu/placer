"""Clinical notes — full CRUD plus sign. Agents draft dispo/progress/consult notes here."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Note, Patient
from ..models.base import new_id, utcnow
from ..schemas import NoteCreate, NoteUpdate
from ._common import get_or_404, serialize, serialize_many

router = APIRouter(tags=["notes"])


@router.get("/patients/{patient_id}/notes", summary="List a patient's notes")
def list_notes(
    patient_id: str,
    session: Session = Depends(get_session),
    note_type: Optional[str] = Query(None, description="progress | history_and_physical | discharge_summary | consult | case_management | ..."),
    status: Optional[str] = Query(None, description="draft | signed"),
) -> list[dict]:
    get_or_404(session, Patient, patient_id, "Patient")
    stmt = select(Note).where(Note.patient_id == patient_id)
    if note_type:
        stmt = stmt.where(Note.note_type == note_type)
    if status:
        stmt = stmt.where(Note.status == status)
    return serialize_many(session.exec(stmt.order_by(Note.created_at.desc())).all())


@router.get("/notes/{note_id}", summary="Get one note")
def get_note(note_id: str, session: Session = Depends(get_session), include_raw: bool = False) -> dict:
    return serialize(get_or_404(session, Note, note_id, "Note"), include_raw)


@router.post(
    "/notes",
    status_code=201,
    summary="Write a note (draft or signed)",
    description="Create a note. Defaults to `status=draft` (pended). Agents typically write draft consult/dispo notes for a clinician to review and sign.",
)
def create_note(body: NoteCreate, session: Session = Depends(get_session)) -> dict:
    note = Note(
        id=new_id(),
        patient_id=body.patient_id,
        encounter_id=body.encounter_id,
        note_type=body.note_type.value,
        title=body.title,
        text=body.text,
        author=body.author,
        author_role=body.author_role,
        authored_by_agent=body.authored_by_agent,
        status=body.status.value,
        signed_at=utcnow() if body.status.value == "signed" else None,
    )
    session.add(note)
    session.commit()
    session.refresh(note)
    return serialize(note)


@router.patch("/notes/{note_id}", summary="Edit a note")
def update_note(note_id: str, body: NoteUpdate, session: Session = Depends(get_session)) -> dict:
    note = get_or_404(session, Note, note_id, "Note")
    if note.status == "signed":
        raise HTTPException(status_code=409, detail="Signed notes cannot be edited; create an addendum note instead")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(note, key, value)
    note.updated_at = utcnow()
    session.add(note)
    session.commit()
    session.refresh(note)
    return serialize(note)


@router.post("/notes/{note_id}/sign", summary="Sign a note")
def sign_note(note_id: str, signed_by: str = Query(..., description="Name of the signer"), session: Session = Depends(get_session)) -> dict:
    note = get_or_404(session, Note, note_id, "Note")
    now = utcnow()
    note.status = "signed"
    note.signed_by = signed_by
    note.signed_at = now
    note.updated_at = now
    session.add(note)
    session.commit()
    session.refresh(note)
    return serialize(note)
