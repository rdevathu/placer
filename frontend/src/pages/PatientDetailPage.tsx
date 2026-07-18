import { Outlet, useNavigate, useParams } from "react-router-dom";
import { useOutletContext } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { patientsApi } from "../lib/api";
import { CenteredSpinner, ErrorState, Badge } from "../components/ui";
import { TabNav } from "../components/TabNav";
import { errorMessage } from "../lib/toast";
import { formatDate, patientDisplayName } from "../lib/format";
import { LABELS } from "../lib/enums";
import type { PatientChart } from "../lib/types";

export interface PatientTabContext {
  patientId: string;
  chart: PatientChart;
}

export function usePatientChart() {
  return useOutletContext<PatientTabContext>();
}

export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: chart, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["chart", id],
    queryFn: () => patientsApi.chart(id!),
    enabled: !!id,
  });

  if (isLoading) return <CenteredSpinner />;
  if (isError || !chart) return <ErrorState message={errorMessage(error)} />;

  const { patient, active_encounter } = chart;

  const tabs = [
    { to: `/patients/${id}`, label: "Overview", end: true },
    { to: `/patients/${id}/encounters`, label: "Encounters" },
    { to: `/patients/${id}/problems`, label: "Problems" },
    { to: `/patients/${id}/medications`, label: "Medications" },
    { to: `/patients/${id}/orders`, label: "Orders" },
    { to: `/patients/${id}/labs`, label: "Labs & vitals" },
    { to: `/patients/${id}/notes`, label: "Notes" },
    { to: `/patients/${id}/placer`, label: "Placer" },
  ];

  return (
    <div className="flex h-full flex-col">
      <div className="shrink-0 border-b border-border px-5 py-3">
        <button
          onClick={() => navigate("/patients")}
          className="mb-2 flex cursor-pointer items-center gap-1 text-[11.5px] text-text-tertiary hover:text-text-secondary"
        >
          <ArrowLeft size={12} /> All patients
        </button>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <h1 className="text-[15px] font-semibold text-text">{patientDisplayName(patient)}</h1>
          <span className="text-[11.5px] text-text-tertiary">
            {patient.age != null ? `${patient.age}y` : ""} {patient.gender ? `· ${patient.gender}` : ""}
          </span>
          <span className="font-mono text-[11px] text-text-tertiary">{patient.mrn}</span>
          {active_encounter && (
            <Badge variant="accent">
              {LABELS.encounterStatus[active_encounter.status] ?? active_encounter.status}
            </Badge>
          )}
          {patient.code_status && <Badge variant="warning">{patient.code_status}</Badge>}
        </div>
        {active_encounter && (
          <p className="mt-1.5 text-[11.5px] text-text-tertiary">
            {active_encounter.visit_title || active_encounter.type_text || "Encounter"} · admitted{" "}
            {formatDate(active_encounter.period_start)}
            {active_encounter.location_display ? ` · ${active_encounter.location_display}` : ""}
            {active_encounter.attending_name ? ` · ${active_encounter.attending_name}` : ""}
          </p>
        )}
      </div>

      <TabNav tabs={tabs} />

      <div className="flex-1 overflow-y-auto px-5 py-4">
        <Outlet context={{ patientId: id!, chart, refetchChart: refetch } satisfies PatientTabContext & { refetchChart: () => void }} />
      </div>
    </div>
  );
}
