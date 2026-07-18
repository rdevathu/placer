import { format, formatDistanceToNow, isValid, parseISO } from "date-fns";
import type { BadgeVariant } from "../components/ui";

export function formatDate(value?: string | null, pattern = "MMM d, yyyy"): string {
  if (!value) return "—";
  const d = parseISO(value);
  if (!isValid(d)) return "—";
  return format(d, pattern);
}

export function formatDateTime(value?: string | null): string {
  return formatDate(value, "MMM d, yyyy h:mm a");
}

export function formatRelative(value?: string | null): string {
  if (!value) return "—";
  const d = parseISO(value);
  if (!isValid(d)) return "—";
  return formatDistanceToNow(d, { addSuffix: true });
}

export function patientDisplayName(p: { full_name?: string | null; given_name?: string | null; family_name?: string | null }): string {
  return p.full_name || [p.given_name, p.family_name].filter(Boolean).join(" ") || "Unnamed patient";
}

// --- status -> badge variant mappings --------------------------------------

const successStatuses = new Set(["final", "signed", "completed", "resolved", "active", "ready", "discharged"]);
const warningStatuses = new Set(["pending", "draft", "in_progress", "in-progress", "predicted", "preliminary", "blocked", "on-hold"]);
const dangerStatuses = new Set(["cancelled", "critical", "discontinued", "expired", "ama"]);
const accentStatuses = new Set(["decided", "amended"]);

export function statusVariant(status?: string | null): BadgeVariant {
  if (!status) return "neutral";
  const s = status.toLowerCase();
  if (dangerStatuses.has(s)) return "danger";
  if (warningStatuses.has(s)) return "warning";
  if (successStatuses.has(s)) return "success";
  if (accentStatuses.has(s)) return "accent";
  return "neutral";
}

export function priorityVariant(priority?: string | null): BadgeVariant {
  const p = (priority || "").toLowerCase();
  if (p === "stat" || p === "high") return "danger";
  if (p === "urgent" || p === "medium") return "warning";
  return "neutral";
}

export function abnormalVariant(flag?: string | null): BadgeVariant {
  if (!flag || flag === "N") return "neutral";
  if (flag === "critical") return "danger";
  return "warning";
}
