"""Clinical Prep worker: chart audits and pended (draft) orders/consults.

Drafts are the human-visible mirror of agent intent — the agent proposes, a
clinician signs. Nothing here ever signs an order.
"""

from __future__ import annotations

import json
import re
from typing import List, Optional

from pydantic import BaseModel, Field
from sqlmodel import Session

from .. import llm
from .common import get_case, get_payload, notify


class ChartAuditFinding(BaseModel):
    title: str = Field(description="Short name of the gap, e.g. 'No PM&R consult on file'")
    detail: str = Field(description="What is missing and why it blocks discharge planning")


class ChartAuditReport(BaseModel):
    findings: List[ChartAuditFinding] = Field(
        description="Missing documentation/orders relevant to disposition; empty if the chart is complete."
    )


_AUDIT_SYSTEM = (
    "You are a hospital discharge-planning documentation auditor. Given a chart "
    "snapshot, list ONLY concrete missing items that block disposition work "
    "(missing consults, unsigned therapy evals, absent code status, pending "
    "labs required for facility acceptance, missing goals-of-care note...). "
    "Be specific and cite what in the chart makes each item necessary. If "
    "nothing is missing, return an empty list."
)


def chart_audit(session: Session, task, ehr, worker: str) -> dict:
    """LLM pass over the chart aggregate; findings land in task.result and,
    when non-empty, a one-line chat note."""
    case = get_case(session, task.case_id)
    chart = ehr.get_chart(case.patient_id)
    prompt = (
        "Audit this chart snapshot for documentation gaps that block discharge "
        "disposition planning.\n\n"
        f"Chart:\n{json.dumps(chart, default=str)[:8000]}"
    )
    report = llm.structured(prompt, ChartAuditReport, system=_AUDIT_SYSTEM)
    findings = [f.model_dump() for f in report.findings]
    if findings:
        headline = "; ".join(f["title"] for f in findings[:3])
        notify(session, case.id, f"{worker}: chart audit found {len(findings)} gap(s) — {headline}")
    return {"findings": findings}


# Order-dedupe tokenization: generic filler words never count as a match, and
# the COVID family ('SARS-CoV-2', 'COVID-19', 'PCR', 'NAA'...) collapses to one
# token class so an intended 'COVID PCR' matches an existing
# 'SARS-CoV-2 (COVID-19) NAA test'.
_ORDER_STOPWORDS = {
    "test", "tests", "testing", "lab", "labs", "pending", "required", "panel",
    "order", "orders", "the", "and", "for", "with", "eval", "evaluation",
    "screen", "screening",
}
_COVID_SYNONYMS = {"covid", "covid19", "sars", "cov", "cov2", "pcr", "naa", "naat", "coronavirus"}

# Existing orders in these states cover the same clinical intent — do not
# duplicate. Completed/cancelled orders don't block a re-order.
_LIVE_ORDER_STATUSES = {"draft", "signed"}


def _order_tokens(text: Optional[str]) -> set:
    lowered = (text or "").lower()
    # Two passes: alnum runs ('sars', 'cov') plus whole words compacted
    # ('pm&r' -> 'pmr') so punctuated abbreviations still match.
    candidates = re.split(r"[^a-z0-9]+", lowered)
    candidates += [re.sub(r"[^a-z0-9]", "", w) for w in lowered.split()]
    tokens = set()
    for raw in candidates:
        if len(raw) < 3 or raw in _ORDER_STOPWORDS:
            continue
        tokens.add("covid" if raw in _COVID_SYNONYMS else raw)
    return tokens


def _find_existing_order(ehr, patient_id: str, order_type: str, display: str) -> Optional[dict]:
    """A live (draft/signed) order of the same type sharing a meaningful token
    with the intended display, or None."""
    intended = _order_tokens(display)
    if not intended:
        return None
    for order in ehr.list_orders(patient_id):
        if order.get("status") not in _LIVE_ORDER_STATUSES:
            continue
        if order.get("order_type") != order_type:
            continue
        if intended & _order_tokens(order.get("display")):
            return order
    return None


def _draft(session: Session, task, ehr, worker: str, forced_order_type=None) -> dict:
    case = get_case(session, task.case_id)
    payload = get_payload(task)
    order_type = forced_order_type or payload.get("order_type")
    if not order_type:
        raise ValueError(f"draft_order task {task.id} needs payload.order_type")
    display = payload.get("display") or task.title

    existing = _find_existing_order(ehr, case.patient_id, order_type, display)
    if existing is not None:
        status = existing.get("status", "draft")
        pending = " (signed, pending result)" if status == "signed" else f" ({status})"
        notify(
            session, case.id,
            f"{worker}: '{existing.get('display', display)}' already ordered{pending} "
            "— tracking the existing order instead of reordering",
        )
        return {
            "order_id": existing.get("id"),
            "status": status,
            "display": existing.get("display", display),
            "deduped": True,
        }

    order = ehr.create_order(
        patient_id=case.patient_id,
        encounter_id=case.encounter_id,
        order_type=order_type,
        display=display,
        detail=payload.get("detail") or task.detail,
        status="draft",
    )
    notify(session, case.id, f"{worker}: pended {order_type} order '{display}' for signature")
    return {"order_id": order.get("id"), "status": order.get("status", "draft"), "display": display}


def draft_order(session: Session, task, ehr, worker: str) -> dict:
    """Create a draft (pended) EHR order from payload {order_type, display, detail}."""
    return _draft(session, task, ehr, worker)


def draft_consult(session: Session, task, ehr, worker: str) -> dict:
    """Draft order with order_type forced to 'consult' (e.g. PM&R for IRF)."""
    return _draft(session, task, ehr, worker, forced_order_type="consult")
