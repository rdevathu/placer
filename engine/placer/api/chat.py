"""Chat + readiness-board API: the team-facing surface of the engine.

Owns three things:
1. ``post_message`` — the ONE function brain/workers use to put anything in
   chat (adds to the session, never commits; committing is the caller's job).
2. The chat/approval/commit endpoints the demo UI drives.
3. The board read endpoints (``/cases``, ``/cases/{id}/board``) and a minimal
   self-contained demo UI at ``/chat/ui``.

Brain functions (``placer.brain.actions``) are imported lazily inside endpoint
bodies — the brain package lands in parallel and tests monkeypatch it via
``sys.modules``.
"""

from __future__ import annotations

import importlib
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

try:  # Python 3.9: Literal lives in typing
    from typing import Literal
except ImportError:  # pragma: no cover
    from typing_extensions import Literal

from sqlmodel import Session, select

from .. import llm
from ..db import get_session
from ..models import (
    Approval,
    Barrier,
    Case,
    ChatMessage,
    DispoTask,
    Referral,
    utcnow,
)
from ..registry import load_pathways
from ..state import READINESS_DIMENSIONS, derive_readiness

router = APIRouter(tags=["chat"])

logger = logging.getLogger(__name__)

# Chat kinds worth showing in the Iliad Placer tab (rich board kinds are not).
_MIRRORABLE_KINDS = {"text", "notification", "approval_card"}


# ---------------------------------------------------------------------------
# Contract helper (imported by brain/workers — see INTERFACES.md)
# ---------------------------------------------------------------------------


def post_message(
    session: Session,
    content: str,
    *,
    case_id: Optional[str] = None,
    kind: str = "text",
    author: str = "placer",
    approval_id: Optional[str] = None,
) -> ChatMessage:
    """Append one chat message. Adds to the session but does NOT commit —
    commits are the caller's responsibility (frozen interface contract)."""
    msg = ChatMessage(
        case_id=case_id,
        author=author,
        kind=kind,
        content=content,
        approval_id=approval_id,
    )
    session.add(msg)
    _mirror_to_ehr(session, msg)
    return msg


def _mirror_to_ehr(session: Session, msg: ChatMessage) -> None:
    """Best-effort mirror of Placer-authored chat into the Iliad Placer tab.

    Only placer-authored kinds in _MIRRORABLE_KINDS go out; team-authored
    messages (author 'team:*', including provider messages the loop mirrored IN
    from Iliad) are never bounced back — that would loop. Never raises."""
    from placer import config

    if not config.PLACER_MIRROR:
        return
    if msg.case_id is None or not msg.content or msg.kind not in _MIRRORABLE_KINDS:
        return
    if not (msg.author or "").startswith("placer"):
        return
    try:
        case = session.get(Case, msg.case_id)
        if case is None or not case.patient_id:
            return
        from placer.ehr_client import EHRClient

        client = EHRClient()
        try:
            client.create_placer_message(case.patient_id, msg.content)
        finally:
            client.close()
    except Exception:
        logger.warning("chat: EHR placer-message mirror failed", exc_info=True)


def _actions():
    """Lazy import of the brain's action seam; monkeypatched in tests."""
    return importlib.import_module("placer.brain.actions")


# ---------------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------------


class IntakeParse(BaseModel):
    """LLM classification of an inbound team message."""

    kind: Literal["answer", "info", "instruction", "question"]
    summary: str


class MessageIn(BaseModel):
    content: str
    case_id: Optional[str] = None
    author: str = "team:cm"


class ResolveIn(BaseModel):
    resolved_by: str


class CommitIn(BaseModel):
    pathway_id: int
    resolved_by: str


def _msg_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "case_id": m.case_id,
        "author": m.author,
        "kind": m.kind,
        "content": m.content,
        "approval_id": m.approval_id,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------


@router.get("/chat/messages", summary="List chat messages (oldest first)")
def list_messages(
    case_id: Optional[str] = None,
    since_id: Optional[str] = None,
    limit: int = 100,
    session: Session = Depends(get_session),
) -> list:
    """Lean message dicts in chronological order. ``case_id`` absent returns
    ALL threads together (general + every case; each dict carries case_id).
    ``since_id`` returns only messages after that message (for polling)."""
    stmt = select(ChatMessage)
    if case_id is not None:
        stmt = stmt.where(ChatMessage.case_id == case_id)
    if since_id is not None:
        ref = session.get(ChatMessage, since_id)
        if ref is not None:
            # ids are uuids, so "after" means after the ref's timestamp
            # (tie-broken by id for same-instant inserts).
            stmt = stmt.where(
                (ChatMessage.created_at > ref.created_at)
                | (
                    (ChatMessage.created_at == ref.created_at)
                    & (ChatMessage.id > ref.id)
                )
            )
    stmt = stmt.order_by(ChatMessage.created_at, ChatMessage.id).limit(limit)
    return [_msg_dict(m) for m in session.exec(stmt).all()]


@router.post(
    "/chat/messages",
    summary="Post a team message (runs Intake classification)",
    description=(
        "Stores the message, then classifies it with one LLM call as "
        "answer | info | instruction | question. info/answer append to the "
        "case's team_notes facts and mark the case for reassessment; "
        "instruction additionally creates a pending message_team DispoTask; "
        "question gets an acknowledgement reply. LLM failure degrades to "
        "'info'. Returns the stored message plus the parse."
    ),
)
def create_message(body: MessageIn, session: Session = Depends(get_session)) -> dict:
    case: Optional[Case] = None
    if body.case_id is not None:
        case = session.get(Case, body.case_id)
        if case is None:
            raise HTTPException(status_code=404, detail=f"Unknown case '{body.case_id}'")

    msg = post_message(
        session, body.content, case_id=body.case_id, author=body.author
    )

    # Intake: one structured call; any failure degrades to plain "info".
    try:
        parse = llm.structured(
            "A care-team member posted this message in the discharge-planning "
            "chat. Classify it.\n\n"
            f"Author: {body.author}\nMessage: {body.content}\n\n"
            "kind meanings — answer: answers a question Placer asked earlier; "
            "info: shares information about the patient or case; instruction: "
            "asks Placer (or the team) to do something; question: asks Placer "
            "a question. summary: one short line restating the message.",
            IntakeParse,
            system="You are the intake classifier for Placer, a discharge-planning agent.",
        )
        kind, summary = parse.kind, parse.summary
    except Exception:
        kind, summary = "info", body.content[:120]

    if case is not None:
        if kind in ("info", "answer", "instruction"):
            # JSON columns don't track in-place mutation — rebuild the dict.
            facts = dict(case.facts or {})
            notes = list(facts.get("team_notes") or [])
            notes.append(
                {
                    "ts": utcnow().isoformat(),
                    "author": body.author,
                    "content": body.content,
                }
            )
            facts["team_notes"] = notes
            case.facts = facts
            case.updated_at = utcnow()
            session.add(case)

        if kind == "instruction":
            payload = {"question": body.content}
            task_kwargs = dict(
                case_id=case.id,
                task_type="message_team",
                mode="auto",
                status="pending",
                title=f"Team instruction: {summary}",
                # Keyed on the message id so repeated instructions never collide.
                idempotency_key=f"{case.id}:message_team:{msg.id}",
            )
            # models.py is frozen without a payload column in this wave; carry
            # the payload there if it exists, else in `detail` as JSON.
            if "payload" in getattr(DispoTask, "model_fields", {}):
                task_kwargs["payload"] = payload
            else:
                task_kwargs["detail"] = json.dumps(payload)
            session.add(DispoTask(**task_kwargs))

        if kind == "question":
            post_message(
                session,
                "On it — I'll look into this and report back.",
                case_id=case.id,
            )

        _actions().reassess_case(session, case.id)

    session.commit()
    session.refresh(msg)
    return {"message": _msg_dict(msg), "parse": {"kind": kind, "summary": summary}}


# ---------------------------------------------------------------------------
# Approval endpoints
# ---------------------------------------------------------------------------


def _load_pending_approval(session: Session, approval_id: str) -> Approval:
    approval = session.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail=f"Unknown approval '{approval_id}'")
    if approval.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Approval '{approval_id}' is '{approval.status}', not pending; "
                "only pending approvals can be resolved"
            ),
        )
    return approval


def _batch_pathway_id(approval: Approval, session: Session) -> int:
    """The brain stores {'pathway_id': X, 'task_ids': [...]} in the batch
    approval's task_ids JSON; older shapes may be a bare list. Handle both."""
    shape = approval.task_ids
    if isinstance(shape, dict) and shape.get("pathway_id") is not None:
        return int(shape["pathway_id"])
    # Bare-list shape: fall back to the case's leading active pathway.
    case = session.get(Case, approval.case_id)
    active = (case.active_pathways or []) if case is not None else []
    if active:
        return int(active[0]["pathway_id"])
    raise HTTPException(
        status_code=409,
        detail=f"Batch approval '{approval.id}' names no pathway and the case has no active pathways",
    )


@router.post(
    "/chat/approvals/{approval_id}/approve",
    summary="Approve an approval card",
    description=(
        "kind='suggested' approves its linked tasks; kind='batch' commits the "
        "pathway the card proposes. 409 if the approval is not pending."
    ),
)
def approve_approval(
    approval_id: str, body: ResolveIn, session: Session = Depends(get_session)
) -> dict:
    approval = _load_pending_approval(session, approval_id)
    actions = _actions()

    if approval.kind == "batch":
        pathway_id = _batch_pathway_id(approval, session)
        try:
            result = actions.commit_pathway(
                session, approval.case_id, pathway_id, body.resolved_by
            )
        except ValueError as exc:  # IllegalTransition et al.
            raise HTTPException(status_code=409, detail=str(exc))
    else:  # suggested / per_action: approve the linked tasks
        shape = approval.task_ids
        task_ids = shape.get("task_ids", []) if isinstance(shape, dict) else list(shape or [])
        result = actions.approve_tasks(session, task_ids, body.resolved_by)

    approval.status = "approved"
    approval.resolved_by = body.resolved_by
    approval.resolved_at = utcnow()
    session.add(approval)
    session.commit()
    return {"approval_id": approval.id, "status": "approved", "result": result}


@router.post("/chat/approvals/{approval_id}/reject", summary="Reject an approval card")
def reject_approval(
    approval_id: str, body: ResolveIn, session: Session = Depends(get_session)
) -> dict:
    _load_pending_approval(session, approval_id)
    result = _actions().reject_approval(session, approval_id, body.resolved_by)
    session.commit()
    return {"approval_id": approval_id, "status": "rejected", "result": result}


# ---------------------------------------------------------------------------
# Commit (the team decision endpoint)
# ---------------------------------------------------------------------------


@router.post(
    "/cases/{case_id}/commit",
    summary="Commit the case to one pathway (team decision)",
    description=(
        "Applies the 'commit' transition via the brain, prunes losing-pathway "
        "work, and resolves any pending batch approval cards for the case. "
        "409 on an illegal state transition."
    ),
)
def commit_case(
    case_id: str, body: CommitIn, session: Session = Depends(get_session)
) -> dict:
    if session.get(Case, case_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown case '{case_id}'")
    try:
        result = _actions().commit_pathway(
            session, case_id, body.pathway_id, body.resolved_by
        )
    except ValueError as exc:  # state.IllegalTransition subclasses ValueError
        raise HTTPException(status_code=409, detail=str(exc))

    # The batch card was informational; this decision resolves it.
    pending_batches = session.exec(
        select(Approval).where(
            Approval.case_id == case_id,
            Approval.kind == "batch",
            Approval.status == "pending",
        )
    ).all()
    for approval in pending_batches:
        approval.status = "approved"
        approval.resolved_by = body.resolved_by
        approval.resolved_at = utcnow()
        session.add(approval)

    session.commit()
    return {"case_id": case_id, "pathway_id": body.pathway_id, "result": result}


# ---------------------------------------------------------------------------
# Board endpoints
# ---------------------------------------------------------------------------

_OPEN_BARRIER = {"open", "in_progress", "blocked"}
_OPEN_TASK = {"suggested", "pending", "approved", "in_progress", "waiting"}
_TASK_GROUPS = [
    "suggested",
    "pending",
    "approved",
    "in_progress",
    "waiting",
    "done",
    "failed",
    "cancelled",
]


def _named_pathways(active: Optional[list]) -> list:
    catalog = load_pathways()
    out = []
    for entry in active or []:
        pid = entry.get("pathway_id")
        info = catalog.get(pid, {})
        out.append(
            {
                "pathway_id": pid,
                "confidence": entry.get("confidence"),
                "name": info.get("name", f"Pathway {pid}"),
            }
        )
    return out


@router.get("/cases", tags=["board"], summary="List all cases with rollup counts")
def list_cases(session: Session = Depends(get_session)) -> list:
    cases = session.exec(select(Case).order_by(Case.created_at)).all()
    out = []
    for c in cases:
        barriers = session.exec(select(Barrier).where(Barrier.case_id == c.id)).all()
        tasks = session.exec(select(DispoTask).where(DispoTask.case_id == c.id)).all()
        referrals = session.exec(select(Referral).where(Referral.case_id == c.id)).all()
        ref_by_status: dict = {}
        for r in referrals:
            ref_by_status[r.status] = ref_by_status.get(r.status, 0) + 1
        out.append(
            {
                "id": c.id,
                "patient_id": c.patient_id,
                "state": c.state,
                "active_pathways": _named_pathways(c.active_pathways),
                "dirty": c.dirty,
                "next_review_at": c.next_review_at.isoformat() if c.next_review_at else None,
                "counts": {
                    "open_barriers": sum(1 for b in barriers if b.status in _OPEN_BARRIER),
                    "open_tasks": sum(1 for t in tasks if t.status in _OPEN_TASK),
                    "referrals": ref_by_status,
                },
            }
        )
    return out


@router.get("/cases/{case_id}/board", tags=["board"], summary="The readiness board for one case")
def case_board(case_id: str, session: Session = Depends(get_session)) -> dict:
    case = session.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Unknown case '{case_id}'")

    barriers = session.exec(select(Barrier).where(Barrier.case_id == case_id)).all()
    tasks = session.exec(select(DispoTask).where(DispoTask.case_id == case_id)).all()
    referrals = session.exec(select(Referral).where(Referral.case_id == case_id)).all()
    approvals = session.exec(
        select(Approval).where(Approval.case_id == case_id, Approval.status == "pending")
    ).all()
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.case_id == case_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(20)
    ).all()

    readiness = derive_readiness(
        [{"dimension": b.dimension, "status": b.status} for b in barriers],
        case.state,
    )

    barriers_by_dim: dict = {}
    for b in barriers:
        barriers_by_dim.setdefault(b.dimension, []).append(
            {
                "id": b.id,
                "btype": b.btype,
                "status": b.status,
                "description": b.description,
                "pathway_ids": b.pathway_ids,
            }
        )

    tasks_by_status: dict = {g: [] for g in _TASK_GROUPS}
    for t in tasks:
        tasks_by_status.setdefault(t.status, []).append(
            {
                "id": t.id,
                "title": t.title,
                "action_id": t.action_id,
                "mode": t.mode,
                "task_type": t.task_type,
                "pathway_ids": t.pathway_ids,
            }
        )

    return {
        "id": case.id,
        "patient_id": case.patient_id,
        "encounter_id": case.encounter_id,
        "state": case.state,
        "brief": case.brief,
        "dirty": case.dirty,
        "next_review_at": case.next_review_at.isoformat() if case.next_review_at else None,
        "active_pathways": _named_pathways(case.active_pathways),
        "readiness": readiness,
        "barriers": barriers_by_dim,
        "tasks": tasks_by_status,
        "referrals": [
            {
                "id": r.id,
                "facility_name": r.facility_name,
                "pathway_id": r.pathway_id,
                "status": r.status,
                "denial_reason": r.denial_reason,
            }
            for r in referrals
        ],
        "approvals": [
            {"id": a.id, "kind": a.kind, "prompt": a.prompt} for a in approvals
        ],
        "messages": [_msg_dict(m) for m in reversed(messages)],
    }


# ---------------------------------------------------------------------------
# Minimal demo UI (single self-contained page; no CDN, no framework)
# ---------------------------------------------------------------------------


@router.get("/chat/ui", include_in_schema=False)
def chat_ui() -> HTMLResponse:
    return HTMLResponse(content=_UI_HTML)


_UI_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Placer</title>
<style>
  :root { --bg:#0d1117; --panel:#161b22; --line:#30363d; --fg:#c9d1d9; --dim:#8b949e;
          --green:#3fb950; --amber:#d29922; --red:#f85149; --blue:#58a6ff; }
  * { box-sizing:border-box; margin:0; }
  body { background:var(--bg); color:var(--fg); font:13px/1.45 "SF Mono",Menlo,Consolas,monospace;
         display:flex; height:100vh; overflow:hidden; }
  #cases { width:260px; border-right:1px solid var(--line); overflow-y:auto; flex-shrink:0; }
  #cases h1 { font-size:14px; padding:12px; color:var(--blue); border-bottom:1px solid var(--line); }
  .caserow { padding:10px 12px; border-bottom:1px solid var(--line); cursor:pointer; }
  .caserow:hover, .caserow.sel { background:var(--panel); }
  .caserow .pid { font-weight:bold; }
  .caserow .meta { color:var(--dim); font-size:11px; margin-top:2px; }
  #main { flex:1; display:flex; flex-direction:column; overflow:hidden; }
  #board { flex:1; overflow-y:auto; padding:14px 18px; }
  #chat { height:34%; border-top:1px solid var(--line); display:flex; flex-direction:column; }
  #thread { flex:1; overflow-y:auto; padding:10px 14px; }
  #compose { display:flex; border-top:1px solid var(--line); }
  #compose input { flex:1; background:var(--panel); border:0; color:var(--fg); padding:10px 12px;
                   font:inherit; outline:none; }
  #compose button { background:var(--blue); color:#0d1117; border:0; padding:0 18px; font:inherit;
                    font-weight:bold; cursor:pointer; }
  .badge { display:inline-block; padding:1px 8px; border-radius:10px; font-size:11px;
           border:1px solid var(--line); text-transform:uppercase; }
  .badge.green { color:var(--green); border-color:var(--green); }
  .badge.committed, .badge.transition { color:var(--blue); border-color:var(--blue); }
  .badge.predicted { color:var(--amber); border-color:var(--amber); }
  h2 { font-size:12px; color:var(--dim); text-transform:uppercase; letter-spacing:.08em;
       margin:16px 0 6px; }
  .pw { display:flex; align-items:center; gap:8px; margin:4px 0; }
  .pw .bar { flex:1; max-width:340px; height:8px; background:var(--panel); border-radius:4px; overflow:hidden; }
  .pw .bar i { display:block; height:100%; background:var(--blue); }
  .pw button { background:none; border:1px solid var(--green); color:var(--green); font:inherit;
               font-size:11px; padding:1px 8px; border-radius:4px; cursor:pointer; }
  .dots { display:flex; gap:14px; margin:6px 0; flex-wrap:wrap; }
  .dot { text-align:center; font-size:10px; color:var(--dim); }
  .dot i { display:block; width:14px; height:14px; border-radius:50%; background:var(--line); margin:0 auto 3px; }
  .dot.clear i { background:var(--green); }
  .item { padding:4px 0; border-bottom:1px dashed var(--line); }
  .item .st { color:var(--dim); font-size:11px; }
  .st.done, .st.accepted, .st.cleared { color:var(--green); }
  .st.failed, .st.declined, .st.blocked { color:var(--red); }
  .st.in_progress, .st.pending, .st.submitted { color:var(--amber); }
  .msg { margin:6px 0; }
  .msg .who { color:var(--blue); font-weight:bold; }
  .msg.placer .who { color:var(--green); }
  .card { border:1px solid var(--amber); border-radius:6px; padding:8px 10px; margin:6px 0;
          background:var(--panel); }
  .card button { font:inherit; font-size:11px; padding:2px 10px; border-radius:4px; cursor:pointer;
                 margin-right:6px; margin-top:6px; border:1px solid; background:none; }
  .card .ok { color:var(--green); border-color:var(--green); }
  .card .no { color:var(--red); border-color:var(--red); }
  .brief { color:var(--dim); white-space:pre-wrap; margin-top:4px; }
  .empty { color:var(--dim); font-style:italic; }
</style></head><body>
<div id="cases"><h1>PLACER — cases</h1><div id="caselist"></div></div>
<div id="main">
  <div id="board"><div class="empty" style="padding:20px">Select a case…</div></div>
  <div id="chat">
    <div id="thread"></div>
    <div id="compose">
      <input id="msg" placeholder="Message the Placer agent… (Enter to send)">
      <button onclick="send()">Send</button>
    </div>
  </div>
</div>
<script>
let sel = null, WHO = 'team:cm';
const esc = s => (s==null?'':String(s)).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function j(url, body) {
  const opts = body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {};
  const r = await fetch(url, opts);
  return r.json();
}
async function pollCases() {
  try {
    const cases = await j('/cases');
    document.getElementById('caselist').innerHTML = cases.map(c => `
      <div class="caserow ${c.id===sel?'sel':''}" onclick="pick('${c.id}')">
        <div class="pid">${esc(c.patient_id)} <span class="badge ${c.state}">${c.state}</span></div>
        <div class="meta">${c.active_pathways.map(p=>esc(p.name)).join(' / ') || 'no pathway yet'}</div>
        <div class="meta">${c.counts.open_barriers} barriers · ${c.counts.open_tasks} tasks</div>
      </div>`).join('');
    if (!sel && cases.length) pick(cases[0].id);
  } catch (e) {}
}
function pick(id) { sel = id; pollBoard(); pollCases(); }
function items(list, f) { return list.length ? list.map(f).join('') : '<div class="empty">none</div>'; }
async function pollBoard() {
  if (!sel) return;
  let b; try { b = await j('/cases/' + sel + '/board'); } catch (e) { return; }
  if (b.detail) return;
  const dims = ['medical','clinical_docs','decision','payer','destination','home_logistics','transport'];
  const openBarriers = [].concat(...Object.keys(b.barriers).map(d => b.barriers[d].map(x => ({...x, dim:d}))));
  const activeTasks = ['pending','approved','in_progress','waiting','suggested','done','failed']
      .flatMap(s => (b.tasks[s]||[]).map(t => ({...t, status:s})));
  document.getElementById('board').innerHTML = `
    <div><b>${esc(b.patient_id)}</b> <span class="badge ${b.state}">${b.state}</span>
      ${b.readiness.green ? '<span class="badge green">GREEN</span>' : ''}</div>
    ${b.brief ? `<div class="brief">${esc(b.brief)}</div>` : ''}
    <h2>Pathways</h2>
    ${items(b.active_pathways, p => `
      <div class="pw"><span style="min-width:210px">${esc(p.name)}</span>
        <div class="bar"><i style="width:${Math.round((p.confidence||0)*100)}%"></i></div>
        <span>${Math.round((p.confidence||0)*100)}%</span>
        <button onclick="commit(${p.pathway_id})">Commit</button></div>`)}
    <h2>Readiness</h2>
    <div class="dots">${dims.map(d => `
      <div class="dot ${b.readiness.dimensions[d].clear?'clear':''}"><i></i>${d.replace('_',' ')}</div>`).join('')}</div>
    <h2>Barriers</h2>
    ${items(openBarriers, x => `
      <div class="item">[${esc(x.dim)}] ${esc(x.description||x.btype)} <span class="st ${x.status}">${x.status}</span></div>`)}
    <h2>Tasks</h2>
    ${items(activeTasks, t => `
      <div class="item">${esc(t.title)} <span class="st">${t.mode}${t.action_id?' · '+esc(t.action_id):''}</span>
        <span class="st ${t.status}">${t.status}</span></div>`)}
    <h2>Referrals</h2>
    ${items(b.referrals, r => `
      <div class="item">${esc(r.facility_name)} <span class="st ${r.status}">${r.status}</span>
        ${r.denial_reason ? '<span class="st">— '+esc(r.denial_reason)+'</span>' : ''}</div>`)}`;
  const cards = b.approvals.map(a => `
    <div class="card">${esc(a.prompt || a.kind + ' approval')}
      <div><button class="ok" onclick="resolve('${a.id}','approve')">Approve</button>
      <button class="no" onclick="resolve('${a.id}','reject')">Reject</button></div></div>`).join('');
  const thread = document.getElementById('thread');
  const atBottom = thread.scrollTop + thread.clientHeight >= thread.scrollHeight - 40;
  thread.innerHTML = b.messages.map(m => `
    <div class="msg ${m.author==='placer'?'placer':''}">
      <span class="who">${esc(m.author)}</span> ${esc(m.content)}</div>`).join('') + cards;
  if (atBottom) thread.scrollTop = thread.scrollHeight;
}
async function send() {
  const box = document.getElementById('msg');
  if (!box.value.trim()) return;
  const content = box.value; box.value = '';
  await j('/chat/messages', {content, case_id: sel, author: WHO});
  pollBoard();
}
async function resolve(id, verb) {
  await j('/chat/approvals/' + id + '/' + verb, {resolved_by: WHO});
  pollBoard();
}
async function commit(pid) {
  const r = await j('/cases/' + sel + '/commit', {pathway_id: pid, resolved_by: WHO});
  if (r.detail) alert(r.detail);
  pollBoard(); pollCases();
}
document.getElementById('msg').addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
pollCases();
setInterval(pollCases, 3000);
setInterval(pollBoard, 3000);
</script></body></html>
"""
