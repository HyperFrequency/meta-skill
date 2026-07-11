# Filters and Preprocessing

Filters are histolab's composable image-processing primitives. They drive tissue detection
inside masks, preprocess individual tiles, and support quality control. They chain together
with `Compose`, and each is callable: `filter(image) -> image`.

Three families:
- **Image filters** — `histolab.filters.image_filters`
- **Morphological filters** — `histolab.filters.morphological_filters`
- **Composition** — `histolab.filters.compositions.Compose`

## Image filters

| Filter | Does | Use for |
| --- | --- | --- |
| `RgbToGrayscale()` | RGB → grayscale | input to thresholding / morphology |
| `RgbToHsv()` | RGB → HSV | color-based segmentation, pen-mark detection by hue |
| `RgbToHed()` | RGB → Hematoxylin/Eosin/DAB | stain deconvolution, nuclei vs cytoplasm |
| `OtsuThreshold()` | automatic global threshold → binary | tissue / nuclei detection |
| `LocalOtsuThreshold(disk_size=3.0)` | local (per-region) Otsu threshold | uneven illumination / staining |
| `StretchContrast()` | stretch intensity range | reveal faint structures |
| `HistogramEqualization()` | equalize histogram | standardize contrast |
| `Invert()` | invert intensities | preprocessing for some segmenters |
| `Lambda(fn)` | wrap an arbitrary function as a filter | custom inline steps |

```python
from histolab.filters.image_filters import RgbToGrayscale, OtsuThreshold
binary = OtsuThreshold()(RgbToGrayscale()(rgb_image))
```

## Morphological filters

Operate on binary images with a disk-shaped structuring element.

| Filter | Does | Use for |
| --- | --- | --- |
| `BinaryDilation(disk_size=5)` | grow white regions | connect nearby tissue, fill gaps |
| `BinaryErosion(disk_size=5)` | shrink white regions | trim protrusions, separate blobs |
| `BinaryOpening(disk_size=3)` | erode then dilate | remove small objects / noise |
| `BinaryClosing(disk_size=5)` | dilate then erode | fill small holes, smooth interiors |
| `RemoveSmallObjects(min_size=500)` | drop components below area | delete dust/artifacts |
| `RemoveSmallHoles(area_threshold=1000)` | fill holes below area | make tissue contiguous |

Bigger `disk_size` and `area_threshold` = more aggressive. Tune per stain and scanner.

## Composition

Chain filters into a reusable pipeline; `Compose` applies them left to right:

```python
from histolab.filters.compositions import Compose
from histolab.filters.image_filters import RgbToGrayscale, OtsuThreshold
from histolab.filters.morphological_filters import (
    BinaryDilation, RemoveSmallHoles, RemoveSmallObjects,
)

tissue_detection = Compose([
    RgbToGrayscale(),
    OtsuThreshold(),
    BinaryDilation(disk_size=5),
    RemoveSmallHoles(area_threshold=1000),
    RemoveSmallObjects(min_size=500),
])
mask = tissue_detection(rgb_image)
```

Order matters: color conversion → thresholding → morphology. `Compose` is for applying a
pipeline directly to an image (as above). To override a **mask's** default detection instead,
pass the filters to it **positionally** (`TissueMask(RgbToGrayscale(), OtsuThreshold(), ...)`,
not a `Compose` or a `filters=` keyword — see `tissue-masks.md`).

## Common pipelines

**Standard tissue detection** — the `tissue_detection` pipeline above.

**Pen-mark removal** (blue/green marks → white) via HSV + a `Lambda`:

```python
import numpy as np
from histolab.filters.image_filters import RgbToHsv, Lambda
from histolab.filters.compositions import Compose

def blank_pen(hsv):
    h, s = hsv[:, :, 0], hsv[:, :, 1]
    pen = (h > 0.45) & (h < 0.7) & (s > 0.3)   # blue/green, saturated
    hsv[pen] = [0, 0, 1]
    return hsv

pen_removal = Compose([RgbToHsv(), Lambda(blank_pen)])
```

**Nuclei enhancement** — isolate the hematoxylin channel and equalize:

```python
from histolab.filters.image_filters import RgbToHed, HistogramEqualization, Lambda
nuclei = Compose([
    RgbToHed(),
    Lambda(lambda hed: hed[:, :, 0]),   # hematoxylin channel
    HistogramEqualization(),
])
```

## Applying filters to tiles

`Tile` objects expose `apply_filters`:

```python
from histolab.filters.compositions import Compose
from histolab.filters.image_filters import RgbToGrayscale, StretchContrast

processed = tile.apply_filters(Compose([RgbToGrayscale(), StretchContrast()]))
```

## Quality-control snippets

**Blur score** (Laplacian variance — lower is blurrier):

```python
import cv2, numpy as np
def blur_score(gray):
    return cv2.Laplacian(np.array(gray), cv2.CV_64F).var()
```

**Tissue coverage %**:

```python
from histolab.filters.compositions import Compose
from histolab.filters.image_filters import RgbToGrayscale, OtsuThreshold
def tissue_pct(image):
    m = Compose([RgbToGrayscale(), OtsuThreshold()])(image)
    return m.sum() / m.size * 100
```

## Stain normalization caveat

Histolab has **no built-in stain normalizer**. `RgbToHed` gives you the stain channels and you
can renormalize channel statistics by hand, but for production stain normalization across a
cohort use a dedicated tool (`pathml` or a stain-norm library). Treat any hand-rolled HED
renormalization here as a rough approximation, not a validated method.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Detection misses valid tissue | lower `RemoveSmallObjects` `min_size`; smaller opening/erosion; try `LocalOtsuThreshold` |
| Too many artifacts kept | raise `RemoveSmallObjects` `min_size`; add opening/closing; color-filter the artifact |
| Rough tissue boundaries | add `BinaryClosing`/`BinaryOpening`; adjust `disk_size` |
| Variable staining across slides | `HistogramEqualization` or `AdaptiveEqualization` per slide |
