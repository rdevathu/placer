"""Brain actions: commit-time pruning (trump) and the green-derivation path."""

from __future__ import annotations

from sqlmodel import select

from placer.brain import actions, pipeline
from placer.brain.schemas import GpsAssessment, PathwayScore
from placer.models import Approval, Barrier, Case, DispoTask, Referral

from test_brain_helpers import FakeEHR, install_stubs, stub_gps


def _predicted_case(session):
    case = Case(
        patient_id="p1", encounter_id="e1", state="predicted",
        active_pathways=[{"pathway_id": 11, "confidence": 0.5},
                         {"pathway_id": 4, "confidence": 0.45}],
    )
    session.add(case)
    session.commit()
    return case


def test_commit_pathway_prunes_exclusive_keeps_shared(session, monkeypatch):
    chat_log = install_stubs(monkeypatch)
    case = _predicted_case(session)

    snf_task = DispoTask(case_id=case.id, task_type="build_shortlist", mode="auto",
                         status="pending", pathway_ids=[11], title="SNF shortlist",
                         idempotency_key=f"{case.id}:build_shortlist:11")
    home_task = DispoTask(case_id=case.id, task_type="draft_consult", mode="auto",
                          status="pending", pathway_ids=[4], title="PT/OT eval",
                          idempotency_key=f"{case.id}:draft_consult:pt-ot")
    shared_task = DispoTask(case_id=case.id, task_type="preference_call", mode="approval",
                            status="suggested", pathway_ids=None, title="Family call",
                            idempotency_key=f"{case.id}:preference_call:-")
    session.add(snf_task); session.add(home_task); session.add(shared_task)

    snf_ref = Referral(case_id=case.id, pathway_id=11, facility_id="f1",
                       facility_name="Oak Grove SNF", status="shortlisted")
    session.add(snf_ref)

    session.add(Barrier(case_id=case.id, dimension="decision", btype="family_decision",
                        description="Preference unknown"))
    session.add(Barrier(case_id=case.id, dimension="destination", btype="bed_availability",
                        description="No bed yet", pathway_ids=[11]))
    home_barrier = Barrier(case_id=case.id, dimension="home_logistics", btype="dme_setup",
                           description="Hospital bed at home", pathway_ids=[4])
    session.add(home_barrier)
    batch = Approval(case_id=case.id, kind="batch", status="pending",
                     task_ids={"pathway_id": 11, "task_ids": [snf_task.id]})
    session.add(batch)
    session.commit()

    result = actions.commit_pathway(session, case.id, 11, resolved_by="team:dr-lee")

    assert result["state"] == "committed"
    assert case.state == "committed" and case.dirty is True
    assert case.active_pathways == [{"pathway_id": 11, "confidence": 1.0}]

    # Pathway-exclusive home work cancelled; SNF + shared kept.
    session.refresh(home_task); session.refresh(snf_task); session.refresh(shared_task)
    assert home_task.status == "cancelled"
    assert home_task.id in result["cancelled"]
    assert snf_task.status == "pending"
    assert snf_task.id in result["kept"]
    # Kept approval-mode work is auto-approved by the committing batch card.
    assert shared_task.status == "approved"

    # Losing-pathway barrier closed with a trump note; decision barrier cleared.
    session.refresh(home_barrier)
    assert home_barrier.status == "cleared"
    decision = session.exec(select(Barrier).where(
        Barrier.case_id == case.id, Barrier.dimension == "decision")).one()
    assert decision.status == "cleared"

    # Referral for the winning pathway untouched; batch card resolved.
    session.refresh(snf_ref)
    assert snf_ref.status == "shortlisted" and not (snf_ref.notes or "")
    session.refresh(batch)
    assert batch.status == "approved" and batch.resolved_by == "team:dr-lee"

    # Post-commit rebuild: intake call for the shortlisted referral is created
    # directly as 'approved' (no new suggested gate).
    intake = session.exec(select(DispoTask).where(
        DispoTask.case_id == case.id, DispoTask.task_type == "facility_intake_call")).one()
    assert intake.status == "approved"
    assert intake.id in result["created"]

    assert any(m["kind"] == "notification" for m in chat_log)


def test_commit_referral_on_losing_pathway_gets_stand_down_note(session, monkeypatch):
    install_stubs(monkeypatch)
    case = _predicted_case(session)
    irf_ref = Referral(case_id=case.id, pathway_id=12, facility_id="f9",
                       facility_name="Valley IRF", status="intake_verified")
    session.add(irf_ref)
    session.commit()

    actions.commit_pathway(session, case.id, 11, resolved_by="team:cm")

    session.refresh(irf_ref)
    assert irf_ref.status == "intake_verified"  # status vocabulary unchanged
    assert "Cancelled on commit to pathway 11" in irf_ref.notes


def test_green_derivation_after_commit(session, monkeypatch):
    chat_log = install_stubs(monkeypatch)
    stub_gps(monkeypatch, GpsAssessment(
        distribution=[PathwayScore(pathway_id=11, confidence=0.92)],
        rationale="All barriers resolved; SNF bed accepted.",
        review_horizon="imminent",
        brief="Ready for SNF discharge.",
        barriers=[],
    ))
    case = Case(patient_id="p1", state="committed",
                active_pathways=[{"pathway_id": 11, "confidence": 1.0}])
    session.add(case)
    # Every dimension clear; medical + decision have explicitly-cleared barriers.
    session.add(Barrier(case_id=case.id, dimension="medical", btype="medical_clearance",
                        status="cleared"))
    session.add(Barrier(case_id=case.id, dimension="decision", btype="family_decision",
                        status="cleared"))
    session.commit()

    pipeline.run_assessment(session, case, FakeEHR())

    assert case.state == "green"
    assert any("\U0001F7E2" in m["content"] and m["kind"] == "notification" for m in chat_log)


def test_approve_and_reject(session, monkeypatch):
    install_stubs(monkeypatch)
    case = _predicted_case(session)
    t1 = DispoTask(case_id=case.id, task_type="preference_call", mode="approval",
                   status="suggested", title="Family call",
                   idempotency_key=f"{case.id}:preference_call:-")
    t2 = DispoTask(case_id=case.id, task_type="facility_intake_call", mode="approval",
                   status="suggested", title="Call Oak Grove",
                   idempotency_key=f"{case.id}:facility_intake_call:f1")
    session.add(t1); session.add(t2)
    session.commit()

    out = actions.approve_tasks(session, [t1.id], resolved_by="team:cm")
    assert out["approved"] == [t1.id]
    session.refresh(t1)
    assert t1.status == "approved" and case.dirty is True

    approval = Approval(case_id=case.id, kind="suggested", task_ids=[t2.id])
    session.add(approval)
    session.commit()
    out = actions.reject_approval(session, approval.id, resolved_by="team:cm")
    session.refresh(t2); session.refresh(approval)
    assert approval.status == "rejected"
    assert t2.status == "cancelled" and out["cancelled"] == [t2.id]

    actions.reassess_case(session, case.id)
    assert case.dirty is True
