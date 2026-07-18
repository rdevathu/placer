"""Runtime configuration for the EHR backend.

Everything is env-overridable but ships with demo-friendly defaults so the app
runs with zero setup. Kept dependency-free (no pydantic-settings) to stay light.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo layout:  <repo>/backend/ehr/config.py  ->  parents[2] == <repo>
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Where the provided Synthea/Abridge FHIR seed lives.
SYNTHETIC_DATA_DIR = Path(
    os.environ.get("EHR_SYNTHETIC_DIR", REPO_ROOT / "synthetic-examples")
)
SYNTHETIC_JSONL = SYNTHETIC_DATA_DIR / "synthetic-ambient-fhir-25.jsonl"

# SQLite database file. Defaults to <backend>/ehr.db.
DATABASE_PATH = Path(os.environ.get("EHR_DATABASE_PATH", BACKEND_ROOT / "ehr.db"))
DATABASE_URL = os.environ.get("EHR_DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

# Echo SQL to stdout when debugging.
SQL_ECHO = os.environ.get("EHR_SQL_ECHO", "").lower() in {"1", "true", "yes"}

# Allow the destructive reset endpoint. On by default for the hackathon demo;
# set EHR_ALLOW_RESET=false to disable in a shared environment.
ALLOW_RESET = os.environ.get("EHR_ALLOW_RESET", "true").lower() in {"1", "true", "yes"}

# Auto-seed an empty database on startup so the app is demoable with no setup.
AUTO_SEED = os.environ.get("EHR_AUTO_SEED", "true").lower() in {"1", "true", "yes"}

# API metadata (surfaced in OpenAPI / Swagger UI).
API_TITLE = "Placer EHR API"
API_VERSION = "0.1.0"
