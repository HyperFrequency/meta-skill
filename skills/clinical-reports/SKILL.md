---
name: clinical-reports
version: 0.1.0
description: >-
  Write and compliance-check clinical documents against their governing
  standards: case reports (CARE), diagnostic reports (radiology/pathology/lab —
  BI-RADS/LI-RADS/PI-RADS, CAP synoptic, TNM), clinical-trial safety and study
  reports (SAE reporting timelines, ICH-E3 CSR, CONSORT), and patient records
  (SOAP, H&P, discharge, consult). Includes de-identification (18 HIPAA
  identifiers, Safe Harbor vs Expert Determination) and regulatory framing
  (HIPAA, FDA 21 CFR, ICH-GCP). Use WHEN drafting, structuring, or
  compliance-checking any of these documents, or de-identifying clinical text
  for publication. Do NOT use for making clinical/diagnostic decisions, as a
  substitute for institutional IRB/legal/regulatory sign-off, for generating
  synthetic patient data, for general manuscript prose (use scientific-writing),
  figures (use scientific-schematics), citations (use citation-management), or
  statistics (use statistical-analysis).
allowed-tools: Read Write Edit Bash
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Clinical Reports

## Overview

Produce clinical documentation that is accurate, complete, objective, and
compliant with the standard that governs each document type. This skill is a
router across four families of clinical report, each with its own required
structure and its own regulatory guardrails:

1. **Case reports** for peer-reviewed publication (CARE guideline).
2. **Diagnostic reports** — radiology, pathology, laboratory.
3. **Clinical-trial reports** — serious adverse events (SAE) and clinical study
   reports (CSR, ICH-E3).
4. **Patient documentation** — SOAP notes, History & Physical, discharge and
   consult notes.

**Non-negotiable principle: patient privacy and data integrity come first.**
Before any document leaves the workflow, confirm it is de-identified to the
correct standard and that required consent/approval exists. See
`references/regulatory_and_terminology.md`.

This SKILL.md is a concise router. The full checklists, section templates,
regulatory timelines, and terminology tables live in `references/` — load the
one matching the document you are working on.

## When to Use This Skill

- Drafting or structuring a **case report** for journal submission (CARE).
- Writing a **radiology, pathology, or laboratory** report to a standard layout
  (structured reporting, CAP synoptic, critical-value handling).
- Documenting a **serious adverse event** or assembling a **clinical study
  report** for a regulatory submission.
- Writing **SOAP notes, an H&P, a discharge summary, or a consult note**.
- **De-identifying** clinical text (removing/altering the 18 HIPAA identifiers)
  before publication or data sharing.
- **Compliance-checking** an existing clinical document for completeness,
  required sections, terminology, and privacy.

## When NOT to Use This Skill

- **Making a clinical or diagnostic decision.** This skill formats and checks
  documentation; it does not interpret a patient's imaging, choose a treatment,
  or determine causality — a qualified clinician does that.
- **As a substitute for institutional sign-off.** Generated text does not
  replace IRB/IEC review, legal review, sponsor/medical-writer QC, or the
  formal regulatory filing itself.
- **Generating synthetic or fabricated patient data.** Do not invent clinical
  values, outcomes, or identities.
- **General manuscript prose / IMRAD narrative** → use `scientific-writing`.
- **Producing figure or diagram image files** (timelines, CONSORT flow) → use
  `scientific-schematics`.
- **Reference discovery and BibTeX management** → use `citation-management`.
- **Statistical analysis of trial data** (the analysis, not its write-up) → use
  `statistical-analysis`.
- **Reviewing** a manuscript rather than writing one → use `peer-review`.

## Choosing the Right Report Family

| You are writing… | Governing standard | Reference |
| --- | --- | --- |
| Case report for publication | CARE guideline | `references/case_reports.md` |
| Radiology / pathology / lab report | ACR + RADS, CAP synoptic + TNM, CLIA | `references/diagnostic_reports.md` |
| SAE report / clinical study report | 21 CFR 312.32, ICH-E3, CONSORT | `references/clinical_trials.md` |
| SOAP / H&P / discharge / consult | Institutional + billing (E/M) | `references/patient_documentation.md` |
| Any of the above (privacy + coding) | HIPAA, FDA, ICH-GCP, SNOMED/LOINC/ICD-10/CPT | `references/regulatory_and_terminology.md` |

### 1. Case reports (CARE)

Report an unusual presentation, novel diagnosis, or rare complication in the
13-item CARE structure: title/keywords, structured abstract, introduction,
**de-identified** patient information with documented consent, timeline,
diagnostic assessment, therapeutic intervention, follow-up/outcomes, discussion,
and (encouraged) patient perspective. Full checklist, journal-fit notes, and
consent language: `references/case_reports.md`.

### 2. Diagnostic reports

- **Radiology** — Indication → Technique → Comparison → Findings (systematic,
  positives then pertinent negatives, with measurements) → Impression that
  answers the clinical question. Use structured systems where they apply
  (BI-RADS, Lung-RADS, LI-RADS, PI-RADS, C-RADS).
- **Pathology** — Specimen → Clinical history → Gross → Microscopic → Diagnosis,
  with **CAP synoptic** elements and TNM staging for cancer specimens.
- **Laboratory** — result + units + reference range + abnormal flags, with
  explicit **critical-value** notification (who, when).

Layouts, RADS categories, synoptic elements, and critical-value thresholds:
`references/diagnostic_reports.md`.

### 3. Clinical-trial reports

- **SAE** — determine seriousness, severity, causality, and expectedness, then
  report on the regulatory clock. FDA IND safety reports (21 CFR 312.32): fatal
  or life-threatening **unexpected** suspected adverse reactions within **7
  calendar days**, other serious unexpected reactions within **15 calendar
  days**; IRB per local policy.
- **CSR** — the ICH-E3 16-section structure (synopsis → ethics → design →
  patients → efficacy → safety → discussion → tables/appendices).

Seriousness criteria, causality scales, timelines, ICH-E3 section map, protocol
deviations, and CONSORT flow: `references/clinical_trials.md`.

### 4. Patient documentation

SOAP (Subjective/Objective/Assessment/Plan), the full H&P (CC, HPI via OPQRST,
PMH, meds, allergies, FH, SH, ROS, exam, A&P), discharge summaries, and consult
notes. Templates and the elements each note must carry (including for E/M
billing): `references/patient_documentation.md`.

## De-identification (do this before publishing or sharing)

Case reports and any shared clinical text must be de-identified. Under HIPAA
**Safe Harbor**, remove/alter all **18 identifiers** (names, geography smaller
than state, all date elements except year, phone/fax, email, SSN, MRN, plan and
account numbers, license/vehicle/device identifiers, URLs, IPs, biometrics,
full-face photos, and any other unique identifier). Ages **over 89** must be
aggregated to "90 or older". The alternative is **Expert Determination**.

A regex scan (`Dr\.`, `\d{3}-\d{2}-\d{4}` SSN, `MM/DD/YYYY` dates, phone, email,
MRN labels, `\d+\.\d+\.\d+\.\d+` IPs, image filenames, ages > 89) flags likely
leaks fast, but is a **heuristic aid, not a compliance guarantee** — always
finish with a manual review. Identifier list, both methods, and scan patterns:
`references/regulatory_and_terminology.md`.

## Cross-Skill Integration

- `scientific-writing` — narrative prose for the discussion of a case report.
- `scientific-schematics` — timeline, diagnostic-algorithm, or CONSORT figures.
- `citation-management` — references for the introduction/discussion.
- `peer-review` — evaluating a clinical manuscript you are reviewing.
- `literature-review` — the background/similar-cases search for a case report.
- `research-grants` — clinical-trial protocol development upstream of a CSR.

## Common Pitfalls

- **Case reports:** weak de-identification or missing consent; no novelty; broad
  conclusions from a single case.
- **Diagnostic reports:** vague language ("unremarkable" without specifics); no
  comparison to priors; impression that never answers the clinical question;
  delayed critical-value notification.
- **Trial reports:** missing an SAE deadline; thin causality rationale;
  unreported protocol deviations; selective reporting of outcomes.
- **Patient notes:** copy-forward propagating stale data; no documented medical
  necessity; unsigned/undated notes.

## Final Check Before Finalizing

- [ ] All required sections for the document type present.
- [ ] De-identified to the correct standard; consent/approval on file.
- [ ] Clinical data accurate and verified; correct terminology and codes.
- [ ] Correct standard applied (CARE / RADS+CAP / 21 CFR+ICH-E3 / institutional).
- [ ] Regulatory deadlines met (SAE) and signatures/dates present.
