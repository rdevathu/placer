// Thin typed fetch client over the Placer agent engine API (separate service
// from the Iliad EHR backend). Only the Placer tab imports this module.
//
// The engine may be down while the rest of Iliad works — callers should treat
// errors here as "engine offline" and degrade gracefully.

export const ENGINE_BASE_URL: string =
  (import.meta.env.VITE_PLACER_ENGINE_URL as string | undefined) ?? "http://localhost:8001";

export class EngineError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "EngineError";
    this.status = status;
    this.detail = detail;
  }
}

// --- Types (mirrors the engine's /cases and /cases/{id}/board payloads) -----

export interface EnginePathway {
  pathway_id: number;
  confidence: number;
  name?: string | null;
}

export interface EngineCase {
  id: string;
  patient_id: string;
  state: string;
  active_pathways: EnginePathway[];
  counts?: Record<string, unknown>;
}

export interface ReadinessDimension {
  clear: boolean;
  open_count: number;
}

export interface EngineReadiness {
  dimensions: Record<string, ReadinessDimension>;
  green: boolean;
}

export interface EngineBarrier {
  id: string;
  btype: string;
  dimension?: string;
  status: string;
  description?: string | null;
}

export interface EngineTask {
  id: string;
  title: string;
  task_type?: string | null;
  mode?: string | null;
  action_id?: string | null;
}

export interface EngineReferral {
  id: string;
  facility_name: string;
  pathway_id?: number | null;
  status: string;
  denial_reason?: string | null;
}

export interface EngineApproval {
  id: string;
  kind?: string | null;
  prompt: string;
  status: string;
}

export interface EngineBoard {
  id: string;
  patient_id: string;
  state: string;
  brief?: string | null;
  active_pathways: EnginePathway[];
  readiness: EngineReadiness;
  barriers: Record<string, EngineBarrier[]>;
  tasks: Record<string, EngineTask[]>;
  referrals: EngineReferral[];
  approvals: EngineApproval[];
  messages: unknown[];
}

// --- Request helper ---------------------------------------------------------

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${ENGINE_BASE_URL}${path}`, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail: unknown;
    try {
      detail = await res.json();
    } catch {
      detail = undefined;
    }
    const message =
      (detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : undefined) ?? `${method} ${path} failed with ${res.status}`;
    throw new EngineError(res.status, message, detail);
  }

  return (await res.json()) as T;
}

const get = <T,>(path: string) => request<T>("GET", path);
const post = <T,>(path: string, body?: unknown) => request<T>("POST", path, body ?? {});

// --- Endpoints --------------------------------------------------------------

const RESOLVED_BY = "provider";

export const placerEngineApi = {
  listCases: () => get<EngineCase[]>("/cases"),

  /** Resolve the engine case for a given Iliad patient, or null if none. */
  caseForPatient: async (patientId: string): Promise<EngineCase | null> => {
    const cases = await get<EngineCase[]>("/cases");
    return cases.find((c) => c.patient_id === patientId) ?? null;
  },

  board: (caseId: string) => get<EngineBoard>(`/cases/${caseId}/board`),

  approve: (approvalId: string) =>
    post(`/chat/approvals/${approvalId}/approve`, { resolved_by: RESOLVED_BY }),
  reject: (approvalId: string) =>
    post(`/chat/approvals/${approvalId}/reject`, { resolved_by: RESOLVED_BY }),

  commit: (caseId: string, pathwayId: number) =>
    post(`/cases/${caseId}/commit`, { pathway_id: pathwayId, resolved_by: RESOLVED_BY }),

  clearBarrier: (caseId: string, barrierId: string, note?: string) =>
    post(`/cases/${caseId}/barriers/${barrierId}/clear`, {
      resolved_by: RESOLVED_BY,
      note: note || undefined,
    }),
};
