"""Readiness-board assembly for one case.

Shared by the chat API (``GET /cases/{id}/board``) and the brain's chat
responder (``placer.brain.respond``) so both ground themselves in exactly the
same case data. Pure reads — no writes, no LLM.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .models import Approval, Barrier, Case, ChatMessage, DispoTask, Referral
from .registry import load_pathways
from .state import derive_readiness

TASK_GROUPS = [
    "suggested",
    "pending",
    "approved",
    "in_progress",
    "waiting",
    "done",
    "failed",
    "cancelled",
]


def message_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "case_id": m.case_id,
        "author": m.author,
        "kind": m.kind,
        "content": m.content,
        "approval_id": m.approval_id,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def named_pathways(active: Optional[list]) -> list:
    catalog = load_pathways()
    out = []
    for entry in active or []:
        pid = entry.get("pathway_id")
        info = catalog.get(pid, {})
        out.append(
            {
                "pathway_id": pid,
                "confidence": entry.get("confidence"),
                "name": info.get("name", f"Pathway {pid}"),
            }
        )
    return out


def build_board(session: Session, case: Case, message_limit: int = 20) -> dict:
    """The full readiness board for one case (barriers by dimension, tasks by
    status, referrals, pending approvals, recent messages oldest-first)."""
    barriers = session.exec(select(Barrier).where(Barrier.case_id == case.id)).all()
    tasks = session.exec(select(DispoTask).where(DispoTask.case_id == case.id)).all()
    referrals = session.exec(select(Referral).where(Referral.case_id == case.id)).all()
    approvals = session.exec(
        select(Approval).where(Approval.case_id == case.id, Approval.status == "pending")
    ).all()
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.case_id == case.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(message_limit)
    ).all()

    readiness = derive_readiness(
        [{"dimension": b.dimension, "status": b.status} for b in barriers],
        case.state,
    )

    barriers_by_dim: dict = {}
    for b in barriers:
        barriers_by_dim.setdefault(b.dimension, []).append(
            {
                "id": b.id,
                "btype": b.btype,
                "status": b.status,
                "description": b.description,
                "pathway_ids": b.pathway_ids,
            }
        )

    tasks_by_status: dict = {g: [] for g in TASK_GROUPS}
    for t in tasks:
        tasks_by_status.setdefault(t.status, []).append(
            {
                "id": t.id,
                "title": t.title,
                "action_id": t.action_id,
                "mode": t.mode,
                "task_type": t.task_type,
                "pathway_ids": t.pathway_ids,
            }
        )

    return {
        "id": case.id,
        "patient_id": case.patient_id,
        "encounter_id": case.encounter_id,
        "state": case.state,
        "brief": case.brief,
        "dirty": case.dirty,
        "next_review_at": case.next_review_at.isoformat() if case.next_review_at else None,
        "active_pathways": named_pathways(case.active_pathways),
        "readiness": readiness,
        "barriers": barriers_by_dim,
        "tasks": tasks_by_status,
        "referrals": [
            {
                "id": r.id,
                "facility_name": r.facility_name,
                "pathway_id": r.pathway_id,
                "status": r.status,
                "denial_reason": r.denial_reason,
            }
            for r in referrals
        ],
        "approvals": [
            {"id": a.id, "kind": a.kind, "prompt": a.prompt} for a in approvals
        ],
        "messages": [message_dict(m) for m in reversed(messages)],
    }
