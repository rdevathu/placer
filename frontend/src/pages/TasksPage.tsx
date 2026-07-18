import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { careTasksApi, patientsApi } from "../lib/api";
import { Badge, CenteredSpinner, EmptyState, ErrorState, PageHeader, Table, Td, Th, Tr } from "../components/ui";
import { Select } from "../components/form";
import { LABELS, TASK_STATUS, TASK_TYPE, humanize } from "../lib/enums";
import { formatDateTime, priorityVariant, statusVariant, patientDisplayName } from "../lib/format";
import { errorMessage } from "../lib/toast";

export default function TasksPage() {
  const [status, setStatus] = useState("pending");
  const [taskType, setTaskType] = useState("");
  const navigate = useNavigate();

  const tasksQuery = useQuery({
    queryKey: ["all-care-tasks", status, taskType],
    queryFn: () => careTasksApi.list({ status: status || undefined, task_type: taskType || undefined, limit: 300 }),
  });

  const patientsQuery = useQuery({
    queryKey: ["patients-lookup"],
    queryFn: () => patientsApi.list({ limit: 500 }),
  });

  const patientMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const p of patientsQuery.data ?? []) map.set(p.id, patientDisplayName(p));
    return map;
  }, [patientsQuery.data]);

  const isLoading = tasksQuery.isLoading || patientsQuery.isLoading;

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Care tasks" subtitle="The disposition-planning worklist across all patients" />

      <div className="flex items-center gap-3 border-b border-border px-5 py-2.5">
        <Select options={TASK_STATUS} placeholder="Any status" value={status} onChange={(e) => setStatus(e.target.value)} className="w-40" />
        <Select options={TASK_TYPE} placeholder="Any type" value={taskType} onChange={(e) => setTaskType(e.target.value)} className="w-48" />
        <span className="ml-auto text-[11.5px] text-text-tertiary">{tasksQuery.data?.length ?? 0} tasks</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && <CenteredSpinner />}
        {tasksQuery.isError && <ErrorState message={errorMessage(tasksQuery.error)} />}
        {!isLoading && tasksQuery.data && tasksQuery.data.length === 0 && <EmptyState title="No tasks match this filter" />}
        {!isLoading && tasksQuery.data && tasksQuery.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Task</Th>
                <Th>Patient</Th>
                <Th>Type</Th>
                <Th>Priority</Th>
                <Th>Status</Th>
                <Th>Assigned to</Th>
                <Th>Due</Th>
              </tr>
            </thead>
            <tbody>
              {tasksQuery.data.map((t) => (
                <Tr key={t.id} onClick={() => navigate(`/patients/${t.patient_id}/tasks`)}>
                  <Td className="font-medium">{t.title}</Td>
                  <Td>{patientMap.get(t.patient_id) ?? t.patient_id}</Td>
                  <Td>{LABELS.taskType[t.task_type] ?? t.task_type}</Td>
                  <Td><Badge variant={priorityVariant(t.priority)}>{t.priority}</Badge></Td>
                  <Td><Badge variant={statusVariant(t.status)}>{humanize(t.status)}</Badge></Td>
                  <Td>{t.assigned_to ?? "—"}</Td>
                  <Td>{t.due_at ? formatDateTime(t.due_at) : "—"}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>
    </div>
  );
}
