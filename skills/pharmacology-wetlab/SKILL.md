---
name: pharmacology-wetlab
version: 0.1.0
description: >-
  Computational reduction of pharmacology wet-lab and preclinical data in Python
  (scipy/numpy/pandas/OpenCV): dose-response IC50/EC50 fitting (4PL, confidence
  intervals, Hill slope, selectivity, Chou-Talalay synergy); western-blot
  densitometry from gel images (background subtraction, loading-control fold
  change); xenograft
  tumor-growth-inhibition (TGI%) with growth kinetics and endpoint statistics;
  Arrhenius shelf-life prediction from accelerated stability data;
  radiolabeled-antibody biodistribution (%ID/g, PK clearance, tumor:blood) and
  MIRD absorbed-dose estimation; and CTCAE adverse-event grading with
  dose-limiting-toxicity assessment. Use when turning bench or in-vivo assay
  tables/images into quantitative pharmacological parameters. NOT for
  drug/target database lookups (use database-lookup), docking or structure
  prediction, cheminformatics descriptors (use rdkit), Kaplan-Meier survival
  (use lifelines), or single-cell/omics — this is preclinical assay reduction,
  not cheminformatics or trial biostatistics.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "scipy, numpy, pandas, scikit-image: BSD-3-Clause; matplotlib: PSF-based (Matplotlib license); OpenCV: Apache-2.0"
---

# Pharmacology Wet-Lab Analysis

## Overview

Turn raw output from pharmacology experiments into quantitative, reportable
parameters. This skill is a **router**: each capability below gives a minimal
entry point, then links to a `references/` file holding the reference
implementation, exact input schema, parameter choices, and failure modes.

Every capability works on plain tables (pandas DataFrames / CSVs) or grayscale
images, and depends only on the scientific-Python stack — no proprietary
instrument SDKs. The capabilities are grouped into five references:

| Capability | Reference |
| --- | --- |
| Dose-response IC50/EC50, Hill, selectivity, combination index | `references/dose-response.md` |
| Western-blot densitometry and fold change | `references/western-blot.md` |
| Xenograft TGI%, growth kinetics, endpoint stats | `references/xenograft-tgi.md` |
| Arrhenius stability and shelf-life prediction | `references/stability.md` |
| Biodistribution (%ID/g, PK) and MIRD dosimetry | `references/radiopharmacology.md` |
| CTCAE adverse-event grading and DLT | `references/adverse-events.md` |

## When to Use This Skill

- Fitting concentration-response data to obtain IC50/EC50, Hill slope, and 95% CI.
- Ranking compound potency or computing a selectivity/therapeutic index.
- Scoring drug synergy with the Chou-Talalay combination index.
- Quantifying protein bands from a western-blot image and normalizing to a loading control.
- Computing tumor growth inhibition (TGI%) and growth kinetics from xenograft caliper data.
- Predicting drug-product shelf life from accelerated (multi-temperature) stability studies.
- Reducing radiolabeled-antibody tissue counts to %ID/g, clearance half-lives, and tumor:blood ratios.
- Estimating absorbed organ dose with the MIRD formalism.
- Grading lab-value adverse events against CTCAE and flagging dose-limiting toxicities.

## When NOT to Use This Skill

- **Drug / target / trial database queries** — use `database-lookup`.
- **Cheminformatics** (descriptors, fingerprints, SMILES handling, docking, structure prediction) — use `rdkit`; this skill never parses chemistry.
- **Kaplan-Meier / Cox survival analysis** — use the `lifelines` library directly; TGI here is growth-based, not time-to-event.
- **General image segmentation or whole-slide IHC** — use `bioimage-analysis` or `histolab`; the western-blot tools here assume a simple lane/band gel layout.
- **Plate immunoassays** (ELISA, Luminex, titers) — use `immunology-assays`.
- **Formal clinical-trial biostatistics** (mixed models, group-sequential designs) — use `statistical-analysis` / `statsmodels`. CTCAE grading here is per-observation, not a trial safety analysis.

## Setup

```bash
uv pip install numpy scipy pandas matplotlib opencv-python scikit-image
```

`opencv-python` and `scikit-image` are only needed for western-blot image work;
everything else runs on numpy/scipy/pandas/matplotlib.

## Capabilities

### Dose-response and drug combinations

Fit a 4-parameter logistic (4PL) in **log-concentration space** (numerically
stabler than linear-space fitting), then read off IC50/EC50, Hill slope, and a
delta-method 95% CI. Extends to multi-compound selectivity indices and the
Chou-Talalay combination index for synergy.

```python
import numpy as np
from scipy.optimize import curve_fit

def four_pl(log_conc, bottom, top, log_ec50, hill):
    return bottom + (top - bottom) / (1 + 10 ** ((log_ec50 - log_conc) * hill))

conc = np.array([1e-3, 1e-2, 1e-1, 1, 10, 100])      # uM
resp = np.array([98, 95, 82, 45, 12, 3])             # % viability
popt, pcov = curve_fit(four_pl, np.log10(conc), resp,
                       p0=[resp.min(), resp.max(), np.median(np.log10(conc)), -1],
                       maxfev=20000)
print(f"IC50 = {10 ** popt[2]:.3g} uM, Hill = {popt[3]:.2f}")
```

Confidence intervals, selectivity index, and combination index: see
`references/dose-response.md`.

### Western-blot densitometry

Load the blot as grayscale, invert if bands are dark-on-light, split into lanes,
subtract a rolling-ball background, integrate band density, and normalize to a
loading control (β-actin / GAPDH / total protein) to report fold change.
Reference implementation, saturation caveats, and normalization guidance:
`references/western-blot.md`.

### Xenograft tumor growth inhibition

Compute `TGI% = (1 - (Tt - T0) / (Ct - C0)) * 100` from group-mean tumor volumes,
fit exponential growth (with a log-linear fallback) for per-group doubling times,
and test endpoint volumes with Mann-Whitney U (two groups) or one-way ANOVA
(more). Full pipeline, growth-delay, and spider plots: `references/xenograft-tgi.md`.

### Pharmaceutical stability (Arrhenius)

Fit degradation kinetics (zero/first order) at each accelerated temperature,
select the dominant order by R², linearize `ln(k)` vs `1/T` to get activation
energy Ea, extrapolate the rate to a storage temperature, and project shelf life
to a potency spec limit. See `references/stability.md`.

### Biodistribution and MIRD dosimetry

Convert tissue counts to %ID/g (with optional decay correction), fit
mono-exponential or Bateman uptake-clearance PK, integrate AUC, and report
tumor:blood ratios. MIRD absorbed dose combines time-integrated activity with
tabulated S-values (self + cross-organ). API and the S-value sourcing caveat:
`references/radiopharmacology.md`.

### Adverse-event grading

Grade lab values (ANC, platelets, hemoglobin, ALT, ...) against CTCAE v5.0
thresholds and flag dose-limiting toxicities. The bundled thresholds are a
convenience subset — the authoritative CTCAE table and lab-specific ULN govern.
See `references/adverse-events.md`.

## Cross-cutting best practices

- **Dose-response** — span ≥6 concentrations across ~3 log units, bracket the inflection so responses run ~10%→~90%, include vehicle and a saturating dose, and leave the Hill slope unconstrained. Combination index is only meaningful near the fraction-affected you measured (typically Fa ≈ 0.5).
- **Western blots** — never quantify saturated bands; keep exposure in the linear range; prefer a total-protein stain over a single housekeeping band; report fold change, not raw intensity.
- **Xenograft** — target ≥8–10 animals/group; always pair TGI% with a statistical test; a *negative* TGI means treatment grew faster than control (check group assignment / growth-factor effects).
- **Stability** — use ≥3 temperatures and confirm `ln(k)` vs `1/T` is linear before extrapolating; exclude temperatures where a phase transition changes the mechanism (ICH Q1A–Q1E).
- **Dosimetry** — S-values are phantom/isotope specific; take them from OLINDA/MIRD or IDAC, never invent them.

## Related Skills

`database-lookup` (drug/target/trial lookups), `rdkit` (cheminformatics),
`immunology-assays` (ELISA / titer / multiplex plate assays), `bioimage-analysis`
and `histolab` (general and slide imaging), `statistical-analysis` /
`statsmodels` (formal biostatistics), `cancer-genomics-analysis` (tumor
sequencing), `clinical-decision-support` (clinical rules).
