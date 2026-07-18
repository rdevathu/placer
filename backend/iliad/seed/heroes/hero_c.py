"""Hero C — Giulia Bianchi, 84F, metastatic pancreatic cancer, DNR.

The hospice storyline: comfort-focused goals of care after a year of
disease-directed therapy, a daughter who is the primary caregiver and is
running on empty, and a live home-hospice-vs-facility decision. Prior chart: a
May 2026 biliary stent admission, three oncology visits tracing the arc from
treatment to progression to stopping, and an outpatient goals-of-care call.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session

from ...models import CareTask, Communication, DispoAssessment, Patient
from .common import NOW, condition, encounter, med, note, placer_msg, vital

PID = "hero-c-hospice"
ENC_CURRENT = "enc-hero-c"
ENC_STENT = "enc-hero-c-2026-stent"
ENC_ONC_DEC = "enc-hero-c-2025-onc"
ENC_ONC_FEB = "enc-hero-c-2026-onc-feb"
ENC_ONC_JUN = "enc-hero-c-2026-onc-jun"

ADMIT = NOW - timedelta(days=5)  # 2026-07-13 08:00
STENT_START = datetime(2026, 5, 5, 11, 0)
STENT_END = datetime(2026, 5, 7, 14, 0)
ONC_DEC_START = datetime(2025, 12, 15, 10, 0)
ONC_FEB_START = datetime(2026, 2, 20, 14, 0)
ONC_JUN_START = datetime(2026, 6, 22, 10, 30)


# ---------------------------------------------------------------------------
# Current admission notes
# ---------------------------------------------------------------------------

HP_CURRENT = """# Medicine/Oncology History & Physical

**Chief Complaint:** Uncontrolled abdominal pain and inability to eat.

**HPI:** Mrs. Giulia Bianchi is an 84-year-old woman with metastatic pancreatic adenocarcinoma (diagnosed November 2025; liver metastases March 2026; disease-directed therapy stopped June 2026) who presents from her daughter's home with one week of escalating epigastric and back pain no longer controlled by oral oxycodone, near-absent oral intake, and progressive weakness. Her daughter reports she has spent most of the last week in bed or a recliner, needs help to reach the bathroom, and has had two near-falls at night. Weight is down approximately 8 kg over three months. No fever, vomiting, melena, or jaundice since her biliary stent (May 2026). Pain is 8/10, boring, radiating to the back, worse with any oral intake. She was admitted for pain control and, per the family's request at the June oncology visit, to formalize hospice planning.

**Review of Systems:** Positive for pain, anorexia, fatigue, constipation (opioid-related), poor sleep. Negative for fever, chills, vomiting, diarrhea, dysuria, new jaundice. Otherwise negative in 10 systems.

**Past Medical History:**
1. Metastatic pancreatic adenocarcinoma (head of pancreas; dx 11/2025 after painless jaundice; liver metastases 3/2026; three cycles gemcitabine/nab-paclitaxel 12/2025-2/2026, stopped for progression and declining function; disease-directed therapy formally concluded 6/2026)
2. Malignant biliary obstruction s/p ERCP with metal stent (5/2026)
3. Hypertension, well controlled
4. Osteoporosis; remote right wrist fracture

**Past Surgical History:** Total abdominal hysterectomy (1989). ERCP with metal biliary stent placement (5/2026).

**Home Medications:**
- Oxycodone 5-10 mg PO q4h PRN pain (escalating use, ~50 mg/day this week)
- Docusate/senna daily
- Amlodipine 5 mg PO daily
- Ondansetron 4 mg PO q8h PRN nausea
- Mirtazapine 7.5 mg PO nightly (appetite/sleep)

**Allergies:** Penicillin (rash).

**Social History:** Widowed 2020; retired seamstress; emigrated from Italy in 1964, bilingual Italian/English. Moved in with her daughter Lucia Ferraro (Newton) in April 2026 when she could no longer manage her own apartment; the apartment has since been given up. Daughter's home: first-floor guest room and full bathroom, four steps at the entry. Functional status: three months ago she walked unassisted and cooked Sunday dinners; now ECOG 3 — out of bed less than half the day, needs standby-to-contact assist for transfers and walking to the bathroom, needs help bathing and dressing, continent. Daughter is the sole caregiver: works part-time (mornings), manages all medications, meals, and appointments, and is up with her mother one to two times most nights. Daughter is devoted but by her own account "running on fumes"; no other local family — son in Milan calls weekly. Never smoker; no alcohol. Insurance: traditional Medicare with Medigap supplement — hospice benefit available and unrestricted.

**Family History:** Husband died of lung cancer 2020. Sister with breast cancer. Parents died elderly, causes unknown.

**Physical Exam:**
- Vitals: T 36.7, HR 102, BP 96/60, RR 18, SpO2 94% RA.
- General: Cachectic, temporal wasting, tired but conversant and clear.
- HEENT: Sclerae anicteric. Dry mucous membranes.
- Cardiac: Regular, tachycardic, no murmur.
- Pulmonary: Shallow effort, clear, decreased breath sounds at the right base.
- Abdomen: Scaphoid, epigastric tenderness without rebound, palpable firm liver edge 4 cm below the costal margin, no ascites clinically.
- Extremities: Marked muscle wasting, trace ankle edema, no calf tenderness.
- Neurologic: Alert, oriented x3, no asterixis. Gets to sitting with assistance.

**Labs/Imaging:** Hgb 9.8, WBC 11.2, plt 320. Na 131, K 3.8, Cr 0.8, albumin 2.1, T bili 1.4 (stent patent), CA 19-9 4,850 (rising). CT abdomen (admission): enlarging pancreatic head mass encasing the celiac axis, innumerable hepatic metastases, no bowel obstruction, patent stent, small right pleural effusion.

**Assessment & Plan:** 84-year-old woman with metastatic pancreatic adenocarcinoma, off disease-directed therapy, admitted with a pain crisis and profound functional decline — prognosis weeks to a few months. DNR/DNI confirmed on admission with patient and daughter.

1. **Cancer pain crisis:** Start IV morphine 2 mg q2h PRN with rapid titration to a scheduled/PCA regimen per palliative care; convert to an oral/long-acting regimen for discharge. Aggressive bowel regimen alongside.
2. **Nausea/anorexia/cachexia:** Ondansetron PRN; continue mirtazapine; no artificial nutrition per patient's clearly stated wishes.
3. **Metastatic pancreatic cancer:** No further disease-directed therapy (decision made 6/2026 with oncology). Formal palliative care consult placed.
4. **Hyponatremia/hypotension:** Consistent with disease state and intake; gentle approach only, no aggressive correction — comfort is the goal.
5. **Disposition:** Hospice is the appropriate frame — she meets eligibility (metastatic pancreatic cancer, ECOG 3, weight loss, off treatment). The live question is SETTING: patient and daughter have consistently preferred home (daughter's house is physically workable — first-floor bedroom and bath), but the daughter is a sole caregiver already up most nights, and this admission was precipitated partly by caregiver exhaustion. Options: home hospice with maximal support (aide hours, volunteer respite, continuous-care nursing during symptom crises) versus general inpatient/residential hospice. Palliative care to lead a family meeting; social work to assess caregiver capacity honestly rather than aspirationally. Medicare hospice benefit — no coverage barrier. Case management to engage Peaceful Passages (serves Newton, offers both home and inpatient programs).
"""

PROG_D1 = """# Progress Note — Hospital Day 1

**Subjective:** Pain improved to 4-5/10 on IV morphine, "first real sleep in a week." Took a few spoonfuls of gelato — meaningful to her. Daughter at bedside most of the day; visibly exhausted.

**Objective:** T 36.8, HR 96, BP 98/62, SpO2 94% RA. Used 14 mg IV morphine in 24h. Abdomen unchanged. No delirium (CAM negative).

**Assessment/Plan:** Metastatic pancreatic cancer with pain crisis, responding to opioid titration.
- Convert tonight to scheduled morphine with PRN breakthrough based on 24h use; bowel regimen escalated, last BM today.
- Palliative care consulted — seeing her tomorrow; family meeting to be scheduled with daughter present.
- Confirmed DNR/DNI order in chart; MOLST at bedside matches.
- Dispo: hospice planning to begin — social work to meet the daughter alone to assess caregiver capacity for home hospice.

— Dr. Helen Sørensen, Medicine/Oncology
"""

PROG_D2 = """# Progress Note — Hospital Day 2

**Subjective:** Comfortable at rest, pain 3/10. Sat in the chair for two hours. Asking when she can go back to her daughter's house — "I want my chair by the window."

**Objective:** T 36.7, HR 94, BP 100/60, SpO2 94% RA. On scheduled morphine q4h with PRN; two breakthrough doses in 24h. Tolerating sips and bites without nausea.

**Assessment/Plan:** Pain regimen converging; goals-of-care work proceeding.
- Continue current regimen; plan conversion to long-acting oral morphine + concentrate for breakthrough at discharge.
- Palliative care saw her today (see consult when filed); recommends hospice, agrees home is feasible IF caregiver support is shored up.
- Social work met daughter separately: committed to home but tearful about nights; exploring aide hours and what the hospice benefit actually covers.
- Family meeting set for tomorrow afternoon with palliative care, SW, daughter (son joining by phone from Milan).

— Dr. Helen Sørensen, Medicine/Oncology
"""

PROG_D3 = """# Progress Note — Hospital Day 3

**Subjective:** Comfortable. Family meeting held this afternoon (documented separately). Patient clear and consistent: she wants to be at her daughter's home, in her chair, with her rosary — "no more hospitals."

**Objective:** T 36.6, HR 90, BP 102/62, SpO2 95% RA. Stable low-dose scheduled morphine, one breakthrough dose in 24h. Eating small amounts. Transfers with one assist.

**Assessment/Plan:** Metastatic pancreatic cancer, symptoms controlled; disposition converging on home hospice.
- Started conversion to long-acting oral morphine this evening; observe 24-48h for stability before discharge.
- Family leaning strongly to home hospice; daughter's night-coverage worry is the open issue — hospice continuous-care criteria and respite options to be laid out concretely before a final decision.
- Case management engaging Peaceful Passages (covers Newton, runs both home hospice and GIP) for intake.
- Anticipate discharge in 2-3 days if the oral regimen holds.

— Dr. Helen Sørensen, Medicine/Oncology
"""

PROG_D4 = """# Progress Note — Hospital Day 4

**Subjective:** "Today was a good day." Pain 2-3/10 on the oral long-acting regimen. Daughter reports feeling "lighter" after the meeting — says knowing a nurse comes to the house changes everything.

**Objective:** T 36.7, HR 92, BP 98/60, SpO2 94% RA. 24h on long-acting oral morphine with one breakthrough dose; no nausea; BM yesterday. Ambulated to the door with one assist.

**Assessment/Plan:** Stable on a discharge-ready oral regimen.
- Continue long-acting morphine + concentrate for breakthrough; bowel regimen scheduled, not PRN.
- Hospice referral packet sent to Peaceful Passages; awaiting intake confirmation, election form, and attending certification of terminal illness.
- Home logistics: hospital bed, bedside commode, and shower chair to be ordered through hospice DME once election signed.
- If intake confirms, target discharge tomorrow or the day after with hospice admission the same day at the daughter's home.

— Dr. Helen Sørensen, Medicine/Oncology
"""

PALLIATIVE_CONSULT = """# Palliative Care Consult

**Reason for consult:** Goals of care and symptom management in metastatic pancreatic cancer.

**HPI:** 84-year-old woman with metastatic pancreatic adenocarcinoma (off disease-directed therapy since June), admitted with a pain crisis and functional decline. I have followed her since an outpatient goals-of-care discussion in June; she has been consistent throughout: comfort is the goal, no more hospitals, no artificial nutrition, no resuscitation.

**Symptoms:** Pain now well controlled on scheduled opioids (3/10). Appetite poor but she enjoys tastes of food. Sleep improved. No delirium. Breathlessness mild, positional. Mood: tired, not depressed — "I have had a full life; I want a peaceful end of it."

**Goals of care:** Re-confirmed with patient (in English and Italian) and daughter at the bedside. DNR/DNI; MOLST current and in chart. She declines further scans, labs beyond what comfort requires, and any future admission if avoidable. She wishes to die at her daughter's home if her care does not "crush" her daughter — she said this looking directly at Lucia.

**Assessment:** Hospice-appropriate by any measure: metastatic pancreatic cancer off therapy, ECOG 3-4, cachexia with 8 kg loss, albumin 2.1. Prognosis weeks to a short number of months. The clinical work remaining is not prognostic — it is operational: matching the care setting to a devoted but depleted sole caregiver.

**Recommendations:**
1. Convert to long-acting oral morphine with concentrate for breakthrough (done with primary team); scheduled bowel regimen.
2. Hospice referral now, not at discharge — recommend Peaceful Passages (serves Newton; runs home hospice, continuous care, respite, and GIP under one roof, which matters for this family).
3. Home hospice is feasible and preference-concordant IF the plan explicitly protects the daughter: aide hours, volunteer coverage, low threshold for continuous-care nursing during symptom crises, and GIP as a named fallback rather than a failure.
4. Family meeting to finalize setting (scheduled).
5. I will follow through discharge and hand off to the hospice medical director.

— Dr. Omar Haddad, Palliative Care
"""

FAM_CURRENT = """# Family Meeting — Goals of Care and Disposition

Family meeting held in the 8 North conference room, ~50 minutes. Present: patient (by wheelchair, participated throughout), daughter Lucia Ferraro, son Marco Bianchi (by phone from Milan), Dr. Haddad (palliative care), Dr. Sørensen (attending), this writer (social work), bedside RN.

Prognosis was reviewed honestly and gently; the patient nodded and said she understood — "weeks, maybe a season." Hospice philosophy and the Medicare benefit were explained: nurse visits, aide hours, 24/7 phone support, continuous-care nursing during crises, respite admissions, and general inpatient care if symptoms cannot be managed at home. The patient stated her preference clearly and repeatedly: home, at her daughter's house. The daughter affirmed she wants this too, then — with the patient holding her hand — was able to say aloud that nights frighten her: she has not slept a full night in a month and is afraid of "doing it wrong" if symptoms escalate at 3 a.m. The son offered to fund private aide hours and to come for two weeks in August.

Consensus reached: pursue HOME HOSPICE with Peaceful Passages, with night-coverage support built into the plan up front (aide hours, respite scheduling, continuous-care criteria reviewed in writing) and GIP named explicitly as the backup, not a failure. Daughter visibly relieved by the framing. Election paperwork to follow intake.

— Miriam Katz, LCSW, Oncology Social Work
"""

# ---------------------------------------------------------------------------
# Prior biliary stent admission (May 2026)
# ---------------------------------------------------------------------------

HP_STENT = """# Medicine History & Physical — Obstructive Jaundice

**Chief Complaint:** Yellowing of the eyes and dark urine.

**HPI:** Mrs. Giulia Bianchi is an 84-year-old woman with metastatic pancreatic adenocarcinoma (dx 11/2025, liver metastases confirmed 3/2026, chemotherapy stopped 2/2026 after three cycles for progression and toxicity) who presents with four days of progressive scleral icterus, dark urine, pale stools, and generalized itching that has kept her awake at night. Her daughter noticed the color change at Sunday dinner and called the oncology clinic, which directed her to the emergency department. She reports mild epigastric discomfort unchanged from her baseline cancer pain, controlled on her home oxycodone. No fever, rigors, confusion, vomiting, or melena; she has been eating small amounts and drinking adequately. Labs in the ED: total bilirubin 9.2, alkaline phosphatase 640, AST/ALT mildly elevated, consistent with malignant biliary obstruction at the level of her known pancreatic head mass; no leukocytosis or hemodynamic signs of cholangitis. GI was consulted from the ED and she was admitted for ERCP and stent placement, a comfort-directed intervention discussed with and desired by the patient and her daughter.

**Review of Systems:** Positive for jaundice, pruritus, dark urine, pale stools, fatigue, poor appetite. Negative for fever, rigors, vomiting, melena, confusion. Otherwise negative in 10 systems.

**Past Medical History:** Metastatic pancreatic adenocarcinoma (as above). Hypertension. Osteoporosis.

**Past Surgical History:** Total abdominal hysterectomy (1989).

**Home Medications:** Oxycodone 5 mg PO q6h PRN pain; amlodipine 5 mg daily; mirtazapine 7.5 mg nightly; docusate/senna; ondansetron PRN.

**Allergies:** Penicillin (rash).

**Social History:** Widowed. Moved in with her daughter Lucia in Newton last month after giving up her apartment; first-floor bedroom and bath. Ambulating short distances independently at home, needs help with bathing; daughter manages medications and meals and works part-time mornings. Never smoker, no alcohol. Insurance: traditional Medicare + Medigap.

**Family History:** Husband died of lung cancer. Sister with breast cancer.

**Physical Exam:**
- Vitals: T 37.0, HR 92, BP 108/64, RR 16, SpO2 96% RA.
- General: Thin, icteric, comfortable.
- HEENT: Scleral icterus. Excoriations from scratching on forearms.
- Cardiac: Regular, no murmur.
- Pulmonary: Clear bilaterally.
- Abdomen: Soft, mild epigastric tenderness, liver edge palpable, no peritonitis, negative Murphy.
- Neurologic: Alert, oriented x3, no asterixis.

**Labs/Imaging:** T bili 9.2 (direct 7.1), AlkP 640, AST 118, ALT 96. WBC 8.4, no fever — no cholangitis clinically. CT: pancreatic head mass compressing the common bile duct, intrahepatic ductal dilation, stable hepatic metastases.

**Assessment & Plan:** 84-year-old woman with malignant biliary obstruction from her known pancreatic head mass, without cholangitis, admitted for endoscopic decompression.
1. **Obstructive jaundice:** NPO after midnight; ERCP with uncovered metal stent placement tomorrow morning (GI consulted and has seen her; risks including post-ERCP pancreatitis, bleeding, and perforation discussed and consented with the daughter present). Metal rather than plastic stent chosen for durability given her prognosis — the intent is that she never needs this procedure again.
2. **Pruritus:** Cholestyramine deferred until the stent's effect is seen (and to avoid binding her other medications); emollients and an antihistamine tonight for sleep.
3. **Pain:** Continue home oxycodone regimen; no escalation needed at present.
4. **Goals of care:** DNR/DNI confirmed on admission with patient and daughter; MOLST reviewed and in chart. All parties aligned that this procedure is comfort-directed — relieving the obstruction treats the itching and prevents cholangitis, and does not represent a change in the overall trajectory or a return to disease-directed therapy.
5. **Nutrition/functional status:** Poor intake and gradual decline noted, appropriate to disease stage; no artificial nutrition, consistent with her stated wishes. Up with assistance; fall precautions.
6. **Disposition:** Anticipate discharge HOME to her daughter's house within 48 hours if the stent is successful and bilirubin trends down. She has good support there — first-floor bedroom and bath, daughter managing medications and meals — and no new services are expected beyond her June oncology follow-up, where the overall direction of care will be revisited.
"""

STENT_PROG_1 = """# Progress Note — Stent Admission, Day 1

**Subjective:** Underwent ERCP this morning; comfortable afterward, no abdominal pain beyond baseline. Itching already "less maddening." Daughter at bedside.

**Objective:** T 36.9, HR 88, BP 110/66, SpO2 96% RA. Post-ERCP exam benign — soft abdomen, no new tenderness. Lipase normal post-procedure.

**Assessment/Plan:** Successful ERCP with uncovered metal stent across the distal CBD stricture; good bile flow observed. No post-ERCP pancreatitis. Diet advanced this evening, tolerated. Recheck LFTs in the morning; if bilirubin trending down and she eats breakfast without issue, discharge home tomorrow.

— Dr. Rachel Lindqvist, Medicine
"""

STENT_PROG_2 = """# Progress Note — Stent Admission, Day 2

**Subjective:** Feels better than she has in two weeks. Ate most of breakfast. Ready to go back to her daughter's — "my granddaughter is visiting Saturday."

**Objective:** T 36.8, HR 86, BP 112/68. T bili 9.2 -> 5.6, AlkP falling. Abdomen benign.

**Assessment/Plan:** Bilirubin falling appropriately after metal stent; no complications. Discharge home this afternoon with daughter. Oncology follow-up already scheduled in June; return precautions (fever, rigors, recurrent jaundice — stent occlusion/cholangitis) reviewed with patient and daughter, teach-back successful.

— Dr. Rachel Lindqvist, Medicine
"""

STENT_DC = """# Discharge Summary — Biliary Stent Admission (May 2026)

**Admission Diagnosis:** Obstructive jaundice.
**Discharge Diagnoses:** 1. Malignant biliary obstruction, s/p ERCP with metal stent. 2. Metastatic pancreatic adenocarcinoma. 3. Pruritus secondary to cholestasis, improving.

**Hospital Course:** 84-year-old woman with metastatic pancreatic cancer admitted with painless progressive jaundice (T bili 9.2). ERCP on hospital day 1 placed an uncovered metal stent across a distal CBD stricture from the known pancreatic head mass, with immediate bile flow and no post-procedure pancreatitis. Bilirubin fell to 5.6 by discharge and pruritus improved. She remained afebrile without cholangitis. DNR/DNI status was confirmed and maintained throughout.

**Discharge Medications:** Unchanged from home: oxycodone 5 mg q6h PRN; amlodipine 5 mg daily; mirtazapine 7.5 mg nightly; docusate/senna; ondansetron PRN.

**Disposition:** Discharged HOME to her daughter's house in Newton, where she lives with first-floor bedroom and bath; daughter continues to manage medications and meals. No new home services required at this time.

**Follow-up:** Oncology (Dr. Krishnan) June 22 — visit will include discussion of overall direction of care given treatment was stopped in February. LFT recheck via PCP in 2 weeks. Return precautions for stent occlusion or cholangitis reviewed.

— Dr. Rachel Lindqvist, Medicine
"""

# ---------------------------------------------------------------------------
# Oncology clinic notes
# ---------------------------------------------------------------------------

ONC_DEC_NOTE = """# Oncology Clinic Note — Cycle 1 Review

**Subjective:** 83F with pancreatic adenocarcinoma (dx last month), here with daughter after cycle 1 of gemcitabine/nab-paclitaxel. Fatigue for 3-4 days after infusion, mild neuropathy in fingertips, appetite fair on mirtazapine. Pain controlled on oxycodone 5 mg once or twice daily. Walking daily around the block. Spirits good — "I want to see what this does."

**Objective:** ECOG 1. Weight 61.2 kg (stable). Labs adequate for treatment: ANC 2.1, plt 180, Cr 0.7, bili 0.9. Exam: no jaundice, abdomen soft.

**Assessment/Plan:** Locally advanced pancreatic head adenocarcinoma on first-line gemcitabine/nab-paclitaxel, tolerating cycle 1 acceptably at her age.
1. Proceed with cycle 2 at current doses; monitor neuropathy closely — dose-reduce nab-paclitaxel if it progresses.
2. CA 19-9 today 890 (baseline 1,120) — early favorable trend.
3. Restaging CT after cycle 3 (February).
4. Supportive care: continue mirtazapine, bowel regimen with opioids; nutrition referral placed.
5. Discussed prognosis honestly at the family's request; goals for now are disease control and preserved independence. Return in February with scan.

— Dr. Anand Krishnan, Oncology
"""

ONC_FEB_NOTE = """# Oncology Clinic Note — Restaging After Cycle 3

**Subjective:** 83F after cycle 3 of gemcitabine/nab-paclitaxel. The winter has been harder: fatigue now lasts most of each cycle, neuropathy in fingers and toes, two falls without injury, and her daughter reports she has stopped her daily walks. Pain up modestly (oxycodone 3-4 doses/day). Weight down 3 kg since December.

**Objective:** ECOG 2. Weight 58.1 kg. CA 19-9 2,140 (rising from nadir 780). Restaging CT (yesterday): primary mass enlarged from 3.1 to 4.2 cm, now abutting the celiac axis; several new sub-centimeter hepatic lesions — findings discussed with radiology, consistent with progression (formal confirmation of hepatic disease to follow on dedicated imaging).

**Assessment/Plan:** Progression on first-line therapy with declining performance status — a turning point conversation held today with patient and daughter.
1. Recommended STOPPING gemcitabine/nab-paclitaxel: progression plus toxicity in an 83-year-old means further cycles are more likely to harm than help. Patient agreed without hesitation; daughter tearful but supportive.
2. Second-line therapy discussed and not recommended given ECOG 2-3 trajectory; patient declines — "no more if it won't cure me."
3. Focus shifts to symptom control: pain regimen adjusted; palliative care referral placed for goals-of-care support.
4. Dedicated liver MRI to characterize new lesions.
5. Return June or sooner; daughter has clinic's direct line.

— Dr. Anand Krishnan, Oncology
"""

ONC_JUN_NOTE = """# Oncology Clinic Note — Transition of Care

**Subjective:** 84F with metastatic pancreatic adenocarcinoma (liver metastases confirmed on March MRI), off treatment since February. Since the May stent admission: appetite poor, weight down further, now out of bed less than half the day. Needs help bathing and dressing; daughter assists with transfers on bad days. Pain requires oxycodone around the clock. She is clear today: "No more procedures unless they keep me comfortable."

**Objective:** ECOG 3. Weight 54.8 kg (down 8 kg since March). Cachectic, anicteric (stent functioning). CA 19-9 4,100. No labs beyond comfort-directed panel; no further imaging planned.

**Assessment/Plan:** Metastatic pancreatic cancer with progressive functional decline off therapy — prognosis on the order of weeks to a few months.
1. No disease-directed therapy; this was formally re-confirmed today and the treatment chapter closed with gratitude on both sides.
2. HOSPICE discussed as the right framework going forward; patient receptive, daughter asks how nights would work — referred to palliative care (Dr. Haddad) for a goals-of-care discussion including the family this week (call arranged).
3. Pain: transitioned plan toward scheduled dosing; prescriptions adjusted.
4. I remain available to the family, but ongoing care will center on palliative/hospice services.

— Dr. Anand Krishnan, Oncology
"""

FAM_GOC_JUN = """# Family Communication — Outpatient Goals-of-Care Call

Telephone goals-of-care discussion following Dr. Krishnan's June visit, arranged at the family's request; ~35 minutes. On the line: patient (speakerphone at daughter's home), daughter Lucia Ferraro, this writer.

Reviewed where things stand: metastatic pancreatic cancer, off treatment, energy fading — the patient summarized it herself: "the medicine part is over." Explored what matters most: being at her daughter's home, her chair by the window, her rosary, seeing her granddaughter in August, and not burdening Lucia "past what a daughter should carry." She reiterated DNR/DNI without hesitation; MOLST already current. Introduced hospice concretely — what a nurse visit looks like, aide hours, the 24/7 line, and that hospice is about more presence at home, not less care. Daughter asked most of the questions, nearly all about nights and emergencies; described continuous-care and GIP options. Neither felt ready to enroll today — the patient wants "one more good month first." Agreed: no pressure now, revisit within 4-6 weeks or immediately if symptoms escalate; they know how to reach me directly.

Impression: patient with clear, stable comfort-focused goals; daughter loving and capable but at risk of caregiver collapse — night coverage will decide whether home hospice succeeds.

— Dr. Omar Haddad, Palliative Care
"""

# ---------------------------------------------------------------------------
# Placer chat
# ---------------------------------------------------------------------------

CHAT = [
    ("placer", "Placer", -30.0,
     "Reviewed Mrs. Bianchi's chart. Predicting home hospice (82%): metastatic pancreatic cancer off "
     "treatment, ECOG 3, DNR/DNI, consistent comfort-focused goals across oncology, palliative, and "
     "the family meeting. Setting is the open question — daughter is a sole caregiver already up most "
     "nights. I'm starting intake with Peaceful Passages (covers Newton, runs both home hospice and "
     "GIP)."),
    ("placer", "Placer", -10.0,
     "Called Peaceful Passages intake: referral packet received; they can admit to home hospice the "
     "same day she discharges. Outstanding items: signed hospice election form and the attending's "
     "certification of terminal illness (CTI). They confirmed continuous-care nursing and respite are "
     "available for the night-coverage concern, and Medicare covers all of it."),
    ("placer", "Placer", -6.0,
     "Question for the team: the family is leaning home hospice but the daughter's worry is nights. "
     "Should I set up home hospice with GIP named as the explicit backup (per Dr. Haddad's consult), "
     "or hold everything until the family's final confirmation after this afternoon's palliative "
     "touch-base?"),
    ("provider", "Dr. Helen Sørensen", -3.0,
     "Proceed with home hospice planning — I'll sign the CTI today. Palliative care is meeting the "
     "family again this afternoon; hold final confirmation to Peaceful Passages until after that, "
     "but keep everything staged so nothing delays discharge."),
    ("placer", "Placer", -1.0,
     "Staged and holding: election form prepped for signature, CTI to you for signing, DME list "
     "ready (hospital bed, bedside commode, shower chair) for delivery to the daughter's home in "
     "Newton once confirmed. I'll finalize with Peaceful Passages the moment the family confirms."),
]


def build(session: Session) -> None:
    session.add(
        Patient(
            id=PID,
            mrn="MRN90003",
            family_name="Bianchi",
            given_name="Giulia",
            prefix="Mrs.",
            full_name="Mrs. Giulia Bianchi",
            gender="female",
            birth_date=datetime(1942, 4, 27).date(),
            marital_status="Widowed",
            language="English",
            phone="(617) 555-0152",
            address_line="9 Chestnut Hill Terrace",
            city="Newton",
            state="MA",
            postal_code="02467",
            emergency_contact_name="Lucia Ferraro",
            emergency_contact_relationship="daughter",
            emergency_contact_phone="(617) 555-0153",
            living_situation="lives_with_family",
            code_status="DNR",
        )
    )

    # --- Encounters -------------------------------------------------------
    encounter(
        session, id=ENC_CURRENT, patient_id=PID, class_code="IMP",
        period_start=ADMIT, period_end=None,
        visit_title="Inpatient admission — metastatic pancreatic cancer, pain crisis",
        reason_text="Metastatic pancreatic cancer with intractable pain and cachexia",
        location_display="8 North — Oncology", attending_name="Dr. Helen Sørensen",
        disposition_status="predicted",
    )
    encounter(
        session, id=ENC_STENT, patient_id=PID, class_code="IMP",
        period_start=STENT_START, period_end=STENT_END,
        visit_title="Inpatient admission — malignant biliary obstruction, ERCP with stent",
        reason_text="Obstructive jaundice from pancreatic head mass",
        location_display="6 North — Medicine", attending_name="Dr. Rachel Lindqvist",
        planned_disposition="home",
    )
    encounter(
        session, id=ENC_ONC_DEC, patient_id=PID, class_code="AMB",
        period_start=ONC_DEC_START, period_end=ONC_DEC_START + timedelta(minutes=40),
        visit_title="Oncology clinic — cycle 1 review",
        reason_text="Pancreatic adenocarcinoma, on gemcitabine/nab-paclitaxel",
        location_display="Cancer Center, Floor 2", attending_name="Dr. Anand Krishnan",
        planned_disposition="home",
    )
    encounter(
        session, id=ENC_ONC_FEB, patient_id=PID, class_code="AMB",
        period_start=ONC_FEB_START, period_end=ONC_FEB_START + timedelta(minutes=45),
        visit_title="Oncology clinic — restaging after cycle 3",
        reason_text="Restaging; progression on first-line therapy",
        location_display="Cancer Center, Floor 2", attending_name="Dr. Anand Krishnan",
        planned_disposition="home",
    )
    encounter(
        session, id=ENC_ONC_JUN, patient_id=PID, class_code="AMB",
        period_start=ONC_JUN_START, period_end=ONC_JUN_START + timedelta(minutes=40),
        visit_title="Oncology clinic — transition of care",
        reason_text="Metastatic pancreatic cancer off therapy; hospice discussion",
        location_display="Cancer Center, Floor 2", attending_name="Dr. Anand Krishnan",
        planned_disposition="home",
    )

    # --- Conditions -------------------------------------------------------
    condition(session, PID, ENC_CURRENT, "363418001", "Malignant tumor of pancreas (disorder)", datetime(2025, 11, 1), category="problem-list-item")
    condition(session, PID, ENC_CURRENT, "94222008", "Secondary malignant neoplasm of liver (disorder)", datetime(2026, 3, 1))
    condition(session, PID, ENC_CURRENT, "267024001", "Cachexia (finding)", ADMIT)
    condition(session, PID, ENC_STENT, "83607001", "Obstructive jaundice (disorder)", STENT_START, status="resolved")

    # --- Vitals -----------------------------------------------------------
    vital(session, PID, ENC_CURRENT, "8867-4", "Heart rate", 104, "/min", NOW - timedelta(hours=2), 60, 100, "H")
    vital(session, PID, ENC_CURRENT, "8480-6", "Systolic blood pressure", 92, "mm[Hg]", NOW - timedelta(hours=2), 90, 140)
    vital(session, PID, ENC_CURRENT, "2708-6", "Oxygen saturation", 93, "%", NOW - timedelta(hours=2), 94, 100, "L")

    # --- Medications ------------------------------------------------------
    med(session, PID, ENC_CURRENT, "Morphine", "2 mg", "IV", "q2h PRN pain", ADMIT)
    med(session, PID, ENC_CURRENT, "Morphine sulfate ER", "15 mg", "PO", "q12h", ADMIT + timedelta(days=3))
    med(session, PID, ENC_CURRENT, "Ondansetron", "4 mg", "IV", "q8h PRN nausea", ADMIT)
    med(session, PID, ENC_CURRENT, "Senna-docusate", "2 tabs", "PO", "BID", ADMIT)

    # --- Notes ------------------------------------------------------------
    # Current admission: H&P + 4 daily progress notes + palliative consult +
    # family meeting note. (Day-5 progress note not yet written at NOW 08:00.)
    note(session, id="note-hero-c-hp-current", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="history_and_physical", title="Medicine/Oncology H&P — pain crisis, hospice planning",
         author="Dr. Helen Sørensen", author_role="physician",
         signed_at=ADMIT + timedelta(hours=5), text=HP_CURRENT)
    note(session, id="note-hero-c-prog-d1", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Progress note — day 1",
         author="Dr. Helen Sørensen", author_role="physician",
         signed_at=ADMIT + timedelta(days=1, hours=3), text=PROG_D1)
    note(session, id="note-hero-c-prog-d2", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Progress note — day 2",
         author="Dr. Helen Sørensen", author_role="physician",
         signed_at=ADMIT + timedelta(days=2, hours=3), text=PROG_D2)
    note(session, id="note-hero-c-prog-d3", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Progress note — day 3",
         author="Dr. Helen Sørensen", author_role="physician",
         signed_at=ADMIT + timedelta(days=3, hours=9), text=PROG_D3)
    note(session, id="note-hero-c-prog-d4", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Progress note — day 4",
         author="Dr. Helen Sørensen", author_role="physician",
         signed_at=ADMIT + timedelta(days=4, hours=8), text=PROG_D4)
    note(session, id="note-hero-c-palliative", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="consult", title="Palliative care consult",
         author="Dr. Omar Haddad", author_role="physician",
         signed_at=NOW - timedelta(days=1), text=PALLIATIVE_CONSULT)
    note(session, id="note-hero-c-fam-current", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="family_communication", title="Family meeting — leaning home hospice, night-coverage concern",
         author="Miriam Katz, LCSW", author_role="social_work",
         signed_at=ADMIT + timedelta(days=3, hours=10), text=FAM_CURRENT)

    # Biliary stent admission (finished IMP): H&P + 2 progress + DC summary.
    note(session, id="note-hero-c-stent-hp", patient_id=PID, encounter_id=ENC_STENT,
         note_type="history_and_physical", title="Medicine H&P — obstructive jaundice",
         author="Dr. Rachel Lindqvist", author_role="physician",
         signed_at=STENT_START + timedelta(hours=4), text=HP_STENT)
    note(session, id="note-hero-c-stent-prog-1", patient_id=PID, encounter_id=ENC_STENT,
         note_type="progress", title="Progress note — stent day 1",
         author="Dr. Rachel Lindqvist", author_role="physician",
         signed_at=STENT_START + timedelta(days=1, hours=6), text=STENT_PROG_1)
    note(session, id="note-hero-c-stent-prog-2", patient_id=PID, encounter_id=ENC_STENT,
         note_type="progress", title="Progress note — stent day 2",
         author="Dr. Rachel Lindqvist", author_role="physician",
         signed_at=STENT_END - timedelta(hours=3), text=STENT_PROG_2)
    note(session, id="note-hero-c-stent-dc", patient_id=PID, encounter_id=ENC_STENT,
         note_type="discharge_summary", title="Discharge summary — biliary stent admission",
         author="Dr. Rachel Lindqvist", author_role="physician",
         signed_at=STENT_END - timedelta(hours=1), text=STENT_DC)

    # Oncology visits: exactly one progress note each; June visit also carries
    # the outpatient goals-of-care family communication (palliative MD call).
    note(session, id="note-hero-c-onc-dec", patient_id=PID, encounter_id=ENC_ONC_DEC,
         note_type="progress", title="Oncology clinic note — cycle 1 review",
         author="Dr. Anand Krishnan", author_role="physician",
         signed_at=ONC_DEC_START + timedelta(minutes=35), text=ONC_DEC_NOTE)
    note(session, id="note-hero-c-onc-feb", patient_id=PID, encounter_id=ENC_ONC_FEB,
         note_type="progress", title="Oncology clinic note — restaging, progression",
         author="Dr. Anand Krishnan", author_role="physician",
         signed_at=ONC_FEB_START + timedelta(minutes=40), text=ONC_FEB_NOTE)
    note(session, id="note-hero-c-onc-jun", patient_id=PID, encounter_id=ENC_ONC_JUN,
         note_type="progress", title="Oncology clinic note — transition of care",
         author="Dr. Anand Krishnan", author_role="physician",
         signed_at=ONC_JUN_START + timedelta(minutes=35), text=ONC_JUN_NOTE)
    note(session, id="note-hero-c-fam-goc", patient_id=PID, encounter_id=ENC_ONC_JUN,
         note_type="family_communication", title="Outpatient goals-of-care call with patient and daughter",
         author="Dr. Omar Haddad", author_role="physician",
         signed_at=ONC_JUN_START + timedelta(days=2), text=FAM_GOC_JUN)

    # --- Dispo domain -----------------------------------------------------
    session.add(
        DispoAssessment(
            id="dispo-hero-c",
            patient_id=PID,
            encounter_id=ENC_CURRENT,
            predicted_disposition="hospice_home",
            confidence=0.82,
            rationale=(
                "84yo with metastatic pancreatic cancer off disease-directed therapy, ECOG 3, "
                "cachexia, DNR/DNI, and comfort-focused goals stated consistently across oncology, "
                "palliative care, and a family meeting. Family is leaning home hospice at the "
                "daughter's house; the deciding variable is night coverage for a sole caregiver — "
                "inpatient hospice is the named fallback if symptoms or caregiver capacity fail."
            ),
            barriers=[
                "Hospice election form not yet signed",
                "Attending certification of terminal illness (CTI) pending signature",
                "Final family confirmation of home vs facility after palliative touch-base",
            ],
            alternatives=[{"disposition": "hospice_facility", "confidence": 0.16}],
            assessed_by="Placer",
            is_current=True,
        )
    )
    session.add(
        CareTask(
            id="task-hero-c-hospice",
            patient_id=PID,
            encounter_id=ENC_CURRENT,
            task_type="verify_eligibility",
            title="Coordinate hospice election",
            description="Confirm home vs inpatient hospice; complete election form and CTI with Peaceful Passages.",
            status="in_progress",
            priority="high",
            assigned_to="Placer",
            related_facility_id="fac-peaceful-hospice",
        )
    )
    session.add(
        Communication(
            patient_id=PID,
            care_task_id="task-hero-c-hospice",
            facility_id="fac-peaceful-hospice",
            direction="outbound",
            modality="phone",
            party_type="facility",
            party_name="Peaceful Passages intake",
            summary=(
                "Referral packet received; same-day home-hospice admission possible on discharge. "
                "Outstanding: signed election form and attending CTI. Continuous-care nursing and "
                "respite confirmed available for the family's night-coverage concern."
            ),
            outcome="intake_in_progress",
            occurred_at=NOW - timedelta(hours=11),
        )
    )

    # --- Placer chat ------------------------------------------------------
    for i, (sender, sender_name, hours, text) in enumerate(CHAT, start=1):
        placer_msg(
            session, id=f"msg-hero-c-{i}", patient_id=PID,
            sender=sender, sender_name=sender_name, text=text,
            at=NOW + timedelta(hours=hours),
        )
