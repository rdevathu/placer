"""Runtime configuration for the Placer Engine.

Everything is env-overridable with demo-friendly defaults, mirroring the
backend's ``ehr/config.py`` (plain os.environ reads, no pydantic-settings).
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo layout:  <repo>/engine/placer/config.py  ->  parents[1] == <repo>/engine
ENGINE_ROOT = Path(__file__).resolve().parents[1]

# SQLite database file for the engine's own state (cases, barriers, tasks...).
DB_PATH = Path(os.environ.get("PLACER_DB_PATH", ENGINE_ROOT / "placer.db"))
DATABASE_URL = os.environ.get("PLACER_DATABASE_URL", f"sqlite:///{DB_PATH}")

# The dummy EHR this engine reads from and acts on.
EHR_BASE_URL = os.environ.get("EHR_BASE_URL", "http://localhost:8000")

# Model for all LLM calls (GPS, watchman, chat responder). Cheap by default.
MODEL = os.environ.get("PLACER_MODEL", "claude-sonnet-5")

# How outbound calls are made: 'disabled' (no telephony — workers park as
# waiting) or 'bland' (Bland AI, integration pending). There is deliberately
# no simulation mode: Placer never fabricates a call outcome.
CALL_MODE = os.environ.get("CALL_MODE", "disabled")

# Cadence / thresholds for the engine loop.
HEARTBEAT_HOURS = int(os.environ.get("HEARTBEAT_HOURS", "24"))
DEBOUNCE_SECONDS = int(os.environ.get("DEBOUNCE_SECONDS", "10"))
CONFIDENCE_FLOOR = float(os.environ.get("CONFIDENCE_FLOOR", "0.25"))
MAX_CANDIDATES = int(os.environ.get("MAX_CANDIDATES", "3"))
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "3"))

# Writes to the EHR are attributed as '<ACTOR_PREFIX>:<agent-name>' via X-Actor.
ACTOR_PREFIX = os.environ.get("ACTOR_PREFIX", "agent")

# Mirror engine chat/tasks into the Iliad "Placer" tab (placer_messages +
# care_tasks). Best-effort: mirror failures never break the loop or workers.
PLACER_MIRROR = os.environ.get("PLACER_MIRROR", "true").lower() in {"1", "true", "yes"}

# Echo SQL when debugging.
SQL_ECHO = os.environ.get("PLACER_SQL_ECHO", "").lower() in {"1", "true", "yes"}

# API metadata.
API_TITLE = "Placer Engine"
API_VERSION = "0.1.0"
