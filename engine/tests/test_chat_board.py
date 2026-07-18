"""Board endpoint tests: /cases and /cases/{id}/board over seeded rows."""

from __future__ import annotations

import os

os.environ["PLACER_LOOP_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session  # noqa: E402

from placer.db import engine  # noqa: E402
from placer.models import Approval, Barrier, Case, ChatMessage, DispoTask, Referral  # noqa: E402

try:
    from placer.main import app
except Exception:
    from fastapi import FastAPI

    from placer.api import routers

    app = FastAPI()
    for r in routers:
        app.include_router(r)

client = TestClient(app)


def _seed_case() -> str:
    with Session(engine) as s:
        case = Case(
            patient_id="hero-a-stroke",
            state="predicted",
            brief="72M s/p MCA stroke, dense L hemiparesis.",
            active_pathways=[
                {"pathway_id": 1, "confidence": 0.2},
                {"pathway_id": 2, "confidence": 0.55},
            ],
        )
        s.add(case)
        s.commit()
        cid = case.id
        s.add(Barrier(case_id=cid, dimension="medical", btype="iv_abx_course",
                      status="open", description="Finishing IV antibiotics"))
        s.add(Barrier(case_id=cid, dimension="payer", btype="auth_pending",
                      status="cleared", description="Auth approved"))
        s.add(DispoTask(case_id=cid, task_type="preference_call", mode="approval",
                        status="suggested", title="Call daughter re: preferences",
                        action_id="FPR-004"))
        s.add(DispoTask(case_id=cid, task_type="build_shortlist", mode="auto",
                        status="done", title="Build SNF shortlist"))
        s.add(Referral(case_id=cid, pathway_id=2, facility_id="fac-1",
                       facility_name="Maple Grove SNF", status="declined",
                       denial_reason="No vent bed"))
        s.add(Approval(case_id=cid, kind="suggested", task_ids=["t1"],
                       prompt="OK to call the family?"))
        s.add(ChatMessage(case_id=cid, author="placer", content="Tracking this admission."))
        s.commit()
        return cid


def test_cases_list_counts_and_pathway_names(fresh_db):
    cid = _seed_case()
    rows = client.get("/cases").json()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == cid
    assert row["state"] == "predicted"
    assert row["counts"]["open_barriers"] == 1  # cleared payer barrier not counted
    assert row["counts"]["open_tasks"] == 1  # done task not counted
    assert row["counts"]["referrals"] == {"declined": 1}
    names = {p["pathway_id"]: p["name"] for p in row["active_pathways"]}
    assert names[1] == "Home / self-care"  # enriched from the registry


def test_board_shape(fresh_db):
    cid = _seed_case()
    b = client.get(f"/cases/{cid}/board").json()

    assert b["patient_id"] == "hero-a-stroke"
    assert b["brief"].startswith("72M")

    # Readiness vector: all 7 dimensions present; medical blocked by the open
    # barrier, payer clear via its cleared barrier, decision needs evidence.
    dims = b["readiness"]["dimensions"]
    assert len(dims) == 7
    assert dims["medical"] == {"clear": False, "open_count": 1}
    assert dims["payer"]["clear"] is True
    assert dims["decision"]["clear"] is False  # no explicit cleared barrier
    assert b["readiness"]["green"] is False

    # Barriers grouped by dimension.
    assert [x["btype"] for x in b["barriers"]["medical"]] == ["iv_abx_course"]
    assert b["barriers"]["payer"][0]["status"] == "cleared"

    # Tasks grouped by status with title+action_id+mode.
    sug = b["tasks"]["suggested"]
    assert sug[0]["title"] == "Call daughter re: preferences"
    assert sug[0]["action_id"] == "FPR-004"
    assert sug[0]["mode"] == "approval"
    assert b["tasks"]["done"][0]["title"] == "Build SNF shortlist"

    assert b["referrals"][0]["facility_name"] == "Maple Grove SNF"
    assert b["referrals"][0]["denial_reason"] == "No vent bed"

    assert b["approvals"][0]["prompt"] == "OK to call the family?"
    assert b["approvals"][0]["kind"] == "suggested"

    assert b["messages"][-1]["content"] == "Tracking this admission."


def test_board_404(fresh_db):
    assert client.get("/cases/nope/board").status_code == 404


def test_ui_served(fresh_db):
    r = client.get("/chat/ui")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "PLACER" in r.text
