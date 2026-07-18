"""Synthesize ACTIVE inpatients — the point of the demo.

The imported cohort is entirely historical (every encounter ``status=finished``),
so a disposition agent would have nothing live to act on. These hero patients
are admitted right now (``encounter.status='in-progress'``, ``period_end=NULL``)
with charts primed so disposition prediction is a *retrieval* problem, not an
extraction one — the signal lives in typed columns (living_situation, active
conditions, pending labs, dispo assessments) while a readable SOAP note is also
present for ambient-style agents.

IDs and MRNs are fixed so demo/agent scripts can hardcode them.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session

from ..models import (
    CareTask,
    Communication,
    Condition,
    DispoAssessment,
    Encounter,
    Medication,
    Note,
    Observation,
    Order,
    Patient,
)

# Deterministic "now" for reproducible demos (matches the project's current date).
NOW = datetime(2026, 7, 18, 8, 0, 0)


def _vital(patient_id, encounter_id, loinc, display, value, unit, when, low=None, high=None, flag=None):
    return Observation(
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


def _condition(patient_id, encounter_id, code, display, onset, status="active", category="encounter-diagnosis"):
    return Condition(
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


def _med(patient_id, encounter_id, display, dose, route, freq, category="inpatient"):
    return Medication(
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
        authored_on=NOW - timedelta(days=2),
    )


# ---------------------------------------------------------------------------
# Hero A — 78yo s/p ischemic stroke, lives alone, deconditioned -> likely SNF
# ---------------------------------------------------------------------------


def _hero_a(session: Session) -> None:
    pid, eid = "hero-a-stroke", "enc-hero-a"
    admit = NOW - timedelta(days=3)

    session.add(
        Patient(
            id=pid,
            mrn="MRN90001",
            family_name="Alvarez",
            given_name="Rosa",
            prefix="Mrs.",
            full_name="Mrs. Rosa Alvarez",
            gender="female",
            birth_date=datetime(1948, 2, 11).date(),
            marital_status="Widowed",
            language="English",
            city="Chelsea",
            state="MA",
            living_situation="lives_alone",
            code_status="full",
        )
    )
    session.add(
        Encounter(
            id=eid,
            patient_id=pid,
            status="in-progress",
            class_code="IMP",
            class_display="inpatient encounter",
            type_text="Hospital admission (procedure)",
            visit_title="Inpatient admission — acute ischemic stroke",
            reason_text="Acute ischemic stroke with left-sided weakness",
            period_start=admit,
            period_end=None,
            location_display="7 West — Neurology",
            service_provider_display="Placer General Hospital",
            attending_name="Dr. Priya Nadkarni",
            disposition_status="predicted",
        )
    )
    session.add_all([
        _condition(pid, eid, "422504002", "Ischemic stroke (disorder)", admit),
        _condition(pid, eid, "44695005", "Left hemiparesis (finding)", admit),
        _condition(pid, eid, "40739000", "Dysphagia (finding)", admit),
        _condition(pid, eid, "59621000", "Essential hypertension (disorder)", datetime(2015, 1, 1), category="problem-list-item"),
        _condition(pid, eid, "302866003", "Deconditioned (finding)", admit),
    ])
    session.add_all([
        _vital(pid, eid, "8867-4", "Heart rate", 82, "/min", NOW - timedelta(hours=4), 60, 100),
        _vital(pid, eid, "8480-6", "Systolic blood pressure", 158, "mm[Hg]", NOW - timedelta(hours=4), 90, 140, "H"),
        _vital(pid, eid, "2708-6", "Oxygen saturation", 96, "%", NOW - timedelta(hours=4), 94, 100),
        _vital(pid, eid, "8310-5", "Body temperature", 37.0, "Cel", NOW - timedelta(hours=4), 36.1, 37.8),
    ])
    session.add_all([
        _med(pid, eid, "Aspirin", "81 mg", "PO", "daily"),
        _med(pid, eid, "Atorvastatin", "80 mg", "PO", "nightly"),
        _med(pid, eid, "Lisinopril", "10 mg", "PO", "daily"),
    ])

    # Pending COVID test — required by the target SNF before it will accept her.
    covid = Observation(
        patient_id=pid,
        encounter_id=eid,
        category="laboratory",
        loinc_code="94500-6",
        display="SARS-CoV-2 (COVID-19) RNA [Presence] by NAA",
        status="pending",
        effective_time=NOW - timedelta(hours=2),
    )
    session.add(covid)
    session.flush()  # get covid.id for the linking order

    session.add(
        Order(
            id="ord-hero-a-covid",
            patient_id=pid,
            encounter_id=eid,
            order_type="lab",
            status="signed",
            code="94500-6",
            display="SARS-CoV-2 (COVID-19) NAA test",
            detail="SNF admission requirement — result pending.",
            priority="routine",
            ordered_by="Dr. Priya Nadkarni",
            signed_by="Dr. Priya Nadkarni",
            authored_at=NOW - timedelta(hours=2),
            signed_at=NOW - timedelta(hours=2),
            result_observation_id=covid.id,
        )
    )
    # Draft PM&R consult — pended by the agent, awaiting the team's signature.
    session.add(
        Order(
            id="ord-hero-a-pmr",
            patient_id=pid,
            encounter_id=eid,
            order_type="consult",
            status="draft",
            display="PM&R consult",
            detail="Evaluate rehab potential / therapy tolerance to support SNF vs acute-rehab placement.",
            priority="routine",
            ordered_by="dispo-agent",
            authored_at=NOW - timedelta(hours=1),
        )
    )

    session.add(
        Note(
            patient_id=pid,
            encounter_id=eid,
            note_type="history_and_physical",
            title="Neurology H&P — acute ischemic stroke",
            author="Dr. Priya Nadkarni",
            author_role="physician",
            status="signed",
            signed_at=admit,
            text=(
                "# History & Physical\n\n"
                "**HPI:** 78yo widowed woman who lives alone presented with acute left-sided "
                "weakness and slurred speech. MRI confirmed a right MCA ischemic stroke.\n\n"
                "**Hospital course:** Left hemiparesis and dysphagia. PT/OT note impaired mobility "
                "and she requires max assist for transfers. Bedside swallow failed; on a modified diet.\n\n"
                "**Social:** Lives alone in a second-floor apartment, no elevator. Daughter lives "
                "out of state. Previously independent in ADLs.\n\n"
                "**Assessment & Plan:** Right MCA CVA. Deconditioned, not safe to return home alone. "
                "Anticipate skilled nursing facility placement for rehab. Await PM&R eval and "
                "clearance labs (COVID PCR for SNF)."
            ),
        )
    )

    session.add(
        DispoAssessment(
            id="dispo-hero-a",
            patient_id=pid,
            encounter_id=eid,
            predicted_disposition="snf",
            confidence=0.78,
            rationale=(
                "78yo, lives alone (2nd-floor walk-up), s/p right MCA stroke with left hemiparesis and "
                "dysphagia, requires max assist for transfers. Not safe for home. Skilled rehab needs "
                "point to SNF over acute inpatient rehab given current low therapy tolerance."
            ),
            barriers=[
                "Pending SARS-CoV-2 PCR required by target SNF",
                "PM&R consult not yet completed",
                "Family preference for facility not yet confirmed",
            ],
            alternatives=[
                {"disposition": "inpatient_rehab", "confidence": 0.15},
                {"disposition": "home_with_services", "confidence": 0.05},
            ],
            assessed_by="dispo-agent",
            is_current=True,
        )
    )

    session.add_all([
        CareTask(
            id="task-hero-a-family",
            patient_id=pid,
            encounter_id=eid,
            task_type="call_family",
            title="Call daughter re: SNF preference",
            description="Confirm preferred SNF and gather insurance details.",
            status="pending",
            priority="high",
            assigned_to="dispo-agent",
            due_at=NOW + timedelta(hours=6),
        ),
        CareTask(
            id="task-hero-a-snf",
            patient_id=pid,
            encounter_id=eid,
            task_type="call_snf",
            title="Call Sunny Acres re: bed availability",
            description="Verify bed availability and COVID test requirement.",
            status="in_progress",
            priority="high",
            assigned_to="dispo-agent",
            related_facility_id="fac-sunny-acres",
            due_at=NOW + timedelta(hours=4),
        ),
    ])
    session.add(
        Communication(
            patient_id=pid,
            care_task_id="task-hero-a-snf",
            facility_id="fac-sunny-acres",
            direction="outbound",
            modality="phone",
            party_type="snf",
            party_name="Sunny Acres admissions",
            summary="Confirmed 3 beds open. They require a negative COVID PCR within 48h before accepting.",
            outcome="bed_available",
            occurred_at=NOW - timedelta(hours=1),
        )
    )


# ---------------------------------------------------------------------------
# Hero B — 66yo CHF exacerbation, lives with spouse, improving -> home + HH
# ---------------------------------------------------------------------------


def _hero_b(session: Session) -> None:
    pid, eid = "hero-b-chf", "enc-hero-b"
    admit = NOW - timedelta(days=2)

    session.add(
        Patient(
            id=pid, mrn="MRN90002", family_name="Okafor", given_name="Daniel", prefix="Mr.",
            full_name="Mr. Daniel Okafor", gender="male", birth_date=datetime(1960, 9, 3).date(),
            marital_status="Married", language="English", city="Cambridge", state="MA",
            living_situation="lives_with_family", code_status="full",
        )
    )
    session.add(
        Encounter(
            id=eid, patient_id=pid, status="in-progress", class_code="IMP",
            class_display="inpatient encounter", type_text="Hospital admission (procedure)",
            visit_title="Inpatient admission — acute CHF exacerbation",
            reason_text="Acute decompensated heart failure", period_start=admit, period_end=None,
            location_display="5 East — Cardiology", service_provider_display="Placer General Hospital",
            attending_name="Dr. Marcus Feld", disposition_status="predicted",
        )
    )
    session.add_all([
        _condition(pid, eid, "42343007", "Congestive heart failure (disorder)", datetime(2019, 6, 1), category="problem-list-item"),
        _condition(pid, eid, "44054006", "Type 2 diabetes mellitus (disorder)", datetime(2012, 1, 1), category="problem-list-item"),
    ])
    session.add_all([
        _vital(pid, eid, "8867-4", "Heart rate", 74, "/min", NOW - timedelta(hours=3), 60, 100),
        _vital(pid, eid, "2708-6", "Oxygen saturation", 97, "%", NOW - timedelta(hours=3), 94, 100),
        _vital(pid, eid, "29463-7", "Body weight", 84.1, "kg", NOW - timedelta(hours=6)),
    ])
    session.add_all([
        _med(pid, eid, "Furosemide", "40 mg", "IV", "BID"),
        _med(pid, eid, "Metoprolol succinate", "50 mg", "PO", "daily"),
        _med(pid, eid, "Lisinopril", "20 mg", "PO", "daily"),
    ])
    session.add(
        Note(
            patient_id=pid, encounter_id=eid, note_type="progress",
            title="Cardiology progress note", author="Dr. Marcus Feld", author_role="physician",
            status="signed", signed_at=NOW - timedelta(hours=5),
            text=(
                "# Progress Note\n\n**Subjective:** Breathing much improved, no orthopnea overnight.\n\n"
                "**Objective:** Diuresing well, net negative 2.5L. O2 sat 97% on room air. Lungs clearing.\n\n"
                "**Assessment/Plan:** CHF exacerbation improving on IV diuresis, transitioning to PO. "
                "Lives with wife who is engaged and able to assist. Ambulatory at baseline. Anticipate "
                "discharge home with home-health nursing for weights/med reconciliation. Likely 1–2 more days."
            ),
        )
    )
    session.add(
        DispoAssessment(
            id="dispo-hero-b", patient_id=pid, encounter_id=eid,
            predicted_disposition="home_with_services", confidence=0.71,
            rationale=(
                "66yo with CHF exacerbation improving rapidly on diuresis, ambulatory at baseline, lives "
                "with an engaged spouse. Home discharge with home-health nursing for daily weights and med "
                "reconciliation is most likely; no skilled facility indicated."
            ),
            barriers=["Home-health referral not yet placed", "Transition IV to PO diuretic and observe"],
            alternatives=[{"disposition": "home", "confidence": 0.22}, {"disposition": "snf", "confidence": 0.07}],
            assessed_by="dispo-agent", is_current=True,
        )
    )
    session.add(
        CareTask(
            id="task-hero-b-hh", patient_id=pid, encounter_id=eid, task_type="draft_consult",
            title="Place home-health referral", description="Skilled nursing visits for CHF weight monitoring.",
            status="pending", priority="medium", assigned_to="dispo-agent", related_facility_id="fac-hometeam-hh",
        )
    )


# ---------------------------------------------------------------------------
# Hero C — 84yo metastatic cancer, comfort-focused -> hospice
# ---------------------------------------------------------------------------


def _hero_c(session: Session) -> None:
    pid, eid = "hero-c-hospice", "enc-hero-c"
    admit = NOW - timedelta(days=5)

    session.add(
        Patient(
            id=pid, mrn="MRN90003", family_name="Bianchi", given_name="Giulia", prefix="Mrs.",
            full_name="Mrs. Giulia Bianchi", gender="female", birth_date=datetime(1942, 4, 27).date(),
            marital_status="Widowed", language="English", city="Newton", state="MA",
            living_situation="lives_with_family", code_status="DNR",
        )
    )
    session.add(
        Encounter(
            id=eid, patient_id=pid, status="in-progress", class_code="IMP",
            class_display="inpatient encounter", type_text="Hospital admission (procedure)",
            visit_title="Inpatient admission — metastatic pancreatic cancer, failure to thrive",
            reason_text="Metastatic pancreatic cancer with intractable pain and cachexia",
            period_start=admit, period_end=None, location_display="8 North — Oncology",
            service_provider_display="Placer General Hospital", attending_name="Dr. Helen Sørensen",
            disposition_status="predicted",
        )
    )
    session.add_all([
        _condition(pid, eid, "363418001", "Malignant tumor of pancreas (disorder)", datetime(2025, 11, 1), category="problem-list-item"),
        _condition(pid, eid, "94222008", "Secondary malignant neoplasm of liver (disorder)", datetime(2026, 3, 1)),
        _condition(pid, eid, "267024001", "Cachexia (finding)", admit),
    ])
    session.add_all([
        _vital(pid, eid, "8867-4", "Heart rate", 104, "/min", NOW - timedelta(hours=2), 60, 100, "H"),
        _vital(pid, eid, "8480-6", "Systolic blood pressure", 92, "mm[Hg]", NOW - timedelta(hours=2), 90, 140),
        _vital(pid, eid, "2708-6", "Oxygen saturation", 93, "%", NOW - timedelta(hours=2), 94, 100, "L"),
    ])
    session.add_all([
        _med(pid, eid, "Morphine", "2 mg", "IV", "q2h PRN pain"),
        _med(pid, eid, "Ondansetron", "4 mg", "IV", "q8h PRN nausea"),
    ])
    session.add(
        Note(
            patient_id=pid, encounter_id=eid, note_type="progress",
            title="Palliative care consult note", author="Dr. Omar Haddad", author_role="physician",
            status="signed", signed_at=NOW - timedelta(days=1),
            text=(
                "# Palliative Care Consult\n\n**HPI:** 84yo with metastatic pancreatic cancer, declining "
                "functional status, poor oral intake, escalating pain.\n\n"
                "**Goals of care:** Family meeting held. Patient and daughter wish to focus on comfort. "
                "Code status DNR/DNI confirmed. No further disease-directed therapy desired.\n\n"
                "**Plan:** Transition to hospice. Family prefers home hospice if symptoms controllable; "
                "consider inpatient hospice if pain remains refractory."
            ),
        )
    )
    session.add(
        DispoAssessment(
            id="dispo-hero-c", patient_id=pid, encounter_id=eid,
            predicted_disposition="hospice_home", confidence=0.82,
            rationale=(
                "84yo with metastatic pancreatic cancer, cachexia, comfort-focused goals of care (DNR/DNI), "
                "no disease-directed therapy desired. Family prefers home hospice. Hospice is the clear "
                "disposition; inpatient hospice is the fallback if pain is refractory."
            ),
            barriers=["Hospice election paperwork pending", "Confirm home vs inpatient hospice with family"],
            alternatives=[{"disposition": "hospice_facility", "confidence": 0.16}],
            assessed_by="dispo-agent", is_current=True,
        )
    )
    session.add(
        CareTask(
            id="task-hero-c-hospice", patient_id=pid, encounter_id=eid, task_type="verify_eligibility",
            title="Coordinate hospice election", description="Confirm home vs inpatient hospice; start paperwork.",
            status="pending", priority="high", assigned_to="dispo-agent", related_facility_id="fac-peaceful-hospice",
        )
    )


# ---------------------------------------------------------------------------
# Hero D — 71yo pneumonia, ambiguous signal -> tests agent reasoning
# ---------------------------------------------------------------------------


def _hero_d(session: Session) -> None:
    pid, eid = "hero-d-ambiguous", "enc-hero-d"
    admit = NOW - timedelta(days=2)

    session.add(
        Patient(
            id=pid, mrn="MRN90004", family_name="Nguyen", given_name="Tom", prefix="Mr.",
            full_name="Mr. Tom Nguyen", gender="male", birth_date=datetime(1955, 12, 19).date(),
            marital_status="Married", language="English", city="Somerville", state="MA",
            living_situation=None,  # unknown — a gap the agent should flag/fill
            code_status="full",
        )
    )
    session.add(
        Encounter(
            id=eid, patient_id=pid, status="in-progress", class_code="IMP",
            class_display="inpatient encounter", type_text="Hospital admission (procedure)",
            visit_title="Inpatient admission — community-acquired pneumonia",
            reason_text="Community-acquired pneumonia with hypoxia", period_start=admit, period_end=None,
            location_display="6 West — Medicine", service_provider_display="Placer General Hospital",
            attending_name="Dr. Aisha Rahman", disposition_status="undetermined",
        )
    )
    session.add_all([
        _condition(pid, eid, "385093006", "Community acquired pneumonia (disorder)", admit),
        _condition(pid, eid, "13645005", "Chronic obstructive pulmonary disease (disorder)", datetime(2018, 1, 1), category="problem-list-item"),
    ])
    session.add_all([
        _vital(pid, eid, "8867-4", "Heart rate", 88, "/min", NOW - timedelta(hours=5), 60, 100),
        _vital(pid, eid, "2708-6", "Oxygen saturation", 91, "%", NOW - timedelta(hours=5), 94, 100, "L"),
        _vital(pid, eid, "8310-5", "Body temperature", 38.2, "Cel", NOW - timedelta(hours=5), 36.1, 37.8, "H"),
    ])
    session.add_all([
        _med(pid, eid, "Ceftriaxone", "1 g", "IV", "daily"),
        _med(pid, eid, "Azithromycin", "500 mg", "IV", "daily"),
    ])
    session.add(
        Note(
            patient_id=pid, encounter_id=eid, note_type="progress",
            title="Medicine progress note", author="Dr. Aisha Rahman", author_role="physician",
            status="signed", signed_at=NOW - timedelta(hours=6),
            text=(
                "# Progress Note\n\n**Subjective:** Still requiring 2L O2, mild dyspnea on exertion.\n\n"
                "**Objective:** Febrile to 38.2C, O2 sat 91% on 2L. Crackles right base.\n\n"
                "**Assessment/Plan:** CAP with COPD, day 2 of IV antibiotics. Oxygen requirement and "
                "deconditioning unclear. Social situation not documented — need to clarify home support "
                "and baseline function before disposition. PT to assess."
            ),
        )
    )
    session.add(
        DispoAssessment(
            id="dispo-hero-d", patient_id=pid, encounter_id=eid,
            predicted_disposition="undetermined", confidence=0.4,
            rationale=(
                "71yo with CAP and COPD, still oxygen-dependent on day 2. Disposition genuinely uncertain: "
                "could be home if he recovers to baseline, or SNF if deconditioning persists. Key data "
                "missing — living situation and baseline function are undocumented. Recommend PT eval and "
                "a call to clarify home support before predicting."
            ),
            barriers=["Living situation unknown", "Oxygen requirement not yet resolved", "Awaiting PT functional assessment"],
            alternatives=[{"disposition": "home", "confidence": 0.35}, {"disposition": "snf", "confidence": 0.25}],
            assessed_by="dispo-agent", is_current=True,
        )
    )
    session.add(
        CareTask(
            id="task-hero-d-pt", patient_id=pid, encounter_id=eid, task_type="collect_preference",
            title="Clarify home support & baseline function", description="Call patient/family to document living situation and ADL baseline.",
            status="pending", priority="medium", assigned_to="dispo-agent",
        )
    )


def seed_hero_patients(session: Session) -> int:
    """Create all hero patients. Returns the number of hero patients created."""
    builders = [_hero_a, _hero_b, _hero_c, _hero_d]
    for build in builders:
        build(session)
    return len(builders)
