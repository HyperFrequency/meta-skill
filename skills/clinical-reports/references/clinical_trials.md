# Clinical-Trial Reports (SAE, CSR, CONSORT)

Trial reports document the conduct, safety, and results of clinical research for
regulators and journals. The two highest-stakes documents are the **serious
adverse event (SAE) report** (safety, on a strict clock) and the **clinical
study report (CSR)** (the comprehensive results document).

> These templates support *writing* the report. Causality, expectedness, and the
> decision to file remain the investigator's/sponsor's judgment, and the actual
> submission is a regulated act — coordinate with the sponsor and IRB/IEC.

---

## Serious Adverse Event (SAE) reports

### Is it "serious"?

An adverse event is **serious** if it:

- results in death,
- is life-threatening,
- requires or prolongs inpatient hospitalization,
- causes persistent or significant disability/incapacity,
- is a congenital anomaly/birth defect, or
- requires intervention to prevent permanent impairment (important medical event).

"Serious" (the above) is distinct from **severity** (mild/moderate/severe, which
grades intensity) — a severe headache may be non-serious; a brief hospitalization
may be serious.

### Report components

1. **Study** — protocol number/title, phase, sponsor, PI, IND/IDE number, NCT
   registry number.
2. **Subject (de-identified)** — subject/randomization ID, age, sex,
   race/ethnicity, study arm, consent date, first-dose date.
3. **Event** — narrative description, onset date, resolution date (or ongoing),
   severity, which seriousness criteria are met, outcome (recovered /
   recovering / not recovered / recovered with sequelae / fatal / unknown).
4. **Causality** — relationship to the intervention (unrelated / unlikely /
   possible / probable / definite), to study procedures, and to underlying
   disease, with rationale.
5. **Action taken** — dose change, temporary hold, permanent discontinuation,
   concomitant treatments, hospitalization details, follow-up plan.
6. **Expectedness** — expected per protocol/Investigator's Brochure, or
   **unexpected** (triggers expedited reporting).
7. **Narrative** — the detailed clinical story: timeline, course, management,
   relevant labs/diagnostics, final diagnosis.
8. **Reporter** — name, contact, report date, signature.

### Regulatory timelines (FDA IND, 21 CFR 312.32)

An **IND safety report** is required for a **serious AND unexpected suspected
adverse reaction** (a "SUSAR"):

- **Fatal or life-threatening** SUSAR → report to FDA as soon as possible, no
  later than **7 calendar days** after the sponsor's initial receipt.
- **Other serious, unexpected** suspected adverse reactions → **15 calendar
  days**.
- Follow-up information → within 15 calendar days of receipt.
- **IRB/IEC** notification → per institutional policy (commonly within
  5–10 days for events affecting subject safety).

EU/other regions have parallel SUSAR timelines (typically 7 days fatal/
life-threatening, 15 days other); confirm the specific framework that governs
the trial.

---

## Clinical Study Report (CSR) — ICH E3 structure

The ICH **E3** guideline defines CSR content. The canonical section order:

1. **Title page**
2. **Synopsis** (5–15 pages; can stand alone — objectives, methods, results,
   conclusions)
3. **Table of contents**
4. **Ethics** — IRB/IEC approvals, informed consent, GCP compliance statement
5. **Investigators and administrative structure**
6. **Introduction** — background and rationale
7. **Study objectives**
8. **Investigational plan** — design, methods, endpoints, sample-size
   determination, changes in conduct/analysis
9. **Study patients** — disposition, protocol deviations
10. **Efficacy evaluation** — analysis sets (ITT / per-protocol / safety),
    baseline characteristics, primary and secondary endpoints, subgroup and
    sensitivity analyses, handling of dropouts/missing data
11. **Safety evaluation** — exposure, adverse events (summary tables), SAE
    narratives, laboratory values, vital signs, deaths and other significant
    events
12. **Discussion and overall conclusions** — interpretation, benefit–risk
13. **Tables, figures, and graphs** (referenced in text)
14. **Reference list**
15. **Appendices** — protocol and amendments, sample CRFs, investigator/ethics
    lists, consent forms, statistical documentation, publications

Principles: objectivity and transparency; adhere to the pre-specified
statistical analysis plan; present safety data completely; do not omit
unfavorable results. Efficacy analysis itself → `statistical-analysis`; prose
polishing → `scientific-writing`.

---

## Protocol deviations

Departures from the approved protocol must be documented, graded, and reported.

- **Minor** — no material impact on subject safety or data integrity.
- **Major** — may affect safety, rights, or data integrity.
- **Violation** — serious deviation needing immediate action/reporting.

Document: description, date, affected subject ID, impact on safety/data, root
cause, and corrective/preventive actions (CAPA).

---

## CONSORT (for publishing an RCT)

When the trial is written up for a journal, follow **CONSORT** (Consolidated
Standards of Reporting Trials): the 25-item checklist plus the **participant
flow diagram** (enrolled → allocated → followed up → analyzed, with numbers and
reasons for exclusion/loss at each stage). Draw the flow diagram with
`scientific-schematics`. Extensions exist for specific designs (cluster,
non-inferiority, pilot). Reporting-guideline selection more broadly is covered by
`scientific-writing`.
