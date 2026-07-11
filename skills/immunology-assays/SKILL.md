---
name: immunology-assays
version: 0.1.0
description: >-
  Analyze bench-immunology assay data in Python: fit ELISA 4-parameter-logistic
  standard curves and interpolate unknown concentrations; compute endpoint
  antibody titers and geometric mean titer from serial dilutions; process
  multiplex cytokine (Luminex/MSD) data with 5PL; quantify IHC staining as an
  H-score via HED color deconvolution; call ATAC-seq peaks with MACS2 and test
  differential chromatin accessibility; and measure immune-cell migration
  kinematics from time-lapse microscopy. Use when processing plate-reader
  ELISA/titer/cytokine tables, scoring IHC slides, calling or comparing
  accessibility peaks, or tracking immune-cell motility. Not for flow cytometry
  (use flow-cytometry-analysis), single-cell RNA-seq (use scanpy), or general
  cell segmentation (use bioimage-analysis).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: "scipy, scikit-image, statsmodels, trackpy: BSD-3-Clause; MACS2: BSD-3-Clause; HOMER: free for academic use"
---

# Immunology Assays

## Overview

This skill turns raw output from common wet-lab immunology experiments into
quantitative results. It covers three families of analysis:

- **Curve-fitting plate assays** — ELISA 4-parameter-logistic (4PL) standard
  curves, endpoint antibody titers and geometric mean titer (GMT), and
  multiplex cytokine (Luminex / MSD) 5PL interpolation.
- **Imaging assays** — immunohistochemistry (IHC) H-score by HED color
  deconvolution, immune-cell migration kinematics from time-lapse microscopy,
  and a coarse cell-cycle phase-duration estimate from pulse labeling.
- **Chromatin accessibility** — ATAC-seq peak calling with MACS2, differential
  accessibility, and HOMER motif enrichment.

Each capability is summarized below with a runnable entry point; deep API
detail, parameters, input schemas, and troubleshooting live in `references/`.

## When to Use This Skill

- Fitting an ELISA standard curve and reading unknown concentrations off it.
- Determining an endpoint antibody titer from a serial-dilution plate, or a
  GMT across a cohort.
- Interpolating multiplex cytokine/chemokine concentrations from MFI.
- Scoring IHC slides (H-score, percent-positive) from DAB or AEC sections.
- Calling ATAC-seq peaks and comparing accessibility between conditions.
- Measuring immune-cell speed, displacement, and confinement from tracked
  microscopy, e.g. leukocytes under flow.

## When NOT to Use This Skill

- **Flow cytometry** (gating, compensation, FCS files) — use
  `flow-cytometry-analysis`.
- **Single-cell RNA-seq** (clustering, DE, trajectories) — use `scanpy`.
- **General cell segmentation / object detection** in microscopy where you need
  the masks themselves rather than assay readouts — use `bioimage-analysis`.
- **Rigorous count-based differential accessibility at scale** — the built-in
  test here is a non-parametric quick look; for a peer-review-grade model move
  the peak count matrix into a proper negative-binomial workflow (DESeq2 /
  edgeR / `pydeseq2`). See `references/atac-seq.md`.

## Setup

```bash
uv pip install numpy scipy pandas scikit-image statsmodels
uv pip install trackpy          # only for immune-cell tracking
# ATAC-seq peak calling / motifs (optional, via bioconda):
#   conda install -c bioconda macs2 homer
```

`deeptools` (a sibling skill) is useful for generating normalized ATAC-seq
coverage tracks upstream of peak calling.

## Quick Start — ELISA 4PL

```python
import numpy as np
from scipy.optimize import curve_fit

def four_pl(x, a, b, c, d):
    # a=min asymptote, b=Hill slope, c=EC50, d=max asymptote
    return d + (a - d) / (1 + (x / c) ** b)

conc = np.array([15.6, 31.25, 62.5, 125, 250, 500, 1000])   # drop the zero for fitting
od   = np.array([0.12, 0.22, 0.45, 0.82, 1.35, 1.85, 2.15])

popt, _ = curve_fit(four_pl, conc, od,
                    p0=[od.min(), 1.0, np.median(conc), od.max()], maxfev=10000)
print(f"EC50={popt[2]:.1f}  dynamic range={popt[0]:.2f}-{popt[3]:.2f} OD")
```

Invert the fit to read unknowns, gate them to the linear range, and report
R²/LOD/LOQ — full recipe in `references/curve-fitting-assays.md`.

## Capabilities

### Curve-fitting plate assays → `references/curve-fitting-assays.md`

4PL fitting with `scipy.optimize.curve_fit`, closed-form inverse for
concentration interpolation, blank subtraction, R²/LOD/LOQ, and in-range
gating. Endpoint titer = highest dilution above a negative-control cutoff
(`mean + 3·SD`); GMT and 95% CI computed in log2 space. Multiplex assays use a
5PL fit with a `brentq` numeric inverse and per-analyte CV flags. Includes the
expected CSV schemas (`well, concentration, od450, sample_type`;
`dilution, od450, sample_id`).

### Imaging assays → `references/imaging-assays.md`

IHC: `skimage.color.rgb2hed` separates DAB/AEC from hematoxylin (Ruifrok &
Johnston vectors); pixels are binned negative / weak / moderate / strong and
combined into an H-score (0–300) plus percent-positive. Tracking: per-track
mean/max speed, net displacement, path length, confinement ratio, and MSD, with
a migratory-phenotype classifier; segmentation + linking via `trackpy`.
Cell-cycle phase durations from dual-nucleoside pulse labeling (approximate —
caveats documented).

### ATAC-seq accessibility → `references/atac-seq.md`

MACS2 `callpeak` with ATAC parameters (`-f BAMPE --nomodel --shift -100
--extsize 200`; broad vs narrow), narrowPeak/broadPeak parsing and peak-size
stats, a quick non-parametric differential-accessibility scan with
Benjamini-Hochberg FDR (`statsmodels.stats.multitest.multipletests`), and HOMER
`findMotifsGenome.pl` motif enrichment. Genome-size codes: `hs`, `mm`, `dm`,
`ce`.

## Assay QC Checklist

- **ELISA / cytokine** — standards in duplicate; require R² > 0.99; re-run
  samples that fall outside the curve at an adjusted dilution; keep unknown OD
  inside `[a, d]`.
- **Titers** — treat titers as log-distributed; summarize a group by GMT, not
  arithmetic mean; a ≥4-fold rise is the usual seroconversion threshold.
- **IHC** — use color deconvolution, not naive RGB thresholds; calibrate the
  weak/moderate/strong cutoffs on known control tissue; confirm the image is
  true RGB.
- **ATAC-seq** — always paired-end (`BAMPE`); check the mitochondrial-read
  fraction and TSS enrichment for library quality; tighten `-q` if peak counts
  explode.
- **Tracking** — drop tracks shorter than ~10 frames; sanity-check by
  overlaying trajectories on the raw movie.

See each reference file for failure modes and fixes.
