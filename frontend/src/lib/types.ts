// Response shapes mirrored from backend/ehr/models/*.py (SQLModel.model_dump()).
// All tables carry created_at/updated_at (TimestampMixin); raw_fhir is stripped
// from responses unless ?include_raw=true is passed.

export interface Patient {
  id: string;
  mrn: string;
  family_name: string | null;
  given_name: string | null;
  prefix: string | null;
  full_name: string | null;
  gender: string | null;
  birth_date: string | null;
  deceased: boolean;
  marital_status: string | null;
  language: string | null;
  phone: string | null;
  address_line: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  emergency_contact_name: string | null;
  emergency_contact_relationship: string | null;
  emergency_contact_phone: string | null;
  living_situation: string | null;
  code_status: string | null;
  age: number | null;
  created_at: string;
  updated_at: string;
}

export interface Encounter {
  id: string;
  patient_id: string;
  status: string;
  class_code: string | null;
  class_display: string | null;
  type_code: string | null;
  type_text: string | null;
  visit_title: string | null;
  reason_code: string | null;
  reason_text: string | null;
  period_start: string | null;
  period_end: string | null;
  admit_source: string | null;
  location_display: string | null;
  service_provider_display: string | null;
  attending_name: string | null;
  attending_npi: string | null;
  disposition_status: string;
  planned_disposition: string | null;
  created_at: string;
  updated_at: string;
}

export interface Condition {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  code_system: string | null;
  code: string | null;
  display: string | null;
  category: string | null;
  clinical_status: string | null;
  verification_status: string | null;
  onset_date: string | null;
  abatement_date: string | null;
  recorded_date: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface Observation {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  diagnostic_report_id: string | null;
  category: string;
  loinc_code: string | null;
  display: string | null;
  value_num: number | null;
  value_unit: string | null;
  value_string: string | null;
  has_components: boolean;
  reference_range_low: number | null;
  reference_range_high: number | null;
  abnormal_flag: string | null;
  interpretation: string | null;
  status: string;
  effective_time: string | null;
  issued_time: string | null;
  created_at: string;
  updated_at: string;
}

export interface DiagnosticReport {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  loinc_code: string | null;
  display: string | null;
  category: string | null;
  status: string;
  effective_time: string | null;
  issued_time: string | null;
  performer_display: string | null;
  conclusion: string | null;
  created_at: string;
  updated_at: string;
  results?: Observation[];
}

export interface Medication {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  code_system: string | null;
  code: string | null;
  display: string | null;
  dose: string | null;
  route: string | null;
  frequency: string | null;
  dosage_text: string | null;
  status: string;
  intent: string | null;
  category: string | null;
  authored_on: string | null;
  requester_display: string | null;
  created_at: string;
  updated_at: string;
}

export interface Note {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  note_type: string;
  title: string | null;
  text: string;
  author: string | null;
  author_role: string | null;
  authored_by_agent: boolean;
  status: string;
  signed_by: string | null;
  signed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  order_type: string;
  status: string;
  code: string | null;
  display: string;
  detail: string | null;
  priority: string;
  ordered_by: string | null;
  signed_by: string | null;
  authored_at: string | null;
  signed_at: string | null;
  completed_at: string | null;
  result_observation_id: string | null;
  linked_care_task_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DispoAssessment {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  predicted_disposition: string;
  confidence: number | null;
  rationale: string | null;
  barriers: string[] | null;
  alternatives: { disposition: string; confidence?: number }[] | null;
  assessed_by: string | null;
  is_current: boolean;
  created_at: string;
  updated_at: string;
}

export interface Facility {
  id: string;
  name: string;
  facility_type: string;
  city: string | null;
  state: string | null;
  phone: string | null;
  total_beds: number | null;
  available_beds: number | null;
  accepts_covid_positive: boolean;
  accepts_medicaid: boolean;
  insurance_accepted: string[] | null;
  specialties: string[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CareTask {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  task_type: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  assigned_to: string | null;
  due_at: string | null;
  related_facility_id: string | null;
  related_order_id: string | null;
  result_summary: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Communication {
  id: string;
  patient_id: string;
  care_task_id: string | null;
  facility_id: string | null;
  direction: string;
  modality: string;
  party_type: string | null;
  party_name: string | null;
  summary: string | null;
  transcript: string | null;
  outcome: string | null;
  occurred_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientChart {
  patient: Patient;
  active_encounter: Encounter | null;
  active_problems: Condition[];
  medications: Medication[];
  latest_vitals: Observation[];
  pending_labs: Observation[];
  abnormal_labs: Observation[];
  current_disposition: DispoAssessment | null;
  open_care_tasks: CareTask[];
  open_orders: Order[];
}

export interface PlacerMessage {
  id: string;
  patient_id: string;
  sender: "provider" | "placer";
  sender_name: string | null;
  text: string;
  created_at: string;
  updated_at: string;
}

export interface AdminStats {
  [table: string]: number;
}
