"""Seeding and reset orchestration.

``reset_and_seed`` is the single primitive shared by the CLI (`iliad reset`) and
the admin endpoint (`POST /admin/reset`). It always drops, recreates, and
reseeds so a demo can be re-run from a known state as many times as needed.
"""

from __future__ import annotations

from sqlmodel import Session, select

from ..db import engine, fk_enforcement, reset_db
from ..models import (
    CareTask,
    Communication,
    Condition,
    DiagnosticReport,
    DispoAssessment,
    Encounter,
    Facility,
    Immunization,
    Medication,
    Note,
    Observation,
    Order,
    Patient,
    PlacerMessage,
    Procedure,
)
from .facilities import seed_facilities
from .hero_patients import seed_hero_patients

_COUNT_MODELS = {
    "patients": Patient,
    "encounters": Encounter,
    "conditions": Condition,
    "observations": Observation,
    "diagnostic_reports": DiagnosticReport,
    "medications": Medication,
    "procedures": Procedure,
    "immunizations": Immunization,
    "notes": Note,
    "orders": Order,
    "dispo_assessments": DispoAssessment,
    "facilities": Facility,
    "care_tasks": CareTask,
    "communications": Communication,
    "placer_messages": PlacerMessage,
}


def row_counts(session: Session) -> dict[str, int]:
    """Return the number of rows in each table (for stats/health)."""
    from sqlalchemy import func

    counts: dict[str, int] = {}
    for name, model in _COUNT_MODELS.items():
        counts[name] = session.exec(select(func.count()).select_from(model)).one()
    return counts


def reset_and_seed(include_heroes: bool = True) -> dict[str, int]:
    """Drop everything, recreate the schema, and reseed. Returns row counts.

    Seeding runs with SQLite foreign-key enforcement disabled on the loading
    connection. Without ORM ``relationship()`` definitions, SQLAlchemy's flush
    orders inserts by add-order/mapper rather than FK dependency, which would
    trip constraints during a mixed bulk load. The data we insert is internally
    consistent, and FK enforcement remains ON for all runtime API connections.
    """
    reset_db()
    with fk_enforcement(False):
        with Session(engine) as session:
            seed_facilities(session)
            if include_heroes:
                seed_hero_patients(session)
            session.commit()
            counts = row_counts(session)
    return counts
