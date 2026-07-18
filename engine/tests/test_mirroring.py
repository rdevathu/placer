"""Offline tests for the Iliad <-> engine mirroring layer.

Inbound: a provider message in the Iliad Placer tab ('placer_message.created'
event) lands in the engine chat thread + case facts and dirties the case.
Outbound: placer-authored chat mirrors to placer_messages, engine tasks mirror
to EHR care_tasks (created on plan, completed on execution) — all via a
monkeypatched EHRClient; no network.
"""

from __future__ import annotations

import json
import sys
import types

import pytest
from sqlmodel import select

from placer import config
from placer.api import chat as chat_mod
from placer.brain import loop, router_logic
from placer.models import Case, ChatMessage, DispoTask


class RecordingEHRClient:
    """Stands in for placer.ehr_client.EHRClient; records every call."""

    calls: list = []  # rebound per-test via `recorder`

    def __init__(self, *args, **kwargs):
        pass

    def close(self):
        pass

    def create_placer_message(self, patient_id, text, sender="placer", sender_name="Placer"):
        self.calls.append(("create_placer_message", patient_id, text, sender))
        return {"id": "pm-1"}

    def create_care_task(self, patient_id, task_type, title, **kwargs):
        self.calls.append(("create_care_task", patient_id, task_type, title))
        return {"id": f"ct-{len(self.calls)}"}

    def update_care_task(self, task_id, **fields):
        self.calls.append(("update_care_task", task_id, fields))
        return {"id": task_id}


@pytest.fixture()
def recorder(monkeypatch):
    """Enable mirroring and swap in the recording client everywhere the mirror
    code resolves EHRClient (lazy imports + loop's module-level import)."""
    calls: list = []
    RecordingEHRClient.calls = calls
    monkeypatch.setattr(config, "PLACER_MIRROR", True)
    import placer.ehr_client

    monkeypatch.setattr(placer.ehr_client, "EHRClient", RecordingEHRClient)
    monkeypatch.setattr(loop, "EHRClient", RecordingEHRClient)
    return calls


def _case(session, patient_id="hero-a-stroke") -> Case:
    case = Case(patient_id=patient_id, encounter_id="enc-1", state="tracking")
    session.add(case)
    session.commit()
    return case


# ---------------------------------------------------------------------------
# Inbound: provider Placer-tab message -> engine chat + facts + dirty
# ---------------------------------------------------------------------------


def _provider_event(patient_id="hero-a-stroke", sender="provider"):
    return {
        "seq": 7,
        "event_type": "placer_message.created",
        "patient_id": patient_id,
        "actor": sender,
        "entity_type": "placer_message",
        "entity_id": "pm-9",
        "payload": {"sender": sender, "sender_name": "Dr. Feld", "text": "Family prefers rehab"},
    }


def test_provider_message_routes_to_chat_facts_dirty(session):
    case = _case(session)
    loop._route_event(session, _provider_event())
    session.commit()

    msg = session.exec(select(ChatMessage).where(ChatMessage.case_id == case.id)).first()
    assert msg is not None
    assert msg.author == "team:Dr. Feld"
    assert msg.content == "Family prefers rehab"

    session.refresh(case)
    notes = case.facts["team_notes"]
    assert len(notes) == 1
    assert notes[0]["author"] == "team:Dr. Feld"
    assert notes[0]["content"] == "Family prefers rehab"
    assert case.dirty is True


def test_placer_sender_is_skipped_as_echo(session):
    case = _case(session)
    loop._route_event(session, _provider_event(sender="placer"))
    session.commit()

    assert session.exec(select(ChatMessage)).first() is None
    session.refresh(case)
    assert not case.dirty
    assert not (case.facts or {}).get("team_notes")


def test_provider_message_without_case_is_ignored(session):
    loop._route_event(session, _provider_event(patient_id="unknown-patient"))
    session.commit()
    assert session.exec(select(ChatMessage)).first() is None


# ---------------------------------------------------------------------------
# Outbound: post_message -> placer_messages mirror
# ---------------------------------------------------------------------------


def test_post_message_mirrors_placer_authored(session, recorder):
    case = _case(session)
    chat_mod.post_message(session, "Called Maple Grove: 2 beds.", case_id=case.id)
    session.commit()
    assert recorder == [("create_placer_message", "hero-a-stroke", "Called Maple Grove: 2 beds.", "placer")]


def test_post_message_does_not_mirror_team_authored(session, recorder):
    case = _case(session)
    chat_mod.post_message(session, "provider said hi", case_id=case.id, author="team:Dr. Feld")
    chat_mod.post_message(session, "board", case_id=case.id, kind="readiness_board")
    chat_mod.post_message(session, "no case here")  # general thread
    session.commit()
    assert recorder == []


def test_post_message_mirror_failure_never_raises(session, monkeypatch):
    monkeypatch.setattr(config, "PLACER_MIRROR", True)
    import placer.ehr_client

    class Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("EHR down")

    monkeypatch.setattr(placer.ehr_client, "EHRClient", Boom)
    case = _case(session)
    msg = chat_mod.post_message(session, "still lands in chat", case_id=case.id)
    session.commit()
    assert msg.id is not None


# ---------------------------------------------------------------------------
# Outbound: task worklist mirror (create on plan, complete on execution)
# ---------------------------------------------------------------------------


def test_persist_plan_mirrors_care_task_and_stores_id(session, recorder):
    case = _case(session)
    spec = router_logic.TaskSpec(
        task_type="preference_call", mode="auto", action_id="PFC-007",
        title="Call family to discuss preferences", target="-", payload={"topics": ["prefs"]},
    )
    router_logic.persist_plan(session, case, [spec])

    creates = [c for c in recorder if c[0] == "create_care_task"]
    assert creates == [("create_care_task", "hero-a-stroke", "call_family", "Call family to discuss preferences")]
    task = session.exec(select(DispoTask)).first()
    assert json.loads(task.detail)["ehr_care_task_id"] == "ct-1"
    # Original payload keys survive the rewrite.
    assert json.loads(task.detail)["topics"] == ["prefs"]


def test_executor_mirrors_completion(session, recorder, monkeypatch):
    case = _case(session)
    task = DispoTask(
        case_id=case.id, task_type="message_team", mode="auto", status="approved",
        title="Ask team", detail=json.dumps({"question": "?", "ehr_care_task_id": "ct-42"}),
    )
    session.add(task)
    session.commit()

    fake_workers = types.ModuleType("placer.workers")
    fake_workers.run_task = lambda session, task: {"summary": "team answered"}
    monkeypatch.setitem(sys.modules, "placer.workers", fake_workers)

    loop._execute_tasks(session, ehr=None)

    session.refresh(task)
    assert task.status == "done"
    updates = [c for c in recorder if c[0] == "update_care_task"]
    assert len(updates) == 1
    _, ehr_id, fields = updates[0]
    assert ehr_id == "ct-42"
    assert fields["status"] == "completed"
    assert "team answered" in fields["result_summary"]
    assert len(fields["result_summary"]) <= 500
