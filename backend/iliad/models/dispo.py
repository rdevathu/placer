"""Disposition-planning tables — the constructs the background agents drive.

These have no FHIR source; they are native to Placer and support the core
product loop: predict where a patient will go after discharge, then proactively
work the barriers (call facilities and family, pend labs, draft consults).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel

from .base import TimestampMixin, new_id


class DispoAssessment(TimestampMixin, table=True):
    """An append-only time series of disposition predictions so an agent's
    reasoning can be shown evolving. The newest row per patient is ``is_current``.
    """

    __tablename__ = "dispo_assessments"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    encounter_id: Optional[str] = Field(default=None, foreign_key="encounters.id", index=True)

    predicted_disposition: str = Field(description="home | home_with_services | snf | assisted_living | inpatient_rehab | ltac | hospice_home | hospice_facility | undetermined")
    confidence: Optional[float] = Field(default=None, description="0.0–1.0")
    rationale: Optional[str] = Field(default=None, sa_column=Column(Text))

    # JSON payloads: barriers is a list[str]; alternatives is list[{disposition, confidence}].
    barriers: Optional[list] = Field(default=None, sa_column=Column(JSON))
    alternatives: Optional[list] = Field(default=None, sa_column=Column(JSON))

    assessed_by: Optional[str] = Field(default=None, description="agent or clinician name")
    is_current: bool = Field(default=True, index=True)


class Facility(TimestampMixin, table=True):
    """Post-acute placement options (SNF/rehab/LTAC/hospice/etc). Agents query
    availability and update ``available_beds`` after phone calls."""

    __tablename__ = "facilities"

    id: str = Field(default_factory=new_id, primary_key=True)
    name: str = Field(index=True)
    facility_type: str = Field(index=True, description="snf | assisted_living | inpatient_rehab | ltac | hospice | home_health | dme")

    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None

    total_beds: Optional[int] = None
    available_beds: Optional[int] = Field(default=None, description="Updated by agents after calling the facility")
    accepts_covid_positive: bool = False
    accepts_medicaid: bool = True

    insurance_accepted: Optional[list] = Field(default=None, sa_column=Column(JSON))
    specialties: Optional[list] = Field(default=None, sa_column=Column(JSON), description="e.g. ['ventilator','dialysis','memory_care']")

    notes: Optional[str] = Field(default=None, sa_column=Column(Text))


class CareTask(TimestampMixin, table=True):
    """A background work item on the disposition worklist (e.g. call an SNF,
    call family for preference, draft a consult). The agent's to-do surface."""

    __tablename__ = "care_tasks"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    encounter_id: Optional[str] = Field(default=None, foreign_key="encounters.id", index=True)

    task_type: str = Field(index=True, description="call_snf | call_family | call_pcp | order_lab | draft_consult | insurance_auth | collect_preference | verify_eligibility | arrange_transport | other")
    title: str
    description: Optional[str] = Field(default=None, sa_column=Column(Text))

    status: str = Field(default="pending", index=True, description="pending | in_progress | blocked | completed | cancelled")
    priority: str = Field(default="medium", description="low | medium | high")

    assigned_to: Optional[str] = Field(default=None, description="agent or human name")
    due_at: Optional[datetime] = None

    related_facility_id: Optional[str] = Field(default=None, foreign_key="facilities.id")
    related_order_id: Optional[str] = Field(default=None, foreign_key="orders.id")

    result_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    completed_at: Optional[datetime] = None


class Communication(TimestampMixin, table=True):
    """Log of outreach (phone/fax/etc) — the audit trail of proactive work,
    e.g. a call to an SNF's admissions desk or to a patient's family."""

    __tablename__ = "communications"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    care_task_id: Optional[str] = Field(default=None, foreign_key="care_tasks.id", index=True)
    facility_id: Optional[str] = Field(default=None, foreign_key="facilities.id")

    direction: str = Field(default="outbound", description="outbound | inbound")
    modality: str = Field(default="phone", description="phone | sms | fax | email | portal")
    party_type: Optional[str] = Field(default=None, description="family | patient | snf | facility | pcp | insurance | other")
    party_name: Optional[str] = None

    summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    transcript: Optional[str] = Field(default=None, sa_column=Column(Text))
    outcome: Optional[str] = Field(default=None, description="e.g. bed_available | declined | callback | preference_captured")

    # Provider-side handle for a live call — e.g. the Bland call_id — so an
    # agent can poll status/transcript after the call is placed.
    external_id: Optional[str] = Field(default=None, index=True, description="External provider call id (e.g. Bland call_id)")

    occurred_at: Optional[datetime] = None


class PlacerMessage(TimestampMixin, table=True):
    """One message in the per-patient chat thread between the care team and
    Placer. ``created_at`` (from the mixin) is the timeline; threads render in
    ascending created_at order."""

    __tablename__ = "placer_messages"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)

    sender: str = Field(index=True, description="provider | placer")
    sender_name: Optional[str] = Field(default=None, description="Display name, e.g. 'Dr. Priya Nadkarni' or 'Placer'")
    text: str = Field(default="", sa_column=Column(Text))
