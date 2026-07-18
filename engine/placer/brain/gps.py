"""The Discharge GPS: one structured LLM call per assessment.

Context assembly happens in code — chart snapshot, case memory, open work — and
the model answers once with a full GpsAssessment. No tool loop: the EHR chart
endpoint already aggregates everything an assessor needs, and a single call
keeps latency and cost bounded per reassessment.
"""

from __future__ import annotations

import json

from sqlmodel import Session, select

from placer import llm
from placer.ehr_client import EHRClient
from placer.models import Barrier, Case, DispoTask, Referral
from placer.registry import load_pathways

from .schemas import GpsAssessment

_OPEN_BARRIER_STATUSES = ("open", "in_progress", "blocked")
_OPEN_TASK_STATUSES = ("suggested", "pending", "approved", "in_progress", "waiting")

SYSTEM_PROMPT = (
    "You are Placer's Discharge GPS: an expert discharge planner assessing a "
    "hospitalized patient's most likely discharge pathway.\n"
    "- Score ALL 25 pathways in the registry, but only include pathways with "
    "confidence >= 0.05 in `distribution`; confidences must sum to <= 1.0.\n"
    "- Maintain the barrier list across the 7 readiness dimensions: medical | "
    "clinical_docs | decision | payer | destination | home_logistics | "
    "transport. Emit `upsert` ops for new/changed barriers and `clear` ops for "
    "resolved ones, keyed by (dimension, btype).\n"
    "- Prefer these canonical btype values so work routes correctly: "
    "medical_clearance, family_decision, consult_needed (name the specialty in "
    "description), pending_lab (name the test in description), insurance_auth, "
    "bed_availability, home_safety, transport_needed. Use a descriptive "
    "snake_case btype only when none fits.\n"
    "- Medical and decision barriers always exist until explicitly cleared by "
    "humans — NEVER emit clear ops for those dimensions yourself.\n"
    "- Cite chart evidence (note text, lab values, orders) in barrier "
    "`evidence` and in `rationale`.\n"
    "- `brief` is an updated ~10-sentence case brief carrying forward what "
    "still matters from the prior brief plus what changed.\n"
    "- Be concise."
)


def _dump(obj: object) -> str:
    return json.dumps(obj, indent=1, default=str)


# How much of each note body to feed the model. Recent notes carry the freshest
# functional-status and goals-of-care signal (the chart snapshot has no notes at
# all), but full H&Ps are long — cap per-note so the prompt stays bounded.
_RECENT_NOTES = 6
_NOTE_TEXT_CAP = 2000
_RECENT_LABS = 15


def _recent_notes(ehr: EHRClient, patient_id: str) -> list:
    """The most recent note bodies, newest first, each truncated. The chart
    aggregate omits notes entirely, so without this GPS never sees a new
    clinician note (e.g. one documenting the patient is now safe for home)."""
    try:
        notes = ehr.list_notes(patient_id)[:_RECENT_NOTES]
    except Exception:  # a notes-endpoint hiccup must not abort the assessment
        return []
    out = []
    for n in notes:
        text = n.get("text") or ""
        if len(text) > _NOTE_TEXT_CAP:
            text = text[:_NOTE_TEXT_CAP] + "… [truncated]"
        out.append({
            "note_type": n.get("note_type"), "title": n.get("title"),
            "author_role": n.get("author_role"), "status": n.get("status"),
            "created_at": n.get("created_at"), "text": text,
        })
    return out


def _recent_labs(ehr: EHRClient, patient_id: str) -> list:
    """Recent lab results, newest first — including *normal* ones. The chart
    snapshot only carries pending + abnormal labs, so a normal resulted lab
    (which can clear a pending-lab barrier) would otherwise be invisible."""
    try:
        labs = ehr.list_labs(patient_id)[:_RECENT_LABS]
    except Exception:  # degrade gracefully; the chart still carries abnormal labs
        return []
    return [
        {"display": l.get("display"), "value_num": l.get("value_num"),
         "value_unit": l.get("value_unit"), "value_string": l.get("value_string"),
         "status": l.get("status"), "abnormal_flag": l.get("abnormal_flag"),
         "effective_time": l.get("effective_time")}
        for l in labs
    ]


def assess(session: Session, case: Case, ehr: EHRClient) -> GpsAssessment:
    """Assemble full case context and run one structured GPS call."""
    chart = ehr.get_chart(case.patient_id)
    notes = _recent_notes(ehr, case.patient_id)
    labs = _recent_labs(ehr, case.patient_id)

    barriers = session.exec(
        select(Barrier).where(Barrier.case_id == case.id, Barrier.status.in_(_OPEN_BARRIER_STATUSES))  # type: ignore[attr-defined]
    ).all()
    tasks = session.exec(
        select(DispoTask).where(DispoTask.case_id == case.id, DispoTask.status.in_(_OPEN_TASK_STATUSES))  # type: ignore[attr-defined]
    ).all()
    referrals = session.exec(select(Referral).where(Referral.case_id == case.id)).all()

    pathway_lines = [
        f"  {p['id']}: {p['name']} (wired={p.get('wired', False)})"
        for p in sorted(load_pathways().values(), key=lambda p: p["id"])
    ]

    prompt = "\n".join([
        "## Pathway registry (score all of these)",
        "\n".join(pathway_lines),
        "",
        "## Chart snapshot",
        _dump(chart),
        "",
        "## Recent notes (newest first — read for functional status, goals of care, disposition intent)",
        _dump(notes),
        "",
        "## Recent lab results (newest first — includes normal results)",
        _dump(labs),
        "",
        "## Prior case brief",
        case.brief or "(first assessment — no prior brief)",
        "",
        "## Structured facts",
        _dump(case.facts or {}),
        "",
        "## Open barriers",
        _dump([
            {"dimension": b.dimension, "btype": b.btype, "status": b.status,
             "description": b.description, "pathway_ids": b.pathway_ids}
            for b in barriers
        ]),
        "",
        "## Open / suggested tasks",
        _dump([
            {"task_type": t.task_type, "status": t.status, "title": t.title,
             "pathway_ids": t.pathway_ids}
            for t in tasks
        ]),
        "",
        "## Referral statuses",
        _dump([
            {"facility": r.facility_name, "pathway_id": r.pathway_id,
             "status": r.status, "denial_reason": r.denial_reason}
            for r in referrals
        ]),
        "",
        "Produce the updated GpsAssessment.",
    ])

    return llm.structured(prompt, GpsAssessment, system=SYSTEM_PROMPT)
