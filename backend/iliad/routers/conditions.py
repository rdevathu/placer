"""Conditions / problem list."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import Condition, Patient
from ..models.base import new_id, utcnow
from ..schemas import ConditionCreate, ConditionUpdate
from ._common import get_or_404, serialize, serialize_many

router = APIRouter(tags=["conditions"])


@router.get("/patients/{patient_id}/conditions", summary="List a patient's problems/diagnoses")
def list_conditions(
    patient_id: str,
    session: Session = Depends(get_session),
    clinical_status: Optional[str] = Query(None, description="active | resolved | ..."),
    category: Optional[str] = Query(None, description="problem-list-item | encounter-diagnosis"),
) -> list[dict]:
    get_or_404(session, Patient, patient_id, "Patient")
    stmt = select(Condition).where(Condition.patient_id == patient_id)
    if clinical_status:
        stmt = stmt.where(Condition.clinical_status == clinical_status)
    if category:
        stmt = stmt.where(Condition.category == category)
    return serialize_many(session.exec(stmt).all())


@router.get("/conditions/{condition_id}", summary="Get one condition")
def get_condition(condition_id: str, session: Session = Depends(get_session), include_raw: bool = False) -> dict:
    return serialize(get_or_404(session, Condition, condition_id, "Condition"), include_raw)


@router.post("/conditions", status_code=201, summary="Add a problem/diagnosis")
def create_condition(body: ConditionCreate, session: Session = Depends(get_session)) -> dict:
    cond = Condition(
        id=new_id(),
        patient_id=body.patient_id,
        encounter_id=body.encounter_id,
        code=body.code,
        display=body.display,
        category=body.category.value,
        clinical_status=body.clinical_status.value,
        verification_status="confirmed",
        recorded_date=utcnow(),
    )
    session.add(cond)
    session.commit()
    session.refresh(cond)
    return serialize(cond)


@router.patch("/conditions/{condition_id}", summary="Update / resolve a condition")
def update_condition(condition_id: str, body: ConditionUpdate, session: Session = Depends(get_session)) -> dict:
    cond = get_or_404(session, Condition, condition_id, "Condition")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(cond, key, value)
    cond.updated_at = utcnow()
    session.add(cond)
    session.commit()
    session.refresh(cond)
    return serialize(cond)
