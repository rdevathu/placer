# CLAUDE.md — Placer / Iliad

Guidance for AI agents (and humans) working in this repository.

## What this is

**Placer** is a project for a healthcare hackathon: a system that predicts a
hospitalized patient's discharge **disposition** (home, SNF, assisted living,
inpatient rehab, hospice, etc.) from their chart and proactively works the
barriers in the background — calling skilled-nursing facilities for bed
availability, calling family for preferences, pending required labs (e.g. COVID
tests), and drafting consult orders (e.g. PM&R to qualify for rehab) — so that
patients aren't stuck in the hospital waiting on case-management legwork.

**Iliad** is the general-purpose **demo EHR** in this repo that Placer runs on
top of. Iliad is deliberately Epic-like and product-agnostic; Placer is built
in parallel as its own product and surfaces inside the Iliad UI only as a
per-patient **Placer** tab (disposition predictions, care tasks, call log, and
a provider↔Placer chat thread). The agent identity string in data is `Placer`.
Everything is synthetic.

## Monorepo layout

```
placer/
├── CLAUDE.md                 # this file
├── README.md                 # project overview + quickstart
├── backend/                  # Iliad backend (FastAPI + SQLite)
│   ├── iliad/                # the `iliad` Python package
│   │   ├── main.py           # FastAPI app (uvicorn iliad.main:app)
│   │   ├── cli.py            # `python -m iliad.cli {reset,seed,stats,serve}`
│   │   ├── config.py         # env-driven config (paths, flags)
│   │   ├── db.py             # engine, session, schema lifecycle, FK toggle
│   │   ├── schemas.py        # Pydantic request DTOs (typed with enums)
│   │   ├── models/           # SQLModel tables (enums.py, clinical.py, dispo.py)
│   │   ├── routers/          # one module per domain (patients, orders, placer, ...)
│   │   └── seed/             # facilities + the hero-patient demo cohort
│   │       └── heroes/       # one module per hero: prose constants + build()
│   ├── tests/                # pytest end-to-end API tests
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/                 # Iliad UI (React + Vite, Linear-styled)
└── synthetic-examples/       # provided FHIR data — kept for reference, NOT imported
```

Add new top-level apps (e.g. `agents/` for the real Placer agent runtime) as
sibling directories. Keep each app self-contained with its own dependency
manifest.

## Backend architecture (read before editing)

- **Single SQLite file** (`backend/iliad.db`), driven by SQLModel/SQLAlchemy 2.0.
  The DB is disposable — it is always rebuilt from the seed set, never migrated.
- **The seed is the demo: 4 hero patients only.** Synthesized **active**
  inpatients (`encounter.status='in-progress'`) with deep charts: prior
  inpatient + outpatient encounters (each fully noted), long realistic H&Ps,
  daily progress notes, discharge summaries, and family-communication notes,
  all primed with disposition signal. Fixed IDs (`hero-a-stroke`, …) and MRNs
  (`MRN90001`…) so agent scripts can hardcode them. The old 25-patient Synthea
  import was removed; `synthetic-examples/` stays on disk but is unused.
- **Orders are the only agent-writable clinical-action surface.** Seeded chart
  history is physician-authored; nothing in the seed is authored by Placer
  except its own domain rows (assessments, care tasks, chat messages). New
  actions go through `/orders`; signing a lab order materializes a pending
  result that can later be resulted.
- **Placer domain** lives in native tables: `dispo_assessments` (append-only
  predictions with `is_current`), `care_tasks` (the per-patient worklist),
  `facilities` (placement search + bed counts), `communications` (call log),
  and `placer_messages` (the per-patient provider↔Placer chat thread,
  rendered ascending by `created_at`; no auto-reply).

### Known constraints / gotchas (don't relearn these the hard way)

- **Target Python 3.9** (system Python on the dev machine). Use
  `from __future__ import annotations`; avoid 3.10+ syntax at runtime. In
  SQLModel/pydantic class bodies always use `Optional[X]`, never `X | None` —
  annotations there are resolved at class-creation time.
- **No ORM `relationship()` definitions.** Without them SQLAlchemy's flush does
  not order inserts by FK dependency, so **bulk seeding runs with FK enforcement
  disabled** via `db.fk_enforcement(False)`. FK enforcement is **ON** for all
  runtime API connections. If you add a bulk loader, wrap it the same way.
- **No circular FKs.** `care_tasks.related_order_id` is the FK-backed link;
  `orders.linked_care_task_id` is a *soft* reference (no constraint) to avoid a
  cycle that breaks insert ordering. Keep new cross-links one-directional.
- **Seed builders must create fresh ORM instances each call** (see
  `seed/facilities.py` and `seed/heroes/`). Module-level *string* constants for
  note prose are fine; module-level SQLModel *instances* are not — they
  silently fail to re-insert on the second reset.
- **Seed note prose lives in `seed/heroes/`**, one module per hero: long-form
  markdown constants at module top, a `build(session)` at the bottom that
  constructs every row. Note `encounter_id`s must match encounter IDs defined
  in the same module.
- **`raw_fhir` is stripped from responses by default** (`?include_raw=true` to
  get it). Enum columns are stored as plain strings; validation/vocabulary lives
  in the request DTOs (`schemas.py`).
- **Age is computed at read time**, never stored (avoids drift vs the demo date).

## Development

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m iliad.cli reset            # build + seed the database
python -m iliad.cli serve --reload   # http://localhost:8000/docs
pytest -q                            # run the test suite
```

- Interactive docs: `/docs` (Swagger) and `/redoc`. Machine schema: `/openapi.json`.
- Reset between demo runs: `POST /admin/reset` or `python -m iliad.cli reset`.
- The app auto-seeds an empty DB on startup (`ILIAD_AUTO_SEED=true` by default).

### Configuration (env vars, all optional)

| Var | Default | Purpose |
|-----|---------|---------|
| `ILIAD_DATABASE_PATH` | `backend/iliad.db` | SQLite file location |
| `ILIAD_AUTO_SEED` | `true` | Seed on startup if DB is empty |
| `ILIAD_ALLOW_RESET` | `true` | Enable `POST /admin/reset` |
| `ILIAD_SQL_ECHO` | `false` | Log SQL |

## Conventions

### API design (optimize for agent traversal)

- **One clear place to read each thing, one clear place to act.** Reads are
  patient-scoped and filtered (`/patients/{id}/labs?status=pending`); never add
  an unbounded list endpoint (a single inpatient encounter has hundreds of
  observations). `/patients/{id}/chart` is the aggregate an agent hits first.
- **Rich OpenAPI where it matters most:** write/transition endpoints (`/orders`,
  `/orders/{id}/sign`, `/dispo-assessments`, `/patients/{id}/placer/messages`)
  and the pending-vs-resulted filters. Give each write endpoint a `summary` and
  a `description` that spells out the state machine and the enum vocabulary.
- **Controlled vocabularies are `str` enums** in `models/enums.py`, surfaced to
  agents through the typed request DTOs. Filter values are lowercase-snake and
  stable — agents depend on them.
- **Illegal state transitions return HTTP 409** with a message naming the current
  state and what's allowed, so an agent can recover.
- List endpoints take `limit`/`offset`; return lean dicts (no `raw_fhir`) by
  default.

### Frontend

- The Iliad UI keeps EHR domains as their own patient tabs (Overview,
  Encounters, Problems, Medications, Orders, Labs, Notes). Everything
  Placer-related lives in the single **Placer** tab
  (`frontend/src/pages/patient/placer/`) — don't leak Placer features into the
  general EHR surfaces beyond the compact header prediction badge.

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
  sets `ILIAD_DATABASE_PATH` before import). Use the `fresh_db` fixture for tests
  that mutate data. Cover new workflows the way `test_api.py` covers the order
  lifecycle and disposition supersession.

### Git

- Conventional, present-tense commit subjects (e.g. "Add facility bed-search
  filter"). Never commit `*.db`, `.venv/`, or `__pycache__` (see `.gitignore`).
- Don't commit real PHI. All data here is and must remain synthetic.
