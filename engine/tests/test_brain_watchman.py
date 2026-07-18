"""Watchman materiality rules — all offline (LLM path monkeypatched)."""

from __future__ import annotations

import placer.llm
from placer.brain import watchman
from placer.brain.schemas import WatchmanVerdict


def _ev(event_type, actor="clinician", **extra):
    return {"event_type": event_type, "actor": actor, "patient_id": "p1", **extra}


def test_agent_actor_always_material():
    v = watchman.is_material(_ev("communication.created", actor="agent:caller"), "brief")
    assert v.material is True
    assert "agent" in v.reason


def test_admission_and_order_events_material():
    for et in ("patient.admitted", "order.completed", "order.resulted", "order.created"):
        assert watchman.is_material(_ev(et), "").material is True


def test_care_task_updated_by_clinician_material():
    assert watchman.is_material(_ev("care_task.updated"), "").material is True


def test_ambient_clinician_events_not_material():
    for et in ("communication.created", "facility.updated", "care_task.created"):
        assert watchman.is_material(_ev(et), "").material is False


def test_unknown_event_type_defaults_not_material():
    assert watchman.is_material(_ev("observation.recorded"), "").material is False


def test_note_created_routes_to_llm(monkeypatch):
    seen = {}

    def fake_structured(prompt, schema, **kwargs):
        seen["prompt"] = prompt
        seen["schema"] = schema
        return WatchmanVerdict(material=True, reason="goals-of-care note")

    monkeypatch.setattr(placer.llm, "structured", fake_structured)
    v = watchman.is_material(_ev("note.created"), "72M stroke, likely SNF")
    assert v.material is True
    assert seen["schema"] is WatchmanVerdict
    assert "72M stroke" in seen["prompt"]  # case brief reaches the classifier


def test_note_created_llm_failure_degrades_to_material(monkeypatch):
    def boom(prompt, schema, **kwargs):
        raise RuntimeError("model down")

    monkeypatch.setattr(placer.llm, "structured", boom)
    v = watchman.is_material(_ev("note.created"), "")
    assert v.material is True
    assert "defaulted material" in v.reason
