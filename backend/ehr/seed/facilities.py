"""Seed a small set of post-acute facilities agents can place patients into.

Bed counts are deliberately varied (including a full SNF and a COVID-accepting
one) so the placement-search workflow has something to reason about.
"""

from __future__ import annotations

from sqlmodel import Session

from ..models import Facility

# Data as plain dicts; fresh Facility instances are built on every seed call so
# the same ORM objects are never reused across sessions (which would fail to
# re-insert on a second reset).
_FACILITY_DATA = [
    dict(
        id="fac-sunny-acres",
        name="Sunny Acres Skilled Nursing",
        facility_type="snf",
        city="Chelsea",
        state="MA",
        phone="+1-617-555-0142",
        total_beds=120,
        available_beds=3,
        accepts_covid_positive=False,
        accepts_medicaid=True,
        insurance_accepted=["Medicare", "Medicaid", "BlueCross"],
        specialties=["rehabilitation", "wound_care"],
        notes="Requires negative COVID PCR within 48h of admission.",
    ),
    dict(
        id="fac-riverside-rehab",
        name="Riverside Rehabilitation & Nursing",
        facility_type="snf",
        city="Cambridge",
        state="MA",
        phone="+1-617-555-0173",
        total_beds=90,
        available_beds=0,
        accepts_covid_positive=True,
        accepts_medicaid=True,
        insurance_accepted=["Medicare", "Medicaid"],
        specialties=["rehabilitation", "dialysis"],
        notes="Currently at capacity; maintains a waitlist.",
    ),
    dict(
        id="fac-bayview-irf",
        name="Bayview Acute Inpatient Rehab",
        facility_type="inpatient_rehab",
        city="Boston",
        state="MA",
        phone="+1-617-555-0198",
        total_beds=40,
        available_beds=5,
        accepts_covid_positive=False,
        accepts_medicaid=True,
        insurance_accepted=["Medicare", "BlueCross", "Aetna"],
        specialties=["stroke_rehab", "brain_injury", "PMR"],
        notes="Requires 3h/day therapy tolerance and PM&R consult to qualify.",
    ),
    dict(
        id="fac-elmwood-alf",
        name="Elmwood Assisted Living",
        facility_type="assisted_living",
        city="Somerville",
        state="MA",
        phone="+1-617-555-0111",
        total_beds=60,
        available_beds=8,
        accepts_covid_positive=False,
        accepts_medicaid=False,
        insurance_accepted=["Private Pay", "LTC Insurance"],
        specialties=["memory_care"],
        notes="Private pay; ADL assistance but not skilled nursing.",
    ),
    dict(
        id="fac-harbor-ltac",
        name="Harbor Long-Term Acute Care",
        facility_type="ltac",
        city="Boston",
        state="MA",
        phone="+1-617-555-0155",
        total_beds=30,
        available_beds=2,
        accepts_covid_positive=True,
        accepts_medicaid=True,
        insurance_accepted=["Medicare", "Medicaid"],
        specialties=["ventilator", "complex_wound", "dialysis"],
        notes="For medically complex patients needing prolonged acute care.",
    ),
    dict(
        id="fac-peaceful-hospice",
        name="Peaceful Passages Hospice",
        facility_type="hospice",
        city="Newton",
        state="MA",
        phone="+1-617-555-0166",
        total_beds=20,
        available_beds=6,
        accepts_covid_positive=True,
        accepts_medicaid=True,
        insurance_accepted=["Medicare", "Medicaid", "BlueCross"],
        specialties=["inpatient_hospice", "home_hospice"],
        notes="Offers both general inpatient and home hospice.",
    ),
    dict(
        id="fac-hometeam-hh",
        name="HomeTeam Home Health",
        facility_type="home_health",
        city="Chelsea",
        state="MA",
        phone="+1-617-555-0120",
        total_beds=None,
        available_beds=None,
        accepts_covid_positive=True,
        accepts_medicaid=True,
        insurance_accepted=["Medicare", "Medicaid", "BlueCross", "Aetna"],
        specialties=["skilled_nursing_visits", "physical_therapy", "IV_infusion"],
        notes="Intermittent skilled visits in the home; 48h to start of care.",
    ),
]


def seed_facilities(session: Session) -> int:
    for data in _FACILITY_DATA:
        session.add(Facility(**data))
    return len(_FACILITY_DATA)
