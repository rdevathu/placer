import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { usePatientChart } from "../PatientDetailPage";
import { communicationsApi } from "../../lib/api";
import { Badge, Button, CenteredSpinner, EmptyState, ErrorState, Table, Td, Th, Tr } from "../../components/ui";
import { Field, FormGrid, Select, TextArea, TextInput } from "../../components/form";
import { Modal } from "../../components/Modal";
import { formatDateTime } from "../../lib/format";
import { COMM_DIRECTION, COMM_MODALITY, LABELS, PARTY_TYPE } from "../../lib/enums";
import { errorMessage, useToast } from "../../lib/toast";

export default function CommunicationsTab() {
  const { patientId } = usePatientChart();
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["communications", patientId],
    queryFn: () => communicationsApi.list({ patient_id: patientId }),
  });

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus size={13} /> Log communication
        </Button>
      </div>

      {isLoading && <CenteredSpinner />}
      {isError && <ErrorState message={errorMessage(error)} />}
      {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No communications logged" />}
      {!isLoading && !isError && data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Party</Th>
              <Th>Modality</Th>
              <Th>Direction</Th>
              <Th>Summary</Th>
              <Th>Outcome</Th>
              <Th>When</Th>
            </tr>
          </thead>
          <tbody>
            {data.map((c) => (
              <Tr key={c.id}>
                <Td className="font-medium">{c.party_name ?? (c.party_type ? LABELS.partyType[c.party_type] : "—")}</Td>
                <Td>{LABELS.commModality[c.modality] ?? c.modality}</Td>
                <Td className="capitalize">{c.direction}</Td>
                <Td className="max-w-xs truncate">{c.summary ?? "—"}</Td>
                <Td>{c.outcome ? <Badge variant="accent">{c.outcome}</Badge> : "—"}</Td>
                <Td>{formatDateTime(c.occurred_at)}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}

      <CreateCommModal patientId={patientId} open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}

function CreateCommModal({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    direction: "outbound",
    modality: "phone",
    party_type: "snf",
    party_name: "",
    summary: "",
    outcome: "",
  });

  const mutation = useMutation({
    mutationFn: () => communicationsApi.create({ patient_id: patientId, ...form }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["communications", patientId] });
      toast.success("Communication logged");
      onClose();
      setForm({ direction: "outbound", modality: "phone", party_type: "snf", party_name: "", summary: "", outcome: "" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Log communication" width={520}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <FormGrid>
          <Field label="Direction">
            <Select options={COMM_DIRECTION} value={form.direction} onChange={(e) => setForm({ ...form, direction: e.target.value })} />
          </Field>
          <Field label="Modality">
            <Select options={COMM_MODALITY} value={form.modality} onChange={(e) => setForm({ ...form, modality: e.target.value })} />
          </Field>
        </FormGrid>
        <FormGrid>
          <Field label="Party type">
            <Select options={PARTY_TYPE} value={form.party_type} onChange={(e) => setForm({ ...form, party_type: e.target.value })} />
          </Field>
          <Field label="Party name">
            <TextInput value={form.party_name} onChange={(e) => setForm({ ...form, party_name: e.target.value })} />
          </Field>
        </FormGrid>
        <Field label="Summary">
          <TextArea value={form.summary} onChange={(e) => setForm({ ...form, summary: e.target.value })} />
        </Field>
        <Field label="Outcome" hint="e.g. bed_available | declined | callback | preference_captured">
          <TextInput value={form.outcome} onChange={(e) => setForm({ ...form, outcome: e.target.value })} />
        </Field>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Log</Button>
        </div>
      </form>
    </Modal>
  );
}
