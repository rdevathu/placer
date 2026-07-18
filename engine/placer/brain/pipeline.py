"""The assessment pipeline: one full GPS pass over a dirty case.

gps.assess -> update case memory/state -> reconcile barriers -> mirror the
assessment into the EHR -> plan + persist tasks -> readiness/green check ->
keep the commit-proposal card current. Called only from the brain loop (and
tests); everything else just marks cases dirty.
"""

from __future__ import annotations

from datetime import timedelta
from typing import List, Optional

from sqlmodel import Session, select

from placer import config, state
from placer.ehr_client import EHRClient
from placer.models import Approval, Barrier, Case, utcnow
from placer.registry import load_pathways

from . import gps, router_logic
from .chatlink import post_chat
from .schemas import BarrierOp, GpsAssessment

_OPEN_BARRIER_STATUSES = ("open", "in_progress", "blocked")

# review_horizon -> hours until the next heartbeat review.
_HORIZON_HOURS = {"imminent": 2, "days": 8, "week_plus": 24}

# Dimensions only humans may clear (mirrors state._EXPLICIT_CLEAR_DIMENSIONS).
_HUMAN_CLEARED_DIMENSIONS = {"medical", "decision"}


def _load_barriers(session: Session, case_id: str) -> List[Barrier]:
    return session.exec(select(Barrier).where(Barrier.case_id == case_id)).all()


def _reconcile_barriers(session: Session, case: Case, ops: List[BarrierOp]) -> None:
    """Apply GPS barrier ops, upserting by (dimension, btype). Medical and
    decision barriers are never auto-cleared (or re-opened once a human cleared
    them) regardless of what the model emitted."""
    existing = {(b.dimension, b.btype): b for b in _load_barriers(session, case.id)}
    for op in ops:
        key = (op.dimension, op.btype)
        barrier = existing.get(key)
        if op.op == "clear":
            if op.dimension in _HUMAN_CLEARED_DIMENSIONS:
                continue  # guardrail: only humans clear these
            if barrier is not None and barrier.status in _OPEN_BARRIER_STATUSES:
                barrier.status = "cleared"
                if op.evidence:
                    barrier.evidence = ((barrier.evidence + "\n") if barrier.evidence else "") + op.evidence
                barrier.updated_at = utcnow()
                session.add(barrier)
            continue
        # upsert
        if barrier is None:
            barrier = Barrier(
                case_id=case.id,
                dimension=op.dimension,
                btype=op.btype,
                description=op.description or None,
                evidence=op.evidence or None,
                pathway_ids=op.pathway_ids or None,
                status=op.status or "open",
            )
            session.add(barrier)
            existing[key] = barrier
        else:
            barrier.description = op.description or barrier.description
            if op.evidence:
                barrier.evidence = op.evidence
            barrier.pathway_ids = op.pathway_ids or barrier.pathway_ids
            if op.dimension not in _HUMAN_CLEARED_DIMENSIONS:
                # Non-protected barriers may be re-opened / re-statused by GPS.
                barrier.status = op.status or ("open" if barrier.status == "cleared" else barrier.status)
            barrier.updated_at = utcnow()
            session.add(barrier)
    session.commit()


def _post_assessment_to_ehr(case: Case, assessment: GpsAssessment, ehr: EHRClient,
                            open_barriers: List[Barrier]) -> None:
    """Mirror the GPS result into the EHR's dispo-assessment table."""
    if not assessment.distribution:
        return
    pathways = load_pathways()
    ranked = sorted(assessment.distribution, key=lambda s: s.confidence, reverse=True)
    leader = ranked[0]
    leader_info = pathways.get(leader.pathway_id, {})
    alternatives = [
        {
            "disposition": pathways.get(s.pathway_id, {}).get("ehr_disposition", "undetermined"),
            "pathway": pathways.get(s.pathway_id, {}).get("name", str(s.pathway_id)),
            "confidence": s.confidence,
        }
        for s in ranked[1:]
    ]
    ehr.post_dispo_assessment(
        patient_id=case.patient_id,
        encounter_id=case.encounter_id,
        predicted_disposition=leader_info.get("ehr_disposition", "undetermined"),
        confidence=leader.confidence,
        rationale=assessment.rationale,
        barriers=[f"{b.dimension}: {b.description or b.btype}" for b in open_barriers],
        alternatives=alternatives or None,
    )


def _ensure_commit_proposal(session: Session, case: Case, leader_id: int) -> None:
    """Keep exactly one pending kind='batch' Approval per predicted case: the
    commit-proposal card.

    Shape (the chat wave depends on this): ``Approval.task_ids`` holds a DICT,
    not a list — {"pathway_id": <leading pathway id>, "task_ids": [<open task
    ids for the case>]}. The card is informational; the chat layer's
    POST /cases/{id}/commit endpoint calls actions.commit_pathway with the
    pathway the team picks.
    """
    from placer.models import DispoTask  # local: avoid widening module imports

    open_task_ids = [
        t.id for t in session.exec(
            select(DispoTask).where(
                DispoTask.case_id == case.id,
                DispoTask.status.in_(("suggested", "pending", "approved", "in_progress", "waiting")),  # type: ignore[attr-defined]
            )
        ).all()
    ]
    payload = {"pathway_id": leader_id, "task_ids": open_task_ids}
    name = load_pathways().get(leader_id, {}).get("name", f"pathway {leader_id}")

    existing = session.exec(
        select(Approval).where(Approval.case_id == case.id, Approval.kind == "batch", Approval.status == "pending")
    ).first()
    if existing is not None:
        existing.task_ids = payload
        existing.prompt = f"Commit to {name}?"
        session.add(existing)
        session.commit()
        return

    approval = Approval(case_id=case.id, kind="batch", task_ids=payload, prompt=f"Commit to {name}?")
    session.add(approval)
    session.commit()
    post_chat(
        session,
        f"Leading pathway: {name}. Review the plan and commit when the team agrees.",
        case_id=case.id,
        kind="approval_card",
        approval_id=approval.id,
    )
    session.commit()


def run_assessment(session: Session, case: Case, ehr: EHRClient) -> GpsAssessment:
    """One full assessment pass over a case. Commits incrementally."""
    assessment = gps.assess(session, case, ehr)

    # -- case memory + review cadence ---------------------------------------
    case.brief = assessment.brief
    distribution = [{"pathway_id": s.pathway_id, "confidence": s.confidence} for s in assessment.distribution]
    case.active_pathways = state.select_active_pathways(
        distribution, config.CONFIDENCE_FLOOR, config.MAX_CANDIDATES
    )
    hours = min(_HORIZON_HOURS.get(assessment.review_horizon, 24), config.HEARTBEAT_HOURS)
    case.next_review_at = utcnow() + timedelta(hours=hours)

    if case.state == state.DispoState.tracking.value and case.active_pathways:
        case.state = state.apply_transition(case.state, "predict")
    case.updated_at = utcnow()
    session.add(case)
    session.commit()

    # -- barriers ------------------------------------------------------------
    _reconcile_barriers(session, case, assessment.barriers)
    barriers = _load_barriers(session, case.id)
    open_barriers = [b for b in barriers if b.status in _OPEN_BARRIER_STATUSES]

    # -- mirror to EHR (best-effort: EHR downtime must not kill the loop) ----
    try:
        _post_assessment_to_ehr(case, assessment, ehr, open_barriers)
    except Exception:  # noqa: BLE001 — logged by caller's Run row via outcome
        import logging
        logging.getLogger(__name__).exception("failed posting dispo assessment to EHR")

    # -- plan ----------------------------------------------------------------
    specs = router_logic.build_plan(session, case, barriers, case.active_pathways or [])
    router_logic.persist_plan(session, case, specs)

    # -- readiness / green ---------------------------------------------------
    if case.state == state.DispoState.committed.value:
        readiness = state.derive_readiness(
            [{"dimension": b.dimension, "status": b.status} for b in barriers], case.state
        )
        if readiness["green"]:
            case.state = state.apply_transition(case.state, "clear")
            case.updated_at = utcnow()
            session.add(case)
            session.commit()
            post_chat(
                session,
                "\U0001F7E2 discharge green — all readiness dimensions clear. Ready to depart.",
                case_id=case.id,
                kind="notification",
            )
            session.commit()

    # -- commit-proposal card ------------------------------------------------
    if case.state == state.DispoState.predicted.value and case.active_pathways:
        leader = max(case.active_pathways, key=lambda p: p.get("confidence", 0))
        _ensure_commit_proposal(session, case, leader["pathway_id"])

    session.commit()
    return assessment
