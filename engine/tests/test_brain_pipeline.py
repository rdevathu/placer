"""Pipeline end-to-end (offline): hedged planning for a 50/50 SNF vs
home-health distribution, guardrails, idempotency, commit-proposal card."""

from __future__ import annotations

from sqlmodel import select

from placer.brain import pipeline
from placer.brain.schemas import BarrierOp, GpsAssessment, PathwayScore
from placer.models import Approval, Barrier, Case, DispoTask

from test_brain_helpers import FakeEHR, install_stubs, stub_gps


def _seed_case(session):
    case = Case(patient_id="p1", encounter_id="e1", state="tracking", dirty=True)
    session.add(case)
    session.commit()
    session.add(Barrier(case_id=case.id, dimension="medical", btype="medical_clearance",
                        description="Not yet cleared"))
    session.add(Barrier(case_id=case.id, dimension="decision", btype="family_decision",
                        description="Preference unknown"))
    session.commit()
    return case


def _fifty_fifty_assessment():
    return GpsAssessment(
        distribution=[PathwayScore(pathway_id=11, confidence=0.5),
                      PathwayScore(pathway_id=4, confidence=0.45)],
        rationale="Deconditioned after sepsis; could rehab at SNF or home with services.",
        review_horizon="days",
        brief="72M admitted with sepsis, now stable. " * 2,
        barriers=[
            BarrierOp(op="upsert", dimension="destination", btype="bed_availability",
                      description="No SNF bed identified", evidence="no referral yet",
                      pathway_ids=[11]),
            BarrierOp(op="upsert", dimension="clinical_docs", btype="consult_needed",
                      description="PT/OT eval for home-health plan", evidence="RN note",
                      pathway_ids=[4]),
            BarrierOp(op="upsert", dimension="clinical_docs", btype="pending_lab",
                      description="COVID PCR", evidence="SNF requires negative test",
                      pathway_ids=[11]),
            BarrierOp(op="upsert", dimension="payer", btype="insurance_auth",
                      description="Benefits not verified", evidence="",
                      pathway_ids=[11, 4]),
            # Guardrail check: GPS must not be able to clear medical.
            BarrierOp(op="clear", dimension="medical", btype="medical_clearance"),
        ],
    )


def _tasks(session, case, task_type=None):
    stmt = select(DispoTask).where(DispoTask.case_id == case.id)
    if task_type:
        stmt = stmt.where(DispoTask.task_type == task_type)
    return session.exec(stmt).all()


def test_hedged_plan_for_fifty_fifty_snf_home_health(session, monkeypatch):
    chat_log = install_stubs(monkeypatch)
    stub_gps(monkeypatch, _fifty_fifty_assessment())
    case = _seed_case(session)
    ehr = FakeEHR()

    pipeline.run_assessment(session, case, ehr)

    # Case advanced to predicted with both hypotheses active.
    assert case.state == "predicted"
    assert sorted(p["pathway_id"] for p in case.active_pathways) == [4, 11]
    assert case.next_review_at is not None
    assert "sepsis" in case.brief

    # SNF side: exactly one shortlist build, for pathway 11 (4 is not facility-bound).
    shortlists = _tasks(session, case, "build_shortlist")
    assert len(shortlists) == 1
    assert shortlists[0].pathway_ids == [11]
    assert shortlists[0].mode == "auto" and shortlists[0].status == "pending"
    import json
    assert json.loads(shortlists[0].detail) == {"pathway_id": 11}

    # Home side: the PT/OT consult draft exists, tagged to home health.
    consults = _tasks(session, case, "draft_consult")
    assert len(consults) == 1 and consults[0].pathway_ids == [4]
    labs = _tasks(session, case, "draft_order")
    assert len(labs) == 1 and labs[0].pathway_ids == [11]
    assert json.loads(labs[0].detail)["order_type"] == "lab"

    # Shared work tagged to BOTH pathways, auto -> pending.
    benefits = _tasks(session, case, "verify_benefits")
    assert len(benefits) == 1
    assert sorted(benefits[0].pathway_ids) == [4, 11]
    assert benefits[0].status == "pending"

    # Decision barrier -> preference_call, approval-gated -> suggested + card.
    prefs = _tasks(session, case, "preference_call")
    assert len(prefs) == 1 and prefs[0].status == "suggested"
    suggested_cards = session.exec(
        select(Approval).where(Approval.case_id == case.id, Approval.kind == "suggested")
    ).all()
    assert len(suggested_cards) == 1
    assert prefs[0].id in suggested_cards[0].task_ids
    assert any(m["kind"] == "approval_card" and m["approval_id"] == suggested_cards[0].id
               for m in chat_log)

    # No binding tasks pre-commit.
    assert not _tasks(session, case, "submit_referral")
    assert not _tasks(session, case, "book_transport")

    # Medical barrier survived the GPS 'clear' attempt.
    medical = session.exec(select(Barrier).where(
        Barrier.case_id == case.id, Barrier.dimension == "medical")).one()
    assert medical.status == "open"

    # Assessment mirrored to the EHR with the leader mapped to its dispo type.
    assert len(ehr.assessments) == 1
    posted = ehr.assessments[0]
    assert posted["predicted_disposition"] == "snf"
    assert posted["confidence"] == 0.5
    assert posted["alternatives"][0]["disposition"] == "home_with_services"

    # Commit-proposal card: kind='batch' Approval whose task_ids JSON is the
    # documented dict shape {"pathway_id": leader, "task_ids": [...]}.
    batch = session.exec(select(Approval).where(
        Approval.case_id == case.id, Approval.kind == "batch")).one()
    assert batch.status == "pending"
    assert batch.task_ids["pathway_id"] == 11
    assert set(batch.task_ids["task_ids"]) >= {shortlists[0].id, benefits[0].id}


def test_reassessment_is_idempotent(session, monkeypatch):
    install_stubs(monkeypatch)
    stub_gps(monkeypatch, _fifty_fifty_assessment())
    case = _seed_case(session)
    ehr = FakeEHR()

    pipeline.run_assessment(session, case, ehr)
    first_count = len(_tasks(session, case))
    pipeline.run_assessment(session, case, ehr)

    # Idempotency keys stop duplicate task creation on the second pass.
    assert len(_tasks(session, case)) == first_count
    # And there is still exactly one pending commit-proposal card.
    batches = session.exec(select(Approval).where(
        Approval.case_id == case.id, Approval.kind == "batch", Approval.status == "pending")).all()
    assert len(batches) == 1


# ---------------------------------------------------------------------------
# EHR assessment-posting gate: no dispo_assessments spam
# ---------------------------------------------------------------------------


def _assessment(leader_conf=0.5, leader_id=11, other_conf=0.45, other_id=4):
    a = _fifty_fifty_assessment()
    a.distribution = [PathwayScore(pathway_id=leader_id, confidence=leader_conf),
                      PathwayScore(pathway_id=other_id, confidence=other_conf)]
    return a


def test_same_leader_same_confidence_posts_once(session, monkeypatch):
    install_stubs(monkeypatch)
    stub_gps(monkeypatch, _assessment())
    case = _seed_case(session)
    ehr = FakeEHR()

    pipeline.run_assessment(session, case, ehr)
    assert len(ehr.assessments) == 1  # first assessment always posts
    lp = case.facts["last_posted_assessment"]
    assert lp == {"pathway_id": 11, "confidence": 0.5, "state": "predicted"}

    pipeline.run_assessment(session, case, ehr)
    pipeline.run_assessment(session, case, ehr)
    assert len(ehr.assessments) == 1  # nothing moved — no new EHR rows


def test_small_confidence_drift_does_not_post(session, monkeypatch):
    install_stubs(monkeypatch)
    stub_gps(monkeypatch, _assessment(leader_conf=0.5))
    case = _seed_case(session)
    ehr = FakeEHR()
    pipeline.run_assessment(session, case, ehr)

    stub_gps(monkeypatch, _assessment(leader_conf=0.55))  # +0.05 < 0.10
    pipeline.run_assessment(session, case, ehr)
    assert len(ehr.assessments) == 1
    assert case.facts["last_posted_assessment"]["confidence"] == 0.5  # unchanged


def test_confidence_jump_posts_again(session, monkeypatch):
    install_stubs(monkeypatch)
    stub_gps(monkeypatch, _assessment(leader_conf=0.5))
    case = _seed_case(session)
    ehr = FakeEHR()
    pipeline.run_assessment(session, case, ehr)

    stub_gps(monkeypatch, _assessment(leader_conf=0.65))  # +0.15 >= 0.10
    pipeline.run_assessment(session, case, ehr)
    assert len(ehr.assessments) == 2
    assert case.facts["last_posted_assessment"]["confidence"] == 0.65


def test_leader_change_posts_and_refreshes_commit_card(session, monkeypatch):
    chat_log = install_stubs(monkeypatch)
    stub_gps(monkeypatch, _assessment(leader_conf=0.5, leader_id=11))
    case = _seed_case(session)
    ehr = FakeEHR()
    pipeline.run_assessment(session, case, ehr)
    cards_before = sum(1 for m in chat_log if m["kind"] == "approval_card")

    # Same leader again: the commit card must NOT churn.
    pipeline.run_assessment(session, case, ehr)
    assert sum(1 for m in chat_log if m["kind"] == "approval_card") == cards_before

    # Leader flips to home health: new EHR post AND the card is refreshed once.
    stub_gps(monkeypatch, _assessment(leader_conf=0.6, leader_id=4, other_conf=0.35, other_id=11))
    pipeline.run_assessment(session, case, ehr)
    assert len(ehr.assessments) == 2
    assert ehr.assessments[-1]["predicted_disposition"] == "home_with_services"
    assert case.facts["last_posted_assessment"]["pathway_id"] == 4
    batch = session.exec(select(Approval).where(
        Approval.case_id == case.id, Approval.kind == "batch", Approval.status == "pending")).one()
    assert batch.task_ids["pathway_id"] == 4
    assert sum(1 for m in chat_log if m["kind"] == "approval_card") == cards_before + 1
