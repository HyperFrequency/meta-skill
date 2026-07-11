# Western-Blot Densitometry

Quantify protein-band intensity from a blot image, subtract background, and
report fold change normalized to a loading control. Assumes a conventional gel
layout: vertical lanes, horizontal bands, roughly uniform illumination.

## Pipeline

`load grayscale → orient (bands bright) → split lanes → detect bands →
integrate density → normalize to loading control → fold change`

## Load and orient

Densitometry needs bands to be the **bright** feature. Chemiluminescent film is
usually dark bands on a light background, so invert when the mean is bright.

```python
import numpy as np

def load_grayscale(path):
    """Return float64 image in [0, 1]. Uses OpenCV, falls back to scikit-image."""
    try:
        import cv2
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise FileNotFoundError(path)
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    except ImportError:
        from skimage.io import imread
        img = imread(path, as_gray=True)
    img = img.astype(np.float64)
    img = img / img.max() if img.max() > 0 else img
    if img.mean() > 0.5:                 # dark bands on light background
        img = 1.0 - img
    return img
```

Load 16-bit TIFFs with `IMREAD_UNCHANGED` — do **not** let an 8-bit read clip a
high-bit-depth scan.

## Lanes and bands

Equal-width lane splitting (with a small edge margin) is robust for most gels;
peak-based lane detection helps only for irregular loading. Within a lane, take
the vertical intensity profile, subtract a rolling-ball background, threshold,
and label contiguous runs as bands.

```python
from scipy.ndimage import minimum_filter1d, maximum_filter1d

def rolling_ball_1d(profile, radius):
    """Grayscale opening (erosion then dilation) as a background estimate."""
    return maximum_filter1d(minimum_filter1d(profile, radius), radius)

def lane_boundaries(img, n_lanes, margin_frac=0.05):
    w = img.shape[1]
    margin = int(w * margin_frac)
    lane_w = (w - 2 * margin) // n_lanes
    return [(margin + i * lane_w, min(margin + (i + 1) * lane_w, w))
            for i in range(n_lanes)]

def detect_bands(lane_img, min_height=5):
    profile = lane_img.mean(axis=1)
    bg = rolling_ball_1d(profile, max(len(profile) // 4, 10))
    corrected = np.clip(profile - bg, 0, None)
    binary = corrected > corrected.mean() + 0.5 * corrected.std()
    bands, start, inside = [], 0, False
    for i, on in enumerate(binary):
        if on and not inside:
            start, inside = i, True
        elif not on and inside:
            if i - start >= min_height:
                bands.append((start, i))
            inside = False
    if inside and len(binary) - start >= min_height:
        bands.append((start, len(binary)))
    return bands or [(0, lane_img.shape[0])]   # fallback: whole lane
```

## Integrated density and fold change

Integrated density = background-subtracted signal summed over the band ROI. Then
normalize each lane's target band to its loading-control band and express fold
change relative to a reference lane.

```python
def integrated_density(lane_img, y0, y1):
    roi = lane_img[y0:y1, :]
    prof = roi.mean(axis=1)
    corrected = np.clip(prof - rolling_ball_1d(prof, max(len(prof) // 3, 5)), 0, None)
    return float(corrected.sum() * roi.shape[1])

def fold_change(target_intensities, loading_control_intensities):
    target = np.asarray(target_intensities, float)
    control = np.asarray(loading_control_intensities, float)
    normalized = target / control          # per-lane loading correction
    return normalized / normalized[0]      # relative to reference lane
```

## Best practices and failure modes

- **Stay in the linear range.** Saturated (pure-white after inversion) bands
  under-report; re-image with shorter exposure. ECL film saturates easily —
  a CCD/CMOS imager with a documented linear range is preferable.
- **Prefer total-protein normalization.** A Ponceau S / stain-free total-protein
  measurement is more reliable than a single housekeeping band (β-actin, GAPDH),
  which can itself vary with treatment.
- **Inconsistent quantification** usually means uneven illumination or exposure
  across lanes — flat-field the image or re-acquire; do not paper over it with
  aggressive background subtraction.
- **Report fold change, not raw intensity.** Raw arbitrary units are not
  comparable across blots or exposures.
- The lane/band detector here is deliberately simple. For crowded, smiling, or
  overlapping bands, or for slide-scale imaging, use `bioimage-analysis`.
