"""Human-decision actions the chat/API layer invokes on the brain.

These implement the frozen cross-boundary contract in engine/INTERFACES.md —
2c imports exactly these four functions. Each commits its own transaction and
marks the case dirty so the loop reassesses soon after a human acts.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from placer import state
from placer.models import Approval, Barrier, Case, DispoTask, Referral, utcnow
from placer.registry import load_pathways

from . import router_logic
from .chatlink import post_chat

_OPEN_TASK_STATUSES = ("suggested", "pending", "approved", "in_progress", "waiting")
_OPEN_BARRIER_STATUSES = ("open", "in_progress", "blocked")
_TERMINAL_REFERRAL_STATUSES = ("declined",)


def _get_case(session: Session, case_id: str) -> Case:
    case = session.get(Case, case_id)
    if case is None:
        raise ValueError(f"No case '{case_id}'")
    return case


def _mark_dirty(case: Case) -> None:
    case.dirty = True
    case.updated_at = utcnow()


def commit_pathway(session: Session, case_id: str, pathway_id: int, resolved_by: str) -> dict:
    """Team decision. Applies 'commit' transition, runs trump() pruning,
    rebuilds the plan for the decided pathway, marks APPROVAL-mode plan tasks
    status='approved' (the batch card that invoked this covered them),
    marks the case dirty. Returns {'state', 'kept', 'cancelled', 'created'}."""
    case = _get_case(session, case_id)
    case.state = state.apply_transition(case.state, "commit")

    tasks = session.exec(
        select(DispoTask).where(DispoTask.case_id == case.id, DispoTask.status.in_(_OPEN_TASK_STATUSES))  # type: ignore[attr-defined]
    ).all()
    referrals = [
        r for r in session.exec(select(Referral).where(Referral.case_id == case.id)).all()
        if r.status not in _TERMINAL_REFERRAL_STATUSES
    ]
    barriers = session.exec(
        select(Barrier).where(Barrier.case_id == case.id, Barrier.status.in_(_OPEN_BARRIER_STATUSES))  # type: ignore[attr-defined]
    ).all()

    keep_ids, cancel_ids = state.trump(
        [{"id": t.id, "pathway_ids": t.pathway_ids} for t in tasks],
        [{"id": r.id, "pathway_ids": [r.pathway_id]} for r in referrals],
        [{"id": b.id, "pathway_ids": b.pathway_ids} for b in barriers],
        pathway_id,
    )
    cancel = set(cancel_ids)

    for t in tasks:
        if t.id in cancel:
            t.status = "cancelled"
            t.updated_at = utcnow()
        elif t.mode == "approval" and t.status == "suggested":
            # Kept plan work is covered by the batch approval that committed us.
            t.status = "approved"
            t.updated_at = utcnow()
        session.add(t)
    for r in referrals:
        if r.id in cancel:
            # Referral status vocabulary has no 'cancelled'; the status stays
            # and the pruning is recorded as a note (the facility may still
            # answer — the note tells workers to stand down).
            r.notes = ((r.notes + "\n") if r.notes else "") + \
                f"Cancelled on commit to pathway {pathway_id} by {resolved_by}."
            r.updated_at = utcnow()
            session.add(r)
    for b in barriers:
        if b.id in cancel:
            b.status = "cleared"
            b.evidence = ((b.evidence + "\n") if b.evidence else "") + \
                f"Pathway trumped on commit to {pathway_id}."
            b.updated_at = utcnow()
            session.add(b)
        elif b.dimension == "decision":
            # The commit IS the decision — clear the decision dimension.
            b.status = "cleared"
            b.evidence = ((b.evidence + "\n") if b.evidence else "") + \
                f"Pathway {pathway_id} committed by {resolved_by}."
            b.updated_at = utcnow()
            session.add(b)

    # Resolve the pending commit-proposal card, if one exists.
    for a in session.exec(
        select(Approval).where(Approval.case_id == case.id, Approval.kind == "batch", Approval.status == "pending")
    ).all():
        a.status = "approved"
        a.resolved_by = resolved_by
        a.resolved_at = utcnow()
        session.add(a)

    case.active_pathways = [{"pathway_id": pathway_id, "confidence": 1.0}]
    _mark_dirty(case)
    session.add(case)
    session.commit()

    # Rebuild the plan for the single committed pathway; APPROVAL tasks in the
    # committed plan are created 'approved' directly by persist_plan.
    open_barriers = session.exec(
        select(Barrier).where(Barrier.case_id == case.id, Barrier.status.in_(_OPEN_BARRIER_STATUSES))  # type: ignore[attr-defined]
    ).all()
    specs = router_logic.build_plan(session, case, open_barriers, case.active_pathways)
    persisted = router_logic.persist_plan(session, case, specs)

    name = load_pathways().get(pathway_id, {}).get("name", f"pathway {pathway_id}")
    post_chat(
        session,
        f"Pathway committed: {name} (by {resolved_by}). "
        f"Pruned {len(cancel)} item(s); working the committed plan now.",
        case_id=case.id,
        kind="notification",
    )
    session.commit()

    return {
        "state": case.state,
        "kept": keep_ids,
        "cancelled": sorted(cancel),
        "created": persisted["created"],
    }


def approve_tasks(session: Session, task_ids: list, resolved_by: str) -> dict:
    """Suggested-card approval: tasks -> status 'approved', mark case dirty."""
    approved: list = []
    case_ids: set = set()
    for tid in task_ids:
        task = session.get(DispoTask, tid)
        if task is None or task.status not in ("suggested", "pending"):
            continue
        task.status = "approved"
        task.updated_at = utcnow()
        session.add(task)
        approved.append(task.id)
        case_ids.add(task.case_id)
    for cid in case_ids:
        case = session.get(Case, cid)
        if case is not None:
            _mark_dirty(case)
            session.add(case)
    session.commit()
    return {"approved": approved, "resolved_by": resolved_by}


def reject_approval(session: Session, approval_id: str, resolved_by: str) -> dict:
    """Approval -> 'rejected'; linked tasks -> 'cancelled'."""
    approval = session.get(Approval, approval_id)
    if approval is None:
        raise ValueError(f"No approval '{approval_id}'")
    approval.status = "rejected"
    approval.resolved_by = resolved_by
    approval.resolved_at = utcnow()
    session.add(approval)

    # task_ids is usually a plain list; the batch commit-proposal card stores
    # {"pathway_id": X, "task_ids": [...]} (see pipeline._ensure_commit_proposal).
    raw = approval.task_ids or []
    ids = raw.get("task_ids", []) if isinstance(raw, dict) else raw
    cancelled: list = []
    for tid in ids:
        task = session.get(DispoTask, tid)
        if task is None or task.status in ("done", "failed", "cancelled"):
            continue
        task.status = "cancelled"
        task.updated_at = utcnow()
        session.add(task)
        cancelled.append(task.id)
    session.commit()
    return {"approval_id": approval_id, "cancelled": cancelled, "resolved_by": resolved_by}


def reassess_case(session: Session, case_id: str) -> None:
    """Mark case dirty so the loop reassesses soon (used by chat Intake)."""
    case = _get_case(session, case_id)
    _mark_dirty(case)
    session.add(case)
    session.commit()
