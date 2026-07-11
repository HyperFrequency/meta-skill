# Formatting, Styling, and QA

How long the document should be, how to style a clean clinical PDF, how to render it,
and the checklists to validate it before sign-off.

## Choose a length

Default to the shortest format that carries the content.

- **One page (preferred for most cases).** A quick-reference card, akin to a
  precision-oncology recommendation: header box (patient/diagnosis/date/risk
  profile), primary regimen (numbered), supportive care, brief rationale, monitoring,
  evidence level, expected outcome. No table of contents, no narrative. Maximize
  information density; use clinician-familiar abbreviations.
- **Standard 3-4 pages.** First-page summary (see below) plus 2-3 pages of detail.
  Use when there is patient-education material or multidisciplinary coordination.
- **Extended 5-6 pages (rare).** Only for complex comorbidities, research protocols,
  or extensive safety monitoring. Even here, cut anything that does not change a
  decision.

## First-page summary layout

The whole first page is an executive summary; detail starts on page 2+.

1. Title + subtitle (plan type; specific condition/patient descriptor).
2. Report/patient info box (de-identified demographics, ICD-10 diagnosis, date).
3. 2-4 key-findings boxes: Primary Goals, Core Interventions, Critical Decision
   Points/safety, Timeline overview.

Remove page numbers from page 1 (`\thispagestyle{empty}`); everything fits before
`\newpage`; a table of contents (if any) starts on page 2, detail on page 3.

## LaTeX styling approach (colored boxes)

A clean clinical look comes from a small set of color-coded boxes built on the
`tcolorbox` package (`[most]` library) with `xcolor`. Define a palette once — a
primary blue for headers/section titles, a green for goals, red/yellow for warnings,
grays for body/background — then reuse box environments so meaning stays consistent:

- **Info box** (blue border, light background) — assessments, monitoring schedules,
  titration protocols.
- **Goal box** (green) — SMART goals, targets, success criteria.
- **Warning box** (red/yellow) — critical decision points, drug-safety alerts,
  contraindications, emergency thresholds.
- **Key-points box** (blue fill) — executive summary, priority recommendations.
- **Emergency box** (bold red) — emergency contacts and hotlines.
- **Patient-info box** (white, blue border) — a small demographics table.

For tables, use blue header rows with white text and alternating light-gray body rows
(`colortbl`/`booktabs`) for scannability. Typical preamble packages: `geometry`,
`xcolor`, `tcolorbox[most]`, `tikz`, `fancyhdr`, `titlesec`, `enumitem`, `booktabs`,
`longtable`, `array`, `colortbl`, `hyperref`. Prefer XeLaTeX/LuaLaTeX with `fontspec`
for font control. Package these definitions into a reusable `.sty` if you author many
plans.

**Styling discipline:** match box color to meaning (goals green, warnings red);
reserve boxes for genuinely important content; keep sufficient contrast and test in
grayscale for print/accessibility; leave white space between sections.

## Rendering to PDF

XeLaTeX (best font support):

```bash
xelatex plan.tex
bibtex plan        # only if the plan has citations
xelatex plan.tex
xelatex plan.tex
```

PDFLaTeX works as an alternative (replace `xelatex` with `pdflatex`). Common issues:
missing packages → install via `tlmgr` (`tcolorbox tikz pgf`); missing glyphs (✓, ≥)
→ use XeLaTeX or math commands (`$\checkmark$`, `$\geq$`) with `amssymb`;
box-not-rendering → ensure the full `tcolorbox`/`tikz`/`pgf` install.

## Optional pathway figure

Complex plans benefit from one diagram — a treatment-pathway flowchart, care-
coordination diagram, medication-management flow, or rehabilitation milestone
timeline. Generate it with the `scientific-schematics` sibling skill (describe the
diagram in natural language) and embed the image. This is optional, not required —
add it only when a visual genuinely aids comprehension.

## Completeness checklist

Confirm every applicable section is present:

- [ ] Patient information (de-identified)
- [ ] Diagnosis and assessment (ICD-10, severity)
- [ ] SMART goals — short-term and long-term
- [ ] Interventions — pharmacological, non-pharmacological, procedural
- [ ] Timeline and schedule
- [ ] Monitoring parameters (with frequency and thresholds)
- [ ] Expected outcomes
- [ ] Follow-up plan
- [ ] Patient education
- [ ] Risk mitigation and safety

## Quality checklist

**Clinical:** diagnosis accurate and coded; goals SMART and patient-centered;
interventions evidence-based and guideline-concordant; timeline realistic; monitoring
comprehensive; safety addressed.

**Patient-centered:** preferences and values incorporated; shared decision-making
documented; health-literacy-appropriate language; cultural considerations; education
plan included.

**Regulatory:** HIPAA de-identification; medical necessity documented; informed
consent noted; provider signature and credentials; date of creation/revision.

**Coordination:** specialist referrals documented; care-team roles defined; follow-up
schedule clear; emergency contacts provided; transition planning addressed.

**Specialty-specific quality signals to verify are actually present:**

- SMART goals literally satisfy all five criteria (specific metric, baseline→target,
  realistic, patient-relevant, timeframe).
- Evidence/guideline references appear where a recommendation is novel or high-stakes
  (0-3 citations for a short plan — no bibliography).
- Mental-health plans include a safety plan and risk assessment; opioid plans include
  PDMP/UDS/naloxone and functional goals.
- Timeline is feasible given expected treatment effect sizes.
