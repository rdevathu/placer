"""Request DTOs for write endpoints.

These are typed with the controlled-vocabulary enums so the allowed values show
up in the OpenAPI schema — the main lever for getting agents to send valid
payloads. Reads return the table models directly (see routers), optionally with
the ``raw_fhir`` escape hatch stripped.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from .models import enums

# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------


class PatientCreate(BaseModel):
    mrn: Optional[str] = Field(default=None, description="Auto-assigned if omitted")
    family_name: Optional[str] = None
    given_name: Optional[str] = None
    prefix: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    marital_status: Optional[str] = None
    language: Optional[str] = None
    phone: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = Field(default=None, description="e.g. spouse, daughter, son, friend")
    emergency_contact_phone: Optional[str] = None
    living_situation: Optional[str] = None
    code_status: Optional[str] = None


class PatientUpdate(BaseModel):
    family_name: Optional[str] = None
    given_name: Optional[str] = None
    phone: Optional[str] = None
    address_line: Optional[str] = None
    postal_code: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    living_situation: Optional[str] = Field(default=None, description="lives_alone | lives_with_family | facility")
    code_status: Optional[str] = Field(default=None, description="full | DNR | DNI | comfort")
    deceased: Optional[bool] = None


# ---------------------------------------------------------------------------
# Encounters
# ---------------------------------------------------------------------------


class EncounterCreate(BaseModel):
    patient_id: str
    status: enums.EncounterStatus = enums.EncounterStatus.in_progress
    class_code: enums.EncounterClass = enums.EncounterClass.inpatient
    type_text: Optional[str] = None
    visit_title: Optional[str] = None
    reason_text: Optional[str] = None
    period_start: Optional[datetime] = None
    location_display: Optional[str] = None
    attending_name: Optional[str] = None


class EncounterUpdate(BaseModel):
    status: Optional[enums.EncounterStatus] = None
    period_end: Optional[datetime] = Field(default=None, description="Set to discharge the patient")
    disposition_status: Optional[enums.DispositionStatus] = None
    planned_disposition: Optional[enums.DispositionType] = None
    location_display: Optional[str] = None


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------


class ConditionCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    code: Optional[str] = None
    display: str
    category: enums.ConditionCategory = enums.ConditionCategory.problem_list_item
    clinical_status: enums.ClinicalStatus = enums.ClinicalStatus.active


class ConditionUpdate(BaseModel):
    clinical_status: Optional[enums.ClinicalStatus] = None
    abatement_date: Optional[datetime] = None
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# Observations / labs
# ---------------------------------------------------------------------------


class ObservationCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    category: enums.ObservationCategory = enums.ObservationCategory.laboratory
    loinc_code: Optional[str] = None
    display: str
    value_num: Optional[float] = None
    value_unit: Optional[str] = None
    value_string: Optional[str] = None
    status: enums.ObservationStatus = enums.ObservationStatus.final


class LabResultUpdate(BaseModel):
    """Result a pending lab (set its value and mark it final)."""

    value_num: Optional[float] = None
    value_unit: Optional[str] = None
    value_string: Optional[str] = Field(default=None, description="For qualitative results, e.g. 'Not detected'")
    abnormal_flag: Optional[str] = Field(default=None, description="H | L | N | critical")
    status: enums.ObservationStatus = enums.ObservationStatus.final


# ---------------------------------------------------------------------------
# Medications
# ---------------------------------------------------------------------------


class MedicationCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    display: str
    dose: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    status: enums.MedicationStatus = enums.MedicationStatus.active
    category: Optional[str] = Field(default=None, description="inpatient | outpatient | discharge")


class MedicationUpdate(BaseModel):
    status: Optional[enums.MedicationStatus] = None
    dose: Optional[str] = None
    frequency: Optional[str] = None


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class OrderCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    order_type: enums.OrderType
    display: str = Field(description="What is being ordered, e.g. 'SARS-CoV-2 NAA test' or 'PM&R consult'")
    detail: Optional[str] = None
    priority: str = Field(default="routine", description="routine | urgent | stat")
    status: enums.OrderStatus = Field(
        default=enums.OrderStatus.draft,
        description="draft = pended (awaiting signature); pass 'signed' to sign immediately",
    )
    ordered_by: Optional[str] = Field(default=None, description="Agent or clinician placing the order")


class OrderUpdate(BaseModel):
    display: Optional[str] = None
    detail: Optional[str] = None
    priority: Optional[str] = None


class OrderSign(BaseModel):
    signed_by: str = Field(description="Name of the clinician/agent signing the order")


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


class NoteCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    note_type: enums.NoteType = enums.NoteType.progress
    title: Optional[str] = None
    text: str
    author: Optional[str] = None
    author_role: Optional[str] = None
    authored_by_agent: bool = False
    status: enums.NoteStatus = enums.NoteStatus.draft


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    status: Optional[enums.NoteStatus] = None


# ---------------------------------------------------------------------------
# Disposition
# ---------------------------------------------------------------------------


class DispoAssessmentCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    predicted_disposition: enums.DispositionType
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rationale: Optional[str] = None
    barriers: Optional[list[str]] = Field(default=None, description="Open items blocking this disposition")
    alternatives: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Ranked alternatives, e.g. [{'disposition': 'home', 'confidence': 0.2}]"
    )
    assessed_by: Optional[str] = None


# ---------------------------------------------------------------------------
# Facilities
# ---------------------------------------------------------------------------


class FacilityCreate(BaseModel):
    name: str
    facility_type: enums.FacilityType
    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    total_beds: Optional[int] = None
    available_beds: Optional[int] = None
    accepts_covid_positive: bool = False
    accepts_medicaid: bool = True
    specialties: Optional[list[str]] = None


class FacilityUpdate(BaseModel):
    available_beds: Optional[int] = Field(default=None, description="Update after calling the facility")
    accepts_covid_positive: Optional[bool] = None
    phone: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Care tasks
# ---------------------------------------------------------------------------


class CareTaskCreate(BaseModel):
    patient_id: str
    encounter_id: Optional[str] = None
    task_type: enums.TaskType
    title: str
    description: Optional[str] = None
    status: enums.TaskStatus = enums.TaskStatus.pending
    priority: str = Field(default="medium", description="low | medium | high")
    assigned_to: Optional[str] = None
    due_at: Optional[datetime] = None
    related_facility_id: Optional[str] = None
    related_order_id: Optional[str] = None


class CareTaskUpdate(BaseModel):
    status: Optional[enums.TaskStatus] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    result_summary: Optional[str] = None
    related_facility_id: Optional[str] = None
    related_order_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Communications
# ---------------------------------------------------------------------------


class CommunicationCreate(BaseModel):
    patient_id: str
    care_task_id: Optional[str] = None
    facility_id: Optional[str] = None
    direction: enums.CommunicationDirection = enums.CommunicationDirection.outbound
    modality: enums.CommunicationModality = enums.CommunicationModality.phone
    party_type: Optional[enums.PartyType] = None
    party_name: Optional[str] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    outcome: Optional[str] = Field(default=None, description="e.g. bed_available | declined | callback | preference_captured")
    occurred_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Placer chat
# ---------------------------------------------------------------------------


class PlacerMessageCreate(BaseModel):
    sender: enums.PlacerMessageSender = enums.PlacerMessageSender.provider
    sender_name: Optional[str] = Field(default=None, description="Display name shown on the message")
    text: str = Field(description="Message body (plain text)")
