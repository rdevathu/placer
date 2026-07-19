"""Coverage worker: simulated payer benefits verification.

One structured LLM call plays the payer line, grounded in whatever insurance
signal the chart/case carries (there is no insurance table in the dummy EHR, so
plausible-but-honest is the bar). Clears payer barriers only when coverage is
clean; otherwise it sharpens the barrier description so the team knows what is
still needed.
"""

from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from .. import config, llm
from ..models import Barrier, utcnow
from ..registry import load_pathways
from .common import clear_barriers, get_case, get_payload, notify, parked


class BenefitsCheck(BaseModel):
    covered: bool = Field(description="Does the plan cover the requested level(s) of care?")
    network_note: Optional[str] = Field(
        default=None, description="In/out-of-network nuance, e.g. 'in-network SNFs only'."
    )
    auth_required: bool = Field(
        default=False, description="Is prior authorization still required before admission?"
    )
    reference: Optional[str] = Field(
        default=None, description="Call reference number from the payer line."
    )


_PAYER_SYSTEM = (
    "You simulate a payer benefits-verification phone line responding to a "
    "hospital discharge planner. Answer honestly and plausibly for the plan "
    "described; if no plan details are given, assume a typical Medicare/"
    "commercial plan for the patient's age. Do not invent guarantees."
)

_OPEN_STATUSES = ("open", "in_progress", "blocked")


def verify_benefits(session: Session, task, ehr, worker: str) -> dict:
    """payload {pathway_ids}: check coverage for those levels of care; clear
    payer barriers when clean, otherwise annotate them with what's needed."""
    case = get_case(session, task.case_id)
    payload = get_payload(task)
    pathway_ids = payload.get("pathway_ids") or task.pathway_ids or []
    catalog = load_pathways()
    levels = [catalog[p]["name"] for p in pathway_ids if p in catalog] or ["the planned discharge disposition"]

    # Verifying benefits means phoning (or role-playing) the payer line. With
    # calls disabled we must not fabricate a benefits determination: leave the
    # payer barrier open, write nothing, and park pending real payer outreach.
    if not config.PLACE_CALLS:
        return parked("calls_disabled", pathway_ids=list(pathway_ids), levels=levels)

    chart = ehr.get_chart(case.patient_id)
    patient = chart.get("patient") or {}
    insurance = (case.facts or {}).get("insurance") or patient.get("insurance")
    prompt = (
        f"Verify benefits for these levels of care: {', '.join(levels)}.\n"
        f"Patient: {json.dumps({'name': patient.get('name'), 'age': patient.get('age')}, default=str)}\n"
        f"Known insurance: {json.dumps(insurance, default=str) if insurance else 'not documented — assume a plausible plan'}\n"
        "Report coverage, network nuance, whether prior auth is required, and a call reference."
    )
    check = llm.structured(prompt, BenefitsCheck, system=_PAYER_SYSTEM)

    barriers_cleared = 0
    if check.covered and not check.auth_required:
        barriers_cleared = clear_barriers(
            session, case.id, "payer", pathway_ids=list(pathway_ids) or None
        )
        note = f"{worker}: benefits verified — covered" + (
            f" ({check.network_note})" if check.network_note else ""
        )
    else:
        needed = "prior authorization required" if check.covered else "not covered as requested"
        description = f"Payer check: {needed}" + (
            f"; {check.network_note}" if check.network_note else ""
        )
        open_payer = [
            b
            for b in session.exec(
                select(Barrier).where(
                    Barrier.case_id == case.id,
                    Barrier.dimension == "payer",
                    Barrier.status.in_(_OPEN_STATUSES),  # type: ignore[attr-defined]
                )
            ).all()
            if not b.pathway_ids or not pathway_ids or set(b.pathway_ids) & set(pathway_ids)
        ]
        if open_payer:
            for barrier in open_payer:
                barrier.description = description
                barrier.updated_at = utcnow()
                session.add(barrier)
        else:
            session.add(
                Barrier(
                    case_id=case.id,
                    pathway_ids=list(pathway_ids) or None,
                    dimension="payer",
                    btype="auth_pending" if check.covered else "not_covered",
                    status="open",
                    description=description,
                )
            )
        note = f"{worker}: payer check — {needed}"
    case.dirty = True
    session.add(case)

    ehr.create_communication(
        patient_id=case.patient_id,
        summary=f"Benefits verification for {', '.join(levels)}: "
        + ("covered" if check.covered else "not covered")
        + (", auth required" if check.auth_required else ""),
        party_type="insurance",
        party_name="Payer benefits line",
        outcome=check.reference or ("verified" if check.covered else "denied"),
    )
    notify(session, case.id, note)
    return {
        "covered": check.covered,
        "auth_required": check.auth_required,
        "network_note": check.network_note,
        "reference": check.reference,
        "barriers_cleared": barriers_cleared,
    }
