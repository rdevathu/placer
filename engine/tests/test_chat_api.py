"""End-to-end tests for the chat/board API (placer/api/chat.py).

Offline: ``placer.llm.structured`` is monkeypatched, and ``placer.brain.actions``
is a fake module injected into sys.modules (the real brain lands in parallel;
chat imports it lazily inside endpoint bodies).
"""

from __future__ import annotations

import json
import os
import sys
import types

import pytest

# Disable the brain loop (if main.py has grown one) BEFORE importing the app.
os.environ["PLACER_LOOP_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from placer import llm as llm_mod  # noqa: E402
from placer.api.chat import IntakeParse, post_message  # noqa: E402
from placer.db import engine  # noqa: E402
from placer.models import Approval, Barrier, Case, ChatMessage, DispoTask, Referral  # noqa: E402

try:
    from placer.main import app
except Exception:  # main.py mid-edit by a parallel agent — test the router alone
    from fastapi import FastAPI

    from placer.api import routers

    app = FastAPI()
    for r in routers:
        app.include_router(r)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def brain(monkeypatch):
    """Fake placer.brain.actions that records every call."""
    calls: list = []
    actions = types.ModuleType("placer.brain.actions")

    def commit_pathway(session, case_id, pathway_id, resolved_by):
        calls.append(("commit_pathway", case_id, pathway_id, resolved_by))
        if pathway_id == 999:  # sentinel: illegal transition
            raise ValueError("Event 'commit' not allowed from state 'tracking'")
        return {"state": "committed", "kept": [], "cancelled": [], "created": []}

    def approve_tasks(session, task_ids, resolved_by):
        calls.append(("approve_tasks", list(task_ids), resolved_by))
        return {"approved": list(task_ids)}

    def reject_approval(session, approval_id, resolved_by):
        calls.append(("reject_approval", approval_id, resolved_by))
        return {"rejected": approval_id}

    def reassess_case(session, case_id):
        calls.append(("reassess_case", case_id))

    actions.commit_pathway = commit_pathway
    actions.approve_tasks = approve_tasks
    actions.reject_approval = reject_approval
    actions.reassess_case = reassess_case

    pkg = types.ModuleType("placer.brain")
    pkg.actions = actions
    monkeypatch.setitem(sys.modules, "placer.brain", pkg)
    monkeypatch.setitem(sys.modules, "placer.brain.actions", actions)
    return calls


@pytest.fixture()
def intake(monkeypatch):
    """Monkeypatchable llm.structured returning a canned IntakeParse."""
    holder = {"kind": "info", "summary": "noted", "raise": False}

    def fake_structured(prompt, schema, **kwargs):
        if holder["raise"]:
            raise RuntimeError("model down")
        return IntakeParse(kind=holder["kind"], summary=holder["summary"])

    monkeypatch.setattr(llm_mod, "structured", fake_structured)
    return holder


def _mk_case(**kw) -> str:
    with Session(engine) as s:
        case = Case(patient_id=kw.pop("patient_id", "hero-a-stroke"), **kw)
        s.add(case)
        s.commit()
        return case.id


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def test_post_get_roundtrip_and_since_id(fresh_db, brain, intake):
    r1 = client.post("/chat/messages", json={"content": "hello there", "case_id": None})
    assert r1.status_code == 200
    body = r1.json()
    assert body["message"]["content"] == "hello there"
    assert body["message"]["author"] == "team:cm"
    assert body["parse"]["kind"] == "info"
    first_id = body["message"]["id"]

    r2 = client.post("/chat/messages", json={"content": "second", "author": "team:md"})
    assert r2.status_code == 200

    all_msgs = client.get("/chat/messages").json()
    assert [m["content"] for m in all_msgs] == ["hello there", "second"]

    after = client.get("/chat/messages", params={"since_id": first_id}).json()
    assert [m["content"] for m in after] == ["second"]

    # No case involved -> no reassessment.
    assert not any(c[0] == "reassess_case" for c in brain)


def test_unknown_case_404(fresh_db, brain, intake):
    r = client.post("/chat/messages", json={"content": "x", "case_id": "nope"})
    assert r.status_code == 404


def test_info_appends_team_notes_and_reassesses(fresh_db, brain, intake):
    case_id = _mk_case()
    intake["kind"] = "info"
    r = client.post(
        "/chat/messages",
        json={"content": "Family prefers Maple Grove", "case_id": case_id},
    )
    assert r.status_code == 200
    with Session(engine) as s:
        case = s.get(Case, case_id)
        notes = case.facts["team_notes"]
        assert notes[0]["content"] == "Family prefers Maple Grove"
        assert notes[0]["author"] == "team:cm"
    assert ("reassess_case", case_id) in brain


def test_instruction_creates_pending_task(fresh_db, brain, intake):
    case_id = _mk_case()
    intake.update(kind="instruction", summary="call the daughter")
    r = client.post(
        "/chat/messages",
        json={"content": "Please call the daughter today", "case_id": case_id},
    )
    assert r.status_code == 200
    assert r.json()["parse"]["kind"] == "instruction"
    with Session(engine) as s:
        task = s.exec(select(DispoTask).where(DispoTask.case_id == case_id)).one()
        assert task.task_type == "message_team"
        assert task.mode == "auto"
        assert task.status == "pending"
        assert task.title == "Team instruction: call the daughter"
        payload = getattr(task, "payload", None) or json.loads(task.detail)
        assert payload == {"question": "Please call the daughter today"}
        # Instruction content also lands in team_notes.
        assert s.get(Case, case_id).facts["team_notes"]
    assert ("reassess_case", case_id) in brain


def test_question_gets_ack_reply(fresh_db, brain, intake):
    case_id = _mk_case()
    intake["kind"] = "question"
    client.post("/chat/messages", json={"content": "Any SNF beds yet?", "case_id": case_id})
    msgs = client.get("/chat/messages", params={"case_id": case_id}).json()
    assert msgs[-1]["author"] == "placer"
    assert "report back" in msgs[-1]["content"]
    assert ("reassess_case", case_id) in brain


def test_llm_failure_degrades_to_info(fresh_db, brain, intake):
    case_id = _mk_case()
    intake["raise"] = True
    r = client.post("/chat/messages", json={"content": "pt ambulating", "case_id": case_id})
    assert r.status_code == 200
    assert r.json()["parse"]["kind"] == "info"
    with Session(engine) as s:
        assert s.get(Case, case_id).facts["team_notes"][0]["content"] == "pt ambulating"


def test_post_message_contract_no_commit(fresh_db):
    with Session(engine) as s:
        msg = post_message(s, "from the brain", case_id=None, kind="notification")
        assert msg.author == "placer"
        s.commit()
    with Session(engine) as s:
        stored = s.exec(select(ChatMessage)).one()
        assert stored.kind == "notification"


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


def test_approve_suggested_calls_approve_tasks(fresh_db, brain):
    case_id = _mk_case()
    with Session(engine) as s:
        approval = Approval(case_id=case_id, kind="suggested", task_ids=["t1", "t2"])
        s.add(approval)
        s.commit()
        approval_id = approval.id

    r = client.post(f"/chat/approvals/{approval_id}/approve", json={"resolved_by": "team:cm"})
    assert r.status_code == 200
    assert ("approve_tasks", ["t1", "t2"], "team:cm") in brain
    with Session(engine) as s:
        a = s.get(Approval, approval_id)
        assert a.status == "approved"
        assert a.resolved_by == "team:cm"
        assert a.resolved_at is not None

    # Second resolution attempt -> 409.
    r2 = client.post(f"/chat/approvals/{approval_id}/approve", json={"resolved_by": "team:cm"})
    assert r2.status_code == 409


def test_batch_approve_dict_shape(fresh_db, brain):
    case_id = _mk_case()
    with Session(engine) as s:
        approval = Approval(
            case_id=case_id, kind="batch",
            task_ids={"pathway_id": 3, "task_ids": ["t1"]},
        )
        s.add(approval)
        s.commit()
        approval_id = approval.id

    r = client.post(f"/chat/approvals/{approval_id}/approve", json={"resolved_by": "team:md"})
    assert r.status_code == 200
    assert ("commit_pathway", case_id, 3, "team:md") in brain


def test_batch_approve_list_shape_falls_back_to_active_pathway(fresh_db, brain):
    case_id = _mk_case(active_pathways=[{"pathway_id": 5, "confidence": 0.7}])
    with Session(engine) as s:
        approval = Approval(case_id=case_id, kind="batch", task_ids=["t1", "t2"])
        s.add(approval)
        s.commit()
        approval_id = approval.id

    r = client.post(f"/chat/approvals/{approval_id}/approve", json={"resolved_by": "team:cm"})
    assert r.status_code == 200
    assert ("commit_pathway", case_id, 5, "team:cm") in brain


def test_reject_calls_brain(fresh_db, brain):
    case_id = _mk_case()
    with Session(engine) as s:
        approval = Approval(case_id=case_id, kind="suggested", task_ids=["t1"])
        s.add(approval)
        s.commit()
        approval_id = approval.id

    r = client.post(f"/chat/approvals/{approval_id}/reject", json={"resolved_by": "team:cm"})
    assert r.status_code == 200
    assert ("reject_approval", approval_id, "team:cm") in brain
    assert client.post(
        "/chat/approvals/does-not-exist/reject", json={"resolved_by": "x"}
    ).status_code == 404


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------


def test_commit_unknown_case_404(fresh_db, brain):
    r = client.post("/cases/nope/commit", json={"pathway_id": 1, "resolved_by": "team:cm"})
    assert r.status_code == 404


def test_commit_ok_resolves_pending_batch_approvals(fresh_db, brain):
    case_id = _mk_case(state="predicted")
    with Session(engine) as s:
        batch = Approval(case_id=case_id, kind="batch", task_ids={"pathway_id": 2, "task_ids": []})
        s.add(batch)
        s.commit()
        batch_id = batch.id

    r = client.post(f"/cases/{case_id}/commit", json={"pathway_id": 2, "resolved_by": "team:cm"})
    assert r.status_code == 200
    assert ("commit_pathway", case_id, 2, "team:cm") in brain
    with Session(engine) as s:
        assert s.get(Approval, batch_id).status == "approved"


def test_commit_illegal_transition_409(fresh_db, brain):
    case_id = _mk_case()
    r = client.post(f"/cases/{case_id}/commit", json={"pathway_id": 999, "resolved_by": "team:cm"})
    assert r.status_code == 409
    assert "not allowed" in r.json()["detail"]
