# CDS Document Format: Structure, LaTeX, and Compliance

Depth reference for `clinical-decision-support`. Covers the mandatory page-1 executive
summary, LaTeX/`tcolorbox` layout, output specification, and regulatory compliance.

## 1. Page-1 executive summary (mandatory)

Every CDS document opens with a **full-page executive summary** — no table of contents or
detailed prose on page 1. It must be scannable in ~60 seconds. Include:

1. **Title + subtitle**: deliverable type and disease state.
2. **Report information box**: document type, disease state, analysis date, population,
   methodology/framework.
3. **3-5 key-finding boxes**, color-coded for hierarchy:
   - blue = primary efficacy/outcome results,
   - green = biomarker/subtype insights (or, for recommendation reports, the top
     GRADE-graded recommendations),
   - orange/yellow = clinical implications / critical monitoring,
   - gray = statistical summary (HRs, p-values),
   - red = safety highlights (if applicable).

Use bullet points, not paragraphs. Suppress the page number (`\thispagestyle{empty}`) and
end with `\newpage`.

```latex
\maketitle
\thispagestyle{empty}

\begin{tcolorbox}[colback=blue!5!white, colframe=blue!75!black, title=Report Information]
\textbf{Document Type:} Patient Cohort Analysis\\
\textbf{Disease State:} HER2-Positive Metastatic Breast Cancer\\
\textbf{Analysis Date:} \today\\
\textbf{Population:} 60 patients, stratified by hormone-receptor status
\end{tcolorbox}

\vspace{0.3cm}

\begin{tcolorbox}[colback=blue!5!white, colframe=blue!75!black, title=Primary Efficacy]
\begin{itemize}
  \item Overall ORR: 72\% (95\% CI 59-83)
  \item Median PFS: 18.5 months (95\% CI 14.2-22.8)
  \item Median OS: 35.2 months (95\% CI 28.1-NR)
\end{itemize}
\end{tcolorbox}

% ...green biomarker box, orange implications box...

\newpage
\tableofcontents   % page 2 (optional)
\newpage           % detailed content starts page 3
```

## 2. Body sections by deliverable

**Patient cohort analysis** (page 3+): cohort characteristics and selection criteria →
biomarker stratification → treatment exposure by subgroup → outcome analysis (response +
survival) → statistical methods → subgroup comparisons (forest plots) → safety profile →
clinical implications → figures and tables.

**Treatment recommendation report** (page 3+): clinical context/epidemiology → target
population and biomarker criteria → evidence review (systematic synthesis, trial data) →
treatment options with mechanism → GRADE assessment per recommendation → recommendations
by line of therapy → biomarker-guided selection → TikZ decision algorithm → monitoring
protocol → special populations → full references with trial names.

## 3. Output specification

- **Format**: LaTeX → PDF, ~0.5in margins for a compact, data-dense presentation.
- **Length**: typically 5-15 pages (1-page executive summary + 4-14 pages detail).
- **Consistent color semantics**: blue = data/information, green = biomarkers/strong
  recommendation, yellow/orange = conditional/implications, red = warnings.
- **Tables**: demographics (Table 1), biomarker frequency, outcomes (ORR/PFS/OS/DOR by
  subtype), adverse events, GRADE evidence summaries.
- **Figures**: Kaplan-Meier curves with number-at-risk, waterfall, forest, swimmer plots,
  and TikZ algorithm flowcharts (see [cohort-analysis.md](cohort-analysis.md) and
  [decision-algorithms.md](decision-algorithms.md)).

## 4. Compliance

- **De-identification**: remove all 18 HIPAA Safe Harbor identifiers before rendering.
  Never emit names, MRNs, exact dates of birth, or geographic detail below state level.
- **Confidentiality**: add a confidentiality/proprietary notice header for pharmaceutical
  data intended for internal or regulatory use.
- **Regulatory alignment**: ICH-GCP framing for trial-derived data; state the reporting
  standard followed (CONSORT/STROBE/REMARK/TRIPOD).
- **Conflict of interest**: disclose pharmaceutical funding or relationships where
  applicable.
- **Reproducibility**: document every statistical method (tests, models, cut-points,
  software) so a reviewer can replicate the analysis.

## 5. Sibling skills

- `scientific-schematics` — AI-generated conceptual diagrams and mechanism figures.
- `scientific-writing` / `venue-templates` — manuscript prose, structured abstracts,
  medical-journal styling (CONSORT/STROBE).
- `statistical-analysis` / `statsmodels` — heavier statistical modeling when it exceeds
  the survival/group-comparison core here.
- `citation-management` / `literature-review` — reference handling and trial-evidence
  gathering that feeds the evidence sections.
- `treatment-plans` — the individual-patient counterpart; this skill produces the
  group-level analyses those bedside plans draw on.
