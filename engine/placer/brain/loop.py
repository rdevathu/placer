"""The brain loop: poll EHR events, keep cases fresh, execute approved work.

Single async background task started from main.py. Each tick runs in a worker
thread (the pipeline is sync: LLM + httpx calls) and does four things:
events -> dirty flags, heartbeat -> dirty flags, dirty cases -> run_assessment,
runnable tasks -> workers.run_task. Every case iteration is wrapped so one bad
case can never stall the fleet; outcomes are recorded as Run rows.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import timedelta
from typing import Optional

from sqlmodel import Session, select

from placer import config
from placer.db import engine as db_engine
from placer.ehr_client import EHRClient
from placer.models import Barrier, Case, DispoTask, EngineMeta, Run, utcnow

from . import pipeline, router_logic, watchman
from .chatlink import post_chat

logger = logging.getLogger(__name__)

CURSOR_KEY = "ehr_cursor"

# Per-case locks so a slow assessment is never entered twice concurrently.
# threading (not asyncio) locks: ticks run inside asyncio.to_thread.
_case_locks: dict = {}
_locks_guard = threading.Lock()


def _lock_for(case_id: str) -> threading.Lock:
    with _locks_guard:
        return _case_locks.setdefault(case_id, threading.Lock())


# -- cursor -----------------------------------------------------------------


def _get_cursor(session: Session) -> int:
    row = session.get(EngineMeta, CURSOR_KEY)
    return int(row.value) if row else 0


def _set_cursor(session: Session, seq: int) -> None:
    row = session.get(EngineMeta, CURSOR_KEY)
    if row is None:
        row = EngineMeta(key=CURSOR_KEY, value=str(seq))
    else:
        row.value = str(seq)
    session.add(row)


# -- case lifecycle ---------------------------------------------------------


def _find_case(session: Session, patient_id: str) -> Optional[Case]:
    return session.exec(
        select(Case).where(Case.patient_id == patient_id, Case.state != "discharged")
    ).first()


def _seed_case(session: Session, patient_id: str, encounter_id: Optional[str] = None) -> Case:
    """New tracked admission: create the case plus the two barriers that must
    exist and be explicitly cleared by humans (see state.derive_readiness)."""
    case = Case(patient_id=patient_id, encounter_id=encounter_id, state="tracking", dirty=True)
    session.add(case)
    session.commit()
    session.add(Barrier(
        case_id=case.id, dimension="medical", btype="medical_clearance",
        description="Medical readiness for discharge not yet confirmed by the team",
    ))
    session.add(Barrier(
        case_id=case.id, dimension="decision", btype="family_decision",
        description="Patient/family disposition preference not yet established",
    ))
    session.commit()
    logger.info("brain: new case %s for patient %s", case.id, patient_id)
    return case


def _mark_dirty(session: Session, case: Case) -> None:
    case.dirty = True
    case.updated_at = utcnow()  # updated_at doubles as the debounce clock
    session.add(case)


# -- tick phases ------------------------------------------------------------


def _process_events(session: Session, ehr: EHRClient) -> None:
    cursor = _get_cursor(session)
    try:
        events = ehr.list_events(since=cursor, limit=200)
    except Exception as exc:
        logger.warning("brain: event poll failed: %s", exc)
        return
    for ev in events:
        try:
            _route_event(session, ev)
        except Exception:
            logger.exception("brain: failed routing event seq=%s", ev.get("seq"))
        cursor = max(cursor, int(ev.get("seq") or cursor))
    _set_cursor(session, cursor)
    session.commit()


def _route_event(session: Session, ev: dict) -> None:
    patient_id = ev.get("patient_id")
    event_type = ev.get("event_type") or ""
    actor = ev.get("actor") or ""

    if event_type == "placer_message.created":
        _route_placer_message(session, ev)
        return

    if event_type == "patient.admitted" and patient_id:
        case = _find_case(session, patient_id)
        if case is None:
            payload = ev.get("payload") or {}
            encounter_id = payload.get("encounter_id") or (
                ev.get("entity_id") if ev.get("entity_type") == "encounter" else None
            )
            _seed_case(session, patient_id, encounter_id)
        else:
            _mark_dirty(session, case)
        return

    if not patient_id:
        return
    case = _find_case(session, patient_id)
    if case is None:
        return

    if actor.startswith(config.ACTOR_PREFIX + ":"):
        # Our own workers' writes are internal outcomes — no triage needed.
        _mark_dirty(session, case)
        return

    verdict = watchman.is_material(ev, case.brief or "")
    if verdict.material:
        _mark_dirty(session, case)


def _route_placer_message(session: Session, ev: dict) -> None:
    """Inbound Iliad Placer-tab chat. Provider messages are mirrored into the
    engine thread, then answered by the shared responder (grounded reply +
    team_notes + dirty); sender='placer' is the echo of our own outbound
    mirror — including the responder's own replies — and is skipped."""
    payload = ev.get("payload") or {}
    if payload.get("sender") != "provider":
        return  # our own mirrored message coming back around
    patient_id = ev.get("patient_id")
    if not patient_id:
        return
    case = _find_case(session, patient_id)
    if case is None:
        return
    text = payload.get("text") or ""
    author = "team:" + (payload.get("sender_name") or "provider")
    try:
        from placer.api.chat import post_message

        post_message(session, text, case_id=case.id, author=author)
    except ImportError:
        logger.warning("brain: placer.api.chat unavailable; provider message not echoed to chat")
    try:
        from .respond import respond_to_team

        respond_to_team(session, case, text, author)
    except Exception:
        # Reply failed — still capture the note + dirty so nothing is lost.
        logger.exception("brain: responder failed for case %s", case.id)
        facts = dict(case.facts or {})  # JSON column: rebuild the dict
        notes = list(facts.get("team_notes") or [])
        notes.append({"ts": utcnow().isoformat(), "author": author, "content": text})
        facts["team_notes"] = notes
        case.facts = facts
        _mark_dirty(session, case)


def _heartbeat(session: Session) -> None:
    now = utcnow()
    due = session.exec(
        select(Case).where(
            Case.state != "discharged",
            Case.next_review_at != None,  # noqa: E711 — SQLAlchemy IS NOT NULL
            Case.next_review_at < now,
        )
    ).all()
    for case in due:
        _mark_dirty(session, case)
        case.next_review_at = None  # re-set by the next assessment
        session.add(case)
    if due:
        session.commit()


def _assess_dirty(session: Session, ehr: EHRClient) -> None:
    now = utcnow()
    debounce = timedelta(seconds=config.DEBOUNCE_SECONDS)
    dirty = session.exec(select(Case).where(Case.dirty == True)).all()  # noqa: E712
    for case in dirty:
        if case.updated_at and now - case.updated_at < debounce:
            continue  # still settling; wait for the burst of events to finish
        lock = _lock_for(case.id)
        if not lock.acquire(blocking=False):
            continue
        try:
            run = Run(agent="brain", case_id=case.id, trigger="dirty", status="running")
            session.add(run)
            session.commit()
            try:
                pipeline.run_assessment(session, case, ehr)
                case.dirty = False
                session.add(case)
                run.status = "done"
                run.outcome = f"assessed; state={case.state}"
            except Exception as exc:
                logger.exception("brain: assessment failed for case %s", case.id)
                run.status = "error"
                run.outcome = str(exc)
                case.dirty = False  # don't hot-loop a broken case; heartbeat retries
                session.add(case)
            run.finished_at = utcnow()
            session.add(run)
            session.commit()
        finally:
            lock.release()


def _execute_tasks(session: Session, ehr: EHRClient) -> None:
    try:
        from placer.workers import run_task  # deferred: built by a sibling agent
    except ImportError:
        logger.debug("brain: placer.workers not available yet; skipping executor")
        return

    # Only pending/approved are ever picked up — 'waiting' tasks (parked on
    # telephony/integrations/humans) are never re-executed by the loop; a
    # human unblocks them by re-approving or the plan replaces them.
    runnable = [
        t for t in session.exec(
            select(DispoTask).where(DispoTask.status.in_(("pending", "approved")))  # type: ignore[attr-defined]
        ).all()
        if t.status == "approved" or t.mode == "auto"
    ]
    touched_cases: set = set()
    for task in runnable:
        task.status = "in_progress"
        task.updated_at = utcnow()
        session.add(task)
        session.commit()
        # Workers read parameters off task.payload (stored as JSON in detail —
        # see router_logic docstring). Instance attribute, not a column —
        # pydantic v2 rejects plain setattr on undeclared fields, so go around.
        object.__setattr__(task, "payload", router_logic.decode_payload(task))
        try:
            result = run_task(session, task)
            result = result if isinstance(result, dict) else {"result": result}
            task.result = result
            if result.get("waiting_on"):
                # Truthful park: the worker could not act for real (no
                # telephony / integration / needs a human). One chat note,
                # no dirty-marking — nothing about the case changed.
                task.status = "waiting"
                if not result.get("chat_posted"):
                    post_chat(
                        session,
                        f"Waiting on {result['waiting_on']}: {task.title} — "
                        f"{result.get('note', 'not yet enabled')}",
                        case_id=task.case_id,
                        kind="notification",
                    )
            else:
                task.status = "done"
                touched_cases.add(task.case_id)
        except Exception as exc:
            logger.exception("brain: task %s (%s) failed", task.id, task.task_type)
            task.status = "failed"
            task.result = {"error": str(exc)}
            _escalate_failure(session, task, exc)
            touched_cases.add(task.case_id)
        task.updated_at = utcnow()
        session.add(task)
        session.commit()
        _mirror_task_outcome(task)

    for cid in touched_cases:
        case = session.get(Case, cid)
        if case is not None:
            _mark_dirty(session, case)
    if touched_cases:
        session.commit()


def _mirror_task_outcome(task: DispoTask) -> None:
    """Best-effort: reflect a finished engine task onto its mirrored EHR care
    task (created by router_logic.persist_plan; id lives in the detail JSON).
    Mirror failure must NEVER break the executor."""
    if not config.PLACER_MIRROR:
        return
    try:
        ehr_id = router_logic.decode_payload(task).get("ehr_care_task_id")
        if not ehr_id:
            return
        import json

        result = task.result
        summary = (json.dumps(result) if isinstance(result, dict) else str(result or ""))[:500]
        status = "completed" if task.status == "done" else "blocked"
        client = EHRClient(actor=f"{config.ACTOR_PREFIX}:placer")
        try:
            client.update_care_task(ehr_id, status=status, result_summary=summary)
        finally:
            client.close()
    except Exception:
        logger.warning("brain: EHR care-task mirror failed for task %s", task.id, exc_info=True)


def _escalate_failure(session: Session, task: DispoTask, exc: Exception) -> None:
    """A failed task becomes a message_team ask plus a chat note."""
    import json

    key = f"{task.case_id}:message_team:failed-{task.id}"
    if not session.exec(select(DispoTask).where(DispoTask.idempotency_key == key)).first():
        session.add(DispoTask(
            case_id=task.case_id,
            barrier_id=task.barrier_id,
            action_id="SGE-027",
            task_type="message_team",
            mode="auto",
            status="pending",
            pathway_ids=task.pathway_ids,
            idempotency_key=key,
            title=f"Escalate: '{task.title}' failed",
            detail=json.dumps({"question": f"Automated step '{task.title}' failed ({exc}). How should we proceed?"}),
        ))
    post_chat(
        session,
        f"Task failed: {task.title} — {exc}. Escalated to the team.",
        case_id=task.case_id,
        kind="notification",
    )


def _reconcile_admitted(session: Session, ehr: EHRClient) -> None:
    """Startup: any currently-admitted patient without a case gets one (covers
    admissions that predate the engine's first event cursor)."""
    try:
        admitted = ehr.list_admitted_patients()
    except Exception as exc:
        logger.warning("brain: startup reconciliation skipped (EHR unreachable: %s)", exc)
        return
    for p in admitted:
        pid = p.get("id")
        if pid and _find_case(session, pid) is None:
            _seed_case(session, pid, p.get("encounter_id"))


def tick(ehr: EHRClient) -> None:
    """One synchronous pass over all four phases."""
    with Session(db_engine) as session:
        _process_events(session, ehr)
        _heartbeat(session)
        _assess_dirty(session, ehr)
        _execute_tasks(session, ehr)


async def engine_loop() -> None:
    """The background task main.py launches at startup."""
    ehr = EHRClient(actor=f"{config.ACTOR_PREFIX}:placer")
    logger.info("brain: loop starting (poll every %ss)", config.POLL_INTERVAL_SECONDS)
    try:
        try:
            with Session(db_engine) as session:
                await asyncio.to_thread(_reconcile_admitted, session, ehr)
        except Exception:
            logger.exception("brain: startup reconciliation failed")
        while True:
            try:
                await asyncio.to_thread(tick, ehr)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("brain: tick failed")
            await asyncio.sleep(config.POLL_INTERVAL_SECONDS)
    finally:
        ehr.close()
