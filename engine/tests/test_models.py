"""Smoke tests: every table round-trips a row; key constraints hold."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from placer.db import engine
from placer.models import (
    Approval,
    Barrier,
    Case,
    ChatMessage,
    DispoTask,
    FacilityIntel,
    Referral,
    Run,
)


def test_create_one_of_each(session: Session):
    case = Case(
        patient_id="hero-a-stroke",
        encounter_id="enc-1",
        state="predicted",
        brief="72M with L MCA stroke, likely IRF vs SNF.",
        facts={"insurance": "Medicare"},
        active_pathways=[{"pathway_id": 12, "confidence": 0.6}],
        dirty=True,
    )
    session.add(case)
    session.commit()

    session.add(Barrier(
        case_id=case.id,
        pathway_ids=[12],
        dimension="clinical_docs",
        btype="pmr_eval_missing",
        status="open",
        description="No PM&R evaluation on chart",
    ))
    session.add(DispoTask(
        case_id=case.id,
        action_id="FPR-004",
        task_type="draft_consult",
        mode="approval",
        channel="ehr_order",
        status="suggested",
        pathway_ids=[12],
        idempotency_key="case1:FPR-004:pmr",
        title="Draft PM&R consult order",
    ))
    session.add(Referral(
        case_id=case.id,
        pathway_id=12,
        facility_id="fac-1",
        facility_name="Valley Acute Rehab",
        status="shortlisted",
    ))
    session.add(Approval(
        case_id=case.id,
        kind="per_action",
        task_ids=["t-1"],
        prompt="OK to draft the PM&R consult?",
    ))
    session.add(ChatMessage(
        case_id=case.id,
        author="placer",
        kind="text",
        content="Started working the IRF pathway.",
    ))
    session.add(Run(
        agent="reviewer",
        case_id=case.id,
        trigger="event:note.created",
        status="done",
        log=[{"step": "read_chart"}],
        outcome="Confidence updated.",
    ))
    session.add(FacilityIntel(
        facility_id="fac-1",
        beds_available=2,
        decline_history=[{"case_id": "x", "reason": "vent"}],
    ))
    session.commit()

    # Round-trip: one row per table, JSON columns intact.
    fetched = session.exec(select(Case)).one()
    assert fetched.active_pathways == [{"pathway_id": 12, "confidence": 0.6}]
    assert session.exec(select(Barrier)).one().pathway_ids == [12]
    assert session.exec(select(DispoTask)).one().idempotency_key == "case1:FPR-004:pmr"
    assert session.exec(select(Referral)).one().status == "shortlisted"
    assert session.exec(select(Approval)).one().status == "pending"
    assert session.exec(select(ChatMessage)).one().author == "placer"
    assert session.exec(select(Run)).one().log == [{"step": "read_chart"}]
    assert session.exec(select(FacilityIntel)).one().beds_available == 2


def test_idempotency_key_unique(fresh_db):
    with Session(engine) as s:
        s.add(DispoTask(case_id="c1", task_type="call_snf", title="Call A", idempotency_key="dup"))
        s.commit()
    with Session(engine) as s:
        s.add(DispoTask(case_id="c1", task_type="call_snf", title="Call B", idempotency_key="dup"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_facility_intel_unique_facility(fresh_db):
    with Session(engine) as s:
        s.add(FacilityIntel(facility_id="fac-9"))
        s.commit()
    with Session(engine) as s:
        s.add(FacilityIntel(facility_id="fac-9"))
        with pytest.raises(IntegrityError):
            s.commit()
