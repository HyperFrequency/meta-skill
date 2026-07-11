# Preprocessing Pipelines & Transforms

PathML preprocessing is a `Pipeline` — an ordered list of `Transform` objects applied
to each tile. Transforms modify the tile image, write masks into `tile.masks`, or
extract features. Pipelines are serializable and run identically on one slide or a
distributed dataset, which is what makes preprocessing reproducible at scale.

```python
from pathml.preprocessing import Pipeline, TissueDetectionHE, StainNormalizationHE

pipeline = Pipeline([
    TissueDetectionHE(),
    StainNormalizationHE(target="normalize", stain_estimation_method="macenko"),
])

wsi.run(pipeline, tile_size=256, tile_stride=256, level=1)   # single slide
dataset.run(pipeline, distributed=True)                       # many slides
```

Order matters: quality control first, then noise reduction, then tissue detection,
then color-dependent steps (stain normalization) that benefit from a tissue mask.

## Transform catalog

Import all of these from `pathml.preprocessing`. Parameter names below are the common
ones; confirm against your installed version.

### Image modification

- `MedianBlur(kernel_size=5)` — edge-preserving denoise (salt-and-pepper).
- `GaussianBlur(kernel_size=5, sigma=1.0)` — smooth denoise.
- `BoxBlur(kernel_size=5)` — fastest, uniform averaging.
- `RescaleIntensity(in_range=..., out_range=(0, 255))` — intensity rescaling.
- `HistogramEqualization()` — global contrast.
- `AdaptiveHistogramEqualization(clip_limit=0.03, ...)` — CLAHE local contrast.
- `SuperpixelInterpolation(...)` — SLIC superpixel segmentation of the tile.

### Mask creation (H&E)

- `TissueDetectionHE(use_saturation=True, threshold=..., min_region_size=...)` — binary
  tissue mask into `tile.masks["tissue"]`; filters small artifacts.
- `NucleusDetectionHE(...)` — separates the hematoxylin channel and thresholds it to a
  nucleus mask. This is classical (thresholding), not deep learning — for instance
  segmentation use HoVer-Net (see `machine_learning.md`).
- `BinaryThreshold(threshold=..., use_otsu=...)` — Otsu or manual thresholding.
- `ForegroundDetection(...)` — generic foreground mask.

### Mask modification

- `MorphOpen(kernel_size=..., mask_name="tissue")` — erosion then dilation; removes
  small false positives.
- `MorphClose(kernel_size=..., mask_name="tissue")` — dilation then erosion; fills small
  holes.

### Quality control

- `LabelArtifactTileHE(...)` — flag tiles with pen marks, bubbles, and similar
  artifacts.
- `LabelWhiteSpaceHE(...)` — flag mostly-background tiles for filtering.

### Multiplex (see `multiparametric.md` for full workflows)

- `CollapseRunsCODEX(z=..., ...)` — consolidate multi-cycle CODEX into one multichannel
  image and select a focal plane.
- `CollapseRunsVectra(...)` — collapse Vectra multispectral data.
- `SegmentMIF(model="mesmer", nuclear_channel=..., cytoplasm_channel=..., image_resolution=...)`
  — DeepCell Mesmer cell segmentation; channels are given by index.
- `QuantifyMIF(segmentation_mask_name="cell_segmentation")` — per-cell marker
  quantification into `slide.counts` as an `AnnData`.

## Stain normalization

`StainNormalizationHE` corrects staining and scanner variability by decomposing H&E
into optical-density stain vectors, then reconstructing to a reference. Core arguments:

- `target` — `"normalize"` (match a reference), `"hematoxylin"`, or `"eosin"` (extract a
  single stain channel).
- `stain_estimation_method` — `"macenko"` (Macenko 2009: faster, robust) or `"vahadane"`
  (Vahadane 2016: more accurate, slower).
- an optional tissue mask so background pixels do not skew the stain-vector estimate.

Best result: detect tissue first, then normalize using that mask.

```python
from pathml.preprocessing import Pipeline, TissueDetectionHE, StainNormalizationHE

pipeline = Pipeline([
    TissueDetectionHE(),
    StainNormalizationHE(target="normalize", stain_estimation_method="macenko"),
])
```

## Worked pipelines

### H&E preprocessing with QC

```python
from pathml.preprocessing import (
    Pipeline, LabelWhiteSpaceHE, MedianBlur, TissueDetectionHE,
    MorphOpen, MorphClose, StainNormalizationHE, NucleusDetectionHE,
)

pipeline = Pipeline([
    LabelWhiteSpaceHE(),                 # 1. drop uninformative tiles
    MedianBlur(kernel_size=3),           # 2. denoise
    TissueDetectionHE(min_region_size=500),
    MorphOpen(mask_name="tissue"),       # 3. clean the mask
    MorphClose(mask_name="tissue"),
    StainNormalizationHE(                # 4. normalize using the tissue mask
        target="normalize", stain_estimation_method="macenko",
    ),
    NucleusDetectionHE(),                # 5. classical nucleus mask
])
```

### CODEX multiplex pipeline

```python
from pathml.preprocessing import Pipeline, CollapseRunsCODEX, SegmentMIF, QuantifyMIF

codex_pipeline = Pipeline([
    CollapseRunsCODEX(z=2),                                  # focal plane
    SegmentMIF(model="mesmer", nuclear_channel=0,
               cytoplasm_channel=1, image_resolution=0.377), # Mesmer
    QuantifyMIF(segmentation_mask_name="cell_segmentation"), # -> slide.counts
])
```

## Custom transforms

Subclass `Transform` and implement `apply(tile)` (mutate `tile.image` / `tile.masks`
in place). Keep transforms pure and stateless so they serialize for distributed runs.

```python
from pathml.preprocessing import Transform

class ClipIntensity(Transform):
    def __init__(self, low, high):
        self.low, self.high = low, high

    def apply(self, tile):
        tile.image = tile.image.clip(self.low, self.high)
```

## Running at scale

- Single slide: `wsi.run(pipeline, tile_size=..., tile_stride=..., level=...)`.
- Many slides: `dataset.run(pipeline, distributed=True, client=<dask client>)` — see
  `data_management.md` for the Dask setup and HDF5 persistence.
- Some transforms (Mesmer, matrix-heavy stain estimation) benefit from a GPU.

## Troubleshooting

- **Stain normalization produces artifacts** — pass a tissue mask; switch macenko↔
  vahadane; check that background intensity assumptions match your slides.
- **Tissue detection misses tissue** — lower the threshold, enable
  `use_saturation=True`, or reduce `min_region_size`.
- **Classical nucleus detection is noisy** — normalize stain first, or move to
  HoVer-Net for instance-level results.
- **OOM during a distributed run** — fewer Dask workers, smaller tiles, higher pyramid
  level, or set a per-worker memory limit.

## External references

- PathML preprocessing API: https://pathml.readthedocs.io/en/latest/api_preprocessing_reference.html
- Macenko et al. 2009; Vahadane et al. 2016 (stain normalization).
- DeepCell Mesmer: https://www.deepcell.org/
