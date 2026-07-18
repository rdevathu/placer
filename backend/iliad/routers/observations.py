"""Vitals, labs, and diagnostic reports.

Vitals and labs share the ``observations`` table (discriminated by category) but
are exposed through separate, patient-scoped endpoints so agents never pull an
unbounded firehose. The flagship filter is ``/patients/{id}/labs?status=pending``
— the "what am I still waiting on" list at the heart of the dispo workflow.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..db import get_session
from ..events import get_actor, record_event
from ..models import DiagnosticReport, Observation, Patient
from ..models.base import new_id, utcnow
from ..schemas import LabResultUpdate, ObservationCreate
from ._common import get_or_404, serialize, serialize_many

router = APIRouter(tags=["observations"])

# Agent-friendly aliases -> stored status values.
_LAB_STATUS_ALIASES = {"resulted": "final", "final": "final", "pending": "pending", "cancelled": "cancelled"}


def _lab_resulted_event(session: Session, obs: Observation, actor: str) -> None:
    """Announce a completed lab result on the event feed so the Placer engine
    reacts to it. Only *final* laboratory results are material — pending orders
    and routine vitals stay off the feed to keep it signal-dense. A normal
    result matters too (it can clear a barrier), so we do not gate on abnormal."""
    if obs.category != "laboratory" or obs.status != "final":
        return
    record_event(
        session,
        "observation.resulted",
        patient_id=obs.patient_id,
        actor=actor,
        entity_type="observation",
        entity_id=obs.id,
        payload={
            "display": obs.display,
            "value_num": obs.value_num,
            "value_unit": obs.value_unit,
            "value_string": obs.value_string,
            "abnormal_flag": obs.abnormal_flag,
        },
    )


@router.get("/patients/{patient_id}/vitals", summary="List a patient's vitals")
def list_vitals(
    patient_id: str,
    session: Session = Depends(get_session),
    code: Optional[str] = Query(None, description="LOINC code filter"),
    limit: int = Query(100, le=1000),
    offset: int = 0,
) -> list[dict]:
    get_or_404(session, Patient, patient_id, "Patient")
    stmt = select(Observation).where(
        Observation.patient_id == patient_id, Observation.category == "vital-signs"
    )
    if code:
        stmt = stmt.where(Observation.loinc_code == code)
    rows = session.exec(stmt.order_by(Observation.effective_time.desc()).offset(offset).limit(limit)).all()
    return serialize_many(rows)


@router.get(
    "/patients/{patient_id}/labs",
    summary="List a patient's labs (filter by pending vs resulted)",
    description=(
        "Returns laboratory observations. `status=pending` returns ordered labs "
        "with no result yet (e.g. an SNF-required COVID test in flight); "
        "`status=resulted` (alias for `final`) returns completed results."
    ),
)
def list_labs(
    patient_id: str,
    session: Session = Depends(get_session),
    status: Optional[str] = Query(None, description="pending | resulted | cancelled"),
    code: Optional[str] = Query(None, description="LOINC code filter"),
    limit: int = Query(200, le=1000),
    offset: int = 0,
) -> list[dict]:
    get_or_404(session, Patient, patient_id, "Patient")
    stmt = select(Observation).where(
        Observation.patient_id == patient_id, Observation.category == "laboratory"
    )
    if status:
        stmt = stmt.where(Observation.status == _LAB_STATUS_ALIASES.get(status, status))
    if code:
        stmt = stmt.where(Observation.loinc_code == code)
    rows = session.exec(stmt.order_by(Observation.effective_time.desc()).offset(offset).limit(limit)).all()
    return serialize_many(rows)


@router.get("/observations/{observation_id}", summary="Get one observation", tags=["observations"])
def get_observation(observation_id: str, session: Session = Depends(get_session), include_raw: bool = False) -> dict:
    return serialize(get_or_404(session, Observation, observation_id, "Observation"), include_raw)


@router.post("/observations", status_code=201, summary="Record an observation (vital or lab)", tags=["observations"])
def create_observation(
    body: ObservationCreate,
    session: Session = Depends(get_session),
    actor: str = Depends(get_actor),
) -> dict:
    obs = Observation(
        id=new_id(),
        patient_id=body.patient_id,
        encounter_id=body.encounter_id,
        category=body.category.value,
        loinc_code=body.loinc_code,
        display=body.display,
        value_num=body.value_num,
        value_unit=body.value_unit,
        value_string=body.value_string,
        status=body.status.value,
        effective_time=utcnow(),
    )
    session.add(obs)
    _lab_resulted_event(session, obs, actor)  # only fires for a final laboratory result
    session.commit()
    session.refresh(obs)
    return serialize(obs)


@router.post(
    "/labs/{observation_id}/result",
    summary="Result a pending lab",
    description="Sets a pending lab's value and marks it final. Also completes the ordering Order if one is linked.",
    tags=["observations"],
)
def result_lab(
    observation_id: str,
    body: LabResultUpdate,
    session: Session = Depends(get_session),
    actor: str = Depends(get_actor),
) -> dict:
    from ..models import Order

    obs = get_or_404(session, Observation, observation_id, "Observation")
    now = utcnow()
    obs.value_num = body.value_num
    obs.value_unit = body.value_unit
    obs.value_string = body.value_string
    obs.abnormal_flag = body.abnormal_flag
    obs.status = body.status.value
    obs.issued_time = now
    obs.updated_at = now
    session.add(obs)
    _lab_resulted_event(session, obs, actor)  # tell the engine a result landed

    # Complete a linked order, if any.
    order = session.exec(select(Order).where(Order.result_observation_id == observation_id)).first()
    if order and order.status == "signed":
        order.status = "completed"
        order.completed_at = now
        order.updated_at = now
        session.add(order)

    session.commit()
    session.refresh(obs)
    return serialize(obs)


@router.get("/patients/{patient_id}/diagnostic-reports", summary="List a patient's lab panels", tags=["observations"])
def list_reports(patient_id: str, session: Session = Depends(get_session), limit: int = Query(100, le=500), offset: int = 0) -> list[dict]:
    get_or_404(session, Patient, patient_id, "Patient")
    rows = session.exec(
        select(DiagnosticReport)
        .where(DiagnosticReport.patient_id == patient_id)
        .order_by(DiagnosticReport.effective_time.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return serialize_many(rows)


@router.get(
    "/diagnostic-reports/{report_id}",
    summary="Get a lab panel with its result observations",
    tags=["observations"],
)
def get_report(report_id: str, session: Session = Depends(get_session), include_raw: bool = False) -> dict:
    report = get_or_404(session, DiagnosticReport, report_id, "DiagnosticReport")
    results = session.exec(
        select(Observation).where(Observation.diagnostic_report_id == report_id)
    ).all()
    data = serialize(report, include_raw)
    data["results"] = serialize_many(results, include_raw)
    return data
