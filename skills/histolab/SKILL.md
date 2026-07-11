---
name: histolab
version: 0.1.0
description: >-
  histolab is a lightweight Python library for whole-slide-image (WSI) processing in
  digital pathology: automatic tissue detection, binary tissue masks, and tile extraction
  that turn gigapixel H&E slides into deep-learning-ready tile datasets. Use it to load
  SVS/TIFF/NDPI/OpenSlide-backed slides, build tissue masks, extract tiles (random, grid,
  or nuclei-score-ranked), compose preprocessing filter pipelines, and preview mask and
  tile locations before committing to a full extraction. Do NOT use it for multiplexed
  immunofluorescence, spatial proteomics, cell/nucleus instance segmentation, stain
  normalization at scale, or end-to-end model training (use `pathml` for those), nor for
  spatial single-cell analysis (use `squidpy` / `scanpy`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "histolab: Apache-2.0"
---

# Histolab

## Overview

Histolab is a focused Python toolkit for the first mile of a computational-pathology
pipeline: taking a gigapixel whole-slide image (WSI) and reducing it to a curated set of
small, tissue-rich tiles. It leans on OpenSlide for pyramidal I/O and adds three things on
top: automated tissue segmentation (binary masks), pluggable tile-extraction strategies
(random, grid, score-ranked), and a composable filter library for preprocessing. Everything
is designed to be previewed before it is run, so you validate mask quality and tile
placement on a thumbnail before spending compute on a full extraction.

Use this skill when the job is "turn these slides into a tile dataset." It is deliberately
narrow — it does not do downstream deep learning, and it does not do multiplexed or spatial
assays.

## When to Use This Skill

- Loading and inspecting WSIs (SVS, TIFF, NDPI, and other OpenSlide formats), including
  dimensions, pyramid levels, and vendor metadata.
- Detecting tissue and building binary masks to exclude background, glass, and artifacts.
- Extracting tiles for a training/eval dataset: random sampling, exhaustive grid coverage,
  or top-`n` selection by a scoring function (e.g. nuclei density).
- Composing image + morphological filter pipelines for tissue detection, pen-mark removal,
  or stain-channel separation.
- Previewing masks (`locate_mask`) and tile locations (`locate_tiles`) on a thumbnail
  before extraction, and visualizing extracted tiles / score distributions afterward.

## When NOT to Use This Skill

- **Multiplexed / mIF imaging, spatial proteomics, cell or nucleus instance segmentation,
  or an integrated DL pipeline** — reach for `pathml`, which is built for that.
- **Spatial single-cell / transcriptomics analysis** — use `squidpy` and `scanpy`.
- **Production stain normalization** — histolab has stain-channel *filters* (HED
  deconvolution) but no batch stain-normalizer; use a dedicated tool.
- **Model training, augmentation, or inference** — histolab stops at producing tiles on
  disk; hand off to your DL framework.

## Installation

```bash
uv pip install histolab
```

Histolab depends on OpenSlide. On some systems you must install the OpenSlide system
library separately (e.g. `brew install openslide`, `apt-get install openslide-tools`) so
the Python bindings can load slide files.

## Quick Start

The canonical loop is **load → mask (implicit) → preview → extract**:

```python
from histolab.slide import Slide
from histolab.tiler import RandomTiler

# 1. Load: slide_path is the WSI, processed_path is where outputs land
slide = Slide("slide.svs", processed_path="output/")
print(slide.dimensions, slide.levels)   # inspect before you commit
slide.thumbnail.save("output/thumbnail.png")   # slide.thumbnail is a PIL image (no save_thumbnail())

# 2. Configure an extractor
tiler = RandomTiler(tile_size=(512, 512), n_tiles=100, level=0, seed=42)

# 3. Preview tile placement on the thumbnail (does not save tiles)
tiler.locate_tiles(slide)

# 4. Extract — the mask is chosen HERE, not in the constructor
tiler.extract(slide)   # defaults to BiggestTissueBoxMask
```

Key API fact that trips people up: the tissue mask is passed to `extract(slide,
extraction_mask=...)` and `locate_tiles(slide, extraction_mask=...)`, **not** to the tiler
constructor. See `references/tile-extraction.md`.

## Capabilities

Each capability has a deep reference with full signatures, parameters, and worked examples.
Load the reference when you need the detail.

### Slide loading and inspection

Load WSIs, read dimensions / pyramid levels / OpenSlide properties, generate thumbnails,
and iterate over slide collections. Histolab also ships built-in TCGA sample slides
(`prostate_tissue()`, `ovarian_tissue()`, `breast_tissue()`, `heart_tissue()`,
`kidney_tissue()`) for testing. Note `slide.level_dimensions(level=k)` is a **method**.

→ `references/slide-management.md`

### Tissue masks

`TissueMask` segments every tissue region; `BiggestTissueBoxMask` (the default) returns the
bounding box of the largest connected region; `BinaryMask` is the base class for custom
masks (fixed ROIs, annotation/pen exclusion, external segmentation). Masks accept custom
filters as **positional args** (`TissueMask(RgbToGrayscale(), OtsuThreshold(), ...)`, not a
`filters=` keyword) and are the `extraction_mask` you hand to a tiler.

→ `references/tissue-masks.md`

### Tile extraction

Three strategies, all sharing `tile_size`, `level`, `check_tissue`, `tissue_percent`,
`prefix`, `suffix`:

| Tiler | Picks | Use when | Key params |
| --- | --- | --- | --- |
| `RandomTiler` | N random tiles | sampling, exploration, balanced training sets | `n_tiles`, `seed`, `max_iter` |
| `GridTiler` | every tile on a grid | full coverage, spatial reconstruction | `pixel_overlap` |
| `ScoreTiler` | top-N by a scorer | most informative regions, dataset curation | `scorer`, `n_tiles` |

Scorers: `NucleiScorer` (nuclei density, cell-rich regions), `CellularityScorer`
(tissue-area fraction), `RandomScorer` (baseline), or a custom subclass of `Scorer`.
`ScoreTiler.extract(slide, report_path="...")` writes a CSV of tile names, coordinates, and
scores.

→ `references/tile-extraction.md`

### Filters and preprocessing

Composable filters run mask detection and tile preprocessing. Image filters
(`RgbToGrayscale`, `RgbToHsv`, `RgbToHed`, `OtsuThreshold`, `LocalOtsuThreshold`,
`StretchContrast`, `HistogramEqualization`, `AdaptiveEqualization`, `Invert`, `Lambda`) and
morphological filters
(`BinaryDilation`, `BinaryErosion`, `BinaryOpening`, `BinaryClosing`, `RemoveSmallObjects`,
`RemoveSmallHoles`) chain via `Compose([...])`. Use them to tune tissue detection, strip pen
marks, or isolate the hematoxylin channel.

→ `references/filters-preprocessing.md`

### Visualization

Inspect and debug with `slide.thumbnail` (a PIL image; save via `slide.thumbnail.save(path)`), mask overlays via
`slide.locate_mask(mask)`, tile-placement previews via `tiler.locate_tiles(slide,
scale_factor=..., outline=...)`, and downstream matplotlib mosaics, score histograms, and
PDF reports (mostly plain matplotlib on top of histolab outputs).

→ `references/visualization.md`

## Choosing a Tiler

- **Just exploring a slide?** `RandomTiler` with a small `n_tiles` and a fixed `seed`.
- **Need every region (segmentation, reconstruction, WSI-level model)?** `GridTiler`;
  set `pixel_overlap=0` for disjoint tiles or a positive value for a sliding window.
- **Want the most cellular / diagnostically dense tiles?** `ScoreTiler` with
  `NucleiScorer` and a `report_path` so you can audit scores.

## Common Pitfalls

- **Zero tiles extracted** → `tissue_percent` too high, or the mask missed the tissue.
  Lower `tissue_percent`, verify the thumbnail has tissue, and preview the mask with
  `locate_mask`. (`references/tile-extraction.md`)
- **Too many background tiles** → set `check_tissue=True`, raise `tissue_percent`, or use a
  tighter mask. (`references/tissue-masks.md`)
- **Extraction is slow** → extract at a higher pyramid level (`level=1` or `2`), reduce
  `n_tiles`, prefer `BiggestTissueBoxMask` over `TissueMask`, and avoid `GridTiler` for mere
  sampling. (`references/tile-extraction.md`)
- **Fewer tiles than `n_tiles` for `RandomTiler`** → expected on sparse slides;
  `n_tiles` is an upper bound bounded by `check_tissue` and `max_iter`.
- **`extraction_mask` ignored** → you passed it to the constructor; it belongs to
  `extract()` / `locate_tiles()`.
