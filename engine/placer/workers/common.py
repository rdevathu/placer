"""Helpers shared by every worker handler.

Notably: the chat-notification seam (``notify`` imports ``post_message`` lazily
because ``placer.api.chat`` is built by a parallel wave), payload extraction
(``DispoTask`` has no payload column — the brain serializes payload keys as
JSON in ``detail``; we also accept a plain ``payload`` attribute for
forward-compat), and the barrier-clearing guard: workers may only clear
barriers in their own dimensions, never medical/decision/clinical_docs.
"""

from __future__ import annotations

import json
import re
from typing import Optional
from uuid import uuid4

from sqlmodel import Session, select

from ..models import Barrier, Case, FacilityIntel, Referral, utcnow

# The only dimensions any worker is allowed to clear. medical / decision /
# clinical_docs stay strictly human (or brain) territory.
CLEARABLE_DIMENSIONS = {"destination", "payer", "transport"}

_OPEN_STATUSES = ("open", "in_progress", "blocked")


def parked(reason: str, **extra) -> dict:
    """Sentinel result for a task that could not complete without fabricating.

    A worker returns this (instead of writing a communication / clearing a
    barrier / inventing a result) when the work needs a real outbound call but
    calls are disabled. The brain executor maps a ``{"parked": True}`` result
    to a non-``done`` task status, so the mirrored EHR care task stays
    pending/attempted rather than completed and the barrier stays open.
    """
    return {"parked": True, "reason": reason, **extra}


def notify(session: Session, case_id: Optional[str], text: str) -> None:
    """One-line chat notification. Lazy import: placer.api.chat is owned by a
    parallel wave and may not exist while workers are developed; tests stub it."""
    from placer.api.chat import post_message

    post_message(session, text, case_id=case_id, kind="notification")


def get_payload(task) -> dict:
    """Task parameters. Prefers a ``payload`` attribute (contract vocabulary);
    falls back to JSON parsed from ``detail`` since DispoTask has no payload
    column. Missing/unparseable -> {} so handlers fail on specific keys."""
    payload = getattr(task, "payload", None)
    if isinstance(payload, dict):
        return payload
    detail = getattr(task, "detail", None)
    if detail:
        try:
            data = json.loads(detail)
            if isinstance(data, dict):
                return data
        except ValueError:
            pass
    return {}


def get_case(session: Session, case_id: Optional[str]) -> Case:
    case = session.get(Case, case_id) if case_id else None
    if case is None:
        raise ValueError(f"Case '{case_id}' not found")
    return case


def get_referral(session: Session, task) -> Referral:
    """Referral targeted by a task: payload['referral_id'] wins, then the
    task's own referral_id column."""
    referral_id = get_payload(task).get("referral_id") or getattr(task, "referral_id", None)
    referral = session.get(Referral, referral_id) if referral_id else None
    if referral is None:
        raise ValueError(f"Referral '{referral_id}' not found for task {task.id}")
    return referral


def guard_referral(referral: Referral, allowed: set, action: str) -> None:
    """409-style guard: name the current status and what's allowed."""
    if referral.status not in allowed:
        raise ValueError(
            f"{action}: referral {referral.id} is '{referral.status}'; "
            f"allowed from: {', '.join(sorted(allowed))}"
        )


def fetch_facility(ehr, facility_id: str) -> dict:
    """Facility record by id. EHRClient exposes only list_facilities, so filter
    client-side (facility counts are demo-small)."""
    for fac in ehr.list_facilities():
        if fac.get("id") == facility_id:
            return fac
    return {}


def get_or_create_intel(session: Session, facility_id: str) -> FacilityIntel:
    intel = session.exec(
        select(FacilityIntel).where(FacilityIntel.facility_id == facility_id)
    ).first()
    if intel is None:
        intel = FacilityIntel(facility_id=facility_id)
        session.add(intel)
    return intel


def record_decline(session: Session, facility_id: str, case_id: str, reason: str) -> None:
    intel = get_or_create_intel(session, facility_id)
    # JSON columns don't track in-place mutation — always assign a new list.
    history = list(intel.decline_history or [])
    history.append({"case_id": case_id, "reason": reason, "at": utcnow().isoformat()})
    intel.decline_history = history
    session.add(intel)


def clear_barriers(
    session: Session,
    case_id: str,
    dimension: str,
    pathway_ids: Optional[list] = None,
) -> int:
    """Mark open barriers of ``dimension`` cleared. Shared barriers (empty
    pathway_ids) always match; pathway-scoped ones must overlap ``pathway_ids``
    (None = clear regardless of pathway). Returns how many were cleared."""
    if dimension not in CLEARABLE_DIMENSIONS:
        raise ValueError(
            f"Workers may not clear '{dimension}' barriers "
            f"(allowed: {', '.join(sorted(CLEARABLE_DIMENSIONS))})"
        )
    barriers = session.exec(
        select(Barrier).where(
            Barrier.case_id == case_id,
            Barrier.dimension == dimension,
            Barrier.status.in_(_OPEN_STATUSES),  # type: ignore[attr-defined]
        )
    ).all()
    cleared = 0
    wanted = set(pathway_ids or [])
    for barrier in barriers:
        scoped = barrier.pathway_ids or []
        if scoped and pathway_ids is not None and not (set(scoped) & wanted):
            continue
        barrier.status = "cleared"
        barrier.updated_at = utcnow()
        session.add(barrier)
        cleared += 1
    return cleared


def extract_int(value) -> Optional[int]:
    """First integer in a value like '2 beds as of today', else None."""
    match = re.search(r"-?\d+", str(value))
    return int(match.group()) if match else None


def extract_beds(answers: dict) -> Optional[int]:
    """Bed count from call answers: first parseable integer in any answer to a
    bed/capacity question."""
    for question, answer in answers.items():
        if "bed" in question.lower() or "capacity" in question.lower():
            beds = extract_int(answer)
            if beds is not None:
                return beds
    return None


def append_note(referral: Referral, text: str) -> None:
    referral.notes = f"{referral.notes}\n{text}" if referral.notes else text
    referral.updated_at = utcnow()


def short_ref(prefix: str) -> str:
    """Human-quotable reference number, e.g. 'REF-9F3A21BC'."""
    return f"{prefix}-{uuid4().hex[:8].upper()}"
