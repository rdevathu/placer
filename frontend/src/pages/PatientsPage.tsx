import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { patientsApi } from "../lib/api";
import { CenteredSpinner, EmptyState, ErrorState, PageHeader, Table, Td, Th, Tr, Button, Badge } from "../components/ui";
import { patientDisplayName } from "../lib/format";
import { errorMessage, useToast } from "../lib/toast";
import { Modal } from "../components/Modal";
import { Field, FormGrid, Select, TextInput } from "../components/form";

const LIVING_SITUATION_OPTIONS = [
  { value: "lives_alone", label: "Lives alone" },
  { value: "lives_with_family", label: "Lives with family" },
  { value: "facility", label: "Facility" },
];

export default function PatientsPage() {
  const [scope, setScope] = useState<"admitted" | "all">("admitted");
  const [q, setQ] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const navigate = useNavigate();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["patients", scope, q],
    queryFn: () => patientsApi.list({ admitted: scope === "admitted" ? true : undefined, q: q || undefined, limit: 200 }),
  });

  const patients = useMemo(() => data ?? [], [data]);

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Patients"
        subtitle={scope === "admitted" ? "Active inpatient encounters" : "All patients"}
        action={
          <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
            <Plus size={13} /> New patient
          </Button>
        }
      />

      <div className="flex items-center gap-3 border-b border-border px-5 py-2.5">
        <div className="flex rounded-md border border-border-strong bg-bg-inset p-0.5">
          {(["admitted", "all"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setScope(s)}
              className={
                "rounded px-2.5 py-1 text-[12px] font-medium transition-colors cursor-pointer " +
                (scope === s ? "bg-bg-elevated text-text shadow-sm" : "text-text-tertiary hover:text-text-secondary")
              }
            >
              {s === "admitted" ? "Admitted" : "All"}
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <Search size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text-tertiary" />
          <TextInput
            placeholder="Search name or MRN…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="pl-7"
          />
        </div>
        <span className="text-[11.5px] text-text-tertiary">{patients.length} patients</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && <CenteredSpinner />}
        {isError && <ErrorState message={errorMessage(error)} />}
        {!isLoading && !isError && patients.length === 0 && (
          <EmptyState title="No patients found" hint="Try switching scope or clearing your search." />
        )}
        {!isLoading && !isError && patients.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Patient</Th>
                <Th>MRN</Th>
                <Th>Age</Th>
                <Th>Gender</Th>
                <Th>Location</Th>
                <Th>Code status</Th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p) => (
                <Tr key={p.id} onClick={() => navigate(`/patients/${p.id}`)}>
                  <Td className="font-medium">{patientDisplayName(p)}</Td>
                  <Td className="font-mono text-[11.5px] text-text-secondary">{p.mrn}</Td>
                  <Td>{p.age ?? "—"}</Td>
                  <Td className="capitalize">{p.gender ?? "—"}</Td>
                  <Td>{[p.city, p.state].filter(Boolean).join(", ") || "—"}</Td>
                  <Td>{p.code_status ? <Badge>{p.code_status}</Badge> : "—"}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <CreatePatientModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}

function CreatePatientModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    given_name: "",
    family_name: "",
    gender: "",
    birth_date: "",
    city: "",
    state: "",
    living_situation: "",
    code_status: "",
  });

  const mutation = useMutation({
    mutationFn: () => patientsApi.create(form),
    onSuccess: (patient) => {
      qc.invalidateQueries({ queryKey: ["patients"] });
      toast.success(`${patientDisplayName(patient)} created`);
      onClose();
      navigate(`/patients/${patient.id}`);
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="New patient">
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <FormGrid>
          <Field label="Given name">
            <TextInput value={form.given_name} onChange={(e) => setForm({ ...form, given_name: e.target.value })} />
          </Field>
          <Field label="Family name">
            <TextInput value={form.family_name} onChange={(e) => setForm({ ...form, family_name: e.target.value })} />
          </Field>
        </FormGrid>
        <FormGrid>
          <Field label="Gender">
            <TextInput value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })} placeholder="female / male / …" />
          </Field>
          <Field label="Birth date">
            <TextInput type="date" value={form.birth_date} onChange={(e) => setForm({ ...form, birth_date: e.target.value })} />
          </Field>
        </FormGrid>
        <FormGrid>
          <Field label="City">
            <TextInput value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
          </Field>
          <Field label="State">
            <TextInput value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} />
          </Field>
        </FormGrid>
        <Field label="Living situation">
          <Select
            options={LIVING_SITUATION_OPTIONS}
            placeholder="Unspecified"
            value={form.living_situation}
            onChange={(e) => setForm({ ...form, living_situation: e.target.value })}
          />
        </Field>
        <Field label="Code status">
          <TextInput value={form.code_status} onChange={(e) => setForm({ ...form, code_status: e.target.value })} placeholder="full / DNR / DNI / comfort" />
        </Field>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            Create patient
          </Button>
        </div>
      </form>
    </Modal>
  );
}
