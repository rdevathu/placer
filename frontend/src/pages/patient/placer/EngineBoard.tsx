// Placer engine control surface: everything the physician needs to drive a
// disposition case (status, decision, approvals, tasks, barriers, referrals)
// without ever leaving this tab. Backed by the standalone Placer engine
// (see lib/placerEngine.ts) and polled so async agent work surfaces live.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { CheckCircle2, CircleDashed, PhoneOff, WifiOff } from "lucide-react";
import { usePatientChart } from "../../PatientDetailPage";
import {
  placerEngineApi,
  type EngineApproval,
  type EngineBarrier,
  type EngineBoard,
  type EnginePathway,
  type EngineTask,
} from "../../../lib/placerEngine";
import {
  Badge,
  type BadgeVariant,
  Button,
  Card,
  CardHeader,
  CenteredSpinner,
  EmptyState,
  SectionLabel,
} from "../../../components/ui";
import { humanize } from "../../../lib/enums";
import { errorMessage, useToast } from "../../../lib/toast";

// Fixed display order + short labels for the 7 readiness dimensions.
const DIMENSIONS: { key: string; label: string }[] = [
  { key: "medical", label: "Medical" },
  { key: "clinical_docs", label: "Docs" },
  { key: "decision", label: "Decision" },
  { key: "payer", label: "Payer" },
  { key: "destination", label: "Destination" },
  { key: "home_logistics", label: "Home" },
  { key: "transport", label: "Transport" },
];

const dimensionLabel = (key: string) =>
  DIMENSIONS.find((d) => d.key === key)?.label ?? humanize(key);

function stateVariant(state: string): BadgeVariant {
  switch (state) {
    case "predicted":
      return "warning";
    case "committed":
      return "accent";
    default:
      return "neutral";
  }
}

// A task that would go out over the phone — telephony isn't wired up yet, so
// we label these honestly instead of implying a call is in flight.
const isTelephonyTask = (t: EngineTask) =>
  (t.task_type ?? "").includes("call") || (t.task_type ?? "").includes("phone");

const BOARD_QUERY_KEY = "placer-engine-board";

export function EngineBoardPanel() {
  const { patientId } = usePatientChart();

  const caseQuery = useQuery({
    queryKey: ["placer-engine-case", patientId],
    queryFn: () => placerEngineApi.caseForPatient(patientId),
    refetchInterval: 5000,
    retry: false,
  });
  const caseId = caseQuery.data?.id;

  const boardQuery = useQuery({
    queryKey: [BOARD_QUERY_KEY, caseId],
    queryFn: () => placerEngineApi.board(caseId as string),
    enabled: Boolean(caseId),
    refetchInterval: 3000,
    retry: false,
  });

  const offline = caseQuery.isError || boardQuery.isError;
  const board = boardQuery.data;

  return (
    <div className="flex flex-col gap-6">
      {offline && <OfflineBanner />}

      {caseQuery.isLoading && <CenteredSpinner />}

      {!caseQuery.isLoading && !caseQuery.isError && caseQuery.data === null && (
        <EmptyState
          title="No Placer case for this patient"
          hint="Placer hasn't opened a disposition case on this admission yet."
        />
      )}

      {caseId && boardQuery.isLoading && !board && <CenteredSpinner />}

      {board && caseId && (
        <>
          <StatusHeader board={board} />
          {board.state === "predicted" && <DecisionCard caseId={caseId} board={board} />}
          <ApprovalsSection approvals={board.approvals} />
          <TasksSection tasks={board.tasks} />
          <BarriersSection caseId={caseId} barriers={board.barriers} />
          <ReferralsSection board={board} />
        </>
      )}
    </div>
  );
}

function OfflineBanner() {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-warning/40 bg-warning-soft px-3 py-2">
      <WifiOff size={14} className="shrink-0 text-warning" />
      <p className="text-[12px] text-text-secondary">
        <span className="font-medium text-warning">Placer engine offline</span> — live case data is
        unavailable. Chat still works.
      </p>
    </div>
  );
}

// --- 1. Status header -------------------------------------------------------

function StatusHeader({ board }: { board: EngineBoard }) {
  const green = board.readiness?.green ?? false;

  return (
    <Card className={clsx("p-4", green && "border-success/50 bg-success-soft")}>
      <div className="flex flex-wrap items-center gap-2">
        {green ? (
          <span className="inline-flex items-center gap-1.5 rounded-md bg-success px-2 py-1 text-[12px] font-semibold text-white">
            <CheckCircle2 size={14} /> GREEN — ready for discharge
          </span>
        ) : (
          <Badge variant={stateVariant(board.state)}>{humanize(board.state)}</Badge>
        )}
        {board.active_pathways.map((p) => (
          <span key={p.pathway_id} className="text-[12.5px] font-medium text-text">
            {p.name ?? `Pathway ${p.pathway_id}`}
            <span className="ml-1 font-normal text-text-tertiary">
              {Math.round(p.confidence * 100)}%
            </span>
          </span>
        ))}
      </div>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
        {DIMENSIONS.map(({ key, label }) => {
          const dim = board.readiness?.dimensions?.[key];
          const clear = dim?.clear ?? false;
          return (
            <span key={key} className="inline-flex items-center gap-1.5 text-[11.5px]">
              <span
                className={clsx("h-2 w-2 rounded-full", clear ? "bg-success" : "bg-warning")}
              />
              <span className={clear ? "text-text-tertiary" : "font-medium text-text-secondary"}>
                {label}
              </span>
              {!clear && dim && dim.open_count > 0 && (
                <span className="text-[10.5px] font-medium text-warning">{dim.open_count}</span>
              )}
            </span>
          );
        })}
      </div>

      {board.brief && (
        <p className="mt-3 border-t border-border pt-3 text-[12px] leading-relaxed text-text-secondary">
          {board.brief}
        </p>
      )}
    </Card>
  );
}

// --- 2. Decision card (commit a pathway) ------------------------------------

function DecisionCard({ caseId, board }: { caseId: string; board: EngineBoard }) {
  const qc = useQueryClient();
  const toast = useToast();

  const mutation = useMutation({
    mutationFn: (pathwayId: number) => placerEngineApi.commit(caseId, pathwayId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARD_QUERY_KEY] });
      qc.invalidateQueries({ queryKey: ["placer-engine-case"] });
      toast.success("Pathway committed");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Card className="border-accent/50">
      <CardHeader
        title="Decision needed"
        subtitle="Placer has a predicted pathway — commit to start placement work"
      />
      <div className="flex flex-col gap-2 p-4">
        {board.active_pathways.map((p: EnginePathway) => (
          <div key={p.pathway_id} className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[12.5px] font-medium text-text">
                {p.name ?? `Pathway ${p.pathway_id}`}
              </p>
              <p className="text-[11.5px] text-text-tertiary">
                {Math.round(p.confidence * 100)}% confidence
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              loading={mutation.isPending && mutation.variables === p.pathway_id}
              disabled={mutation.isPending}
              onClick={() => mutation.mutate(p.pathway_id)}
            >
              Commit
            </Button>
          </div>
        ))}
      </div>
    </Card>
  );
}

// --- 3. Approvals + tasks ---------------------------------------------------

function ApprovalsSection({ approvals }: { approvals: EngineApproval[] }) {
  const qc = useQueryClient();
  const toast = useToast();
  const pending = approvals.filter((a) => a.status === "pending");

  const mutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" }) =>
      action === "approve" ? placerEngineApi.approve(id) : placerEngineApi.reject(id),
    onSuccess: (_data, { action }) => {
      qc.invalidateQueries({ queryKey: [BOARD_QUERY_KEY] });
      toast.success(action === "approve" ? "Approved" : "Dismissed");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  if (pending.length === 0) return null;

  return (
    <section>
      <SectionLabel>Needs your approval</SectionLabel>
      <div className="flex flex-col gap-3">
        {pending.map((a) => (
          <Card key={a.id} className="border-warning/40 p-4">
            <div className="flex items-center gap-2">
              <Badge variant="warning">{humanize(a.kind ?? "approval")}</Badge>
            </div>
            <p className="mt-2 whitespace-pre-wrap text-[12.5px] leading-relaxed text-text">
              {a.prompt}
            </p>
            <div className="mt-3 flex gap-2">
              <Button
                variant="primary"
                size="sm"
                loading={mutation.isPending && mutation.variables?.id === a.id && mutation.variables?.action === "approve"}
                disabled={mutation.isPending}
                onClick={() => mutation.mutate({ id: a.id, action: "approve" })}
              >
                Approve
              </Button>
              <Button
                variant="ghost"
                size="sm"
                loading={mutation.isPending && mutation.variables?.id === a.id && mutation.variables?.action === "reject"}
                disabled={mutation.isPending}
                onClick={() => mutation.mutate({ id: a.id, action: "reject" })}
              >
                Dismiss
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </section>
  );
}

// Task groups worth surfacing, in worklist order, with honest status labels.
const TASK_GROUPS: { key: string; label: string; variant: BadgeVariant }[] = [
  { key: "suggested", label: "Suggested", variant: "neutral" },
  { key: "pending", label: "Pending", variant: "warning" },
  { key: "approved", label: "Approved", variant: "accent" },
  { key: "in_progress", label: "In progress", variant: "warning" },
  { key: "waiting", label: "Waiting", variant: "neutral" },
];

function TasksSection({ tasks }: { tasks: Record<string, EngineTask[]> }) {
  const visible = TASK_GROUPS.filter((g) => (tasks[g.key] ?? []).length > 0);
  const doneCount = (tasks["done"] ?? []).length;

  if (visible.length === 0 && doneCount === 0) return null;

  return (
    <section>
      <SectionLabel>Placer worklist</SectionLabel>
      <Card>
        {visible.length === 0 && (
          <p className="px-4 py-3 text-[12px] text-text-tertiary">No active tasks.</p>
        )}
        <div className="flex flex-col divide-y divide-border">
          {visible.flatMap((g) =>
            (tasks[g.key] ?? []).map((t) => {
              const waitingOnPhone = g.key === "waiting" && isTelephonyTask(t);
              return (
                <div key={t.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate text-[12.5px] text-text">{t.title}</p>
                    {t.task_type && (
                      <p className="text-[11px] text-text-tertiary">{humanize(t.task_type)}</p>
                    )}
                  </div>
                  {waitingOnPhone ? (
                    <span className="inline-flex shrink-0 items-center gap-1 text-[11px] text-text-tertiary">
                      <PhoneOff size={12} /> waiting — calling not yet enabled
                    </span>
                  ) : (
                    <Badge variant={g.variant} className="shrink-0">
                      {g.label}
                    </Badge>
                  )}
                </div>
              );
            }),
          )}
        </div>
        {doneCount > 0 && (
          <p className="border-t border-border px-4 py-2 text-[11px] text-text-tertiary">
            {doneCount} task{doneCount === 1 ? "" : "s"} completed
          </p>
        )}
      </Card>
    </section>
  );
}

// --- 4. Barriers ------------------------------------------------------------

function barrierVariant(status: string): BadgeVariant {
  if (status === "open") return "warning";
  if (status === "resolved" || status === "cleared") return "success";
  return "neutral";
}

function BarriersSection({
  caseId,
  barriers,
}: {
  caseId: string;
  barriers: Record<string, EngineBarrier[]>;
}) {
  const qc = useQueryClient();
  const toast = useToast();

  const mutation = useMutation({
    mutationFn: ({ barrierId, note }: { barrierId: string; note?: string }) =>
      placerEngineApi.clearBarrier(caseId, barrierId, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARD_QUERY_KEY] });
      toast.success("Barrier resolved");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const markResolved = (barrierId: string) => {
    const note = window.prompt("Resolution note (optional):");
    if (note === null) return; // cancelled
    mutation.mutate({ barrierId, note: note.trim() || undefined });
  };

  const dimensions = Object.entries(barriers).filter(([, list]) => list.length > 0);
  if (dimensions.length === 0) return null;

  return (
    <section>
      <SectionLabel>Barriers</SectionLabel>
      <div className="flex flex-col gap-4">
        {dimensions.map(([dimension, list]) => (
          <div key={dimension}>
            <div className="px-1 pb-1 text-[11px] font-medium text-text-tertiary">
              {dimensionLabel(dimension)} · {list.length}
            </div>
            <Card className="flex flex-col divide-y divide-border">
              {list.map((b) => (
                <div key={b.id} className="flex items-start justify-between gap-3 px-4 py-2.5">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge variant={barrierVariant(b.status)}>{humanize(b.status)}</Badge>
                      <span className="text-[11px] text-text-tertiary">{humanize(b.btype)}</span>
                    </div>
                    {b.description && (
                      <p className="mt-1 text-[12.5px] leading-relaxed text-text-secondary">
                        {b.description}
                      </p>
                    )}
                  </div>
                  {b.status === "open" && (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="shrink-0"
                      disabled={mutation.isPending}
                      onClick={() => markResolved(b.id)}
                    >
                      Mark resolved
                    </Button>
                  )}
                </div>
              ))}
            </Card>
          </div>
        ))}
      </div>
    </section>
  );
}

// --- 5. Referrals -----------------------------------------------------------

function referralVariant(status: string): BadgeVariant {
  if (status === "accepted") return "success";
  if (status === "declined" || status === "denied") return "danger";
  if (status === "pending" || status === "sent") return "warning";
  return "neutral";
}

function ReferralsSection({ board }: { board: EngineBoard }) {
  if (board.referrals.length === 0) return null;

  return (
    <section>
      <SectionLabel>Referrals</SectionLabel>
      <Card className="flex flex-col divide-y divide-border">
        {board.referrals.map((r) => (
          <div key={r.id} className="flex items-start justify-between gap-3 px-4 py-2.5">
            <div className="min-w-0">
              <p className="flex items-center gap-1.5 text-[12.5px] font-medium text-text">
                <CircleDashed size={12} className="shrink-0 text-text-tertiary" />
                {r.facility_name}
              </p>
              {r.denial_reason && (
                <p className="mt-0.5 text-[11.5px] text-danger">{r.denial_reason}</p>
              )}
            </div>
            <Badge variant={referralVariant(r.status)} className="shrink-0">
              {humanize(r.status)}
            </Badge>
          </div>
        ))}
      </Card>
    </section>
  );
}
