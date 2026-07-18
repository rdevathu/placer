"""Patient endpoints, including the ``/chart`` aggregate an agent hits first."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import Session, select

from ..db import get_session
from ..events import get_actor, record_event
from ..models import (
    CareTask,
    Condition,
    DispoAssessment,
    Encounter,
    Medication,
    Note,
    Observation,
    Order,
    Patient,
)
from ..models.base import new_id, utcnow
from ..schemas import PatientCreate, PatientUpdate
from ._common import age_years, get_or_404, serialize, serialize_many

router = APIRouter(prefix="/patients", tags=["patients"])


def _patient_out(p: Patient, include_raw: bool = False) -> dict:
    data = serialize(p, include_raw)
    data["age"] = age_years(p.birth_date)
    return data


@router.get(
    "",
    summary="List / search patients",
    description=(
        "Returns patients with computed age. Use `admitted=true` to get the "
        "inpatient worklist — patients with an active (in-progress) encounter, "
        "which is the cohort the disposition agents work on."
    ),
)
def list_patients(
    session: Session = Depends(get_session),
    q: Optional[str] = Query(None, description="Case-insensitive match on name or MRN"),
    admitted: Optional[bool] = Query(None, description="If true, only patients with an active inpatient encounter"),
    limit: int = Query(50, le=500),
    offset: int = 0,
) -> list[dict]:
    stmt = select(Patient)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            func.lower(Patient.full_name).like(like) | func.lower(Patient.mrn).like(like)
        )
    if admitted:
        active_ids = select(Encounter.patient_id).where(Encounter.status == "in-progress")
        stmt = stmt.where(Patient.id.in_(active_ids))
    patients = session.exec(stmt.offset(offset).limit(limit)).all()
    return [_patient_out(p) for p in patients]


@router.get("/{patient_id}", summary="Get one patient")
def get_patient(
    patient_id: str,
    session: Session = Depends(get_session),
    include_raw: bool = False,
) -> dict:
    return _patient_out(get_or_404(session, Patient, patient_id, "Patient"), include_raw)


@router.get(
    "/{patient_id}/chart",
    summary="Aggregate chart snapshot",
    description=(
        "One call that returns everything an agent needs to reason about a "
        "patient: demographics, the active encounter, active problems, current "
        "medications, latest vitals (one per type), pending and abnormal labs, "
        "the current disposition assessment, and open care tasks. Designed to "
        "avoid many round-trips and to keep observation volume small."
    ),
)
def get_chart(patient_id: str, session: Session = Depends(get_session)) -> dict:
    patient = get_or_404(session, Patient, patient_id, "Patient")

    active_encounter = session.exec(
        select(Encounter)
        .where(Encounter.patient_id == patient_id, Encounter.status == "in-progress")
        .order_by(Encounter.period_start.desc())
    ).first()
    # Fall back to the most recent encounter if none active.
    if active_encounter is None:
        active_encounter = session.exec(
            select(Encounter).where(Encounter.patient_id == patient_id).order_by(Encounter.period_start.desc())
        ).first()

    problems = session.exec(
        select(Condition).where(
            Condition.patient_id == patient_id, Condition.clinical_status == "active"
        )
    ).all()

    meds = session.exec(
        select(Medication).where(Medication.patient_id == patient_id, Medication.status == "active")
    ).all()

    # Latest vital per LOINC code (keeps the payload small).
    vitals = session.exec(
        select(Observation)
        .where(Observation.patient_id == patient_id, Observation.category == "vital-signs")
        .order_by(Observation.effective_time.desc())
    ).all()
    latest_vitals: dict[str, Observation] = {}
    for v in vitals:
        key = v.loinc_code or v.display or v.id
        if key not in latest_vitals:
            latest_vitals[key] = v

    pending_labs = session.exec(
        select(Observation).where(
            Observation.patient_id == patient_id,
            Observation.category == "laboratory",
            Observation.status == "pending",
        )
    ).all()
    abnormal_labs = session.exec(
        select(Observation).where(
            Observation.patient_id == patient_id,
            Observation.category == "laboratory",
            Observation.abnormal_flag.in_(["H", "L", "critical"]),
        )
    ).all()

    dispo = session.exec(
        select(DispoAssessment).where(
            DispoAssessment.patient_id == patient_id, DispoAssessment.is_current == True  # noqa: E712
        )
    ).first()

    open_tasks = session.exec(
        select(CareTask).where(
            CareTask.patient_id == patient_id,
            CareTask.status.in_(["pending", "in_progress", "blocked"]),
        )
    ).all()

    open_orders = session.exec(
        select(Order).where(
            Order.patient_id == patient_id, Order.status.in_(["draft", "signed"])
        )
    ).all()

    return {
        "patient": _patient_out(patient),
        "active_encounter": serialize(active_encounter) if active_encounter else None,
        "active_problems": serialize_many(problems),
        "medications": serialize_many(meds),
        "latest_vitals": serialize_many(latest_vitals.values()),
        "pending_labs": serialize_many(pending_labs),
        "abnormal_labs": serialize_many(abnormal_labs),
        "current_disposition": serialize(dispo) if dispo else None,
        "open_care_tasks": serialize_many(open_tasks),
        "open_orders": serialize_many(open_orders),
    }


@router.post("", status_code=201, summary="Create a patient")
def create_patient(
    body: PatientCreate,
    session: Session = Depends(get_session),
    actor: str = Depends(get_actor),
) -> dict:
    from datetime import date

    count = session.exec(select(func.count()).select_from(Patient)).one()
    mrn = body.mrn or f"MRN{count + 1:04d}"
    birth = None
    if body.birth_date:
        try:
            birth = date.fromisoformat(body.birth_date)
        except ValueError:
            birth = None
    full = " ".join(x for x in [body.prefix, body.given_name, body.family_name] if x) or None
    patient = Patient(
        id=new_id(),
        mrn=mrn,
        family_name=body.family_name,
        given_name=body.given_name,
        prefix=body.prefix,
        full_name=full,
        gender=body.gender,
        birth_date=birth,
        marital_status=body.marital_status,
        language=body.language,
        city=body.city,
        state=body.state,
        living_situation=body.living_situation,
        code_status=body.code_status,
    )
    session.add(patient)
    record_event(
        session,
        "patient.created",
        patient_id=patient.id,
        actor=actor,
        entity_type="patient",
        entity_id=patient.id,
        payload={"mrn": patient.mrn, "full_name": patient.full_name},
    )
    session.commit()
    session.refresh(patient)
    return _patient_out(patient)


@router.patch("/{patient_id}", summary="Update patient demographics / social fields")
def update_patient(patient_id: str, body: PatientUpdate, session: Session = Depends(get_session)) -> dict:
    patient = get_or_404(session, Patient, patient_id, "Patient")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(patient, key, value)
    patient.updated_at = utcnow()
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return _patient_out(patient)
