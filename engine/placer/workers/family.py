"""Family Liaison worker: preference calls to the patient's family.

The preference profile is the decision-dimension raw material — the worker
records it in ``case.facts`` and the EHR, but never clears decision barriers
(that is a human/team call surfaced by the brain).
"""

from __future__ import annotations

import json

from sqlmodel import Session

from .. import calls
from ..models import utcnow
from .common import get_case, notify, telephony_waiting

PREFERENCE_QUESTIONS = [
    "What discharge destination does the family prefer (home, a family member's home, assisted living, skilled nursing, rehab, hospice)?",
    "What are the family's top priorities or concerns for this discharge?",
    "Are any options unacceptable to the family?",
    "What location or distance constraints matter (near which city/family member)?",
    "Is a family caregiver available, and roughly how many hours per day?",
]


def preference_call(session: Session, task, ehr, worker: str) -> dict:
    """Call the family, store the preference profile in case.facts, mirror the
    call into the EHR communications log, and post the headline preference.
    Without telephony the task parks as waiting — no outcome is ever invented."""
    waiting = telephony_waiting()
    if waiting is not None:
        return waiting
    case = get_case(session, task.case_id)
    chart = ehr.get_chart(case.patient_id)
    patient = chart.get("patient") or {}
    callee = {
        "role": "family member",
        "relationship": "next of kin",
        "patient": {
            "name": patient.get("name"),
            "age": patient.get("age"),
            "address": patient.get("address"),
        },
    }
    context = case.brief or (
        f"Inpatient {patient.get('name', case.patient_id)}; active problems: "
        f"{json.dumps(chart.get('active_problems', []), default=str)[:1500]}"
    )
    call = calls.place_call(
        objective="Learn the family's discharge preferences, constraints, and caregiver availability",
        questions=PREFERENCE_QUESTIONS,
        callee=callee,
        context=context,
    )

    profile = {
        "answers": call.answers,
        "outcome": call.outcome,
        "notes": call.notes,
        "follow_up_needed": call.follow_up_needed,
        "captured_at": utcnow().isoformat(),
    }
    facts = dict(case.facts or {})  # JSON column: assign a fresh dict
    facts["preference_profile"] = profile
    case.facts = facts
    case.dirty = True
    case.updated_at = utcnow()
    session.add(case)

    ehr.create_communication(
        patient_id=case.patient_id,
        summary=f"Family preference call: {call.outcome}",
        party_type="family",
        party_name="Family (next of kin)",
        outcome=call.outcome,
        transcript=call.transcript,
    )
    headline = call.answers.get(PREFERENCE_QUESTIONS[0]) or call.outcome
    notify(session, case.id, f"{worker}: family preference — {headline}")
    return {"preference_profile": profile}
