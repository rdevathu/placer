import { Link } from "react-router-dom";
import { usePatientChart } from "../PatientDetailPage";
import { Badge, Card, CardHeader, EmptyState, Kv } from "../../components/ui";
import { formatDate, statusVariant, priorityVariant, abnormalVariant } from "../../lib/format";
import { humanize } from "../../lib/enums";

export default function OverviewTab() {
  const { patientId, chart } = usePatientChart();
  const { patient, active_problems, medications, latest_vitals, pending_labs, abnormal_labs, open_care_tasks, open_orders } = chart;

  const cityStateZip = [[patient.city, patient.state].filter(Boolean).join(", "), patient.postal_code]
    .filter(Boolean)
    .join(" ");
  const address = [patient.address_line, cityStateZip].filter(Boolean).join(", ") || null;
  const emergencyContact =
    [patient.emergency_contact_name, patient.emergency_contact_relationship, patient.emergency_contact_phone]
      .filter(Boolean)
      .join(" · ") || null;

  return (
    <div className="grid grid-cols-2 gap-4 pb-6">
      <Card>
        <CardHeader title="Demographics" />
        <div className="divide-y divide-border px-4">
          <Kv label="MRN" value={patient.mrn} />
          <Kv label="Birth date" value={formatDate(patient.birth_date)} />
          <Kv label="Marital status" value={patient.marital_status ? humanize(patient.marital_status) : null} />
          <Kv label="Language" value={patient.language} />
          <Kv label="Phone" value={patient.phone} />
          <Kv label="Address" value={address} />
          <Kv label="Emergency contact" value={emergencyContact} />
          <Kv label="Living situation" value={patient.living_situation ? humanize(patient.living_situation) : null} />
          <Kv label="Code status" value={patient.code_status} />
        </div>
      </Card>

      <Card>
        <CardHeader title="Active problems" subtitle={`${active_problems.length} active`} />
        {active_problems.length === 0 ? (
          <EmptyState title="No active problems" />
        ) : (
          <div className="flex flex-wrap gap-1.5 px-4 py-3">
            {active_problems.map((c) => (
              <Badge key={c.id} variant="neutral">{c.display}</Badge>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Medications" subtitle={`${medications.length} active`} action={<Link to={`/patients/${patientId}/medications`} className="text-[11.5px] text-accent hover:underline">View all →</Link>} />
        {medications.length === 0 ? (
          <EmptyState title="No active medications" />
        ) : (
          <div className="divide-y divide-border px-4">
            {medications.slice(0, 6).map((m) => (
              <Kv key={m.id} label={m.display ?? "—"} value={[m.dose, m.frequency].filter(Boolean).join(" · ") || null} />
            ))}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Latest vitals" action={<Link to={`/patients/${patientId}/labs`} className="text-[11.5px] text-accent hover:underline">View all →</Link>} />
        {latest_vitals.length === 0 ? (
          <EmptyState title="No vitals recorded" />
        ) : (
          <div className="divide-y divide-border px-4">
            {latest_vitals.map((v) => (
              <Kv key={v.id} label={v.display ?? "—"} value={v.value_num != null ? `${v.value_num} ${v.value_unit ?? ""}` : v.value_string} />
            ))}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader
          title="Pending labs"
          subtitle={`${pending_labs.length} in flight`}
          action={<Link to={`/patients/${patientId}/labs`} className="text-[11.5px] text-accent hover:underline">View all →</Link>}
        />
        {pending_labs.length === 0 ? (
          <EmptyState title="No pending labs" />
        ) : (
          <div className="divide-y divide-border px-4">
            {pending_labs.map((l) => (
              <Kv key={l.id} label={l.display ?? "—"} value={<Badge variant="warning">pending</Badge>} />
            ))}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Abnormal labs" subtitle={`${abnormal_labs.length} flagged`} />
        {abnormal_labs.length === 0 ? (
          <EmptyState title="No abnormal results" />
        ) : (
          <div className="divide-y divide-border px-4">
            {abnormal_labs.map((l) => (
              <Kv
                key={l.id}
                label={l.display ?? "—"}
                value={
                  <span className="flex items-center justify-end gap-1.5">
                    {l.value_num != null ? `${l.value_num} ${l.value_unit ?? ""}` : l.value_string}
                    <Badge variant={abnormalVariant(l.abnormal_flag)}>{l.abnormal_flag}</Badge>
                  </span>
                }
              />
            ))}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Open care tasks" subtitle={`${open_care_tasks.length} open`} action={<Link to={`/patients/${patientId}/placer`} className="text-[11.5px] text-accent hover:underline">View all →</Link>} />
        {open_care_tasks.length === 0 ? (
          <EmptyState title="No open tasks" />
        ) : (
          <div className="divide-y divide-border px-4">
            {open_care_tasks.map((t) => (
              <Kv
                key={t.id}
                label={t.title}
                value={
                  <span className="flex items-center justify-end gap-1.5">
                    <Badge variant={priorityVariant(t.priority)}>{t.priority}</Badge>
                    <Badge variant={statusVariant(t.status)}>{humanize(t.status)}</Badge>
                  </span>
                }
              />
            ))}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader title="Open orders" subtitle={`${open_orders.length} open`} action={<Link to={`/patients/${patientId}/orders`} className="text-[11.5px] text-accent hover:underline">View all →</Link>} />
        {open_orders.length === 0 ? (
          <EmptyState title="No open orders" />
        ) : (
          <div className="divide-y divide-border px-4">
            {open_orders.map((o) => (
              <Kv
                key={o.id}
                label={o.display}
                value={<Badge variant={statusVariant(o.status)}>{humanize(o.status)}</Badge>}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
