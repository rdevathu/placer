// Controlled vocabularies mirrored from backend/ehr/models/enums.py.
// Keep values in sync with the API — they are sent verbatim as query params / body fields.

export interface EnumOption {
  value: string;
  label: string;
}

function opts(pairs: [string, string][]): EnumOption[] {
  return pairs.map(([value, label]) => ({ value, label }));
}

export const ENCOUNTER_STATUS = opts([
  ["planned", "Planned"],
  ["in-progress", "In progress"],
  ["finished", "Finished"],
  ["cancelled", "Cancelled"],
]);

export const ENCOUNTER_CLASS = opts([
  ["AMB", "Ambulatory"],
  ["IMP", "Inpatient"],
  ["EMER", "Emergency"],
  ["OBSENC", "Observation"],
  ["VR", "Virtual"],
]);

export const DISPOSITION_TYPE = opts([
  ["home", "Home"],
  ["home_with_services", "Home + services"],
  ["snf", "Skilled nursing facility"],
  ["assisted_living", "Assisted living"],
  ["inpatient_rehab", "Inpatient rehab (IRF)"],
  ["ltac", "Long-term acute care"],
  ["hospice_home", "Hospice — home"],
  ["hospice_facility", "Hospice — facility"],
  ["ama", "Against medical advice"],
  ["expired", "Expired"],
  ["undetermined", "Undetermined"],
]);

export const DISPOSITION_STATUS = opts([
  ["undetermined", "Undetermined"],
  ["predicted", "Predicted"],
  ["decided", "Decided"],
  ["in_progress", "In progress"],
  ["ready", "Ready"],
  ["discharged", "Discharged"],
]);

export const CONDITION_CATEGORY = opts([
  ["problem-list-item", "Problem list item"],
  ["encounter-diagnosis", "Encounter diagnosis"],
]);

export const CLINICAL_STATUS = opts([
  ["active", "Active"],
  ["recurrence", "Recurrence"],
  ["relapse", "Relapse"],
  ["inactive", "Inactive"],
  ["remission", "Remission"],
  ["resolved", "Resolved"],
]);

export const OBSERVATION_CATEGORY = opts([
  ["vital-signs", "Vital signs"],
  ["laboratory", "Laboratory"],
  ["imaging", "Imaging"],
  ["survey", "Survey"],
]);

export const OBSERVATION_STATUS = opts([
  ["registered", "Registered"],
  ["preliminary", "Preliminary"],
  ["pending", "Pending"],
  ["final", "Final"],
  ["amended", "Amended"],
  ["cancelled", "Cancelled"],
]);

export const MEDICATION_STATUS = opts([
  ["active", "Active"],
  ["on-hold", "On hold"],
  ["completed", "Completed"],
  ["stopped", "Stopped"],
  ["draft", "Draft"],
  ["cancelled", "Cancelled"],
]);

export const NOTE_TYPE = opts([
  ["progress", "Progress"],
  ["history_and_physical", "History & physical"],
  ["discharge_summary", "Discharge summary"],
  ["consult", "Consult"],
  ["case_management", "Case management"],
  ["nursing", "Nursing"],
  ["social_work", "Social work"],
  ["therapy", "Therapy (PT/OT/SLP)"],
  ["after_visit_summary", "After-visit summary"],
]);

export const NOTE_STATUS = opts([
  ["draft", "Draft"],
  ["signed", "Signed"],
  ["amended", "Amended"],
]);

export const ORDER_TYPE = opts([
  ["lab", "Lab"],
  ["medication", "Medication"],
  ["imaging", "Imaging"],
  ["consult", "Consult"],
  ["nursing", "Nursing"],
  ["dispo", "Disposition"],
  ["referral", "Referral"],
]);

export const ORDER_STATUS = opts([
  ["draft", "Draft (pended)"],
  ["signed", "Signed"],
  ["completed", "Completed"],
  ["cancelled", "Cancelled"],
  ["discontinued", "Discontinued"],
]);

export const ORDER_PRIORITY = opts([
  ["routine", "Routine"],
  ["urgent", "Urgent"],
  ["stat", "STAT"],
]);

export const TASK_TYPE = opts([
  ["call_snf", "Call SNF"],
  ["call_family", "Call family"],
  ["call_pcp", "Call PCP"],
  ["order_lab", "Order lab"],
  ["draft_consult", "Draft consult"],
  ["insurance_auth", "Insurance authorization"],
  ["collect_preference", "Collect preference"],
  ["verify_eligibility", "Verify eligibility"],
  ["arrange_transport", "Arrange transport"],
  ["other", "Other"],
]);

export const TASK_STATUS = opts([
  ["pending", "Pending"],
  ["in_progress", "In progress"],
  ["blocked", "Blocked"],
  ["completed", "Completed"],
  ["cancelled", "Cancelled"],
]);

export const TASK_PRIORITY = opts([
  ["low", "Low"],
  ["medium", "Medium"],
  ["high", "High"],
]);

export const FACILITY_TYPE = opts([
  ["snf", "Skilled nursing facility"],
  ["assisted_living", "Assisted living"],
  ["inpatient_rehab", "Inpatient rehab"],
  ["ltac", "Long-term acute care"],
  ["hospice", "Hospice"],
  ["home_health", "Home health"],
  ["dme", "Durable medical equipment"],
]);

export const COMM_DIRECTION = opts([
  ["outbound", "Outbound"],
  ["inbound", "Inbound"],
]);

export const COMM_MODALITY = opts([
  ["phone", "Phone"],
  ["sms", "SMS"],
  ["fax", "Fax"],
  ["email", "Email"],
  ["portal", "Portal"],
]);

export const PARTY_TYPE = opts([
  ["family", "Family"],
  ["patient", "Patient"],
  ["snf", "SNF"],
  ["facility", "Facility"],
  ["pcp", "PCP"],
  ["insurance", "Insurance"],
  ["other", "Other"],
]);

function toLabelMap(list: EnumOption[]): Record<string, string> {
  return Object.fromEntries(list.map((o) => [o.value, o.label]));
}

export const LABELS = {
  encounterStatus: toLabelMap(ENCOUNTER_STATUS),
  encounterClass: toLabelMap(ENCOUNTER_CLASS),
  dispositionType: toLabelMap(DISPOSITION_TYPE),
  dispositionStatus: toLabelMap(DISPOSITION_STATUS),
  conditionCategory: toLabelMap(CONDITION_CATEGORY),
  clinicalStatus: toLabelMap(CLINICAL_STATUS),
  observationCategory: toLabelMap(OBSERVATION_CATEGORY),
  observationStatus: toLabelMap(OBSERVATION_STATUS),
  medicationStatus: toLabelMap(MEDICATION_STATUS),
  noteType: toLabelMap(NOTE_TYPE),
  noteStatus: toLabelMap(NOTE_STATUS),
  orderType: toLabelMap(ORDER_TYPE),
  orderStatus: toLabelMap(ORDER_STATUS),
  taskType: toLabelMap(TASK_TYPE),
  taskStatus: toLabelMap(TASK_STATUS),
  facilityType: toLabelMap(FACILITY_TYPE),
  commModality: toLabelMap(COMM_MODALITY),
  partyType: toLabelMap(PARTY_TYPE),
};

export function humanize(value?: string | null): string {
  if (!value) return "";
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
