"""Controlled vocabularies used across the EHR.

These are plain ``str`` enums so they serialize as human-readable strings in the
API and are easy for agents to reason about. Keep values lowercase-snake and
stable — agents will filter on them.
"""

from __future__ import annotations

from enum import Enum


class EncounterStatus(str, Enum):
    planned = "planned"
    in_progress = "in-progress"  # active admission
    finished = "finished"
    cancelled = "cancelled"


class EncounterClass(str, Enum):
    ambulatory = "AMB"
    inpatient = "IMP"
    emergency = "EMER"
    observation = "OBSENC"
    virtual = "VR"


class DispositionType(str, Enum):
    """Where a patient is expected/decided to go after discharge."""

    home = "home"
    home_with_services = "home_with_services"  # home + home health / DME
    snf = "snf"  # skilled nursing facility
    assisted_living = "assisted_living"
    inpatient_rehab = "inpatient_rehab"  # IRF / acute rehab
    ltac = "ltac"  # long-term acute care
    hospice_home = "hospice_home"
    hospice_facility = "hospice_facility"
    ama = "ama"  # against medical advice
    expired = "expired"
    undetermined = "undetermined"


class DispositionStatus(str, Enum):
    """Lifecycle of the discharge-planning process for an encounter."""

    undetermined = "undetermined"  # no plan yet
    predicted = "predicted"  # agent/team has a leading prediction
    decided = "decided"  # team committed to a disposition
    in_progress = "in_progress"  # actively arranging (calls, auths, orders)
    ready = "ready"  # all barriers cleared, ready to discharge
    discharged = "discharged"


class ConditionCategory(str, Enum):
    problem_list_item = "problem-list-item"
    encounter_diagnosis = "encounter-diagnosis"


class ClinicalStatus(str, Enum):
    active = "active"
    recurrence = "recurrence"
    relapse = "relapse"
    inactive = "inactive"
    remission = "remission"
    resolved = "resolved"


class ObservationCategory(str, Enum):
    vital_signs = "vital-signs"
    laboratory = "laboratory"
    imaging = "imaging"
    survey = "survey"


class ObservationStatus(str, Enum):
    registered = "registered"
    preliminary = "preliminary"
    pending = "pending"  # ordered, specimen/result not yet available
    final = "final"
    amended = "amended"
    cancelled = "cancelled"


class ReportStatus(str, Enum):
    registered = "registered"
    partial = "partial"
    preliminary = "preliminary"
    pending = "pending"
    final = "final"
    cancelled = "cancelled"


class MedicationStatus(str, Enum):
    active = "active"
    on_hold = "on-hold"
    completed = "completed"
    stopped = "stopped"
    draft = "draft"  # ordered but not yet signed/active
    cancelled = "cancelled"


class NoteType(str, Enum):
    progress = "progress"
    history_and_physical = "history_and_physical"
    discharge_summary = "discharge_summary"
    consult = "consult"
    case_management = "case_management"
    nursing = "nursing"
    social_work = "social_work"
    therapy = "therapy"  # PT/OT/SLP eval
    after_visit_summary = "after_visit_summary"
    family_communication = "family_communication"  # calls/discussions with family re: dispo preferences


class NoteStatus(str, Enum):
    draft = "draft"  # pended, not signed
    signed = "signed"
    amended = "amended"


class OrderType(str, Enum):
    lab = "lab"
    medication = "medication"
    imaging = "imaging"
    consult = "consult"  # e.g. PM&R, PT/OT, social work
    nursing = "nursing"  # e.g. isolation, foley care
    dispo = "dispo"  # discharge / placement order
    referral = "referral"


class OrderStatus(str, Enum):
    """Order lifecycle.

    ``draft`` == "pended" in Epic parlance: saved but not signed. Agents create
    orders as drafts for a clinician to sign, or sign directly when authorized.
    """

    draft = "draft"  # pended, awaiting signature
    signed = "signed"  # signed, active/in-progress (e.g. lab collected)
    completed = "completed"  # fulfilled / resulted
    cancelled = "cancelled"
    discontinued = "discontinued"


class TaskType(str, Enum):
    call_snf = "call_snf"
    call_family = "call_family"
    call_pcp = "call_pcp"
    order_lab = "order_lab"
    draft_consult = "draft_consult"
    insurance_auth = "insurance_auth"
    collect_preference = "collect_preference"
    verify_eligibility = "verify_eligibility"
    arrange_transport = "arrange_transport"
    other = "other"


class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    blocked = "blocked"
    completed = "completed"
    cancelled = "cancelled"


class FacilityType(str, Enum):
    snf = "snf"
    assisted_living = "assisted_living"
    inpatient_rehab = "inpatient_rehab"
    ltac = "ltac"
    hospice = "hospice"
    home_health = "home_health"
    dme = "dme"  # durable medical equipment


class CommunicationDirection(str, Enum):
    outbound = "outbound"
    inbound = "inbound"


class CommunicationModality(str, Enum):
    phone = "phone"
    sms = "sms"
    fax = "fax"
    email = "email"
    portal = "portal"


class PartyType(str, Enum):
    family = "family"
    patient = "patient"
    snf = "snf"
    facility = "facility"
    pcp = "pcp"
    insurance = "insurance"
    other = "other"
