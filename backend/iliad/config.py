"""Runtime configuration for the Iliad backend.

Everything is env-overridable but ships with demo-friendly defaults so the app
runs with zero setup. Kept dependency-free (no pydantic-settings) to stay light.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo layout:  <repo>/backend/iliad/config.py  ->  parents[1] == <repo>/backend
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    """Minimal ``.env`` loader (avoids a python-dotenv dependency).

    Reads ``KEY=value`` lines from ``path`` into ``os.environ`` with
    ``setdefault`` so a real shell/CI environment always wins over the file.
    Silently no-ops if the file is absent. Secrets (e.g. ``BLAND_API_KEY``)
    live in ``backend/.env``, which is git-ignored.
    """
    try:
        raw = path.read_text()
    except OSError:
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_dotenv(BACKEND_ROOT / ".env")

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

# ---------------------------------------------------------------------------
# Bland AI outbound calling (Placer's real phone-call surface)
# ---------------------------------------------------------------------------
# Placer places outbound calls (SNF bed checks, family preference calls, etc.)
# through Bland — https://docs.bland.ai. The API key is a secret and belongs in
# backend/.env (git-ignored), not here.
BLAND_API_KEY = os.environ.get("BLAND_API_KEY", "")
BLAND_BASE_URL = os.environ.get("BLAND_BASE_URL", "https://api.bland.ai").rstrip("/")
BLAND_VOICE = os.environ.get("BLAND_VOICE", "June")

# DEMO SAFETY VALVE: every call is force-dialed to this number regardless of the
# facility/family phone on record, so a demo can never ring a real third party.
# Set BLAND_FORCE_NUMBER="" to dial the real number on the record instead.
BLAND_FORCE_NUMBER = os.environ.get("BLAND_FORCE_NUMBER", "+13179939042")

# GATE: the only party Placer may call autonomously (no medical-team sign-off)
# is a skilled-nursing facility. Comma-separated party_type/facility_type values.
BLAND_AUTONOMOUS_PARTY_TYPES = {
    v.strip()
    for v in os.environ.get("BLAND_AUTONOMOUS_PARTY_TYPES", "snf").split(",")
    if v.strip()
}
