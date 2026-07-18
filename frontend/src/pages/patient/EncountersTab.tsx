import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { usePatientChart } from "../PatientDetailPage";
import { encountersApi } from "../../lib/api";
import { Badge, Button, CenteredSpinner, EmptyState, ErrorState, Table, Td, Th, Tr } from "../../components/ui";
import { Field, FormGrid, Select, TextInput } from "../../components/form";
import { Modal } from "../../components/Modal";
import { formatDate, statusVariant } from "../../lib/format";
import { LABELS, ENCOUNTER_CLASS, ENCOUNTER_STATUS } from "../../lib/enums";
import { errorMessage, useToast } from "../../lib/toast";
import type { Encounter } from "../../lib/types";

export default function EncountersTab() {
  const { patientId } = usePatientChart();
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Encounter | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["encounters", patientId],
    queryFn: () => encountersApi.listForPatient(patientId),
  });

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus size={13} /> Admit encounter
        </Button>
      </div>

      {isLoading && <CenteredSpinner />}
      {isError && <ErrorState message={errorMessage(error)} />}
      {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No encounters" />}
      {!isLoading && !isError && data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Visit</Th>
              <Th>Class</Th>
              <Th>Status</Th>
              <Th>Start</Th>
              <Th>End</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {data.map((e) => (
              <Tr key={e.id}>
                <Td className="font-medium">{e.visit_title || e.type_text || e.reason_text || "Encounter"}</Td>
                <Td>{LABELS.encounterClass[e.class_code ?? ""] ?? e.class_code ?? "—"}</Td>
                <Td><Badge variant={statusVariant(e.status)}>{LABELS.encounterStatus[e.status] ?? e.status}</Badge></Td>
                <Td>{formatDate(e.period_start)}</Td>
                <Td>{formatDate(e.period_end)}</Td>
                <Td>
                  <Button size="sm" variant="ghost" onClick={() => setEditing(e)}>Edit</Button>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}

      <CreateEncounterModal patientId={patientId} open={createOpen} onClose={() => setCreateOpen(false)} />
      {editing && <EditEncounterModal encounter={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function CreateEncounterModal({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    class_code: "IMP",
    status: "in-progress",
    visit_title: "",
    reason_text: "",
    location_display: "",
    attending_name: "",
  });

  const mutation = useMutation({
    mutationFn: () => encountersApi.create({ patient_id: patientId, ...form }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounters", patientId] });
      qc.invalidateQueries({ queryKey: ["chart", patientId] });
      toast.success("Encounter created");
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Admit encounter">
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Field label="Visit title">
          <TextInput value={form.visit_title} onChange={(e) => setForm({ ...form, visit_title: e.target.value })} placeholder="e.g. Acute stroke admission" />
        </Field>
        <FormGrid>
          <Field label="Class" required>
            <Select options={ENCOUNTER_CLASS} value={form.class_code} onChange={(e) => setForm({ ...form, class_code: e.target.value })} />
          </Field>
          <Field label="Status" required>
            <Select options={ENCOUNTER_STATUS} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} />
          </Field>
        </FormGrid>
        <Field label="Reason">
          <TextInput value={form.reason_text} onChange={(e) => setForm({ ...form, reason_text: e.target.value })} />
        </Field>
        <FormGrid>
          <Field label="Location">
            <TextInput value={form.location_display} onChange={(e) => setForm({ ...form, location_display: e.target.value })} />
          </Field>
          <Field label="Attending">
            <TextInput value={form.attending_name} onChange={(e) => setForm({ ...form, attending_name: e.target.value })} />
          </Field>
        </FormGrid>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Create</Button>
        </div>
      </form>
    </Modal>
  );
}

function EditEncounterModal({ encounter, onClose }: { encounter: Encounter; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [status, setStatus] = useState(encounter.status);
  const [discharge, setDischarge] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      encountersApi.update(encounter.id, {
        status,
        ...(discharge ? { period_end: new Date().toISOString() } : {}),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["encounters", encounter.patient_id] });
      qc.invalidateQueries({ queryKey: ["chart", encounter.patient_id] });
      toast.success("Encounter updated");
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open onClose={onClose} title="Edit encounter">
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Field label="Status">
          <Select options={ENCOUNTER_STATUS} value={status} onChange={(e) => setStatus(e.target.value)} />
        </Field>
        {!encounter.period_end && (
          <label className="flex items-center gap-2 text-[12.5px] text-text">
            <input type="checkbox" checked={discharge} onChange={(e) => setDischarge(e.target.checked)} className="h-3.5 w-3.5 accent-[var(--accent)]" />
            Discharge now (sets end time)
          </label>
        )}
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Save</Button>
        </div>
      </form>
    </Modal>
  );
}
