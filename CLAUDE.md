# CLAUDE.md — Placer

Guidance for AI agents (and humans) working in this repository.

## What this is

**Placer** is a project for a healthcare hackathon. The goal is a system that
predicts a hospitalized patient's discharge **disposition** (home, SNF, assisted
living, inpatient rehab, hospice, etc.) from their chart and proactively works
the barriers in the background — calling skilled-nursing facilities for bed
availability, calling family for preferences, pending required labs (e.g. COVID
tests), and drafting consult orders (e.g. PM&R to qualify for rehab) — so that
patients aren't stuck in the hospital waiting on case-management legwork.

This repo currently contains the **dummy EHR backend**: a lightweight, Epic-like
EHR with a REST API that the disposition agents (and a later frontend) build
against. Everything is synthetic.

## Monorepo layout

```
placer/
├── CLAUDE.md                 # this file
├── README.md                 # project overview + quickstart
├── backend/                  # the dummy EHR (FastAPI + SQLite)
│   ├── ehr/                  # the `ehr` Python package
│   │   ├── main.py           # FastAPI app (uvicorn ehr.main:app)
│   │   ├── cli.py            # `python -m ehr.cli {reset,seed,stats,serve}`
│   │   ├── config.py         # env-driven config (paths, flags)
│   │   ├── db.py             # engine, session, schema lifecycle, FK toggle
│   │   ├── schemas.py        # Pydantic request DTOs (typed with enums)
│   │   ├── models/           # SQLModel tables (enums.py, clinical.py, dispo.py)
│   │   ├── routers/          # one module per domain (patients, orders, ...)
│   │   └── seed/             # FHIR import, hero patients, facilities, reset
│   ├── tests/                # pytest end-to-end API tests
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/                 # (placeholder) rudimentary UI, added later
└── synthetic-examples/       # provided Synthea/Abridge FHIR seed data (read-only)
```

Add new top-level apps (e.g. `agents/`, `frontend/`) as sibling directories.
Keep each app self-contained with its own dependency manifest.

## Backend architecture (read before editing)

- **Single SQLite file** (`backend/ehr.db`), driven by SQLModel/SQLAlchemy 2.0.
  The DB is disposable — it is always rebuilt from the seed set, never migrated.
- **Two data provenances, kept separate:**
  1. *Imported history* — the 25 Synthea patients flattened from
     `synthetic-examples/`. All encounters are historical (`status=finished`).
  2. *Hero patients* — synthesized **active** inpatients
     (`encounter.status='in-progress'`) whose charts are primed with disposition
     signal. These are the demo. Fixed IDs (`hero-a-stroke`, …) and MRNs
     (`MRN90001`…) so agent scripts can hardcode them.
- **Orders are the only agent-writable clinical-action surface.** Imported
  history (observations, medications) is never mutated by writes. New actions go
  through `/orders`; signing a lab order materializes a pending result that can
  later be resulted.
- **Disposition domain** lives in native tables: `dispo_assessments` (append-only
  predictions with `is_current`), `care_tasks` (the worklist), `facilities`
  (placement search + bed counts), `communications` (call log).

### Known constraints / gotchas (don't relearn these the hard way)

- **Target Python 3.9** (system Python on the dev machine). Use
  `from __future__ import annotations`; avoid 3.10+ syntax at runtime.
- **No ORM `relationship()` definitions.** Without them SQLAlchemy's flush does
  not order inserts by FK dependency, so **bulk seeding runs with FK enforcement
  disabled** via `db.fk_enforcement(False)`. FK enforcement is **ON** for all
  runtime API connections. If you add a bulk loader, wrap it the same way.
- **No circular FKs.** `care_tasks.related_order_id` is the FK-backed link;
  `orders.linked_care_task_id` is a *soft* reference (no constraint) to avoid a
  cycle that breaks insert ordering. Keep new cross-links one-directional.
- **Seed builders must create fresh ORM instances each call** (see
  `seed/facilities.py`). Never reuse a module-level SQLModel instance across
  sessions — it silently fails to re-insert on the second reset.
- **`raw_fhir` is stripped from responses by default** (`?include_raw=true` to
  get it). Enum columns are stored as plain strings; validation/vocabulary lives
  in the request DTOs (`schemas.py`).
- **Age is computed at read time**, never stored (avoids drift vs the demo date).

## Development

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m ehr.cli reset            # build + seed the database
python -m ehr.cli serve --reload   # http://localhost:8000/docs
pytest -q                          # run the test suite
```

- Interactive docs: `/docs` (Swagger) and `/redoc`. Machine schema: `/openapi.json`.
- Reset between demo runs: `POST /admin/reset` or `python -m ehr.cli reset`.
- The app auto-seeds an empty DB on startup (`EHR_AUTO_SEED=true` by default).

### Configuration (env vars, all optional)

| Var | Default | Purpose |
|-----|---------|---------|
| `EHR_DATABASE_PATH` | `backend/ehr.db` | SQLite file location |
| `EHR_AUTO_SEED` | `true` | Seed on startup if DB is empty |
| `EHR_ALLOW_RESET` | `true` | Enable `POST /admin/reset` |
| `EHR_SYNTHETIC_DIR` | `synthetic-examples/` | FHIR seed source |
| `EHR_SQL_ECHO` | `false` | Log SQL |

## Conventions

### API design (optimize for agent traversal)

- **One clear place to read each thing, one clear place to act.** Reads are
  patient-scoped and filtered (`/patients/{id}/labs?status=pending`); never add
  an unbounded list endpoint (a single inpatient encounter has ~500
  observations). `/patients/{id}/chart` is the aggregate an agent hits first.
- **Rich OpenAPI where it matters most:** write/transition endpoints (`/orders`,
  `/orders/{id}/sign`, `/dispo-assessments`) and the pending-vs-resulted filters.
  Give each write endpoint a `summary` and a `description` that spells out the
  state machine and the enum vocabulary.
- **Controlled vocabularies are `str` enums** in `models/enums.py`, surfaced to
  agents through the typed request DTOs. Filter values are lowercase-snake and
  stable — agents depend on them.
- **Illegal state transitions return HTTP 409** with a message naming the current
  state and what's allowed, so an agent can recover.
- List endpoints take `limit`/`offset`; return lean dicts (no `raw_fhir`) by
  default.

### Python style

- Standard library + FastAPI/SQLModel idioms; no heavyweight extras. Prefer
  `argparse`/stdlib over adding a dependency for small needs.
- Type-annotate signatures. Keep functions small and single-purpose.
- Module docstrings explain *why*; comments flag non-obvious decisions (the
  gotchas above are load-bearing — annotate similar ones).
- Match the surrounding code's naming and structure. New domains get their own
  `models/`, `routers/`, and `schemas.py` entries plus registration in
  `routers/__init__.py`.

### Testing

- End-to-end tests use FastAPI `TestClient` against a temp DB (`tests/conftest.py`
  sets `EHR_DATABASE_PATH` before import). Use the `fresh_db` fixture for tests
  that mutate data. Cover new workflows the way `test_api.py` covers the order
  lifecycle and disposition supersession.

### Git

- Conventional, present-tense commit subjects (e.g. "Add facility bed-search
  filter"). Never commit `*.db`, `.venv/`, or `__pycache__` (see `.gitignore`).
- Don't commit real PHI. All data here is and must remain synthetic.
