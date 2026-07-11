# Morphology & Intensity Quantification Reference

Once you have a label mask, `skimage.measure.regionprops_table` turns it (plus an
intensity image) into a tidy per-object DataFrame. This is the workhorse for every
counting/shape/intensity task.

## regionprops_table

```python
import skimage.measure
import pandas as pd, numpy as np

props = skimage.measure.regionprops_table(
    masks, intensity_image=image,
    properties=[
        "label", "area", "perimeter", "eccentricity", "solidity",
        "major_axis_length", "minor_axis_length", "orientation",
        "mean_intensity", "max_intensity", "min_intensity", "centroid",
    ])
df = pd.DataFrame(props)
```

`regionprops(masks, intensity_image=...)` returns per-object objects instead of a
column dict; `regionprops_table` is preferred for building DataFrames.

### Commonly used properties

| Property | Meaning |
|---|---|
| `label` | integer id (matches the mask value) |
| `area` | pixel count of the object |
| `perimeter` | boundary length (px) |
| `eccentricity` | 0 = circle, → 1 = elongated ellipse |
| `solidity` | area / convex-hull area (concavity/roughness) |
| `major_axis_length`, `minor_axis_length` | fitted-ellipse axes |
| `orientation` | angle of the major axis (radians) |
| `euler_number` | connectivity (holes/branches); useful for networks |
| `mean_intensity`, `max_intensity`, `min_intensity` | require `intensity_image` |
| `centroid` | expands to `centroid-0` (row), `centroid-1` (col) |

Multi-value properties expand into indexed columns (`centroid-0`, `centroid-1`).
Intensity properties require passing `intensity_image`.

### Derived shape metrics

```python
df["circularity"] = 4 * np.pi * df["area"] / (df["perimeter"] ** 2)   # 1 = perfect circle
df["aspect_ratio"] = df["major_axis_length"] / (df["minor_axis_length"] + 1e-6)
```

Circularity above ~1 can occur for tiny objects due to perimeter discretization —
filter out very small `area` before interpreting shape descriptors.

## Object counting

`masks.max()` equals the number of objects only when labels are contiguous
`1..N` (Cellpose and `skimage.measure.label` both guarantee this). Otherwise count
with `len(np.unique(masks)) - 1` (subtracting background 0), or `len(df)`.

## Fiber / cytoskeleton orientation

Characterize alignment of filamentous structures (actin, collagen, microtubules)
via edge detection + a Hough line transform, then reduce to an alignment order
parameter.

```python
import skimage.feature, skimage.transform

edges = skimage.feature.canny(image, sigma=2)
angles = np.linspace(-np.pi / 2, np.pi / 2, 180, endpoint=False)
h, theta, d = skimage.transform.hough_line(edges, theta=angles)
_, peak_angles, _ = skimage.transform.hough_line_peaks(h, theta, d, num_peaks=50)

deg = np.degrees(peak_angles)
order_parameter = np.mean(np.cos(2 * np.radians(deg)))   # relative to mean axis
print(f"mean {deg.mean():.1f}±{deg.std():.1f}°, order S≈{order_parameter:.3f}")
```

Order parameter interpretation: `S ≈ 1` strongly aligned, `S ≈ 0` random/isotropic.
For a direction-independent measure, compute `S` about the mean orientation
(subtract the mean angle before the `cos(2θ)` step) rather than the lab axis.

## Mitochondrial morphology (JC-1 / TMRM)

JC-1 forms red aggregates in polarized (healthy) mitochondria and green monomers
when depolarized; the red/green ratio proxies membrane potential.

```python
red = skimage.io.imread("jc1_red.tif").astype(float)
green = skimage.io.imread("jc1_green.tif").astype(float)

ratio = red / (green + 1e-6)                              # avoid divide-by-zero
mean_ratio = ratio[ratio > 0].mean()

mito = green > skimage.filters.threshold_otsu(green)      # segment from monomer ch
labels = skimage.measure.label(mito)
m = pd.DataFrame(skimage.measure.regionprops_table(
    labels, properties=["label", "area", "major_axis_length",
                        "minor_axis_length", "eccentricity", "euler_number"]))
m["aspect_ratio"] = m["major_axis_length"] / (m["minor_axis_length"] + 1e-6)
m["shape"] = pd.cut(m["aspect_ratio"], bins=[0, 2, 4, np.inf],
                    labels=["round", "intermediate", "elongated"])
print(mean_ratio, m["shape"].value_counts().to_dict())
```

`euler_number` on the mitochondrial mask hints at network connectivity
(fragmented punctate vs. fused tubular networks).

## Handoff

The DataFrame is the deliverable. Send it to `statistical-analysis` /
`statsmodels` for group comparisons, `scikit-learn` to classify phenotypes, or
`seaborn`/`matplotlib` for distributions. Always attach the pixel size (µm/px) so
`area`/lengths convert to physical units downstream.
