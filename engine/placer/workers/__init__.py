"""Worker dispatch: ``run_task`` executes one approved/auto DispoTask.

Contract (see engine/INTERFACES.md): workers do their own EHR writes (via
EHRClient, actor 'agent:<worker>') and engine-DB writes (referrals, intel,
chat notifications), set ``task.result``, and return it. They never change
``task.status`` (the brain executor owns the lifecycle) and never call the
GPS/router. Unknown task types raise ValueError so the brain can mark the task
failed and escalate.
"""

from __future__ import annotations

from sqlmodel import Session

from .. import config
from ..ehr_client import EHRClient
from ..models import utcnow
from . import clinical, coverage, family, misc, placement, transitions

# task_type -> (actor slug, human-readable worker name, handler).
_DISPATCH = {
    "chart_audit": ("clinical-prep", "Clinical Prep", clinical.chart_audit),
    "draft_order": ("clinical-prep", "Clinical Prep", clinical.draft_order),
    "draft_consult": ("clinical-prep", "Clinical Prep", clinical.draft_consult),
    "preference_call": ("family-liaison", "Family Liaison", family.preference_call),
    "build_shortlist": ("placement", "Placement", placement.build_shortlist),
    "facility_intake_call": ("placement", "Placement", placement.facility_intake_call),
    "facility_screen_call": ("placement", "Placement", placement.facility_screen_call),
    "submit_referral": ("placement", "Placement", placement.submit_referral),
    "finalize_acceptance": ("placement", "Placement", placement.finalize_acceptance),
    "verify_benefits": ("coverage", "Coverage", coverage.verify_benefits),
    "book_transport": ("transitions", "Transitions", transitions.book_transport),
    "message_team": ("coordinator", "Coordinator", misc.message_team),
}


def run_task(session: Session, task) -> dict:
    """Execute one DispoTask. Dispatches on ``task.task_type``; sets
    ``task.result`` and returns it. Raises ValueError for unknown types."""
    try:
        slug, worker_name, handler = _DISPATCH[task.task_type]
    except KeyError:
        raise ValueError(
            f"Unknown task_type '{task.task_type}' "
            f"(known: {', '.join(sorted(_DISPATCH))})"
        )
    ehr = EHRClient(actor=f"{config.ACTOR_PREFIX}:{slug}")
    try:
        result = handler(session, task, ehr, worker_name)
    finally:
        ehr.close()
    task.result = result
    task.updated_at = utcnow()
    session.add(task)
    return result
