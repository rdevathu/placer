"""SQLModel table models.

Importing this package registers every table on ``SQLModel.metadata`` so
``create_all`` / ``drop_all`` see the full schema.
"""

from .clinical import (
    Condition,
    DiagnosticReport,
    Encounter,
    Immunization,
    Medication,
    Note,
    Observation,
    Order,
    Patient,
    Procedure,
)
from .dispo import CareTask, Communication, DispoAssessment, Facility
from .events import Event

__all__ = [
    "Patient",
    "Encounter",
    "Condition",
    "Observation",
    "DiagnosticReport",
    "Medication",
    "Procedure",
    "Immunization",
    "Note",
    "Order",
    "DispoAssessment",
    "Facility",
    "CareTask",
    "Communication",
    "Event",
]
