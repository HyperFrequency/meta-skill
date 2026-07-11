# Gating and Compensation

Downstream of `flow-cytometry-analysis`. Covers loading events, spectral
compensation, manual/automated gating, and the `gate_fcs` CLI.

## Loading events with flowio

`flowio.FlowData` exposes a flat `events` list plus metadata. Reshape to a 2-D
array and pull channel labels from `pnn_labels` (`$PnN` detector names) and
`pns_labels` (`$PnS` stain names). Some instruments leave `$PnS` blank, so fall
back to the detector name.

```python
import flowio, numpy as np

fcs = flowio.FlowData("sample.fcs")
n_channels = int(fcs.channel_count)
events = np.reshape(fcs.events, (-1, n_channels)).astype(np.float64)

# Prefer stain name, fall back to detector name (keys in fcs.text are the
# lowercased FCS TEXT keywords, e.g. "p1n", "p1s").
channels = []
for i in range(1, n_channels + 1):
    stain = fcs.text.get(f"p{i}s", "").strip()
    name = fcs.text.get(f"p{i}n", f"Ch{i}").strip()
    channels.append(stain or name)
```

`fcs.pnn_labels` / `fcs.pns_labels` return the same lists directly if you do not
need the fallback logic.

## Compensation

Fluorescence spillover is corrected by multiplying the fluorescence columns by
the inverse of the square spillover matrix. The matrix is stored in the FCS TEXT
segment under the `$SPILLOVER` (FCS 3.1) or `SPILL` (FCS 3.0) keyword, or supplied
as an external CSV from the acquisition software.

### Parsing the in-file spillover keyword

The keyword value is a comma-separated string: first the integer `n`, then the
`n` channel names, then the `n×n` matrix in row-major order.

```python
import numpy as np

def parse_spillover(spill_string):
    parts = spill_string.split(",")
    n = int(parts[0])
    comp_channels = parts[1 : n + 1]
    values = [float(x) for x in parts[n + 1:]]
    matrix = np.array(values).reshape(n, n)
    return comp_channels, matrix

spill_string = fcs.text.get("spillover") or fcs.text.get("spill") or ""
```

### Applying compensation

Compensate only the fluorescence columns; leave scatter (FSC/SSC) and Time
untouched. With the spillover matrix parsed row-major (row = source fluorochrome,
column = detector) as below, compensation is `compensated = fluoro @ inv(matrix)`.

```python
def compensate(events, fluoro_indices, spillover_matrix):
    inv_spill = np.linalg.inv(spillover_matrix)          # raises LinAlgError if singular
    out = events.copy()
    out[:, fluoro_indices] = events[:, fluoro_indices] @ inv_spill
    return out

comp_channels, spill = parse_spillover(spill_string)
fluoro_idx = [channels.index(c) for c in comp_channels]
events_comp = compensate(events, fluoro_idx, spill)
```

Negative values after compensation are **expected and correct** — do not clip
them. Use a biexponential/logicle transform for display only.

## Manual gating

### Rectangular gate (one channel)

```python
def rect_gate(events, ch_idx, lo, hi):
    col = events[:, ch_idx]
    return (col >= lo) & (col <= hi)
```

### Polygon gate (two channels, ray casting)

```python
from matplotlib.path import Path

def polygon_gate(events, x_idx, y_idx, vertices):
    points = np.column_stack([events[:, x_idx], events[:, y_idx]])
    return Path(vertices).contains_points(points)
```

### Singlet / doublet exclusion

Doublets have an inflated area relative to height. Keep events whose FSC-A/FSC-H
ratio sits near 1.0 (a `+1` guards against divide-by-zero):

```python
fsc_a, fsc_h = channels.index("FSC-A"), channels.index("FSC-H")
ratio = events[:, fsc_a] / (events[:, fsc_h] + 1)
singlets = (ratio > 0.8) & (ratio < 1.2)
```

### Sequential hierarchy

Combine gates with `&` in order and record `% parent` / `% total` at each node:

```python
scatter = rect_gate(events, fsc_a, 30000, 250000) & rect_gate(events, ssc_a, 5000, 200000)
singlet = scatter & ((events[:, fsc_a] / (events[:, fsc_h] + 1) > 0.8) &
                     (events[:, fsc_a] / (events[:, fsc_h] + 1) < 1.2))
# live = singlet & rect_gate(events, viability_idx, 0, dead_threshold)
```

## Automated gating (Gaussian Mixture Model)

Unsupervised gating fits a `sklearn.mixture.GaussianMixture` to log-transformed
channels and labels each event by component. Order the components by summed mean
intensity so the assignment is reproducible.

```python
from sklearn.mixture import GaussianMixture

def auto_gate_gmm(events, channel_indices, n_components=2, random_state=42):
    data = np.log1p(np.clip(events[:, channel_indices], 0, None))
    gmm = GaussianMixture(n_components=n_components, random_state=random_state)
    labels = gmm.fit_predict(data)
    order = np.argsort(gmm.means_.sum(axis=1))   # dimmest → brightest component
    return labels, gmm, order

labels, gmm, order = auto_gate_gmm(events, [fsc_a, ssc_a], n_components=3)
lymphocytes = labels == order[1]   # middle scatter cluster is typically lymphocytes
```

## `gate_fcs` CLI

A reproducible loader + sequential rectangular gater that emits CSVs. This is a
reference spec — assemble the script from the functions above; no `.py` file ships
with the skill.

```bash
python gate_fcs.py --fcs sample.fcs \
    --gates '{"FSC-A": [30000, 250000], "SSC-A": [5000, 200000], "FL1-A": [500, 100000]}' \
    --compensation-matrix spillover.csv \
    --output-dir gated/
```

| Flag | Meaning |
| --- | --- |
| `--fcs` | Path to the FCS file (required). |
| `--gates` | JSON string **or** path to a JSON file: `{"channel": [low, high], ...}`. Gates apply sequentially in insertion order. Validated: each bound is `[lo, hi]` with `lo < hi`. |
| `--compensation-matrix` | Optional CSV spillover matrix; must be square and non-singular. Scatter/Time channels are auto-excluded when inferring which columns to compensate. |
| `--output-dir` | Destination (default `gated_output`). |

Outputs: `gated_events.csv` (surviving events), `gate_statistics.csv`
(per-gate events-in/out, `% parent`, `% total`).

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Compensation yields many negatives | Normal. Do not clip; display with biexponential/logicle. |
| `LinAlgError: singular matrix` | Spillover matrix is not invertible — re-export it, or drop a fully collinear channel. |
| GMM splits one population in two | Lower `n_components`; pre-gate obvious debris; ensure the log transform is applied before fitting. |
| Channel name lookup fails | Check both `pnn_labels` (short) and `pns_labels` (stain) — naming differs by instrument. Match case-insensitively if needed. |
| Everything gated out | A `[low, high]` bound is on the wrong scale for the data range; inspect `events[:, idx].min()/.max()` first. |
