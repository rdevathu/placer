import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { usePatientChart } from "../PatientDetailPage";
import { observationsApi } from "../../lib/api";
import { Badge, Button, Card, CardHeader, CenteredSpinner, EmptyState, ErrorState, Table, Td, Th, Tr } from "../../components/ui";
import { Field, FormGrid, Select, TextInput } from "../../components/form";
import { Modal } from "../../components/Modal";
import { formatDateTime, abnormalVariant, statusVariant } from "../../lib/format";
import { OBSERVATION_STATUS } from "../../lib/enums";
import { errorMessage, useToast } from "../../lib/toast";
import type { Observation } from "../../lib/types";

type LabFilter = "pending" | "resulted" | "all";

export default function LabsTab() {
  const { patientId } = usePatientChart();
  const [labFilter, setLabFilter] = useState<LabFilter>("pending");
  const [addVitalOpen, setAddVitalOpen] = useState(false);
  const [addLabOpen, setAddLabOpen] = useState(false);
  const [resulting, setResulting] = useState<Observation | null>(null);

  const vitalsQuery = useQuery({
    queryKey: ["vitals", patientId],
    queryFn: () => observationsApi.listVitals(patientId),
  });

  const labsQuery = useQuery({
    queryKey: ["labs", patientId, labFilter],
    queryFn: () => observationsApi.listLabs(patientId, { status: labFilter === "all" ? undefined : labFilter }),
  });

  const reportsQuery = useQuery({
    queryKey: ["diagnostic-reports", patientId],
    queryFn: () => observationsApi.listReports(patientId),
  });

  return (
    <div className="flex flex-col gap-4 pb-6">
      <Card>
        <CardHeader
          title="Vitals"
          action={
            <Button size="sm" variant="secondary" onClick={() => setAddVitalOpen(true)}>
              <Plus size={13} /> Record vital
            </Button>
          }
        />
        {vitalsQuery.isLoading && <CenteredSpinner />}
        {vitalsQuery.isError && <ErrorState message={errorMessage(vitalsQuery.error)} />}
        {vitalsQuery.data && vitalsQuery.data.length === 0 && <EmptyState title="No vitals recorded" />}
        {vitalsQuery.data && vitalsQuery.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Vital</Th>
                <Th>Value</Th>
                <Th>Recorded</Th>
              </tr>
            </thead>
            <tbody>
              {vitalsQuery.data.map((v) => (
                <Tr key={v.id}>
                  <Td className="font-medium">{v.display ?? v.loinc_code ?? "—"}</Td>
                  <Td>{v.value_num != null ? `${v.value_num} ${v.value_unit ?? ""}` : v.value_string ?? "—"}</Td>
                  <Td>{formatDateTime(v.effective_time)}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card>
        <CardHeader
          title="Labs"
          action={
            <div className="flex items-center gap-2">
              <div className="flex rounded-md border border-border-strong bg-bg-inset p-0.5">
                {(["pending", "resulted", "all"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setLabFilter(f)}
                    className={
                      "rounded px-2 py-1 text-[11.5px] font-medium capitalize transition-colors cursor-pointer " +
                      (labFilter === f ? "bg-bg-elevated text-text shadow-sm" : "text-text-tertiary hover:text-text-secondary")
                    }
                  >
                    {f}
                  </button>
                ))}
              </div>
              <Button size="sm" variant="secondary" onClick={() => setAddLabOpen(true)}>
                <Plus size={13} /> Add lab
              </Button>
            </div>
          }
        />
        {labsQuery.isLoading && <CenteredSpinner />}
        {labsQuery.isError && <ErrorState message={errorMessage(labsQuery.error)} />}
        {labsQuery.data && labsQuery.data.length === 0 && <EmptyState title="No labs in this view" />}
        {labsQuery.data && labsQuery.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Lab</Th>
                <Th>Result</Th>
                <Th>Flag</Th>
                <Th>Status</Th>
                <Th>Effective</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {labsQuery.data.map((l) => (
                <Tr key={l.id}>
                  <Td className="font-medium">{l.display ?? l.loinc_code ?? "—"}</Td>
                  <Td>{l.value_num != null ? `${l.value_num} ${l.value_unit ?? ""}` : l.value_string ?? "—"}</Td>
                  <Td>{l.abnormal_flag ? <Badge variant={abnormalVariant(l.abnormal_flag)}>{l.abnormal_flag}</Badge> : "—"}</Td>
                  <Td><Badge variant={statusVariant(l.status)}>{l.status}</Badge></Td>
                  <Td>{formatDateTime(l.effective_time)}</Td>
                  <Td>
                    {l.status === "pending" && (
                      <Button size="sm" variant="primary" onClick={() => setResulting(l)}>Result</Button>
                    )}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <Card>
        <CardHeader title="Diagnostic reports / panels" />
        {reportsQuery.isLoading && <CenteredSpinner />}
        {reportsQuery.data && reportsQuery.data.length === 0 && <EmptyState title="No diagnostic reports" />}
        {reportsQuery.data && reportsQuery.data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Panel</Th>
                <Th>Status</Th>
                <Th>Effective</Th>
                <Th>Conclusion</Th>
              </tr>
            </thead>
            <tbody>
              {reportsQuery.data.map((r) => (
                <Tr key={r.id}>
                  <Td className="font-medium">{r.display ?? r.loinc_code ?? "—"}</Td>
                  <Td><Badge variant={statusVariant(r.status)}>{r.status}</Badge></Td>
                  <Td>{formatDateTime(r.effective_time)}</Td>
                  <Td className="max-w-xs truncate">{r.conclusion ?? "—"}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      <AddVitalModal patientId={patientId} open={addVitalOpen} onClose={() => setAddVitalOpen(false)} />
      <AddLabModal patientId={patientId} open={addLabOpen} onClose={() => setAddLabOpen(false)} />
      {resulting && <ResultLabModal observation={resulting} onClose={() => setResulting(null)} />}
    </div>
  );
}

function AddVitalModal({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ display: "", value_num: "", value_unit: "" });

  const mutation = useMutation({
    mutationFn: () =>
      observationsApi.create({
        patient_id: patientId,
        category: "vital-signs",
        display: form.display,
        value_num: form.value_num ? Number(form.value_num) : undefined,
        value_unit: form.value_unit || undefined,
        status: "final",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vitals", patientId] });
      qc.invalidateQueries({ queryKey: ["chart", patientId] });
      toast.success("Vital recorded");
      onClose();
      setForm({ display: "", value_num: "", value_unit: "" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Record vital">
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Field label="Vital" required>
          <TextInput value={form.display} onChange={(e) => setForm({ ...form, display: e.target.value })} placeholder="e.g. Heart rate" required />
        </Field>
        <FormGrid>
          <Field label="Value">
            <TextInput type="number" step="any" value={form.value_num} onChange={(e) => setForm({ ...form, value_num: e.target.value })} />
          </Field>
          <Field label="Unit">
            <TextInput value={form.value_unit} onChange={(e) => setForm({ ...form, value_unit: e.target.value })} placeholder="bpm" />
          </Field>
        </FormGrid>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Save</Button>
        </div>
      </form>
    </Modal>
  );
}

function AddLabModal({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ display: "", status: "final", value_num: "", value_unit: "", value_string: "" });

  const mutation = useMutation({
    mutationFn: () =>
      observationsApi.create({
        patient_id: patientId,
        category: "laboratory",
        display: form.display,
        status: form.status,
        value_num: form.value_num ? Number(form.value_num) : undefined,
        value_unit: form.value_unit || undefined,
        value_string: form.value_string || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["labs", patientId] });
      qc.invalidateQueries({ queryKey: ["chart", patientId] });
      toast.success("Lab added");
      onClose();
      setForm({ display: "", status: "final", value_num: "", value_unit: "", value_string: "" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Add lab">
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Field label="Lab" required>
          <TextInput value={form.display} onChange={(e) => setForm({ ...form, display: e.target.value })} placeholder="e.g. SARS-CoV-2 NAA" required />
        </Field>
        <Field label="Status">
          <Select options={OBSERVATION_STATUS} value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} />
        </Field>
        <FormGrid>
          <Field label="Numeric value">
            <TextInput type="number" step="any" value={form.value_num} onChange={(e) => setForm({ ...form, value_num: e.target.value })} />
          </Field>
          <Field label="Unit">
            <TextInput value={form.value_unit} onChange={(e) => setForm({ ...form, value_unit: e.target.value })} />
          </Field>
        </FormGrid>
        <Field label="Qualitative value" hint="For non-numeric results, e.g. 'Not detected'">
          <TextInput value={form.value_string} onChange={(e) => setForm({ ...form, value_string: e.target.value })} />
        </Field>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Save</Button>
        </div>
      </form>
    </Modal>
  );
}

function ResultLabModal({ observation, onClose }: { observation: Observation; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ value_num: "", value_unit: observation.value_unit ?? "", value_string: "", abnormal_flag: "N" });

  const mutation = useMutation({
    mutationFn: () =>
      observationsApi.resultLab(observation.id, {
        value_num: form.value_num ? Number(form.value_num) : undefined,
        value_unit: form.value_unit || undefined,
        value_string: form.value_string || undefined,
        abnormal_flag: form.abnormal_flag || undefined,
        status: "final",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["labs", observation.patient_id] });
      qc.invalidateQueries({ queryKey: ["chart", observation.patient_id] });
      qc.invalidateQueries({ queryKey: ["orders", observation.patient_id] });
      toast.success("Lab resulted");
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open onClose={onClose} title={`Result: ${observation.display ?? "Lab"}`}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <FormGrid>
          <Field label="Numeric value">
            <TextInput type="number" step="any" value={form.value_num} onChange={(e) => setForm({ ...form, value_num: e.target.value })} />
          </Field>
          <Field label="Unit">
            <TextInput value={form.value_unit} onChange={(e) => setForm({ ...form, value_unit: e.target.value })} />
          </Field>
        </FormGrid>
        <Field label="Qualitative value" hint="e.g. 'Not detected' — used when there is no numeric value">
          <TextInput value={form.value_string} onChange={(e) => setForm({ ...form, value_string: e.target.value })} />
        </Field>
        <Field label="Abnormal flag">
          <Select
            options={[
              { value: "N", label: "Normal" },
              { value: "H", label: "High" },
              { value: "L", label: "Low" },
              { value: "critical", label: "Critical" },
            ]}
            value={form.abnormal_flag}
            onChange={(e) => setForm({ ...form, abnormal_flag: e.target.value })}
          />
        </Field>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Submit result</Button>
        </div>
      </form>
    </Modal>
  );
}
