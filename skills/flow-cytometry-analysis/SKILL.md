---
name: flow-cytometry-analysis
version: 0.1.0
description: >-
  End-to-end analysis of flow cytometry event data (from `flowio`-parsed FCS or
  CSV exports): spectral compensation, sequential manual gating
  (rectangular/polygon, doublet exclusion) and automated Gaussian-mixture
  gating, multi-marker immunophenotyping (CD3/CD4/CD8/CD19/CD56/CD14 panels with
  frequency tables and quadrant plots), CFSE/CellTrace proliferation (division
  and proliferation indices, percent divided), Dean-Jett-Fox cell-cycle phasing
  from DNA content, and Annexin V/PI apoptosis quadrants. Use when you already
  have cytometry events and need gated populations, marker frequencies, or
  functional readouts. Do NOT use for raw FCS parsing/writing alone (use
  `flowio`), single-cell RNA-seq (use `scanpy`), CyTOF/mass-cytometry bead
  normalization, or spectral unmixing of full-spectrum instruments — this
  assumes a conventional compensated fluorescence panel.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "flowio: BSD-3-Clause"
---

# Flow Cytometry Analysis

## Overview

Turn parsed flow cytometry events into biological answers. This skill covers the
analytical pipeline that sits *downstream* of file parsing: correcting spectral
overlap, carving out cell populations with gates, and running the standard
functional assays (immunophenotyping, proliferation, cell cycle, apoptosis).

The canonical order is **compensate → gate → quantify**. Every step operates on
a 2-D array of shape `(n_events, n_channels)` plus a parallel list of channel
labels, so the same primitives compose across assays. Deep API tables, reference
implementations, and CLI specs live in `references/`.

Input assumption: you have already parsed an FCS file with `flowio` (or loaded a
CSV export). Get events and channel labels with:

```python
import flowio, numpy as np
fcs = flowio.FlowData("sample.fcs")
events = np.reshape(fcs.events, (-1, fcs.channel_count))  # (n_events, n_channels)
channels = fcs.pnn_labels   # $PnN detector/short names, e.g. "FSC-A", "FL1-A"
stains = fcs.pns_labels     # $PnS conjugate/stain names, e.g. "CD3 FITC"
```

## When to Use This Skill

- Applying a compensation/spillover matrix before analyzing fluorescence.
- Building a sequential gating hierarchy: debris → singlets → viable → markers.
- Immunophenotyping PBMC / whole-blood panels into named populations with
  parent-referenced frequencies.
- Quantifying proliferation from CFSE / CellTrace dye dilution.
- Determining G0/G1, S, G2/M fractions from PI / DAPI DNA-content histograms.
- Scoring apoptosis from Annexin V / propidium-iodide quadrants.
- Automated (unsupervised) gating for high-throughput plates.

## When NOT to Use This Skill

- **Raw FCS read/write, keyword/metadata extraction only** → use `flowio`.
- **Single-cell RNA-seq / cytometry-by-clustering at scale** → use `scanpy`
  (or dimensionality reduction via `umap-learn`) for UMAP/Leiden phenograph-style
  workflows on very high-parameter data.
- **Mass cytometry (CyTOF)**: bead normalization, EQ calibration, and
  arcsinh(cofactor=5) conventions differ — this skill assumes fluorescence.
- **Spectral (full-spectrum) unmixing**: instruments like Aurora need per-detector
  unmixing, not square-matrix compensation.
- **Wet-lab assay design / staining panels** (not computation) → see
  `immunology-assays`.
- **General model fitting or hypothesis tests** on the derived tables → hand off
  to `statistical-analysis` / `statsmodels`.

## Capabilities

Each capability below is a one-paragraph router. Follow the link for signatures,
parameters, failure modes, and runnable CLI scripts.

### Compensation

Spectral overlap is corrected by multiplying fluorescence columns by the
**inverse** of the spillover matrix. The matrix ships inside the FCS TEXT segment
(`$SPILLOVER` / `SPILL` keyword, readable via `fcs.text`) or as an external CSV.
Compensate *before* any fluorescence gating; expect and keep negative values
afterward. See `references/gating-and-compensation.md`.

### Gating

Two families: **manual** (rectangular thresholds and polygon gates via ray
casting) applied sequentially to build a hierarchy, and **automated**
(Gaussian Mixture Model on log-transformed scatter/marker channels, delegated to
`scikit-learn`). Doublet exclusion uses the FSC-A vs FSC-H ratio. Report events
and `% parent` / `% total` at each node. See
`references/gating-and-compensation.md`.

### Immunophenotyping

Define a panel of `marker → {channel, threshold}` entries, gate positivity per
marker, then combine into named populations (CD3+ T cells, CD4/CD8 helper vs
cytotoxic, CD19+ B, CD56+ NK, CD14+ monocytes, CD4+CD25+ Treg candidates, etc.).
Frequencies must be reported against the correct parent gate. Quadrant density
plots visualize two-marker relationships. See `references/immunophenotyping.md`.

### Proliferation (CFSE / CellTrace)

Each division halves dye intensity, producing evenly spaced peaks ~log10(2)
apart on a log scale. Detect generation peaks, assign events to generations by
midpoint boundaries, then compute the standard metrics — **division index**,
**proliferation index**, and **percent divided** — via precursor back-calculation
(a generation-*i* cell descends from 1/2ⁱ precursors). See
`references/functional-assays.md`.

### Cell Cycle (DNA content)

Fit a **Dean-Jett-Fox** model to a PI/DAPI histogram: two Gaussians for G0/G1
and G2/M (mean ratio ≈ 2.0) with a broadened S-phase term between them. Integrate
each component to get phase fractions. Gate singlets on DNA-area vs DNA-width
first, or the fit will be corrupted by doublets. See
`references/functional-assays.md`.

### Apoptosis (Annexin V / PI)

Threshold two channels into four quadrants: viable (AnnexinV−/PI−), early
apoptotic (AnnexinV+/PI−), late apoptotic (AnnexinV+/PI+), and necrotic
(AnnexinV−/PI+). Report each as a percent of the gated parent. See
`references/functional-assays.md`.

### Visualization

2-D pseudo-color density plots (`hist2d` with a log-norm colormap) and overlaid
1-D histograms for comparing conditions, built on `matplotlib` / `seaborn`.
Threshold and quadrant annotations are covered in the reference files above.

## Installation

```bash
uv pip install flowio numpy pandas scipy scikit-learn matplotlib
```

`flowio` (BSD-3-Clause) parses FCS 2.0/3.0/3.1. `fcsparser` is an optional
alternative reader that returns a metadata dict plus a DataFrame.

## Best Practices

- **Compensate first.** Uncompensated data misidentifies populations. Never
  zero-clip compensated values — negatives carry real information; use a
  biexponential/logicle display instead.
- **Gate in order:** debris exclusion → singlets → viability → lineage markers.
  Back-gate to confirm a population lands where expected in scatter.
- **Set thresholds with controls:** FMO (fluorescence-minus-one) for gate
  boundaries, isotype/unstained for background.
- **Report the parent denominator** with every frequency — a percentage is
  meaningless without it.
- **Check rare-event counts.** Aim for >100 events in the population of interest
  before trusting a frequency.
- **Build the CLI wrappers documented in `references/`** (each emits CSVs) for
  reproducible runs instead of ad-hoc notebook code — the reference files give the
  full flag/output spec plus the core functions to assemble them. These CLIs are
  specifications, not files shipped with the skill.

## References

- `references/gating-and-compensation.md` — flowio loading, spillover parsing and
  application, rectangular/polygon/singlet gates, GMM auto-gating, the `gate_fcs`
  CLI, and gating troubleshooting.
- `references/immunophenotyping.md` — panel schema, marker thresholding,
  population-definition table, quadrant/density plots, and the `immunophenotype`
  CLI.
- `references/functional-assays.md` — CFSE proliferation metrics and the
  `cfse_proliferation` CLI, the Dean-Jett-Fox cell-cycle model and the
  `cell_cycle` CLI, Annexin V/PI apoptosis quadrants, and assay-specific
  troubleshooting.

## Related Skills

`flowio` (raw FCS I/O) · `scanpy` (high-parameter clustering / scRNA-seq) ·
`scikit-learn` (GMM auto-gating) · `matplotlib` / `seaborn` (plots) ·
`immunology-assays` (wet-lab panel design) · `statistical-analysis` (downstream
stats).
