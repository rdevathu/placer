"""Core clinical tables.

Enum-valued columns are stored as plain strings (the enum *value*) to keep
SQLite storage predictable and queryable. The controlled vocabularies live in
``ehr.models.enums`` and are enforced at the API boundary via typed request
DTOs and query parameters, which is also where they surface in OpenAPI.

Every clinically-sourced table keeps a ``raw_fhir`` JSON escape hatch so the
long tail of FHIR detail is never lost, but agents should read the flat columns.
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel

from .base import TimestampMixin, new_id


class Patient(TimestampMixin, table=True):
    __tablename__ = "patients"

    id: str = Field(default_factory=new_id, primary_key=True)
    mrn: str = Field(index=True, description="Human-friendly medical record number, e.g. MRN0001")

    family_name: Optional[str] = None
    given_name: Optional[str] = None
    prefix: Optional[str] = None
    full_name: Optional[str] = Field(default=None, index=True)

    gender: Optional[str] = None
    birth_date: Optional[date] = None
    deceased: bool = False

    marital_status: Optional[str] = None
    language: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    # Dispo-relevant social signal (typed, not buried in notes).
    living_situation: Optional[str] = Field(
        default=None,
        description="e.g. lives_alone, lives_with_family, facility — a disposition signal",
    )
    code_status: Optional[str] = Field(
        default=None, description="e.g. full, DNR, DNI, comfort"
    )

    raw_fhir: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class Encounter(TimestampMixin, table=True):
    __tablename__ = "encounters"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)

    status: str = Field(default="finished", index=True, description="planned | in-progress | finished | cancelled")
    class_code: Optional[str] = Field(default=None, description="AMB | IMP | EMER | OBSENC | VR")
    class_display: Optional[str] = None

    type_code: Optional[str] = None
    type_text: Optional[str] = None
    visit_title: Optional[str] = Field(default=None, description="Human-readable visit label")
    reason_code: Optional[str] = None
    reason_text: Optional[str] = None

    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = Field(default=None, description="NULL while a patient is still admitted")

    admit_source: Optional[str] = None
    location_display: Optional[str] = None
    service_provider_display: Optional[str] = None
    attending_name: Optional[str] = None
    attending_npi: Optional[str] = None

    # Disposition planning state carried on the (active) encounter.
    disposition_status: str = Field(default="undetermined", description="undetermined | predicted | decided | in_progress | ready | discharged")
    planned_disposition: Optional[str] = Field(default=None, description="Committed disposition once decided, e.g. snf")

    raw_fhir: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class Condition(TimestampMixin, table=True):
    __tablename__ = "conditions"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    encounter_id: Optional[str] = Field(default=None, foreign_key="encounters.id", index=True)

    code_system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None

    category: Optional[str] = Field(default=None, description="problem-list-item | encounter-diagnosis")
    clinical_status: Optional[str] = Field(default=None, index=True, description="active | resolved | remission | ...")
    verification_status: Optional[str] = None

    onset_date: Optional[datetime] = None
    abatement_date: Optional[datetime] = None
    recorded_date: Optional[datetime] = None

    note: Optional[str] = Field(default=None, sa_column=Column(Text))
    raw_fhir: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class DiagnosticReport(TimestampMixin, table=True):
    __tablename__ = "diagnostic_reports"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    encounter_id: Optional[str] = Field(default=None, foreign_key="encounters.id", index=True)

    loinc_code: Optional[str] = None
    display: Optional[str] = None
    category: Optional[str] = Field(default=None, description="LAB | RAD | ...")
    status: str = Field(default="final", description="registered | partial | preliminary | pending | final | cancelled")

    effective_time: Optional[datetime] = None
    issued_time: Optional[datetime] = None
    performer_display: Optional[str] = None
    conclusion: Optional[str] = Field(default=None, sa_column=Column(Text))

    raw_fhir: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class Observation(TimestampMixin, table=True):
    """Vitals and labs share this table, discriminated by ``category``.

    Labs that have been ordered but not yet resulted carry ``status='pending'``
    with a NULL ``value_num``. That is the signal for "still pending" — the core
    of the disposition workflow (e.g. an SNF-required COVID test in flight).
    """

    __tablename__ = "observations"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    encounter_id: Optional[str] = Field(default=None, foreign_key="encounters.id", index=True)
    diagnostic_report_id: Optional[str] = Field(default=None, foreign_key="diagnostic_reports.id", index=True)

    category: str = Field(default="laboratory", index=True, description="vital-signs | laboratory | imaging | survey")
    loinc_code: Optional[str] = None
    display: Optional[str] = None

    value_num: Optional[float] = None
    value_unit: Optional[str] = None
    value_string: Optional[str] = Field(default=None, description="For non-numeric results, e.g. 'Not detected'")
    has_components: bool = Field(default=False, description="True for composite obs like blood pressure; see raw_fhir")

    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None
    abnormal_flag: Optional[str] = Field(default=None, description="H | L | N | critical")
    interpretation: Optional[str] = None

    status: str = Field(default="final", index=True, description="pending | preliminary | final | amended | cancelled")
    effective_time: Optional[datetime] = None
    issued_time: Optional[datetime] = None

    raw_fhir: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class Medication(TimestampMixin, table=True):
    """Medication list / orders-as-history for a patient.

    NOTE: In the source FHIR, ``MedicationRequest.medicationReference`` cannot be
    resolved to a drug name (the ``Medication`` resource is absent), so imported
    rows rely on ``display`` best-effort and may be sparse. Hero patients carry
    clean, coded meds. New inpatient med orders flow through the ``orders`` table.
    """

    __tablename__ = "medications"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    encounter_id: Optional[str] = Field(default=None, foreign_key="encounters.id", index=True)

    code_system: Optional[str] = Field(default=None, description="usually RxNorm")
    code: Optional[str] = None
    display: Optional[str] = Field(default=None, description="Drug name — the reliable field")

    dose: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    dosage_text: Optional[str] = None

    status: str = Field(default="active", index=True, description="active | on-hold | completed | stopped | draft | cancelled")
    intent: Optional[str] = None
    category: Optional[str] = Field(default=None, description="inpatient | outpatient | discharge")

    authored_on: Optional[datetime] = None
    requester_display: Optional[str] = None

    raw_fhir: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class Procedure(TimestampMixin, table=True):
    __tablename__ = "procedures"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    encounter_id: Optional[str] = Field(default=None, foreign_key="encounters.id", index=True)

    code_system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None
    status: Optional[str] = None
    performed_start: Optional[datetime] = None
    performed_end: Optional[datetime] = None
    location_display: Optional[str] = None

    raw_fhir: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class Immunization(TimestampMixin, table=True):
    __tablename__ = "immunizations"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    encounter_id: Optional[str] = Field(default=None, foreign_key="encounters.id", index=True)

    cvx_code: Optional[str] = None
    display: Optional[str] = None
    status: Optional[str] = None
    occurrence_date: Optional[datetime] = None

    raw_fhir: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class Note(TimestampMixin, table=True):
    """Clinical documentation. Imported SOAP notes and agent-written notes
    (progress, dispo, consult) live here together."""

    __tablename__ = "notes"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    encounter_id: Optional[str] = Field(default=None, foreign_key="encounters.id", index=True)

    note_type: str = Field(default="progress", index=True, description="progress | history_and_physical | discharge_summary | consult | case_management | nursing | family_communication | ...")
    title: Optional[str] = None
    text: str = Field(default="", sa_column=Column(Text))

    author: Optional[str] = None
    author_role: Optional[str] = None
    authored_by_agent: bool = False

    status: str = Field(default="draft", index=True, description="draft (pended) | signed | amended")
    signed_by: Optional[str] = None
    signed_at: Optional[datetime] = None

    raw_fhir: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class Order(TimestampMixin, table=True):
    """The live, agent-writable action surface — the only clinical-action table
    that agents mutate. Kept separate from imported history so writes never
    corrupt the source record.

    Lifecycle: draft (pended) -> signed -> completed | cancelled. A lab order,
    when signed, materializes a pending Observation; completing it results that
    Observation.
    """

    __tablename__ = "orders"

    id: str = Field(default_factory=new_id, primary_key=True)
    patient_id: str = Field(foreign_key="patients.id", index=True)
    encounter_id: Optional[str] = Field(default=None, foreign_key="encounters.id", index=True)

    order_type: str = Field(index=True, description="lab | medication | imaging | consult | nursing | dispo | referral")
    status: str = Field(default="draft", index=True, description="draft (pended) | signed | completed | cancelled | discontinued")

    code: Optional[str] = None
    display: str = Field(description="What is being ordered, e.g. 'SARS-CoV-2 NAA test' or 'PM&R consult'")
    detail: Optional[str] = Field(default=None, sa_column=Column(Text))
    priority: str = Field(default="routine", description="routine | stat | urgent")

    ordered_by: Optional[str] = None
    signed_by: Optional[str] = None
    authored_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Bridges back to results / work items. linked_care_task_id is a soft
    # reference (no FK constraint) to avoid a care_tasks<->orders cycle that
    # would break SQLAlchemy's insert ordering; care_tasks.related_order_id is
    # the FK-backed side of the link.
    result_observation_id: Optional[str] = Field(default=None, foreign_key="observations.id")
    linked_care_task_id: Optional[str] = Field(default=None, description="Soft reference to care_tasks.id")
