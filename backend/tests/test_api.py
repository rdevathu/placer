"""End-to-end API tests covering the core agent workflows."""

from __future__ import annotations


def test_health(client):
    r = client.get("/admin/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_seed_populated(client):
    counts = client.get("/admin/stats").json()
    assert counts["patients"] >= 29  # 25 imported + 4 heroes
    assert counts["facilities"] >= 6
    assert counts["observations"] > 100


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
            "ordered_by": "dispo-agent",
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
            "ordered_by": "dispo-agent",
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
            "assessed_by": "dispo-agent",
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
            "author": "dispo-agent",
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
