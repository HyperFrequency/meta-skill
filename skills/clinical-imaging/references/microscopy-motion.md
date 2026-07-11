# 2D Microscopy and Motion: Optical Flow and Plaque Quantification

Displacement/strain fields and object morphometry from 2D image data. Uses
OpenCV (`cv2`) for optical flow and `scikit-image` for segmentation.

## 1. Tissue Deformation via Optical Flow

Quantify how tissue moves/strains between two consecutive grayscale frames.
Choose **dense** (Farneback) for a full strain field, **sparse** (Lucas–Kanade)
for tracking a few features.

### Dense field (Farneback) — strain, divergence, curl

```python
import cv2
import numpy as np

def dense_deformation(frame1, frame2):
    """frame1, frame2: consecutive uint8 grayscale frames. Displacements in px."""
    flow = cv2.calcOpticalFlowFarneback(
        frame1, frame2, None,
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
    )
    u, v = flow[..., 0], flow[..., 1]
    magnitude = np.hypot(u, v)

    du_dx = np.gradient(u, axis=1)
    du_dy = np.gradient(u, axis=0)
    dv_dx = np.gradient(v, axis=1)
    dv_dy = np.gradient(v, axis=0)

    return {
        "flow": flow,
        "magnitude": magnitude,
        "divergence": du_dx + dv_dy,        # >0 expansion, <0 contraction
        "curl": dv_dx - du_dy,              # rotation
        "strain_xx": du_dx,                 # infinitesimal strain tensor
        "strain_yy": dv_dy,
        "strain_xy": 0.5 * (du_dy + dv_dx),
    }
```

### Sparse tracking (Lucas–Kanade)

```python
def sparse_tracking(frame1, frame2, max_corners=500):
    """Track good features frame1 -> frame2. Returns per-point displacement."""
    pts = cv2.goodFeaturesToTrack(
        frame1, maxCorners=max_corners, qualityLevel=0.01, minDistance=10)
    if pts is None:
        return None
    new_pts, status, _ = cv2.calcOpticalFlowPyrLK(frame1, frame2, pts, None)
    ok = status.ravel() == 1
    old, new = pts[ok], new_pts[ok]
    dx = new[:, 0] - old[:, 0]
    dy = new[:, 1] - old[:, 1]
    return {
        "old_pts": old, "new_pts": new,
        "dx": dx, "dy": dy,
        "magnitude": np.hypot(dx, dy),
    }
```

**Notes**
- Displacements are in **pixels**; multiply by the calibrated pixel size for
  physical strain. Divergence/curl are per-pixel spatial derivatives.
- Farneback expects reasonably smooth intensity; denoise first if the frames are
  noisy. Feature tracking needs texture — it fails on smooth/uniform tissue.
- For a sequence, chain frame pairs and accumulate displacement, or track the
  same feature set across all frames.

## 2. Amyloid Plaque Quantification

Segment and measure amyloid plaques from fluorescence microscopy (Thioflavin-S,
Congo Red, or immunofluorescence). Returns per-plaque morphometrics plus a
summary.

```python
import numpy as np
import pandas as pd
from skimage.filters import gaussian, threshold_otsu, threshold_local
from skimage.measure import label, regionprops
from skimage.morphology import remove_small_objects
from skimage.segmentation import clear_border

def quantify_plaques(image, method="otsu", manual_threshold=None,
                     min_size=50, drop_border=True):
    """image: 2D (or take channel 0 of RGB). Returns (DataFrame, summary dict)."""
    if image.ndim == 3:
        image = image[..., 0]
    smoothed = gaussian(image, sigma=2)

    if method == "otsu":
        binary = smoothed > threshold_otsu(smoothed)
    elif method == "adaptive":                       # uneven illumination
        binary = smoothed > threshold_local(smoothed, block_size=51)
    elif method == "manual":
        binary = smoothed > manual_threshold
    else:
        raise ValueError(f"unknown method: {method}")

    cleaned = remove_small_objects(binary, min_size=min_size)
    if drop_border:
        cleaned = clear_border(cleaned)              # drop plaques clipped by FOV

    labels = label(cleaned)
    regions = regionprops(labels, intensity_image=image)
    rows = [{
        "label": r.label,
        "area_px": r.area,
        "perimeter": r.perimeter,
        "eccentricity": r.eccentricity,
        "mean_intensity": r.mean_intensity,
        "max_intensity": r.max_intensity,
        "centroid_y": r.centroid[0],
        "centroid_x": r.centroid[1],
    } for r in regions]
    df = pd.DataFrame(rows)

    total_px = image.shape[0] * image.shape[1]
    plaque_px = int(df["area_px"].sum()) if not df.empty else 0
    summary = {
        "plaque_count": len(df),
        "plaque_area_px": plaque_px,
        "plaque_area_fraction": plaque_px / total_px,
        "mean_plaque_area_px": float(df["area_px"].mean()) if not df.empty else 0.0,
        "density_per_Mpx": len(df) / (total_px / 1e6),
    }
    return df, summary
```

**Notes**
- `min_size` rejects noise specks; raise it if background dust is counted.
- Touching plaques are merged into one object — apply a distance-transform +
  watershed split before `regionprops` if separation matters.
- Convert `area_px` to µm² with the known pixel size before reporting; keep the
  raw pixel value too for reproducibility.
- `adaptive` (local) thresholding handles uneven illumination that Otsu fails on;
  `manual` is for reproducing a fixed lab protocol.
