---
name: treatment-plans
version: 0.1.0
description: >-
  Draft concise, evidence-based clinical treatment plans as structured LaTeX/PDF
  documents across specialties — general medicine, rehabilitation, mental health,
  chronic-disease management, perioperative care, and pain management. Use when you
  need to author an individualized care plan: SMART goals, guideline-concordant
  interventions with dosing, monitoring parameters, follow-up, patient education,
  risk mitigation, and HIPAA-safe de-identification, with a scannable first-page
  summary. Do NOT use to make real clinical decisions for a specific patient without
  a licensed clinician, to process live PHI without de-identifying it first, or to
  write encounter notes / SOAP / H&P / discharge summaries (use a clinical-notes
  skill), literature reviews (literature-review), or citations alone
  (citation-management).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Treatment Plans

## Overview

A treatment plan is a structured document that translates a diagnosis into a
concrete course of care: measurable goals, evidence-based interventions with
specific dosing and timing, monitoring parameters, follow-up, patient education,
and safety planning. This skill helps you draft such plans as clean LaTeX/PDF
documents across the major clinical specialties, with three non-negotiable
priorities:

1. **Concise and actionable.** Default to the shortest format that carries the
   clinical content — often a single quick-reference page, otherwise 3-4 pages.
   Every line should change a care decision. Prefer tables and bullets over prose.
2. **Evidence-based and specific.** "Reduce HbA1c from 8.5% to <7% within 3 months
   via metformin 1000 mg BID" beats "improve diabetes control." Goals are SMART;
   interventions cite guidelines only where credibility or novelty requires it.
3. **Compliant and de-identified.** Strip all 18 HIPAA identifiers before any plan
   leaves the treating team. Document medical necessity, consent, and safety.

> **Boundary / disclaimer.** This skill drafts *documentation templates* for
> education, research, and clinician review. It does not practice medicine. A
> licensed professional must set, verify, and sign any plan used for real care.
> Treat every dose, threshold, and guideline reference here as a starting point to
> confirm against current primary sources — not as authoritative medical advice.

## When to Use This Skill

- Authoring an individualized treatment or care plan for a patient scenario.
- Documenting chronic-disease management (diabetes, hypertension, heart failure,
  COPD, CKD) with targets and monitoring schedules.
- Writing rehabilitation programs (PT/OT/SLP, post-stroke, orthopedic, cardiac).
- Drafting mental-health plans (psychotherapy + pharmacology + safety planning).
- Building perioperative pathways (pre-op optimization, ERAS, post-op milestones).
- Establishing multimodal pain-management protocols with opioid-safety documentation.
- Converting clinical goals into SMART, patient-centered objectives.
- Producing a professional PDF for a chart, teaching case, or research protocol.

## When NOT to Use This Skill

- **Real clinical decisions for a named patient** without a licensed clinician in
  the loop — this drafts documents, it does not diagnose or prescribe.
- **Live PHI** that has not been de-identified — de-identify first (see
  `references/regulatory_compliance.md`).
- **Encounter notes** (SOAP, H&P, progress notes, discharge summaries) — those are a
  different document class; use a clinical-notes skill.
- **A literature review or evidence synthesis** — use `literature-review` /
  `research-lookup`; a treatment plan cites sparingly, it does not survey them.
- **Formatting citations / building a bibliography** — use `citation-management`.
- **A conceptual diagram on its own** — use `scientific-schematics` directly.

## Workflow

1. **Identify the specialty and complexity.** Pick the matching playbook in
   `references/specialty_playbooks.md`; choose a document length (one-page,
   standard 3-4 page, or extended) per `references/formatting_and_qa.md`.
2. **Assess and de-identify.** Capture baseline status and disease severity; remove
   the 18 HIPAA identifiers (`references/regulatory_compliance.md`).
3. **Set SMART goals.** Short- and long-term, patient-centered, using the framework
   and condition-specific examples in `references/goal_setting.md`.
4. **Select interventions.** Pharmacological (with dose/route/frequency/rationale),
   non-pharmacological, and procedural — grounded in
   `references/interventions.md`. Add monitoring parameters and thresholds.
5. **Compose the document.** Lead with a scannable first-page summary; structure the
   body against `references/treatment_plan_standards.md`.
6. **Validate and render.** Run the completeness + quality checklist and compile to
   PDF per `references/formatting_and_qa.md`.

## Capability Map

Route to the reference that matches the sub-task:

- **What every plan must contain** — components, the Foundation-Medicine-style
  first-page summary, documentation standards, quality indicators, common
  deficiencies, and when to revise → `references/treatment_plan_standards.md`.
- **Writing the goals** — SMART criteria, ICF and clinical/functional/QoL goal
  levels, patient-reported outcomes, shared decision-making, condition-specific
  SMART examples, and goal-setting pitfalls → `references/goal_setting.md`.
- **Choosing interventions** — evidence grading, first/second-line drug classes by
  indication with dosing, lifestyle and behavioral interventions, procedural and
  interventional options, and a per-intervention documentation template →
  `references/interventions.md`.
- **Specialty specifics** — assessment tools, targets, and clinical pearls for the
  six plan types, plus concise-vs-verbose worked examples →
  `references/specialty_playbooks.md`.
- **Staying compliant** — HIPAA de-identification, 42 CFR Part 2, CMS/quality
  reporting, opioid-prescribing rules, and mental-health-specific law →
  `references/regulatory_compliance.md`.
- **Formatting, styling, and QA** — length options, colored-box LaTeX styling,
  first-page layout, PDF compilation, and the completeness/quality validation
  checklists → `references/formatting_and_qa.md`.

## Cross-Links to Sibling Skills

- `scientific-schematics` — generate an optional treatment-pathway flowchart, care-
  coordination diagram, or rehab milestone timeline to embed as a figure. Figures
  are helpful for complex plans but are not required.
- `citation-management` — format the handful of guideline references a plan needs.
- `literature-review` / `research-lookup` — confirm current best practice or
  guideline targets before committing them to a plan.
- `venue-templates` — if the plan is being written up for publication (case report,
  guideline), match journal medical-writing style there.

## Key Failure Modes to Avoid

- **Verbosity.** A wall of narrative prose is the most common defect. If a section
  does not change a decision, cut it. See the concise-vs-verbose examples in
  `references/specialty_playbooks.md`.
- **Vague goals.** "Improve mobility" is unmeasurable. Every goal needs a metric, a
  baseline, a target, and a timeframe.
- **Missing safety net.** Mental-health plans require an explicit safety plan and
  risk assessment; opioid plans require PDMP/UDS/naloxone documentation; every plan
  needs warning signs and emergency actions.
- **Un-de-identified PHI.** Never emit names, exact dates, MRNs, or addresses in a
  shared plan.
- **Over-citing.** A 3-4 page plan carries 0-3 citations, not a bibliography.
