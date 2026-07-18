"""Worker dispatch + handler tests, fully offline.

Seams stubbed: ``placer.llm.structured`` (LLM), EHRClient methods (recorded,
no network), and ``placer.api.chat`` (a fake module in sys.modules). Calling
is disabled by default (no telephony integration), so every external-contact
worker must park as waiting WITHOUT writing anything — no simulated outcomes.
"""

from __future__ import annotations

import json
import sys
import types

import pytest
from sqlmodel import select

from placer import calls, config
from placer.models import Barrier, Case, DispoTask, FacilityIntel, Referral
from placer.workers import run_task

# ---------------------------------------------------------------------------
# Stubs / fixtures
# ---------------------------------------------------------------------------

FACILITIES = [
    {"id": "fac-1", "name": "Sunrise SNF", "facility_type": "snf", "available_beds": 3},
    {"id": "fac-2", "name": "Oak Grove SNF", "facility_type": "snf", "available_beds": 1},
    {"id": "fac-3", "name": "Willow SNF", "facility_type": "snf", "available_beds": 0},
    {"id": "fac-4", "name": "Cedar SNF", "facility_type": "snf", "available_beds": 5},
]

CHART = {
    "patient": {"name": "Alma Hero", "age": 81, "address": "12 Elm St"},
    "active_problems": [{"display": "Ischemic stroke"}],
}

WAITING_NOTE = "Real call required — calling is not yet enabled (Bland integration pending)"


@pytest.fixture()
def chat_log(monkeypatch):
    """Fake placer.api.chat module (chat surface owned by the API layer)."""
    log = []
    mod = types.ModuleType("placer.api.chat")

    def post_message(session, content, *, case_id=None, kind="text", author="placer", approval_id=None):
        log.append({"content": content, "case_id": case_id, "kind": kind})

    mod.post_message = post_message
    monkeypatch.setitem(sys.modules, "placer.api.chat", mod)
    return log


@pytest.fixture()
def ehr_log(monkeypatch):
    """Record-only EHRClient: no httpx client, no network."""
    from placer.ehr_client import EHRClient

    log = {"orders": [], "comms": [], "facility_updates": [], "actors": [], "existing_orders": []}

    def fake_init(self, base_url=None, actor="agent:test", timeout=10.0):
        self.actor = actor
        log["actors"].append(actor)

    def create_order(self, **kw):
        log["orders"].append(kw)
        return {"id": f"order-{len(log['orders'])}", "status": kw.get("status", "draft")}

    def list_orders(self, patient_id, status=None, order_type=None):
        return list(log["existing_orders"])

    def create_communication(self, **kw):
        log["comms"].append(kw)
        return {"id": f"comm-{len(log['comms'])}"}

    def list_facilities(self, facility_type=None, has_available_beds=None):
        return [f for f in FACILITIES if facility_type in (None, f["facility_type"])]

    def update_facility(self, facility_id, **fields):
        log["facility_updates"].append((facility_id, fields))
        return {"id": facility_id, **fields}

    monkeypatch.setattr(EHRClient, "__init__", fake_init)
    monkeypatch.setattr(EHRClient, "close", lambda self: None)
    monkeypatch.setattr(EHRClient, "create_order", create_order)
    monkeypatch.setattr(EHRClient, "list_orders", list_orders)
    monkeypatch.setattr(EHRClient, "create_communication", create_communication)
    monkeypatch.setattr(EHRClient, "list_facilities", list_facilities)
    monkeypatch.setattr(EHRClient, "update_facility", update_facility)
    monkeypatch.setattr(EHRClient, "get_chart", lambda self, patient_id: dict(CHART))
    return log


@pytest.fixture()
def case(session):
    c = Case(patient_id="hero-a-stroke", encounter_id="enc-1", state="committed")
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def make_task(session, case, task_type, payload=None):
    task = DispoTask(
        case_id=case.id,
        task_type=task_type,
        title=task_type,
        detail=json.dumps(payload) if payload else None,
        status="approved",
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def make_referral(session, case, facility_id="fac-1", name="Sunrise SNF", status="shortlisted", pathway_id=11):
    ref = Referral(
        case_id=case.id, pathway_id=pathway_id, facility_id=facility_id,
        facility_name=name, status=status,
    )
    session.add(ref)
    session.commit()
    session.refresh(ref)
    return ref


def assert_waiting_on_telephony(result):
    assert result["waiting_on"] == "telephony"
    assert result["note"] == WAITING_NOTE


# ---------------------------------------------------------------------------
# Call layer: no fabrication, ever
# ---------------------------------------------------------------------------


def test_place_call_disabled_raises_calling_unavailable():
    assert config.CALL_MODE == "disabled"  # the default: no telephony
    with pytest.raises(calls.CallingUnavailable):
        calls.place_call("objective", ["q"], {"role": "facility"}, "context")


def test_place_call_bland_not_implemented_yet(monkeypatch):
    monkeypatch.setattr(config, "CALL_MODE", "bland")
    with pytest.raises(NotImplementedError, match="bland"):
        calls.place_call("objective", ["q"], {"role": "facility"}, "context")


def test_place_call_unknown_mode_rejected(monkeypatch):
    monkeypatch.setattr(config, "CALL_MODE", "simulated")  # removed mode
    with pytest.raises(ValueError, match="simulated"):
        calls.place_call("objective", ["q"], {"role": "facility"}, "context")


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def test_unknown_task_type_raises(session, case, chat_log, ehr_log):
    task = make_task(session, case, "frobnicate")
    with pytest.raises(ValueError, match="frobnicate"):
        run_task(session, task)


def test_run_task_never_touches_status_and_sets_result(session, case, chat_log, ehr_log):
    task = make_task(session, case, "book_transport")
    result = run_task(session, task)
    assert task.status == "approved"  # lifecycle is the brain's job
    assert task.result == result


# ---------------------------------------------------------------------------
# Clinical Prep
# ---------------------------------------------------------------------------


def test_draft_order_creates_draft_ehr_order(session, case, chat_log, ehr_log):
    task = make_task(session, case, "draft_order",
                     {"order_type": "lab", "display": "CBC with differential", "detail": "Pre-discharge labs"})
    result = run_task(session, task)
    assert len(ehr_log["orders"]) == 1
    order = ehr_log["orders"][0]
    assert order["status"] == "draft"
    assert order["order_type"] == "lab"
    assert order["display"] == "CBC with differential"
    assert order["patient_id"] == "hero-a-stroke"
    assert result["order_id"] == "order-1"
    assert ehr_log["actors"] == ["agent:clinical-prep"]
    assert any("pended" in m["content"] for m in chat_log)


def test_draft_order_dedupes_existing_covid_order(session, case, chat_log, ehr_log):
    """A signed 'SARS-CoV-2 (COVID-19) NAA test' already covers an intended
    'COVID-19 PCR' — no second order, result references the existing one."""
    ehr_log["existing_orders"] = [
        {"id": "ehr-order-77", "order_type": "lab", "status": "signed",
         "display": "SARS-CoV-2 (COVID-19) NAA test"},
    ]
    task = make_task(session, case, "draft_order",
                     {"order_type": "lab", "display": "COVID-19 PCR", "detail": "Required for SNF intake"})
    result = run_task(session, task)
    assert ehr_log["orders"] == []  # nothing created
    assert result["deduped"] is True
    assert result["order_id"] == "ehr-order-77"
    assert result["status"] == "signed"
    assert any("already ordered" in m["content"] and "instead of reordering" in m["content"]
               for m in chat_log)


def test_draft_order_ignores_completed_and_unrelated_orders(session, case, chat_log, ehr_log):
    ehr_log["existing_orders"] = [
        {"id": "o1", "order_type": "lab", "status": "completed",
         "display": "SARS-CoV-2 (COVID-19) NAA test"},  # done — re-order allowed
        {"id": "o2", "order_type": "lab", "status": "signed", "display": "Basic metabolic panel"},
        {"id": "o3", "order_type": "consult", "status": "draft", "display": "COVID clearance consult"},
    ]
    result = run_task(session, make_task(session, case, "draft_order",
                                         {"order_type": "lab", "display": "COVID-19 PCR"}))
    assert len(ehr_log["orders"]) == 1
    assert result.get("deduped") is None


def test_draft_consult_forces_consult_type(session, case, chat_log, ehr_log):
    task = make_task(session, case, "draft_consult", {"display": "PM&R evaluation"})
    run_task(session, task)
    assert ehr_log["orders"][0]["order_type"] == "consult"
    assert ehr_log["orders"][0]["status"] == "draft"


def test_draft_consult_dedupes_existing_consult(session, case, chat_log, ehr_log):
    ehr_log["existing_orders"] = [
        {"id": "c-1", "order_type": "consult", "status": "draft", "display": "PM&R consult"},
    ]
    result = run_task(session, make_task(session, case, "draft_consult",
                                         {"display": "PM&R evaluation for IRF"}))
    assert ehr_log["orders"] == []
    assert result["order_id"] == "c-1"


# ---------------------------------------------------------------------------
# Placement — no telephony: park as waiting, write NOTHING
# ---------------------------------------------------------------------------


def test_build_shortlist_ranks_caps_and_dedupes(session, case, chat_log, ehr_log):
    result = run_task(session, make_task(session, case, "build_shortlist", {"pathway_id": 11}))
    ids = [r["facility_id"] for r in result["referrals"]]
    assert ids == ["fac-4", "fac-1", "fac-2"]  # ranked by beds, capped at 3
    assert result["facility_type"] == "snf"

    # Second run must not duplicate — only the remaining facility gets added.
    result2 = run_task(session, make_task(session, case, "build_shortlist", {"pathway_id": 11}))
    assert [r["facility_id"] for r in result2["referrals"]] == ["fac-3"]
    all_refs = session.exec(select(Referral).where(Referral.case_id == case.id)).all()
    assert len(all_refs) == 4
    assert len({r.facility_id for r in all_refs}) == 4

    # Third run: nothing left to shortlist.
    result3 = run_task(session, make_task(session, case, "build_shortlist", {"pathway_id": 11}))
    assert result3["referrals"] == []


def test_build_shortlist_unmapped_pathway_raises(session, case, chat_log, ehr_log):
    with pytest.raises(ValueError, match="mapping"):
        run_task(session, make_task(session, case, "build_shortlist", {"pathway_id": 4}))


def test_intake_call_waits_on_telephony_and_writes_nothing(session, case, chat_log, ehr_log):
    ref = make_referral(session, case, status="shortlisted")
    result = run_task(session, make_task(session, case, "facility_intake_call", {"referral_id": ref.id}))
    assert_waiting_on_telephony(result)
    session.refresh(ref)
    assert ref.status == "shortlisted"  # not advanced
    assert ref.notes is None
    assert ehr_log["comms"] == []
    assert ehr_log["facility_updates"] == []
    assert session.exec(select(FacilityIntel)).all() == []
    session.refresh(case)
    assert case.dirty is False


def test_screen_call_waits_on_telephony(session, case, chat_log, ehr_log):
    ref = make_referral(session, case, status="intake_verified")
    result = run_task(session, make_task(session, case, "facility_screen_call", {"referral_id": ref.id}))
    assert_waiting_on_telephony(result)
    session.refresh(ref)
    assert ref.status == "intake_verified"
    assert ehr_log["comms"] == []


def test_submit_referral_waits_on_portal_no_fake_confirmation(session, case, chat_log, ehr_log):
    ref = make_referral(session, case, status="screened")
    result = run_task(session, make_task(session, case, "submit_referral", {"referral_id": ref.id}))
    assert result["waiting_on"] == "referral_portal"
    assert "referral portal integration pending" in result["note"]
    assert "confirmation" not in result
    session.refresh(ref)
    assert ref.status == "screened"  # untouched
    assert ref.notes is None
    assert ehr_log["comms"] == []


def test_submit_referral_already_submitted_short_circuits(session, case, chat_log, ehr_log):
    ref = make_referral(session, case, status="pending")
    result = run_task(session, make_task(session, case, "submit_referral", {"referral_id": ref.id}))
    assert result == {"referral_id": ref.id, "status": "pending", "note": "already submitted"}


def test_finalize_acceptance_waits_on_telephony_barriers_untouched(session, case, chat_log, ehr_log):
    ref = make_referral(session, case, status="pending")
    dest = Barrier(case_id=case.id, pathway_ids=[11], dimension="destination",
                   btype="no_bed_secured", status="open")
    session.add(dest)
    session.commit()
    result = run_task(session, make_task(session, case, "finalize_acceptance", {"referral_id": ref.id}))
    assert_waiting_on_telephony(result)
    session.refresh(ref)
    assert ref.status == "pending"
    assert ref.bed_hold_expires is None
    session.refresh(dest)
    assert dest.status == "open"  # no invented acceptance, no barrier clear
    assert ehr_log["facility_updates"] == []


# ---------------------------------------------------------------------------
# Family Liaison — no telephony: park as waiting
# ---------------------------------------------------------------------------


def test_preference_call_waits_on_telephony_no_invented_preferences(session, case, chat_log, ehr_log):
    result = run_task(session, make_task(session, case, "preference_call"))
    assert_waiting_on_telephony(result)
    session.refresh(case)
    assert (case.facts or {}).get("preference_profile") is None
    assert case.dirty is False
    assert ehr_log["comms"] == []
    assert chat_log == []  # the loop posts the single waiting note, not the worker


# ---------------------------------------------------------------------------
# Coverage — asks the team, never invents a payer verdict
# ---------------------------------------------------------------------------


def test_verify_benefits_asks_team_and_waits(session, case, chat_log, ehr_log):
    payer = Barrier(case_id=case.id, pathway_ids=[11], dimension="payer",
                    btype="auth_pending", status="open")
    session.add(payer)
    session.commit()
    result = run_task(session, make_task(session, case, "verify_benefits", {"pathway_ids": [11]}))
    assert result["waiting_on"] == "team"
    assert result["chat_posted"] is True
    assert result["levels"] == ["SNF / subacute / TCU"]
    session.refresh(payer)
    assert payer.status == "open"  # barrier untouched — no invented verdict
    assert ehr_log["comms"] == []  # no fabricated payer communication
    # Exactly ONE chat note, routed as a question for a human.
    assert len(chat_log) == 1
    assert chat_log[0]["kind"] == "text"
    assert "needs a human" in chat_log[0]["content"]
    assert "verify payer benefits" in chat_log[0]["content"]


# ---------------------------------------------------------------------------
# Transitions / misc
# ---------------------------------------------------------------------------


def test_book_transport_waits_on_telephony_barrier_stays(session, case, chat_log, ehr_log):
    barrier = Barrier(case_id=case.id, dimension="transport", btype="no_ride", status="open")
    session.add(barrier)
    session.commit()
    result = run_task(session, make_task(session, case, "book_transport"))
    assert_waiting_on_telephony(result)
    assert "booking_ref" not in result  # no invented booking reference
    session.refresh(barrier)
    assert barrier.status == "open"
    assert ehr_log["comms"] == []


def test_message_team_posts_plain_text_chat(session, case, chat_log, ehr_log):
    result = run_task(session, make_task(session, case, "message_team",
                                         {"question": "Does the patient have a POLST on file?"}))
    assert result == {"noted": True, "question": "Does the patient have a POLST on file?"}
    assert len(chat_log) == 1
    assert chat_log[0]["kind"] == "text"
    assert "needs a human" in chat_log[0]["content"]
    assert "POLST" in chat_log[0]["content"]
