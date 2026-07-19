"""Outbound calling — Placer places real phone calls (via Bland) and logs them.

This is the *action* surface for phone calls; ``/communications`` remains the
read/audit log. Placing a call here dials through Bland and, on success, writes
the matching ``Communication`` row so the call shows up in the patient's call
log with the returned provider ``call_id`` stashed in ``external_id``.

### Autonomy gate (load-bearing — don't loosen without intent)

Placer may dial a **skilled-nursing facility (SNF) autonomously**. Every other
party (family, patient, PCP, insurance, generic facility) is a human-in-the-loop
action: the request must carry ``medical_team_approval`` naming the authorizing
clinician, or it is refused with **HTTP 403**. The allowed party types come from
``config.BLAND_AUTONOMOUS_PARTY_TYPES`` (default ``{"snf"}``).

### Demo safety

Every call is force-dialed to ``config.BLAND_FORCE_NUMBER`` regardless of the
number on record, so a demo can never ring a real third party. The response
reports both the intended and the actually-dialed number.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session

from .. import bland, config
from ..db import engine, get_session
from sqlmodel import select

from ..events import get_actor, record_event
from ..models import Communication, Facility, Patient
from ..models.base import new_id, utcnow
from ..schemas import CallRequest
from ._common import get_or_404, serialize

router = APIRouter(prefix="/calls", tags=["calls"])
logger = logging.getLogger(__name__)


def _await_and_complete(call_id: str, comm_id: str, patient_id: Optional[str]) -> None:
    """Poll Bland until the call finishes, then attach the transcript and emit a
    ``call.completed`` event — so Placer acts on the outcome with NO manual step
    and NO reachable webhook (Bland's cloud can't reach a localhost demo).

    Runs in a background thread after the place-call response returns, so a fresh
    Session is opened (the request's is already closed)."""
    for _ in range(120):  # ~10 min at 5s between polls
        try:
            data = bland.get_call(call_id)
        except Exception as exc:
            logger.warning("bland poll failed for %s: %s", call_id, exc)
            time.sleep(5)
            continue
        done = str(data.get("status") or "").lower() in {"completed", "complete"} or bool(data.get("completed"))
        if not done:
            time.sleep(5)
            continue
        transcript = data.get("concatenated_transcript") or data.get("transcript") or ""
        summary = data.get("summary") or (transcript[:500] if transcript else "Call completed.")
        with Session(engine) as s:
            comm = s.get(Communication, comm_id)
            if comm is not None:
                comm.transcript = transcript or comm.transcript
                comm.summary = summary
                comm.outcome = "call_completed"
                comm.updated_at = utcnow()
                s.add(comm)
            record_event(
                s,
                "call.completed",
                patient_id=patient_id,
                actor="agent:placer",
                entity_type="communication",
                entity_id=comm_id,
                payload={"call_id": call_id, "summary": summary, "transcript": transcript},
            )
            s.commit()
        logger.info("bland call %s completed; call.completed emitted", call_id)
        return
    logger.warning("bland call %s did not complete within the poll window", call_id)


@router.post(
    "/webhook",
    summary="Receive a completed-call result (Bland) and surface its action items",
    description=(
        "Bland posts the finished call here (or POST it manually to simulate). "
        "The transcript/summary is attached to the logged Communication and a "
        "`call.completed` event is emitted so Placer can act on what the callee "
        "required — e.g. draft a COVID-test order. Matches the call by "
        "`call_id`/`metadata.call_id` against the communication's `external_id`."
    ),
)
def call_webhook(payload: dict, session: Session = Depends(get_session), actor: str = Depends(get_actor)) -> dict:
    meta = payload.get("metadata") or {}
    call_id = payload.get("call_id") or payload.get("id") or meta.get("call_id")
    transcript = (
        payload.get("concatenated_transcript")
        or payload.get("transcript")
        or payload.get("summary")
        or ""
    )
    summary = payload.get("summary") or (transcript[:500] if transcript else "Call completed.")

    comm = None
    if call_id:
        comm = session.exec(select(Communication).where(Communication.external_id == str(call_id))).first()
    if comm is not None:
        comm.summary = summary
        comm.transcript = transcript or comm.transcript
        comm.outcome = "call_completed"
        comm.updated_at = utcnow()
        session.add(comm)

    patient_id = (comm.patient_id if comm else None) or meta.get("patient_id") or payload.get("patient_id")
    record_event(
        session,
        "call.completed",
        patient_id=patient_id,
        actor=actor,
        entity_type="communication",
        entity_id=comm.id if comm else None,
        payload={"call_id": call_id, "summary": summary, "transcript": transcript},
    )
    session.commit()
    return {"matched_communication": comm.id if comm else None, "patient_id": patient_id, "event": "call.completed"}


def _snf_gate(body: CallRequest, session: Session) -> None:
    """Enforce: only SNF calls are autonomous; everything else needs sign-off.

    Raises HTTP 403 when a non-SNF call arrives without ``medical_team_approval``.
    A ``facility_id`` pointing at a SNF counts as a SNF call even if
    ``party_type`` was left at a different value.
    """
    party_is_allowed = body.party_type.value in config.BLAND_AUTONOMOUS_PARTY_TYPES

    if body.facility_id:
        facility = get_or_404(session, Facility, body.facility_id, "Facility")
        if facility.facility_type in config.BLAND_AUTONOMOUS_PARTY_TYPES:
            party_is_allowed = True

    if party_is_allowed or body.medical_team_approval:
        return

    allowed = ", ".join(sorted(config.BLAND_AUTONOMOUS_PARTY_TYPES)) or "(none)"
    raise HTTPException(
        status_code=403,
        detail=(
            f"Placer may place calls autonomously only to: {allowed}. "
            f"A call to party_type='{body.party_type.value}' requires medical-team "
            f"sign-off — resubmit with `medical_team_approval` set to the name of "
            f"the authorizing clinician."
        ),
    )


@router.post(
    "",
    status_code=201,
    summary="Place an outbound phone call (Bland) and log it",
    description=(
        "Dials a real outbound call through Bland, then records it as a "
        "`Communication`.\n\n"
        "**Autonomy gate:** only `party_type='snf'` (or a `facility_id` that is a "
        "SNF) may be called without a human in the loop. Any other party requires "
        "`medical_team_approval` naming the authorizing clinician, else **403**.\n\n"
        "**Demo safety:** every call is force-dialed to a fixed number regardless "
        "of `phone_number`. Returns the Bland `call_id` (also stored on the "
        "communication's `external_id`), the number actually dialed, and the "
        "logged communication."
    ),
)
def place_call(
    body: CallRequest,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    actor: str = Depends(get_actor),
) -> dict:
    get_or_404(session, Patient, body.patient_id, "Patient")
    _snf_gate(body, session)

    # Demo safety valve: force every call to the configured number. Keep the
    # intended number for the audit trail.
    intended = body.phone_number
    if body.facility_id and not intended:
        facility = session.get(Facility, body.facility_id)
        intended = facility.phone if facility else None
    dialed = config.BLAND_FORCE_NUMBER or intended
    if not dialed:
        raise HTTPException(
            status_code=422,
            detail="No number to dial: provide `phone_number` (or set BLAND_FORCE_NUMBER).",
        )

    try:
        result = bland.place_call(
            phone_number=dialed,
            task=body.task,
            voice=body.voice or config.BLAND_VOICE,
            first_sentence=body.first_sentence,
            max_duration=body.max_duration,
            metadata={"patient_id": body.patient_id, "care_task_id": body.care_task_id},
        )
    except bland.BlandError as exc:
        # 502: we accepted the request but the upstream call provider failed.
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    call_id = result.get("call_id") or result.get("id")
    approval = body.medical_team_approval
    summary = (
        f"Outbound call placed via Bland to {body.party_name or body.party_type.value}."
        + (f" Authorized by {approval}." if approval else " Autonomous SNF call.")
    )

    comm = Communication(
        id=new_id(),
        patient_id=body.patient_id,
        care_task_id=body.care_task_id,
        facility_id=body.facility_id,
        direction="outbound",
        modality="phone",
        party_type=body.party_type.value,
        party_name=body.party_name,
        summary=summary,
        outcome="call_placed",
        external_id=call_id,
        occurred_at=utcnow(),
    )
    session.add(comm)
    record_event(
        session,
        "call.placed",
        patient_id=body.patient_id,
        actor=actor,
        entity_type="communication",
        entity_id=comm.id,
        payload={
            "party_type": body.party_type.value,
            "call_id": call_id,
            "autonomous": approval is None,
            "authorized_by": approval,
        },
    )
    session.commit()
    session.refresh(comm)

    # Close the loop automatically: poll Bland for the result and emit
    # call.completed when it finishes, so Placer drafts any required orders
    # (e.g. a COVID test) with no manual intervention.
    if call_id:
        background.add_task(_await_and_complete, call_id, comm.id, body.patient_id)

    return {
        "call_id": call_id,
        "dialed_number": dialed,
        "intended_number": intended,
        "forced": bool(config.BLAND_FORCE_NUMBER),
        "bland_response": result,
        "communication": serialize(comm),
    }
