# Time-Lapse Tracking Reference (trackpy)

trackpy detects bright features per frame, links them into trajectories across
frames, filters spurious tracks, then computes motion statistics. Input is a
time-lapse stack shaped `(T, Y, X)` (e.g. `tifffile.imread("timelapse.tif")`) or
an iterable of frames.

## Pipeline

```python
import trackpy as tp
import pandas as pd, numpy as np

frames = tifffile.imread("timelapse.tif")            # (T, Y, X)

# 1. Detect features in every frame at once (adds a 'frame' column).
feats = tp.batch(frames, diameter=11, minmass=1000)  # diameter MUST be odd

# 2. Link detections into trajectories (assigns a 'particle' id).
tracks = tp.link(feats, search_range=15, memory=3)

# 3. Drop short spurious tracks.
tracks = tp.filter_stubs(tracks, threshold=10)
print(f"{tracks['particle'].nunique()} tracks over {len(frames)} frames")
```

`tp.locate(frame, ...)` does one frame; `tp.batch(frames, ...)` loops all frames
and is the usual entry point. The result is a tidy DataFrame with at least
`x`, `y`, `mass`, `size`, `frame`, and (after linking) `particle`.

## Key parameters

| Parameter | Meaning | Failure if wrong |
|---|---|---|
| `diameter` (locate/batch) | expected feature size in px; **odd integer** | wrong size → missed or merged features |
| `minmass` (locate/batch) | minimum integrated brightness | too low → noise detected; too high → dim cells lost |
| `search_range` (link) | max displacement between consecutive frames | too large → cross-links between objects; too small → broken tracks |
| `memory` (link) | frames a feature may vanish and still relink | handles blinking/occlusion; too large → wrong relinks |
| `threshold` (filter_stubs) | minimum track length in frames | removes short spurious trajectories |

Rule of thumb: set `search_range` **below the typical inter-object spacing**, and
raise `minmass` until only real objects survive `tp.locate` on a single frame.

## Motion statistics

### Per-track velocity and directionality

Scale by pixel size (µm/px) and frame interval to get physical units.

```python
pixel_size = 0.65      # µm/px
dt = 5                 # minutes per frame

rows = []
for pid, g in tracks.groupby("particle"):
    g = g.sort_values("frame")
    dx = np.diff(g["x"].to_numpy()) * pixel_size
    dy = np.diff(g["y"].to_numpy()) * pixel_size
    step = np.hypot(dx, dy)                              # per-frame distance (µm)
    path_len = step.sum()
    net_disp = np.hypot(g["x"].iloc[-1] - g["x"].iloc[0],
                        g["y"].iloc[-1] - g["y"].iloc[0]) * pixel_size
    rows.append({
        "particle": pid,
        "mean_speed": step.mean() / dt,                 # µm/min
        "max_speed": step.max() / dt,
        "net_displacement": net_disp,
        "directionality": net_disp / path_len if path_len else 0.0,  # 1=straight
        "n_frames": len(g),
    })
vel = pd.DataFrame(rows)
```

`directionality` (net displacement / path length) is 1 for perfectly straight
migration and near 0 for confined/random motion.

### Mean squared displacement (MSD)

```python
em = tp.emsd(tracks, mpp=0.65, fps=1/300)   # ensemble MSD; mpp=µm/px, fps=1/sec
im = tp.imsd(tracks, mpp=0.65, fps=1/300)    # per-particle MSD
```

`mpp` is microns-per-pixel and `fps` is frames-per-second (use `1/seconds_per_frame`).
The log-log slope of MSD vs lag time diagnoses motion type: slope ≈ 1 diffusive,
> 1 directed/super-diffusive, < 1 sub-diffusive/confined.

## Drift subtraction

Stage or flow drift inflates apparent motility. Estimate and remove ensemble drift
before computing per-cell statistics:

```python
drift = tp.compute_drift(tracks)
tracks = tp.subtract_drift(tracks.copy(), drift)
```

## Gotchas

- **Odd `diameter`.** A non-odd value raises; pick the smallest odd size that
  covers a typical object.
- **Broken vs cross-linked tracks.** If one object yields many short tracks, raise
  `memory` or `search_range`; if two objects share a track, lower `search_range`.
- **Always `filter_stubs`.** Single- or double-frame "tracks" are almost always
  detection noise and skew velocity/MSD.
- **Physical units.** Everything is in px/frame until you multiply by pixel size
  and frame interval — read both from microscope metadata.
