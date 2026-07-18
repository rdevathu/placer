# Placer EHR — frontend

A lightweight, Linear-styled UI over the [dummy EHR API](../backend). Built with
Vite + React + TypeScript, TanStack Query for server state, React Router for
navigation, and Tailwind CSS v4 for styling — no heavier framework needed.

It surfaces every resource the backend exposes: the patient worklist and chart,
encounters, problems, medications, orders (place/sign/complete/cancel), notes
(draft/sign), vitals & labs (including resulting a pending lab), disposition
predictions, facility placement search, the care-task worklist (patient-scoped
and global), communications log, and an admin panel for stats + demo reset.

## Development

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

The backend must be running separately (see `../backend`):

```bash
cd backend
python -m ehr.cli serve --reload   # http://localhost:8000
```

By default the frontend talks to `http://localhost:8000`. Override with a
`.env.local` (see `.env.example`):

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Build

```bash
npm run build     # type-checks then bundles to dist/
npm run preview   # serve the production build locally
```

## Structure

```
src/
├── lib/
│   ├── api.ts        # typed fetch client, one namespace per backend router
│   ├── types.ts       # response shapes mirroring the SQLModel tables
│   ├── enums.ts        # controlled vocabularies + display labels
│   ├── format.ts        # date formatting, status → badge-color mapping
│   ├── theme.tsx          # light/dark theme context
│   └── toast.tsx           # lightweight toast notifications
├── components/         # shared UI primitives (Button, Card, Table, Modal, form fields)
├── pages/
│   ├── PatientsPage.tsx        # worklist (admitted / all, search, create)
│   ├── PatientDetailPage.tsx   # chart header + tab shell
│   ├── patient/                # one tab per chart section
│   ├── FacilitiesPage.tsx      # placement search
│   ├── TasksPage.tsx           # cross-patient care-task worklist
│   └── AdminPage.tsx           # health, row counts, reset
└── routes.tsx
```
