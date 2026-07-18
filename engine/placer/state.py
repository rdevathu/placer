"""Pure disposition-state logic: the state machine, pathway selection,
readiness derivation, and pathway trumping.

Everything here is deterministic and I/O-free so it can be unit-tested offline
and reused by both the engine loop and the API layer. Inputs are plain dicts
(or dict-likes) rather than ORM rows to keep the functions pure.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Optional


class DispoState(str, Enum):
    """Case lifecycle. Mirrors the spirit of the EHR's DispositionStatus but is
    the engine's own vocabulary (the engine drives, the EHR records)."""

    tracking = "tracking"  # admitted, no confident prediction yet
    predicted = "predicted"  # engine has candidate pathway(s)
    committed = "committed"  # team decided the pathway
    green = "green"  # all readiness dimensions clear
    transition = "transition"  # discharge in motion (transport, handoff)
    discharged = "discharged"  # terminal


class IllegalTransition(ValueError):
    """Raised when an event is not allowed from the current state."""


# state -> {event: next_state}. Events are lowercase-snake verbs. Regressions
# are explicit (a reopened barrier drops green back to committed; a revoked
# team decision drops back to predicted) so the engine never silently jumps.
ALLOWED_TRANSITIONS: dict = {
    DispoState.tracking.value: {"predict": DispoState.predicted.value},
    DispoState.predicted.value: {"commit": DispoState.committed.value},
    DispoState.committed.value: {
        "clear": DispoState.green.value,
        "revoke": DispoState.predicted.value,
    },
    DispoState.green.value: {
        "depart": DispoState.transition.value,
        "regress": DispoState.committed.value,
        "revoke": DispoState.predicted.value,
    },
    DispoState.transition.value: {
        "discharge": DispoState.discharged.value,
        "regress": DispoState.committed.value,
    },
    DispoState.discharged.value: {},
}


def apply_transition(case_state: str, event: str) -> str:
    """Return the next state for ``event``, raising IllegalTransition otherwise.

    The error message names the current state and its legal events so a calling
    agent can recover (same philosophy as the EHR's 409 responses).
    """
    allowed = ALLOWED_TRANSITIONS.get(case_state)
    if allowed is None:
        raise IllegalTransition(f"Unknown case state '{case_state}'")
    if event not in allowed:
        legal = ", ".join(sorted(allowed)) or "none (terminal state)"
        raise IllegalTransition(
            f"Event '{event}' not allowed from state '{case_state}'; allowed: {legal}"
        )
    return allowed[event]


# A candidate below the floor can still be worked if it is the clear leader —
# but only if it has at least token confidence. Keeps a 0.0-everywhere
# distribution from producing phantom work.
MIN_LEADER_CONFIDENCE = 0.05


def select_active_pathways(distribution: list, floor: float, max_k: int) -> list:
    """Pick which pathways to work in parallel from a confidence distribution.

    ``distribution`` is [{'pathway_id': ..., 'confidence': ...}, ...]. Returns
    entries sorted by confidence desc, filtered to confidence >= floor, capped
    at ``max_k``. If nothing clears the floor, the single top candidate is kept
    anyway provided it reaches MIN_LEADER_CONFIDENCE (there is always a leading
    hypothesis unless the model has effectively no signal).
    """
    ranked = sorted(
        (d for d in distribution if d.get("confidence") is not None),
        key=lambda d: d["confidence"],
        reverse=True,
    )
    selected = [d for d in ranked if d["confidence"] >= floor][:max_k]
    if not selected and ranked and ranked[0]["confidence"] >= MIN_LEADER_CONFIDENCE:
        selected = [ranked[0]]
    return selected


READINESS_DIMENSIONS = [
    "medical",
    "clinical_docs",
    "decision",
    "payer",
    "destination",
    "home_logistics",
    "transport",
]

# Dimensions that require positive evidence: a barrier of that dimension must
# EXIST and be cleared. Absence of barriers is not proof the patient is
# medically ready or that a decision was made — someone has to have checked.
_EXPLICIT_CLEAR_DIMENSIONS = {"medical", "decision"}

_OPEN_STATUSES = {"open", "in_progress", "blocked"}


def derive_readiness(barriers: list, state: str) -> dict:
    """Compute the per-dimension readiness board and the overall green flag.

    ``barriers`` is a list of Barrier-like dicts with 'dimension' and 'status'.
    Returns {'dimensions': {dim: {'clear': bool, 'open_count': int}},
    'green': bool}. A dimension with zero barriers counts as clear EXCEPT
    'medical' and 'decision', which need an explicitly cleared barrier. Overall
    green additionally requires the case to be in the committed state — a
    barrier-free case that the team has not committed to is not dischargeable.
    """
    per_dim: dict = {}
    for dim in READINESS_DIMENSIONS:
        dim_barriers = [b for b in barriers if b.get("dimension") == dim]
        open_count = sum(1 for b in dim_barriers if b.get("status") in _OPEN_STATUSES)
        has_cleared = any(b.get("status") == "cleared" for b in dim_barriers)
        if dim in _EXPLICIT_CLEAR_DIMENSIONS:
            clear = open_count == 0 and has_cleared
        else:
            clear = open_count == 0
        per_dim[dim] = {"clear": clear, "open_count": open_count}

    green = state == DispoState.committed.value and all(
        d["clear"] for d in per_dim.values()
    )
    return {"dimensions": per_dim, "green": green}


def _classify(items: Iterable, decided_pathway_id: int, keep_ids: list, cancel_ids: list) -> None:
    for item in items:
        pathway_ids: Optional[list] = item.get("pathway_ids")
        if item.get("id") is None:
            continue
        if not pathway_ids:  # None or [] = shared across pathways = keep
            keep_ids.append(item["id"])
        elif decided_pathway_id in pathway_ids:
            keep_ids.append(item["id"])
        else:
            cancel_ids.append(item["id"])


def trump(active_tasks: list, referrals: list, barriers: list, decided_pathway_id: int) -> tuple:
    """When the team commits to one pathway, classify all in-flight work.

    Pure classification, no side effects: anything (task/referral/barrier —
    dicts with 'id' and 'pathway_ids') exclusive to a losing pathway goes in
    ``cancel_ids``; work whose pathway_ids include the decided pathway, or
    whose pathway_ids is empty/None (shared), goes in ``keep_ids``. Referrals
    carry a scalar 'pathway_id' in the DB; callers pass them here with a
    'pathway_ids' list like everything else.
    """
    keep_ids: list = []
    cancel_ids: list = []
    _classify(active_tasks, decided_pathway_id, keep_ids, cancel_ids)
    _classify(referrals, decided_pathway_id, keep_ids, cancel_ids)
    _classify(barriers, decided_pathway_id, keep_ids, cancel_ids)
    return keep_ids, cancel_ids
