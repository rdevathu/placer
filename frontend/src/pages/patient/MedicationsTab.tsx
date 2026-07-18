import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { usePatientChart } from "../PatientDetailPage";
import { medicationsApi } from "../../lib/api";
import { Badge, Button, CenteredSpinner, EmptyState, ErrorState, Table, Td, Th, Tr } from "../../components/ui";
import { Field, FormGrid, Select, TextInput } from "../../components/form";
import { Modal } from "../../components/Modal";
import { formatDate, statusVariant } from "../../lib/format";
import { MEDICATION_STATUS } from "../../lib/enums";
import { errorMessage, useToast } from "../../lib/toast";

export default function MedicationsTab() {
  const { patientId } = usePatientChart();
  const [createOpen, setCreateOpen] = useState(false);
  const qc = useQueryClient();
  const toast = useToast();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["medications", patientId],
    queryFn: () => medicationsApi.listForPatient(patientId),
  });

  const stopMutation = useMutation({
    mutationFn: (id: string) => medicationsApi.update(id, { status: "stopped" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["medications", patientId] });
      qc.invalidateQueries({ queryKey: ["chart", patientId] });
      toast.success("Medication stopped");
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus size={13} /> Add medication
        </Button>
      </div>

      {isLoading && <CenteredSpinner />}
      {isError && <ErrorState message={errorMessage(error)} />}
      {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No medications recorded" />}
      {!isLoading && !isError && data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Medication</Th>
              <Th>Dose</Th>
              <Th>Route</Th>
              <Th>Frequency</Th>
              <Th>Status</Th>
              <Th>Authored</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {data.map((m) => (
              <Tr key={m.id}>
                <Td className="font-medium">{m.display ?? "—"}</Td>
                <Td>{m.dose ?? "—"}</Td>
                <Td>{m.route ?? "—"}</Td>
                <Td>{m.frequency ?? "—"}</Td>
                <Td><Badge variant={statusVariant(m.status)}>{m.status}</Badge></Td>
                <Td>{formatDate(m.authored_on)}</Td>
                <Td>
                  {m.status === "active" && (
                    <Button size="sm" variant="ghost" loading={stopMutation.isPending} onClick={() => stopMutation.mutate(m.id)}>
                      Stop
                    </Button>
                  )}
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}

      <CreateMedicationModal patientId={patientId} open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}

function CreateMedicationModal({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ display: "", dose: "", route: "", frequency: "", status: "active", category: "inpatient" });

  const mutation = useMutation({
    mutationFn: () => medicationsApi.create({ patient_id: patientId, ...form }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["medications", patientId] });
      qc.invalidateQueries({ queryKey: ["chart", patientId] });
      toast.success("Medication added");
      onClose();
      setForm({ display: "", dose: "", route: "", frequency: "", status: "active", category: "inpatient" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Add medication">
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Field label="Drug name" required>
          <TextInput value={form.display} onChange={(e) => setForm({ ...form, display: e.target.value })} placeholder="e.g. Atorvastatin" required />
        </Field>
        <FormGrid>
          <Field label="Dose">
            <TextInput value={form.dose} onChange={(e) => setForm({ ...form, dose: e.target.value })} placeholder="40 mg" />
          </Field>
          <Field label="Route">
            <TextInput value={form.route} onChange={(e) => setForm({ ...form, route: e.target.value })} placeholder="PO" />
          </Field>
        </FormGrid>
        <FormGrid>
          <Field label="Frequency">
            <TextInput value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })} placeholder="Daily" />
          </Field>
          <Field label="Status">
            <Select options={MEDICATION_STATUS} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} />
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
