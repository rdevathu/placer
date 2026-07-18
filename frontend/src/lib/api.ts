// Thin typed fetch client over the Iliad REST API.
// One function per backend endpoint — see backend/ehr/routers/*.py.

import type {
  AdminStats,
  CareTask,
  Communication,
  Condition,
  DiagnosticReport,
  DispoAssessment,
  Encounter,
  Facility,
  Medication,
  Note,
  Observation,
  Order,
  Patient,
  PatientChart,
  PlacerMessage,
} from "./types";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

function qs(params?: Query): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

async function request<T>(
  method: string,
  path: string,
  { query, body }: { query?: Query; body?: unknown } = {},
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}${qs(query)}`, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail: unknown;
    try {
      detail = await res.json();
    } catch {
      detail = await res.text().catch(() => undefined);
    }
    const message =
      (detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : undefined) ?? `${method} ${path} failed with ${res.status}`;
    throw new ApiError(res.status, message, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const get = <T,>(path: string, query?: Query) => request<T>("GET", path, { query });
const post = <T,>(path: string, body?: unknown, query?: Query) =>
  request<T>("POST", path, { body: body ?? {}, query });
const patch = <T,>(path: string, body?: unknown) => request<T>("PATCH", path, { body: body ?? {} });

// ---------------------------------------------------------------------------
// Patients
// ---------------------------------------------------------------------------

export const patientsApi = {
  list: (params?: { q?: string; admitted?: boolean; limit?: number; offset?: number }) =>
    get<Patient[]>("/patients", params),
  get: (id: string, includeRaw = false) => get<Patient>(`/patients/${id}`, { include_raw: includeRaw }),
  chart: (id: string) => get<PatientChart>(`/patients/${id}/chart`),
  create: (body: Partial<Patient> & { mrn?: string }) => post<Patient>("/patients", body),
  update: (id: string, body: Partial<Patient>) => patch<Patient>(`/patients/${id}`, body),
};

// ---------------------------------------------------------------------------
// Encounters
// ---------------------------------------------------------------------------

export const encountersApi = {
  list: (params?: { patient_id?: string; status?: string; class_code?: string; limit?: number; offset?: number }) =>
    get<Encounter[]>("/encounters", params),
  listForPatient: (patientId: string) => get<Encounter[]>(`/patients/${patientId}/encounters`),
  get: (id: string, includeRaw = false) => get<Encounter>(`/encounters/${id}`, { include_raw: includeRaw }),
  create: (body: Record<string, unknown>) => post<Encounter>("/encounters", body),
  update: (id: string, body: Record<string, unknown>) => patch<Encounter>(`/encounters/${id}`, body),
};

// ---------------------------------------------------------------------------
// Conditions
// ---------------------------------------------------------------------------

export const conditionsApi = {
  listForPatient: (patientId: string, params?: { clinical_status?: string; category?: string }) =>
    get<Condition[]>(`/patients/${patientId}/conditions`, params),
  get: (id: string) => get<Condition>(`/conditions/${id}`),
  create: (body: Record<string, unknown>) => post<Condition>("/conditions", body),
  update: (id: string, body: Record<string, unknown>) => patch<Condition>(`/conditions/${id}`, body),
};

// ---------------------------------------------------------------------------
// Observations (vitals / labs) + diagnostic reports
// ---------------------------------------------------------------------------

export const observationsApi = {
  listVitals: (patientId: string, params?: { code?: string; limit?: number; offset?: number }) =>
    get<Observation[]>(`/patients/${patientId}/vitals`, params),
  listLabs: (patientId: string, params?: { status?: string; code?: string; limit?: number; offset?: number }) =>
    get<Observation[]>(`/patients/${patientId}/labs`, params),
  get: (id: string) => get<Observation>(`/observations/${id}`),
  create: (body: Record<string, unknown>) => post<Observation>("/observations", body),
  resultLab: (id: string, body: Record<string, unknown>) => post<Observation>(`/labs/${id}/result`, body),
  listReports: (patientId: string, params?: { limit?: number; offset?: number }) =>
    get<DiagnosticReport[]>(`/patients/${patientId}/diagnostic-reports`, params),
  getReport: (id: string) => get<DiagnosticReport>(`/diagnostic-reports/${id}`),
};

// ---------------------------------------------------------------------------
// Medications
// ---------------------------------------------------------------------------

export const medicationsApi = {
  listForPatient: (patientId: string, params?: { status?: string; category?: string }) =>
    get<Medication[]>(`/patients/${patientId}/medications`, params),
  get: (id: string) => get<Medication>(`/medications/${id}`),
  create: (body: Record<string, unknown>) => post<Medication>("/medications", body),
  update: (id: string, body: Record<string, unknown>) => patch<Medication>(`/medications/${id}`, body),
};

// ---------------------------------------------------------------------------
// Notes
// ---------------------------------------------------------------------------

export const notesApi = {
  listForPatient: (patientId: string, params?: { note_type?: string; status?: string }) =>
    get<Note[]>(`/patients/${patientId}/notes`, params),
  get: (id: string) => get<Note>(`/notes/${id}`),
  create: (body: Record<string, unknown>) => post<Note>("/notes", body),
  update: (id: string, body: Record<string, unknown>) => patch<Note>(`/notes/${id}`, body),
  sign: (id: string, signedBy: string) => post<Note>(`/notes/${id}/sign`, undefined, { signed_by: signedBy }),
};

// ---------------------------------------------------------------------------
// Orders
// ---------------------------------------------------------------------------

export const ordersApi = {
  list: (params?: { patient_id?: string; status?: string; order_type?: string; limit?: number; offset?: number }) =>
    get<Order[]>("/orders", params),
  get: (id: string) => get<Order>(`/orders/${id}`),
  create: (body: Record<string, unknown>) => post<Order>("/orders", body),
  update: (id: string, body: Record<string, unknown>) => patch<Order>(`/orders/${id}`, body),
  sign: (id: string, signedBy: string) => post<Order>(`/orders/${id}/sign`, { signed_by: signedBy }),
  complete: (id: string) => post<Order>(`/orders/${id}/complete`),
  cancel: (id: string) => post<Order>(`/orders/${id}/cancel`),
};

// ---------------------------------------------------------------------------
// Disposition assessments + facilities
// ---------------------------------------------------------------------------

export const dispoApi = {
  listForPatient: (patientId: string) => get<DispoAssessment[]>(`/patients/${patientId}/dispo-assessments`),
  current: (patientId: string) => get<DispoAssessment | null>(`/patients/${patientId}/dispo-assessments/current`),
  create: (body: Record<string, unknown>) => post<DispoAssessment>("/dispo-assessments", body),
};

export const facilitiesApi = {
  list: (params?: {
    facility_type?: string;
    state?: string;
    has_available_beds?: boolean;
    accepts_covid_positive?: boolean;
  }) => get<Facility[]>("/facilities", params),
  get: (id: string) => get<Facility>(`/facilities/${id}`),
  create: (body: Record<string, unknown>) => post<Facility>("/facilities", body),
  update: (id: string, body: Record<string, unknown>) => patch<Facility>(`/facilities/${id}`, body),
};

// ---------------------------------------------------------------------------
// Care tasks + communications
// ---------------------------------------------------------------------------

export const careTasksApi = {
  list: (params?: {
    patient_id?: string;
    status?: string;
    task_type?: string;
    assigned_to?: string;
    limit?: number;
    offset?: number;
  }) => get<CareTask[]>("/care-tasks", params),
  get: (id: string) => get<CareTask>(`/care-tasks/${id}`),
  create: (body: Record<string, unknown>) => post<CareTask>("/care-tasks", body),
  update: (id: string, body: Record<string, unknown>) => patch<CareTask>(`/care-tasks/${id}`, body),
};

export const communicationsApi = {
  list: (params?: { patient_id?: string; care_task_id?: string; facility_id?: string; limit?: number; offset?: number }) =>
    get<Communication[]>("/communications", params),
  get: (id: string) => get<Communication>(`/communications/${id}`),
  create: (body: Record<string, unknown>) => post<Communication>("/communications", body),
};

// ---------------------------------------------------------------------------
// Placer chat (provider <-> Placer messages, per patient)
// ---------------------------------------------------------------------------

export const placerApi = {
  listMessages: (patientId: string, params?: { limit?: number; offset?: number }) =>
    get<PlacerMessage[]>(`/patients/${patientId}/placer/messages`, params),
  sendMessage: (
    patientId: string,
    body: { sender?: "provider" | "placer"; sender_name?: string; text: string },
  ) => post<PlacerMessage>(`/patients/${patientId}/placer/messages`, body),
};

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------

export const adminApi = {
  health: () => get<{ status: string; service: string; version: string }>("/admin/health"),
  stats: () => get<AdminStats>("/admin/stats"),
  reset: () => post<{ status: string; row_counts: AdminStats }>("/admin/reset"),
};
