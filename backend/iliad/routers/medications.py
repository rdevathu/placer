"""Medications / medication list.

NOTE: imported (historical) medication rows are sparse because Synthea's
``MedicationRequest.medicationReference`` cannot be resolved to a drug name.
Hero patients carry clean, coded meds. New inpatient med orders should be
placed through the /orders endpoint (order_type=medication)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Medication, Patient
from ..models.base import new_id, utcnow
from ..schemas import MedicationCreate, MedicationUpdate
from ._common import get_or_404, serialize, serialize_many

router = APIRouter(tags=["medications"])


@router.get("/patients/{patient_id}/medications", summary="List a patient's medications")
def list_medications(
    patient_id: str,
    session: Session = Depends(get_session),
    status: Optional[str] = Query(None, description="active | stopped | completed | ..."),
    category: Optional[str] = Query(None, description="inpatient | outpatient | discharge"),
) -> list[dict]:
    get_or_404(session, Patient, patient_id, "Patient")
    stmt = select(Medication).where(Medication.patient_id == patient_id)
    if status:
        stmt = stmt.where(Medication.status == status)
    if category:
        stmt = stmt.where(Medication.category == category)
    return serialize_many(session.exec(stmt).all())


@router.get("/medications/{medication_id}", summary="Get one medication")
def get_medication(medication_id: str, session: Session = Depends(get_session), include_raw: bool = False) -> dict:
    return serialize(get_or_404(session, Medication, medication_id, "Medication"), include_raw)


@router.post("/medications", status_code=201, summary="Add a medication to the list")
def create_medication(body: MedicationCreate, session: Session = Depends(get_session)) -> dict:
    med = Medication(
        id=new_id(),
        patient_id=body.patient_id,
        encounter_id=body.encounter_id,
        display=body.display,
        dose=body.dose,
        route=body.route,
        frequency=body.frequency,
        dosage_text=" ".join(x for x in [body.display, body.dose, body.route, body.frequency] if x),
        status=body.status.value,
        category=body.category,
        authored_on=utcnow(),
    )
    session.add(med)
    session.commit()
    session.refresh(med)
    return serialize(med)


@router.patch("/medications/{medication_id}", summary="Update / stop a medication")
def update_medication(medication_id: str, body: MedicationUpdate, session: Session = Depends(get_session)) -> dict:
    med = get_or_404(session, Medication, medication_id, "Medication")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(med, key, value)
    med.updated_at = utcnow()
    session.add(med)
    session.commit()
    session.refresh(med)
    return serialize(med)
