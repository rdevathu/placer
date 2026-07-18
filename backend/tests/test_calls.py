"""Tests for the Bland outbound-calling surface and its SNF autonomy gate.

Bland itself is monkeypatched — these tests never hit the network. They cover
the gate (SNF autonomous vs. everything-else-needs-approval), the demo
force-number, and that a Communication row is logged on success.
"""

from __future__ import annotations

import pytest

from iliad import bland, config


@pytest.fixture()
def fake_bland(monkeypatch):
    """Record calls to bland.place_call and return a canned success response."""
    calls: list[dict] = []

    def _fake(**kwargs):
        calls.append(kwargs)
        return {"status": "success", "call_id": "call_test_123"}

    monkeypatch.setattr(bland, "place_call", _fake)
    return calls


def _snf_facility_id(client) -> str:
    facs = client.get("/facilities", params={"facility_type": "snf"}).json()
    assert facs, "seed should include at least one SNF"
    return facs[0]["id"]


def test_snf_call_is_autonomous(client, fresh_db, fake_bland):
    r = client.post(
        "/calls",
        json={
            "patient_id": "hero-a-stroke",
            "party_type": "snf",
            "party_name": "Maplewood SNF",
            "task": "Ask if a Medicare rehab bed is available.",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["call_id"] == "call_test_123"
    # Demo safety: forced to the configured number, not a real one.
    assert body["dialed_number"] == config.BLAND_FORCE_NUMBER
    assert body["forced"] is True
    assert len(fake_bland) == 1
    assert fake_bland[0]["phone_number"] == config.BLAND_FORCE_NUMBER

    # A communication row is logged and carries the Bland call_id.
    comms = client.get("/communications", params={"patient_id": "hero-a-stroke"}).json()
    assert any(c["external_id"] == "call_test_123" and c["outcome"] == "call_placed" for c in comms)


def test_non_snf_call_blocked_without_approval(client, fresh_db, fake_bland):
    r = client.post(
        "/calls",
        json={
            "patient_id": "hero-a-stroke",
            "party_type": "family",
            "party_name": "Daughter",
            "task": "Ask about discharge preferences.",
        },
    )
    assert r.status_code == 403, r.text
    assert "medical_team_approval" in r.json()["detail"]
    # Gate blocks BEFORE dialing.
    assert fake_bland == []


def test_non_snf_call_allowed_with_approval(client, fresh_db, fake_bland):
    r = client.post(
        "/calls",
        json={
            "patient_id": "hero-a-stroke",
            "party_type": "family",
            "party_name": "Daughter",
            "task": "Ask about discharge preferences.",
            "medical_team_approval": "Dr. Nadkarni",
        },
    )
    assert r.status_code == 201, r.text
    assert len(fake_bland) == 1
    comms = client.get("/communications", params={"patient_id": "hero-a-stroke"}).json()
    assert any("Authorized by Dr. Nadkarni" in (c["summary"] or "") for c in comms)


def test_facility_snf_gate_overrides_party_type(client, fresh_db, fake_bland):
    """A facility_id that is a SNF counts as a SNF call even if party_type differs."""
    snf_id = _snf_facility_id(client)
    r = client.post(
        "/calls",
        json={
            "patient_id": "hero-a-stroke",
            "party_type": "facility",
            "facility_id": snf_id,
            "task": "Bed availability?",
        },
    )
    assert r.status_code == 201, r.text
    assert len(fake_bland) == 1


def test_call_requires_known_patient(client, fresh_db, fake_bland):
    r = client.post(
        "/calls",
        json={"patient_id": "nope", "party_type": "snf", "task": "hi"},
    )
    assert r.status_code == 404
    assert fake_bland == []
