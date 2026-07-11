---
name: clinical-decision-support
version: 0.1.0
description: >-
  Produce publication-ready clinical decision support (CDS) documents for pharmaceutical
  and clinical-research settings — biomarker-stratified patient cohort analyses (survival
  outcomes, hazard ratios, waterfall/forest plots) and evidence-based treatment
  recommendation reports (GRADE grading, decision algorithms, TikZ flowcharts), rendered
  to LaTeX/PDF. Use when you need GROUP-LEVEL analytical deliverables: trial subgroup
  analyses, real-world-evidence cohorts, clinical-guideline development, or regulatory /
  medical-affairs documents that pair statistics with evidence grading. Do NOT use for
  individual bedside patient care plans (use a patient `treatment-plans` skill), a bare
  statistical run with no clinical document (use `statistical-analysis` / `statsmodels`),
  a citation/literature pull with no synthesis (use `literature-review` /
  `citation-management`), or diagram generation alone (use `scientific-schematics`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "lifelines BSD-3-Clause; scipy / matplotlib / pandas BSD-3-Clause"
---

# Clinical Decision Support Documents

## Overview

Build analytical, evidence-graded documents that inform treatment strategy and drug
development at the **population** level. This skill covers two deliverables and the
statistics, evidence grading, and formatting that back them:

1. **Patient Cohort Analysis** — biomarker- or subtype-stratified groups compared on
   survival and response endpoints, with hazard ratios and publication figures.
2. **Treatment Recommendation Report** — evidence-based guidance graded with the GRADE
   system, expressed as line-of-therapy recommendations and decision algorithms.

Both render to LaTeX/PDF at data-dense margins, suitable for regulatory submissions,
medical-affairs materials, and guideline development. The analysis layer uses standard
scientific Python (`lifelines` for survival, `scipy.stats` for group tests, `matplotlib`
for figures); the document layer is LaTeX with `tcolorbox` summary boxes and `TikZ`
algorithm flowcharts.

## When to Use This Skill

Use this skill when the request is for a **group-level clinical/pharma document**:

- Stratify a patient cohort by biomarker, molecular subtype, or clinical feature and
  compare outcomes (OS, PFS, ORR, DOR, DCR) with hazard ratios and 95% CIs.
- Generate a treatment recommendation report with GRADE-graded recommendations by line
  of therapy for a disease state.
- Synthesize evidence across multiple trials or real-world data into an evidence table
  with quality ratings.
- Build a biomarker-guided therapy-selection algorithm as a decision flowchart.
- Produce trial subgroup analyses, real-world-evidence cohort studies, or guideline
  drafts for a specialty society or medical-affairs team.

Anti-triggers overlap with siblings — read the next section before proceeding.

## When NOT to Use This Skill

- **Individual patient care at the bedside** — SMART goals, patient-specific dosing, EHR
  care plans. Use a `treatment-plans` skill. This skill is population/evidence-level, not
  one-patient.
- **A statistical computation with no clinical document** — if the ask is "fit a Cox
  model" or "run a log-rank test" with no report to produce, use `statistical-analysis`
  or `statsmodels` directly.
- **A literature search / citation pull with no synthesis or grading** — use
  `literature-review` or `citation-management`.
- **A standalone diagram** with no surrounding analysis — call `scientific-schematics`
  directly.
- **Journal-manuscript prose and formatting** — draft narrative and CONSORT/STROBE
  structure with `scientific-writing`; return here for the analytical CDS artifact.

## Workflow

1. **Classify the deliverable** — cohort analysis vs treatment recommendation. They share
   the executive-summary-first page structure but differ in body sections. See
   [document-format.md](references/document-format.md).
2. **Define endpoints and grouping up front** — pre-specify subgroups, biomarker
   cut-points, response criteria (RECIST 1.1 / iRECIST), and AE grading (CTCAE v5.0).
   Label exploratory vs pre-planned analyses.
3. **Run the analysis** — survival (Kaplan-Meier + log-rank + Cox), group comparisons,
   effect sizes, multiple-testing control. Method-by-method with concrete `lifelines` /
   `scipy` calls in [cohort-analysis.md](references/cohort-analysis.md).
4. **Grade the evidence** (recommendation reports) — assign GRADE quality and strength,
   reconcile guideline concordance/discordance, build the evidence table. See
   [evidence-and-recommendations.md](references/evidence-and-recommendations.md).
5. **Draw the algorithm** (where a decision pathway is needed) — TikZ flowchart with
   unambiguous decision nodes. See [decision-algorithms.md](references/decision-algorithms.md).
6. **Assemble the document** — page-1 executive summary of colored `tcolorbox` findings,
   then detailed sections, tables, and figures. De-identify per HIPAA Safe Harbor before
   generation. See [document-format.md](references/document-format.md).
7. **Verify** — every recommendation carries a grade; hazard ratios report 95% CIs (not
   just p-values); median follow-up and number-at-risk are shown for survival; statistical
   methods are documented for reproducibility.

## Analytical Backbone

The statistics are not optional decoration — a CDS document that reports p-values without
effect sizes, or survival curves without number-at-risk tables, will not survive review.
Core methods and their library calls live in
[cohort-analysis.md](references/cohort-analysis.md):

- **Survival**: `lifelines.KaplanMeierFitter`, `lifelines.statistics.logrank_test`,
  `lifelines.CoxPHFitter` for adjusted hazard ratios; check proportional hazards before
  trusting a single HR.
- **Group comparisons**: `scipy.stats` — `ttest_ind` / `mannwhitneyu` (continuous),
  `chi2_contingency` / `fisher_exact` (categorical, Fisher for small cells).
- **Effect sizes**: hazard ratio, odds ratio, risk ratio, NNT — always with 95% CI.
- **Multiple testing**: Bonferroni or Benjamini-Hochberg FDR when many subgroups.

## Figures and Visual Algorithms

Clinical decision documents communicate through figures: Kaplan-Meier curves, waterfall
and swimmer plots, forest plots, patient-flow (CONSORT-style) diagrams, and treatment
decision flowcharts. Generate data plots with `matplotlib` (recipes in
[cohort-analysis.md](references/cohort-analysis.md)); generate conceptual diagrams and
mechanism figures by delegating to the `scientific-schematics` skill. Encode
decision-pathway flowcharts as TikZ so they stay editable in the LaTeX source — see
[decision-algorithms.md](references/decision-algorithms.md).

## House Rules

- **Executive summary first**: page 1 is a full-page scannable summary of 3-5 colored
  `tcolorbox` findings; no table of contents or detailed prose on page 1.
- **De-identification**: strip all 18 HIPAA Safe Harbor identifiers before rendering;
  add confidentiality notices for proprietary pharmaceutical data.
- **Traceability**: cite trials by name (e.g. KEYNOTE-189, FLAURA, CLEOPATRA), grade
  every recommendation, and document statistical methods so results can be reproduced.

## Reference Files

- [references/cohort-analysis.md](references/cohort-analysis.md) — stratification methods,
  outcome endpoints, survival/statistical analysis with `lifelines` + `scipy`, table and
  plot formats.
- [references/evidence-and-recommendations.md](references/evidence-and-recommendations.md)
  — GRADE grading, guideline systems, evidence synthesis and meta-analysis, treatment
  sequencing, biomarker-drug pairs, special populations.
- [references/decision-algorithms.md](references/decision-algorithms.md) — algorithm
  design, TikZ flowchart patterns, risk scores, validation and update process.
- [references/document-format.md](references/document-format.md) — page-1 executive
  summary, LaTeX/`tcolorbox` structure, output specification, HIPAA/regulatory compliance.
