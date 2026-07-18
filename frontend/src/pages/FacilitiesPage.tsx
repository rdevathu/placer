import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { facilitiesApi } from "../lib/api";
import { Badge, Button, CenteredSpinner, EmptyState, ErrorState, PageHeader, Table, Td, Th, Tr } from "../components/ui";
import { Checkbox, Field, FormGrid, Select, TextInput } from "../components/form";
import { Modal } from "../components/Modal";
import { FACILITY_TYPE, LABELS } from "../lib/enums";
import { errorMessage, useToast } from "../lib/toast";
import type { Facility } from "../lib/types";

export default function FacilitiesPage() {
  const [facilityType, setFacilityType] = useState("");
  const [state, setState] = useState("");
  const [availableOnly, setAvailableOnly] = useState(false);
  const [covidOnly, setCovidOnly] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Facility | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["facilities", facilityType, state, availableOnly, covidOnly],
    queryFn: () =>
      facilitiesApi.list({
        facility_type: facilityType || undefined,
        state: state || undefined,
        has_available_beds: availableOnly || undefined,
        accepts_covid_positive: covidOnly || undefined,
      }),
  });

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title="Facilities"
        subtitle="Post-acute placement search — SNF, rehab, LTAC, hospice, home health, DME"
        action={
          <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
            <Plus size={13} /> Add facility
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-3 border-b border-border px-5 py-2.5">
        <Select options={FACILITY_TYPE} placeholder="All types" value={facilityType} onChange={(e) => setFacilityType(e.target.value)} className="w-44" />
        <TextInput placeholder="State (e.g. CA)" value={state} onChange={(e) => setState(e.target.value.toUpperCase())} className="w-32" />
        <Checkbox label="Available beds" checked={availableOnly} onChange={(e) => setAvailableOnly(e.target.checked)} />
        <Checkbox label="Accepts COVID+" checked={covidOnly} onChange={(e) => setCovidOnly(e.target.checked)} />
        <span className="ml-auto text-[11.5px] text-text-tertiary">{data?.length ?? 0} facilities</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading && <CenteredSpinner />}
        {isError && <ErrorState message={errorMessage(error)} />}
        {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No facilities match" />}
        {!isLoading && !isError && data && data.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Name</Th>
                <Th>Type</Th>
                <Th>Location</Th>
                <Th>Beds</Th>
                <Th>COVID+</Th>
                <Th>Medicaid</Th>
                <Th>Specialties</Th>
                <Th />
              </tr>
            </thead>
            <tbody>
              {data.map((f) => (
                <Tr key={f.id}>
                  <Td className="font-medium">{f.name}</Td>
                  <Td>{LABELS.facilityType[f.facility_type] ?? f.facility_type}</Td>
                  <Td>{[f.city, f.state].filter(Boolean).join(", ") || "—"}</Td>
                  <Td>
                    {f.available_beds != null ? (
                      <Badge variant={f.available_beds > 0 ? "success" : "danger"}>
                        {f.available_beds}/{f.total_beds ?? "?"}
                      </Badge>
                    ) : (
                      "—"
                    )}
                  </Td>
                  <Td>{f.accepts_covid_positive ? "Yes" : "No"}</Td>
                  <Td>{f.accepts_medicaid ? "Yes" : "No"}</Td>
                  <Td className="max-w-[200px] truncate">{f.specialties?.join(", ") ?? "—"}</Td>
                  <Td>
                    <Button size="sm" variant="ghost" onClick={() => setEditing(f)}>Edit</Button>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <CreateFacilityModal open={createOpen} onClose={() => setCreateOpen(false)} />
      {editing && <EditFacilityModal facility={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function CreateFacilityModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    name: "",
    facility_type: "snf",
    city: "",
    state: "",
    phone: "",
    total_beds: "",
    available_beds: "",
    accepts_covid_positive: false,
    accepts_medicaid: true,
  });

  const mutation = useMutation({
    mutationFn: () =>
      facilitiesApi.create({
        ...form,
        total_beds: form.total_beds ? Number(form.total_beds) : undefined,
        available_beds: form.available_beds ? Number(form.available_beds) : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["facilities"] });
      toast.success("Facility added");
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Add facility">
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Field label="Name" required>
          <TextInput value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </Field>
        <FormGrid>
          <Field label="Type" required>
            <Select options={FACILITY_TYPE} value={form.facility_type} onChange={(e) => setForm({ ...form, facility_type: e.target.value })} />
          </Field>
          <Field label="Phone">
            <TextInput value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
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
        <FormGrid>
          <Field label="Total beds">
            <TextInput type="number" value={form.total_beds} onChange={(e) => setForm({ ...form, total_beds: e.target.value })} />
          </Field>
          <Field label="Available beds">
            <TextInput type="number" value={form.available_beds} onChange={(e) => setForm({ ...form, available_beds: e.target.value })} />
          </Field>
        </FormGrid>
        <Checkbox label="Accepts COVID-positive patients" checked={form.accepts_covid_positive} onChange={(e) => setForm({ ...form, accepts_covid_positive: e.target.checked })} />
        <Checkbox label="Accepts Medicaid" checked={form.accepts_medicaid} onChange={(e) => setForm({ ...form, accepts_medicaid: e.target.checked })} />
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Add facility</Button>
        </div>
      </form>
    </Modal>
  );
}

function EditFacilityModal({ facility, onClose }: { facility: Facility; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [availableBeds, setAvailableBeds] = useState(String(facility.available_beds ?? ""));
  const [acceptsCovid, setAcceptsCovid] = useState(facility.accepts_covid_positive);
  const [phone, setPhone] = useState(facility.phone ?? "");
  const [notes, setNotes] = useState(facility.notes ?? "");

  const mutation = useMutation({
    mutationFn: () =>
      facilitiesApi.update(facility.id, {
        available_beds: availableBeds ? Number(availableBeds) : undefined,
        accepts_covid_positive: acceptsCovid,
        phone: phone || undefined,
        notes: notes || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["facilities"] });
      toast.success("Facility updated");
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open onClose={onClose} title={facility.name}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <Field label="Available beds" hint="Update after calling the facility's admissions desk">
          <TextInput type="number" value={availableBeds} onChange={(e) => setAvailableBeds(e.target.value)} />
        </Field>
        <Field label="Phone">
          <TextInput value={phone} onChange={(e) => setPhone(e.target.value)} />
        </Field>
        <Checkbox label="Accepts COVID-positive patients" checked={acceptsCovid} onChange={(e) => setAcceptsCovid(e.target.checked)} />
        <Field label="Notes">
          <TextInput value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Save</Button>
        </div>
      </form>
    </Modal>
  );
}
