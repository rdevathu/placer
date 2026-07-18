"""Ops API: cross-case observability for the Placer engine.

The board endpoints in ``chat.py`` answer "what's happening on this one case";
nothing before this module answered "what is Placer doing right now, across
every case" — the ``Run`` table (one row per brain-loop assessment tick) was
modeled and written by ``brain/loop.py`` but never read back by any endpoint.
This module is read-only and owns no state: it just surfaces Run, and cross-
case rollups of Case/DispoTask/Barrier/Referral, plus a self-contained demo
dashboard at ``/ops/ui`` (same no-build-step style as ``chat.py``'s ``/chat/ui``).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..db import get_session
from ..models import Barrier, Case, DispoTask, Referral, Run

router = APIRouter(tags=["ops"])

_OPEN_BARRIER = {"open", "in_progress", "blocked"}


def _patients_by_case(session: Session, case_ids: set) -> dict:
    if not case_ids:
        return {}
    cases = session.exec(select(Case).where(Case.id.in_(case_ids))).all()
    return {c.id: c.patient_id for c in cases}


def _run_dict(r: Run, patient_by_case: dict) -> dict:
    return {
        "id": r.id,
        "agent": r.agent,
        "case_id": r.case_id,
        "patient_id": patient_by_case.get(r.case_id) if r.case_id else None,
        "trigger": r.trigger,
        "status": r.status,
        "outcome": r.outcome,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }


@router.get(
    "/runs",
    tags=["ops"],
    summary="Audit trail of agent runs",
    description=(
        "One row per brain-loop assessment tick (agent='brain', trigger='dirty') "
        "plus any future agent invocations that adopt the Run contract. This is "
        "the actual 'what has Placer been doing' log — sorted newest first."
    ),
)
def list_runs(
    session: Session = Depends(get_session),
    case_id: Optional[str] = None,
    status: Optional[str] = Query(None, description="running | done | error"),
    agent: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
) -> list[dict]:
    stmt = select(Run)
    if case_id:
        stmt = stmt.where(Run.case_id == case_id)
    if status:
        stmt = stmt.where(Run.status == status)
    if agent:
        stmt = stmt.where(Run.agent == agent)
    rows = session.exec(stmt.order_by(Run.created_at.desc()).offset(offset).limit(limit)).all()
    patient_by_case = _patients_by_case(session, {r.case_id for r in rows if r.case_id})
    return [_run_dict(r, patient_by_case) for r in rows]


@router.get(
    "/ops/overview",
    tags=["ops"],
    summary="Global engine dashboard summary",
    description=(
        "Cross-case rollups (cases by state, tasks by status, open barriers by "
        "readiness dimension, referrals by status) plus the most recent agent "
        "runs — the top-level snapshot for 'what is Placer doing right now'."
    ),
)
def ops_overview(session: Session = Depends(get_session)) -> dict:
    cases = session.exec(select(Case)).all()
    cases_by_state: dict = {}
    for c in cases:
        cases_by_state[c.state] = cases_by_state.get(c.state, 0) + 1

    tasks_by_status: dict = {}
    for t in session.exec(select(DispoTask)).all():
        tasks_by_status[t.status] = tasks_by_status.get(t.status, 0) + 1

    open_barriers_by_dimension: dict = {}
    for b in session.exec(select(Barrier)).all():
        if b.status in _OPEN_BARRIER:
            open_barriers_by_dimension[b.dimension] = open_barriers_by_dimension.get(b.dimension, 0) + 1

    referrals_by_status: dict = {}
    for r in session.exec(select(Referral)).all():
        referrals_by_status[r.status] = referrals_by_status.get(r.status, 0) + 1

    recent_runs = session.exec(select(Run).order_by(Run.created_at.desc()).limit(25)).all()
    patient_by_case = _patients_by_case(session, {r.case_id for r in recent_runs if r.case_id})

    return {
        "total_cases": len(cases),
        "cases_by_state": cases_by_state,
        "tasks_by_status": tasks_by_status,
        "open_barriers_by_dimension": open_barriers_by_dimension,
        "referrals_by_status": referrals_by_status,
        "recent_runs": [_run_dict(r, patient_by_case) for r in recent_runs],
    }


# ---------------------------------------------------------------------------
# Minimal demo UI (single self-contained page — same style as chat.py's
# /chat/ui: no build step, no CDN, dark monospace theme).
# ---------------------------------------------------------------------------


@router.get("/ops/ui", include_in_schema=False)
def ops_ui() -> HTMLResponse:
    return HTMLResponse(content=_UI_HTML)


_UI_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Placer — Ops</title>
<style>
  :root { --bg:#0d1117; --panel:#161b22; --line:#30363d; --fg:#c9d1d9; --dim:#8b949e;
          --green:#3fb950; --amber:#d29922; --red:#f85149; --blue:#58a6ff; }
  * { box-sizing:border-box; margin:0; }
  body { background:var(--bg); color:var(--fg); font:13px/1.45 "SF Mono",Menlo,Consolas,monospace;
         height:100vh; overflow:hidden; display:flex; flex-direction:column; }
  header { display:flex; align-items:center; gap:14px; padding:12px 18px; border-bottom:1px solid var(--line); flex-shrink:0; }
  header h1 { font-size:14px; color:var(--blue); }
  header a { color:var(--dim); font-size:12px; text-decoration:none; }
  header a:hover { color:var(--fg); }
  #stats { display:flex; gap:22px; padding:12px 18px; border-bottom:1px solid var(--line); flex-shrink:0; flex-wrap:wrap; }
  .stat { min-width:100px; }
  .stat .n { font-size:20px; font-weight:bold; }
  .stat .l { color:var(--dim); font-size:11px; text-transform:uppercase; letter-spacing:.04em; }
  #body { flex:1; display:flex; overflow:hidden; }
  #cases { width:46%; overflow-y:auto; border-right:1px solid var(--line); padding:10px 18px; }
  #runs { flex:1; overflow-y:auto; padding:10px 18px; }
  h2 { font-size:12px; color:var(--dim); text-transform:uppercase; letter-spacing:.08em; margin:10px 0 8px; }
  table { width:100%; border-collapse:collapse; }
  td, th { text-align:left; padding:4px 8px 4px 0; border-bottom:1px dashed var(--line); font-size:12px; vertical-align:top; }
  th { color:var(--dim); font-weight:normal; text-transform:uppercase; font-size:10px; }
  .badge { display:inline-block; padding:1px 8px; border-radius:10px; font-size:11px;
           border:1px solid var(--line); text-transform:uppercase; }
  .badge.green { color:var(--green); border-color:var(--green); }
  .badge.committed, .badge.transition, .badge.done, .badge.running { color:var(--blue); border-color:var(--blue); }
  .badge.predicted, .badge.pending, .badge.suggested { color:var(--amber); border-color:var(--amber); }
  .badge.error, .badge.failed { color:var(--red); border-color:var(--red); }
  .dim-row { display:flex; justify-content:space-between; padding:2px 0; font-size:12px; }
  .dim-row .n { color:var(--amber); }
  .empty { color:var(--dim); font-style:italic; padding:8px 0; }
  .outcome { color:var(--dim); font-size:11px; }
</style></head><body>
<header><h1>PLACER — ops</h1><span style="color:var(--dim); font-size:11px">cross-case observability</span>
  <a href="/chat/ui" style="margin-left:auto">chat / board →</a></header>
<div id="stats"></div>
<div id="body">
  <div id="cases"><h2>Cases</h2><table><thead><tr><th>Patient</th><th>State</th><th>Barriers</th><th>Tasks</th></tr></thead>
    <tbody id="caserows"></tbody></table>
    <h2>Open barriers by dimension</h2><div id="dims"></div>
    <h2>Referrals by status</h2><div id="refs"></div></div>
  <div id="runs"><h2>Run log (agent invocations, newest first)</h2><table>
    <thead><tr><th>Started</th><th>Agent</th><th>Patient</th><th>Trigger</th><th>Status</th><th>Outcome</th></tr></thead>
    <tbody id="runrows"></tbody></table></div>
</div>
<script>
const esc = s => (s==null?'':String(s)).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function j(url) { const r = await fetch(url); return r.json(); }
function ago(iso) {
  if (!iso) return '—';
  const s = Math.max(0, Math.round((Date.now() - new Date(iso + 'Z')) / 1000));
  if (s < 60) return s + 's ago';
  if (s < 3600) return Math.round(s/60) + 'm ago';
  return Math.round(s/3600) + 'h ago';
}
async function refresh() {
  const [overview, cases, runs] = await Promise.all([j('/ops/overview'), j('/cases'), j('/runs?limit=50')]);

  document.getElementById('stats').innerHTML = [
    ['Cases', overview.total_cases],
    ...Object.entries(overview.cases_by_state).map(([k,v]) => [k, v]),
  ].map(([l,n]) => `<div class="stat"><div class="n">${n}</div><div class="l">${esc(l)}</div></div>`).join('');

  document.getElementById('caserows').innerHTML = cases.length ? cases.map(c => `
    <tr><td>${esc(c.patient_id)}</td><td><span class="badge ${c.state}">${c.state}</span></td>
      <td>${c.counts.open_barriers}</td><td>${c.counts.open_tasks}</td></tr>`).join('')
    : '<tr><td colspan="4" class="empty">no cases yet</td></tr>';

  document.getElementById('dims').innerHTML = Object.keys(overview.open_barriers_by_dimension).length
    ? Object.entries(overview.open_barriers_by_dimension).map(([d,n]) =>
        `<div class="dim-row"><span>${esc(d.replace('_',' '))}</span><span class="n">${n}</span></div>`).join('')
    : '<div class="empty">none open</div>';

  document.getElementById('refs').innerHTML = Object.keys(overview.referrals_by_status).length
    ? Object.entries(overview.referrals_by_status).map(([s,n]) =>
        `<div class="dim-row"><span>${esc(s)}</span><span class="n">${n}</span></div>`).join('')
    : '<div class="empty">none yet</div>';

  document.getElementById('runrows').innerHTML = runs.length ? runs.map(r => `
    <tr><td>${ago(r.created_at)}</td><td>${esc(r.agent)}</td><td>${esc(r.patient_id || '—')}</td>
      <td>${esc(r.trigger)}</td><td><span class="badge ${r.status}">${r.status}</span></td>
      <td class="outcome">${esc(r.outcome || '')}</td></tr>`).join('')
    : '<tr><td colspan="6" class="empty">no runs yet — the brain loop ticks on dirty cases</td></tr>';
}
refresh();
setInterval(refresh, 3000);
</script></body></html>
"""
