"""The shared chat responder: a provider message gets a grounded ANSWER.

Both inbound provider paths — POST /chat/messages and the Iliad Placer-tab
mirror in the brain loop — call :func:`respond_to_team`. One structured LLM
call, grounded in the readiness board, decides the reply and whether the
message actually needs new work. "Summarize blockers" gets a direct answer,
never a task.
"""

from __future__ import annotations

import json
import logging

try:  # Python 3.9: Literal lives in typing
    from typing import Literal
except ImportError:  # pragma: no cover
    from typing_extensions import Literal

from pydantic import BaseModel, Field
from sqlmodel import Session

from placer import llm
from placer.board import build_board
from placer.models import Case, DispoTask, new_id, utcnow

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are Placer replying to a care-team member inside the patient's chart. "
    "Answer from the case data provided; be specific and concise (<=120 words). "
    "NEVER claim an action happened unless it appears in the data. If they ask "
    "for something requiring external action, say what you'd need (approval / "
    "telephony). Questions like 'summarize blockers' get direct grounded answers."
)

_FALLBACK_REPLY = (
    "Noted — I've logged this on the case. I couldn't compose a full answer "
    "just now; ask again or check the readiness board."
)


class TeamReply(BaseModel):
    """One turn of Placer's side of the chart chat."""

    reply: str = Field(description="The message Placer posts back to the team, grounded in the case data.")
    action_kind: Literal["none", "create_task", "clear_barrier_request", "commit_request"] = Field(
        description=(
            "'create_task' ONLY when the member asked Placer to do new real work "
            "not already covered by an existing task; 'clear_barrier_request' / "
            "'commit_request' when they are asking for those human actions; "
            "otherwise 'none' (questions, status checks, FYIs)."
        )
    )
    detail: str = Field(default="", description="One line describing the requested work (create_task only).")


def _context(session: Session, case: Case) -> dict:
    """Trimmed readiness board: what the responder grounds its answer in."""
    board = build_board(session, case, message_limit=10)
    open_tasks = {
        status: board["tasks"].get(status, [])
        for status in ("suggested", "pending", "approved", "in_progress", "waiting")
        if board["tasks"].get(status)
    }
    return {
        "state": board["state"],
        "brief": board["brief"],
        "active_pathways": board["active_pathways"],
        "readiness": board["readiness"],
        "barriers_by_dimension": board["barriers"],
        "open_tasks": open_tasks,
        "referrals": board["referrals"],
        "pending_approvals": board["approvals"],
        "recent_messages": [
            {"author": m["author"], "content": m["content"]} for m in board["messages"]
        ],
    }


def respond_to_team(session: Session, case: Case, text: str, author: str) -> str:
    """Answer one team message: append it to team_notes, mark the case dirty,
    post ONE grounded reply (author='placer' — the mirror loop skips it), and
    create a task only when the message asks for new real work. Returns the
    reply text. Never raises on LLM failure (degrades to a truthful fallback)."""
    # Team text always lands in the case memory, whatever the reply says.
    facts = dict(case.facts or {})  # JSON column: assign a fresh dict
    notes = list(facts.get("team_notes") or [])
    notes.append({"ts": utcnow().isoformat(), "author": author, "content": text})
    facts["team_notes"] = notes
    case.facts = facts
    case.dirty = True
    case.updated_at = utcnow()
    session.add(case)

    try:
        context = _context(session, case)
    except Exception:  # board build must never kill the reply
        logger.exception("respond: board build failed for case %s", case.id)
        context = {"state": case.state, "brief": case.brief}

    prompt = (
        "A care-team member wrote in the discharge-planning chat.\n\n"
        f"Author: {author}\nMessage: {text}\n\n"
        f"Case data (readiness board):\n{json.dumps(context, default=str)[:8000]}\n\n"
        "Reply to them. Set action_kind='create_task' ONLY if they asked Placer "
        "to do new real work not already covered by an open task (put a one-line "
        "description in detail). Informational asks — 'summarize blockers', "
        "status questions, FYIs — are action_kind='none'."
    )
    try:
        parsed = llm.structured(prompt, TeamReply, system=_SYSTEM)
        reply, action_kind, detail = parsed.reply, parsed.action_kind, parsed.detail
    except Exception:
        logger.exception("respond: LLM reply failed for case %s", case.id)
        reply, action_kind, detail = _FALLBACK_REPLY, "none", ""

    from placer.api.chat import post_message  # lazy: parallel-wave seam

    post_message(session, reply, case_id=case.id, author="placer", kind="text")

    if action_kind == "create_task":
        session.add(DispoTask(
            case_id=case.id,
            task_type="message_team",
            mode="auto",
            status="pending",
            title=f"Team request: {(detail or text)[:60]}",
            detail=json.dumps({"question": text}),
            # Unique per request — repeated asks are new asks, never collide.
            idempotency_key=f"{case.id}:message_team:req-{new_id()[:8]}",
        ))
    return reply
