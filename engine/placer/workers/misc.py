"""Escalation to humans: things no worker is allowed to do on its own."""

from __future__ import annotations

from sqlmodel import Session

from .common import get_payload


def message_team(session: Session, task, ehr, worker: str) -> dict:
    """payload {question}: put the question in front of the care team in chat.
    Plain text (not a notification) — it needs a human reply."""
    payload = get_payload(task)
    question = payload.get("question") or task.detail or task.title
    from placer.api.chat import post_message

    post_message(session, f"[needs a human] {question}", case_id=task.case_id, kind="text")
    return {"noted": True, "question": question}
