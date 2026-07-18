"""End-to-end API tests covering the core agent workflows."""

from __future__ import annotations


def test_health(client):
    r = client.get("/admin/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_seed_populated(client):
    counts = client.get("/admin/stats").json()
    assert counts["patients"] == 4  # the hero cohort is the whole demo
    assert counts["facilities"] >= 6
    assert counts["observations"] >= 12
    assert counts["encounters"] >= 12  # each hero has priors + the current admission
    assert counts["notes"] >= 30
    assert counts["placer_messages"] >= 12


def test_patient_demographics(client):
    p = client.get("/patients/hero-a-stroke").json()
    assert p["phone"]
    assert p["address_line"]
    assert p["emergency_contact_name"]
    assert p["emergency_contact_relationship"]
    assert p["emergency_contact_phone"]


def test_encounter_history(client):
    encounters = client.get("/patients/hero-a-stroke/encounters").json()
    assert len(encounters) >= 3
    active = [e for e in encounters if e["status"] == "in-progress"]
    assert len(active) == 1
    # The current admission is the most recent encounter.
    assert active[0]["period_start"] == max(e["period_start"] for e in encounters)

    notes = client.get("/patients/hero-a-stroke/notes").json()
    by_enc = {}
    for n in notes:
        by_enc.setdefault(n["encounter_id"], set()).add(n["note_type"])

    # Every finished inpatient stay is fully noted; the current one has no
    # discharge summary yet.
    finished_imp = [e for e in encounters if e["status"] == "finished" and e["class_code"] == "IMP"]
    assert finished_imp
    for enc in finished_imp:
        assert {"history_and_physical", "progress", "discharge_summary"} <= by_enc[enc["id"]]
    current_types = by_enc[active[0]["id"]]
    assert "history_and_physical" in current_types
    assert "progress" in current_types
    assert "discharge_summary" not in current_types
    # Outpatient visits each carry a progress note.
    for enc in (e for e in encounters if e["class_code"] == "AMB"):
        assert "progress" in by_enc[enc["id"]]


def test_seed_has_no_agent_authored_artifacts(client):
    # "For now" nothing clinical in the seed is authored by Placer: no orders,
    # no notes. Placer only owns its native rows (assessments, tasks, chat).
    for pid in ("hero-a-stroke", "hero-b-chf", "hero-c-hospice", "hero-d-ambiguous"):
        orders = client.get("/orders", params={"patient_id": pid}).json()
        assert all(o["ordered_by"] not in ("Placer", "dispo-agent") for o in orders)
        notes = client.get(f"/patients/{pid}/notes").json()
        assert all(not n["authored_by_agent"] for n in notes)


def test_placer_message_thread_seeded(client):
    msgs = client.get("/patients/hero-a-stroke/placer/messages").json()
    assert len(msgs) >= 3
    senders = {m["sender"] for m in msgs}
    assert senders == {"placer", "provider"}
    stamps = [m["created_at"] for m in msgs]
    assert stamps == sorted(stamps)  # chronological thread order


def test_placer_message_post(client, fresh_db):
    r = client.post(
        "/patients/hero-b-chf/placer/messages",
        json={"text": "Plan is IV to PO today; target discharge tomorrow."},
    )
    assert r.status_code == 201
    msg = r.json()
    assert msg["sender"] == "provider"  # default sender

    msgs = client.get("/patients/hero-b-chf/placer/messages").json()
    assert msgs[-1]["id"] == msg["id"]

    assert client.get("/patients/nope/placer/messages").status_code == 404


def test_admitted_worklist(client):
    r = client.get("/patients", params={"admitted": True})
    assert r.status_code == 200
    admitted = r.json()
    mrns = {p["mrn"] for p in admitted}
    assert {"MRN90001", "MRN90002", "MRN90003", "MRN90004"} <= mrns
    # Age is computed, never stored.
    assert all(p["age"] is not None for p in admitted)


def test_patient_search(client):
    r = client.get("/patients", params={"q": "alvarez"})
    assert any("Alvarez" in (p["full_name"] or "") for p in r.json())


def test_chart_aggregate(client):
    r = client.get("/patients/hero-a-stroke/chart")
    assert r.status_code == 200
    chart = r.json()
    assert chart["active_encounter"]["status"] == "in-progress"
    assert chart["current_disposition"]["predicted_disposition"] == "snf"
    assert any(l["status"] == "pending" for l in chart["pending_labs"])
    assert len(chart["active_problems"]) >= 3
    # raw_fhir is stripped from list payloads by default.
    assert "raw_fhir" not in chart["patient"]


def test_labs_pending_filter(client):
    r = client.get("/patients/hero-a-stroke/labs", params={"status": "pending"})
    assert r.status_code == 200
    labs = r.json()
    assert labs and all(l["status"] == "pending" for l in labs)


def test_facility_placement_search(client):
    r = client.get("/facilities", params={"facility_type": "snf", "has_available_beds": True})
    facs = r.json()
    assert facs and all(f["available_beds"] and f["available_beds"] > 0 for f in facs)


def test_order_lifecycle(client, fresh_db):
    # Pend a consult order (draft), then sign it.
    r = client.post(
        "/orders",
        json={
            "patient_id": "hero-b-chf",
            "order_type": "consult",
            "display": "PT/OT eval",
            "ordered_by": "Placer",
        },
    )
    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "draft"

    r = client.post(f"/orders/{order['id']}/sign", json={"signed_by": "Dr. Feld"})
    assert r.json()["status"] == "signed"

    # Cannot edit a signed order.
    r = client.patch(f"/orders/{order['id']}", json={"detail": "x"})
    assert r.status_code == 409


def test_lab_order_materializes_and_results(client, fresh_db):
    # Sign a lab order -> a pending observation is created and linked.
    r = client.post(
        "/orders",
        json={
            "patient_id": "hero-d-ambiguous",
            "order_type": "lab",
            "display": "SARS-CoV-2 NAA test",
            "code": "94500-6",
            "ordered_by": "Placer",
            "status": "signed",
        },
    )
    order = r.json()
    obs_id = order["result_observation_id"]
    assert obs_id

    pending = client.get("/patients/hero-d-ambiguous/labs", params={"status": "pending"}).json()
    assert any(l["id"] == obs_id for l in pending)

    # Result it -> final, and the order auto-completes.
    r = client.post(f"/labs/{obs_id}/result", json={"value_string": "Not detected", "status": "final"})
    assert r.json()["status"] == "final"
    assert client.get(f"/orders/{order['id']}").json()["status"] == "completed"


def test_dispo_assessment_supersession(client, fresh_db):
    before = client.get("/patients/hero-c-hospice/dispo-assessments").json()
    r = client.post(
        "/dispo-assessments",
        json={
            "patient_id": "hero-c-hospice",
            "predicted_disposition": "hospice_facility",
            "confidence": 0.6,
            "assessed_by": "Placer",
        },
    )
    assert r.status_code == 201
    assert r.json()["is_current"] is True
    after = client.get("/patients/hero-c-hospice/dispo-assessments").json()
    assert len(after) == len(before) + 1
    # Exactly one current assessment.
    assert sum(1 for a in after if a["is_current"]) == 1


def test_note_crud_and_sign(client, fresh_db):
    r = client.post(
        "/notes",
        json={
            "patient_id": "hero-a-stroke",
            "note_type": "case_management",
            "title": "Dispo planning",
            "text": "Working SNF placement.",
            "author": "Placer",
            "authored_by_agent": True,
        },
    )
    assert r.status_code == 201
    note = r.json()
    assert note["status"] == "draft"

    r = client.post(f"/notes/{note['id']}/sign", params={"signed_by": "Dr. Nadkarni"})
    assert r.json()["status"] == "signed"
    # Signed notes are immutable.
    assert client.patch(f"/notes/{note['id']}", json={"text": "y"}).status_code == 409


def test_communication_logging(client, fresh_db):
    r = client.post(
        "/communications",
        json={
            "patient_id": "hero-a-stroke",
            "facility_id": "fac-sunny-acres",
            "party_type": "snf",
            "party_name": "Sunny Acres admissions",
            "summary": "Confirmed bed availability.",
            "outcome": "bed_available",
        },
    )
    assert r.status_code == 201
    comms = client.get("/communications", params={"patient_id": "hero-a-stroke"}).json()
    assert any(c["outcome"] == "bed_available" for c in comms)


def test_dispo_assessments_global_list(client):
    rows = client.get("/dispo-assessments").json()
    # One current assessment per hero, at minimum.
    assert len(rows) >= 4
    assert any(r["patient_id"] == "hero-a-stroke" for r in rows)

    current_only = client.get("/dispo-assessments", params={"is_current": True}).json()
    assert all(r["is_current"] for r in current_only)

    scoped = client.get("/dispo-assessments", params={"patient_id": "hero-a-stroke"}).json()
    assert all(r["patient_id"] == "hero-a-stroke" for r in scoped)


def test_placer_overview(client):
    r = client.get("/placer/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["counts"]["monitored_patients"] >= 4
    assert body["counts"]["open_tasks"] >= 1
    ids = {p["patient_id"] for p in body["patients"]}
    assert "hero-a-stroke" in ids
    hero_a = next(p for p in body["patients"] if p["patient_id"] == "hero-a-stroke")
    assert hero_a["current_disposition"]["predicted_disposition"] == "snf"
    assert hero_a["open_tasks"] >= 1


def test_placer_activity_feed(client):
    r = client.get("/placer/activity", params={"limit": 500})
    assert r.status_code == 200
    events = r.json()
    event_types = {e["event_type"] for e in events}
    assert {"dispo_assessment", "care_task", "communication", "chat_message"} <= event_types
    # Sorted newest-first.
    timestamps = [e["occurred_at"] for e in events]
    assert timestamps == sorted(timestamps, reverse=True)

    scoped = client.get("/placer/activity", params={"patient_id": "hero-a-stroke", "limit": 500}).json()
    assert all(e["patient_id"] == "hero-a-stroke" for e in scoped)

    tasks_only = client.get("/placer/activity", params={"event_type": "care_task", "limit": 500}).json()
    assert all(e["event_type"] == "care_task" for e in tasks_only)
    assert len(tasks_only) >= 1


def test_404_shape(client):
    r = client.get("/patients/does-not-exist")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()


def test_reset_restores_state(client):
    # Create an order, then reset, and confirm it's gone.
    client.post(
        "/orders",
        json={"patient_id": "hero-a-stroke", "order_type": "nursing", "display": "temp order"},
    )
    client.post("/admin/reset")
    orders = client.get("/orders", params={"patient_id": "hero-a-stroke"}).json()
    assert all(o["display"] != "temp order" for o in orders)
