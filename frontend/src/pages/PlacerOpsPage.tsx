import { useState } from "react";
import type { ComponentType } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Brain,
  CheckCircle2,
  ClipboardList,
  ListChecks,
  MessageSquare,
  PhoneCall,
  Users,
} from "lucide-react";
import { placerOpsApi } from "../lib/api";
import {
  Badge,
  Card,
  CenteredSpinner,
  EmptyState,
  ErrorState,
  PageHeader,
  SectionLabel,
  Table,
  Td,
  Th,
  Tr,
} from "../components/ui";
import { Select } from "../components/form";
import { DISPOSITION_TYPE, LABELS, humanize } from "../lib/enums";
import { formatRelative, statusVariant } from "../lib/format";
import { errorMessage } from "../lib/toast";
import type { ActivityEvent, PlacerOverview } from "../lib/types";

const POLL_MS = 5000;

const EVENT_TYPE_OPTIONS = [
  { value: "dispo_assessment", label: "Predictions" },
  { value: "care_task", label: "Task activity" },
  { value: "communication", label: "Calls & outreach" },
  { value: "chat_message", label: "Placer messages" },
];

const EVENT_ICON: Record<ActivityEvent["event_type"], ComponentType<{ size?: number; className?: string }>> = {
  dispo_assessment: Brain,
  care_task: ClipboardList,
  communication: PhoneCall,
  chat_message: MessageSquare,
};

export default function PlacerOpsPage() {
  const overviewQuery = useQuery({
    queryKey: ["placer-overview"],
    queryFn: placerOpsApi.overview,
    refetchInterval: POLL_MS,
  });

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Placer Ops"
        subtitle="Live view of what Placer is monitoring, working, and changing across every patient"
      />

      <div className="flex min-h-0 flex-1">
        <div className="flex-1 overflow-y-auto p-5">
          {overviewQuery.isLoading && <CenteredSpinner />}
          {overviewQuery.isError && <ErrorState message={errorMessage(overviewQuery.error)} />}
          {overviewQuery.data && <Overview overview={overviewQuery.data} />}
        </div>

        <ActivityFeed />
      </div>
    </div>
  );
}

function Overview({ overview }: { overview: PlacerOverview }) {
  const { counts, dispositions_current, patients } = overview;

  return (
    <>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <StatTile icon={Users} label="Monitored patients" value={counts.monitored_patients} />
        <StatTile icon={ListChecks} label="Open tasks" value={counts.open_tasks} />
        <StatTile
          icon={ClipboardList}
          label="Blocked tasks"
          value={counts.blocked_tasks}
          tone={counts.blocked_tasks > 0 ? "danger" : "neutral"}
        />
        <StatTile icon={PhoneCall} label="Calls logged" value={counts.communications_logged} />
        <StatTile icon={CheckCircle2} label="Tasks completed" value={counts.completed_tasks} tone="success" />
      </div>

      <div className="mt-5">
        <SectionLabel>Current predictions</SectionLabel>
        <div className="flex flex-wrap gap-2">
          {Object.keys(dispositions_current).length === 0 && (
            <span className="text-[12px] text-text-tertiary">No predictions posted yet.</span>
          )}
          {DISPOSITION_TYPE.filter((o) => dispositions_current[o.value]).map((o) => (
            <Badge key={o.value} variant="accent">
              {o.label} · {dispositions_current[o.value]}
            </Badge>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <SectionLabel>Patients Placer is working</SectionLabel>
        <Card>
          {patients.length === 0 ? (
            <EmptyState
              title="No patients under Placer's watch"
              hint="Predictions, tasks, or outreach will show up here once Placer starts working a patient."
            />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Patient</Th>
                  <Th>Current prediction</Th>
                  <Th>Open tasks</Th>
                  <Th>Calls</Th>
                  <Th>Last activity</Th>
                </tr>
              </thead>
              <tbody>
                {patients.map((p) => (
                  <Tr key={p.patient_id}>
                    <Td>
                      <Link to={`/patients/${p.patient_id}/placer`} className="font-medium text-text hover:underline">
                        {p.patient_name ?? p.mrn}
                      </Link>
                      <div className="text-[11px] text-text-tertiary">{p.mrn}</div>
                    </Td>
                    <Td>
                      {p.current_disposition ? (
                        <div className="flex items-center gap-1.5">
                          <Badge variant={p.current_disposition.is_current ? "accent" : "neutral"}>
                            {LABELS.dispositionType[p.current_disposition.predicted_disposition] ??
                              p.current_disposition.predicted_disposition}
                          </Badge>
                          {p.current_disposition.confidence != null && (
                            <span className="text-[11px] text-text-tertiary">
                              {Math.round(p.current_disposition.confidence * 100)}%
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-[12px] text-text-tertiary">No prediction yet</span>
                      )}
                    </Td>
                    <Td>
                      <div className="flex items-center gap-1.5">
                        <span>{p.open_tasks}</span>
                        {p.blocked_tasks > 0 && <Badge variant="danger">{p.blocked_tasks} blocked</Badge>}
                        {p.high_priority_open_tasks > 0 && <Badge variant="warning">{p.high_priority_open_tasks} high</Badge>}
                      </div>
                    </Td>
                    <Td>{p.communications_count}</Td>
                    <Td className="text-text-tertiary">{formatRelative(p.last_activity_at)}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      </div>
    </>
  );
}

function StatTile({
  icon: Icon,
  label,
  value,
  tone = "neutral",
}: {
  icon: ComponentType<{ size?: number; className?: string }>;
  label: string;
  value: number;
  tone?: "neutral" | "success" | "danger";
}) {
  const toneClass = tone === "success" ? "text-success" : tone === "danger" && value > 0 ? "text-danger" : "text-text";

  return (
    <Card className="flex items-center gap-3 px-4 py-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-bg-inset text-text-tertiary">
        <Icon size={15} />
      </div>
      <div className="min-w-0">
        <div className={`text-[19px] font-semibold leading-none tabular-nums ${toneClass}`}>{value}</div>
        <div className="mt-1 text-[11px] text-text-tertiary">{label}</div>
      </div>
    </Card>
  );
}

function ActivityFeed() {
  const [eventType, setEventType] = useState("");

  const activityQuery = useQuery({
    queryKey: ["placer-activity", eventType],
    queryFn: () => placerOpsApi.activity({ event_type: eventType || undefined, limit: 100 }),
    refetchInterval: POLL_MS,
  });

  return (
    <aside className="flex w-[380px] shrink-0 flex-col border-l border-border">
      <div className="border-b border-border px-4 py-2.5">
        <h3 className="text-[12.5px] font-semibold text-text">Live activity</h3>
        <p className="mt-0.5 text-[11px] text-text-tertiary">Newest first · refreshes every {POLL_MS / 1000}s</p>
      </div>
      <div className="border-b border-border px-4 py-2">
        <Select
          options={EVENT_TYPE_OPTIONS}
          placeholder="All activity"
          value={eventType}
          onChange={(e) => setEventType(e.target.value)}
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        {activityQuery.isLoading && <CenteredSpinner />}
        {activityQuery.isError && <ErrorState message={errorMessage(activityQuery.error)} />}
        {!activityQuery.isLoading &&
          !activityQuery.isError &&
          (!activityQuery.data || activityQuery.data.length === 0) && (
            <EmptyState
              title="No activity yet"
              hint="Placer's predictions, task updates, calls, and messages will appear here as they happen."
            />
          )}
        {activityQuery.data?.map((event) => (
          <ActivityRow key={event.id} event={event} />
        ))}
      </div>
    </aside>
  );
}

function ActivityRow({ event }: { event: ActivityEvent }) {
  const Icon = EVENT_ICON[event.event_type];
  return (
    <div className="flex gap-2.5 border-b border-border px-4 py-2.5 last:border-0">
      <div className="mt-0.5 shrink-0 text-text-tertiary">
        <Icon size={14} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <Link
            to={`/patients/${event.patient_id}/placer`}
            className="truncate text-[11.5px] font-medium text-text hover:underline"
          >
            {event.patient_name ?? event.patient_mrn ?? "Unknown patient"}
          </Link>
          <span className="shrink-0 text-[10.5px] text-text-tertiary">{formatRelative(event.occurred_at)}</span>
        </div>
        <p className="mt-0.5 text-[12px] text-text">{event.title}</p>
        {event.detail && <p className="mt-0.5 line-clamp-2 text-[11.5px] text-text-tertiary">{event.detail}</p>}
        {event.status && (
          <Badge variant={statusVariant(event.status)} className="mt-1">
            {humanize(event.status)}
          </Badge>
        )}
      </div>
    </div>
  );
}
