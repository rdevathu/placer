# Iliad — Backend

**Iliad** is a lightweight, Epic-like demo EHR exposed as a REST API over a
single SQLite database. It exists so **Placer** (the disposition-planning
product built in parallel) and the Iliad frontend can reliably traverse a
patient's chart and take clinical actions. All data is synthetic.

- **Stack:** FastAPI · SQLModel/SQLAlchemy 2.0 · SQLite · Pydantic v2 (Python 3.9+)
- **Docs:** interactive Swagger at `/docs`, ReDoc at `/redoc`, schema at `/openapi.json`
- **No auth** (local demo backend, open CORS).

## Setup

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m iliad.cli reset             # drop + recreate + seed
python -m iliad.cli serve --reload    # http://localhost:8000/docs
pytest -q                             # end-to-end API tests
```

The app also auto-seeds an empty database on startup, so `uvicorn iliad.main:app`
alone works too.

### CLI

```bash
python -m iliad.cli reset [--no-heroes]               # rebuild the database
python -m iliad.cli seed [--force]                    # seed if empty
python -m iliad.cli stats                             # row counts per table
python -m iliad.cli serve [--host H --port P --reload]
```

### Configuration (env vars, all optional)

| Var | Default | Purpose |
|-----|---------|---------|
| `ILIAD_DATABASE_PATH` | `backend/iliad.db` | SQLite file location |
| `ILIAD_AUTO_SEED` | `true` | Seed on startup if DB is empty |
| `ILIAD_ALLOW_RESET` | `true` | Enable `POST /admin/reset` |
| `ILIAD_SQL_ECHO` | `false` | Log SQL |

## Data model

The seed is the demo: **4 synthesized hero patients**, each an **active
inpatient** (`encounter.status=in-progress`) with a deep chart — prior
inpatient and outpatient encounters, long realistic H&Ps, daily progress
notes, discharge summaries, and family-communication notes. Fixed IDs/MRNs so
scripts can hardcode them:

| ID | MRN | Likely disposition |
|----|-----|--------------------|
| `hero-a-stroke` | MRN90001 | SNF |
| `hero-b-chf` | MRN90002 | Home + home health |
| `hero-c-hospice` | MRN90003 | Hospice |
| `hero-d-ambiguous` | MRN90004 | Undetermined |

Tables: `patients`, `encounters`, `conditions`, `observations` (vitals + labs),
`diagnostic_reports`, `medications`, `procedures`, `immunizations`, `notes`,
`orders`, and the Placer domain: `dispo_assessments`, `care_tasks`,
`facilities`, `communications`, `placer_messages`.

## Key workflows

**Read a chart (one call):**
```
GET /patients/{id}/chart
```
Returns demographics (incl. phone, address, emergency contact), active
encounter, active problems, current meds, latest vitals (one per type),
pending + abnormal labs, current disposition prediction, and open care tasks.

**Order lifecycle** — `draft` (pended) → `signed` → `completed` | `cancelled`:
```
POST /orders                 { order_type, display, status: "draft" }   # pend
POST /orders/{id}/sign       { signed_by }                              # sign
POST /orders/{id}/complete                                              # fulfill
```
Signing a `lab` order auto-creates a **pending** observation; completing it (or
`POST /labs/{obs_id}/result`) marks it final. Query in-flight labs with
`GET /patients/{id}/labs?status=pending`.

**Disposition** — post a prediction (auto-supersedes the prior current one):
```
POST /dispo-assessments   { patient_id, predicted_disposition, confidence, rationale, barriers }
GET  /patients/{id}/dispo-assessments/current
```

**Placer chat** — the per-patient thread between the care team and Placer:
```
GET  /patients/{id}/placer/messages          # ascending created_at
POST /patients/{id}/placer/messages          { sender: "provider"|"placer", sender_name, text }
```
No auto-reply is generated; Placer responds asynchronously.

**Placement search / calls:**
```
GET   /facilities?facility_type=snf&has_available_beds=true&accepts_covid_positive=false
PATCH /facilities/{id}     { available_beds }        # update after a call
POST  /communications      { ... }                   # log the call
POST  /care-tasks          { task_type, title }      # the worklist
```

**Reset between demo runs:**
```
POST /admin/reset          # or: python -m iliad.cli reset
```

## Full endpoint reference

### patients
- `GET    /patients` — List / search (filters: `q`, `admitted`, `limit`, `offset`)
- `GET    /patients/{id}` — Get one patient (computed `age`)
- `GET    /patients/{id}/chart` — **Aggregate chart snapshot**
- `POST   /patients` — Create a patient
- `PATCH  /patients/{id}` — Update demographics / social fields

### encounters
- `GET    /encounters` — List / filter (`patient_id`, `status`, `class_code`)
- `GET    /patients/{id}/encounters` — A patient's encounters
- `GET    /encounters/{id}` — Get one
- `POST   /encounters` — Create/admit
- `PATCH  /encounters/{id}` — Update (discharge via `period_end`, set disposition)

### conditions
- `GET    /patients/{id}/conditions` — Problems/diagnoses (`clinical_status`, `category`)
- `GET    /conditions/{id}` · `POST /conditions` · `PATCH /conditions/{id}`

### observations (vitals / labs)
- `GET    /patients/{id}/vitals` — Vitals (`code`)
- `GET    /patients/{id}/labs` — Labs (`status=pending|resulted`, `code`)
- `GET    /patients/{id}/diagnostic-reports` — Lab panels
- `GET    /diagnostic-reports/{id}` — Panel with nested results
- `GET    /observations/{id}` · `POST /observations`
- `POST   /labs/{id}/result` — Result a pending lab

### medications
- `GET    /patients/{id}/medications` (`status`, `category`)
- `GET    /medications/{id}` · `POST /medications` · `PATCH /medications/{id}`

### orders
- `GET    /orders` (`patient_id`, `status`, `order_type`)
- `GET    /orders/{id}` · `POST /orders` · `PATCH /orders/{id}`
- `POST   /orders/{id}/sign` · `/complete` · `/cancel`

### notes
- `GET    /patients/{id}/notes` (`note_type`, `status`)
- `GET    /notes/{id}` · `POST /notes` · `PATCH /notes/{id}` · `POST /notes/{id}/sign`

### disposition
- `GET    /patients/{id}/dispo-assessments` · `/current`
- `POST   /dispo-assessments`
- `GET    /facilities` (`facility_type`, `state`, `has_available_beds`, `accepts_covid_positive`)
- `GET    /facilities/{id}` · `POST /facilities` · `PATCH /facilities/{id}`

### care-tasks
- `GET    /care-tasks` (`patient_id`, `status`, `task_type`, `assigned_to`)
- `GET    /care-tasks/{id}` · `POST /care-tasks` · `PATCH /care-tasks/{id}`

### placer
- `GET    /patients/{id}/placer/messages` — The provider↔Placer chat thread
- `POST   /patients/{id}/placer/messages` — Append a message

### communications
- `GET    /communications` (`patient_id`, `care_task_id`, `facility_id`)
- `GET    /communications/{id}` · `POST /communications`

### admin
- `GET    /admin/health` · `GET /admin/stats` · `POST /admin/reset`

## Notes for agent builders

- Enum values in the request schemas are the accepted vocabulary — send those
  exact strings. Illegal state transitions return **409** with the allowed states.
- Responses omit the bulky `raw_fhir` field by default; pass `?include_raw=true`
  on detail endpoints to get the original FHIR.
- The agent identity string used in seeded data (`assessed_by`, `assigned_to`)
  is **`Placer`**.
