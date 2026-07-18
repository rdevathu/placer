"""Hero D — Tom Nguyen, 71M, community-acquired pneumonia + COPD.

The ambiguity storyline: the medicine is straightforward but the disposition is
genuinely unknowable from the chart — baseline function and living situation
are undocumented (the patient deflects the questions, and did so in 2025 too).
His demographics are complete (wife Linh is the emergency contact); what is
missing is functional/social documentation, which is exactly the gap Placer
surfaces. The chat thread deliberately ends on an unanswered Placer question.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session

from ...models import CareTask, DispoAssessment, Patient
from .common import NOW, condition, encounter, med, note, placer_msg, vital

PID = "hero-d-ambiguous"
ENC_CURRENT = "enc-hero-d"
ENC_COPD = "enc-hero-d-2025-copd"
ENC_PULM = "enc-hero-d-2025-pulm"

ADMIT = NOW - timedelta(days=2)  # 2026-07-16 08:00
COPD_START = datetime(2025, 1, 12, 20, 0)
COPD_END = datetime(2025, 1, 15, 13, 0)
PULM_START = datetime(2025, 3, 18, 11, 0)


# ---------------------------------------------------------------------------
# Current admission notes
# ---------------------------------------------------------------------------

HP_CURRENT = """# Medicine History & Physical

**Chief Complaint:** Cough, fever, and shortness of breath.

**HPI:** Mr. Tom Nguyen is a 71-year-old man with COPD (on tiotropium and PRN albuterol, prior exacerbation admission January 2025) who presents with four days of productive cough with rusty sputum, subjective fevers and chills, and progressive dyspnea, now short of breath crossing a room. He took extra albuterol without relief. He arrived by taxi, alone. In the ED: T 38.4, SpO2 88% on room air improving to 93% on 2L, RR 24. Chest radiograph shows a right lower lobe consolidation. He received ceftriaxone, azithromycin, and nebulizers and was admitted for community-acquired pneumonia with hypoxia on a background of COPD. He denies chest pain, hemoptysis, orthopnea, leg swelling, recent travel, or sick contacts — then adds, "the guys at the card table were coughing," without elaborating.

**Review of Systems:** Positive for cough, sputum, fever, dyspnea, fatigue, decreased appetite x4 days. Negative for chest pain, hemoptysis, weight loss, night sweats, dysuria, diarrhea. Otherwise negative in 10 systems.

**Past Medical History:**
1. Chronic obstructive pulmonary disease (dx ~2018; FEV1 54% predicted on 2025 spirometry; one prior exacerbation admission 1/2025; no home oxygen)
2. Hypertension
3. Hyperlipidemia
4. Remote peptic ulcer disease (~1990s), no recent symptoms

**Past Surgical History:** Right inguinal hernia repair (2001).

**Home Medications:**
- Tiotropium 18 mcg inhaled daily
- Albuterol MDI 2 puffs q4-6h PRN
- Amlodipine 10 mg PO daily
- Atorvastatin 20 mg PO nightly

**Allergies:** No known drug allergies.

**Social History:** INCOMPLETE — patient deferred most questions. Married; wife Linh Nguyen is listed as emergency contact, but she was not present at admission and has not yet been reached (day-shift attempts ongoing). Lives in Dorchester; when asked about his home he said "it's fine" and changed the subject; number of floors, stairs, and who is at home are NOT established. Baseline functional status could not be assessed: he states he "gets around fine," but declined to answer questions about walking distance, stairs, bathing, or who does the shopping and cooking, becoming visibly irritated ("I didn't come here for a survey"). Former smoker per the 2025 chart (40 pack-years, reportedly quit 2020); today he said only "not really" when asked if he still smokes. Alcohol: "a little." Occupation: retired; previously commercial fishing and later a school custodian per old notes. Of note, the January 2025 discharge summary contains the same gap — "patient declined to discuss home situation." Social work consult placed. Insurance: traditional Medicare.

**Family History:** Unable to obtain beyond "everyone's gone." Records note a brother deceased of lung cancer.

**Physical Exam:**
- Vitals: T 38.2, HR 96, BP 142/84, RR 22, SpO2 92% on 2L NC.
- General: Thin, weathered-appearing man, mildly dyspneic with speech, guarded but cooperative with the exam itself.
- HEENT: Oropharynx dry. Poor dentition.
- Cardiac: Regular, tachycardic, no murmur.
- Pulmonary: Prolonged expiratory phase diffusely; coarse crackles and egophony at the right base; scattered expiratory wheeze.
- Abdomen: Soft, non-tender.
- Extremities: No edema. Muscle bulk modestly reduced in the thighs; calluses on both hands.
- Neurologic: Alert, oriented x3. Gait not formally assessed (on oxygen); he walked from the wheelchair to the bed slowly but unaided.

**Labs/Imaging:** WBC 14.6 with left shift. Na 133, Cr 1.0, glucose 118. Lactate 1.6. Procalcitonin 0.9. Blood cultures pending. Influenza/COVID/RSV PCR negative. CXR: dense RLL consolidation, hyperinflation, no effusion. ECG: sinus tachycardia.

**Assessment & Plan:** 71-year-old man with community-acquired pneumonia (RLL, CURB-65 = 1-2) with hypoxia, on a background of moderate COPD.

1. **Community-acquired pneumonia:** Ceftriaxone 1 g IV daily + azithromycin 500 mg IV daily; narrow per cultures. Anticipate 5-7 day total course with early IV-to-PO switch if he defervesces.
2. **COPD:** Scheduled nebulizers (albuterol/ipratropium), continue tiotropium, prednisone 40 mg daily x5 days given wheeze and prior exacerbation phenotype. Titrate O2 to SpO2 88-92%.
3. **Hypoxia:** 2L NC currently. Wean as tolerated; he has no home oxygen, so the discharge O2 requirement is a decision point.
4. **Hyponatremia, mild:** Likely parapneumonic; monitor.
5. **Disposition:** CANNOT BE ASSESSED YET, and the obstacle is informational, not medical. His expected clinical course (afebrile in 48-72h, wean to room air) would ordinarily mean discharge home in 3-4 days — but we do not know what home is: stairs, supports, who is there, or his true baseline function. He deflected all such questions today, exactly as documented in January 2025. Needs: (a) PT evaluation for objective functional data; (b) social work to build rapport and to reach his wife Linh (emergency contact) for collateral on home setup and baseline; (c) reassess daily. Until then the plan ranges anywhere from home, to home with services, to SNF.
"""

PROG_D1 = """# Medicine Progress Note — Hospital Day 1

**Subjective:** "Better than yesterday." Cough productive but less frequent; fevers down overnight. Ate most of breakfast. Declined to call his wife from the bedside phone when nursing offered — "she's busy."

**Objective:** T max 37.9 (down from 38.4), HR 88, BP 138/80, SpO2 92% on 2L. Lungs: persistent right-base crackles, less wheeze after scheduled nebs. Walking to the bathroom with the O2 tether, steady but slow. Blood cultures no growth at 24h.

**Assessment/Plan:** CAP + COPD, day 1, early improvement.
- Continue ceftriaxone/azithromycin IV; if afebrile through tomorrow morning, switch to PO.
- Prednisone day 2 of 5; scheduled nebs; wean O2 as tolerated (still 2L).
- Dispo: no new information. PT consult placed — not yet seen. Social work attempted a visit this afternoon; he was polite but deflected again ("I manage"). SW will attempt the wife by phone tomorrow. Baseline function and home setup remain undocumented; disposition range unchanged (home vs home-with-services vs SNF).

— Dr. Aisha Rahman, Medicine
"""

PROG_D2 = """# Medicine Progress Note — Hospital Day 2

**Subjective:** Afebrile overnight, "breathing easier." Wants to know when he can leave. When told the team would like to speak with his wife, he shrugged: "if you can catch her."

**Objective:** T max 37.4, HR 84, BP 136/82, SpO2 93% on 2L; brief room-air trial dipped to 88% with ambulation — placed back on 2L. WBC 14.6 -> 10.8. Lungs: improving right base.

**Assessment/Plan:** CAP + COPD, day 2, responding to treatment.
- Switched to PO doxycycline this morning to complete the course (cultures negative, procalcitonin trending down).
- Prednisone day 3 of 5; continue nebs; ambulatory O2 requirement persists — recheck ambulatory saturation daily; may need short-term home O2 if it does not clear.
- Dispo: still blocked on information, not medicine. PT eval now expected today (weekend backlog). SW left a voicemail for wife Linh this morning; no callback yet. If ambulatory hypoxia persists and baseline remains unknown, cannot safely default to home. Medical readiness likely in 1-2 days; disposition readiness is the open question.

— Dr. Aisha Rahman, Medicine
"""

# ---------------------------------------------------------------------------
# Prior COPD admission (Jan 2025) — deliberately thin social documentation.
# ---------------------------------------------------------------------------

HP_COPD = """# Medicine History & Physical — COPD Exacerbation

**Chief Complaint:** Worsening shortness of breath and wheeze.

**HPI:** Mr. Tom Nguyen is a 69-year-old man with COPD who presents with three days of worsening dyspnea, wheeze, and increased sputum volume with a change from white to yellow, following "a cold that went to my chest" about a week ago. He has been using his albuterol inhaler every 2-3 hours for two days without sustained relief, and last night sat up in a chair to sleep because lying flat "made the whistling worse." He denies fever at home (does not own a thermometer), chest pain, hemoptysis, leg swelling, or calf pain. He waited to come in because he "figured it would pass," and arrived alone by taxi this evening. In the ED: SpO2 87% on room air improving to 92% on 2L, RR 24, diffuse expiratory wheeze with prolonged expiration, chest radiograph without consolidation or pneumothorax. He received stacked albuterol/ipratropium nebulizers and methylprednisolone with moderate improvement and was admitted for a COPD exacerbation not safe for outpatient management given hypoxia and persistent work of breathing.

**Review of Systems:** Positive for dyspnea, wheeze, sputum, poor sleep. Negative for fever, chest pain, hemoptysis, edema. Otherwise negative in 10 systems.

**Past Medical History:** COPD (dx ~2018, no prior admissions). Hypertension. Hyperlipidemia. Remote peptic ulcer disease.

**Past Surgical History:** Right inguinal hernia repair (2001).

**Home Medications:** Tiotropium 18 mcg inhaled daily; albuterol MDI PRN; amlodipine 10 mg daily; atorvastatin 20 mg nightly.

**Allergies:** No known drug allergies.

**Social History:** 40 pack-year smoking history, states he quit "a few years ago." Married. Lives locally. Patient declined to discuss his home situation further and became irritated with additional questions; deferred. Alcohol "sometimes." Retired.

**Family History:** Brother died of lung cancer. Otherwise unknown.

**Physical Exam:**
- Vitals: T 37.1, HR 98, BP 148/88, RR 24, SpO2 92% on 2L.
- General: Thin man, moderate respiratory distress, speaking in short sentences.
- Pulmonary: Diffuse expiratory wheeze, prolonged expiration, no focal crackles.
- Cardiac: Tachycardic, regular, no murmur.
- Extremities: No edema, no cyanosis.
- Neurologic: Alert, oriented x3, no asterixis.

**Labs/Imaging:** WBC 9.8. BMP unremarkable. VBG pH 7.36, pCO2 48. CXR: hyperinflation, no infiltrate. Influenza PCR negative.

**Assessment & Plan:** 69-year-old man with a moderate COPD exacerbation, likely viral trigger given the preceding URI and negative influenza testing, first hospitalization for COPD. VBG shows compensated mild hypercapnia without acute respiratory acidosis; no indication for ventilatory support.
1. **COPD exacerbation:** Prednisone 40 mg daily x5 days (no taper needed at this dose/duration); azithromycin 500 mg then 250 mg daily x4 days; scheduled albuterol/ipratropium nebulizers q4h with PRN in between; continue home tiotropium. Titrate oxygen to a target SpO2 of 88-92% given CO2 retention on VBG. Reassess with a room-air trial daily.
2. **Hypertension:** Continue amlodipine 10 mg; readings acceptable in the context of illness and bronchodilators.
3. **Hyperlipidemia:** Continue atorvastatin.
4. **Smoking status:** Unclear — chart says quit, patient noncommittal. Counseled regardless; offered nicotine replacement and cessation resources — declined further discussion.
5. **Never-established maintenance therapy:** He has never had spirometry on file or pulmonology input; this admission is the prompt. Referral to be placed at discharge.
6. **Disposition:** Anticipate discharge home in 2-3 days as bronchospasm settles and he weans to room air. Spirometry and pulmonology follow-up as an outpatient. Social context not further characterized this admission — the patient declined to discuss his home situation and became irritated with repeated questions; he is managing independently on the unit, and no services were arranged. Would benefit from a fuller functional and social assessment at a future encounter if he permits it.
"""

COPD_PROG_1 = """# Medicine Progress Note — Jan 2025, Day 1

**Subjective:** Wheeze improved with scheduled nebs; slept "okay." Wants the monitor leads off. No visitors documented.

**Objective:** T 37.0, HR 90, SpO2 93% on 2L. Diffuse wheeze, better air movement than admission. VBG stable.

**Assessment/Plan:** COPD exacerbation, improving on steroids/nebulizers/azithromycin. Wean O2 as tolerated; space nebs to q4h. Continue prednisone. Anticipate discharge tomorrow or the day after. Social work not consulted; patient managing independently on the unit.

— Dr. Aisha Rahman, Medicine
"""

COPD_PROG_2 = """# Medicine Progress Note — Jan 2025, Day 2

**Subjective:** "Ready to go home." Breathing near baseline by his report; walking laps on the unit without the oxygen.

**Objective:** T 36.9, HR 84, SpO2 94% RA at rest, 92% ambulating. Scattered end-expiratory wheeze only.

**Assessment/Plan:** COPD exacerbation resolving; off oxygen. Discharge tomorrow morning on prednisone taper and azithromycin to complete 5 days. Inhaler technique reviewed — adequate. Pulmonology referral placed for spirometry. Asked again about home support for discharge planning; patient declined to discuss home situation — discharging home at his insistence, independent per his self-report.

— Dr. Aisha Rahman, Medicine
"""

COPD_DC = """# Discharge Summary — COPD Exacerbation (Jan 2025)

**Admission Diagnosis:** COPD exacerbation.
**Discharge Diagnoses:** 1. Acute exacerbation of COPD, resolved. 2. Hypertension. 3. Hyperlipidemia.

**Hospital Course:** 69-year-old man admitted with a moderate COPD exacerbation after a viral upper respiratory infection, his first COPD hospitalization. He improved steadily on prednisone, azithromycin, and scheduled bronchodilators, weaning to room air by hospital day 2 (SpO2 94% at rest, 92% ambulating). He remained afebrile without consolidation on imaging.

**Discharge Medications:** Prednisone taper (30 mg x2d, 20 mg x2d, 10 mg x2d); azithromycin 250 mg daily x2 more days; tiotropium 18 mcg daily; albuterol MDI PRN; amlodipine 10 mg daily; atorvastatin 20 mg nightly.

**Disposition:** Discharged HOME at the patient's insistence. Of note, the patient declined to discuss his home situation during this admission; functional baseline and home supports were not characterized, and no services were arranged. He left independently by taxi.

**Follow-up:** Pulmonology referral for spirometry and COPD management (appointment to be mailed); PCP within 2 weeks; return precautions reviewed.

— Dr. Aisha Rahman, Medicine
"""

PULM_NOTE = """# Pulmonology Clinic Note

**Subjective:** 69M seen for initial pulmonology evaluation after January COPD admission. Reports he is "back to normal," though on questioning he admits dyspnea on hills and with heavy bags. Using tiotropium daily, albuterol "a few times a week." Smoking: says he quit in 2020; ambivalent when pressed. Declined to have anyone accompany him today; questions about who is at home redirected — "just me and the wife, we're fine."

**Objective:** SpO2 96% RA. Spirometry today: FEV1 54% predicted, FEV1/FVC 0.58, minimal bronchodilator response — moderate obstruction (GOLD 2). CXR (recent) hyperinflated, clear.

**Assessment/Plan:** Moderate COPD (GOLD 2, exacerbation history now 1 in the past year).
1. Step up maintenance: add a LABA — switched tiotropium to tiotropium/olodaterol combination inhaler; technique taught and confirmed.
2. Albuterol PRN; rescue plan reviewed in writing.
3. Vaccinations updated (influenza received in ED in January; pneumococcal given today).
4. Smoking cessation revisited; he took the pamphlet this time.
5. Pulmonary rehab offered — declined ("too far to travel"). Will re-offer at next visit.
6. Return 6 months with repeat spirometry; sooner for exacerbation.

— Dr. Deborah Klein, Pulmonology
"""

# ---------------------------------------------------------------------------
# Placer chat — ends on an unanswered Placer question.
# ---------------------------------------------------------------------------

CHAT = [
    ("placer", "Placer", -22.0,
     "Reviewed Mr. Nguyen's chart. I can't produce a confident disposition yet (best guess "
     "undetermined, 40%): CAP + COPD improving as expected, but his baseline function and living "
     "situation are undocumented — and the January 2025 discharge summary has the same gap "
     "('patient declined to discuss home situation'). Wife Linh Nguyen is on file as emergency "
     "contact. I'd suggest PT for objective function and social work for collateral."),
    ("provider", "Dr. Aisha Rahman", -20.0,
     "Agreed — he's been just as vague with us. PT consult is in. Have social work keep trying; "
     "he waved off calling his wife from the bedside."),
    ("placer", "Placer", -6.0,
     "Update: social work attempted again this morning — he deflected ('I manage'), and their "
     "voicemail to Linh hasn't been returned. PT still pending (weekend backlog). Meanwhile his "
     "ambulatory sat dipped to 88% on room air, so a home-O2 decision may join the list. He'll "
     "likely be medically ready before we can say where he's actually going."),
    ("placer", "Placer", -2.0,
     "Is family at bedside today? I can't determine his baseline function from the chart — could "
     "the team ask his wife Linh about the home setup (stairs, who's at home, how he manages "
     "bathing, shopping, cooking) during visiting hours? Even one collateral conversation would "
     "move this from guesswork to a plan."),
]


def build(session: Session) -> None:
    session.add(
        Patient(
            id=PID,
            mrn="MRN90004",
            family_name="Nguyen",
            given_name="Tom",
            prefix="Mr.",
            full_name="Mr. Tom Nguyen",
            gender="male",
            birth_date=datetime(1955, 6, 19).date(),
            marital_status="Married",
            language="English",
            phone="(617) 555-0190",
            address_line="77 Savin Hill Ave",
            city="Dorchester",
            state="MA",
            postal_code="02125",
            emergency_contact_name="Linh Nguyen",
            emergency_contact_relationship="spouse",
            emergency_contact_phone="(617) 555-0191",
            living_situation=None,  # unknown — the dispo gap is baseline function/home setup, not contacts
            code_status="full",
        )
    )

    # --- Encounters -------------------------------------------------------
    encounter(
        session, id=ENC_CURRENT, patient_id=PID, class_code="IMP",
        period_start=ADMIT, period_end=None,
        visit_title="Inpatient admission — community-acquired pneumonia",
        reason_text="Community-acquired pneumonia with hypoxia",
        location_display="6 West — Medicine", attending_name="Dr. Aisha Rahman",
        disposition_status="undetermined",
    )
    encounter(
        session, id=ENC_COPD, patient_id=PID, class_code="IMP",
        period_start=COPD_START, period_end=COPD_END,
        visit_title="Inpatient admission — COPD exacerbation",
        reason_text="Acute exacerbation of COPD",
        location_display="6 West — Medicine", attending_name="Dr. Aisha Rahman",
        planned_disposition="home",
    )
    encounter(
        session, id=ENC_PULM, patient_id=PID, class_code="AMB",
        period_start=PULM_START, period_end=PULM_START + timedelta(minutes=45),
        visit_title="Pulmonology clinic — initial evaluation with spirometry",
        reason_text="COPD evaluation after January admission",
        location_display="Pulmonology Clinic, Suite 340", attending_name="Dr. Deborah Klein",
        planned_disposition="home",
    )

    # --- Conditions -------------------------------------------------------
    condition(session, PID, ENC_CURRENT, "385093006", "Community acquired pneumonia (disorder)", ADMIT)
    condition(session, PID, ENC_CURRENT, "13645005", "Chronic obstructive pulmonary disease (disorder)", datetime(2018, 1, 1), category="problem-list-item")
    condition(session, PID, ENC_COPD, "195951007", "Acute exacerbation of COPD (disorder)", COPD_START, status="resolved")

    # --- Vitals -----------------------------------------------------------
    vital(session, PID, ENC_CURRENT, "8867-4", "Heart rate", 88, "/min", NOW - timedelta(hours=5), 60, 100)
    vital(session, PID, ENC_CURRENT, "2708-6", "Oxygen saturation", 91, "%", NOW - timedelta(hours=5), 94, 100, "L")
    vital(session, PID, ENC_CURRENT, "8310-5", "Body temperature", 37.4, "Cel", NOW - timedelta(hours=5), 36.1, 37.8)

    # --- Medications ------------------------------------------------------
    med(session, PID, ENC_CURRENT, "Ceftriaxone", "1 g", "IV", "daily", ADMIT)
    med(session, PID, ENC_CURRENT, "Azithromycin", "500 mg", "IV", "daily", ADMIT)
    med(session, PID, ENC_CURRENT, "Prednisone", "40 mg", "PO", "daily", ADMIT)
    med(session, PID, ENC_CURRENT, "Tiotropium", "18 mcg", "INH", "daily", ADMIT)

    # --- Notes ------------------------------------------------------------
    note(session, id="note-hero-d-hp-current", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="history_and_physical", title="Medicine H&P — CAP with COPD, social history incomplete",
         author="Dr. Aisha Rahman", author_role="physician",
         signed_at=ADMIT + timedelta(hours=4), text=HP_CURRENT)
    note(session, id="note-hero-d-prog-d1", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Medicine progress note — day 1",
         author="Dr. Aisha Rahman", author_role="physician",
         signed_at=ADMIT + timedelta(days=1, hours=3), text=PROG_D1)
    note(session, id="note-hero-d-prog-d2", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Medicine progress note — day 2",
         author="Dr. Aisha Rahman", author_role="physician",
         signed_at=NOW - timedelta(hours=1), text=PROG_D2)

    note(session, id="note-hero-d-copd-hp", patient_id=PID, encounter_id=ENC_COPD,
         note_type="history_and_physical", title="Medicine H&P — COPD exacerbation (Jan 2025)",
         author="Dr. Aisha Rahman", author_role="physician",
         signed_at=COPD_START + timedelta(hours=5), text=HP_COPD)
    note(session, id="note-hero-d-copd-prog-1", patient_id=PID, encounter_id=ENC_COPD,
         note_type="progress", title="Medicine progress note — Jan 2025 day 1",
         author="Dr. Aisha Rahman", author_role="physician",
         signed_at=COPD_START + timedelta(days=1), text=COPD_PROG_1)
    note(session, id="note-hero-d-copd-prog-2", patient_id=PID, encounter_id=ENC_COPD,
         note_type="progress", title="Medicine progress note — Jan 2025 day 2",
         author="Dr. Aisha Rahman", author_role="physician",
         signed_at=COPD_START + timedelta(days=2), text=COPD_PROG_2)
    note(session, id="note-hero-d-copd-dc", patient_id=PID, encounter_id=ENC_COPD,
         note_type="discharge_summary", title="Discharge summary — COPD exacerbation (Jan 2025)",
         author="Dr. Aisha Rahman", author_role="physician",
         signed_at=COPD_END - timedelta(hours=1), text=COPD_DC)

    note(session, id="note-hero-d-pulm-2025", patient_id=PID, encounter_id=ENC_PULM,
         note_type="progress", title="Pulmonology clinic note — initial evaluation",
         author="Dr. Deborah Klein", author_role="physician",
         signed_at=PULM_START + timedelta(minutes=40), text=PULM_NOTE)

    # --- Dispo domain -----------------------------------------------------
    session.add(
        DispoAssessment(
            id="dispo-hero-d",
            patient_id=PID,
            encounter_id=ENC_CURRENT,
            predicted_disposition="undetermined",
            confidence=0.4,
            rationale=(
                "71yo with CAP and COPD, improving but still oxygen-dependent on day 2 with "
                "ambulatory desaturation. Disposition genuinely uncertain: could be home if he "
                "returns to baseline — but baseline function and living situation are undocumented "
                "in this and the prior (Jan 2025) admission, and the patient deflects all social "
                "questions. Recommend PT evaluation and collateral from his wife (emergency "
                "contact Linh Nguyen) before predicting."
            ),
            barriers=[
                "Baseline function and living situation undocumented (patient deflects)",
                "Ambulatory oxygen requirement not yet resolved",
                "Awaiting PT functional assessment",
                "Collateral from wife (emergency contact) not yet obtained",
            ],
            alternatives=[
                {"disposition": "home", "confidence": 0.35},
                {"disposition": "snf", "confidence": 0.25},
            ],
            assessed_by="Placer",
            is_current=True,
        )
    )
    session.add(
        CareTask(
            id="task-hero-d-pt",
            patient_id=PID,
            encounter_id=ENC_CURRENT,
            task_type="collect_preference",
            title="Clarify home support & baseline function",
            description="Reach wife Linh Nguyen (emergency contact) for collateral on living situation and ADL baseline; pair with PT eval.",
            status="pending",
            priority="medium",
            assigned_to="Placer",
        )
    )

    # --- Placer chat (ends on an unanswered Placer question) --------------
    for i, (sender, sender_name, hours, text) in enumerate(CHAT, start=1):
        placer_msg(
            session, id=f"msg-hero-d-{i}", patient_id=PID,
            sender=sender, sender_name=sender_name, text=text,
            at=NOW + timedelta(hours=hours),
        )
