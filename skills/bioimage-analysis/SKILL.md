---
name: bioimage-analysis
version: 0.1.0
description: >-
  Quantify microscopy images of cells with open-source Python tools:
  segmentation (Cellpose deep-learning models, watershed, Otsu/adaptive
  thresholding), time-lapse object tracking (trackpy), morphology and
  intensity measurement (scikit-image regionprops), colony counting,
  two-channel colocalization (Pearson, Manders), and cytoskeleton/fiber
  orientation. Use when you have raw fluorescence or brightfield micrographs
  (TIFF/CZI/PNG) and need masks, counts, tracks, or per-object shape/intensity
  tables for downstream statistics — for single fields, time-lapse stacks, or
  batch multi-well runs. NOT for whole-slide histopathology (use a WSI tool),
  flow-cytometry event tables, radiology volumes (MRI/CT), or generic
  non-microscopy computer vision. This skill produces measurement tables; hand
  them to `statistical-analysis`, `statsmodels`, or `scikit-learn` for modeling.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (Cellpose, scikit-image, trackpy)"
---

# Bioimage Analysis: Microscopy Quantification for Cell Biology

## Overview

This skill is a **router** for turning raw microscopy images into quantitative
measurements. Almost every task follows the same arc: **load** an image, **segment**
objects into a labeled mask, then **measure** shape/intensity/motion per object and
export a table for statistics. It maps that arc onto a small, stable stack —
`cellpose` for deep-learning segmentation, `scikit-image` for classical
segmentation and measurement, `trackpy` for time-lapse tracking, and
`tifffile`/`aicsimageio` for I/O — and delegates deep parameter tables, extended
recipes, best practices, and troubleshooting to `references/`.

The unifying data structure is an integer **label mask**: a 2D array where each
object's pixels carry a unique positive integer and background is 0. Feed that
mask plus the intensity image to `skimage.measure.regionprops_table` to get a
tidy DataFrame of measurements.

## When to Use This Skill

Trigger when the user wants to:
- Segment cells or nuclei from brightfield or fluorescence images
- Count objects (cells, nuclei, bacterial/mammalian colonies) on a field or plate
- Measure per-object morphology (area, eccentricity, circularity, aspect ratio,
  solidity) and intensity
- Track cell migration or particle motion across time-lapse frames and compute
  velocity, directionality, or MSD
- Quantify colocalization of two fluorescence channels (Pearson, Manders M1/M2)
- Characterize cytoskeleton/fiber orientation and alignment order parameter
- Score mitochondrial morphology or membrane-potential ratio (JC-1/TMRM)
- Batch-process many fields of view or multi-well plate images with identical
  parameters

## When NOT to Use This Skill

- **Whole-slide histopathology (WSI, gigapixel `.svs`/`.ndpi`)** — use a dedicated
  WSI/pathology tool with tiling and stain deconvolution, not full-image loads here.
- **Flow-cytometry event tables (FCS)** — those are per-event tabular data, not
  images; use a flow-cytometry analysis tool.
- **Radiology volumes (MRI/CT/PET)** — clinical 3D imaging needs its own toolchain.
- **Generic non-microscopy computer vision** (natural photos, OCR, object
  detection on scenes) — use a general vision stack.
- **Downstream statistics or ML on the measurements** — this skill emits tables;
  hand them to `statistical-analysis`, `statsmodels`, `pymc`, or `scikit-learn`,
  and plot with `matplotlib`/`seaborn`.

## Install and Import

```bash
pip install "cellpose<4" scikit-image trackpy tifffile aicsimageio numpy pandas
# scipy comes with scikit-image; add matplotlib for visual QC overlays.
```

```python
import numpy as np, pandas as pd
import tifffile, skimage.io, skimage.filters, skimage.measure, skimage.segmentation
```

**Cellpose version — recipes below use the classic v2/v3 API** (`models.Cellpose`,
`model_type=`, a 4-value `eval` returning `masks, flows, styles, diams`). A bare
`pip install cellpose` now installs **Cellpose 4 (Cellpose-SAM)**, which drops
`models.Cellpose` for `models.CellposeModel` (one generalist model, no
`model_type`) and returns **3 values** (`masks, flows, styles`). Pin `cellpose<4`
to run these recipes verbatim, or see `references/segmentation.md` for the v4 form.

Cellpose is a large/optional dependency (pulls in PyTorch). Import it lazily and
keep a classical `watershed` fallback so the pipeline still runs without a GPU or
model download — see `references/segmentation.md`.

## Capability Map

Each row is an entry point; follow the reference link for signatures, parameters,
and worked examples.

| Task | Entry point | Depth |
|---|---|---|
| Load TIFF/CZI/multi-dim, preprocess (CLAHE, denoise, background) | `tifffile.imread`, `AICSImage`, `skimage.exposure`/`filters` | `references/workflows.md` |
| Deep-learning cell/nucleus segmentation | `cellpose.models.Cellpose(...).eval(...)` | `references/segmentation.md` |
| Classical segmentation (Otsu, adaptive, watershed) | `skimage.filters.threshold_*`, `skimage.segmentation.watershed` | `references/segmentation.md` |
| Per-object morphology + intensity table | `skimage.measure.regionprops_table` | `references/morphology.md` |
| Cytoskeleton/fiber orientation, mitochondria | `skimage.feature.canny` + `hough_line`; regionprops | `references/morphology.md` |
| Time-lapse tracking, velocity, MSD | `trackpy.batch`/`link`/`filter_stubs`/`emsd` | `references/tracking.md` |
| Two-channel colocalization (Pearson, Manders, Costes) | `scipy.stats.pearsonr` + threshold masks | `references/colocalization.md` |
| Colony counting on plates | Otsu + `remove_small_objects` + watershed | `references/workflows.md` |
| Batch over many fields/wells | loop + `pandas.concat` + `groupby` | `references/workflows.md` |

## Minimal Recipes

**Segment (Cellpose) and measure — the canonical pipeline:**

```python
from cellpose import models                           # classic v2/v3 API (pin cellpose<4)
image = skimage.io.imread("cells.tif")
model = models.Cellpose(model_type="cyto2")           # "nuclei" for DAPI-only
masks, flows, styles, diams = model.eval(
    image, diameter=None, channels=[0, 0])            # diameter=None auto-estimates
# Cellpose 4: model = models.CellposeModel(gpu=True); masks, flows, styles = model.eval(image)
props = skimage.measure.regionprops_table(
    masks, intensity_image=image,
    properties=["label", "area", "eccentricity", "mean_intensity"])
df = pd.DataFrame(props)
print(f"Detected {masks.max()} cells")                # masks.max() == object count
```

**Classical fallback (no GPU / no model) — Otsu + watershed split:**

```python
from scipy import ndimage
binary = image > skimage.filters.threshold_otsu(image)
distance = ndimage.distance_transform_edt(binary)
coords = skimage.feature.peak_local_max(distance, min_distance=20, labels=binary)
markers = np.zeros(image.shape, dtype=int)
markers[tuple(coords.T)] = np.arange(1, len(coords) + 1)
labels = skimage.segmentation.watershed(-distance, markers, mask=binary)
```

**Track a time-lapse (T, Y, X) and count trajectories:**

```python
import trackpy as tp
frames = tifffile.imread("timelapse.tif")             # shape (T, Y, X)
feats = tp.batch(frames, diameter=11, minmass=1000)   # diameter must be ODD
tracks = tp.filter_stubs(tp.link(feats, search_range=15, memory=3), threshold=10)
print(f"{tracks['particle'].nunique()} tracks over {len(frames)} frames")
```

Extended, runnable versions — preprocessing, adaptive thresholding, colony
counting, migration velocity, colocalization, mitochondrial/fiber analysis, and
batch loops — live in `references/`.

## Failure Modes and Gotchas

- **Validate segmentation before trusting counts.** Overlay masks on the raw
  image (`skimage.segmentation.mark_boundaries` or a `matplotlib` overlay) on a
  few fields before batch-processing. Bad segmentation silently corrupts every
  downstream number.
- **Cellpose diameter drives everything.** If auto-detection (`diameter=None`)
  under- or over-segments, pass an explicit pixel diameter. Tune
  `cellprob_threshold` (higher → fewer objects) and `flow_threshold` next. See
  `references/segmentation.md`.
- **`peak_local_max` returns coordinates, not a mask.** In current scikit-image it
  returns an `(N, 2)` array of row/col indices — seed markers with
  `markers[tuple(coords.T)] = ...`, do not treat the return value as a boolean image.
- **trackpy `diameter` must be an odd integer**; set `search_range` smaller than
  the typical inter-object spacing or links jump between objects, and raise
  `minmass` to drop dim spurious features. `filter_stubs` removes short spurious
  tracks.
- **Record the pixel size (µm/px) and frame interval** from microscope metadata.
  Areas, speeds, and MSD are meaningless in absolute units without them; regionprops
  reports pixels/frames until you scale.
- **Colocalization needs background subtraction and controls.** Threshold both
  channels (Costes/Otsu), report Pearson *and* Manders, and include single-stained
  controls to bound bleed-through — see `references/colocalization.md`.
- **Keep preprocessing identical across a batch.** Any per-image tweak to
  threshold, denoise, or segmentation parameters makes fields non-comparable.
- **Check bit depth and axis order first.** `tifffile.imread(...).shape`/`.dtype`;
  multi-series or TCZYX files load cleanly via `aicsimageio.AICSImage`.

## References

- `references/segmentation.md` — Cellpose model selection (`cyto2`/`nuclei`/`cyto`),
  full `eval` parameters and `channels` semantics, GPU/fallback handling, and the
  classical Otsu / adaptive-threshold / watershed pipeline with tuning notes.
- `references/tracking.md` — trackpy locate/batch/link/filter/MSD workflow, parameter
  tuning, drift subtraction, and per-track velocity/directionality/displacement.
- `references/morphology.md` — the `regionprops_table` property catalogue, derived
  shape metrics (circularity, aspect ratio), fiber-orientation via Hough transform
  with the alignment order parameter, and mitochondrial morphology classification.
- `references/colocalization.md` — Pearson, Manders M1/M2, Manders overlap, Costes
  automatic thresholding, threshold-method choices, and required controls.
- `references/workflows.md` — end-to-end recipes (segment+count, colony counting,
  migration velocity, batch multi-well), image loading/preprocessing, best
  practices, and a troubleshooting table.
