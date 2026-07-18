"""Ops endpoint tests: /runs and /ops/overview cross-case rollups."""

from __future__ import annotations

import os

os.environ["PLACER_LOOP_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session  # noqa: E402

from placer.db import engine  # noqa: E402
from placer.models import Barrier, Case, DispoTask, Referral, Run  # noqa: E402

try:
    from placer.main import app
except Exception:
    from fastapi import FastAPI

    from placer.api import routers

    app = FastAPI()
    for r in routers:
        app.include_router(r)

client = TestClient(app)


def _seed() -> dict:
    with Session(engine) as s:
        case_a = Case(patient_id="hero-a-stroke", state="predicted")
        case_b = Case(patient_id="hero-b-chf", state="green")
        s.add(case_a)
        s.add(case_b)
        s.commit()

        s.add(Barrier(case_id=case_a.id, dimension="medical", btype="iv_abx_course", status="open"))
        s.add(Barrier(case_id=case_a.id, dimension="payer", btype="auth_pending", status="cleared"))
        s.add(DispoTask(case_id=case_a.id, task_type="preference_call", mode="approval", status="suggested", title="Call daughter"))
        s.add(DispoTask(case_id=case_b.id, task_type="build_shortlist", mode="auto", status="done", title="Build shortlist"))
        s.add(Referral(case_id=case_a.id, pathway_id=1, facility_id="fac-1", facility_name="Maple Grove SNF", status="declined"))

        s.add(Run(agent="brain", case_id=case_a.id, trigger="dirty", status="done", outcome="assessed; state=predicted"))
        s.add(Run(agent="brain", case_id=case_b.id, trigger="dirty", status="error", outcome="boom"))
        s.commit()
        return {"case_a": case_a.id, "case_b": case_b.id}


def test_runs_list_newest_first_and_carries_patient_id(fresh_db):
    ids = _seed()
    rows = client.get("/runs").json()
    assert len(rows) == 2
    patient_ids = {r["patient_id"] for r in rows}
    assert patient_ids == {"hero-a-stroke", "hero-b-chf"}
    # newest first
    assert rows[0]["created_at"] >= rows[1]["created_at"]

    scoped = client.get("/runs", params={"case_id": ids["case_a"]}).json()
    assert len(scoped) == 1
    assert scoped[0]["patient_id"] == "hero-a-stroke"

    errors = client.get("/runs", params={"status": "error"}).json()
    assert len(errors) == 1
    assert errors[0]["outcome"] == "boom"


def test_ops_overview_rollups(fresh_db):
    _seed()
    body = client.get("/ops/overview").json()
    assert body["total_cases"] == 2
    assert body["cases_by_state"] == {"predicted": 1, "green": 1}
    assert body["tasks_by_status"] == {"suggested": 1, "done": 1}
    assert body["open_barriers_by_dimension"] == {"medical": 1}  # cleared payer barrier excluded
    assert body["referrals_by_status"] == {"declined": 1}
    assert len(body["recent_runs"]) == 2


def test_ops_overview_empty_state(fresh_db):
    body = client.get("/ops/overview").json()
    assert body["total_cases"] == 0
    assert body["cases_by_state"] == {}
    assert body["recent_runs"] == []


def test_ops_ui_served(fresh_db):
    r = client.get("/ops/ui")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "PLACER" in r.text
