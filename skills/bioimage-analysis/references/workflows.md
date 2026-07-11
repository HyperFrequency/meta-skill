# Workflows, Preprocessing, Best Practices & Troubleshooting

End-to-end recipes plus the I/O, preprocessing, and QC glue around them. Each
workflow is the "load → segment → measure → export" arc specialized to a task.

## Image loading & preprocessing

```python
import tifffile, skimage.io, skimage.exposure, skimage.filters
from skimage.morphology import white_tophat, disk, square
from skimage.filters import median

image = tifffile.imread("experiment.tif")            # raw loader; check shape/dtype
print(image.shape, image.dtype)

# Multi-dimensional (TCZYX) formats like .czi/.nd2:
from aicsimageio import AICSImage                     # successor project: bioio
data = AICSImage("multi_dim.czi").get_image_data("ZYX", C=0, T=0)

# Contrast / denoise / background:
enhanced = skimage.exposure.equalize_adapthist(image, clip_limit=0.03)  # CLAHE
denoised = skimage.filters.gaussian(image, sigma=1.0)                    # smooth noise
cleaned  = median(image, square(3))                                     # salt & pepper
bg_removed = white_tophat(image, disk(50))            # rolling-ball-style background
```

Inspect **before** processing: bit depth (`dtype`), dimensions/axis order
(`shape`), and channel order. Match preprocessing to the defect — CLAHE for low
contrast, Gaussian/median for noise, white-tophat for uneven illumination — and
keep it **identical across every image in an experiment**.

## Workflow 1 — Segment and count cells (brightfield/fluorescence)

```python
from cellpose import models
import skimage.io, skimage.measure, pandas as pd

image = skimage.io.imread("cells.tif")
model = models.Cellpose(model_type="cyto2")
masks, _, _, diams = model.eval(image, diameter=None, channels=[0, 0])

df = pd.DataFrame(skimage.measure.regionprops_table(
    masks, intensity_image=image,
    properties=["label", "area", "eccentricity", "mean_intensity", "centroid"]))
print(f"count={masks.max()}, mean_area={df['area'].mean():.1f}px, "
      f"mean_ecc={df['eccentricity'].mean():.3f}")
```

## Workflow 2 — Colony counting on an agar plate

```python
import numpy as np, skimage.io, skimage.filters, skimage.measure, skimage.segmentation
from skimage.morphology import remove_small_objects
from skimage.feature import peak_local_max
from scipy import ndimage

plate = skimage.io.imread("agar_plate.jpg", as_gray=True)
smoothed = skimage.filters.gaussian(plate, sigma=2)
binary = smoothed < skimage.filters.threshold_otsu(smoothed)   # colonies are dark
binary = remove_small_objects(binary, min_size=50)             # drop debris

distance = ndimage.distance_transform_edt(binary)
coords = peak_local_max(distance, min_distance=10, labels=binary)
markers = np.zeros(plate.shape, dtype=int)
markers[tuple(coords.T)] = np.arange(1, len(coords) + 1)
labels = skimage.segmentation.watershed(-distance, markers, mask=binary)

regions = skimage.measure.regionprops(labels)
areas = [r.area for r in regions]
print(f"colonies={len(regions)}, mean_area={np.mean(areas):.0f}px^2")
```

Tune `min_size` (debris rejection) and `min_distance` (splitting of touching
colonies). For low-contrast plates, use a manual threshold instead of Otsu.

## Workflow 3 — Cell migration velocity (time-lapse)

```python
import trackpy as tp, tifffile, numpy as np, pandas as pd

frames = tifffile.imread("migration.tif")            # (T, Y, X)
pixel_size, dt = 0.65, 5                              # µm/px, min/frame

feats = tp.batch(frames, diameter=15, minmass=500)
tracks = tp.filter_stubs(tp.link(feats, search_range=20, memory=3), threshold=10)

speeds = []
for _, g in tracks.groupby("particle"):
    g = g.sort_values("frame")
    step = np.hypot(np.diff(g["x"]) * pixel_size, np.diff(g["y"]) * pixel_size)
    speeds.append(step.mean() / dt)                  # µm/min
print(f"mean migration speed = {np.mean(speeds):.3f} µm/min")
```

See `references/tracking.md` for directionality, MSD, and drift subtraction.

## Workflow 4 — Batch over many fields / wells

```python
from pathlib import Path
import skimage.io, skimage.measure, pandas as pd
from cellpose import models

model = models.Cellpose(model_type="cyto2")          # build ONCE, reuse in loop
results = []
for path in sorted(Path("plate_images/").glob("*.tif")):
    image = skimage.io.imread(str(path))
    masks, _, _, _ = model.eval(image, diameter=None, channels=[0, 0])
    df = pd.DataFrame(skimage.measure.regionprops_table(
        masks, intensity_image=image,
        properties=["label", "area", "eccentricity", "mean_intensity"]))
    df["image"] = path.stem
    results.append(df)

allcells = pd.concat(results, ignore_index=True)
summary = allcells.groupby("image").agg(
    cell_count=("label", "count"),
    mean_area=("area", "mean"),
    mean_intensity=("mean_intensity", "mean")).reset_index()
```

Instantiate the Cellpose model once outside the loop (weight loading is expensive).
Use identical parameters for every field so wells are comparable.

## Best practices

1. **Inspect first** — bit depth, dimensions, channel order before any processing.
2. **Match preprocessing to the defect** — CLAHE (contrast), Gaussian/median
   (noise), white-tophat (illumination); do not stack transforms blindly.
3. **QC segmentation visually** — overlay masks (`mark_boundaries`) on a few fields
   before batch-processing.
4. **Cellpose model choice** — `cyto2` whole-cell, `nuclei` nuclear; set an explicit
   `diameter` if auto-detection misfires.
5. **trackpy tuning** — odd `diameter`; `search_range` < inter-object spacing;
   `memory` for blinking; always `filter_stubs`.
6. **Colocalization controls** — single-stained controls; report Pearson *and*
   Manders (see `references/colocalization.md`).
7. **Batch consistency** — identical parameters across all images of an experiment.
8. **Record scale** — pixel size (µm/px) and frame interval from metadata; without
   them measurements are in pixels/frames only.

## Troubleshooting

| Problem | Fix |
|---|---|
| Cellpose over/under-segments | Set explicit `diameter`; raise `cellprob_threshold` to reduce false positives, lower to recover missed cells; adjust `flow_threshold`. |
| Touching objects not split by watershed | Lower `min_distance` in `peak_local_max`; try erosion before the distance transform; smooth the distance map. |
| trackpy links wrong particles | Lower `search_range`; raise `minmass` to drop dim features; check `diameter` is odd and correct. |
| Tracks fragment into many short pieces | Raise `memory` and/or `search_range`; then `filter_stubs`. |
| TIFF won't load / wrong dimensions | Use `tifffile.imread`; check `.shape`/`.dtype`; for multi-series/TCZYX use `aicsimageio.AICSImage`. |
| Colocalization values seem too high | Ensure background subtraction; verify threshold method; check bleed-through with single-stain controls; exclude saturated pixels. |
| Circularity > 1 for small objects | Filter out very small `area` before interpreting shape metrics (perimeter discretization artifact). |

## Resources

- Cellpose — https://cellpose.readthedocs.io/
- scikit-image — https://scikit-image.org/docs/stable/
- trackpy — http://soft-matter.github.io/trackpy/
- aicsimageio / bioio — https://allencellmodeling.github.io/aicsimageio/
