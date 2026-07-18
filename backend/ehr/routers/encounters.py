"""Encounters (admissions/visits) and their disposition status."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Encounter, Patient
from ..models.base import new_id, utcnow
from ..schemas import EncounterCreate, EncounterUpdate
from ._common import get_or_404, serialize, serialize_many

router = APIRouter(tags=["encounters"])


@router.get("/encounters", summary="List / filter encounters")
def list_encounters(
    session: Session = Depends(get_session),
    patient_id: Optional[str] = None,
    status: Optional[str] = Query(None, description="planned | in-progress | finished | cancelled"),
    class_code: Optional[str] = Query(None, description="AMB | IMP | EMER"),
    limit: int = Query(100, le=500),
    offset: int = 0,
) -> list[dict]:
    stmt = select(Encounter)
    if patient_id:
        stmt = stmt.where(Encounter.patient_id == patient_id)
    if status:
        stmt = stmt.where(Encounter.status == status)
    if class_code:
        stmt = stmt.where(Encounter.class_code == class_code)
    rows = session.exec(stmt.order_by(Encounter.period_start.desc()).offset(offset).limit(limit)).all()
    return serialize_many(rows)


@router.get("/patients/{patient_id}/encounters", summary="List a patient's encounters")
def list_patient_encounters(patient_id: str, session: Session = Depends(get_session)) -> list[dict]:
    get_or_404(session, Patient, patient_id, "Patient")
    rows = session.exec(
        select(Encounter).where(Encounter.patient_id == patient_id).order_by(Encounter.period_start.desc())
    ).all()
    return serialize_many(rows)


@router.get("/encounters/{encounter_id}", summary="Get one encounter")
def get_encounter(encounter_id: str, session: Session = Depends(get_session), include_raw: bool = False) -> dict:
    return serialize(get_or_404(session, Encounter, encounter_id, "Encounter"), include_raw)


@router.post("/encounters", status_code=201, summary="Create/admit an encounter")
def create_encounter(body: EncounterCreate, session: Session = Depends(get_session)) -> dict:
    enc = Encounter(
        id=new_id(),
        patient_id=body.patient_id,
        status=body.status.value,
        class_code=body.class_code.value,
        type_text=body.type_text,
        visit_title=body.visit_title,
        reason_text=body.reason_text,
        period_start=body.period_start or utcnow(),
        location_display=body.location_display,
        attending_name=body.attending_name,
    )
    session.add(enc)
    session.commit()
    session.refresh(enc)
    return serialize(enc)


@router.patch(
    "/encounters/{encounter_id}",
    summary="Update an encounter (discharge, set disposition)",
    description="Set `period_end` to discharge. Set `disposition_status`/`planned_disposition` as the team commits to a plan.",
)
def update_encounter(encounter_id: str, body: EncounterUpdate, session: Session = Depends(get_session)) -> dict:
    enc = get_or_404(session, Encounter, encounter_id, "Encounter")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(enc, key, value)
    enc.updated_at = utcnow()
    session.add(enc)
    session.commit()
    session.refresh(enc)
    return serialize(enc)
