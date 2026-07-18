"""Placer Engine FastAPI entrypoint.

Run with:  uvicorn placer.main:app --port 8001
The dummy EHR is a separate service (default http://localhost:8000).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .api import routers as api_routers
from .db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=(
        "Agentic discharge-readiness engine for the Placer demo. Watches the "
        "dummy EHR event feed, maintains per-patient cases, and works "
        "disposition barriers in the background."
    ),
    lifespan=lifespan,
)

# Open CORS — local demo service consumed by a frontend on another port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in api_routers:
    app.include_router(router)


def _ehr_reachable() -> bool:
    """Best-effort ping of the EHR; never raises (health must not fail
    just because the EHR is down)."""
    try:
        resp = httpx.get(f"{config.EHR_BASE_URL}/", timeout=2.0)
        return resp.status_code < 500
    except Exception:
        return False


@app.get("/health", tags=["meta"], summary="Service health")
def health() -> dict:
    return {
        "status": "ok",
        "db": str(config.DB_PATH),
        "ehr_reachable": _ehr_reachable(),
    }
