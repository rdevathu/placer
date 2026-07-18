import { Navigate, Route, Routes } from "react-router-dom";
import App from "./App";
import PatientsPage from "./pages/PatientsPage";
import PatientDetailPage from "./pages/PatientDetailPage";
import OverviewTab from "./pages/patient/OverviewTab";
import EncountersTab from "./pages/patient/EncountersTab";
import ProblemsTab from "./pages/patient/ProblemsTab";
import MedicationsTab from "./pages/patient/MedicationsTab";
import OrdersTab from "./pages/patient/OrdersTab";
import NotesTab from "./pages/patient/NotesTab";
import LabsTab from "./pages/patient/LabsTab";
import PlacerTab from "./pages/patient/placer/PlacerTab";
import FacilitiesPage from "./pages/FacilitiesPage";
import AdminPage from "./pages/AdminPage";
import NotFoundPage from "./pages/NotFoundPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<App />}>
        <Route index element={<Navigate to="/patients" replace />} />
        <Route path="patients" element={<PatientsPage />} />
        <Route path="patients/:id" element={<PatientDetailPage />}>
          <Route index element={<OverviewTab />} />
          <Route path="encounters" element={<EncountersTab />} />
          <Route path="problems" element={<ProblemsTab />} />
          <Route path="medications" element={<MedicationsTab />} />
          <Route path="orders" element={<OrdersTab />} />
          <Route path="notes" element={<NotesTab />} />
          <Route path="labs" element={<LabsTab />} />
          <Route path="placer" element={<PlacerTab />} />
          {/* Legacy per-patient tabs — everything moved into the Placer tab. */}
          <Route path="disposition" element={<Navigate to="../placer" replace />} />
          <Route path="tasks" element={<Navigate to="../placer" replace />} />
          <Route path="communications" element={<Navigate to="../placer" replace />} />
        </Route>
        <Route path="facilities" element={<FacilitiesPage />} />
        {/* Legacy global care-tasks worklist — removed with the Placer tab refactor. */}
        <Route path="tasks" element={<Navigate to="/patients" replace />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
