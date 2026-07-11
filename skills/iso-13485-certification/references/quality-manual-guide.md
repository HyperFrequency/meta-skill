# Quality Manual Development Guide

The Quality Manual is the Tier-1, policy-level document of the QMS (Clause 4.2.2). It
defines scope, states the quality policy, references every procedure, and describes how
processes interact and how the documentation is structured. It is typically 20-50 pages
and changes rarely, while procedures and work instructions change more often.

## Required content (Clause 4.2.2)

The manual **must** contain, at minimum:

a) **Scope** of the QMS — organizational units, sites, activities, and product types
   covered — with any exclusions and their justification.
b) **Documented procedures** or references to them.
c) A **description of the interaction** between QMS processes (usually a process map).
d) The **structure of the documentation** used in the QMS (the tier model).

## Recommended structure

```
0  Document control          approvals, revision history, distribution
1  Introduction              company overview, purpose, definitions
2  Scope and exclusions      scope, products, applicable regulations, justified exclusions (4.2.2.a)
3  Quality policy & objectives  signed policy (5.3), measurable objectives (5.4)
4  Quality management system  processes & interactions, risk mgmt, software validation, doc/record control
5  Management responsibility  commitment, customer focus, roles, mgmt representative, review
6  Resource management       resources, HR/competence, infrastructure, work environment
7  Product realization       planning, customer processes, D&D, purchasing, production, M&M equipment
8  Measurement & improvement feedback, complaints, audits, nonconformity, data analysis, CAPA
9  Appendices                A procedures list · B org chart · C process map · D definitions · E regulations
```

Appendix A (the procedure list, 4.2.2.b), Appendix C (the process map, 4.2.2.c), and the
Section 4 documentation-structure description (4.2.2.d) are how you satisfy the manual's
own mandatory content — do not omit them.

## The altitude rule

Keep the manual at **policy level**. State WHAT the organization does and WHY, name WHO is
responsible, and point to WHERE the detail lives. Do not put step-by-step HOW-TO, forms,
or heavy technical detail in the manual — that belongs in Tier-2 procedures and Tier-3 work
instructions.

**Good (policy level):**
> "The organization maintains a documented procedure for control of nonconforming product
> that ensures such product is identified, segregated, and dispositioned. The Quality
> Manager reviews all nonconformances and determines corrective action. Refer to
> SOP-8.3-01, Control of Nonconforming Product."

**Too detailed (belongs in a procedure/work instruction):**
> "The inspector fills out Form NCR-001, applies a red tag, and moves the product to the
> quarantine area in Building B, Row 5. Within 24 hours the Quality Manager checks one of
> Rework / Scrap / Use-As-Is..."

For Sections 5-8, use one repeatable pattern per clause: **state the requirement →
describe how you meet it → reference the procedure(s) → name the responsible role.**

## The tiered documentation structure

Describe this hierarchy in Section 4 to satisfy 4.2.2.d:

- **Tier 1 — Quality Manual**: policy; defines scope and structure; references procedures.
- **Tier 2 — Procedures (SOPs)**: WHAT/WHO/WHEN for multi-functional activities; the
  required documented procedures.
- **Tier 3 — Work Instructions**: HOW; step-by-step, task/department specific.
- **Tier 4 — Records & Forms**: evidence of conformity; retained per requirements.

## Exclusions

Only genuinely inapplicable activities may be excluded, and each exclusion must be
justified in Section 2.4. You may **not** exclude a process you actually perform, and no
exclusion may affect your ability or responsibility to supply safe, effective devices.

Common defensible exclusions:

- **Design & Development (7.3)** — pure contract manufacturers building to a customer's
  complete design.
- **Installation (7.5.3)** — devices supplied ready to use.
- **Servicing (7.5.4)** — no servicing offered / single-use devices.
- **Sterilization (7.5.7)** — non-sterile product.

A strong justification explains *why* the activity does not apply and shows there is no
impact on device safety/effectiveness. "We don't do design" is not sufficient — state that
all design is performed by the customer and the organization holds no responsibility for
design inputs, outputs, verification, validation, or changes.

## Quality policy essentials (Section 3)

The policy must be appropriate to the organization, commit to meeting requirements and
maintaining QMS effectiveness, frame the quality objectives, be communicated and
understood, and be **signed by top management**. Make it specific to your organization and
products — a policy that could belong to any company is a finding. Pair it with
**measurable** objectives (e.g. on-time delivery ≥ 95%, CAPA closed within 60 days ≥ 90%,
defect rate < 0.5%), reviewed on a defined cadence.

## Development process

1. **Prepare** — gather the standard and applicable regulations, review existing docs,
   assign clause owners, decide exclusions.
2. **Draft** — Sections 0-3 (admin + policy) first, then 4-8 using the per-clause pattern,
   then appendices. Hold the policy altitude.
3. **Review & approve** — technical review by the Quality Manager, management review by top
   management, legal review if needed, resolve comments, final sign-off.
4. **Implement** — communicate and train, make controlled copies available, control
   distribution.
5. **Maintain** — review at least annually, update on significant change, keep revision
   history, retire superseded copies.

## Common mistakes

1. Too much operational detail → keep at policy level.
2. Copy-pasting ISO 13485 text → write your own words about **your** QMS.
3. Broken references → maintain a master procedure list; verify every reference exists.
4. Unjustified exclusions → justify against actual business activities.
5. No process map → add a clear map in Appendix C.
6. Generic quality policy → make it specific and signed.
7. Missing Appendix A → include the complete procedure list.
8. No management signatures / no revision control → enforce document control (4.2.4).

## Completeness checklist

Required content (4.2.2):
- [ ] Scope defined; exclusions identified and justified.
- [ ] Documented procedures listed or referenced (Appendix A).
- [ ] Process interactions described (Appendix C).
- [ ] Documentation structure outlined (Section 4 / tier model).

Approval & completeness:
- [ ] Approved and signed by top management, with date and document-control info.
- [ ] All Clauses 4-8 addressed; responsibilities assigned per clause.
- [ ] Quality policy included and signed; objectives measurable.
- [ ] Every referenced procedure exists with the correct number/title.

Appendices: [ ] A procedures · [ ] B org chart · [ ] C process map · [ ] D definitions ·
[ ] E regulatory requirements.

## After approval

Train staff on the manual, then develop/refresh the documented procedures, create work
instructions, implement the processes, run internal audits, hold a management review, and
schedule the certification audit when readiness (see `gap-analysis.md`) is confirmed.
