"""Test fixtures: an isolated, freshly-seeded SQLite DB and a TestClient.

The database path is set via env var *before* importing the app so the app
binds to the throwaway file rather than the dev database.
"""

from __future__ import annotations

import os
import tempfile

import pytest

# Point the app at a temp DB and disable auto-seed (we seed explicitly).
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="ehr-test-"), "test.db")
os.environ["EHR_DATABASE_PATH"] = _TMP_DB
os.environ["EHR_AUTO_SEED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from ehr.main import app  # noqa: E402
from ehr.seed import reset_and_seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _seed_once():
    reset_and_seed()
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def fresh_db():
    """Reset to seed state for tests that mutate data destructively."""
    reset_and_seed()
    yield
