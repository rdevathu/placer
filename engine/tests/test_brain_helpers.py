"""Shared offline test doubles for the brain suite (no tests in this module).

The sibling packages (placer.workers, placer.api.chat) are built in parallel
and may not exist at test time — stubs are injected into sys.modules so the
brain's deferred imports resolve to fakes either way.
"""

from __future__ import annotations

import sys
import types


class FakeEHR:
    """Minimal EHRClient stand-in recording writes."""

    def __init__(self, chart=None, admitted=None, events=None, notes=None, labs=None):
        self.chart = chart or {"patient": {"id": "p1", "name": "Test Patient"}, "problems": []}
        self.admitted = admitted or []
        self.events = events or []
        self.notes = notes or []
        self.labs = labs or []
        self.calls_placed: list = []
        self.assessments: list = []

    def get_chart(self, patient_id):
        return self.chart

    def list_notes(self, patient_id, note_type=None):
        return self.notes

    def list_labs(self, patient_id, status=None):
        return self.labs

    def place_call(self, patient_id, task, party_type="snf", party_name=None,
                   facility_id=None, care_task_id=None):
        rec = {"patient_id": patient_id, "task": task, "party_type": party_type,
               "party_name": party_name, "facility_id": facility_id, "care_task_id": care_task_id}
        self.calls_placed.append(rec)
        return {"call_id": f"bland-{len(self.calls_placed)}", "communication": {"id": "comm-x"}}

    def post_dispo_assessment(self, **kwargs):
        self.assessments.append(kwargs)
        return {"id": f"ehr-assess-{len(self.assessments)}"}

    def list_admitted_patients(self):
        return self.admitted

    def list_events(self, since=0, limit=100):
        return [e for e in self.events if e.get("seq", 0) > since][:limit]

    def close(self):
        pass


def install_stubs(monkeypatch, chat_log=None, run_task=None):
    """Inject fake placer.workers / placer.api.chat modules; returns chat_log."""
    chat_log = chat_log if chat_log is not None else []

    chat_mod = types.ModuleType("placer.api.chat")

    def post_message(session, content, *, case_id=None, kind="text", author="placer", approval_id=None):
        chat_log.append({
            "content": content, "case_id": case_id, "kind": kind,
            "author": author, "approval_id": approval_id,
        })
        return None

    chat_mod.post_message = post_message
    monkeypatch.setitem(sys.modules, "placer.api.chat", chat_mod)

    workers_mod = types.ModuleType("placer.workers")
    workers_mod.run_task = run_task or (lambda session, task: {"ok": True})
    monkeypatch.setitem(sys.modules, "placer.workers", workers_mod)
    return chat_log


def stub_gps(monkeypatch, assessment):
    """Route placer.llm.structured (the GPS + watchman seam) to a canned answer."""
    import placer.llm

    def fake_structured(prompt, schema, **kwargs):
        return assessment

    monkeypatch.setattr(placer.llm, "structured", fake_structured)
