"""Test fixtures: an isolated temp SQLite DB for the engine.

The DB path is set via env var *before* importing placer so the engine binds to
the throwaway file rather than the dev database — same trick as backend/tests.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make `import placer` work regardless of how pytest is invoked (the package
# is run from source, not installed).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="placer-test-"), "test.db")
os.environ["PLACER_DB_PATH"] = _TMP_DB
# Tests are offline: never mirror chat/tasks to a (possibly running) EHR.
# Mirror tests re-enable via monkeypatch on placer.config.PLACER_MIRROR.
os.environ["PLACER_MIRROR"] = "false"

from placer.db import engine, reset_db  # noqa: E402
from sqlmodel import Session  # noqa: E402


@pytest.fixture()
def fresh_db():
    """Empty schema for tests that write rows."""
    reset_db()
    yield


@pytest.fixture()
def session(fresh_db) -> Session:
    with Session(engine) as s:
        yield s
