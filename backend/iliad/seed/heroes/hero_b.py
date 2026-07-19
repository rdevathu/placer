"""Hero B — Daniel Okafor, 66M, acute CHF exacerbation (HFrEF, EF 25%).

The home-with-services storyline: rapid diuresis, engaged spouse who works
weekdays, single-story ranch — the right answer is home + home-health nursing
for daily weights and med teaching, and the open questions are the IV-to-PO
diuretic transition and the HomeTeam referral timing. Prior chart: a November
2025 CHF admission and two cardiology follow-ups showing GDMT titration.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session

from ...models import CareTask, DispoAssessment, Patient
from .common import NOW, condition, encounter, med, note, placer_msg, vital

PID = "hero-b-chf"
ENC_CURRENT = "enc-hero-b"
ENC_CHF_2025 = "enc-hero-b-2025-chf"
ENC_CARDS_DEC = "enc-hero-b-2025-cards-fu"
ENC_CARDS_APR = "enc-hero-b-2026-cards-fu"

ADMIT = NOW - timedelta(days=2)  # 2026-07-16 08:00
CHF25_START = datetime(2025, 11, 3, 16, 0)
CHF25_END = datetime(2025, 11, 7, 12, 0)
CARDS_DEC_START = datetime(2025, 12, 9, 13, 30)
CARDS_APR_START = datetime(2026, 4, 14, 9, 0)


# ---------------------------------------------------------------------------
# Current admission notes
# ---------------------------------------------------------------------------

HP_CURRENT = """# Cardiology History & Physical

**Chief Complaint:** Progressive shortness of breath and leg swelling.

**HPI:** Mr. Daniel Okafor is a 66-year-old man with ischemic cardiomyopathy (EF 25% on echo April 2026), type 2 diabetes, and a prior CHF admission in November 2025, who presents with one week of progressive exertional dyspnea, three-pillow orthopnea, and bilateral leg swelling. He attributes the decline to the week after the July 4th holiday — several days of salty leftovers and takeout, and he admits missing two or three evening medication doses while hosting family. Home weight rose from 79 kg to 84 kg over ten days. Last night he woke twice gasping and slept upright in a recliner, prompting his wife to bring him in. Denies chest pain, palpitations, syncope, fever, or cough. In the ED: SpO2 92% RA, bibasilar crackles, BNP 1,840, and chest radiograph with pulmonary vascular congestion; he received IV furosemide 80 mg with brisk diuresis and was admitted to cardiology.

**Review of Systems:** Positive for dyspnea, orthopnea, PND, leg edema, fatigue. Negative for chest pain, palpitations, syncope, fever, cough, abdominal pain. Otherwise negative in 10 systems.

**Past Medical History:**
1. Ischemic cardiomyopathy, EF 25% (echo 4/2026); NSTEMI 2018 with drug-eluting stent to the LAD
2. Congestive heart failure (dx 2019); prior exacerbation admission 11/2025
3. Type 2 diabetes mellitus (2012), on oral therapy, last HbA1c 7.2
4. Hyperlipidemia
5. Obstructive sleep apnea, on CPAP (adherent)

**Past Surgical History:** Percutaneous coronary intervention with DES to LAD (2018). Right inguinal hernia repair (2005).

**Home Medications:**
- Furosemide 40 mg PO daily
- Metoprolol succinate 50 mg PO daily
- Lisinopril 20 mg PO daily
- Dapagliflozin 10 mg PO daily (started 11/2025)
- Atorvastatin 40 mg PO nightly
- Metformin 1000 mg PO BID
- Aspirin 81 mg PO daily

**Allergies:** No known drug allergies.

**Social History:** Married 38 years; lives with his wife Adaeze in a single-story ranch house in Cambridge — three steps at the front entry with a sturdy railing, bedroom and full bathroom on the single level, no interior stairs. Retired MBTA transit mechanic. Independent in all ADLs and IADLs at baseline; before this decompensation he walked about a mile most mornings and did his own yard work. Wife works weekdays (school administrator, 7:30-16:00) so he is home alone during the day; she manages the pillbox on weekends and describes herself as "the enforcer" of his salt restriction, less successfully around holidays. Two adult sons in the area who visit weekly. Former smoker, quit 2018 (20 pack-years); rare beer; no other substances. Insurance: Blue Cross Blue Shield of MA PPO through his wife's employer (he is Medicare-eligible but has deferred enrollment while covered).

**Family History:** Father died of stroke at 70. Mother had type 2 diabetes, died at 84. Brother with coronary disease.

**Physical Exam:**
- Vitals: T 36.9, HR 88, BP 132/78, RR 20, SpO2 92% RA improving to 95% on 2L.
- General: Comfortable seated upright, speaks in full sentences.
- Neck: JVP ~12 cm.
- Cardiac: Regular rate, S3 present, no murmur. PMI displaced laterally.
- Pulmonary: Bibasilar crackles to one-third up bilaterally.
- Abdomen: Soft, mild hepatomegaly, no ascites.
- Extremities: 2+ pitting edema to the knees bilaterally, warm and well perfused.
- Neurologic: Alert and oriented, nonfocal.

**Labs/Imaging:** BNP 1,840 (baseline ~400). Cr 1.4 (baseline 1.1), K 4.2, Na 134. Troponin negative x2. HbA1c 7.2. CXR: cardiomegaly, vascular congestion, small bilateral effusions. ECG: sinus rhythm, old anterior Q waves, no acute change. Echo (4/2026, reviewed): EF 25%, dilated LV, moderate MR.

**Assessment & Plan:** 66-year-old man with HFrEF (EF 25%) and acute decompensated heart failure precipitated by dietary indiscretion and medication non-adherence — his second admission in nine months.

1. **Acute decompensated heart failure:** IV furosemide 40 mg BID targeting net -1.5 to -2 L/day; daily weights, strict I/O, 2 g sodium and 1.5 L fluid restriction. Transition to an oral diuretic once euvolemic — given two admissions on furosemide 40 mg, plan discharge on torsemide.
2. **GDMT:** Continue metoprolol succinate, lisinopril, dapagliflozin. Recheck K/Cr on diuresis; consider adding spironolactone before discharge if K and Cr allow.
3. **Type 2 diabetes:** Hold metformin while inpatient; sliding scale. Resume at discharge.
4. **Renal function:** Mild contraction expected with diuresis; monitor.
5. **Disposition:** Anticipate discharge HOME WITH HOME HEALTH in 2-3 days. Home is physically suitable — single-story ranch, only three railed entry steps — and he is independent at baseline, so no facility need. The gap is daytime support and adherence: his wife works weekdays, and both admissions followed adherence lapses. Home-health skilled nursing (HomeTeam has been used by this service) for daily weights, med reconciliation, and CHF teach-back, plus a scale-and-log program, addresses exactly that. BCBS PPO covers intermittent home health with the standard homebound documentation. Case management to place the referral once a discharge date firms up; heart-failure clinic follow-up within 7 days.
"""

PROG_D1 = """# Cardiology Progress Note — Hospital Day 1

**Subjective:** "Best night of sleep in a week." One pillow, no PND. Mild thirst on fluid restriction; otherwise comfortable. Wife visited last evening for teaching, asked good questions about the salt budget.

**Objective:** T 36.8, HR 78, BP 124/74, SpO2 95% RA. Weight 84.1 -> 82.6 kg. Net -2.5 L since admission. JVP down to ~9 cm. Crackles now bases only. Edema 1+. Cr 1.3, K 3.9 (repleted to 4.0).

**Assessment/Plan:** ADHF on IV diuresis, responding briskly.
- Continue furosemide 40 mg IV BID today; reassess volume this evening — likely one more day of IV.
- Continue metoprolol, lisinopril, dapagliflozin; started spironolactone 12.5 mg this morning (K/Cr acceptable), monitor K.
- Reinforced 2 g Na teaching with patient; dietician consult placed.
- Dispo: on track for home with home-health nursing. Case management aware; referral to go out once we set the IV-to-PO transition. Wife available evenings/weekends; sons nearby.

— Dr. Marcus Feld, Cardiology
"""

PROG_D2 = """# Cardiology Progress Note — Hospital Day 2

**Subjective:** Feels "close to normal." Walked the hallway loop twice with nursing without dyspnea. No orthopnea overnight. Eager to go home; wife has taken tomorrow morning off to be present for discharge teaching if we discharge.

**Objective:** T 36.8, HR 74, BP 120/72, SpO2 97% RA. Weight 82.6 -> 81.4 kg (dry weight ~80-81 kg). Net -2.1 L. JVP ~7 cm. Lungs clear. Trace edema. Cr 1.3, K 4.1 on spironolactone.

**Assessment/Plan:** ADHF, near euvolemic — day of IV-to-PO transition.
- Switching to torsemide 20 mg PO daily this morning; observe weight and renal function for 24h. If overnight weight stable, discharge tomorrow late morning.
- Continue GDMT incl. spironolactone 12.5 mg; labs in 1 week via home health.
- Teaching: scale delivered to bedside teaching done; red-flag weights (>1.4 kg/day or >2.3 kg/week) reviewed; teach-back successful with patient, to repeat with wife at discharge.
- Dispo: home with home health confirmed as plan — referral to HomeTeam to be finalized for start of care within 48h of discharge; heart-failure clinic follow-up early next week.

— Dr. Marcus Feld, Cardiology
"""

# ---------------------------------------------------------------------------
# Prior CHF admission (Nov 2025)
# ---------------------------------------------------------------------------

HP_CHF_2025 = """# Cardiology History & Physical — CHF Exacerbation

**Chief Complaint:** Shortness of breath and weight gain.

**HPI:** Mr. Daniel Okafor is a 65-year-old man with ischemic cardiomyopathy (EF then 30%, echo 2024) and type 2 diabetes presenting with two weeks of progressive dyspnea on exertion, now provoked by a single flight of stairs, with two-pillow orthopnea and 4 kg of weight gain. He dates the decline to the weeks after his retirement party in October: he reports gradually loosening his salt habits ("a lot of restaurant dinners"), and he stopped his daily weights "because the numbers were boring." He has taken his medications most days but admits his refill of furosemide lapsed for about five days last month. No chest pain, pressure, palpitations, syncope, or presyncope; no fever, cough, or recent illness. He sleeps with two pillows and woke once this week acutely short of breath. In the ED: SpO2 93% on room air, BNP 1,420, congestion on chest radiograph, troponin negative; he received IV furosemide 40 mg with good urine output and was admitted for continued IV diuresis. This is his first heart-failure hospitalization.

**Review of Systems:** Positive for dyspnea, orthopnea, edema, fatigue; negative for chest pain, palpitations, fever, cough; otherwise negative in 10 systems.

**Past Medical History:** Ischemic cardiomyopathy (NSTEMI 2018, DES to LAD); CHF (dx 2019); type 2 diabetes (2012); hyperlipidemia; obstructive sleep apnea on CPAP.

**Past Surgical History:** PCI with DES to LAD (2018); right inguinal hernia repair (2005).

**Home Medications:** Furosemide 20 mg PO daily; metoprolol succinate 25 mg PO daily; lisinopril 10 mg PO daily; atorvastatin 40 mg nightly; metformin 1000 mg BID; aspirin 81 mg daily.

**Allergies:** No known drug allergies.

**Social History:** Married, lives with wife in a single-story ranch in Cambridge (three entry steps with railing). Retired MBTA mechanic. Independent in all ADLs/IADLs; walks daily at baseline. Wife works weekdays. Two adult sons nearby. Former smoker, quit 2018 (20 pack-years); rare alcohol. Insurance: BCBS PPO via wife's employer.

**Family History:** Father — stroke at 70. Mother — diabetes. Brother — CAD.

**Physical Exam:**
- Vitals: T 37.0, HR 92, BP 138/82, RR 20, SpO2 93% RA.
- Neck: JVP 11 cm.
- Cardiac: Regular, S3, no murmur.
- Pulmonary: Crackles at both bases.
- Abdomen: Soft, non-tender.
- Extremities: 2+ edema to mid-shin.
- Neurologic: Nonfocal.

**Labs/Imaging:** BNP 1,420. Cr 1.2, K 4.0. Troponin negative. CXR: congestion, cardiomegaly. ECG: sinus, old anterior Q waves. Echo this admission: EF 25-30%, down from 30%.

**Assessment & Plan:** 65-year-old man with first hospitalization for acute decompensated HFrEF, precipitated by dietary drift, a lapsed diuretic refill, and abandoned self-monitoring, on notably sub-target GDMT — an admission that is as much an adherence and titration opportunity as a diuresis problem.

1. **ADHF:** IV furosemide 40 mg BID targeting net -1.5 to -2 L/day; daily standing weights before breakfast, strict I/O, 2 g sodium and 1.5 L fluid restriction; BMP daily with potassium repletion protocol.
2. **GDMT optimization — the main opportunity:** Uptitrate metoprolol succinate 25 -> 50 mg and lisinopril 10 -> 20 mg as blood pressure tolerates (admission BP 138/82 gives room); START dapagliflozin 10 mg daily. Discharge diuretic dose to be set once euvolemic (anticipate furosemide 40 mg daily, doubled from home).
3. **Diabetes:** Hold metformin while inpatient; sliding-scale insulin; dapagliflozin will serve double duty on discharge. HbA1c this admission to guide outpatient adjustments.
4. **Ischemic cardiomyopathy:** Continue aspirin and statin; no anginal symptoms; repeat echocardiogram this admission to re-stage EF after titration.
5. **OSA:** Home CPAP settings continued inpatient; adherent by his report.
6. **Disposition:** Expect discharge HOME in 3-4 days once euvolemic and titrated. He is fully independent with a suitable single-story home and an engaged wife; no home services anticipated beyond heart-failure clinic follow-up within 7 days, a lab check at one week, and a re-committed daily-weight program with written red-flag thresholds. Dietician and pharmacy to see him and his wife together before discharge — this admission was preventable, and the teaching is the treatment.
"""

CHF25_PROG_1 = """# Cardiology Progress Note — Nov 2025, Day 1

**Subjective:** Sleeping flatter, breathing easier. Tolerated first dose changes without dizziness.

**Objective:** HR 84, BP 128/76, SpO2 95% RA. Weight down 1.6 kg; net -2.2 L. JVP 9 cm, crackles improved, edema 1+.

**Assessment/Plan:** ADHF responding to IV diuresis. Metoprolol uptitrated to 50 mg today; lisinopril increase planned tomorrow; dapagliflozin started. Continue IV furosemide BID. Diabetes on sliding scale. Dietician saw patient — engaged. Dispo: home, likely day 3-4; no services beyond HF clinic anticipated.

— Dr. Marcus Feld, Cardiology
"""

CHF25_PROG_2 = """# Cardiology Progress Note — Nov 2025, Day 2

**Subjective:** No dyspnea walking halls. Asking about restarting morning walks after discharge.

**Objective:** HR 78, BP 122/74, SpO2 96% RA. Weight down another 1.2 kg. Lungs clear at bases. Trace edema. Cr 1.3 (mild contraction), K 4.2.

**Assessment/Plan:** Near euvolemic. Lisinopril uptitrated to 20 mg, tolerated. Continue dapagliflozin. Plan IV-to-PO furosemide transition tomorrow morning at 40 mg daily, observe 24h, then discharge. Teaching: daily weights re-committed — wife bringing their scale's log book in; red-flag thresholds reviewed.

— Dr. Marcus Feld, Cardiology
"""

CHF25_PROG_3 = """# Cardiology Progress Note — Nov 2025, Day 3

**Subjective:** Feels back to baseline. Weight stable overnight on PO furosemide.

**Objective:** HR 76, BP 118/72, SpO2 97% RA. Weight 79.4 kg (dry weight). Euvolemic exam. Cr 1.2, K 4.3.

**Assessment/Plan:** ADHF resolved; successful transition to furosemide 40 mg PO. GDMT meaningfully advanced this admission (metoprolol 50, lisinopril 20, dapagliflozin added). Discharge tomorrow morning after final teach-back with wife present. HF clinic in 7 days; labs in 1 week.

— Dr. Marcus Feld, Cardiology
"""

CHF25_DC = """# Discharge Summary — CHF Admission (Nov 2025)

**Admission Diagnosis:** Acute decompensated heart failure.
**Discharge Diagnoses:** 1. Acute on chronic systolic heart failure (HFrEF, EF 25-30%), resolved to euvolemia. 2. Ischemic cardiomyopathy. 3. Type 2 diabetes mellitus.

**Hospital Course:** 65-year-old man admitted with his first CHF decompensation after dietary drift and lapsed daily weights. He diuresed briskly on IV furosemide (net -6 L over three days) with improvement to euvolemia. The admission was used to advance chronically sub-target GDMT: metoprolol succinate uptitrated 25 to 50 mg, lisinopril 10 to 20 mg, and dapagliflozin 10 mg newly started, all tolerated without hypotension or renal deterioration (discharge Cr 1.2). He transitioned to furosemide 40 mg PO with a stable overnight weight.

**Discharge Medications:** Furosemide 40 mg daily (INCREASED); metoprolol succinate 50 mg daily (INCREASED); lisinopril 20 mg daily (INCREASED); dapagliflozin 10 mg daily (NEW); atorvastatin 40 mg nightly; metformin 1000 mg BID (resumed); aspirin 81 mg daily.

**Disposition:** Discharged HOME with his wife; independent, no home services indicated. Committed to daily weights with a written log; red-flag weight thresholds (call for >1.4 kg/day or >2.3 kg/week) reviewed with patient and wife, teach-back successful.

**Follow-up:** Heart-failure clinic (Dr. Feld) in 7 days; BMP in 1 week; PCP within a month.

— Dr. Marcus Feld, Cardiology
"""

CARDS_DEC_NOTE = """# Cardiology Clinic Note — Post-Discharge Follow-up

**Subjective:** 65M seen 4 weeks after CHF admission. Feels well; walking 30-40 minutes daily again. Weights logged every morning — brought the notebook; range 79.0-79.8 kg. No orthopnea, PND, or edema. Tolerating the uptitrated regimen and dapagliflozin without dizziness or GU symptoms.

**Objective:** HR 72, BP 118/70. Weight 79.5 kg. JVP normal. Lungs clear. No edema. Labs: Cr 1.1, K 4.4, HbA1c 7.4.

**Assessment/Plan:** HFrEF, euvolemic on furosemide 40/metoprolol 50/lisinopril 20/dapagliflozin 10. Excellent adherence since discharge. Discussed adding spironolactone; deferred for now given single-agent changes each visit — revisit in spring. Repeat echo in April to reassess EF. Continue salt restriction and daily weights; praised the log. Return 4 months, sooner for red-flag weights.

— Dr. Marcus Feld, Cardiology
"""

CARDS_APR_NOTE = """# Cardiology Clinic Note — Spring Follow-up

**Subjective:** 66M doing well overall. Weights stable 79-80 kg all winter, adherent to medications and mostly to diet ("holidays are hard"). No dyspnea beyond baseline at hills, no orthopnea or edema. CPAP adherent.

**Objective:** HR 70, BP 116/72. Weight 79.8 kg. Euvolemic exam. Repeat echocardiogram (today): EF 25%, dilated LV, moderate MR — no recovery despite GDMT.

**Assessment/Plan:** HFrEF with persistent EF 25% on good medical therapy.
1. EF remains <=35% >3 months on GDMT: referred for electrophysiology evaluation for primary-prevention ICD; patient wants to think it over and discuss with his wife.
2. Continue current regimen; add spironolactone at next titration touchpoint or during any admission if K/Cr allow.
3. Reinforced sodium vigilance heading into summer cookout season — his known vulnerability.
4. Return 6 months or sooner; HF clinic contact card re-issued.

— Dr. Marcus Feld, Cardiology
"""

# ---------------------------------------------------------------------------
# Placer chat
# ---------------------------------------------------------------------------

CHAT = [
    ("placer", "Placer", -30.0,
     "Reviewed Mr. Okafor's chart. Predicting home with services (71%): diuresing well, independent "
     "baseline, single-story home — but his wife works weekdays and both admissions followed "
     "adherence lapses, so home-health nursing for daily weights and med teaching is the key service. "
     "I'm checking HomeTeam Home Health capacity and his BCBS PPO coverage."),
    ("placer", "Placer", -9.0,
     "HomeTeam Home Health is the agency I'd plan to use here — this service has worked with them "
     "before, and home-health nursing for daily weights, med reconciliation, and CHF teach-back is "
     "exactly the service he needs. I haven't reached their intake line yet and no referral is placed; "
     "I'll confirm their capacity and that they take his BCBS PPO, then tee up the referral once the "
     "discharge date firms."),
    ("placer", "Placer", -7.0,
     "Question for the team: when do you plan to transition IV furosemide to PO? If the switch "
     "happens this morning and his weight holds overnight, he could discharge tomorrow late morning "
     "and HomeTeam could start Sunday."),
    ("provider", "Dr. Marcus Feld", -3.0,
     "Switched to torsemide 20 mg PO this morning. If overnight weight is stable, discharge tomorrow "
     "late morning — go ahead and line up HomeTeam for a Sunday start of care."),
    ("placer", "Placer", -2.0,
     "Will do — I'll place the HomeTeam referral and work toward a Sunday start of care pending your "
     "discharge order; nothing is confirmed with them yet. In the meantime I'll prep CHF teach-back "
     "materials for his wife Adaeze (she took tomorrow morning off) and make sure the scale-and-log "
     "program is in place before he leaves."),
]


def build(session: Session) -> None:
    session.add(
        Patient(
            id=PID,
            mrn="MRN90002",
            family_name="Okafor",
            given_name="Daniel",
            prefix="Mr.",
            full_name="Mr. Daniel Okafor",
            gender="male",
            birth_date=datetime(1960, 5, 14).date(),
            marital_status="Married",
            language="English",
            phone="(617) 555-0177",
            address_line="42 Fernwood Rd",
            city="Cambridge",
            state="MA",
            postal_code="02140",
            emergency_contact_name="Adaeze Okafor",
            emergency_contact_relationship="spouse",
            emergency_contact_phone="(617) 555-0179",
            living_situation="lives_with_family",
            code_status="full",
        )
    )

    # --- Encounters -------------------------------------------------------
    encounter(
        session, id=ENC_CURRENT, patient_id=PID, class_code="IMP",
        period_start=ADMIT, period_end=None,
        visit_title="Inpatient admission — acute CHF exacerbation",
        reason_text="Acute decompensated heart failure",
        location_display="5 East — Cardiology", attending_name="Dr. Marcus Feld",
        disposition_status="predicted",
    )
    encounter(
        session, id=ENC_CHF_2025, patient_id=PID, class_code="IMP",
        period_start=CHF25_START, period_end=CHF25_END,
        visit_title="Inpatient admission — CHF exacerbation (first)",
        reason_text="Acute decompensated heart failure",
        location_display="5 East — Cardiology", attending_name="Dr. Marcus Feld",
        planned_disposition="home",
    )
    encounter(
        session, id=ENC_CARDS_DEC, patient_id=PID, class_code="AMB",
        period_start=CARDS_DEC_START, period_end=CARDS_DEC_START + timedelta(minutes=30),
        visit_title="Cardiology follow-up — post-discharge",
        reason_text="Heart failure follow-up after November admission",
        location_display="Cardiology Clinic, Suite 210", attending_name="Dr. Marcus Feld",
        planned_disposition="home",
    )
    encounter(
        session, id=ENC_CARDS_APR, patient_id=PID, class_code="AMB",
        period_start=CARDS_APR_START, period_end=CARDS_APR_START + timedelta(minutes=40),
        visit_title="Cardiology follow-up — echo reassessment",
        reason_text="HFrEF surveillance; repeat echocardiogram",
        location_display="Cardiology Clinic, Suite 210", attending_name="Dr. Marcus Feld",
        planned_disposition="home",
    )

    # --- Conditions -------------------------------------------------------
    condition(session, PID, ENC_CURRENT, "42343007", "Congestive heart failure (disorder)", datetime(2019, 6, 1), category="problem-list-item")
    condition(session, PID, ENC_CURRENT, "44054006", "Type 2 diabetes mellitus (disorder)", datetime(2012, 1, 1), category="problem-list-item")
    condition(session, PID, ENC_CURRENT, "56675007", "Acute heart failure (disorder)", ADMIT)
    condition(session, PID, ENC_CHF_2025, "56675007", "Acute heart failure (disorder)", CHF25_START, status="resolved")

    # --- Vitals -----------------------------------------------------------
    vital(session, PID, ENC_CURRENT, "8867-4", "Heart rate", 74, "/min", NOW - timedelta(hours=3), 60, 100)
    vital(session, PID, ENC_CURRENT, "2708-6", "Oxygen saturation", 97, "%", NOW - timedelta(hours=3), 94, 100)
    vital(session, PID, ENC_CURRENT, "29463-7", "Body weight", 81.4, "kg", NOW - timedelta(hours=6))

    # --- Medications ------------------------------------------------------
    med(session, PID, ENC_CURRENT, "Furosemide", "40 mg", "IV", "BID", ADMIT)
    med(session, PID, ENC_CURRENT, "Metoprolol succinate", "50 mg", "PO", "daily", ADMIT)
    med(session, PID, ENC_CURRENT, "Lisinopril", "20 mg", "PO", "daily", ADMIT)
    med(session, PID, ENC_CURRENT, "Dapagliflozin", "10 mg", "PO", "daily", ADMIT)
    med(session, PID, ENC_CURRENT, "Spironolactone", "12.5 mg", "PO", "daily", ADMIT + timedelta(days=1))
    # IV-to-PO transition made on hospital day 2 (see progress note / Placer chat).
    med(session, PID, ENC_CURRENT, "Torsemide", "20 mg", "PO", "daily", NOW - timedelta(hours=2))

    # --- Notes ------------------------------------------------------------
    note(session, id="note-hero-b-hp-current", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="history_and_physical", title="Cardiology H&P — acute CHF exacerbation",
         author="Dr. Marcus Feld", author_role="physician",
         signed_at=ADMIT + timedelta(hours=4), text=HP_CURRENT)
    note(session, id="note-hero-b-prog-d1", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Cardiology progress note — day 1",
         author="Dr. Marcus Feld", author_role="physician",
         signed_at=ADMIT + timedelta(days=1, hours=2), text=PROG_D1)
    note(session, id="note-hero-b-prog-d2", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Cardiology progress note — day 2",
         author="Dr. Marcus Feld", author_role="physician",
         signed_at=NOW - timedelta(hours=1), text=PROG_D2)

    note(session, id="note-hero-b-chf25-hp", patient_id=PID, encounter_id=ENC_CHF_2025,
         note_type="history_and_physical", title="Cardiology H&P — CHF exacerbation (Nov 2025)",
         author="Dr. Marcus Feld", author_role="physician",
         signed_at=CHF25_START + timedelta(hours=5), text=HP_CHF_2025)
    note(session, id="note-hero-b-chf25-prog-1", patient_id=PID, encounter_id=ENC_CHF_2025,
         note_type="progress", title="Cardiology progress note — Nov 2025 day 1",
         author="Dr. Marcus Feld", author_role="physician",
         signed_at=CHF25_START + timedelta(days=1), text=CHF25_PROG_1)
    note(session, id="note-hero-b-chf25-prog-2", patient_id=PID, encounter_id=ENC_CHF_2025,
         note_type="progress", title="Cardiology progress note — Nov 2025 day 2",
         author="Dr. Marcus Feld", author_role="physician",
         signed_at=CHF25_START + timedelta(days=2), text=CHF25_PROG_2)
    note(session, id="note-hero-b-chf25-prog-3", patient_id=PID, encounter_id=ENC_CHF_2025,
         note_type="progress", title="Cardiology progress note — Nov 2025 day 3",
         author="Dr. Marcus Feld", author_role="physician",
         signed_at=CHF25_START + timedelta(days=3), text=CHF25_PROG_3)
    note(session, id="note-hero-b-chf25-dc", patient_id=PID, encounter_id=ENC_CHF_2025,
         note_type="discharge_summary", title="Discharge summary — CHF admission (Nov 2025)",
         author="Dr. Marcus Feld", author_role="physician",
         signed_at=CHF25_END - timedelta(hours=1), text=CHF25_DC)

    note(session, id="note-hero-b-cards-dec", patient_id=PID, encounter_id=ENC_CARDS_DEC,
         note_type="progress", title="Cardiology clinic note — post-discharge follow-up",
         author="Dr. Marcus Feld", author_role="physician",
         signed_at=CARDS_DEC_START + timedelta(minutes=25), text=CARDS_DEC_NOTE)
    note(session, id="note-hero-b-cards-apr", patient_id=PID, encounter_id=ENC_CARDS_APR,
         note_type="progress", title="Cardiology clinic note — echo reassessment",
         author="Dr. Marcus Feld", author_role="physician",
         signed_at=CARDS_APR_START + timedelta(minutes=35), text=CARDS_APR_NOTE)

    # --- Dispo domain -----------------------------------------------------
    session.add(
        DispoAssessment(
            id="dispo-hero-b",
            patient_id=PID,
            encounter_id=ENC_CURRENT,
            predicted_disposition="home_with_services",
            confidence=0.71,
            rationale=(
                "66yo with HFrEF exacerbation improving rapidly on diuresis, independent at baseline, "
                "single-story home with an engaged spouse — but the spouse works weekdays and both "
                "admissions followed adherence lapses. Home discharge with home-health nursing for "
                "daily weights, med reconciliation, and CHF teach-back is most likely; no skilled "
                "facility indicated."
            ),
            barriers=[
                "Home-health referral not yet placed",
                "IV-to-PO diuretic transition must hold overnight",
            ],
            alternatives=[
                {"disposition": "home", "confidence": 0.22},
                {"disposition": "snf", "confidence": 0.07},
            ],
            assessed_by="Placer",
            is_current=True,
        )
    )
    session.add(
        CareTask(
            id="task-hero-b-hh",
            patient_id=PID,
            encounter_id=ENC_CURRENT,
            task_type="draft_consult",
            title="Place home-health referral",
            description="Skilled nursing visits for CHF weight monitoring and med teaching (HomeTeam).",
            status="pending",
            priority="medium",
            assigned_to="Placer",
            related_facility_id="fac-hometeam-hh",
        )
    )

    # --- Placer chat ------------------------------------------------------
    for i, (sender, sender_name, hours, text) in enumerate(CHAT, start=1):
        placer_msg(
            session, id=f"msg-hero-b-{i}", patient_id=PID,
            sender=sender, sender_name=sender_name, text=text,
            at=NOW + timedelta(hours=hours),
        )
