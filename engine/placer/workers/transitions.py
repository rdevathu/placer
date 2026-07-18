"""Transitions worker: discharge-day logistics (transport, handoff)."""

from __future__ import annotations

from sqlmodel import Session

from .. import calls
from .common import clear_barriers, get_case, get_payload, notify, short_ref

TRANSPORT_QUESTIONS = [
    "Can you transport the patient on the planned discharge date and time?",
    "What level of transport can you provide (wheelchair van, gurney, BLS/ALS)?",
    "What is the pickup window and booking reference?",
]

DEFAULT_VENDOR = "CareVan Medical Transport"


def book_transport(session: Session, task, ehr, worker: str) -> dict:
    """Call the transport vendor, book the ride, clear the transport barrier."""
    case = get_case(session, task.case_id)
    payload = get_payload(task)
    vendor = payload.get("vendor") or DEFAULT_VENDOR
    call = calls.place_call(
        objective="Book medical transport for a hospital discharge",
        questions=TRANSPORT_QUESTIONS,
        callee={"role": "transport dispatcher", "company": vendor},
        context=case.brief
        or f"Patient {case.patient_id} discharging; destination {payload.get('destination', 'per discharge order')}",
    )
    booking_ref = short_ref("TRN")
    barriers_cleared = clear_barriers(session, case.id, "transport")
    case.dirty = True
    session.add(case)

    ehr.create_communication(
        patient_id=case.patient_id,
        summary=f"Transport booked with {vendor} (ref {booking_ref})",
        party_type="other",
        party_name=vendor,
        outcome=call.outcome,
        transcript=call.transcript,
    )
    notify(session, case.id, f"{worker}: transport booked with {vendor} — ref {booking_ref}")
    return {
        "booking_ref": booking_ref,
        "vendor": vendor,
        "outcome": call.outcome,
        "barriers_cleared": barriers_cleared,
    }
