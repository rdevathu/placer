# Placer

A hackathon project for **agentic discharge-disposition planning**. The idea:
once a care team decides where a hospitalized patient should go after discharge
(home, skilled nursing, assisted living, inpatient rehab, hospice, …), a lot of
slow human legwork stands between that decision and the patient actually leaving
— calling SNFs for open beds, calling family for preferences, ordering
SNF-required labs (COVID tests), getting consults (PM&R) to qualify for rehab.
Patients wait extra days in the hospital for this.

Placer predicts the likely disposition from the patient's chart **early** and
works those barriers in the background (computer use + phone calls), so the
paperwork and coordination are already moving by the time the team commits.

## This repo

This repo has two pieces so far:

- **`backend/`** — the **dummy EHR** the agents build against: a lightweight,
  Epic-like EHR with a clean REST API over a single SQLite database. It mimics
  the core EHR functions (patients, encounters, notes, labs, meds, orders,
  problems) and adds the disposition-planning constructs (predictions,
  care-task worklist, facilities, call logs). Everything is synthetic.
- **`frontend/`** — a lightweight, Linear-styled demo UI over that API:
  patient worklist + chart, orders/notes/labs with their write actions,
  disposition predictions, facility search, and the cross-patient care-task
  worklist.

See **[`backend/README.md`](backend/README.md)** for the full API reference,
**[`frontend/README.md`](frontend/README.md)** for the UI, and
**[`CLAUDE.md`](CLAUDE.md)** for architecture and conventions.

## Quickstart

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m ehr.cli reset          # build + seed the SQLite database
python -m ehr.cli serve --reload # API at http://localhost:8000  (docs at /docs)
```

In a second terminal, start the UI:

```bash
cd frontend
npm install
npm run dev                      # UI at http://localhost:5173
```

Then explore the API directly if you like:

```bash
curl 'http://localhost:8000/patients?admitted=true'        # the inpatient worklist
curl 'http://localhost:8000/patients/hero-a-stroke/chart'  # one-call chart snapshot
```

Reset to the seed state anytime (great between demo runs):

```bash
curl -X POST http://localhost:8000/admin/reset      # or: python -m ehr.cli reset
```

## Demo patients

Four **active inpatients** are seeded with charts primed for disposition
prediction:

| ID | MRN | Sketch | Likely disposition |
|----|-----|--------|--------------------|
| `hero-a-stroke` | MRN90001 | 78F, stroke, lives alone, deconditioned; pending COVID lab + draft PM&R consult | **SNF** |
| `hero-b-chf` | MRN90002 | 66M, CHF exacerbation improving, lives with spouse | **Home + home health** |
| `hero-c-hospice` | MRN90003 | 84F, metastatic cancer, comfort-focused (DNR) | **Hospice** |
| `hero-d-ambiguous` | MRN90004 | 71M, pneumonia + COPD, social situation undocumented | **Undetermined** (tests reasoning) |

Plus 25 historical Synthea patients imported from `synthetic-examples/`.

## Status

- [x] Backend: dummy EHR API + seed/reset
- [ ] Agents: disposition prediction + background task execution
- [x] Frontend: lightweight demo UI (see [`frontend/README.md`](frontend/README.md))

## Data & safety

All clinical data is synthetic (Synthea + LLM-generated, provided by Abridge for
the hackathon, plus hand-authored demo patients). No real PHI is present, and
none should ever be committed.
