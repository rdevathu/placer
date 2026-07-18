import { usePatientChart } from "../../PatientDetailPage";
import { Badge } from "../../../components/ui";
import { DispositionSection } from "./DispositionSection";
import { TasksSection } from "./TasksSection";
import { CommunicationsSection } from "./CommunicationsSection";
import { ChatPanel } from "./ChatPanel";

export default function PlacerTab() {
  const { patientId } = usePatientChart();

  return (
    <div className="flex min-w-0 flex-col gap-4 pb-6 lg:flex-row lg:items-start">
      <div className="flex min-w-0 flex-1 flex-col gap-6">
        <div className="flex items-center gap-2">
          <Badge variant="accent">Placer</Badge>
          <span className="text-[11.5px] text-text-tertiary">
            Disposition planning by Placer, embedded in Iliad
          </span>
        </div>
        <DispositionSection />
        <TasksSection />
        <CommunicationsSection />
      </div>

      <div className="w-full shrink-0 lg:sticky lg:top-0 lg:w-[380px]">
        <ChatPanel patientId={patientId} />
      </div>
    </div>
  );
}
