import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { usePatientChart } from "../PatientDetailPage";
import { careTasksApi } from "../../lib/api";
import { Badge, Button, CenteredSpinner, EmptyState, ErrorState, Table, Td, Th, Tr } from "../../components/ui";
import { Field, FormGrid, Select, TextArea, TextInput } from "../../components/form";
import { Modal } from "../../components/Modal";
import { formatDateTime, priorityVariant, statusVariant } from "../../lib/format";
import { LABELS, TASK_PRIORITY, TASK_STATUS, TASK_TYPE, humanize } from "../../lib/enums";
import { errorMessage, useToast } from "../../lib/toast";
import type { CareTask } from "../../lib/types";

export default function TasksTab() {
  const { patientId } = usePatientChart();
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<CareTask | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["care-tasks", patientId],
    queryFn: () => careTasksApi.list({ patient_id: patientId }),
  });

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus size={13} /> New task
        </Button>
      </div>

      {isLoading && <CenteredSpinner />}
      {isError && <ErrorState message={errorMessage(error)} />}
      {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No care tasks" />}
      {!isLoading && !isError && data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Task</Th>
              <Th>Type</Th>
              <Th>Priority</Th>
              <Th>Status</Th>
              <Th>Assigned to</Th>
              <Th>Due</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {data.map((t) => (
              <Tr key={t.id} onClick={() => setEditing(t)}>
                <Td className="font-medium">{t.title}</Td>
                <Td>{LABELS.taskType[t.task_type] ?? t.task_type}</Td>
                <Td><Badge variant={priorityVariant(t.priority)}>{t.priority}</Badge></Td>
                <Td><Badge variant={statusVariant(t.status)}>{humanize(t.status)}</Badge></Td>
                <Td>{t.assigned_to ?? "—"}</Td>
                <Td>{t.due_at ? formatDateTime(t.due_at) : "—"}</Td>
                <Td />
              </Tr>
            ))}
          </tbody>
        </Table>
      )}

      <CreateTaskModal patientId={patientId} open={createOpen} onClose={() => setCreateOpen(false)} />
      {editing && <EditTaskModal task={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function CreateTaskModal({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ task_type: "call_snf", title: "", description: "", priority: "medium", assigned_to: "" });

  const mutation = useMutation({
    mutationFn: () => careTasksApi.create({ patient_id: patientId, ...form }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["care-tasks", patientId] });
      qc.invalidateQueries({ queryKey: ["chart", patientId] });
      qc.invalidateQueries({ queryKey: ["all-care-tasks"] });
      toast.success("Task created");
      onClose();
      setForm({ task_type: "call_snf", title: "", description: "", priority: "medium", assigned_to: "" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="New care task">
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Field label="Title" required>
          <TextInput value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Call Riverside SNF re: bed availability" required />
        </Field>
        <FormGrid>
          <Field label="Type" required>
            <Select options={TASK_TYPE} value={form.task_type} onChange={(e) => setForm({ ...form, task_type: e.target.value })} />
          </Field>
          <Field label="Priority">
            <Select options={TASK_PRIORITY} value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
          </Field>
        </FormGrid>
        <Field label="Description">
          <TextArea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="Assigned to">
          <TextInput value={form.assigned_to} onChange={(e) => setForm({ ...form, assigned_to: e.target.value })} placeholder="Agent or human name" />
        </Field>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Create task</Button>
        </div>
      </form>
    </Modal>
  );
}

function EditTaskModal({ task, onClose }: { task: CareTask; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [status, setStatus] = useState(task.status);
  const [resultSummary, setResultSummary] = useState(task.result_summary ?? "");

  const mutation = useMutation({
    mutationFn: () => careTasksApi.update(task.id, { status, result_summary: resultSummary || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["care-tasks", task.patient_id] });
      qc.invalidateQueries({ queryKey: ["chart", task.patient_id] });
      qc.invalidateQueries({ queryKey: ["all-care-tasks"] });
      toast.success("Task updated");
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open onClose={onClose} title={task.title}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        {task.description && <p className="text-[12.5px] text-text-secondary">{task.description}</p>}
        <Field label="Status">
          <Select options={TASK_STATUS} value={status} onChange={(e) => setStatus(e.target.value)} />
        </Field>
        <Field label="Result summary" hint="Outcome of the call/action, e.g. 'bed available, holding for 24h'">
          <TextArea value={resultSummary} onChange={(e) => setResultSummary(e.target.value)} />
        </Field>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Save</Button>
        </div>
      </form>
    </Modal>
  );
}
