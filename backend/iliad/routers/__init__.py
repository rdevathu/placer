"""API routers, grouped one module per clinical domain."""

from . import (
    admin,
    care_tasks,
    communications,
    conditions,
    dispo,
    encounters,
    medications,
    notes,
    observations,
    orders,
    patients,
    placer,
    placer_ops,
)

# Order here controls tag order in the OpenAPI docs.
all_routers = [
    patients.router,
    encounters.router,
    conditions.router,
    observations.router,
    medications.router,
    orders.router,
    notes.router,
    dispo.router,
    care_tasks.router,
    communications.router,
    placer.router,
    placer_ops.router,
    admin.router,
]
