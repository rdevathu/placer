"""Placer Engine FastAPI entrypoint.

Run with:  uvicorn placer.main:app --port 8001
The dummy EHR is a separate service (default http://localhost:8000).
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .api import routers as api_routers
from .db import init_db

# The brain loop can be disabled (tests, frontend-only dev) via env.
_LOOP_ENABLED = os.environ.get("PLACER_LOOP_ENABLED", "true").lower() in {"1", "true", "yes"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    loop_task = None
    if _LOOP_ENABLED:
        from .brain.loop import engine_loop

        loop_task = asyncio.create_task(engine_loop(), name="placer-brain-loop")
    yield
    if loop_task is not None:
        loop_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await loop_task


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

# CORS — the Iliad frontend (Placer tab) calls the engine directly from the
# browser during local dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
