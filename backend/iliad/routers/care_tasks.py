"""Care tasks — the disposition-planning worklist agents create and work."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..db import get_session
from ..events import get_actor, record_event
from ..models import CareTask
from ..models.base import new_id, utcnow
from ..schemas import CareTaskCreate, CareTaskUpdate
from ._common import get_or_404, serialize, serialize_many

router = APIRouter(prefix="/care-tasks", tags=["care-tasks"])


@router.get("", summary="List care tasks (the dispo worklist)")
def list_tasks(
    session: Session = Depends(get_session),
    patient_id: Optional[str] = None,
    status: Optional[str] = Query(None, description="pending | in_progress | blocked | completed | cancelled"),
    task_type: Optional[str] = Query(None, description="call_snf | call_family | order_lab | draft_consult | ..."),
    assigned_to: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
) -> list[dict]:
    stmt = select(CareTask)
    if patient_id:
        stmt = stmt.where(CareTask.patient_id == patient_id)
    if status:
        stmt = stmt.where(CareTask.status == status)
    if task_type:
        stmt = stmt.where(CareTask.task_type == task_type)
    if assigned_to:
        stmt = stmt.where(CareTask.assigned_to == assigned_to)
    rows = session.exec(stmt.order_by(CareTask.created_at.desc()).offset(offset).limit(limit)).all()
    return serialize_many(rows)


@router.get("/{task_id}", summary="Get one care task")
def get_task(task_id: str, session: Session = Depends(get_session)) -> dict:
    return serialize(get_or_404(session, CareTask, task_id, "CareTask"))


@router.post("", status_code=201, summary="Create a care task")
def create_task(
    body: CareTaskCreate,
    session: Session = Depends(get_session),
    actor: str = Depends(get_actor),
) -> dict:
    task = CareTask(
        id=new_id(),
        patient_id=body.patient_id,
        encounter_id=body.encounter_id,
        task_type=body.task_type.value,
        title=body.title,
        description=body.description,
        status=body.status.value,
        priority=body.priority,
        assigned_to=body.assigned_to,
        due_at=body.due_at,
        related_facility_id=body.related_facility_id,
        related_order_id=body.related_order_id,
    )
    session.add(task)
    record_event(
        session,
        "care_task.created",
        patient_id=task.patient_id,
        actor=actor,
        entity_type="care_task",
        entity_id=task.id,
        payload={"task_type": task.task_type, "status": task.status, "title": task.title},
    )
    session.commit()
    session.refresh(task)
    return serialize(task)


@router.patch(
    "/{task_id}",
    summary="Update a care task (status, result)",
    description="Move a task through pending -> in_progress -> completed and record the result_summary (e.g. the outcome of a call).",
)
def update_task(
    task_id: str,
    body: CareTaskUpdate,
    session: Session = Depends(get_session),
    actor: str = Depends(get_actor),
) -> dict:
    task = get_or_404(session, CareTask, task_id, "CareTask")
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(task, key, value)
    if updates.get("status") in ("completed", "cancelled") and task.completed_at is None:
        task.completed_at = utcnow()
    task.updated_at = utcnow()
    session.add(task)
    record_event(
        session,
        "care_task.updated",
        patient_id=task.patient_id,
        actor=actor,
        entity_type="care_task",
        entity_id=task.id,
        payload={"task_type": task.task_type, "status": task.status, "updated_fields": sorted(updates.keys())},
    )
    session.commit()
    session.refresh(task)
    return serialize(task)
