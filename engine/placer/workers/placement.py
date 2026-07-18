"""Placement worker: the facility referral pipeline.

shortlisted -> (intake call) intake_verified -> (screen call) screened ->
(portal) submitted/pending -> (confirm call) accepted | declined, with
conditional and waitlist off-ramps. Every call is mirrored into the EHR
communications log and learned facts land in FacilityIntel so the next case
benefits.
"""

from __future__ import annotations

import json
from datetime import timedelta

from sqlmodel import Session, select

from .. import calls
from ..models import Referral, utcnow
from ..registry import load_pathways
from .common import (
    append_note,
    clear_barriers,
    extract_beds,
    fetch_facility,
    get_case,
    get_or_create_intel,
    get_payload,
    get_referral,
    guard_referral,
    notify,
    record_decline,
    short_ref,
)

# Wired placement pathways -> the EHR facility_type vocabulary.
PATHWAY_FACILITY_TYPE = {
    8: "assisted_living",
    11: "snf",
    12: "inpatient_rehab",
    14: "hospice",
}

SHORTLIST_MAX = 3
BED_HOLD_HOURS = 48

INTAKE_QUESTIONS = [
    "How many beds do you currently have available?",
    "What is your intake route (fax, referral portal, phone) and what documents do you require?",
    "What are your admissions office hours?",
    "How quickly can you turn around a referral decision?",
]

FINALIZE_QUESTIONS = [
    "Do you accept this patient?",
    "If accepted, how long will you hold the bed?",
    "Are there any conditions on the acceptance?",
]

_DECLINE_MARKERS = ("declin", "denied", "cannot accept", "unable to accept", "not able to accept")


def _pathway(pathway_id: int) -> dict:
    return load_pathways().get(pathway_id) or {}


def _callee_for(session: Session, ehr, referral: Referral) -> dict:
    facility = fetch_facility(ehr, referral.facility_id) or {
        "id": referral.facility_id,
        "name": referral.facility_name,
    }
    intel = get_or_create_intel(session, referral.facility_id)
    return {
        "role": "facility admissions coordinator",
        "facility": facility,
        "engine_intel": {
            "beds_available": intel.beds_available,
            "last_verified_at": intel.last_verified_at.isoformat() if intel.last_verified_at else None,
            "past_declines": len(intel.decline_history or []),
        },
    }


def _mirror_call(ehr, case, referral: Referral, call, summary: str) -> None:
    ehr.create_communication(
        patient_id=case.patient_id,
        summary=summary,
        party_type="facility",
        party_name=referral.facility_name,
        outcome=call.outcome,
        transcript=call.transcript,
        facility_id=referral.facility_id,
    )


def _categorize_denial(call) -> str:
    """Bucket a decline into the contract's denial vocabulary."""
    text = f"{call.outcome} {call.notes} {json.dumps(call.answers)}".lower()
    if any(w in text for w in ("no bed", "no beds", "no capacity", "census full", "at capacity", "full")):
        return "no_bed"
    if any(w in text for w in ("network", "insurance", "payer", "contract")):
        return "network"
    if any(w in text for w in ("document", "paperwork", "records", "packet")):
        return "documentation"
    return "clinical_capability"


def _is_declined(call) -> bool:
    text = f"{call.outcome} {call.notes}".lower()
    return any(w in text for w in _DECLINE_MARKERS)


# -- handlers ----------------------------------------------------------------


def build_shortlist(session: Session, task, ehr, worker: str) -> dict:
    """payload {pathway_id}: pick up to 3 candidate facilities of the pathway's
    type, ranked by available beds and past-decline history, as Referral rows.
    Deduped against every existing referral on the case."""
    payload = get_payload(task)
    pathway_id = payload.get("pathway_id")
    if pathway_id is None and task.pathway_ids:
        pathway_id = task.pathway_ids[0]
    if pathway_id is None:
        raise ValueError(f"build_shortlist task {task.id} needs payload.pathway_id")
    pathway_id = int(pathway_id)
    facility_type = PATHWAY_FACILITY_TYPE.get(pathway_id)
    if facility_type is None:
        raise ValueError(
            f"Pathway {pathway_id} has no facility placement mapping "
            f"(wired: {sorted(PATHWAY_FACILITY_TYPE)})"
        )

    facilities = ehr.list_facilities(facility_type=facility_type)

    def score(fac: dict) -> int:
        intel = get_or_create_intel(session, fac["id"])
        beds = fac.get("available_beds")
        if beds is None:
            beds = intel.beds_available
        return (beds or 0) - 2 * len(intel.decline_history or [])

    ranked = sorted(facilities, key=score, reverse=True)
    existing = {
        r.facility_id
        for r in session.exec(select(Referral).where(Referral.case_id == task.case_id)).all()
    }
    created = []
    for fac in ranked:
        if len(created) >= SHORTLIST_MAX:
            break
        if fac["id"] in existing:
            continue
        referral = Referral(
            case_id=task.case_id,
            pathway_id=pathway_id,
            facility_id=fac["id"],
            facility_name=fac.get("name", fac["id"]),
            status="shortlisted",
        )
        session.add(referral)
        created.append(referral)
    session.flush()

    result = {
        "pathway_id": pathway_id,
        "facility_type": facility_type,
        "referrals": [
            {"referral_id": r.id, "facility_id": r.facility_id, "facility_name": r.facility_name}
            for r in created
        ],
    }
    if created:
        names = ", ".join(r.facility_name for r in created)
        pathway_name = _pathway(pathway_id).get("name", facility_type)
        notify(session, task.case_id, f"{worker}: shortlisted {len(created)} {pathway_name} option(s) — {names}")
    return result


def facility_intake_call(session: Session, task, ehr, worker: str) -> dict:
    """payload {referral_id}: verify intake route/hours/capacity by phone.
    shortlisted -> intake_verified, or declined ('no_bed') on a hard zero."""
    referral = get_referral(session, task)
    guard_referral(referral, {"shortlisted", "intake_verified"}, "facility_intake_call")
    case = get_case(session, referral.case_id)

    call = calls.place_call(
        objective=f"Verify intake route and current bed capacity at {referral.facility_name}",
        questions=INTAKE_QUESTIONS,
        callee=_callee_for(session, ehr, referral),
        context=case.brief or f"Patient {case.patient_id}, pathway {referral.pathway_id} placement",
    )

    beds = extract_beds(call.answers)
    if beds == 0 or (_is_declined(call) and _categorize_denial(call) == "no_bed"):
        referral.status = "declined"
        referral.denial_reason = "no_bed"
        record_decline(session, referral.facility_id, case.id, "no_bed")
        case.dirty = True
        note = f"{worker}: {referral.facility_name} has no capacity — struck from shortlist"
    else:
        referral.status = "intake_verified"
        note = f"{worker}: intake verified at {referral.facility_name} — {call.outcome}"
    append_note(referral, "Intake call: " + json.dumps(call.answers))
    session.add(referral)

    intel = get_or_create_intel(session, referral.facility_id)
    intel.last_verified_at = utcnow()
    if beds is not None:
        intel.beds_available = beds
        ehr.update_facility(referral.facility_id, available_beds=beds)
    session.add(intel)

    _mirror_call(ehr, case, referral, call, f"Intake call to {referral.facility_name}: {call.outcome}")
    notify(session, case.id, note)
    return {
        "referral_id": referral.id,
        "status": referral.status,
        "beds_available": beds,
        "outcome": call.outcome,
        "answers": call.answers,
    }


def facility_screen_call(session: Session, task, ehr, worker: str) -> dict:
    """payload {referral_id}: run the pathway's requirement checklist against
    the facility. intake_verified -> screened | conditional | declined
    (categorized denial_reason)."""
    referral = get_referral(session, task)
    guard_referral(referral, {"intake_verified", "shortlisted"}, "facility_screen_call")
    case = get_case(session, referral.case_id)
    pathway = _pathway(referral.pathway_id)
    questions = pathway.get("requirements") or [
        "Can you meet this patient's clinical needs as described?",
        "Are there any conditions on accepting this patient?",
    ]

    call = calls.place_call(
        objective=(
            f"Screen {referral.facility_name} for clinical capability to accept "
            f"this patient on the {pathway.get('name', referral.pathway_id)} pathway"
        ),
        questions=questions,
        callee=_callee_for(session, ehr, referral),
        context=case.brief or f"Patient {case.patient_id}",
    )

    text = f"{call.outcome} {call.notes}".lower()
    conditions = None
    if _is_declined(call):
        referral.status = "declined"
        referral.denial_reason = _categorize_denial(call)
        record_decline(session, referral.facility_id, case.id, referral.denial_reason)
        case.dirty = True
        note = f"{worker}: {referral.facility_name} declined on screening ({referral.denial_reason})"
    elif "condition" in text:
        referral.status = "conditional"
        conditions = [
            f"{q}: {a}"
            for q, a in call.answers.items()
            if "condition" in str(a).lower() or str(a).lower().startswith(("only if", "if "))
        ] or ([call.notes] if call.notes else [call.outcome])
        referral.conditions = conditions
        note = f"{worker}: {referral.facility_name} can accept with conditions — {call.outcome}"
    else:
        referral.status = "screened"
        note = f"{worker}: {referral.facility_name} screened clean — {call.outcome}"
    append_note(referral, "Screen call: " + json.dumps(call.answers))
    session.add(referral)

    _mirror_call(ehr, case, referral, call, f"Screening call to {referral.facility_name}: {call.outcome}")
    notify(session, case.id, note)
    return {
        "referral_id": referral.id,
        "status": referral.status,
        "denial_reason": referral.denial_reason,
        "conditions": conditions,
        "answers": call.answers,
    }


def submit_referral(session: Session, task, ehr, worker: str) -> dict:
    """payload {referral_id}: simulated portal submission. screened ->
    submitted -> pending decision, with a confirmation number in notes."""
    referral = get_referral(session, task)
    if referral.status in ("submitted", "pending"):
        return {"referral_id": referral.id, "status": referral.status, "note": "already submitted"}
    guard_referral(referral, {"screened", "conditional"}, "submit_referral")
    case = get_case(session, referral.case_id)

    confirmation = short_ref("REF")
    referral.status = "pending"
    append_note(referral, f"Submitted via portal; confirmation {confirmation}")
    session.add(referral)

    ehr.create_communication(
        patient_id=case.patient_id,
        summary=f"Referral packet submitted to {referral.facility_name} (confirmation {confirmation})",
        party_type="facility",
        party_name=referral.facility_name,
        outcome="submitted",
        facility_id=referral.facility_id,
        modality="portal",
    )
    notify(
        session,
        case.id,
        f"{worker}: referral submitted to {referral.facility_name} (confirmation {confirmation}) — awaiting decision",
    )
    return {"referral_id": referral.id, "status": "pending", "confirmation": confirmation}


def finalize_acceptance(session: Session, task, ehr, worker: str) -> dict:
    """payload {referral_id}: confirmation call for the final decision.
    pending/conditional -> accepted (48h bed hold + destination barrier cleared)
    or declined (categorized)."""
    referral = get_referral(session, task)
    guard_referral(referral, {"pending", "conditional", "submitted"}, "finalize_acceptance")
    case = get_case(session, referral.case_id)

    call = calls.place_call(
        objective=f"Confirm the final acceptance decision for the referral to {referral.facility_name}",
        questions=FINALIZE_QUESTIONS,
        callee=_callee_for(session, ehr, referral),
        context=case.brief or f"Patient {case.patient_id}; referral {referral.id} pending decision",
    )

    intel = get_or_create_intel(session, referral.facility_id)
    barriers_cleared = 0
    if _is_declined(call):
        referral.status = "declined"
        referral.denial_reason = _categorize_denial(call)
        record_decline(session, referral.facility_id, case.id, referral.denial_reason)
        note = f"{worker}: {referral.facility_name} declined at final review ({referral.denial_reason})"
    else:
        referral.status = "accepted"
        referral.bed_hold_expires = utcnow() + timedelta(hours=BED_HOLD_HOURS)
        barriers_cleared = clear_barriers(
            session, case.id, "destination", pathway_ids=[referral.pathway_id]
        )
        # The accepted bed is spoken for — decrement what we know, mirror to EHR.
        facility = fetch_facility(ehr, referral.facility_id)
        beds = facility.get("available_beds")
        if beds is None:
            beds = intel.beds_available
        if isinstance(beds, int) and beds > 0:
            intel.beds_available = beds - 1
            ehr.update_facility(referral.facility_id, available_beds=beds - 1)
        note = f"🛏 Bed secured at {referral.facility_name} — hold expires in {BED_HOLD_HOURS}h"
    intel.last_verified_at = utcnow()
    session.add(intel)
    append_note(referral, f"Final decision: {call.outcome}")
    session.add(referral)
    case.dirty = True
    session.add(case)

    _mirror_call(ehr, case, referral, call, f"Acceptance confirmation call to {referral.facility_name}: {call.outcome}")
    notify(session, case.id, note)
    return {
        "referral_id": referral.id,
        "status": referral.status,
        "denial_reason": referral.denial_reason,
        "bed_hold_expires": referral.bed_hold_expires.isoformat() if referral.bed_hold_expires else None,
        "barriers_cleared": barriers_cleared,
        "outcome": call.outcome,
    }
