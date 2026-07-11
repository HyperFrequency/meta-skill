# Imaging Assays

IHC H-scoring, immune-cell migration kinematics, and cell-cycle phase-duration
estimation. Depends on `scikit-image` (and `trackpy` for tracking).

## 1. IHC Quantification (H-score)

Chromogenic IHC stains an antigen brown (DAB) or red (AEC) over a blue
hematoxylin counterstain. **Color deconvolution** unmixes the stains far better
than thresholding the raw RGB, because DAB and hematoxylin overlap in every RGB
channel. `skimage.color.rgb2hed` applies the Ruifrok & Johnston stain matrix to
recover Hematoxylin / Eosin / DAB channels.

```python
import numpy as np
import skimage.io
from skimage.color import rgb2hed

def quantify_ihc(image_path,
                 tissue_thresh=0.05,          # hematoxylin cutoff for "tissue"
                 bins=(0.10, 0.20, 0.40)):    # weak / moderate / strong DAB
    image = skimage.io.imread(image_path)
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError("IHC quantification needs an RGB image")

    hed = rgb2hed(image[..., :3])
    hematoxylin, dab = hed[..., 0], hed[..., 2]   # channel 2 is DAB

    tissue = hematoxylin > tissue_thresh          # ignore glass/background
    dab_t = dab[tissue]
    total = dab_t.size
    if total == 0:
        raise ValueError("no tissue detected; lower tissue_thresh")

    w1, w2, w3 = bins
    negative = (dab_t < w1).sum()
    weak     = ((dab_t >= w1) & (dab_t < w2)).sum()
    moderate = ((dab_t >= w2) & (dab_t < w3)).sum()
    strong   = (dab_t >= w3).sum()

    # H-score = 1*%weak + 2*%moderate + 3*%strong, range 0-300
    h_score = (1 * weak + 2 * moderate + 3 * strong) / total * 100
    positive_pct = 100 * (weak + moderate + strong) / total
    return {
        "h_score": float(h_score),
        "positive_pct": float(positive_pct),
        "negative_pct": float(100 * negative / total),
        "weak_pct": float(100 * weak / total),
        "moderate_pct": float(100 * moderate / total),
        "strong_pct": float(100 * strong / total),
    }
```

Practical points:
- **AEC** sections: AEC also lands on the DAB axis of the HED decomposition in
  practice, but if separation is poor supply custom stain vectors via
  `skimage.color.separate_stains` with an AEC/hematoxylin matrix.
- The intensity `bins` are **assay-specific** — calibrate them on control
  tissue with a known 1+/2+/3+ pathologist call before trusting absolute
  H-scores across batches.
- H-score answers "how much and how strong"; if you only need
  percent-positive-nuclei (e.g. Ki-67 index) use `positive_pct` and consider
  restricting to a nuclear mask.

Failure modes: grayscale or CMYK input (convert to RGB first); non-standard
chromogens (supply the correct stain matrix); uneven illumination (flat-field
correct before deconvolution).

## 2. Immune-Cell Tracking Kinematics

Given per-frame cell positions, compute migration metrics. Positions can come
from any segmentation + linking pipeline; `trackpy` (`trackpy.locate` +
`trackpy.link`) is the usual source and yields a tidy
`[particle, frame, x, y]` table.

```python
import numpy as np
import pandas as pd

def track_kinematics(tracks_df, pixel_size_um=0.65, frame_interval_min=1.0,
                     min_frames=10, max_msd_lag=20):
    """tracks_df: columns [particle, frame, x, y] in pixels/frames."""
    rows = []
    for pid, tr in tracks_df.groupby("particle"):
        tr = tr.sort_values("frame")
        if len(tr) < min_frames:
            continue                                   # reject short artifacts
        x = tr["x"].to_numpy() * pixel_size_um
        y = tr["y"].to_numpy() * pixel_size_um
        t = tr["frame"].to_numpy() * frame_interval_min

        dx, dy, dt = np.diff(x), np.diff(y), np.diff(t)
        step = np.hypot(dx, dy)
        speeds = step / dt
        path_length = step.sum()
        displacement = np.hypot(x[-1] - x[0], y[-1] - y[0])
        confinement = displacement / path_length if path_length > 0 else 0.0

        msd = [np.mean((x[k:] - x[:-k]) ** 2 + (y[k:] - y[:-k]) ** 2)
               for k in range(1, min(len(x), max_msd_lag))]

        rows.append({
            "particle": pid,
            "mean_speed": float(speeds.mean()),
            "max_speed": float(speeds.max()),
            "displacement": float(displacement),
            "path_length": float(path_length),
            "confinement_ratio": float(confinement),
            "duration_min": float(t[-1] - t[0]),
            "n_frames": int(len(tr)),
            "msd": msd,
        })
    df = pd.DataFrame(rows)

    # simple phenotype call from confinement ratio (directional persistence)
    df["phenotype"] = "confined"
    df.loc[df["confinement_ratio"] > 0.5, "phenotype"] = "directed"
    df.loc[df["confinement_ratio"].between(0.2, 0.5, inclusive="right"),
           "phenotype"] = "random_walk"
    return df
```

Interpretation:
- **Confinement ratio** = net displacement / total path length ∈ [0, 1]. Near 1
  = directed/persistent migration; near 0 = confined or oscillating.
- **MSD vs lag**: linear slope ⇒ diffusive/random; super-linear (upward curve)
  ⇒ directed motility.
- **Under-flow leukocyte assays** map naturally onto behavior categories —
  arrest (near-zero speed), rolling (moving with the flow axis, low confinement
  transverse to it), crawling (persistent, often against flow), and diapedesis
  (loss of the tracked object as it transmigrates). Resolve these by combining
  speed thresholds with the flow-axis component of displacement.
- Choose `min_frames` to your frame rate — too low admits segmentation flicker,
  too high discards genuinely fast/transient cells.

## 3. Cell-Cycle Phase Duration (approximate)

Dual-nucleoside pulse labeling (e.g. sequential IdU/CldU) lets you estimate
phase lengths from labeled fractions over time. This is a **coarse** estimate —
treat it as an order-of-magnitude sanity check, not a definitive measurement.

```python
import numpy as np

def estimate_phase_durations(labeled_fractions, pulse_interval_hours,
                             total_cycle_time=None):
    """labeled_fractions: {timepoint_hours: fraction_labeled}."""
    times = sorted(labeled_fractions)
    fr = [labeled_fractions[t] for t in times]

    if total_cycle_time is None:            # rough Tc from labeling kinetics
        if len(fr) > 1:
            rate = (fr[-1] - fr[0]) / (times[-1] - times[0])
            total_cycle_time = 1 / rate if rate > 0 else 24.0
        else:
            total_cycle_time = 24.0

    s_phase = fr[0] * total_cycle_time      # labeling index * cycle length
    g2m = pulse_interval_hours              # label -> mitosis transit
    g1 = max(total_cycle_time - s_phase - g2m, 0.0)
    return {"total_cycle": total_cycle_time, "G1": g1, "S": s_phase, "G2_M": g2m}
```

Caveats: assumes an asynchronous, exponentially growing population and steady
state; the G2/M estimate is only as good as your knowledge of the label-to-
mitosis transit time; use a proper percent-labeled-mitoses (PLM) or FUCCI
time-lapse method when precision matters.
