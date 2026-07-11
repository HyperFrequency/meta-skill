# Immunophenotyping

Downstream of `flow-cytometry-analysis`. Multi-marker threshold gating that turns
a compensated, parent-gated event array into named immune populations with
parent-referenced frequencies.

## Panel schema

A panel maps each marker to the channel it is measured on and a positivity
threshold:

```json
{
  "CD3":  {"channel": "FL1-A", "threshold": 1000},
  "CD4":  {"channel": "FL2-A", "threshold": 500},
  "CD8":  {"channel": "FL3-A", "threshold": 800},
  "CD19": {"channel": "FL4-A", "threshold": 400}
}
```

Thresholds should be set from FMO controls, not guessed. An event is positive for
a marker when `value >= threshold`.

## Marker positivity

For each marker, compute a boolean column and per-marker stats (percent positive,
plus median intensity of the positive and negative fractions — a sanity check
that the threshold sits in the valley between populations).

```python
import numpy as np, pandas as pd

def marker_positivity(df, panel):
    positivity = pd.DataFrame(index=df.index)
    for marker, defn in panel.items():
        col = defn["channel"]
        positivity[marker] = df[col].values >= defn["threshold"]
    return positivity
```

## Population identification

Combine marker booleans into standard populations. Only populations whose markers
are all present in the panel are emitted. Frequencies are `% of parent` (the
parent being whatever gate produced `df` — e.g. singlet-gated lymphocytes).

| Population | Definition |
| --- | --- |
| CD3+ T cells | CD3+ |
| Helper T (exclusive) | CD3+ CD4+ CD8− |
| Cytotoxic T (exclusive) | CD3+ CD4− CD8+ |
| Double-negative T | CD3+ CD4− CD8− |
| Double-positive T | CD3+ CD4+ CD8+ |
| B cells | CD3− CD19+ |
| NK cells | CD3− CD56+ |
| Mature NK | CD3− CD16+ CD56+ |
| NKT cells | CD3+ CD56+ |
| Treg candidates | CD4+ CD25+ |
| Monocytes | CD3− CD14+ |

```python
def population_mask(positivity, criteria):
    mask = np.ones(len(positivity), dtype=bool)
    for marker, want_positive in criteria.items():
        col = positivity[marker].values
        mask &= col if want_positive else ~col
    return mask

helper_t = population_mask(positivity, {"CD3": True, "CD4": True, "CD8": False})
freq = 100 * helper_t.sum() / len(positivity)   # % of parent
```

For small panels (≤6 markers) you can additionally enumerate every marker
combination to surface unexpected co-expression, but the named table above is the
primary output.

## Quadrant / density plots

Two-marker relationships are shown as a 2-D density plot with threshold crosshairs
and the four quadrant percentages annotated.

```python
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

def quadrant_plot(df, m1, m2, panel, ax=None):
    ch1, ch2 = panel[m1]["channel"], panel[m2]["channel"]
    t1, t2 = panel[m1]["threshold"], panel[m2]["threshold"]
    x, y = df[ch1].values, df[ch2].values
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 6))
    ax.hist2d(x, y, bins=200, cmap="viridis", norm=LogNorm(), cmin=1)
    ax.axvline(t1, color="red", ls="--"); ax.axhline(t2, color="red", ls="--")
    n = len(x)
    for qx, qy, mx, my in [(x >= t1, y >= t2, 0.75, 0.95),
                           (x < t1,  y >= t2, 0.25, 0.95),
                           (x >= t1, y < t2,  0.75, 0.05),
                           (x < t1,  y < t2,  0.25, 0.05)]:
        pct = 100 * (qx & qy).sum() / n if n else 0
        ax.text(mx, my, f"{pct:.1f}%", transform=ax.transAxes, ha="center")
    ax.set_xlabel(f"{m1} ({ch1})"); ax.set_ylabel(f"{m2} ({ch2})")
    return ax
```

Subsample to ~50k events before density estimation on large files to keep
plotting fast.

## `immunophenotype` CLI

Reference spec — build the script from the functions above; no `.py` file ships
with the skill.

```bash
python immunophenotype.py --fcs pbmc.fcs \
    --panel panel.json \
    --parent-gate '{"FSC-A": [40000, 180000], "SSC-A": [5000, 80000]}' \
    --output-dir lymphocytes/
```

| Flag | Meaning |
| --- | --- |
| `--fcs` | Path to the FCS file (required). |
| `--panel` | JSON string or file: `{"Marker": {"channel": ..., "threshold": ...}}`. Markers whose channel is absent are dropped with a warning. |
| `--parent-gate` | Optional rectangular FSC/SSC gate `{"channel": [low, high]}` applied before marker gating (selects lymphocytes). |
| `--output-dir` | Destination (default `immunophenotype_output`). |

Outputs: `marker_positivity.csv` (per-marker % positive + medians),
`population_frequencies.csv` (named populations, counts, `% parent`),
`phenotyped_events.csv` (events plus boolean marker columns), and
`density_<m1>_vs_<m2>.png` plots for marker pairs.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| A named population shows 0% | Required marker missing from the panel, or its threshold is on the wrong side of the valley — check `median_positive`/`median_negative`. |
| Frequencies do not sum sensibly | You changed parent gates between markers. Keep one parent and report every frequency against it. |
| Positive fraction implausibly high/low | Data not compensated, or threshold set without an FMO control. Compensate first (see gating reference). |
| Rare population unreliable | Fewer than ~100 events in the gate — collect more events or widen the parent. |
