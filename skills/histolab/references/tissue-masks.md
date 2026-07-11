# Tissue Masks

A tissue mask is a binary array marking which pixels are tissue vs background. It is what a
tiler uses to decide *where* it is allowed to place tiles. Picking (or building) the right
mask is the single biggest lever on extraction quality.

## The three mask classes

All live in `histolab.masks`.

### `BiggestTissueBoxMask` (default)

Bounding box around the **largest connected tissue region**. This is the default mask for
every tiler.

```python
from histolab.masks import BiggestTissueBoxMask
mask = BiggestTissueBoxMask()
```

Best for slides with one dominant tissue section where you want to ignore small fragments,
control tissue, or debris. It is also the cheapest mask to compute.

### `TissueMask`

Segments **all** tissue regions on the slide, not just the largest.

```python
from histolab.masks import TissueMask
mask = TissueMask()
binary = mask(slide)   # calling the mask on a slide returns a binary numpy array
```

Default detection pipeline (conceptually): grayscale → Otsu threshold → binary dilation →
fill small holes → remove small objects. `True` = tissue, `False` = background.

Best for slides with multiple separate sections (e.g. tissue microarrays, several biopsies on
one slide) where every region matters. More thorough but heavier than `BiggestTissueBoxMask`.

### `BinaryMask`

Abstract base class for custom masks. Subclass it and implement `_mask(self, obj)` returning a
boolean numpy array shaped like the slide thumbnail.

```python
import numpy as np
from histolab.masks import BinaryMask

class RectangularMask(BinaryMask):
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    def _mask(self, obj):
        thumb = np.array(obj.thumbnail)
        m = np.zeros(thumb.shape[:2], dtype=bool)
        m[self.y:self.y + self.h, self.x:self.x + self.w] = True
        return m

roi = RectangularMask(1000, 500, 2000, 1500)
```

Use `BinaryMask` for fixed regions of interest, annotation/pen exclusion, or wiring in an
external segmentation model.

## Customizing detection with filters

`TissueMask` (and `BiggestTissueBoxMask`) accept custom filters as **positional arguments**
that replace the default detection pipeline — pass the individual filters directly, **not**
wrapped in a `Compose` and **not** via a `filters=` keyword (the signature is
`TissueMask(*filters)`). Bigger structuring elements and larger area thresholds detect tissue
more aggressively and discard more small artifacts:

```python
from histolab.masks import TissueMask
from histolab.filters.image_filters import RgbToGrayscale, OtsuThreshold
from histolab.filters.morphological_filters import (
    BinaryDilation, RemoveSmallHoles, RemoveSmallObjects,
)

mask = TissueMask(
    RgbToGrayscale(),
    OtsuThreshold(),
    BinaryDilation(disk_size=10),
    RemoveSmallHoles(area_threshold=5000),
    RemoveSmallObjects(min_size=3000),   # drop connected components below 3000 px
)
```

## Excluding pen marks / annotations

Pathologists' pen marks (usually blue/green) get segmented as tissue and pollute tiles. Detect
them in HSV and subtract from the tissue mask inside a custom `BinaryMask`:

```python
import cv2, numpy as np
from histolab.masks import BinaryMask, TissueMask

class PenExcludingMask(BinaryMask):
    def _mask(self, obj):
        thumb = np.array(obj.thumbnail)
        hsv = cv2.cvtColor(thumb, cv2.COLOR_RGB2HSV)
        pen = cv2.inRange(hsv, np.array([100, 50, 50]), np.array([130, 255, 255]))
        tissue = TissueMask()(obj)
        return tissue & ~pen.astype(bool)
```

## Previewing a mask

Always eyeball the mask before extracting. `locate_mask` overlays the mask boundary on the
slide thumbnail:

```python
slide.locate_mask(TissueMask())
```

Or compare masks manually with matplotlib (see `visualization.md` for a side-by-side and
overlay recipe).

## Using a mask in extraction

The mask is passed to the tiler's `extract()` / `locate_tiles()` methods — **not** the
constructor:

```python
from histolab.tiler import RandomTiler
from histolab.masks import TissueMask

tiler = RandomTiler(tile_size=(512, 512), n_tiles=100, level=0, seed=42)
tiler.extract(slide, extraction_mask=TissueMask())   # all tissue sections
# omit extraction_mask to use the default BiggestTissueBoxMask
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Mask includes too much background | Raise `RemoveSmallObjects` `min_size`; tighten Otsu via custom filters |
| Mask drops valid tissue | Lower `RemoveSmallObjects` `min_size`; reduce dilation `disk_size` |
| Only the largest section captured | Switch `BiggestTissueBoxMask` → `TissueMask` |
| Pen marks captured as tissue | Add a custom pen-exclusion `BinaryMask` (above) |
| `TissueMask` too slow | Fall back to `BiggestTissueBoxMask` for single-section slides |
