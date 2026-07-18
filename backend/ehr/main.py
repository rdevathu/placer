"""FastAPI application entrypoint.

Run with:  uvicorn ehr.main:app --reload
Docs:      http://localhost:8000/docs   (OpenAPI at /openapi.json)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from . import config
from .db import engine, init_db
from .models import Patient
from .routers import all_routers
from .seed import reset_and_seed

DESCRIPTION = """
A lightweight, Epic-like **dummy EHR** for building and demoing healthcare agents.

It exposes clean REST endpoints over a single SQLite database so agents can
reliably traverse a patient's chart and take clinical actions. Built for a
discharge-**disposition** planning use case: predict where a hospitalized
patient will go after discharge and work the barriers (call facilities/family,
pend labs, draft consults) in the background.

### Where to start
- `GET /patients?admitted=true` — the inpatient worklist (active encounters).
- `GET /patients/{id}/chart` — one-call chart snapshot for an agent.
- `GET /patients/{id}/labs?status=pending` — labs still in flight.
- `POST /orders` — pend or sign an order (labs auto-create a pending result).
- `GET /patients/{id}/dispo-assessments/current` — the current prediction.
- `GET /facilities?facility_type=snf&has_available_beds=true` — placement search.
- `POST /admin/reset` — reset to the seed state to re-run the demo.

All data is synthetic. Enum values shown in request schemas are the accepted
vocabularies — send those exact strings.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if config.AUTO_SEED:
        with Session(engine) as session:
            empty = session.exec(select(Patient).limit(1)).first() is None
        if empty:
            reset_and_seed()
    yield


app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=DESCRIPTION,
    lifespan=lifespan,
)

# Open CORS — this is a local demo backend for a frontend + agents.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in all_routers:
    app.include_router(router)


@app.get("/", tags=["meta"], summary="Service metadata")
def root() -> dict:
    return {
        "service": config.API_TITLE,
        "version": config.API_VERSION,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "start_here": [
            "/patients?admitted=true",
            "/patients/{id}/chart",
            "/facilities?facility_type=snf&has_available_beds=true",
        ],
    }
