"""Admin/ops endpoints: health, stats, and the demo reset.

``POST /admin/reset`` is the button that makes the demo re-runnable: it drops,
recreates, and reseeds the database from the fixed seed set, so a run with the
agents can be reset and repeated.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from .. import config
from ..db import get_session
from ..seed import reset_and_seed, row_counts

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/health", summary="Liveness check")
def health() -> dict:
    return {"status": "ok", "service": config.API_TITLE, "version": config.API_VERSION}


@router.get("/stats", summary="Row counts per table")
def stats(session: Session = Depends(get_session)) -> dict:
    return row_counts(session)


@router.post(
    "/reset",
    summary="Reset the database to the seed state",
    description=(
        "Drops all data and reseeds from scratch: the 25 imported FHIR patients "
        "plus the active 'hero' inpatients and facilities. Use between demo runs "
        "to return to a known state. Set `heroes_only=true` to skip the imported "
        "cohort for a faster reset."
    ),
)
def reset(
    heroes_only: bool = Query(False, description="Skip importing the 25 FHIR patients"),
) -> dict:
    if not config.ALLOW_RESET:
        raise HTTPException(status_code=403, detail="Reset is disabled (set EHR_ALLOW_RESET=true to enable)")
    counts = reset_and_seed(include_heroes=True, include_fhir=not heroes_only)
    return {"status": "reset complete", "row_counts": counts}
