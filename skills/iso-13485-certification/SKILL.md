---
name: iso-13485-certification
version: 0.1.0
description: >-
  Build and gap-analyze the Quality Management System (QMS) documentation required for
  ISO 13485:2016 certification of medical devices — the clause-by-clause requirements
  (Clauses 4-8), the mandatory documented procedures and records, Quality Manual
  authoring, Medical Device File (MDF) assembly, justified exclusions, and alignment
  with FDA QMSR and EU MDR. Use when preparing, auditing, or remediating medical-device
  QMS documentation: running a gap analysis over existing SOPs, drafting a Quality
  Manual or CAPA / complaint / internal-audit procedures, consolidating DHF/DMR/DHR into
  an MDF, or planning a certification path. Do NOT use to author the ISO 14971 risk
  management file itself, to draft FDA 510(k) or EU MDR clinical-evaluation submissions
  (use `clinical-reports`), to grant certification or legally sign off a QMS, or for
  non-medical-device quality systems such as ISO 9001.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# ISO 13485 Certification Documentation

## Overview

ISO 13485:2016 is the international standard for a medical-device Quality Management
System (QMS). Certification requires a coherent documentation set: a Quality Manual, a
defined list of documented procedures, a Medical Device File per device type/family, and
the records that prove the system operates. This skill helps you **assess what exists,
understand what the standard demands, author the missing documents, and reach audit
readiness** — writing in your organization's own voice, not copying the standard.

The four reference files below carry the depth; this page routes you to them.

- `references/requirements-by-clause.md` — plain-language breakdown of Clauses 4-8.
- `references/mandatory-documents.md` — the documented procedures, records, and the
  documentation matrix (mandatory vs. conditional).
- `references/gap-analysis.md` — status scheme, clause→keyword map, an automated scan,
  and the prioritization/summary structure.
- `references/quality-manual-guide.md` — Quality Manual structure, tiered documentation,
  exclusions, and a completeness checklist.

## When to Use This Skill

- Starting an ISO 13485 program from scratch and needing a build order.
- Running a **gap analysis** of existing QMS documents to find what is missing or weak.
- Authoring a Quality Manual, or procedures such as CAPA, complaint handling, internal
  audit, document/record control, management review.
- Assembling or restructuring a **Medical Device File** (including consolidating separate
  DHF/DMR/DHR after FDA QMSR harmonization).
- Preparing for a certification or surveillance audit (readiness review, mock audit).
- Updating documentation for a regulatory shift (FDA QMSR, EU MDR/IVDR).

## When NOT to Use This Skill

- **Authoring the risk management file** to ISO 14971 — this skill references risk
  management as a QMS input but does not perform hazard analysis or risk evaluation.
- **Clinical/regulatory submissions** — 510(k), De Novo, PMA, EU MDR technical
  documentation, or clinical-evaluation reports. Those are separate deliverables; for
  clinical evidence documents use `clinical-reports`.
- **Granting certification or legal sign-off** — only an accredited notified/certifying
  body issues certification; this skill produces the documentation you present to them.
- **Non-medical-device quality systems** — ISO 9001, ISO/IEC 17025, GxP-only programs.
- **Design/engineering of the device itself** — this governs the QMS, not the product.

## The QMS Documentation Model

ISO 13485 documentation is conventionally tiered. Keep each tier at its own altitude:

| Tier | Document type | Answers | Stability |
|------|---------------|---------|-----------|
| 1 | Quality Manual | scope, policy, structure | Rarely changes |
| 2 | Procedures (SOPs) | WHAT, WHO, WHEN | Changes with process |
| 3 | Work Instructions | HOW (step-by-step) | Changes frequently |
| 4 | Records & Forms | evidence it happened | Continuous |

The most common authoring mistake is pushing Tier-3 "how-to" detail up into the Quality
Manual or procedures. See `references/quality-manual-guide.md` for the altitude rule with
worked good/bad examples.

## Workflow

Pick the entry point that matches the request; steps are independent.

### 1. Gap analysis (existing documentation)

Assess coverage before writing anything new. Score each requirement **Compliant /
Partial / Non-compliant / N/A (justified)**. An automated first pass keyword-scans the
document set against the clause→procedure map to flag which of the required procedures and
key documents are present; then do a manual deep pass on quality, not just presence.
Full method, the keyword map, and a runnable scan script are in
`references/gap-analysis.md`. Output: a scored checklist plus a prioritized action plan.

### 2. Understand a requirement

For any clause question, read the relevant section of
`references/requirements-by-clause.md` and explain it in plain language with a concrete
example. To know whether a document is mandatory, conditional, or excludable, consult the
documentation matrix in `references/mandatory-documents.md`.

### 3. Author documents (in priority order)

Build foundation first, then core processes, then product realization and support. A
sensible order:

1. **Foundation** — Quality Manual, Quality Policy & Objectives, Control of Documents,
   Control of Records.
2. **Core processes** — CAPA (8.5.2/8.5.3), Complaint Handling, Internal Audit,
   Management Review, Risk Management interface.
3. **Product realization** — Design & Development (if applicable), Purchasing, Production
   & Service Provision, Control of Nonconforming Product.
4. **Supporting** — Competence/Training, Calibration (control of M&M equipment), Process
   Validation, Identification & Traceability.
5. **Post-market & conditional** — Feedback, Regulatory Reporting, Installation,
   Servicing, Sterilization, Contamination Control.

Each document needs the standard skeleton — Purpose, Scope, Definitions,
Responsibilities (by role, not name), Procedure, Records, References — and must name the
records it produces. Write in your own words; describe **your** process, never paste the
standard. For the Quality Manual specifically, follow `references/quality-manual-guide.md`.

### 4. Assemble the Medical Device File

Create one MDF per device type or family. Under FDA QMSR (effective 2 Feb 2026) the MDF
replaces the separate DHF, DMR, and DHR. Required contents per Clause 4.2.3 (device
description and intended use, label/IFU specs, product and manufacturing specs, the
purchasing/manufacturing/servicing and measuring/monitoring procedures, installation
requirements if applicable, the risk management file, verification & validation info, and
the design & development file when applicable) are detailed in
`references/mandatory-documents.md`.

### 5. Audit readiness

Re-run the gap-analysis checklist as a readiness review, verify records actually exist for
every required item, run a mock audit against the clause requirements, and close findings
before the certification audit. The readiness checklist lives in
`references/gap-analysis.md`.

## Boundaries and Common Pitfalls

- **The "31 procedures" is a convention, not a file count.** Procedures may be combined
  (e.g. CAPA merges 8.5.2 + 8.5.3; document + record control merge 4.2.4 + 4.2.5) or
  split. Several are conditional ("when applicable"), so the literal list runs to ~33.
- **Exclusions must be justified in the Quality Manual.** Only genuinely inapplicable
  activities may be excluded (typically Design & Development for pure contract
  manufacturers, Installation, Servicing, Sterilization). "We don't do design" is not a
  justification; explain *why* and show no impact on safe, effective devices.
- **Records ≠ procedures.** Every procedure must specify the records it generates and
  their retention. Missing records is the most common audit finding after missing
  procedures.
- **Retention** is at least the lifetime of the device as the organization defines it,
  and never shorter than any applicable regulatory minimum (often 5-10 years).
- **Regulatory layering.** ISO 13485 is the floor; FDA QMSR, EU MDR/IVDR, and Health
  Canada may each demand more. Confirm the target market(s) before declaring scope.
- **Do not assert compliance you cannot evidence.** Presence of a document is not
  conformity — the gap analysis must judge adequacy and implementation.

## References

- [Requirements by clause](references/requirements-by-clause.md)
- [Mandatory documents & records](references/mandatory-documents.md)
- [Gap analysis method & scan](references/gap-analysis.md)
- [Quality Manual guide](references/quality-manual-guide.md)
