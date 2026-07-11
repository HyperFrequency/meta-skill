# Clinical Decision Algorithms and TikZ Flowcharts

Depth reference for `clinical-decision-support`. Covers algorithm design, encoding a
pathway as a TikZ flowchart, common risk scores, and validation.

## 1. Design principles

An algorithm is a directed graph of three node kinds:
- **Decision node** — a measurable criterion (lab value, imaging finding, biomarker
  cut-point). Prefer binary yes/no; use multi-way only when branches are mutually
  exclusive.
- **Action node** — a specific intervention (drug + dose), test, referral, or timed
  observation.
- **Terminal node** — outcome, follow-up schedule, or exit criterion.

Design constraints that keep an algorithm usable:
- **Clarity**: unambiguous criteria, mutually exclusive paths, one entry point, no
  unintended loops.
- **Cognitive load**: ≤7 decision points per pathway; highlight the most common route.
- **Completeness**: a default branch for edge cases and an explicit escalation/safety-net
  path; state entry and exit conditions.
- **Validity**: evidence-based criteria and validated cut-points; mark expert-consensus
  steps where evidence is thin.

## 2. Worked pathway shape

Treatment-selection algorithms generally follow: confirm eligibility → check biomarker
testing complete → branch on actionable alteration → branch on the relevant expression
marker → select regimen by histology → define monitoring/response cadence. Diagnostic
algorithms follow: compute a validated risk score → risk-stratify → order the
next test conditional on the stratum → act on the result. Keep dosing and thresholds
explicit at each node so the pathway is executable, not aspirational.

## 3. TikZ encoding

Encode decision flowcharts as TikZ (not raster images) so they stay editable in the LaTeX
source and print crisply. Baseline styles and a minimal graph:

```latex
\usepackage{tikz}
\usetikzlibrary{shapes, arrows, positioning}

\tikzstyle{decision} = [diamond, draw, fill=yellow!20, text width=4em,
  text centered, inner sep=2pt, font=\small]
\tikzstyle{process}  = [rectangle, draw, fill=blue!20, text width=6em,
  text centered, rounded corners, minimum height=2.5em, font=\small]
\tikzstyle{terminal} = [rectangle, draw, fill=green!20, text width=6em,
  text centered, rounded corners=8pt, minimum height=2.5em, font=\small]
\tikzstyle{alert}    = [rectangle, draw=red, line width=1.5pt, fill=red!10,
  text width=6em, text centered, rounded corners, minimum height=2.5em,
  font=\small\bfseries]
\tikzstyle{arrow}    = [thick, ->, >=stealth]

\begin{tikzpicture}[node distance=2cm, auto]
  \node [terminal] (start) {Advanced NSCLC, ECOG 0-2};
  \node [decision, below of=start] (bm) {Actionable alteration?};
  \node [process, below of=bm, node distance=2.5cm] (tki) {Matched targeted therapy};
  \node [decision, right of=bm, node distance=4cm] (pdl1) {PD-L1 $\geq$50\%?};
  \node [terminal, below of=pdl1, node distance=2.5cm] (io) {IO $\pm$ chemo};

  \draw [arrow] (start) -- (bm);
  \draw [arrow] (bm) -- node {Yes} (tki);
  \draw [arrow] (bm) -- node {No} (pdl1);
  \draw [arrow] (pdl1) -- (io);
\end{tikzpicture}
```

**Color coding by urgency**: red = life-threatening/immediate, orange = urgent (hours),
yellow = semi-urgent (24-48 h), green = routine/stable, blue = informational. Emphasize
the common pathway with bold arrows; use dashed arrows for rare branches.

For hand-drawn-style conceptual figures (mechanism diagrams, biology pathways) rather than
editable decision trees, delegate to the `scientific-schematics` skill instead of TikZ.

## 4. Common risk scores

Reproduce validated scores exactly; they are entry criteria for many algorithms.
- **TIMI** (NSTEMI/UA, 0-7): age ≥65, ≥3 CAD risk factors, known CAD, ASA in 7 days,
  ≥2 anginal episodes/24 h, ST deviation ≥0.5 mm, elevated biomarkers.
- **CHA2DS2-VASc** (AF stroke risk): CHF, HTN, age ≥75 (2), diabetes, prior stroke/TIA
  (2), vascular disease, age 65-74, female. Anticoagulate at ≥2 (male)/≥3 (female).
  Pair with **HAS-BLED** for bleeding risk.
- **Wells** (PE): DVT signs (3), PE most likely (3), HR >100 (1.5), recent
  immobilization/surgery (1.5), prior PE/DVT (1.5), hemoptysis (1), malignancy (1) →
  D-dimer if ≤4, CTPA if >4.
- **MELD** (liver): `3.78·ln(bilirubin) + 11.2·ln(INR) + 9.57·ln(creatinine) + 6.43`.
- **Genomic recurrence assays**: Oncotype DX / MammaPrint for breast-cancer adjuvant
  chemo decisions.

## 5. Validation and maintenance

**Development**: guideline + meta-analysis review → multidisciplinary draft → retrospective
pilot on 20-50 historical cases → prospective validation tracking adherence (target >80%)
and outcomes vs historical controls → continuous review.

**Metrics**: adherence rate, time-to-decision, completion rate (process); guideline
concordance, mortality/morbidity/readmission, resource use (outcome); ease-of-use and
perceived utility (user).

**Update triggers**: FDA approval or NCCN/ASCO/ESMO Category-1 change (mandatory within
3 months), safety alert/black-box (fast), drug shortage or recall (emergency, within a
week). Keep a version + change-log with effective dates, evidence cited, and reviewer.
