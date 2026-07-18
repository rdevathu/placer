# Placer (+ Iliad, the demo EHR it runs on)

A hackathon project for **agentic discharge-disposition planning**. The idea:
once a care team decides where a hospitalized patient should go after discharge
(home, skilled nursing, assisted living, inpatient rehab, hospice, …), a lot of
slow human legwork stands between that decision and the patient actually leaving
— calling SNFs for open beds, calling family for preferences, ordering
SNF-required labs (COVID tests), getting consults (PM&R) to qualify for rehab.
Patients wait extra days in the hospital for this.

**Placer** predicts the likely disposition from the patient's chart **early**
and works those barriers in the background (computer use + phone calls), so the
paperwork and coordination are already moving by the time the team commits.

**Iliad** is the general-purpose demo EHR that Placer runs on top of. Placer is
built in parallel as its own product; inside the Iliad UI it surfaces as a
per-patient **Placer** tab (predictions, care tasks, call log, and a chat
thread with the care team).

## This repo

- **`backend/`** — **Iliad's** backend: a lightweight, Epic-like EHR with a
  clean REST API over a single SQLite database. It mimics the core EHR
  functions (patients, encounters, notes, labs, meds, orders, problems) and
  hosts the Placer-facing constructs (predictions, care-task worklist,
  facilities, call logs, provider↔Placer chat). Everything is synthetic.
- **`frontend/`** — **Iliad's** UI: a lightweight, Linear-styled app over that
  API — patient worklist + chart, orders/notes/labs with their write actions,
  facility search, and the per-patient Placer tab.

See **[`backend/README.md`](backend/README.md)** for the full API reference,
**[`frontend/README.md`](frontend/README.md)** for the UI, and
**[`CLAUDE.md`](CLAUDE.md)** for architecture and conventions.

## Quickstart

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m iliad.cli reset          # build + seed the SQLite database
python -m iliad.cli serve --reload # API at http://localhost:8000  (docs at /docs)
```

In a second terminal, start the UI:

```bash
cd frontend
npm install
npm run dev                        # UI at http://localhost:5173
```

Then explore the API directly if you like:

```bash
curl 'http://localhost:8000/patients?admitted=true'        # the inpatient worklist
curl 'http://localhost:8000/patients/hero-a-stroke/chart'  # one-call chart snapshot
```

Reset to the seed state anytime (great between demo runs):

```bash
curl -X POST http://localhost:8000/admin/reset      # or: python -m iliad.cli reset
```

## Demo patients

Four **active inpatients** are seeded with deep charts (prior inpatient and
outpatient encounters, long realistic H&Ps, daily progress notes, discharge
summaries, family-communication notes) primed for disposition prediction:

| ID | MRN | Sketch | Likely disposition |
|----|-----|--------|--------------------|
| `hero-a-stroke` | MRN90001 | 78F, stroke, lives alone in a 2nd-floor walk-up, daughter out of state | **SNF** |
| `hero-b-chf` | MRN90002 | 66M, CHF exacerbation improving, lives with spouse in single-story home | **Home + home health** |
| `hero-c-hospice` | MRN90003 | 84F, metastatic cancer, comfort-focused (DNR), daughter is caregiver | **Hospice** |
| `hero-d-ambiguous` | MRN90004 | 71M, pneumonia + COPD, social situation undocumented | **Undetermined** (tests reasoning) |

## Status

- [x] Iliad backend: demo EHR API + seed/reset + Placer chat thread
- [x] Iliad frontend: demo UI with the per-patient Placer tab
- [ ] Placer agents: disposition prediction + background task execution

## Data & safety

All clinical data is synthetic (hand-authored demo patients; the
`synthetic-examples/` FHIR set provided by Abridge is kept for reference but no
longer imported). No real PHI is present, and none should ever be committed.
