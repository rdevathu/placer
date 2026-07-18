"""Flatten the provided Synthea/Abridge FHIR R4 records into the EHR schema.

The source is ``synthetic-examples/synthetic-ambient-fhir-25.jsonl`` — one
encounter per patient. We map each FHIR resource to a flat row and stash the
original under ``raw_fhir``. FHIR references (``urn:uuid:``, ``Practitioner?...``)
are resolved to display strings where possible and otherwise dropped, so agents
never try to follow an unresolvable reference.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any, Optional

from sqlmodel import Session

from .. import config
from ..models import (
    Condition,
    DiagnosticReport,
    Encounter,
    Immunization,
    Medication,
    Note,
    Observation,
    Patient,
    Procedure,
)

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Best-effort ISO-8601 -> naive datetime (tzinfo dropped for SQLite)."""
    if not value or not isinstance(value, str):
        return None
    v = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        # Fall back to date-only strings.
        try:
            return datetime.combine(date.fromisoformat(value[:10]), datetime.min.time())
        except ValueError:
            return None
    return dt.replace(tzinfo=None)


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def first_coding(concept: Optional[dict]) -> dict:
    """Return the first coding dict of a CodeableConcept, or {}."""
    if not concept:
        return {}
    coding = concept.get("coding") or []
    return coding[0] if coding else {}


def concept_text(concept: Optional[dict]) -> Optional[str]:
    """Human display for a CodeableConcept: prefer .text, then coding.display."""
    if not concept:
        return None
    if concept.get("text"):
        return concept["text"]
    return first_coding(concept).get("display")


_NPI_RE = re.compile(r"us-npi\|(\d+)")


def extract_npi(reference: Optional[str]) -> Optional[str]:
    if not reference:
        return None
    m = _NPI_RE.search(reference)
    return m.group(1) if m else None


def strip_urn(reference: Optional[str]) -> Optional[str]:
    """'urn:uuid:abc' -> 'abc'; pass through bare ids."""
    if not reference:
        return None
    return reference.split("urn:uuid:")[-1]


# ---------------------------------------------------------------------------
# Per-resource mappers
# ---------------------------------------------------------------------------


def _map_patient(fhir: dict, mrn: str) -> Patient:
    names = fhir.get("name") or [{}]
    name = names[0]
    given = " ".join(name.get("given") or [])
    family = name.get("family")
    prefix = " ".join(name.get("prefix") or []) or None
    full_name = " ".join(part for part in [prefix, given, family] if part) or None

    address = (fhir.get("address") or [{}])[0]
    language = concept_text((fhir.get("communication") or [{}])[0].get("language"))

    return Patient(
        id=fhir["id"],
        mrn=mrn,
        family_name=family,
        given_name=given or None,
        prefix=prefix,
        full_name=full_name,
        gender=fhir.get("gender"),
        birth_date=parse_date(fhir.get("birthDate")),
        deceased=bool(fhir.get("deceasedBoolean") or fhir.get("deceasedDateTime")),
        marital_status=concept_text(fhir.get("maritalStatus")),
        language=language,
        city=address.get("city"),
        state=address.get("state"),
        raw_fhir=fhir,
    )


def _map_encounter(fhir: dict, patient_id: str, visit_title: Optional[str]) -> Encounter:
    klass = fhir.get("class") or {}
    etype = (fhir.get("type") or [{}])[0]
    type_coding = first_coding(etype)
    period = fhir.get("period") or {}

    attending_name = None
    attending_npi = None
    for part in fhir.get("participant") or []:
        individual = part.get("individual") or {}
        if individual.get("display"):
            attending_name = individual["display"]
            attending_npi = extract_npi(individual.get("reference"))
            break

    location = (fhir.get("location") or [{}])[0].get("location") or {}
    reason = (fhir.get("reasonCode") or [{}])[0]

    return Encounter(
        id=fhir["id"],
        patient_id=patient_id,
        status=fhir.get("status") or "finished",
        class_code=klass.get("code"),
        class_display=klass.get("display") or klass.get("code"),
        type_code=type_coding.get("code"),
        type_text=concept_text(etype),
        visit_title=visit_title,
        reason_code=first_coding(reason).get("code"),
        reason_text=concept_text(reason),
        period_start=parse_dt(period.get("start")),
        period_end=parse_dt(period.get("end")),
        location_display=location.get("display"),
        service_provider_display=(fhir.get("serviceProvider") or {}).get("display"),
        attending_name=attending_name,
        attending_npi=attending_npi,
        raw_fhir=fhir,
    )


def _map_condition(fhir: dict, patient_id: str, encounter_id: str) -> Condition:
    code = fhir.get("code") or {}
    coding = first_coding(code)
    category = (fhir.get("category") or [{}])[0]
    return Condition(
        id=fhir["id"],
        patient_id=patient_id,
        encounter_id=encounter_id,
        code_system=coding.get("system"),
        code=coding.get("code"),
        display=concept_text(code),
        category=first_coding(category).get("code"),
        clinical_status=first_coding(fhir.get("clinicalStatus")).get("code"),
        verification_status=first_coding(fhir.get("verificationStatus")).get("code"),
        onset_date=parse_dt(fhir.get("onsetDateTime")),
        abatement_date=parse_dt(fhir.get("abatementDateTime")),
        recorded_date=parse_dt(fhir.get("recordedDate")),
        raw_fhir=fhir,
    )


_VITAL_CATEGORIES = {"vital-signs"}


def _map_observation(fhir: dict, patient_id: str, encounter_id: str) -> Observation:
    code = fhir.get("code") or {}
    coding = first_coding(code)
    category_code = first_coding((fhir.get("category") or [{}])[0]).get("code") or "laboratory"

    value_num = None
    value_unit = None
    value_string = None
    has_components = bool(fhir.get("component"))
    if "valueQuantity" in fhir:
        vq = fhir["valueQuantity"]
        value_num = vq.get("value")
        value_unit = vq.get("unit")
    elif "valueCodeableConcept" in fhir:
        value_string = concept_text(fhir["valueCodeableConcept"])
    elif "valueString" in fhir:
        value_string = fhir["valueString"]

    ref_range = (fhir.get("referenceRange") or [{}])[0]

    status = fhir.get("status") or "final"
    return Observation(
        id=fhir["id"],
        patient_id=patient_id,
        encounter_id=encounter_id,
        category=category_code,
        loinc_code=coding.get("code"),
        display=concept_text(code),
        value_num=value_num,
        value_unit=value_unit,
        value_string=value_string,
        has_components=has_components,
        reference_range_low=(ref_range.get("low") or {}).get("value"),
        reference_range_high=(ref_range.get("high") or {}).get("value"),
        interpretation=concept_text((fhir.get("interpretation") or [{}])[0]) if fhir.get("interpretation") else None,
        status=status,
        effective_time=parse_dt(fhir.get("effectiveDateTime")),
        issued_time=parse_dt(fhir.get("issued")),
        raw_fhir=fhir,
    )


def _map_report(fhir: dict, patient_id: str, encounter_id: str) -> DiagnosticReport:
    code = fhir.get("code") or {}
    coding = first_coding(code)
    category = first_coding((fhir.get("category") or [{}])[0]).get("code")
    return DiagnosticReport(
        id=fhir["id"],
        patient_id=patient_id,
        encounter_id=encounter_id,
        loinc_code=coding.get("code"),
        display=concept_text(code),
        category=category,
        status=fhir.get("status") or "final",
        effective_time=parse_dt(fhir.get("effectiveDateTime")),
        issued_time=parse_dt(fhir.get("issued")),
        performer_display=(fhir.get("performer") or [{}])[0].get("display"),
        raw_fhir=fhir,
    )


def _map_medication(fhir: dict, patient_id: str, encounter_id: str) -> Medication:
    # medicationReference is generally unresolvable; fall back through options.
    display = (
        concept_text(fhir.get("medicationCodeableConcept"))
        or (fhir.get("medicationReference") or {}).get("display")
    )
    med_coding = first_coding(fhir.get("medicationCodeableConcept"))
    dosage = (fhir.get("dosageInstruction") or [{}])[0]
    return Medication(
        id=fhir["id"],
        patient_id=patient_id,
        encounter_id=encounter_id,
        code_system=med_coding.get("system"),
        code=med_coding.get("code"),
        display=display,
        dosage_text=dosage.get("text"),
        status=fhir.get("status") or "active",
        intent=fhir.get("intent"),
        authored_on=parse_dt(fhir.get("authoredOn")),
        requester_display=(fhir.get("requester") or {}).get("display"),
        raw_fhir=fhir,
    )


def _map_procedure(fhir: dict, patient_id: str, encounter_id: str) -> Procedure:
    code = fhir.get("code") or {}
    coding = first_coding(code)
    period = fhir.get("performedPeriod") or {}
    return Procedure(
        id=fhir["id"],
        patient_id=patient_id,
        encounter_id=encounter_id,
        code_system=coding.get("system"),
        code=coding.get("code"),
        display=concept_text(code),
        status=fhir.get("status"),
        performed_start=parse_dt(period.get("start") or fhir.get("performedDateTime")),
        performed_end=parse_dt(period.get("end")),
        location_display=(fhir.get("location") or {}).get("display"),
        raw_fhir=fhir,
    )


def _map_immunization(fhir: dict, patient_id: str, encounter_id: str) -> Immunization:
    vaccine = fhir.get("vaccineCode") or {}
    coding = first_coding(vaccine)
    return Immunization(
        id=fhir["id"],
        patient_id=patient_id,
        encounter_id=encounter_id,
        cvx_code=coding.get("code"),
        display=concept_text(vaccine),
        status=fhir.get("status"),
        occurrence_date=parse_dt(fhir.get("occurrenceDateTime")),
        raw_fhir=fhir,
    )


# Dispatch table for the related_resources groups we flatten row-per-resource.
_MAPPERS = {
    "Condition": _map_condition,
    "Observation": _map_observation,
    "DiagnosticReport": _map_report,
    "MedicationRequest": _map_medication,
    "Procedure": _map_procedure,
    "Immunization": _map_immunization,
}


def _note_type_for(visit_type: Optional[str]) -> str:
    vt = (visit_type or "").lower()
    if "admission" in vt or "hospital" in vt or "hospice" in vt:
        return "history_and_physical"
    return "progress"


# ---------------------------------------------------------------------------
# Record + file import
# ---------------------------------------------------------------------------


def import_record(session: Session, record: dict, mrn: str) -> None:
    """Flatten a single JSONL record into the session (no commit)."""
    meta = record.get("metadata") or {}
    patient_fhir = (record.get("patient_context") or {}).get("patient") or {}
    encounter_fhir = (record.get("encounter_fhir") or {}).get("encounter") or {}
    related = (record.get("encounter_fhir") or {}).get("related_resources") or {}

    patient_id = patient_fhir.get("id") or meta.get("patient_id")
    encounter_id = encounter_fhir.get("id") or meta.get("encounter_id")

    session.add(_map_patient(patient_fhir, mrn))
    session.add(_map_encounter(encounter_fhir, patient_id, meta.get("visit_title")))

    # report result-reference -> observation id, resolved after both exist.
    obs_to_report: dict[str, str] = {}
    for report in related.get("DiagnosticReport") or []:
        for result in report.get("result") or []:
            obs_id = strip_urn(result.get("reference"))
            if obs_id:
                obs_to_report[obs_id] = report["id"]

    for resource_type, mapper in _MAPPERS.items():
        for resource in related.get(resource_type) or []:
            try:
                row = mapper(resource, patient_id, encounter_id)
            except Exception:  # noqa: BLE001 — one malformed resource shouldn't abort import
                continue
            if isinstance(row, Observation) and row.id in obs_to_report:
                row.diagnostic_report_id = obs_to_report[row.id]
            session.add(row)

    # Clinical note (SOAP) + after-visit summary as documentation rows.
    note_text = record.get("note")
    if note_text:
        session.add(
            Note(
                patient_id=patient_id,
                encounter_id=encounter_id,
                note_type=_note_type_for(meta.get("visit_type")),
                title=meta.get("visit_title"),
                text=note_text,
                author=(encounter_fhir.get("participant") or [{}])[0].get("individual", {}).get("display"),
                author_role="physician",
                status="signed",
                signed_at=parse_dt((encounter_fhir.get("period") or {}).get("end")),
                raw_fhir={"transcript": record.get("transcript"), "visit_type": meta.get("visit_type")},
            )
        )
    avs = record.get("after_visit_summary")
    if avs:
        session.add(
            Note(
                patient_id=patient_id,
                encounter_id=encounter_id,
                note_type="after_visit_summary",
                title="After Visit Summary",
                text=avs,
                author_role="system",
                status="signed",
            )
        )


def import_fhir_file(session: Session, path: Optional[Any] = None) -> int:
    """Import every JSONL record from ``path`` (defaults to the configured file).

    Returns the number of records imported. Does not commit — the caller owns
    the transaction.
    """
    src = path or config.SYNTHETIC_JSONL
    count = 0
    with open(src, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            count += 1
            import_record(session, record, mrn=f"MRN{count:04d}")
    return count
