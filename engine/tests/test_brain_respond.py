"""Unit tests for the shared chat responder (placer/brain/respond.py)."""

from __future__ import annotations

import json

from sqlmodel import select

import placer.llm
from placer.brain.respond import TeamReply, respond_to_team
from placer.models import Barrier, Case, DispoTask

from test_brain_helpers import install_stubs


def _case(session, **kw):
    case = Case(patient_id="hero-a-stroke", state=kw.pop("state", "predicted"),
                active_pathways=[{"pathway_id": 11, "confidence": 0.6}], **kw)
    session.add(case)
    session.commit()
    session.add(Barrier(case_id=case.id, dimension="destination", btype="bed_availability",
                        status="open", description="No SNF bed identified"))
    session.commit()
    return case


def test_summarize_blockers_gets_answer_not_task(session, monkeypatch):
    chat_log = install_stubs(monkeypatch)
    prompts = []

    def fake_structured(prompt, schema, **kw):
        prompts.append(prompt)
        return TeamReply(reply="One open barrier: no SNF bed identified (destination).",
                         action_kind="none", detail="")

    monkeypatch.setattr(placer.llm, "structured", fake_structured)
    case = _case(session)

    reply = respond_to_team(session, case, "summarize blockers", "team:cm")
    session.commit()

    assert reply == "One open barrier: no SNF bed identified (destination)."
    # Reply posted to chat as placer, kind text.
    assert chat_log == [{"content": reply, "case_id": case.id, "kind": "text",
                         "author": "placer", "approval_id": None}]
    # Grounded: the board data and the message are both in the prompt.
    assert "summarize blockers" in prompts[0]
    assert "bed_availability" in prompts[0]
    # No action item fabricated from a question.
    assert session.exec(select(DispoTask).where(DispoTask.case_id == case.id)).all() == []
    # Team text captured; case marked for reassessment.
    assert case.facts["team_notes"][0]["content"] == "summarize blockers"
    assert case.dirty is True


def test_create_task_only_for_real_work(session, monkeypatch):
    install_stubs(monkeypatch)
    monkeypatch.setattr(placer.llm, "structured", lambda p, s, **kw: TeamReply(
        reply="Queued — the team will see the request.",
        action_kind="create_task", detail="fax records to Sunrise SNF"))
    case = _case(session)

    respond_to_team(session, case, "Please fax the records to Sunrise SNF", "team:cm")
    session.commit()

    task = session.exec(select(DispoTask).where(DispoTask.case_id == case.id)).one()
    assert task.task_type == "message_team"
    assert task.status == "pending"
    assert task.title == "Team request: fax records to Sunrise SNF"
    assert json.loads(task.detail) == {"question": "Please fax the records to Sunrise SNF"}


def test_llm_failure_degrades_to_truthful_fallback(session, monkeypatch):
    chat_log = install_stubs(monkeypatch)

    def boom(prompt, schema, **kw):
        raise RuntimeError("model down")

    monkeypatch.setattr(placer.llm, "structured", boom)
    case = _case(session)

    reply = respond_to_team(session, case, "any beds yet?", "team:md")
    session.commit()

    assert "logged this on the case" in reply
    assert chat_log[0]["content"] == reply
    assert session.exec(select(DispoTask).where(DispoTask.case_id == case.id)).all() == []
    assert case.facts["team_notes"][0]["content"] == "any beds yet?"
