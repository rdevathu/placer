"""Placer Ops — a cross-patient view of what Placer is doing.

There is no dedicated event-log table (see CLAUDE.md: the Placer domain lives
in native tables — dispo_assessments, care_tasks, communications,
placer_messages). This module synthesizes a monitoring dashboard by reading
those tables directly, without introducing new persisted state. Because
care_tasks has no per-transition history, a task's activity-feed timestamp is
its ``updated_at`` — it surfaces once at its latest state, not once per status
change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..db import get_session
from ..models import CareTask, Communication, DispoAssessment, Encounter, Patient, PlacerMessage
from ._common import serialize

router = APIRouter(prefix="/placer", tags=["placer-ops"])

_OPEN_TASK_STATUSES = ("pending", "in_progress", "blocked")


def _patient_label(p: Patient) -> dict:
    return {"patient_id": p.id, "patient_name": p.full_name, "mrn": p.mrn}


@router.get(
    "/overview",
    summary="Placer monitoring dashboard summary",
    description=(
        "Aggregate counts plus a per-patient summary of what Placer is currently "
        "watching: active inpatients, open/blocked care tasks, logged outreach, "
        "and each monitored patient's current predicted disposition. This is the "
        "top-level snapshot for a 'what is Placer doing' dashboard."
    ),
)
def overview(session: Session = Depends(get_session)) -> dict:
    patients_by_id = {p.id: p for p in session.exec(select(Patient)).all()}

    active_encounter_patient_ids = {
        e.patient_id for e in session.exec(select(Encounter).where(Encounter.status == "in-progress")).all()
    }

    current_dispo_rows = session.exec(
        select(DispoAssessment).where(DispoAssessment.is_current == True)  # noqa: E712
    ).all()
    current_dispo_by_patient = {d.patient_id: d for d in current_dispo_rows}

    tasks_by_patient: dict[str, list[CareTask]] = {}
    tasks_by_status: dict[str, int] = {}
    for t in session.exec(select(CareTask)).all():
        tasks_by_patient.setdefault(t.patient_id, []).append(t)
        tasks_by_status[t.status] = tasks_by_status.get(t.status, 0) + 1

    comms_by_patient: dict[str, list[Communication]] = {}
    total_comms = 0
    for c in session.exec(select(Communication)).all():
        comms_by_patient.setdefault(c.patient_id, []).append(c)
        total_comms += 1

    dispositions_current: dict[str, int] = {}
    for d in current_dispo_rows:
        dispositions_current[d.predicted_disposition] = dispositions_current.get(d.predicted_disposition, 0) + 1

    monitored_ids = active_encounter_patient_ids | set(current_dispo_by_patient) | set(tasks_by_patient)

    patient_summaries = []
    for pid in monitored_ids:
        p = patients_by_id.get(pid)
        if p is None:
            continue
        p_tasks = tasks_by_patient.get(pid, [])
        p_comms = comms_by_patient.get(pid, [])
        open_tasks = [t for t in p_tasks if t.status in _OPEN_TASK_STATUSES]
        dispo = current_dispo_by_patient.get(pid)

        candidates = [t.updated_at for t in p_tasks] + [c.occurred_at or c.created_at for c in p_comms]
        if dispo is not None:
            candidates.append(dispo.created_at)
        last_activity_at = max(candidates) if candidates else None

        patient_summaries.append(
            {
                **_patient_label(p),
                "encounter_active": pid in active_encounter_patient_ids,
                "current_disposition": serialize(dispo) if dispo else None,
                "open_tasks": len(open_tasks),
                "blocked_tasks": sum(1 for t in open_tasks if t.status == "blocked"),
                "high_priority_open_tasks": sum(1 for t in open_tasks if t.priority == "high"),
                "communications_count": len(p_comms),
                "last_activity_at": last_activity_at,
            }
        )
    patient_summaries.sort(key=lambda row: row["last_activity_at"] or datetime.min, reverse=True)

    return {
        "counts": {
            "monitored_patients": len(monitored_ids),
            "active_inpatients": len(active_encounter_patient_ids),
            "open_tasks": sum(tasks_by_status.get(s, 0) for s in _OPEN_TASK_STATUSES),
            "blocked_tasks": tasks_by_status.get("blocked", 0),
            "completed_tasks": tasks_by_status.get("completed", 0),
            "communications_logged": total_comms,
        },
        "tasks_by_status": tasks_by_status,
        "dispositions_current": dispositions_current,
        "patients": patient_summaries,
    }


@router.get(
    "/activity",
    summary="Unified cross-patient activity feed",
    description=(
        "Merges disposition predictions, care-task changes, logged communications, "
        "and Placer's own chat messages into one chronological feed — the closest "
        "thing to an audit trail of what Placer has done and is doing. Sorted "
        "newest first; filter by patient_id and/or event_type."
    ),
)
def activity(
    session: Session = Depends(get_session),
    patient_id: Optional[str] = None,
    event_type: Optional[str] = Query(
        None, description="dispo_assessment | care_task | communication | chat_message"
    ),
    limit: int = Query(50, le=500),
    offset: int = 0,
) -> list[dict]:
    patients_by_id = {p.id: p for p in session.exec(select(Patient)).all()}
    events: list[dict] = []

    def label(pid: str) -> dict:
        p = patients_by_id.get(pid)
        return {"patient_id": pid, "patient_name": p.full_name if p else None, "patient_mrn": p.mrn if p else None}

    if event_type in (None, "dispo_assessment"):
        stmt = select(DispoAssessment)
        if patient_id:
            stmt = stmt.where(DispoAssessment.patient_id == patient_id)
        for d in session.exec(stmt).all():
            confidence_text = f"{round(d.confidence * 100)}% confidence" if d.confidence is not None else "confidence unknown"
            events.append(
                {
                    "id": f"dispo:{d.id}",
                    "event_type": "dispo_assessment",
                    "occurred_at": d.created_at,
                    **label(d.patient_id),
                    "title": f"Predicted disposition: {d.predicted_disposition} ({confidence_text})",
                    "detail": d.rationale,
                    "status": "current" if d.is_current else "superseded",
                    "meta": {
                        "predicted_disposition": d.predicted_disposition,
                        "confidence": d.confidence,
                        "barriers": d.barriers,
                        "alternatives": d.alternatives,
                        "assessed_by": d.assessed_by,
                        "is_current": d.is_current,
                    },
                }
            )

    if event_type in (None, "care_task"):
        stmt = select(CareTask)
        if patient_id:
            stmt = stmt.where(CareTask.patient_id == patient_id)
        for t in session.exec(stmt).all():
            events.append(
                {
                    "id": f"task:{t.id}",
                    "event_type": "care_task",
                    "occurred_at": t.updated_at,
                    **label(t.patient_id),
                    "title": t.title,
                    "detail": t.result_summary or t.description,
                    "status": t.status,
                    "meta": {
                        "task_type": t.task_type,
                        "priority": t.priority,
                        "assigned_to": t.assigned_to,
                        "due_at": t.due_at,
                        "completed_at": t.completed_at,
                    },
                }
            )

    if event_type in (None, "communication"):
        stmt = select(Communication)
        if patient_id:
            stmt = stmt.where(Communication.patient_id == patient_id)
        for c in session.exec(stmt).all():
            who = c.party_name or c.party_type or "an unknown party"
            verb = "Called" if c.modality == "phone" else "Contacted"
            events.append(
                {
                    "id": f"comm:{c.id}",
                    "event_type": "communication",
                    "occurred_at": c.occurred_at or c.created_at,
                    **label(c.patient_id),
                    "title": f"{verb} {who}",
                    "detail": c.summary,
                    "status": c.outcome,
                    "meta": {
                        "direction": c.direction,
                        "modality": c.modality,
                        "party_type": c.party_type,
                        "party_name": c.party_name,
                        "outcome": c.outcome,
                    },
                }
            )

    if event_type in (None, "chat_message"):
        stmt = select(PlacerMessage).where(PlacerMessage.sender == "placer")
        if patient_id:
            stmt = stmt.where(PlacerMessage.patient_id == patient_id)
        for m in session.exec(stmt).all():
            events.append(
                {
                    "id": f"chat:{m.id}",
                    "event_type": "chat_message",
                    "occurred_at": m.created_at,
                    **label(m.patient_id),
                    "title": "Placer sent a chat message",
                    "detail": m.text,
                    "status": None,
                    "meta": {"sender_name": m.sender_name},
                }
            )

    events.sort(key=lambda e: e["occurred_at"], reverse=True)
    return events[offset : offset + limit]
