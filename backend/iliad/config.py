"""Runtime configuration for the Iliad backend.

Everything is env-overridable but ships with demo-friendly defaults so the app
runs with zero setup. Kept dependency-free (no pydantic-settings) to stay light.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo layout:  <repo>/backend/iliad/config.py  ->  parents[1] == <repo>/backend
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# SQLite database file. Defaults to <backend>/iliad.db.
DATABASE_PATH = Path(os.environ.get("ILIAD_DATABASE_PATH", BACKEND_ROOT / "iliad.db"))
DATABASE_URL = os.environ.get("ILIAD_DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

# Echo SQL to stdout when debugging.
SQL_ECHO = os.environ.get("ILIAD_SQL_ECHO", "").lower() in {"1", "true", "yes"}

# Allow the destructive reset endpoint. On by default for the hackathon demo;
# set ILIAD_ALLOW_RESET=false to disable in a shared environment.
ALLOW_RESET = os.environ.get("ILIAD_ALLOW_RESET", "true").lower() in {"1", "true", "yes"}

# Auto-seed an empty database on startup so the app is demoable with no setup.
AUTO_SEED = os.environ.get("ILIAD_AUTO_SEED", "true").lower() in {"1", "true", "yes"}

# API metadata (surfaced in OpenAPI / Swagger UI).
API_TITLE = "Iliad API"
API_VERSION = "0.1.0"
