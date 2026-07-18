"""End-to-end tests for the append-only event feed (the agent-engine trigger)."""

from __future__ import annotations


def test_fresh_reset_has_zero_events(client, fresh_db):
    r = client.get("/events")
    assert r.status_code == 200
    assert r.json() == []  # seeding is event-silent


def test_order_lifecycle_emits_events(client, fresh_db):
    r = client.post(
        "/orders",
        json={
            "patient_id": "hero-b-chf",
            "order_type": "consult",
            "display": "PM&R eval",
            "ordered_by": "dispo-agent",
        },
    )
    assert r.status_code == 201
    order = r.json()

    r = client.post(f"/orders/{order['id']}/sign", json={"signed_by": "Dr. Feld"})
    assert r.status_code == 200

    events = client.get("/events").json()
    assert [e["event_type"] for e in events] == ["order.created", "order.signed"]
    assert all(e["patient_id"] == "hero-b-chf" for e in events)
    assert all(e["entity_type"] == "order" and e["entity_id"] == order["id"] for e in events)
    assert events[0]["payload"]["order_type"] == "consult"
    assert events[0]["payload"]["status"] == "draft"
    assert events[1]["payload"]["status"] == "signed"
    # seq is a strictly increasing cursor.
    assert events[1]["seq"] > events[0]["seq"]
    # Default actor (no X-Actor header) is the clinician.
    assert all(e["actor"] == "clinician" for e in events)


def test_since_cursor_pagination(client, fresh_db):
    for i in range(3):
        r = client.post(
            "/care-tasks",
            json={"patient_id": "hero-a-stroke", "task_type": "call_snf", "title": f"Call SNF #{i}"},
        )
        assert r.status_code == 201

    all_events = client.get("/events").json()
    assert len(all_events) == 3
    cursor = all_events[0]["seq"]

    newer = client.get("/events", params={"since": cursor}).json()
    assert [e["seq"] for e in newer] == [e["seq"] for e in all_events[1:]]

    # Cursor at the tip -> nothing new.
    tip = all_events[-1]["seq"]
    assert client.get("/events", params={"since": tip}).json() == []

    # limit is honored, oldest-first.
    limited = client.get("/events", params={"limit": 1}).json()
    assert len(limited) == 1 and limited[0]["seq"] == all_events[0]["seq"]


def test_x_actor_header_captured(client, fresh_db):
    r = client.post(
        "/orders",
        json={
            "patient_id": "hero-a-stroke",
            "order_type": "lab",
            "display": "COVID PCR",
            "ordered_by": "clinical-prep",
            "status": "signed",
        },
        headers={"X-Actor": "agent:clinical-prep"},
    )
    assert r.status_code == 201

    events = client.get("/events", params={"patient_id": "hero-a-stroke"}).json()
    assert events, "expected events for the agent's write"
    assert all(e["actor"] == "agent:clinical-prep" for e in events)
    # Immediate-sign emits both created and signed.
    assert {e["event_type"] for e in events} == {"order.created", "order.signed"}


def test_patient_id_filter(client, fresh_db):
    client.post(
        "/communications",
        json={"patient_id": "hero-a-stroke", "party_type": "family", "summary": "Called daughter"},
    )
    client.post(
        "/care-tasks",
        json={"patient_id": "hero-b-chf", "task_type": "call_family", "title": "Call spouse"},
    )

    a = client.get("/events", params={"patient_id": "hero-a-stroke"}).json()
    assert [e["event_type"] for e in a] == ["communication.created"]
    b = client.get("/events", params={"patient_id": "hero-b-chf"}).json()
    assert [e["event_type"] for e in b] == ["care_task.created"]


def test_provider_placer_message_emits_event(client, fresh_db):
    r = client.post(
        "/patients/hero-a-stroke/placer/messages",
        json={"sender": "provider", "sender_name": "Dr. Feld", "text": "Family prefers rehab close to home"},
    )
    assert r.status_code == 201
    msg = r.json()

    events = client.get("/events", params={"patient_id": "hero-a-stroke"}).json()
    assert [e["event_type"] for e in events] == ["placer_message.created"]
    evt = events[0]
    assert evt["actor"] == "provider"
    assert evt["entity_type"] == "placer_message"
    assert evt["entity_id"] == msg["id"]
    assert evt["payload"]["sender"] == "provider"
    assert evt["payload"]["sender_name"] == "Dr. Feld"
    assert evt["payload"]["text"] == "Family prefers rehab close to home"
