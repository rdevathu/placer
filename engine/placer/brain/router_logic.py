"""The Router: pure deterministic planning from barriers to task specs.

``build_plan`` maps open barriers (plus the referral pipeline) onto task
templates — no LLM, no side effects beyond reads. ``persist_plan`` materializes
specs as DispoTask rows with idempotency-key dedupe and raises the human
approval surface (suggested-batch Approval + chat card) when needed.

Payload convention: DispoTask has no dedicated payload column (models.py is
frozen), so each task's structured parameters are stored as JSON in ``detail``.
The brain's executor decodes it onto ``task.payload`` before handing the task
to ``placer.workers.run_task``; use ``decode_payload`` anywhere else.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from placer import config
from placer.models import Approval, Barrier, Case, DispoTask, Referral
from placer.registry import load_pathways

from .chatlink import post_chat

logger = logging.getLogger(__name__)

# Pathways whose destination is a facility bed that must be found and won.
FACILITY_BOUND_PATHWAYS = {8, 11, 12, 14}

# Tasks that bind the hospital externally (submissions, holds, bookings) —
# never created before the team commits to a pathway.
BINDING_TASK_TYPES = {"submit_referral", "finalize_acceptance", "book_transport"}

COMMITTED_STATES = {"committed", "green", "transition"}

_OPEN_BARRIER_STATUSES = {"open", "in_progress", "blocked"}

# Referral status -> next call/action in the placement pipeline.
_REFERRAL_PROGRESSION = {
    "shortlisted": ("facility_intake_call", "approval", "FPR-003"),
    "intake_verified": ("facility_screen_call", "approval", "FPR-005"),
    "screened": ("submit_referral", "approval", "FPR-006"),
    "conditional": ("finalize_acceptance", "approval", "FPR-011"),
    "pending": ("finalize_acceptance", "approval", "FPR-011"),
}


@dataclass
class TaskSpec:
    """A planned unit of work, not yet persisted."""

    task_type: str
    mode: str  # "auto" | "approval"
    action_id: str
    title: str
    target: str  # idempotency-key discriminator: facility/order-type/pathway/"-"
    payload: dict = field(default_factory=dict)
    pathway_ids: Optional[list] = None  # None/[] = shared across pathways
    barrier_id: Optional[str] = None
    referral_id: Optional[str] = None


# Engine task_type -> Iliad CareTask TaskType (models/enums.py) for the
# worklist mirror shown in the EHR's Placer tab.
_EHR_TASK_TYPE = {
    "build_shortlist": "call_snf",
    "facility_intake_call": "call_snf",
    "facility_screen_call": "call_snf",
    "submit_referral": "call_snf",
    "finalize_acceptance": "call_snf",
    "preference_call": "call_family",
    "draft_order": "order_lab",
    "draft_consult": "draft_consult",
    "verify_benefits": "verify_eligibility",
    "book_transport": "arrange_transport",
    "chart_audit": "other",
    "message_team": "other",
}


def mirror_task_to_ehr(session: Session, case: Case, task: DispoTask) -> None:
    """Best-effort: create the matching EHR care task and remember its id in
    the task's detail JSON ('ehr_care_task_id') so the executor can complete it
    later. Mirror failure must NEVER break planning."""
    if not config.PLACER_MIRROR:
        return
    try:
        from placer.ehr_client import EHRClient

        client = EHRClient()
        try:
            ehr_task = client.create_care_task(
                patient_id=case.patient_id,
                task_type=_EHR_TASK_TYPE.get(task.task_type, "other"),
                title=task.title,
                encounter_id=case.encounter_id,
            )
        finally:
            client.close()
        payload = decode_payload(task)
        payload["ehr_care_task_id"] = ehr_task.get("id")
        task.detail = json.dumps(payload)
        session.add(task)
        session.commit()
    except Exception:
        logger.warning("router: EHR care-task mirror failed for task %s", task.id, exc_info=True)


def decode_payload(task: DispoTask) -> dict:
    """Recover the structured payload stored as JSON in ``detail``."""
    if not task.detail:
        return {}
    try:
        loaded = json.loads(task.detail)
        return loaded if isinstance(loaded, dict) else {}
    except (TypeError, ValueError):
        return {}


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in (text or "-").lower())[:40] or "-"


def _tags(barrier_pathway_ids: Optional[list], active_ids: list) -> Optional[list]:
    """Task pathway tags: barrier tags restricted to active pathways; shared
    (None) when the barrier is shared. Hedging = the union of tags across all
    the parallel active pathways a barrier blocks."""
    if not barrier_pathway_ids:
        return None
    tags = [p for p in barrier_pathway_ids if p in active_ids]
    return tags or list(barrier_pathway_ids)


def build_plan(session: Session, case: Case, barriers: list, active_pathways: list) -> List[TaskSpec]:
    """Deterministically map open barriers + the referral pipeline to TaskSpecs.

    Pure planning: reads referrals for the case, produces specs, mutates
    nothing. Ordering is shared-first (broadest pathway coverage earliest).
    """
    active_ids = [p.get("pathway_id") for p in (active_pathways or [])]
    committed = case.state in COMMITTED_STATES
    pathways = load_pathways()
    specs: List[TaskSpec] = []

    open_barriers = [b for b in barriers if getattr(b, "status", None) in _OPEN_BARRIER_STATUSES]
    saw_destination = False

    for b in open_barriers:
        tags = _tags(b.pathway_ids, active_ids)

        if b.btype == "bed_availability" or b.dimension == "destination":
            saw_destination = True  # handled below via the facility pipeline

        elif b.btype == "family_decision" or (b.dimension == "decision" and b.btype == "preference"):
            topics = [b.description or "discharge preferences"]
            topics.extend(pathways[p]["name"] for p in active_ids if p in pathways)
            specs.append(TaskSpec(
                task_type="preference_call", mode="approval", action_id="PFC-007",
                title="Call family to discuss preferences",
                target="-", payload={"topics": topics},
                pathway_ids=tags, barrier_id=b.id,
            ))

        elif b.btype == "pending_lab" and b.dimension == "clinical_docs":
            display = b.description or "lab panel"
            specs.append(TaskSpec(
                task_type="draft_order", mode="auto", action_id="CED-031",
                title=f"Draft lab order: {display}",
                target=_slug(display),
                payload={"order_type": "lab", "display": display, "detail": b.evidence},
                pathway_ids=tags, barrier_id=b.id,
            ))

        elif b.btype == "consult_needed" and b.dimension == "clinical_docs":
            consult = b.description or "consult"
            specs.append(TaskSpec(
                task_type="draft_consult", mode="auto", action_id="CED-013",
                title=f"Draft consult: {consult}",
                target=_slug(consult),
                payload={"consult": consult, "indication": b.evidence},
                pathway_ids=tags, barrier_id=b.id,
            ))

        elif b.btype == "insurance_auth" or b.dimension == "payer":
            specs.append(TaskSpec(
                task_type="verify_benefits", mode="auto", action_id="PBF-002",
                title="Verify benefits / payer coverage",
                target="-", payload={"pathway_ids": tags or active_ids},
                pathway_ids=tags, barrier_id=b.id,
            ))

        elif b.dimension == "transport":
            if committed:  # transport is only bookable once the pathway is decided
                specs.append(TaskSpec(
                    task_type="book_transport", mode="approval", action_id="TSH-020",
                    title="Book discharge transport",
                    target="-", payload={"detail": b.description},
                    pathway_ids=tags, barrier_id=b.id,
                ))

        elif b.dimension == "medical":
            # Medical readiness is team-owned; the agent can only ask.
            specs.append(TaskSpec(
                task_type="message_team", mode="auto", action_id="SGE-027",
                title="Ask team: medical readiness status",
                target=b.btype,
                payload={"question": f"Medical barrier open: {b.description or b.btype}. What is the expected clearance timeline?"},
                pathway_ids=tags, barrier_id=b.id,
            ))

        else:  # unmappable — surface to the team rather than dropping it
            specs.append(TaskSpec(
                task_type="message_team", mode="auto", action_id="SGE-027",
                title=f"Ask team about: {b.btype}",
                target=b.btype,
                payload={"question": f"Open barrier '{b.btype}' ({b.dimension}): {b.description or 'no detail'} — how should this be worked?"},
                pathway_ids=tags, barrier_id=b.id,
            ))

    # Facility pipeline: shortlists for every active facility-bound pathway,
    # then per-referral progression tasks.
    if saw_destination:
        dest_barrier_ids = {b.id: b for b in open_barriers if b.btype == "bed_availability" or b.dimension == "destination"}
        for pid in active_ids:
            if pid in FACILITY_BOUND_PATHWAYS:
                bid = next(
                    (b.id for b in dest_barrier_ids.values() if not b.pathway_ids or pid in b.pathway_ids),
                    next(iter(dest_barrier_ids), None),
                )
                specs.append(TaskSpec(
                    task_type="build_shortlist", mode="auto", action_id="FPR-001",
                    title=f"Build facility shortlist for {pathways.get(pid, {}).get('name', pid)}",
                    target=str(pid), payload={"pathway_id": pid},
                    pathway_ids=[pid], barrier_id=bid,
                ))

    referrals = session.exec(select(Referral).where(Referral.case_id == case.id)).all()
    for r in referrals:
        if active_ids and r.pathway_id not in active_ids:
            continue
        step = _REFERRAL_PROGRESSION.get(r.status)
        if not step:
            continue
        task_type, mode, action_id = step
        specs.append(TaskSpec(
            task_type=task_type, mode=mode, action_id=action_id,
            title=f"{task_type.replace('_', ' ').capitalize()}: {r.facility_name}",
            target=r.facility_id, payload={"referral_id": r.id},
            pathway_ids=[r.pathway_id], referral_id=r.id,
        ))

    # Pre-commit, the referral pipeline caps at facility_screen_call and no
    # binding action is ever planned.
    if not committed:
        specs = [s for s in specs if s.task_type not in BINDING_TASK_TYPES]

    # Shared-first ordering: shared (no tags) earliest, then broader pathway
    # coverage (more tags) before pathway-exclusive work.
    specs.sort(key=lambda s: (1 if s.pathway_ids else 0, -len(s.pathway_ids or [])))
    return specs


def persist_plan(session: Session, case: Case, specs: List[TaskSpec]) -> dict:
    """Materialize TaskSpecs as DispoTask rows (idempotency-key dedupe).

    Pre-commit: APPROVAL-mode tasks land as 'suggested' and one
    Approval(kind='suggested') batches them behind a chat card. Post-commit:
    APPROVAL tasks are created 'approved' directly — the batch approval that
    committed the pathway covered them. AUTO tasks are always 'pending'.
    Commits incrementally (per task) so IntegrityError dedupe cannot discard
    sibling creations.
    """
    committed = case.state in COMMITTED_STATES
    created_ids: list = []
    suggested: list = []

    for spec in specs:
        key = f"{case.id}:{spec.task_type}:{spec.target}"
        if session.exec(select(DispoTask).where(DispoTask.idempotency_key == key)).first():
            continue
        status = "pending" if spec.mode == "auto" else ("approved" if committed else "suggested")
        task = DispoTask(
            case_id=case.id,
            barrier_id=spec.barrier_id,
            referral_id=spec.referral_id,
            action_id=spec.action_id,
            task_type=spec.task_type,
            mode=spec.mode,
            status=status,
            pathway_ids=spec.pathway_ids,
            idempotency_key=key,
            title=spec.title,
            detail=json.dumps(spec.payload),
        )
        session.add(task)
        try:
            session.commit()
        except IntegrityError:  # racing creator got there first — that's fine
            session.rollback()
            continue
        created_ids.append(task.id)
        mirror_task_to_ehr(session, case, task)
        if status == "suggested":
            suggested.append(task)

    approval_id = None
    if suggested:
        approval = Approval(
            case_id=case.id,
            kind="suggested",
            task_ids=[t.id for t in suggested],
            prompt="Placer suggests: " + "; ".join(t.title for t in suggested),
        )
        session.add(approval)
        session.commit()
        approval_id = approval.id
        post_chat(
            session,
            "Suggested next steps:\n" + "\n".join(f"- {t.title}" for t in suggested),
            case_id=case.id,
            kind="approval_card",
            approval_id=approval.id,
        )
        session.commit()

    return {"created": created_ids, "suggested": [t.id for t in suggested], "approval_id": approval_id}
