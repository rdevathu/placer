import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { usePatientChart } from "../PatientDetailPage";
import { notesApi } from "../../lib/api";
import { Badge, Button, CenteredSpinner, EmptyState, ErrorState, Table, Td, Th, Tr } from "../../components/ui";
import { Field, FormGrid, Select, TextArea, TextInput } from "../../components/form";
import { Modal } from "../../components/Modal";
import { formatDateTime, statusVariant } from "../../lib/format";
import { LABELS, NOTE_TYPE } from "../../lib/enums";
import { errorMessage, useToast } from "../../lib/toast";
import type { Note } from "../../lib/types";

export default function NotesTab() {
  const { patientId } = usePatientChart();
  const [createOpen, setCreateOpen] = useState(false);
  const [viewing, setViewing] = useState<Note | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["notes", patientId],
    queryFn: () => notesApi.listForPatient(patientId),
  });

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus size={13} /> Write note
        </Button>
      </div>

      {isLoading && <CenteredSpinner />}
      {isError && <ErrorState message={errorMessage(error)} />}
      {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No notes" />}
      {!isLoading && !isError && data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Title</Th>
              <Th>Type</Th>
              <Th>Status</Th>
              <Th>Author</Th>
              <Th>Created</Th>
            </tr>
          </thead>
          <tbody>
            {data.map((n) => (
              <Tr key={n.id} onClick={() => setViewing(n)}>
                <Td className="font-medium">{n.title || LABELS.noteType[n.note_type] || n.note_type}</Td>
                <Td>{LABELS.noteType[n.note_type] ?? n.note_type}</Td>
                <Td><Badge variant={statusVariant(n.status)}>{n.status}</Badge></Td>
                <Td>{n.author ?? (n.authored_by_agent ? "Agent" : "—")}</Td>
                <Td>{formatDateTime(n.created_at)}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}

      <CreateNoteModal patientId={patientId} open={createOpen} onClose={() => setCreateOpen(false)} />
      {viewing && <ViewNoteModal note={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}

function CreateNoteModal({ patientId, open, onClose }: { patientId: string; open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [form, setForm] = useState({ note_type: "progress", title: "", text: "", author: "", status: "draft" });

  const mutation = useMutation({
    mutationFn: () => notesApi.create({ patient_id: patientId, ...form }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notes", patientId] });
      toast.success("Note saved");
      onClose();
      setForm({ note_type: "progress", title: "", text: "", author: "", status: "draft" });
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  return (
    <Modal open={open} onClose={onClose} title="Write note" width={560}>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}>
        <FormGrid>
          <Field label="Type" required>
            <Select options={NOTE_TYPE} value={form.note_type} onChange={(e) => setForm({ ...form, note_type: e.target.value })} />
          </Field>
          <Field label="Author">
            <TextInput value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} />
          </Field>
        </FormGrid>
        <Field label="Title">
          <TextInput value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="Text" required>
          <TextArea rows={8} value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} required />
        </Field>
        <label className="flex items-center gap-2 text-[12.5px] text-text">
          <input type="checkbox" checked={form.status === "signed"} onChange={(e) => setForm({ ...form, status: e.target.checked ? "signed" : "draft" })} className="h-3.5 w-3.5 accent-[var(--accent)]" />
          Sign immediately
        </label>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>Save note</Button>
        </div>
      </form>
    </Modal>
  );
}

function ViewNoteModal({ note, onClose }: { note: Note; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [text, setText] = useState(note.text);

  const saveMutation = useMutation({
    mutationFn: () => notesApi.update(note.id, { text }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notes", note.patient_id] });
      toast.success("Note updated");
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const signMutation = useMutation({
    mutationFn: () => notesApi.sign(note.id, "Attending"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notes", note.patient_id] });
      toast.success("Note signed");
      onClose();
    },
    onError: (err) => toast.error(errorMessage(err)),
  });

  const editable = note.status === "draft";

  return (
    <Modal open onClose={onClose} title={note.title || LABELS.noteType[note.note_type] || "Note"} width={560}>
      <div className="mb-3 flex items-center gap-2">
        <Badge variant={statusVariant(note.status)}>{note.status}</Badge>
        <span className="text-[11.5px] text-text-tertiary">
          {note.author ?? "Agent"} · {formatDateTime(note.created_at)}
        </span>
      </div>
      {editable ? (
        <TextArea rows={12} value={text} onChange={(e) => setText(e.target.value)} />
      ) : (
        <p className="whitespace-pre-wrap text-[12.5px] leading-relaxed text-text">{note.text}</p>
      )}
      <div className="mt-3 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>Close</Button>
        {editable && (
          <>
            <Button variant="secondary" loading={saveMutation.isPending} onClick={() => saveMutation.mutate()}>Save</Button>
            <Button variant="primary" loading={signMutation.isPending} onClick={() => signMutation.mutate()}>Sign</Button>
          </>
        )}
      </div>
    </Modal>
  );
}
