import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { usePatientChart } from "../../PatientDetailPage";
import { dispoApi } from "../../../lib/api";
import { Badge, Button, Card, CenteredSpinner, EmptyState, ErrorState, SectionLabel } from "../../../components/ui";
import { Field, FormGrid, Select, TextArea, TextInput } from "../../../components/form";
import { Modal } from "../../../components/Modal";
import { formatDateTime } from "../../../lib/format";
import { DISPOSITION_TYPE, LABELS } from "../../../lib/enums";
import { errorMessage, useToast } from "../../../lib/toast";

export function DispositionSection() {
  const { patientId } = usePatientChart();
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dispo-history", patientId],
    queryFn: () => dispoApi.listForPatient(patientId),
  });

  return (
    <section>
      <div className="mb-1.5 flex items-center justify-between">
        <SectionLabel>Disposition</SectionLabel>
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus size={13} /> Post prediction
        </Button>
      </div>

      {isLoading && <CenteredSpinner />}
      {isError && <ErrorState message={errorMessage(error)} />}
      {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No disposition assessments yet" />}

      <div className="flex flex-col gap-3">
        {data?.map((d) => (
          <Card key={d.id} className="p-4">
            <div className="flex items-center gap-2">
              <Badge variant={d.is_current ? "success" : "neutral"}>
                {LABELS.dispositionType[d.predicted_disposition] ?? d.predicted_disposition}
              </Badge>
              {d.is_current && <span className="text-[11px] font-medium text-success">current</span>}
              {d.confidence != null && <span className="text-[11.5px] text-text-tertiary">{Math.round(d.confidence * 100)}% confidence</span>}
              <span className="ml-auto text-[11px] text-text-tertiary">{formatDateTime(d.created_at)}</span>
            </div>
            {d.rationale && <p className="mt-2 text-[12.5px] leading-relaxed text-text-secondary">{d.rationale}</p>}
            {d.barriers && d.barriers.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {d.barriers.map((b, i) => (
                  <Badge key={i} variant="warning">{b}</Badge>
                ))}
              </div>
            )}
            {d.alternatives && d.alternatives.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {d.alternatives.map((a, i) => (
                  <Badge key={i} variant="neutral">
                    {LABELS.dispositionType[a.disposition] ?? a.disposition}
                    {a.confidence != null ? ` (${Math.round(a.confidence * 100)}%)` : ""}
                  </Badge>
                ))}
              </div>
            )}
            {d.assessed_by && <p className="mt-2 text-[11px] text-text-tertiary">Assessed by {d.assessed_by}</p>}
          </Card>
        ))}
      </div>

      <CreateDispoModal patientId={patientId} open={createOpen} onClose={() => setCreateOpen(false)} />
    </section>
  );
}

function CreateDispoModal({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    predicted_disposition: "home",
    confidence: "",
    rationale: "",
    barriers: "",
    assessed_by: "",
  });

  const mutation = useMutation({
    mutationFn: () =>
      dispoApi.create({
        patient_id: patientId,
        predicted_disposition: form.predicted_disposition,
        confidence: form.confidence ? Number(form.confidence) : undefined,
        rationale: form.rationale || undefined,
        barriers: form.barriers ? form.barriers.split(",").map((s) => s.trim()).filter(Boolean) : undefined,
        assessed_by: form.assessed_by || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dispo-history", patientId] });
      qc.invalidateQueries({ queryKey: ["chart", patientId] });
      toast.success("Disposition prediction posted");
      onClose();
      setForm({ predicted_disposition: "home", confidence: "", rationale: "", barriers: "", assessed_by: "" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Post disposition prediction" width={520}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <FormGrid>
          <Field label="Predicted disposition" required>
            <Select options={DISPOSITION_TYPE} value={form.predicted_disposition} onChange={(e) => setForm({ ...form, predicted_disposition: e.target.value })} />
          </Field>
          <Field label="Confidence" hint="0.0 – 1.0">
            <TextInput type="number" min={0} max={1} step={0.05} value={form.confidence} onChange={(e) => setForm({ ...form, confidence: e.target.value })} />
          </Field>
        </FormGrid>
        <Field label="Rationale">
          <TextArea rows={4} value={form.rationale} onChange={(e) => setForm({ ...form, rationale: e.target.value })} />
        </Field>
        <Field label="Barriers" hint="Comma-separated open items blocking this disposition">
          <TextInput value={form.barriers} onChange={(e) => setForm({ ...form, barriers: e.target.value })} placeholder="pending COVID test, PM&R consult" />
        </Field>
        <Field label="Assessed by">
          <TextInput value={form.assessed_by} onChange={(e) => setForm({ ...form, assessed_by: e.target.value })} placeholder="Placer or clinician name" />
        </Field>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Post prediction</Button>
        </div>
      </form>
    </Modal>
  );
}
