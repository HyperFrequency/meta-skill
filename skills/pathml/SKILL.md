---
name: pathml
version: 0.1.0
description: >-
  PathML is a full-featured Python toolkit for computational pathology: load whole-slide
  and multiplexed images across 160+ vendor formats, build composable preprocessing
  pipelines (tissue detection, H&E stain normalization, nucleus/cell segmentation),
  construct cell and tissue graphs, train and run deep models (HoVer-Net, HACTNet),
  quantify multiplexed immunofluorescence (CODEX, Vectra) to single-cell AnnData, and
  persist tiled datasets to HDF5 (h5path) with Dask-distributed scaling. Use when loading
  WSI/multiparametric slides, normalizing stains at scale, segmenting nuclei or cells,
  building spatial graphs, training pathology CNNs, or turning CODEX/Vectra runs into a
  cell-by-marker table. Do NOT use for simple H&E tile extraction (use `histolab`), for
  generic single-cell or spatial-statistics analysis once you already hold an AnnData
  (use `scanpy`/`squidpy`/`anndata`), for the AnnData container/IO itself (`anndata`), or
  for radiology and other non-pathology imaging.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "PathML: GPL-2.0"
---

# PathML

## Overview

PathML (Dana-Farber / Berbeco Lab) is a Python framework for building reproducible,
scalable computational-pathology pipelines. Everything centers on one data object,
`SlideData`, and one processing primitive, a `Pipeline` of composable `Transform`
steps. You load a slide, run a pipeline over its tiles, and read back processed
tiles, masks, extracted features, and — for multiplexed data — a single-cell
`AnnData` table. Work scales from one slide on a laptop to thousands of slides on a
Dask cluster, and processed state persists to an HDF5 `h5path` file.

PathML covers brightfield H&E (segmentation, stain normalization, tissue/nucleus
detection), multiparametric immunofluorescence (CODEX, Vectra, multiplex IF), graph
construction for graph-neural-network models, and PyTorch model training/inference
(HoVer-Net, HACTNet). It hands off to `scanpy`/`squidpy` for downstream single-cell
and spatial analysis rather than reimplementing them.

## When to Use This Skill

- Loading whole-slide images in vendor formats (Aperio SVS, Hamamatsu NDPI, Leica
  SCN, 3DHISTECH MRXS, DICOM WSI, OME-TIFF) or multiplex formats (CODEX, Vectra
  `.qptiff`).
- Building preprocessing pipelines: tissue detection, H&E stain normalization
  (Macenko/Vahadane), blur/threshold/morphology, artifact and whitespace labeling.
- Nucleus or cell segmentation (H&E nucleus detection; Mesmer cell segmentation for
  multiplex IF) and per-cell marker quantification to `AnnData`.
- Constructing cell graphs and tissue graphs for spatial GNN models (the HACT
  hierarchical representation used by HACTNet).
- Training, fine-tuning, or running HoVer-Net / HACTNet, or extracting tile
  embeddings, with PyTorch and public datasets (PanNuke, etc.).
- Managing large tiled datasets: HDF5 `h5path` storage, distributed processing,
  batch and HPC job workflows.

## When NOT to Use This Skill

- Simple H&E tissue masking and tile extraction from a single slide — `histolab` is
  lighter and has no JVM dependency.
- Downstream single-cell analysis once you already have a cell-by-marker matrix
  (clustering, UMAP, marker ranking) — use `scanpy`; for spatial neighborhood
  enrichment, co-occurrence, or Moran's I use `squidpy`.
- Creating, reading, or concatenating the `AnnData` container itself — use `anndata`.
- Non-pathology imaging (radiology, generic microscopy segmentation without the WSI
  pyramid model) — use `bioimage-analysis` or `pydicom`.
- Training loops that are not pathology-specific — the model layer is plain PyTorch;
  wrap it with `pytorch-lightning` if you want a generic trainer.

## Core Mental Model

```python
from pathml.core import HESlide
from pathml.preprocessing import Pipeline, TissueDetectionHE, StainNormalizationHE

wsi = HESlide("slide.svs")                       # SlideData subclass, lazy pyramid
pipeline = Pipeline([                             # ordered list of Transforms
    TissueDetectionHE(),                          # writes tile.masks["tissue"]
    StainNormalizationHE(target="normalize",
                         stain_estimation_method="macenko"),
])
wsi.run(pipeline, tile_size=256, tile_stride=256, level=0)  # tiles + runs pipeline
for tile in wsi.tiles:                            # processed results
    img  = tile.image                             # numpy array
    mask = tile.masks["tissue"]
wsi.write("slide.h5path")                         # persist processed state
```

Key objects: `SlideData` (and typed subclasses `HESlide`, `VectraSlide`,
`CODEXSlide`, `MultiparametricSlide`); `Tile` with `.image`, `.coords`, `.masks`;
`Pipeline` / `Transform`; and after `QuantifyMIF`, the single-cell table lives on
`slide.counts` as an `AnnData`. `slide.run(...)` accepts `distributed=True,
client=<dask client>` to fan tiles across workers.

## Capabilities

Each area has a dedicated reference with concrete APIs, parameters, and worked
pipelines. Read the reference for the task in front of you rather than loading all
of them.

| Area | Use it for | Reference |
| --- | --- | --- |
| Image loading & formats | Opening WSI/multiplex slides, pyramid levels, tiling, thumbnails, metadata, backends | [references/image_loading.md](references/image_loading.md) |
| Preprocessing pipelines | Transform catalog, stain normalization, tissue/nucleus detection, QC, custom transforms | [references/preprocessing.md](references/preprocessing.md) |
| Graph construction | Cell graphs (KNN), tissue graphs (RAG/superpixels), graph features, HACT representation | [references/graphs.md](references/graphs.md) |
| Machine learning | HoVer-Net / HACTNet, loss & post-processing, PanNuke datasets, training, ONNX inference | [references/machine_learning.md](references/machine_learning.md) |
| Multiparametric imaging | CODEX/Vectra workflows, Mesmer segmentation, QuantifyMIF → AnnData, scanpy/squidpy handoff | [references/multiparametric.md](references/multiparametric.md) |
| Data management | h5path HDF5 storage, tile stitching, distributed/HPC batch processing, feature stores | [references/data_management.md](references/data_management.md) |

## Installation

PathML wraps native libraries (OpenSlide for WSI, Bio-Formats via a Java runtime for
OME-TIFF/CODEX/Vectra), so a conda environment is the reliable path:

```bash
conda create -n pathml python=3.10
conda activate pathml
conda install -c conda-forge openslide openjdk       # native WSI + JVM for Bio-Formats
pip install pathml
```

DeepCell (Mesmer) segmentation and the deep models pull in TensorFlow/PyTorch; a GPU
is strongly recommended for segmentation and training. Verify the install with
`python -c "import pathml; print(pathml.__version__)"`.

## Boundaries and Gotchas

- **Native dependencies.** OME-TIFF, CODEX, and Vectra go through the Bio-Formats
  backend, which needs a JVM (`scyjava`/`javabridge`). "Slide won't open" is almost
  always a missing OpenSlide or missing/mismatched JDK — try the other `backend`.
- **License.** PathML is **GPL-2.0**; linking it into distributed software imposes
  GPL obligations. This skill's wrapper text is Apache-2.0, but the library is not.
- **Memory.** WSIs are gigapixel. Always tile (`tile_size` at `level=1`/`2` for most
  work; reserve `level=0` for final high-res passes). Never `extract_region` the full
  level-0 image.
- **Mesmer needs microns-per-pixel.** `SegmentMIF(image_resolution=...)` must match
  the slide's real mpp or segmentation degrades badly.
- **Channels are positional.** Multiplex transforms reference channels by index/order;
  map marker names to channel indices from the slide's `channel_names`.
- **Verify exact signatures.** PathML's API evolves across major versions (notably the
  `pathml.graph` and `pathml.ml` modules). Treat the parameter lists in the references
  as a guide and confirm against the installed version's `pathml` API reference.

## References

- [references/image_loading.md](references/image_loading.md) — formats, slide classes, tiling, pyramids, metadata.
- [references/preprocessing.md](references/preprocessing.md) — full transform catalog and pipeline construction.
- [references/graphs.md](references/graphs.md) — cell/tissue graph builders and features.
- [references/machine_learning.md](references/machine_learning.md) — models, training, evaluation, ONNX.
- [references/multiparametric.md](references/multiparametric.md) — CODEX/Vectra, Mesmer, quantification, downstream analysis.
- [references/data_management.md](references/data_management.md) — h5path storage, stitching, batch/HPC processing.
