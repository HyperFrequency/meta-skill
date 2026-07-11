# Cell Segmentation Reference

Two families: deep learning (Cellpose) and classical (thresholding + watershed).
Cellpose is more accurate on crowded/irregular cells but needs a model download
and benefits from a GPU; classical methods are dependency-light and deterministic.
Keep a classical fallback so a pipeline runs even when Cellpose is unavailable.

## Cellpose (deep learning)

> **API version.** The recipes here use the classic Cellpose **v2/v3** API. A bare
> `pip install cellpose` now installs **Cellpose 4 (Cellpose-SAM)** — pin
> `cellpose<4` to run them verbatim, or use the v4 form in the box below. See the
> "Cellpose 4 vs classic API" section for the exact differences.

```python
from cellpose import models

model = models.Cellpose(model_type="cyto2")
masks, flows, styles, diams = model.eval(
    image,
    diameter=None,          # None -> auto-estimate; else object diameter in pixels
    channels=[0, 0],        # see channel semantics below
    flow_threshold=0.4,     # higher -> keep more/less-round masks (0.0-3.0)
    cellprob_threshold=0.0, # higher -> fewer, more-confident objects (-6 to 6)
)
print(f"{masks.max()} objects; estimated diameter {diams:.1f}px")
```

`model.eval` returns four values:
- `masks` — integer label image, same HxW as input, 0 = background.
- `flows` — flow fields (mostly for diagnostics/visualization).
- `styles` — a style vector per image.
- `diams` — the diameter Cellpose used (the estimate when `diameter=None`).

### Model selection (`model_type`)

- `cyto2` — general whole-cell/cytoplasm model; the default first choice.
- `cyto` — original cytoplasm model; try if `cyto2` under-segments.
- `nuclei` — nuclear segmentation (DAPI/Hoechst); use for nucleus-only counts.

Auto-diameter estimation (`diameter=None`) is available for these built-in models
because they ship a paired size model.

### Channel semantics (`channels=[cytoplasm, nucleus]`)

Cellpose channel codes: `0` = grayscale, `1` = red, `2` = green, `3` = blue.
- `[0, 0]` — single grayscale channel (most common for brightfield/mono images).
- `[2, 3]` — green cytoplasm + blue nucleus (nucleus channel aids splitting).
- `[cyto_channel, 0]` — cytoplasm channel, no nucleus channel.

### Tuning order when results are wrong

1. **Set an explicit `diameter`** in pixels (measure a few cells). Auto-detection
   is the most common cause of gross over/under-segmentation.
2. **Adjust `cellprob_threshold`** — raise (e.g. `0.5`, up to `6`) to drop weak
   detections, lower (toward `-6`) to recover missed dim cells.
3. **Adjust `flow_threshold`** — lower it (e.g. `0.4 -> 0.2`) to reject
   ill-formed masks; raise it to keep more irregular shapes.

Nuclei-only pass alongside cytoplasm:

```python
nuc_model = models.Cellpose(model_type="nuclei")
nuc_masks, _, _, _ = nuc_model.eval(image, diameter=None, channels=[0, 0])
```

### GPU and lazy-import / fallback

Cellpose pulls in PyTorch and downloads model weights on first use. Import it
lazily and fall back to classical watershed so the pipeline degrades gracefully:

```python
def segment(image, diameter=None):
    try:
        from cellpose import models
        model = models.Cellpose(model_type="cyto2")     # gpu=True to force GPU
        masks, *_ = model.eval(image, diameter=diameter, channels=[0, 0])
        return masks
    except Exception:                                     # no model / no torch / OOM
        return watershed_segment(image)                   # see below
```

Pass `gpu=True` to `models.Cellpose(...)` to request GPU; it silently uses CPU if
no CUDA device is present (slower but identical results).

### Cellpose 4 (Cellpose-SAM) vs the classic API

Cellpose 4 is a rewrite; the recipes above target the classic v2/v3 API. If you
are on v4, adapt as follows:

- **Class:** v4 removes `models.Cellpose`; use `models.CellposeModel(gpu=True)`.
  There is a single super-generalist model, so `model_type="cyto2"/"nuclei"/"cyto"`
  no longer applies — load an older named model (if needed) via
  `pretrained_model="cyto"` / `"nuclei"`.
- **Return arity:** `eval` returns **three** values, `masks, flows, styles`, not
  four — there is no separate size model, so no `diams`. The classic 4-tuple
  unpack raises `ValueError` on v4. `styles` is a zero vector (kept for
  compatibility).
- **Args:** `diameter` and `channels` are still accepted (both optional; channels
  are inferred when `None`). `flow_threshold`/`cellprob_threshold` are unchanged.

```python
from cellpose import models                         # Cellpose 4 (Cellpose-SAM)
model = models.CellposeModel(gpu=True)
masks, flows, styles = model.eval(image, diameter=None)   # 3 values, no model_type
print(f"{masks.max()} objects")
```

To keep the classic recipes working without changes, pin `pip install "cellpose<4"`.

## Classical segmentation (scikit-image + scipy)

### Global Otsu threshold

```python
import skimage.filters
thresh = skimage.filters.threshold_otsu(image)
binary = image > thresh                                   # invert (<) if objects are dark
labeled = skimage.measure.label(binary)                   # connected components
```

Other automatic thresholds for hard cases: `threshold_li` (dim signals, minimum
cross-entropy), `threshold_yen` (high dynamic range), `threshold_triangle`
(skewed histograms). All take the image and return a scalar.

### Adaptive (local) threshold — uneven illumination

```python
block_size = 51                                           # odd; ~ object size
adaptive = skimage.filters.threshold_local(image, block_size, offset=10)
binary = image > adaptive
```

### Watershed to split touching objects

Connected-component labeling merges touching cells into one blob. Watershed splits
them using the distance transform as a topographic surface seeded at local maxima.

```python
import numpy as np
from scipy import ndimage
import skimage.feature, skimage.segmentation

distance = ndimage.distance_transform_edt(binary)         # peaks = object centers
coords = skimage.feature.peak_local_max(
    distance, min_distance=20, labels=binary)             # returns (N, 2) coords
markers = np.zeros(binary.shape, dtype=int)
markers[tuple(coords.T)] = np.arange(1, len(coords) + 1)  # one seed per object
labels = skimage.segmentation.watershed(-distance, markers, mask=binary)
print(f"{labels.max()} objects")
```

Key knob: `min_distance` in `peak_local_max` sets the minimum separation between
seeds. Too small → over-segmentation (one cell split into many); too large →
merged cells. Optionally erode the mask or smooth the distance map first.

`peak_local_max` **returns coordinates**, not a boolean image — always seed markers
via `markers[tuple(coords.T)] = ...`.

## Choosing an approach

| Situation | Use |
|---|---|
| Crowded, irregular, or low-contrast cells | Cellpose `cyto2` |
| Nuclei only (DAPI/Hoechst) | Cellpose `nuclei` |
| Clean, well-separated blobs; no GPU | Otsu + `label` |
| Touching round objects (colonies, nuclei) | Otsu + watershed |
| Uneven illumination / vignetting | adaptive threshold (or background subtract first) |

Always QC: overlay masks with `skimage.segmentation.mark_boundaries(image, labels)`
on a few fields before batch-processing.
