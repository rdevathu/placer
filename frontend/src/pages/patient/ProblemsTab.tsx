import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { usePatientChart } from "../PatientDetailPage";
import { conditionsApi } from "../../lib/api";
import { Badge, Button, CenteredSpinner, EmptyState, ErrorState, Table, Td, Th, Tr } from "../../components/ui";
import { Field, FormGrid, Select, TextInput } from "../../components/form";
import { Modal } from "../../components/Modal";
import { formatDate, statusVariant } from "../../lib/format";
import { CLINICAL_STATUS, CONDITION_CATEGORY, LABELS } from "../../lib/enums";
import { errorMessage, useToast } from "../../lib/toast";

export default function ProblemsTab() {
  const { patientId } = usePatientChart();
  const [createOpen, setCreateOpen] = useState(false);
  const qc = useQueryClient();
  const toast = useToast();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["conditions", patientId],
    queryFn: () => conditionsApi.listForPatient(patientId),
  });

  const resolveMutation = useMutation({
    mutationFn: (id: string) => conditionsApi.update(id, { clinical_status: "resolved" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conditions", patientId] });
      qc.invalidateQueries({ queryKey: ["chart", patientId] });
      toast.success("Problem resolved");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus size={13} /> Add problem
        </Button>
      </div>

      {isLoading && <CenteredSpinner />}
      {isError && <ErrorState message={errorMessage(error)} />}
      {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No problems recorded" />}
      {!isLoading && !isError && data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Problem</Th>
              <Th>Category</Th>
              <Th>Status</Th>
              <Th>Recorded</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {data.map((c) => (
              <Tr key={c.id}>
                <Td className="font-medium">{c.display ?? c.code ?? "—"}</Td>
                <Td>{c.category ? LABELS.conditionCategory[c.category] ?? c.category : "—"}</Td>
                <Td><Badge variant={statusVariant(c.clinical_status)}>{c.clinical_status ? LABELS.clinicalStatus[c.clinical_status] ?? c.clinical_status : "—"}</Badge></Td>
                <Td>{formatDate(c.recorded_date)}</Td>
                <Td>
                  {c.clinical_status === "active" && (
                    <Button size="sm" variant="ghost" loading={resolveMutation.isPending} onClick={() => resolveMutation.mutate(c.id)}>
                      Resolve
                    </Button>
                  )}
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}

      <CreateProblemModal patientId={patientId} open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}

function CreateProblemModal({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ display: "", category: "problem-list-item", clinical_status: "active" });

  const mutation = useMutation({
    mutationFn: () => conditionsApi.create({ patient_id: patientId, ...form }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conditions", patientId] });
      qc.invalidateQueries({ queryKey: ["chart", patientId] });
      toast.success("Problem added");
      onClose();
      setForm({ display: "", category: "problem-list-item", clinical_status: "active" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Add problem">
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Field label="Problem" required>
          <TextInput value={form.display} onChange={(e) => setForm({ ...form, display: e.target.value })} placeholder="e.g. Acute ischemic stroke" required />
        </Field>
        <FormGrid>
          <Field label="Category">
            <Select options={CONDITION_CATEGORY} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
          </Field>
          <Field label="Clinical status">
            <Select options={CLINICAL_STATUS} value={form.clinical_status} onChange={(e) => setForm({ ...form, clinical_status: e.target.value })} />
          </Field>
        </FormGrid>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Add</Button>
        </div>
      </form>
    </Modal>
  );
}
