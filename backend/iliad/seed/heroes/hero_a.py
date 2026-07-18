"""Hero A — Rosa Alvarez, 78F, acute ischemic stroke.

The classic SNF-placement storyline: previously independent widow in a
second-floor walk-up, now with dense left hemiparesis and dysphagia, daughter
out of state, Medicare Advantage plan, target SNF requiring a COVID PCR that is
still pending. Prior chart: a 2024 TIA admission (the warning shot), a
cardiology follow-up, and a PCP annual — so agents have real history to read.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlmodel import Session

from ...models import (
    CareTask,
    Communication,
    DispoAssessment,
    Observation,
    Order,
    Patient,
)
from .common import NOW, condition, encounter, med, note, placer_msg, vital

PID = "hero-a-stroke"
ENC_CURRENT = "enc-hero-a"
ENC_TIA = "enc-hero-a-2024-tia"
ENC_CARDS = "enc-hero-a-2024-cards"
ENC_PCP = "enc-hero-a-2026-pcp"

ADMIT = NOW - timedelta(days=3)  # 2026-07-15 08:00
TIA_START = datetime(2024, 10, 8, 14, 30)
TIA_END = datetime(2024, 10, 11, 11, 0)
CARDS_START = datetime(2024, 11, 19, 9, 0)
PCP_START = datetime(2026, 3, 10, 10, 30)


# ---------------------------------------------------------------------------
# Current admission notes
# ---------------------------------------------------------------------------

HP_CURRENT = """# Neurology History & Physical

**Chief Complaint:** Acute left-sided weakness and slurred speech.

**HPI:** Mrs. Rosa Alvarez is a 78-year-old right-handed widowed woman with hypertension, hyperlipidemia, and a prior TIA (October 2024) who presents with acute onset left-sided weakness and dysarthria. She was found by a neighbor at approximately 06:30 on the day of admission, seated on her kitchen floor, unable to stand, with slurred speech and a left facial droop. She had last been seen normal the prior evening around 21:00 when she spoke with her daughter by phone. EMS transported her to the Iliad General emergency department, where NIH Stroke Scale was 14 (left facial droop, dense left arm and leg weakness, dysarthria, left-sided sensory loss, partial gaze preference). Given the unknown time of onset well beyond the thrombolysis window and no large-vessel occlusion amenable to thrombectomy on CTA, she was not a candidate for acute reperfusion therapy. MRI brain confirmed an acute right MCA-territory infarct involving the corona radiata and insular cortex. She was admitted to the neuro ICU for the first night for blood pressure monitoring and transferred to the floor the following morning.

**Review of Systems:** Positive for left-sided weakness, dysarthria, and difficulty swallowing thin liquids. Negative for headache, neck pain, chest pain, palpitations, fever, dysuria. Remainder of a 10-system review is negative except as noted in the HPI.

**Past Medical History:**
1. Transient ischemic attack, October 2024 (transient right arm weakness and dysphasia; MRI negative at that time)
2. Essential hypertension (since ~2015)
3. Hyperlipidemia
4. Osteoarthritis, bilateral knees

**Past Surgical History:** Cholecystectomy (1998). Right total knee arthroplasty (2016).

**Home Medications:**
- Aspirin 81 mg PO daily (started after 2024 TIA)
- Atorvastatin 80 mg PO nightly
- Lisinopril 10 mg PO daily
- Acetaminophen 500 mg PO PRN knee pain

**Allergies:** No known drug allergies.

**Social History:** Widowed since 2019; retired school cafeteria manager. Lives ALONE in a second-floor walk-up apartment in Chelsea (18 Winnisimmet St, Apt 3) — approximately 14 stairs, NO elevator, no chair lift, bathroom without grab bars. Prior to this event she was fully independent in all ADLs and IADLs: cooked daily, managed her own medications and finances, walked to church and the market without an assistive device, and climbed her stairs without difficulty. She stopped driving after the 2024 TIA and uses the bus or rides from friends. Her only child, daughter Marisol Alvarez-Reyes, lives in Miami, Florida and works full-time; she visits two or three times a year and speaks with her mother daily by phone. No other family locally; an elderly neighbor checks in most days. Never smoker; wine rarely; no other substances. Insurance: Tufts Medicare Preferred (Medicare Advantage HMO).

**Family History:** Mother died of stroke at 81. Father died of myocardial infarction at 74. No known malignancy.

**Physical Exam:**
- Vitals: T 37.0 C, HR 82, BP 158/84 (permissive), RR 16, SpO2 96% on room air.
- General: Elderly woman, alert, frustrated by her speech. No acute distress.
- HEENT: Left lower facial droop. Moist mucous membranes. No carotid bruits.
- Cardiac: Regular rate and rhythm, no murmur. Telemetry without atrial fibrillation to date.
- Pulmonary: Clear to auscultation bilaterally.
- Abdomen: Soft, non-tender.
- Neurologic: Alert, oriented x3. Dysarthric but comprehensible. Left facial droop sparing the forehead. Motor: left deltoid 1/5, left grip 2/5, left hip flexion 2/5, left dorsiflexion 1/5; right side 5/5 throughout. Diminished sensation to light touch on the left. Reflexes brisker on the left, left Babinski upgoing. NIHSS 12 today (improved from 14).
- Extremities: No edema. Well-healed right knee incision.

**Labs/Imaging:** MRI brain: acute right MCA infarct, no hemorrhagic conversion. CTA head/neck: 40% right ICA stenosis, no occlusion. TTE: EF 60%, no thrombus; bubble study negative. LDL 118. HbA1c 5.9. TSH normal. Telemetry: sinus rhythm, no AF captured; 30-day monitor to be arranged.

**Assessment & Plan:** 78-year-old woman with acute right MCA ischemic stroke, presumed large-artery atherosclerosis vs. cardioembolic, with dense left hemiparesis and oropharyngeal dysphagia.

1. **Acute ischemic stroke:** Continue aspirin 81 mg and high-intensity atorvastatin. Permissive hypertension for 48h, then resume gentle BP control (lisinopril). 30-day event monitor for occult AF. DVT prophylaxis.
2. **Dysphagia:** Failed bedside swallow. Speech-language pathology consulted; video swallow ordered. NPO except modified diet per SLP; aspiration precautions.
3. **Left hemiparesis / deconditioning:** PT/OT evaluation and daily therapy. Fall precautions.
4. **Hypertension / hyperlipidemia:** As above; recheck lipids in 3 months.
5. **Disposition:** Major open problem. She lives alone in a second-floor walk-up with no elevator and was previously independent — she cannot return to that apartment requiring maximal assistance for transfers. Anticipate skilled nursing facility placement for subacute rehab; if her therapy tolerance improves toward 3 hours/day, acute inpatient rehab (IRF) could be considered, which would require a PM&R consult to certify. Her daughter (Miami, FL) is her only family and cannot provide in-home care locally. Insurance is Tufts Medicare Preferred — SNF benefit requires plan authorization; case management aware. Target SNFs require a negative COVID PCR within 48 hours of admission — test pending. Social work to contact daughter regarding facility preference.
"""

PROG_D1 = """# Neurology Progress Note — Hospital Day 1

**Subjective:** Transferred overnight from the neuro ICU to 7 West. No headache. Frustrated that her left arm "won't listen." Slept in short stretches.

**Objective:** T 36.8, HR 78, BP 162/86 (permissive), SpO2 97% RA. NIHSS 13. Dense left arm plegia, left leg antigravity only. Dysarthria unchanged. Telemetry: sinus rhythm, no AF. Repeat CT: no hemorrhagic conversion.

**Assessment/Plan:** 78F with right MCA ischemic stroke, day 1, neurologically stable.
- Continue aspirin 81 mg, atorvastatin 80 mg; hold lisinopril one more day (permissive HTN), resume tomorrow.
- Strict NPO pending speech evaluation today; IV fluids.
- PT/OT consults placed; evaluations expected tomorrow.
- Foley avoided; bladder scans. DVT prophylaxis with heparin SQ.
- Dispo: flagged early as high placement risk — lives alone, second-floor walk-up. Case management and social work notified on admission. Daughter in Florida aware she is hospitalized.

— Dr. Priya Nadkarni, Neurology
"""

PROG_D2 = """# Neurology Progress Note — Hospital Day 2

**Subjective:** "The therapists worked me hard." Reports her swallow feels safer with thicker liquids. Mood fair; asked when she can go home, then acknowledged she "knows the stairs are a problem."

**Objective:** T 37.0, HR 80, BP 154/82, SpO2 96% RA. NIHSS 12. Left deltoid now 1-2/5, left hip flexion 2/5. Video swallow (SLP): moderate oropharyngeal dysphagia with silent aspiration of thin liquids; safe for nectar-thick liquids and moist ground solids with chin-tuck. PT eval: maximal assist x2 for bed-to-chair transfers, unable to ambulate; sitting balance fair. OT eval: maximal assist for lower-body dressing and toileting; standing tolerance under one minute.

**Assessment/Plan:** Right MCA stroke, day 2, small early motor gains.
- Advance to dysphagia diet per SLP (nectar-thick liquids, ground solids); aspiration precautions; daily SLP treatment.
- Daily PT/OT; therapy notes document current tolerance ~45-60 min/day — below IRF threshold at present, favoring SNF-level rehab.
- Resume lisinopril 10 mg today; BP goal <160/90 this week.
- Dispo: case management screening SNFs with Tufts Medicare Preferred contracts near Chelsea so her neighbor and church community can visit. COVID PCR sent (SNF admission requirement). Social work to call daughter today regarding preference.

— Dr. Priya Nadkarni, Neurology
"""

PROG_D3 = """# Neurology Progress Note — Hospital Day 3

**Subjective:** Brighter today. Tolerating the modified diet without coughing. Worked with PT this morning; stood at the parallel bars with two assist for nearly two minutes.

**Objective:** T 36.9, HR 82, BP 148/80, SpO2 96% RA. NIHSS 11. Left hip flexion 3/5 today; arm unchanged. Taking >75% of meals on the dysphagia diet. Telemetry remains sinus. COVID PCR: still pending in lab.

**Assessment/Plan:** Right MCA stroke, day 3, slow steady improvement; medically stable for discharge to subacute rehab once placement clears.
- Continue aspirin/statin/lisinopril; discontinue telemetry today, 30-day monitor ordered at discharge.
- PT/OT/SLP daily; therapy tolerance improving but still well under 3 h/day.
- Swallow: SLP will re-titrate diet before discharge; likely discharges on nectar-thick liquids.
- Dispo: SNF placement is the working plan — Sunny Acres (Chelsea) has beds and takes her plan but requires a negative COVID PCR within 48h; result pending. Social work spoke with daughter yesterday (see separate note) — family favors Sunny Acres. Anticipate discharge early next week if PCR results and the plan authorizes.

— Dr. Priya Nadkarni, Neurology
"""

FAM_CURRENT = """# Social Work — Family Communication

Telephone call with Marisol Alvarez-Reyes (daughter, sole family contact, lives in Miami, FL; number on file), approximately 25 minutes.

Reviewed her mother's stroke, current function (maximal assistance for transfers, modified diet), and the team's recommendation for skilled nursing facility rehab. Daughter was tearful but engaged. She confirmed her mother cannot manage the second-floor walk-up as she is now, and that she herself cannot relocate to Boston; she works full-time and has two school-age children. We discussed two paths: (1) subacute rehab at a SNF near Chelsea, with a later re-assessment about returning home with services or considering assisted living; (2) eventually moving her mother to Florida to live near her — daughter feels this is premature and her mother "would refuse to leave Chelsea." She prefers Sunny Acres given proximity to her mother's neighbor and church community, and asked about Tufts Medicare Preferred coverage of the SNF stay; I explained plan authorization is being pursued by case management. Daughter will call her mother daily and can fly up on short notice for a family meeting if needed.

Plan: relay preference to case management; update daughter when the COVID PCR results and a bed date is set.

— Karen Mullaney, LICSW
"""

# ---------------------------------------------------------------------------
# Prior TIA admission (Oct 2024)
# ---------------------------------------------------------------------------

HP_TIA = """# Neurology History & Physical — TIA

**Chief Complaint:** Transient right arm weakness and difficulty finding words.

**HPI:** Mrs. Rosa Alvarez is a 76-year-old widowed woman with hypertension and hyperlipidemia who presents after a 45-minute episode of right arm heaviness and word-finding difficulty that began while she was preparing lunch. Her neighbor, present at the time, reports her speech was "jumbled" and she could not lift her coffee cup; there was no facial droop she noticed, no leg involvement, and no loss of consciousness. The episode resolved gradually and completely over three-quarters of an hour, and by the time EMS arrived she was conversing normally and insisting she did not need to go to the hospital. She has never had a similar episode. She denies preceding palpitations, chest pain, headache, or visual change, and there was no head trauma. In the ED she was back to baseline; NIHSS 0. Given her age, blood pressure of 172/94 on arrival, unilateral weakness with speech disturbance, and symptom duration over 10 minutes (ABCD2 score 5), she was admitted for expedited TIA evaluation and telemetry monitoring rather than outpatient workup.

**Review of Systems:** Negative for headache, chest pain, palpitations, visual change, vertigo, or prior similar episodes. Otherwise negative in 10 systems.

**Past Medical History:** Essential hypertension (~2015). Hyperlipidemia (untreated to date). Osteoarthritis, bilateral knees.

**Past Surgical History:** Cholecystectomy (1998). Right total knee arthroplasty (2016).

**Home Medications:** Lisinopril 10 mg PO daily. Acetaminophen PRN knee pain. She takes no antiplatelet or statin at present.

**Allergies:** No known drug allergies.

**Social History:** Widowed, lives alone in a second-floor walk-up apartment in Chelsea. Fully independent in all ADLs and IADLs — cooks, shops, manages medications and finances, climbs her stairs daily without difficulty. Still drives short distances locally. Daughter Marisol lives in Miami, FL; they speak daily. Retired school cafeteria manager. Never smoker; rare wine. Insurance: Tufts Medicare Preferred.

**Family History:** Mother died of stroke at 81. Father died of MI at 74.

**Physical Exam:**
- Vitals: T 36.8, HR 76, BP 168/90, RR 14, SpO2 98% RA.
- General: Well-appearing, no distress.
- HEENT: No facial asymmetry. No carotid bruits.
- Cardiac: Regular rate and rhythm, no murmur.
- Pulmonary: Clear bilaterally.
- Neurologic: NIHSS 0. Cranial nerves II-XII intact. Strength 5/5 throughout, sensation intact, no drift, fluent speech, normal repetition and naming. Gait narrow-based and steady.

**Labs/Imaging:** MRI brain: no acute infarct; mild chronic small-vessel change. CTA head/neck: 30-40% right ICA plaque, no flow-limiting stenosis. TTE: EF 60%, no source of embolism. ECG: sinus rhythm. LDL 142. HbA1c 5.8. CBC/BMP unremarkable.

**Assessment & Plan:** 76-year-old woman with a high-risk TIA (ABCD2 5), most likely small-vessel disease or artery-to-artery embolism from non-stenotic right ICA plaque; cardioembolism not yet excluded.
1. **TIA / secondary prevention:** Start aspirin 81 mg daily and atorvastatin 80 mg nightly (LDL 142, goal <70 on high-intensity therapy). Continue lisinopril; BP goal <130/80 as an outpatient, allowing moderate values during the acute window. Telemetry during admission; discharge with a 14-day event monitor to exclude paroxysmal atrial fibrillation, which would change management to anticoagulation.
2. **Hypertension:** Home readings requested; uptitrate lisinopril at PCP follow-up if consistently >140 systolic.
3. **Carotid disease:** 30-40% right ICA plaque — below any revascularization threshold; optimal medical therapy as above with surveillance only if symptoms recur.
4. **Counseling:** Stroke warning signs (FAST) reviewed with the patient in person and with her daughter by phone with the patient's consent. Advised not to drive until cleared at follow-up; she was reluctant but agreed.
5. **Disposition:** Expected discharge home in 1-2 days once telemetry is complete. She is fully independent at baseline, lives alone but manages all ADLs/IADLs, and has a nearby neighbor and daily phone contact with her daughter; no home services indicated. Follow-up: cardiology for monitor results in 4-6 weeks, PCP in 2 weeks for risk-factor management.
"""

TIA_PROG_1 = """# Neurology Progress Note — TIA, Day 1

**Subjective:** No recurrent symptoms overnight. Feels "perfectly fine" and is eager to go home; worried about who is watering her plants.

**Objective:** T 36.7, HR 74, BP 156/84, SpO2 98% RA. NIHSS 0. Exam unchanged — no deficits. Telemetry: sinus rhythm, no ectopy.

**Assessment/Plan:** High-risk TIA, workup in progress. Aspirin and atorvastatin started, tolerated. TTE done — no embolic source. Await final CTA read; continue telemetry a second night given ABCD2 of 5. Reinforced stroke warning signs; daughter updated by phone with patient's permission. Anticipate discharge tomorrow with 14-day event monitor.

— Dr. Samuel Ortiz, Neurology
"""

TIA_PROG_2 = """# Neurology Progress Note — TIA, Day 2

**Subjective:** No symptoms. Ambulating the hallway independently. Asking to leave this morning.

**Objective:** T 36.8, HR 72, BP 148/82. NIHSS 0. Telemetry x48h: sinus rhythm throughout, no atrial fibrillation.

**Assessment/Plan:** TIA workup essentially complete and reassuring: MRI negative, CTA with non-flow-limiting right ICA plaque, TTE without source, no AF on telemetry. Discharge today on aspirin 81, atorvastatin 80, lisinopril 10. 14-day monitor arranged. Nursing to complete discharge teaching and call the daughter with the plan (patient consents). Follow-up: cardiology in 4-6 weeks, PCP in 2 weeks.

— Dr. Samuel Ortiz, Neurology
"""

TIA_DC = """# Discharge Summary — TIA Admission

**Admission Diagnosis:** Transient ischemic attack.
**Discharge Diagnoses:** 1. Transient ischemic attack, resolved. 2. Essential hypertension. 3. Hyperlipidemia, newly treated.

**Hospital Course:** 76-year-old woman admitted after a 45-minute episode of right arm weakness and word-finding difficulty, fully resolved on arrival (NIHSS 0). Expedited workup: MRI without acute infarct; CTA with 30-40% right ICA plaque, non-flow-limiting; TTE without embolic source; 48 hours of telemetry without atrial fibrillation. Aspirin 81 mg and atorvastatin 80 mg were started for secondary prevention and tolerated. She remained symptom-free and independent throughout the stay.

**Discharge Medications:** Aspirin 81 mg daily (NEW); atorvastatin 80 mg nightly (NEW); lisinopril 10 mg daily; acetaminophen PRN.

**Disposition:** Discharged HOME, independent, no services needed. She lives alone and is at her functional baseline; her neighbor will check in and her daughter is aware of the plan. A 14-day cardiac event monitor was placed; results to cardiology.

**Follow-up:** Cardiology (Dr. Cho) in 4-6 weeks for monitor review; PCP in 2 weeks for BP check; return precautions for any recurrent focal weakness or speech change reviewed in person and in writing.

— Dr. Samuel Ortiz, Neurology
"""

TIA_FAM = """# Nursing — Family Communication (Discharge Call)

With the patient's verbal consent, telephoned daughter Marisol Alvarez-Reyes (Miami, FL) prior to discharge, ~15 minutes.

Reviewed the admission: transient stroke-warning episode, now fully resolved; all imaging reassuring; two new daily medications (aspirin 81 mg, atorvastatin 80 mg) added to her mother's pillbox. Reviewed FAST stroke warning signs and the instruction to call 911 immediately for any recurrence — daughter repeated these back. Daughter states she speaks with her mother every evening and the downstairs neighbor has a key. She asked whether her mother should still be living alone on the second floor; advised that her mother is at her independent baseline today and that this is a good conversation to continue with the PCP at follow-up. Daughter verbalized understanding and had no further questions. Monitor wear and follow-up appointments reviewed.

— Patricia Doyle, RN, 7 West
"""

CARDS_NOTE = """# Cardiology Clinic Note

**Subjective:** 76F seen in follow-up after October TIA admission. No recurrent neurologic symptoms. Taking aspirin, atorvastatin, and lisinopril without side effects. Home BP log 130-145 systolic. Walking to church daily; no chest pain, dyspnea, or palpitations.

**Objective:** BP 138/78, HR 70 regular. Cardiac exam: regular rate and rhythm, no murmur. 14-day event monitor report reviewed: sinus rhythm throughout, rare PACs, NO atrial fibrillation.

**Assessment/Plan:** TIA workup complete — no AF on extended monitoring, no cardiac source on TTE. Presumed small-vessel/atherosclerotic mechanism; current regimen (aspirin + high-intensity statin + ACE inhibitor) appropriate. No indication for anticoagulation. Continue home BP monitoring, goal <130/80; PCP to uptitrate lisinopril if needed. Cleared to resume driving from a cardiac standpoint; she reports she has decided to give up the car regardless. Return as needed; no routine cardiology follow-up required.

— Dr. Evelyn Cho, Cardiology
"""

PCP_NOTE = """# Primary Care — Annual Visit

**Subjective:** 78F for annual exam. Feels well. No neurologic symptoms since the 2024 TIA. Independent at home: cooking, cleaning, finances, medications; climbs her stairs daily, though knees ache on the way up. Walks 20-30 minutes most days. Daughter in Florida calls daily. Mood good; PHQ-2 negative. Takes aspirin 81, atorvastatin 80, lisinopril 10 reliably (pillbox).

**Objective:** BP 136/76, HR 72, BMI 27.1. Exam: no carotid bruits, heart regular, lungs clear, mild bilateral knee crepitus, gait steady, gets up from chair without using arms. Labs: LDL 88 (on statin), HbA1c 5.9, Cr 0.9, TSH normal.

**Assessment/Plan:**
1. Secondary stroke prevention — at goal; continue current regimen.
2. Hypertension — controlled; continue lisinopril 10.
3. Knee osteoarthritis — acetaminophen PRN; discussed PT referral, she declined for now.
4. Health maintenance — influenza and COVID boosters given today; declined screening mammography at her age after discussion. Fall-risk screen low. Discussed advance care planning; she remains full code and wants her daughter as health care proxy — form given to complete.
5. Living situation — counseled that the second-floor walk-up may become difficult with age; she firmly wishes to stay in her apartment and community. Revisit yearly.

— Dr. Susan Park, Primary Care
"""

# ---------------------------------------------------------------------------
# Placer chat (last 36 hours, ascending)
# ---------------------------------------------------------------------------

CHAT = [
    ("placer", "Placer", -35.0,
     "I've reviewed Ms. Alvarez's chart. Predicting SNF (78% confidence): dense left hemiparesis, "
     "max-assist transfers, lives alone in a 2nd-floor walk-up, only family is out of state. I'm "
     "verifying her Tufts Medicare Preferred SNF authorization and starting outreach to in-network "
     "facilities near Chelsea."),
    ("placer", "Placer", -19.0,
     "Called Sunny Acres Skilled Nursing (Chelsea): 3 beds available, they accept Tufts Medicare "
     "Preferred, and they can take her early next week. One condition — they require a negative COVID "
     "PCR within 48h of admission. Her PCR was collected but is still pending; I'll flag the moment "
     "it results."),
    ("placer", "Placer", -8.0,
     "Two questions for the team: (1) Should I draft a PM&R consult to keep the acute-rehab (IRF) "
     "option open at Bayview in case her therapy tolerance improves past 3h/day? (2) What discharge "
     "date should I give Sunny Acres for the bed hold?"),
    ("provider", "Dr. Priya Nadkarni", -5.0,
     "Yes — please pend the PM&R consult and I'll sign on rounds. Realistically she stays SNF-level, "
     "but keep IRF open. Target discharge Monday 7/20 if swallow keeps improving. SW note says the "
     "daughter prefers Sunny Acres."),
    ("placer", "Placer", -4.0,
     "Got it. I'll pend the PM&R consult for your signature shortly and tell Sunny Acres to plan for "
     "Monday 7/20. I'll also confirm the plan with her daughter Marisol this afternoon and keep the "
     "authorization moving with Tufts."),
    ("placer", "Placer", -2.0,
     "Update: Sunny Acres will hold a bed through Monday, contingent on the negative PCR. Transport "
     "can be booked same-day once the result is back. Remaining barriers: pending COVID PCR, plan "
     "authorization, PM&R consult signature."),
]


def build(session: Session) -> None:
    session.add(
        Patient(
            id=PID,
            mrn="MRN90001",
            family_name="Alvarez",
            given_name="Rosa",
            prefix="Mrs.",
            full_name="Mrs. Rosa Alvarez",
            gender="female",
            birth_date=datetime(1948, 2, 11).date(),
            marital_status="Widowed",
            language="English",
            phone="(617) 555-0134",
            address_line="18 Winnisimmet St, Apt 3",
            city="Chelsea",
            state="MA",
            postal_code="02150",
            emergency_contact_name="Marisol Alvarez-Reyes",
            emergency_contact_relationship="daughter",
            emergency_contact_phone="(305) 555-0188",
            living_situation="lives_alone",
            code_status="full",
        )
    )

    # --- Encounters -------------------------------------------------------
    encounter(
        session, id=ENC_CURRENT, patient_id=PID, class_code="IMP",
        period_start=ADMIT, period_end=None,
        visit_title="Inpatient admission — acute ischemic stroke",
        reason_text="Acute ischemic stroke with left-sided weakness",
        location_display="7 West — Neurology", attending_name="Dr. Priya Nadkarni",
        disposition_status="predicted",
    )
    encounter(
        session, id=ENC_TIA, patient_id=PID, class_code="IMP",
        period_start=TIA_START, period_end=TIA_END,
        visit_title="Inpatient admission — transient ischemic attack",
        reason_text="Transient right arm weakness and dysphasia, resolved",
        location_display="7 West — Neurology", attending_name="Dr. Samuel Ortiz",
        planned_disposition="home",
    )
    encounter(
        session, id=ENC_CARDS, patient_id=PID, class_code="AMB",
        period_start=CARDS_START, period_end=CARDS_START + timedelta(minutes=40),
        visit_title="Cardiology follow-up — post-TIA monitor review",
        reason_text="Event-monitor review after October TIA",
        location_display="Cardiology Clinic, Suite 210", attending_name="Dr. Evelyn Cho",
        planned_disposition="home",
    )
    encounter(
        session, id=ENC_PCP, patient_id=PID, class_code="AMB",
        period_start=PCP_START, period_end=PCP_START + timedelta(minutes=45),
        visit_title="Primary care — annual visit",
        reason_text="Annual preventive visit",
        location_display="Iliad Primary Care Associates", attending_name="Dr. Susan Park",
        planned_disposition="home",
    )

    # --- Conditions -------------------------------------------------------
    condition(session, PID, ENC_CURRENT, "422504002", "Ischemic stroke (disorder)", ADMIT)
    condition(session, PID, ENC_CURRENT, "44695005", "Left hemiparesis (finding)", ADMIT)
    condition(session, PID, ENC_CURRENT, "40739000", "Dysphagia (finding)", ADMIT)
    condition(session, PID, ENC_CURRENT, "59621000", "Essential hypertension (disorder)", datetime(2015, 1, 1), category="problem-list-item")
    condition(session, PID, ENC_CURRENT, "302866003", "Deconditioned (finding)", ADMIT)
    condition(session, PID, ENC_TIA, "266257000", "Transient ischemic attack (disorder)", TIA_START, status="resolved")

    # --- Vitals -----------------------------------------------------------
    vital(session, PID, ENC_CURRENT, "8867-4", "Heart rate", 82, "/min", NOW - timedelta(hours=4), 60, 100)
    vital(session, PID, ENC_CURRENT, "8480-6", "Systolic blood pressure", 158, "mm[Hg]", NOW - timedelta(hours=4), 90, 140, "H")
    vital(session, PID, ENC_CURRENT, "2708-6", "Oxygen saturation", 96, "%", NOW - timedelta(hours=4), 94, 100)
    vital(session, PID, ENC_CURRENT, "8310-5", "Body temperature", 37.0, "Cel", NOW - timedelta(hours=4), 36.1, 37.8)

    # --- Medications ------------------------------------------------------
    med(session, PID, ENC_CURRENT, "Aspirin", "81 mg", "PO", "daily", ADMIT)
    med(session, PID, ENC_CURRENT, "Atorvastatin", "80 mg", "PO", "nightly", ADMIT)
    med(session, PID, ENC_CURRENT, "Lisinopril", "10 mg", "PO", "daily", ADMIT + timedelta(days=1))

    # --- Pending COVID PCR (SNF admission requirement) + physician order --
    covid = Observation(
        id="obs-hero-a-covid",
        patient_id=PID,
        encounter_id=ENC_CURRENT,
        category="laboratory",
        loinc_code="94500-6",
        display="SARS-CoV-2 (COVID-19) RNA [Presence] by NAA",
        status="pending",
        effective_time=NOW - timedelta(hours=20),
    )
    session.add(covid)
    session.add(
        Order(
            id="ord-hero-a-covid",
            patient_id=PID,
            encounter_id=ENC_CURRENT,
            order_type="lab",
            status="signed",
            code="94500-6",
            display="SARS-CoV-2 (COVID-19) NAA test",
            detail="SNF admission requirement — result pending.",
            priority="routine",
            ordered_by="Dr. Priya Nadkarni",
            signed_by="Dr. Priya Nadkarni",
            authored_at=NOW - timedelta(hours=20),
            signed_at=NOW - timedelta(hours=20),
            result_observation_id="obs-hero-a-covid",
        )
    )

    # --- Notes ------------------------------------------------------------
    # Current admission: H&P + one progress note per hospital day, no DC summary.
    note(session, id="note-hero-a-hp-current", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="history_and_physical", title="Neurology H&P — acute ischemic stroke",
         author="Dr. Priya Nadkarni", author_role="physician",
         signed_at=ADMIT + timedelta(hours=3), text=HP_CURRENT)
    note(session, id="note-hero-a-prog-d1", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Neurology progress note — day 1",
         author="Dr. Priya Nadkarni", author_role="physician",
         signed_at=ADMIT + timedelta(days=1, hours=2), text=PROG_D1)
    note(session, id="note-hero-a-prog-d2", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Neurology progress note — day 2",
         author="Dr. Priya Nadkarni", author_role="physician",
         signed_at=ADMIT + timedelta(days=2, hours=2), text=PROG_D2)
    note(session, id="note-hero-a-prog-d3", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="progress", title="Neurology progress note — day 3",
         author="Dr. Priya Nadkarni", author_role="physician",
         signed_at=NOW - timedelta(minutes=30), text=PROG_D3)
    note(session, id="note-hero-a-fam-current", patient_id=PID, encounter_id=ENC_CURRENT,
         note_type="family_communication", title="Social work call with daughter — SNF preference",
         author="Karen Mullaney, LICSW", author_role="social_work",
         signed_at=ADMIT + timedelta(days=2, hours=7), text=FAM_CURRENT)

    # TIA admission (finished IMP): H&P + 2 progress + DC summary + nurse family call.
    note(session, id="note-hero-a-tia-hp", patient_id=PID, encounter_id=ENC_TIA,
         note_type="history_and_physical", title="Neurology H&P — TIA",
         author="Dr. Samuel Ortiz", author_role="physician",
         signed_at=TIA_START + timedelta(hours=4), text=HP_TIA)
    note(session, id="note-hero-a-tia-prog-1", patient_id=PID, encounter_id=ENC_TIA,
         note_type="progress", title="Neurology progress note — TIA day 1",
         author="Dr. Samuel Ortiz", author_role="physician",
         signed_at=TIA_START + timedelta(days=1), text=TIA_PROG_1)
    note(session, id="note-hero-a-tia-prog-2", patient_id=PID, encounter_id=ENC_TIA,
         note_type="progress", title="Neurology progress note — TIA day 2",
         author="Dr. Samuel Ortiz", author_role="physician",
         signed_at=TIA_START + timedelta(days=2), text=TIA_PROG_2)
    note(session, id="note-hero-a-tia-dc", patient_id=PID, encounter_id=ENC_TIA,
         note_type="discharge_summary", title="Discharge summary — TIA admission",
         author="Dr. Samuel Ortiz", author_role="physician",
         signed_at=TIA_END - timedelta(hours=1), text=TIA_DC)
    note(session, id="note-hero-a-tia-fam", patient_id=PID, encounter_id=ENC_TIA,
         note_type="family_communication", title="Nursing discharge call to daughter",
         author="Patricia Doyle, RN", author_role="nursing",
         signed_at=TIA_END - timedelta(minutes=30), text=TIA_FAM)

    # Outpatient visits: exactly one progress note each.
    note(session, id="note-hero-a-cards-2024", patient_id=PID, encounter_id=ENC_CARDS,
         note_type="progress", title="Cardiology clinic note — post-TIA follow-up",
         author="Dr. Evelyn Cho", author_role="physician",
         signed_at=CARDS_START + timedelta(minutes=35), text=CARDS_NOTE)
    note(session, id="note-hero-a-pcp-2026", patient_id=PID, encounter_id=ENC_PCP,
         note_type="progress", title="Primary care annual visit",
         author="Dr. Susan Park", author_role="physician",
         signed_at=PCP_START + timedelta(minutes=40), text=PCP_NOTE)

    # --- Dispo domain -----------------------------------------------------
    session.add(
        DispoAssessment(
            id="dispo-hero-a",
            patient_id=PID,
            encounter_id=ENC_CURRENT,
            predicted_disposition="snf",
            confidence=0.78,
            rationale=(
                "78yo, lives alone (2nd-floor walk-up, no elevator), s/p right MCA stroke with left "
                "hemiparesis and dysphagia, requires max assist for transfers; only family is out of "
                "state. Not safe for home. Therapy tolerance (~45-60 min/day) is below the IRF "
                "threshold, pointing to SNF-level rehab; keep IRF open if tolerance improves."
            ),
            barriers=[
                "Pending SARS-CoV-2 PCR required by target SNF",
                "PM&R consult not yet placed",
                "Tufts Medicare Preferred SNF authorization in progress",
            ],
            alternatives=[
                {"disposition": "inpatient_rehab", "confidence": 0.15},
                {"disposition": "home_with_services", "confidence": 0.05},
            ],
            assessed_by="Placer",
            is_current=True,
        )
    )
    session.add_all([
        CareTask(
            id="task-hero-a-family",
            patient_id=PID,
            encounter_id=ENC_CURRENT,
            task_type="call_family",
            title="Call daughter re: SNF preference",
            description="Confirm preferred SNF and gather insurance details.",
            status="pending",
            priority="high",
            assigned_to="Placer",
            due_at=NOW + timedelta(hours=6),
        ),
        CareTask(
            id="task-hero-a-snf",
            patient_id=PID,
            encounter_id=ENC_CURRENT,
            task_type="call_snf",
            title="Call Sunny Acres re: bed availability",
            description="Verify bed availability and COVID test requirement.",
            status="in_progress",
            priority="high",
            assigned_to="Placer",
            related_facility_id="fac-sunny-acres",
            due_at=NOW + timedelta(hours=4),
        ),
    ])
    session.add(
        Communication(
            patient_id=PID,
            care_task_id="task-hero-a-snf",
            facility_id="fac-sunny-acres",
            direction="outbound",
            modality="phone",
            party_type="snf",
            party_name="Sunny Acres admissions",
            summary="Confirmed 3 beds open. They require a negative COVID PCR within 48h before accepting.",
            outcome="bed_available",
            occurred_at=NOW - timedelta(hours=20),
        )
    )

    # --- Placer chat ------------------------------------------------------
    for i, (sender, sender_name, hours, text) in enumerate(CHAT, start=1):
        placer_msg(
            session, id=f"msg-hero-a-{i}", patient_id=PID,
            sender=sender, sender_name=sender_name, text=text,
            at=NOW + timedelta(hours=hours),
        )
