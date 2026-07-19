"""Worker dispatch + handler tests, fully offline.

Seams stubbed: ``placer.llm.structured`` (LLM), ``placer.calls.place_call``
(the call layer, where a handler consumes CallResult), ``EHRClient`` methods
(recorded, no network), and ``placer.api.chat`` (a fake module in sys.modules,
since the real one is built by a parallel wave).
"""

from __future__ import annotations

import json
import sys
import types

import pytest

from placer.calls.schemas import CallResult
from placer.models import Barrier, Case, DispoTask, FacilityIntel, Referral
from placer.workers import run_task
from placer.workers.family import PREFERENCE_QUESTIONS

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


@pytest.fixture()
def chat_log(monkeypatch):
    """Fake placer.api.chat module (owned by a parallel wave)."""
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

    log = {"orders": [], "comms": [], "facility_updates": [], "actors": [], "calls": []}

    def fake_init(self, base_url=None, actor="agent:test", timeout=10.0):
        self.actor = actor
        log["actors"].append(actor)

    def create_order(self, **kw):
        log["orders"].append(kw)
        return {"id": f"order-{len(log['orders'])}", "status": kw.get("status", "draft")}

    def create_communication(self, **kw):
        log["comms"].append(kw)
        return {"id": f"comm-{len(log['comms'])}"}

    def list_facilities(self, facility_type=None, has_available_beds=None):
        return [f for f in FACILITIES if facility_type in (None, f["facility_type"])]

    def update_facility(self, facility_id, **fields):
        log["facility_updates"].append((facility_id, fields))
        return {"id": facility_id, **fields}

    def place_call(self, **kw):
        log["calls"].append(kw)
        return {"call_id": f"bland-{len(log['calls'])}", "communication": {"id": "comm-x"}}

    monkeypatch.setattr(EHRClient, "__init__", fake_init)
    monkeypatch.setattr(EHRClient, "close", lambda self: None)
    monkeypatch.setattr(EHRClient, "create_order", create_order)
    monkeypatch.setattr(EHRClient, "create_communication", create_communication)
    monkeypatch.setattr(EHRClient, "list_facilities", list_facilities)
    monkeypatch.setattr(EHRClient, "update_facility", update_facility)
    monkeypatch.setattr(EHRClient, "place_call", place_call)
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


def stub_call(monkeypatch, result: CallResult):
    """Stub the call layer with a canned CallResult AND enable calls: a stubbed
    call stands in for the simulated/twilio (PLACE_CALLS=True) path."""
    monkeypatch.setattr("placer.config.PLACE_CALLS", True)
    made = []

    def fake_place_call(objective, questions, callee, context):
        made.append({"objective": objective, "questions": questions, "callee": callee})
        return result

    monkeypatch.setattr("placer.calls.place_call", fake_place_call)
    return made


@pytest.fixture()
def enabled_calls(monkeypatch):
    """Turn on outbound calls for tests of the enabled (simulated) path that do
    not go through ``stub_call`` (coverage/submit_referral read the flag)."""
    monkeypatch.setattr("placer.config.PLACE_CALLS", True)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def test_unknown_task_type_raises(session, case, chat_log, ehr_log):
    task = make_task(session, case, "frobnicate")
    with pytest.raises(ValueError, match="frobnicate"):
        run_task(session, task)


def test_run_task_never_touches_status_and_sets_result(session, case, chat_log, ehr_log, monkeypatch):
    stub_call(monkeypatch, CallResult(transcript="t", outcome="ok", answers={}, notes=""))
    task = make_task(session, case, "book_transport")
    result = run_task(session, task)
    assert task.status == "approved"  # lifecycle is the brain's job
    assert task.result == result


# ---------------------------------------------------------------------------
# Clinical Prep
# ---------------------------------------------------------------------------


def test_draft_order_creates_draft_ehr_order(session, case, chat_log, ehr_log):
    task = make_task(session, case, "draft_order",
                     {"order_type": "lab", "display": "COVID-19 PCR", "detail": "Required for SNF intake"})
    result = run_task(session, task)
    assert len(ehr_log["orders"]) == 1
    order = ehr_log["orders"][0]
    assert order["status"] == "draft"
    assert order["order_type"] == "lab"
    assert order["display"] == "COVID-19 PCR"
    assert order["patient_id"] == "hero-a-stroke"
    assert result["order_id"] == "order-1"
    assert ehr_log["actors"] == ["agent:clinical-prep"]
    assert any("pended" in m["content"] for m in chat_log)


def test_draft_consult_forces_consult_type(session, case, chat_log, ehr_log):
    task = make_task(session, case, "draft_consult", {"display": "PM&R evaluation"})
    run_task(session, task)
    assert ehr_log["orders"][0]["order_type"] == "consult"
    assert ehr_log["orders"][0]["status"] == "draft"


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------


def test_build_shortlist_ranks_caps_and_dedupes(session, case, chat_log, ehr_log):
    from sqlmodel import select

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


def test_intake_call_verifies_and_updates_intel(session, case, chat_log, ehr_log, monkeypatch):
    from sqlmodel import select

    ref = make_referral(session, case, status="shortlisted")
    stub_call(monkeypatch, CallResult(
        transcript="Placer: ...", outcome="Two beds open; referrals via portal",
        answers={"How many beds do you currently have available?": "2 beds right now"},
        notes="",
    ))
    result = run_task(session, make_task(session, case, "facility_intake_call", {"referral_id": ref.id}))
    assert ref.status == "intake_verified"
    assert result["beds_available"] == 2
    intel = session.exec(select(FacilityIntel).where(FacilityIntel.facility_id == "fac-1")).first()
    assert intel.beds_available == 2 and intel.last_verified_at is not None
    assert ("fac-1", {"available_beds": 2}) in ehr_log["facility_updates"]
    assert ehr_log["comms"][0]["party_type"] == "facility"


def test_intake_call_hard_no_capacity_declines(session, case, chat_log, ehr_log, monkeypatch):
    ref = make_referral(session, case, facility_id="fac-3", name="Willow SNF")
    stub_call(monkeypatch, CallResult(
        transcript="t", outcome="Census full, no beds",
        answers={"How many beds do you currently have available?": "0"}, notes="",
    ))
    run_task(session, make_task(session, case, "facility_intake_call", {"referral_id": ref.id}))
    assert ref.status == "declined"
    assert ref.denial_reason == "no_bed"
    assert case.dirty is True


def test_screen_call_advances_to_screened_with_pathway_questions(session, case, chat_log, ehr_log, monkeypatch):
    ref = make_referral(session, case, status="intake_verified")
    made = stub_call(monkeypatch, CallResult(
        transcript="t", outcome="Can meet all clinical needs",
        answers={"Does the patient need IV therapy, and can the facility administer it?": "Yes, we run IV antibiotics"},
        notes="",
    ))
    result = run_task(session, make_task(session, case, "facility_screen_call", {"referral_id": ref.id}))
    assert ref.status == "screened"
    assert result["denial_reason"] is None
    # The pathway-11 requirement checklist drove the call.
    assert len(made[0]["questions"]) == 8
    assert "IV therapy" in " ".join(made[0]["questions"])
    assert "Screen call:" in ref.notes


def test_screen_call_decline_records_categorized_reason(session, case, chat_log, ehr_log, monkeypatch):
    from sqlmodel import select

    ref = make_referral(session, case, facility_id="fac-2", name="Oak Grove SNF", status="intake_verified")
    stub_call(monkeypatch, CallResult(
        transcript="t", outcome="Declined: cannot manage a wound VAC",
        answers={}, notes="No wound-care nurse on staff",
    ))
    result = run_task(session, make_task(session, case, "facility_screen_call", {"referral_id": ref.id}))
    assert ref.status == "declined"
    assert ref.denial_reason == "clinical_capability"
    assert result["denial_reason"] == "clinical_capability"
    intel = session.exec(select(FacilityIntel).where(FacilityIntel.facility_id == "fac-2")).first()
    assert len(intel.decline_history) == 1
    assert intel.decline_history[0]["reason"] == "clinical_capability"
    assert case.dirty is True


def test_screen_call_from_terminal_state_raises(session, case, chat_log, ehr_log, monkeypatch):
    ref = make_referral(session, case, status="accepted")
    stub_call(monkeypatch, CallResult(transcript="t", outcome="ok", answers={}, notes=""))
    with pytest.raises(ValueError, match="accepted"):
        run_task(session, make_task(session, case, "facility_screen_call", {"referral_id": ref.id}))


def test_submit_referral_generates_confirmation(session, case, chat_log, ehr_log, enabled_calls):
    ref = make_referral(session, case, status="screened")
    result = run_task(session, make_task(session, case, "submit_referral", {"referral_id": ref.id}))
    assert ref.status == "pending"
    assert result["confirmation"].startswith("REF-")
    assert result["confirmation"] in ref.notes
    assert ehr_log["comms"][0]["modality"] == "portal"


def test_finalize_acceptance_clears_destination_barrier_and_holds_bed(session, case, chat_log, ehr_log, monkeypatch):
    ref = make_referral(session, case, status="pending")
    dest = Barrier(case_id=case.id, pathway_ids=[11], dimension="destination",
                   btype="no_bed_secured", status="open")
    medical = Barrier(case_id=case.id, dimension="medical", btype="iv_abx_course", status="open")
    session.add(dest)
    session.add(medical)
    session.commit()

    stub_call(monkeypatch, CallResult(
        transcript="t", outcome="Accepted; bed held for 48 hours", answers={}, notes="",
    ))
    result = run_task(session, make_task(session, case, "finalize_acceptance", {"referral_id": ref.id}))
    assert ref.status == "accepted"
    assert ref.bed_hold_expires is not None
    assert result["barriers_cleared"] == 1
    assert dest.status == "cleared"
    assert medical.status == "open"  # never touch medical barriers
    assert case.dirty is True
    # The taken bed is mirrored back to the EHR (fac-1 had 3).
    assert ("fac-1", {"available_beds": 2}) in ehr_log["facility_updates"]
    assert any("Bed secured at Sunrise SNF" in m["content"] for m in chat_log)


def test_finalize_decline_categorizes_and_records(session, case, chat_log, ehr_log, monkeypatch):
    ref = make_referral(session, case, status="pending")
    stub_call(monkeypatch, CallResult(
        transcript="t", outcome="Declined — patient is out of network for their plan",
        answers={}, notes="",
    ))
    result = run_task(session, make_task(session, case, "finalize_acceptance", {"referral_id": ref.id}))
    assert ref.status == "declined"
    assert result["denial_reason"] == "network"
    assert ref.bed_hold_expires is None


# ---------------------------------------------------------------------------
# Family Liaison
# ---------------------------------------------------------------------------


def test_preference_call_writes_facts_and_communication(session, case, chat_log, ehr_log, monkeypatch):
    stub_call(monkeypatch, CallResult(
        transcript="Placer: Hi...\nFamily: ...",
        outcome="Family prefers home with daughter as caregiver",
        answers={PREFERENCE_QUESTIONS[0]: "Home with her daughter", PREFERENCE_QUESTIONS[2]: "No SNF far from Oakland"},
        follow_up_needed=False,
        notes="Daughter works weekdays",
    ))
    result = run_task(session, make_task(session, case, "preference_call"))
    profile = case.facts["preference_profile"]
    assert profile["answers"][PREFERENCE_QUESTIONS[0]] == "Home with her daughter"
    assert result["preference_profile"] == profile
    assert case.dirty is True
    comm = ehr_log["comms"][0]
    assert comm["party_type"] == "family"
    assert comm["transcript"].startswith("Placer:")
    assert any("Home with her daughter" in m["content"] for m in chat_log)
    assert ehr_log["actors"] == ["agent:family-liaison"]


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


def test_verify_benefits_clears_payer_barrier_when_clean(session, case, chat_log, ehr_log, monkeypatch, enabled_calls):
    from placer.workers.coverage import BenefitsCheck

    payer = Barrier(case_id=case.id, pathway_ids=[11], dimension="payer",
                    btype="auth_pending", status="open")
    session.add(payer)
    session.commit()
    monkeypatch.setattr("placer.llm.structured", lambda prompt, schema, **kw: BenefitsCheck(
        covered=True, auth_required=False, network_note="in-network SNFs", reference="PAY-123"))
    result = run_task(session, make_task(session, case, "verify_benefits", {"pathway_ids": [11]}))
    assert payer.status == "cleared"
    assert result["covered"] is True and result["barriers_cleared"] == 1
    assert ehr_log["comms"][0]["party_type"] == "insurance"


def test_verify_benefits_auth_needed_keeps_barrier_open(session, case, chat_log, ehr_log, monkeypatch, enabled_calls):
    from sqlmodel import select
    from placer.workers.coverage import BenefitsCheck

    monkeypatch.setattr("placer.llm.structured", lambda prompt, schema, **kw: BenefitsCheck(
        covered=True, auth_required=True, network_note=None, reference="PAY-9"))
    result = run_task(session, make_task(session, case, "verify_benefits", {"pathway_ids": [11]}))
    assert result["barriers_cleared"] == 0
    barrier = session.exec(select(Barrier).where(Barrier.case_id == case.id,
                                                 Barrier.dimension == "payer")).first()
    assert barrier is not None and barrier.status == "open"
    assert "authorization" in barrier.description


# ---------------------------------------------------------------------------
# Transitions / misc
# ---------------------------------------------------------------------------


def test_book_transport_clears_transport_barrier(session, case, chat_log, ehr_log, monkeypatch):
    barrier = Barrier(case_id=case.id, dimension="transport", btype="no_ride", status="open")
    session.add(barrier)
    session.commit()
    stub_call(monkeypatch, CallResult(
        transcript="t", outcome="Booked wheelchair van for Friday 10am", answers={}, notes=""))
    result = run_task(session, make_task(session, case, "book_transport"))
    assert barrier.status == "cleared"
    assert result["booking_ref"].startswith("TRN-")
    assert result["barriers_cleared"] == 1


def test_message_team_posts_plain_text_chat(session, case, chat_log, ehr_log):
    result = run_task(session, make_task(session, case, "message_team",
                                         {"question": "Does the patient have a POLST on file?"}))
    assert result == {"noted": True, "question": "Does the patient have a POLST on file?"}
    assert len(chat_log) == 1
    assert chat_log[0]["kind"] == "text"
    assert "needs a human" in chat_log[0]["content"]
    assert "POLST" in chat_log[0]["content"]


# ---------------------------------------------------------------------------
# Calls disabled (the NEW default): workers must PARK, never fabricate.
#
# No stub_call / enabled_calls here — config.PLACE_CALLS defaults False, so the
# real place_call raises CallsDisabled (and coverage/submit read the flag).
# The contract for every parked run: result {"parked": True}, NO communication
# row, the relevant barrier stays OPEN, and no fabricated referral/bed state.
# ---------------------------------------------------------------------------


def test_verify_benefits_parks_when_calls_disabled(session, case, chat_log, ehr_log, monkeypatch):
    from sqlmodel import select

    called = []
    monkeypatch.setattr("placer.llm.structured",
                        lambda *a, **k: called.append(1))  # must NOT be invoked
    payer = Barrier(case_id=case.id, pathway_ids=[11], dimension="payer",
                    btype="auth_pending", status="open")
    session.add(payer)
    session.commit()

    result = run_task(session, make_task(session, case, "verify_benefits", {"pathway_ids": [11]}))
    assert result["parked"] is True and result["reason"] == "calls_disabled"
    assert called == []                    # no payer role-play
    assert ehr_log["comms"] == []          # no fabricated communication
    session.refresh(payer)
    assert payer.status == "open"          # barrier left open


def test_book_transport_parks_when_calls_disabled(session, case, chat_log, ehr_log):
    barrier = Barrier(case_id=case.id, dimension="transport", btype="no_ride", status="open")
    session.add(barrier)
    session.commit()

    result = run_task(session, make_task(session, case, "book_transport"))
    assert result["parked"] is True
    assert "booking_ref" not in result
    assert ehr_log["comms"] == []
    session.refresh(barrier)
    assert barrier.status == "open"        # transport barrier not cleared


def test_preference_call_parks_when_calls_disabled(session, case, chat_log, ehr_log):
    result = run_task(session, make_task(session, case, "preference_call"))
    assert result["parked"] is True
    assert ehr_log["comms"] == []
    session.refresh(case)
    assert "preference_profile" not in (case.facts or {})  # nothing fabricated


def test_facility_intake_parks_and_is_idempotent_when_calls_disabled(session, case, chat_log, ehr_log):
    from sqlmodel import select

    ref = make_referral(session, case, status="shortlisted")

    # Invoke repeatedly while parked — must not accumulate rows or advance state.
    for _ in range(3):
        result = run_task(session, make_task(session, case, "facility_intake_call", {"referral_id": ref.id}))
        assert result["parked"] is True
    session.refresh(ref)
    assert ref.status == "shortlisted"         # no advance to intake_verified
    assert ehr_log["comms"] == []              # no facility communication
    assert ehr_log["facility_updates"] == []   # no fabricated bed count
    assert len(session.exec(select(FacilityIntel)).all()) == 0
    assert len(session.exec(select(Referral).where(Referral.case_id == case.id)).all()) == 1


def test_snf_intake_places_real_bland_call_and_parks(session, case, chat_log, ehr_log, monkeypatch):
    """With PLACER_SNF_CALLS on, a SNF bed-check dials a REAL call via /calls and
    parks awaiting the outcome — no fabricated beds, no engine-written comm, and
    it never re-dials the same facility."""
    monkeypatch.setattr("placer.config.SNF_CALLS", True)
    ref = make_referral(session, case, facility_id="fac-1", name="Sunrise SNF", status="shortlisted")

    result = run_task(session, make_task(session, case, "facility_intake_call", {"referral_id": ref.id}))
    session.commit()  # the brain executor commits after each task; the idempotency marker persists
    assert result["parked"] is True
    assert result["reason"] == "snf_call_placed"
    assert len(ehr_log["calls"]) == 1                      # one real Bland call
    assert ehr_log["calls"][0]["party_type"] == "snf"
    assert ehr_log["calls"][0]["facility_id"] == "fac-1"
    assert ehr_log["comms"] == []                          # backend logs it, engine must not
    assert ehr_log["facility_updates"] == []              # no fabricated bed count
    session.refresh(ref)
    assert ref.status == "shortlisted"                     # no fabricated advance

    # Idempotent: a second invocation must NOT place another call.
    run_task(session, make_task(session, case, "facility_intake_call", {"referral_id": ref.id}))
    assert len(ehr_log["calls"]) == 1


def test_finalize_acceptance_parks_when_calls_disabled(session, case, chat_log, ehr_log):
    ref = make_referral(session, case, status="pending")
    dest = Barrier(case_id=case.id, pathway_ids=[11], dimension="destination",
                   btype="no_bed_secured", status="open")
    session.add(dest)
    session.commit()

    result = run_task(session, make_task(session, case, "finalize_acceptance", {"referral_id": ref.id}))
    assert result["parked"] is True
    assert ehr_log["comms"] == []
    assert ehr_log["facility_updates"] == []   # no bed decrement
    session.refresh(ref)
    assert ref.status == "pending" and ref.bed_hold_expires is None
    session.refresh(dest)
    assert dest.status == "open"               # destination barrier not cleared


def test_submit_referral_parks_when_calls_disabled(session, case, chat_log, ehr_log):
    ref = make_referral(session, case, status="screened")
    result = run_task(session, make_task(session, case, "submit_referral", {"referral_id": ref.id}))
    assert result["parked"] is True
    assert ehr_log["comms"] == []              # no "packet submitted" + confirmation
    session.refresh(ref)
    assert ref.status == "screened"            # not advanced to pending
