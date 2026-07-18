"""Shared clock and factory helpers for the hero-patient seed modules.

Every helper *constructs and session.adds a fresh ORM instance* on each call —
never reuse a module-level SQLModel instance across sessions (it silently fails
to re-insert on the second reset; see ``seed/facilities.py``). Prose (note
bodies, chat messages) lives as module-level string constants in the per-hero
modules; only the ORM objects are built at seed time.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Session

from ...models import (
    Condition,
    Encounter,
    Medication,
    Note,
    Observation,
    PlacerMessage,
)

# Deterministic "now" for reproducible demos (matches the project's demo date).
NOW = datetime(2026, 7, 18, 8, 0, 0)

# Every hero encounter happens at the same (fictional) hospital.
HOSPITAL = "Iliad General Hospital"

_CLASS_DISPLAY = {
    "IMP": "inpatient encounter",
    "AMB": "ambulatory",
    "EMER": "emergency",
}


def encounter(
    session: Session,
    *,
    id: str,
    patient_id: str,
    class_code: str,
    period_start: datetime,
    period_end: Optional[datetime] = None,
    visit_title: Optional[str] = None,
    reason_text: Optional[str] = None,
    type_text: Optional[str] = None,
    location_display: Optional[str] = None,
    attending_name: Optional[str] = None,
    disposition_status: Optional[str] = None,
    planned_disposition: Optional[str] = None,
) -> Encounter:
    """Add an encounter. ``period_end=None`` means an active admission
    (status ``in-progress``); otherwise the encounter is ``finished`` and, by
    default, carries ``disposition_status='discharged'``."""
    active = period_end is None
    if disposition_status is None:
        disposition_status = "undetermined" if active else "discharged"
    enc = Encounter(
        id=id,
        patient_id=patient_id,
        status="in-progress" if active else "finished",
        class_code=class_code,
        class_display=_CLASS_DISPLAY.get(class_code),
        type_text=type_text or ("Hospital admission (procedure)" if class_code == "IMP" else "Office visit"),
        visit_title=visit_title,
        reason_text=reason_text,
        period_start=period_start,
        period_end=period_end,
        location_display=location_display,
        service_provider_display=HOSPITAL,
        attending_name=attending_name,
        disposition_status=disposition_status,
        planned_disposition=planned_disposition,
    )
    session.add(enc)
    return enc


def note(
    session: Session,
    *,
    id: str,
    patient_id: str,
    encounter_id: str,
    note_type: str,
    title: str,
    author: str,
    author_role: str,
    signed_at: datetime,
    text: str,
) -> Note:
    """Add a signed, clinician-authored note (heroes ship with no agent notes)."""
    n = Note(
        id=id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        note_type=note_type,
        title=title,
        text=text,
        author=author,
        author_role=author_role,
        authored_by_agent=False,
        status="signed",
        signed_by=author,
        signed_at=signed_at,
    )
    session.add(n)
    return n


def vital(
    session: Session,
    patient_id: str,
    encounter_id: str,
    loinc: str,
    display: str,
    value: float,
    unit: str,
    when: datetime,
    low: Optional[float] = None,
    high: Optional[float] = None,
    flag: Optional[str] = None,
) -> Observation:
    obs = Observation(
        patient_id=patient_id,
        encounter_id=encounter_id,
        category="vital-signs",
        loinc_code=loinc,
        display=display,
        value_num=value,
        value_unit=unit,
        reference_range_low=low,
        reference_range_high=high,
        abnormal_flag=flag,
        status="final",
        effective_time=when,
        issued_time=when,
    )
    session.add(obs)
    return obs


def condition(
    session: Session,
    patient_id: str,
    encounter_id: str,
    code: str,
    display: str,
    onset: datetime,
    status: str = "active",
    category: str = "encounter-diagnosis",
) -> Condition:
    cond = Condition(
        patient_id=patient_id,
        encounter_id=encounter_id,
        code_system="http://snomed.info/sct",
        code=code,
        display=display,
        category=category,
        clinical_status=status,
        verification_status="confirmed",
        onset_date=onset,
        recorded_date=onset,
    )
    session.add(cond)
    return cond


def med(
    session: Session,
    patient_id: str,
    encounter_id: str,
    display: str,
    dose: str,
    route: str,
    freq: str,
    authored: datetime,
    category: str = "inpatient",
) -> Medication:
    m = Medication(
        patient_id=patient_id,
        encounter_id=encounter_id,
        code_system="http://www.nlm.nih.gov/research/umls/rxnorm",
        display=display,
        dose=dose,
        route=route,
        frequency=freq,
        dosage_text=f"{display} {dose} {route} {freq}",
        status="active",
        intent="order",
        category=category,
        authored_on=authored,
    )
    session.add(m)
    return m


def placer_msg(
    session: Session,
    *,
    id: str,
    patient_id: str,
    sender: str,
    sender_name: str,
    text: str,
    at: datetime,
) -> PlacerMessage:
    """Add a Placer-chat message. ``created_at`` is set explicitly because it is
    the thread's timeline (the API returns messages ascending by created_at)."""
    msg = PlacerMessage(
        id=id,
        patient_id=patient_id,
        sender=sender,
        sender_name=sender_name,
        text=text,
        created_at=at,
        updated_at=at,
    )
    session.add(msg)
    return msg
