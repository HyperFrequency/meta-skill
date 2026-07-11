---
name: peer-review
version: 0.1.0
description: Structured manuscript/grant review with checklist-based evaluation. Use when writing formal peer reviews with specific criteria — methodology assessment, statistical validity, reporting standards compliance (CONSORT/STROBE/PRISMA), and constructive feedback. Best for actual review writing and manuscript revision. NOT for general evidence/claim quality judgement (use scientific-critical-thinking) or quantitative scoring frameworks (use scholar-evaluation); for authoring slide decks rather than reviewing them use scientific-slides.
allowed-tools: Read Write Edit Bash
license: MIT license
metadata:
    skill-author: K-Dense Inc.
---

# Scientific Critical Evaluation and Peer Review

## Overview

Peer review is a systematic process for evaluating scientific manuscripts and
grants: assess methodology, statistics, design, reproducibility, ethics, and
reporting standards, then deliver constructive, rigorous, actionable feedback.

This SKILL.md is a router. The full section-by-section criteria, rigor checks,
and report structure live in `references/review_workflow.md` — load it when
conducting an actual review.

## When to Use This Skill

- Peer review of scientific manuscripts for journals
- Evaluating grant proposals and research applications
- Assessing methodology, experimental design, and statistical rigor
- Evaluating reproducibility, data/code availability, and ethics
- Checking compliance with reporting guidelines (CONSORT, STROBE, PRISMA, ARRIVE)
- Providing constructive feedback on scientific writing or slide decks

**When NOT to use:** for judging the quality of a single claim or body of
evidence in the abstract, use `scientific-critical-thinking`; for numeric
scoring/ranking frameworks, use `scholar-evaluation`; for *authoring* (not
reviewing) manuscripts or slides, use `scientific-writing` / `scientific-slides`.

## Review Workflow (Stage Outline)

Work through these stages, adapting depth to manuscript type and discipline.
Each stage's detailed checklist is in `references/review_workflow.md`.

1. **Initial Assessment** — scope, novelty, soundness; produce a 2-3 sentence summary.
2. **Section-by-Section Review** — abstract/title, introduction, methods, results, discussion, references.
3. **Methodological & Statistical Rigor** — assumptions, effect sizes, multiple-testing correction, power, controls, computational reproducibility.
4. **Reproducibility & Transparency** — data deposition, code availability, reporting-standard compliance (`references/reporting_standards.md`).
5. **Figure & Data Presentation** — quality, integrity (image manipulation), standalone clarity; run the table/figure/notation/structure audit in `references/paper_mechanics.md`.
6. **Ethical Considerations** — human/animal approvals, consent, conflicts, research integrity.
7. **Writing Quality & Clarity** — organization, language, accessibility.

## Report Structure

Organize feedback hierarchically (full templates in `references/review_workflow.md`):

- **Summary Statement** — synopsis, overall recommendation (accept / minor / major / reject), key strengths and weaknesses.
- **Major Comments** — numbered, critical issues; state issue, why it matters, suggested fix, whether essential for publication.
- **Minor Comments** — numbered, clarity/completeness issues with location and fix.
- **Line-by-Line Comments** (optional) and **Questions for Authors**.

Maintain a constructive, specific, balanced, respectful, objective tone. Avoid
personal attacks, vague criticism, and out-of-scope experiment demands. See
`references/review_workflow.md` for tone guidance and per-manuscript-type notes
(original articles, reviews/meta-analyses, methods papers, short reports,
preprints, presentations).

## Reviewing Presentations

Slide decks (PowerPoint, Beamer) need an image-based workflow — **never read the
presentation PDF as text** (it overflows and hides visual formatting issues).
See `references/presentation_review.md` for the conversion workflow, slide-level
checklists, and the presentation report format.

## Resources

- **`references/review_workflow.md`** — full stage checklists, rigor criteria, report templates, tone, and per-type guidance.
- **`references/reporting_standards.md`** — major reporting standards (CONSORT, PRISMA, ARRIVE, MIAME, STROBE, etc.).
- **`references/common_issues.md`** — catalog of frequent methodological/statistical issues and how to address them.
- **`references/presentation_review.md`** — image-based workflow and checklists for reviewing slide decks.
- **`references/paper_mechanics.md`** — table/figure/notation/structure pass-fail audit for presentation mechanics.

## Final Checklist

Before finalizing the review, verify:

- [ ] Summary statement clearly conveys overall assessment
- [ ] Major concerns are clearly identified and justified
- [ ] Suggested revisions are specific and actionable
- [ ] Minor issues are noted and properly categorized
- [ ] Statistical methods have been evaluated
- [ ] Reproducibility and data availability assessed
- [ ] Ethical considerations verified
- [ ] Figures and tables evaluated for quality and integrity
- [ ] Writing quality assessed
- [ ] Tone is constructive and professional throughout
- [ ] Review is thorough but proportionate to manuscript scope
- [ ] Recommendation is consistent with identified issues
