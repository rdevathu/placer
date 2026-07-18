import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { usePatientChart } from "../PatientDetailPage";
import { ordersApi } from "../../lib/api";
import { Badge, Button, CenteredSpinner, EmptyState, ErrorState, Table, Td, Th, Tr } from "../../components/ui";
import { Field, FormGrid, Select, TextArea, TextInput } from "../../components/form";
import { Modal } from "../../components/Modal";
import { formatDateTime, priorityVariant, statusVariant } from "../../lib/format";
import { LABELS, ORDER_PRIORITY, ORDER_TYPE, humanize } from "../../lib/enums";
import { errorMessage, useToast } from "../../lib/toast";
import type { Order } from "../../lib/types";

export default function OrdersTab() {
  const { patientId } = usePatientChart();
  const [createOpen, setCreateOpen] = useState(false);
  const qc = useQueryClient();
  const toast = useToast();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["orders", patientId],
    queryFn: () => ordersApi.list({ patient_id: patientId }),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["orders", patientId] });
    qc.invalidateQueries({ queryKey: ["chart", patientId] });
    qc.invalidateQueries({ queryKey: ["labs", patientId] });
  };

  const signMutation = useMutation({
    mutationFn: (id: string) => ordersApi.sign(id, "Attending"),
    onSuccess: () => { invalidate(); toast.success("Order signed"); },
    onError: (err) => toast.error(errorMessage(err)),
  });
  const completeMutation = useMutation({
    mutationFn: (id: string) => ordersApi.complete(id),
    onSuccess: () => { invalidate(); toast.success("Order completed"); },
    onError: (err) => toast.error(errorMessage(err)),
  });
  const cancelMutation = useMutation({
    mutationFn: (id: string) => ordersApi.cancel(id),
    onSuccess: () => { invalidate(); toast.success("Order cancelled"); },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const busy = signMutation.isPending || completeMutation.isPending || cancelMutation.isPending;

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus size={13} /> Place order
        </Button>
      </div>

      {isLoading && <CenteredSpinner />}
      {isError && <ErrorState message={errorMessage(error)} />}
      {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No orders placed" />}
      {!isLoading && !isError && data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Order</Th>
              <Th>Type</Th>
              <Th>Priority</Th>
              <Th>Status</Th>
              <Th>Ordered by</Th>
              <Th>Placed</Th>
              <Th />
            </tr>
          </thead>
          <tbody>
            {data.map((o: Order) => (
              <Tr key={o.id}>
                <Td className="font-medium">{o.display}</Td>
                <Td>{LABELS.orderType[o.order_type] ?? o.order_type}</Td>
                <Td><Badge variant={priorityVariant(o.priority)}>{o.priority}</Badge></Td>
                <Td><Badge variant={statusVariant(o.status)}>{LABELS.orderStatus[o.status] ?? o.status}</Badge></Td>
                <Td>{o.ordered_by ?? "—"}</Td>
                <Td>{formatDateTime(o.authored_at)}</Td>
                <Td>
                  <div className="flex justify-end gap-1">
                    {o.status === "draft" && (
                      <Button size="sm" variant="ghost" disabled={busy} onClick={() => signMutation.mutate(o.id)}>Sign</Button>
                    )}
                    {o.status === "signed" && (
                      <Button size="sm" variant="ghost" disabled={busy} onClick={() => completeMutation.mutate(o.id)}>Complete</Button>
                    )}
                    {(o.status === "draft" || o.status === "signed") && (
                      <Button size="sm" variant="danger" disabled={busy} onClick={() => cancelMutation.mutate(o.id)}>Cancel</Button>
                    )}
                  </div>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}

      <CreateOrderModal patientId={patientId} open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}

function CreateOrderModal({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({
    order_type: "lab",
    display: "",
    detail: "",
    priority: "routine",
    ordered_by: "",
    signNow: false,
  });

  const mutation = useMutation({
    mutationFn: () =>
      ordersApi.create({
        patient_id: patientId,
        order_type: form.order_type,
        display: form.display,
        detail: form.detail || undefined,
        priority: form.priority,
        ordered_by: form.ordered_by || undefined,
        status: form.signNow ? "signed" : "draft",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["orders", patientId] });
      qc.invalidateQueries({ queryKey: ["chart", patientId] });
      qc.invalidateQueries({ queryKey: ["labs", patientId] });
      toast.success("Order placed");
      onClose();
      setForm({ order_type: "lab", display: "", detail: "", priority: "routine", ordered_by: "", signNow: false });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Place order">
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <FormGrid>
          <Field label="Type" required>
            <Select options={ORDER_TYPE} value={form.order_type} onChange={(e) => setForm({ ...form, order_type: e.target.value })} />
          </Field>
          <Field label="Priority">
            <Select options={ORDER_PRIORITY} value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} />
          </Field>
        </FormGrid>
        <Field label="What is being ordered" required>
          <TextInput value={form.display} onChange={(e) => setForm({ ...form, display: e.target.value })} placeholder="e.g. SARS-CoV-2 NAA test" required />
        </Field>
        <Field label="Detail">
          <TextArea value={form.detail} onChange={(e) => setForm({ ...form, detail: e.target.value })} />
        </Field>
        <Field label="Ordered by">
          <TextInput value={form.ordered_by} onChange={(e) => setForm({ ...form, ordered_by: e.target.value })} placeholder="Placer or clinician name" />
        </Field>
        <label className="flex items-center gap-2 text-[12.5px] text-text">
          <input type="checkbox" checked={form.signNow} onChange={(e) => setForm({ ...form, signNow: e.target.checked })} className="h-3.5 w-3.5 accent-[var(--accent)]" />
          Sign immediately (otherwise saved as {humanize("draft")}/pended)
        </label>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Place order</Button>
        </div>
      </form>
    </Modal>
  );
}
