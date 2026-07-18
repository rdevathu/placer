# Placer Engine

The agentic service that drives inpatients to discharge readiness. It watches
the dummy EHR (`backend/`) event feed, maintains a Case per admitted patient,
tracks candidate discharge pathways and their barriers, and works tasks
(facility referrals, family calls, orders) until the case goes green.

It also mirrors both ways into the Iliad EHR's per-patient "Placer" tab:
placer-authored chat and engine tasks go out as `placer_messages` /
`care_tasks`, and provider replies come back via the `placer_message.created`
event (toggle with `PLACER_MIRROR`, default on).

## Run

```bash
# 1) The Iliad EHR (separate terminal, from backend/, its own .venv):
python -m iliad.cli serve               # http://localhost:8000

# 2) The engine:
cd engine
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...     # required: GPS/intake LLM calls
export PLACER_LOOP_ENABLED=true         # brain loop on (default true)
export CALL_MODE=simulated              # scripted calls, no Twilio
uvicorn placer.main:app --port 8001

python -m pytest -q                     # offline test suite (no EHR, no LLM)
```

Demo UI: http://localhost:8001/chat/ui (cases appear once the loop's startup
reconciliation sees the 4 admitted hero patients on :8000).

Env vars (all optional): `PLACER_DB_PATH`, `EHR_BASE_URL`, `PLACER_MODEL`,
`CALL_MODE` (simulated|twilio), `HEARTBEAT_HOURS`, `DEBOUNCE_SECONDS`,
`CONFIDENCE_FLOOR`, `MAX_CANDIDATES`, `POLL_INTERVAL_SECONDS`, `ACTOR_PREFIX`,
`PLACER_MIRROR` (mirror chat/tasks into the Iliad Placer tab, default true),
`PLACER_LOOP_ENABLED`.
