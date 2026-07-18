# Wave-2 interface contract (frozen)

Three agents build in parallel against this contract. File ownership is exclusive —
do not edit files outside your area.

## File ownership

| Area | Owner | Files |
|---|---|---|
| Brain | 2a | `placer/brain/*` (new pkg), `placer/main.py` (startup wiring ONLY), may ADD an `EngineMeta` key-value table to `placer/models.py` (touch nothing else in it), `tests/test_brain*.py` |
| Workers | 2b | `placer/workers/*` (new pkg), `placer/calls/*` (new pkg), `tests/test_workers*.py` |
| Chat/API | 2c | `placer/api/chat.py` (new), append-only edit to `placer/api/__init__.py` `routers` list, `tests/test_chat*.py` |
| Shared (frozen) | orchestrator | `placer/llm.py`, `placer/models.py` (except 2a's EngineMeta addition), `placer/state.py`, `placer/ehr_client.py`, `placer/registry/*`, `placer/config.py`, `placer/db.py` |

## Cross-boundary functions (implement/import exactly these)

### Brain exposes (2a implements in `placer/brain/actions.py`; 2c imports)

```python
def commit_pathway(session, case_id: str, pathway_id: int, resolved_by: str) -> dict:
    """Team decision. Applies 'commit' transition, runs trump() pruning,
    rebuilds the plan for the decided pathway, marks APPROVAL-mode plan tasks
    status='approved' (the batch card that invoked this covered them),
    marks the case dirty. Returns {'state', 'kept', 'cancelled', 'created'}."""

def approve_tasks(session, task_ids: list, resolved_by: str) -> dict:
    """Suggested-card approval: tasks -> status 'approved', mark case dirty."""

def reject_approval(session, approval_id: str, resolved_by: str) -> dict:
    """Approval -> 'rejected'; linked tasks -> 'cancelled'."""

def reassess_case(session, case_id: str) -> None:
    """Mark case dirty so the loop reassesses soon (used by chat Intake)."""
```

2c: call these; do not reimplement their logic. If the import fails at your test
time because 2a hasn't landed, mock `placer.brain.actions` in tests.

### Workers expose (2b implements in `placer/workers/__init__.py`; 2a imports)

```python
def run_task(session, task) -> dict:
    """Execute one DispoTask (already status approved/auto). Dispatch on
    task.task_type. Does its own EHR writes via EHRClient and engine-DB writes
    (referrals, chat notifications, intel). Sets task.result and returns it.
    Must NOT change task.status ('in_progress'/'done'/'failed' is the brain
    executor's job) and must NOT call GPS/router. Unknown task_type ->
    raise ValueError (brain marks the task failed + creates a message_team task)."""
```

Task types 2b must handle (task.payload carries parameters; see router templates
in 2a's spec — payload keys are documented in each template's `payload` note):
`chart_audit`, `draft_order`, `draft_consult`, `preference_call`, `build_shortlist`,
`facility_intake_call`, `facility_screen_call`, `submit_referral`, `finalize_acceptance`,
`verify_benefits`, `book_transport`, `message_team`.

### Chat exposes (2c implements; brain/workers import from `placer/api/chat.py`)

```python
def post_message(session, content: str, *, case_id=None, kind="text",
                 author="placer", approval_id=None) -> "ChatMessage":
    """The ONLY way brain/workers put anything in chat. Commits are the
    caller's responsibility (add to session, no commit inside)."""
```

## Conventions all three follow

- LLM access ONLY via `placer.llm.structured(prompt, PydanticSchema, system=...)`
  and `placer.llm.complete(messages, system=...)`. Tests monkeypatch these.
- Python 3.9 (`from __future__ import annotations`), no ORM relationships,
  match backend code style. All tests offline (mock llm + EHRClient with
  monkeypatch or httpx MockTransport).
- Engine writes to the EHR always go through `EHRClient` (it sets X-Actor).
- Case mutation discipline: set `case.dirty = True` after anything that should
  trigger reassessment; never call GPS directly outside the brain loop.
- `DispoTask.idempotency_key` = f"{case_id}:{task_type}:{target}" where target
  is facility_id / order type / pathway id / "-" — creators catch IntegrityError
  as the dedupe signal.
