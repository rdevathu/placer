# Placer Engine

The agentic service that drives inpatients to discharge readiness. It watches
the dummy EHR (`backend/`) event feed, maintains a Case per admitted patient,
tracks candidate discharge pathways and their barriers, and works tasks
(facility referrals, family calls, orders) until the case goes green.

This wave is a pure skeleton: deterministic state machine, pathway registry,
SQLModel store, and an EHR client. No LLM calls yet.

## Run

```bash
cd engine
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn placer.main:app --port 8001     # EHR should be on :8000
python -m pytest -q                     # offline test suite
```

Env vars (all optional): `PLACER_DB_PATH`, `EHR_BASE_URL`, `PLACER_MODEL`,
`CALL_MODE` (simulated|twilio), `HEARTBEAT_HOURS`, `DEBOUNCE_SECONDS`,
`CONFIDENCE_FLOOR`, `MAX_CANDIDATES`, `POLL_INTERVAL_SECONDS`, `ACTOR_PREFIX`.
