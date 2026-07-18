"""Disposition assessments and facility placement search."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import DispoAssessment, Facility, Patient
from ..models.base import new_id, utcnow
from ..schemas import DispoAssessmentCreate, FacilityCreate, FacilityUpdate
from ._common import get_or_404, serialize, serialize_many

router = APIRouter(tags=["disposition"])


# --- Disposition assessments (predictions over time) -----------------------


@router.get("/patients/{patient_id}/dispo-assessments", summary="History of disposition predictions")
def list_dispo(patient_id: str, session: Session = Depends(get_session)) -> list[dict]:
    get_or_404(session, Patient, patient_id, "Patient")
    rows = session.exec(
        select(DispoAssessment)
        .where(DispoAssessment.patient_id == patient_id)
        .order_by(DispoAssessment.created_at.desc())
    ).all()
    return serialize_many(rows)


@router.get(
    "/patients/{patient_id}/dispo-assessments/current",
    summary="Current (latest) disposition prediction",
)
def current_dispo(patient_id: str, session: Session = Depends(get_session)) -> Optional[dict]:
    get_or_404(session, Patient, patient_id, "Patient")
    row = session.exec(
        select(DispoAssessment).where(
            DispoAssessment.patient_id == patient_id, DispoAssessment.is_current == True  # noqa: E712
        )
    ).first()
    return serialize(row) if row else None


@router.post(
    "/dispo-assessments",
    status_code=201,
    summary="Post a disposition prediction",
    description=(
        "Records a new predicted disposition with rationale, confidence, and "
        "barriers. Automatically supersedes the patient's previous current "
        "assessment (sets its is_current=false), preserving the full history."
    ),
)
def create_dispo(body: DispoAssessmentCreate, session: Session = Depends(get_session)) -> dict:
    # Supersede prior current assessment for this patient.
    prior = session.exec(
        select(DispoAssessment).where(
            DispoAssessment.patient_id == body.patient_id, DispoAssessment.is_current == True  # noqa: E712
        )
    ).all()
    for p in prior:
        p.is_current = False
        session.add(p)

    row = DispoAssessment(
        id=new_id(),
        patient_id=body.patient_id,
        encounter_id=body.encounter_id,
        predicted_disposition=body.predicted_disposition.value,
        confidence=body.confidence,
        rationale=body.rationale,
        barriers=body.barriers,
        alternatives=body.alternatives,
        assessed_by=body.assessed_by,
        is_current=True,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return serialize(row)


# --- Facilities (placement options) ----------------------------------------


@router.get(
    "/facilities",
    summary="Search post-acute facilities",
    description="Find SNFs/rehab/LTAC/hospice/etc for placement. Filter by type, state, bed availability, and COVID-positive acceptance.",
)
def list_facilities(
    session: Session = Depends(get_session),
    facility_type: Optional[str] = Query(None, description="snf | assisted_living | inpatient_rehab | ltac | hospice | home_health | dme"),
    state: Optional[str] = None,
    has_available_beds: Optional[bool] = Query(None, description="If true, only facilities with available_beds > 0"),
    accepts_covid_positive: Optional[bool] = None,
) -> list[dict]:
    stmt = select(Facility)
    if facility_type:
        stmt = stmt.where(Facility.facility_type == facility_type)
    if state:
        stmt = stmt.where(Facility.state == state)
    if has_available_beds:
        stmt = stmt.where(Facility.available_beds > 0)
    if accepts_covid_positive is not None:
        stmt = stmt.where(Facility.accepts_covid_positive == accepts_covid_positive)
    return serialize_many(session.exec(stmt).all())


@router.get("/facilities/{facility_id}", summary="Get one facility")
def get_facility(facility_id: str, session: Session = Depends(get_session)) -> dict:
    return serialize(get_or_404(session, Facility, facility_id, "Facility"))


@router.post("/facilities", status_code=201, summary="Add a facility")
def create_facility(body: FacilityCreate, session: Session = Depends(get_session)) -> dict:
    fac = Facility(
        id=new_id(),
        name=body.name,
        facility_type=body.facility_type.value,
        city=body.city,
        state=body.state,
        phone=body.phone,
        total_beds=body.total_beds,
        available_beds=body.available_beds,
        accepts_covid_positive=body.accepts_covid_positive,
        accepts_medicaid=body.accepts_medicaid,
        specialties=body.specialties,
    )
    session.add(fac)
    session.commit()
    session.refresh(fac)
    return serialize(fac)


@router.patch(
    "/facilities/{facility_id}",
    summary="Update a facility (e.g. bed count after a call)",
    description="Agents update available_beds and notes after calling a facility's admissions desk.",
)
def update_facility(facility_id: str, body: FacilityUpdate, session: Session = Depends(get_session)) -> dict:
    fac = get_or_404(session, Facility, facility_id, "Facility")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(fac, key, value)
    fac.updated_at = utcnow()
    session.add(fac)
    session.commit()
    session.refresh(fac)
    return serialize(fac)
