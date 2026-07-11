# Functional Assays

Downstream of `flow-cytometry-analysis`. Covers three quantitative readouts:
CFSE/CellTrace proliferation, Dean-Jett-Fox cell-cycle phasing, and Annexin V/PI
apoptosis. Run these on singlet-gated, viable events. The `cfse_proliferation`
and `cell_cycle` CLI blocks below are reference specs to assemble from the
functions shown; no `.py` files ship with the skill.

---

## CFSE / CellTrace proliferation

Each cell division splits the tracking dye roughly in half, so on a log10 scale
generations appear as evenly spaced peaks separated by log10(2) ≈ 0.301.
Generation 0 (undivided) is the brightest, right-most peak.

### Pipeline

1. Drop non-positive values, then `log10`-transform the dye channel.
2. Histogram (≈512 bins), smooth, and `scipy.signal.find_peaks` with a minimum
   inter-peak distance derived from the expected log10(2) spacing.
3. Assign generation 0 to the brightest peak; accept a dimmer peak as generation
   *k* only if its offset from gen-0 is within ~40% of `k · log10(2)`.
4. Assign every event to the nearest generation using midpoint boundaries between
   adjacent peaks.
5. Back-calculate precursors: a generation-*i* cell descends from `count / 2**i`
   original precursors.

### Metrics

Let `count[i]` be the events in generation *i* and `prec[i] = count[i] / 2**i`.

| Metric | Definition |
| --- | --- |
| **Division Index** | Average divisions across the *whole* starting population: `(Σ i·prec[i]) / (Σ prec[i])`. |
| **Proliferation Index** | Average divisions among *responding* cells only: `(Σ i·prec[i]) / (Σ_{i>0} prec[i])`. |
| **Percent Divided** | Fraction of precursors that divided at least once: `100 · (Σ prec[i] − prec[0]) / Σ prec[i]`. |

```python
def proliferation_metrics(generation_counts):
    prec = {i: c / (2 ** i) for i, c in generation_counts.items()}
    total_prec = sum(prec.values())
    responding_prec = total_prec - prec.get(0, 0)
    total_divisions = sum(i * p for i, p in prec.items())   # each gen-i precursor divided i times
    return {
        "division_index": total_divisions / total_prec if total_prec else 0.0,
        "proliferation_index": total_divisions / responding_prec if responding_prec else 0.0,
        "percent_divided": 100 * responding_prec / total_prec if total_prec else 0.0,
    }
```

### `cfse_proliferation` CLI

```bash
python cfse_proliferation.py --fcs stimulated.fcs \
    --cfse-channel "FITC-A" --max-generations 8 --output-dir proliferation/
```

| Flag | Meaning |
| --- | --- |
| `--fcs` | FCS file or CSV export (required). |
| `--cfse-channel` | Channel name (e.g. `FITC-A`, `BV421-A` for CellTrace Violet) or a column index. |
| `--max-generations` | Cap on generations to detect (default 8). |
| `--output-dir` | Destination (default `cfse_output`). |

Outputs: `generation_counts.csv`, `proliferation_metrics.csv`, and a labeled
histogram PNG.

---

## Cell cycle (Dean-Jett-Fox)

Quantifies G0/G1, S, and G2/M fractions from a DNA-content histogram (PI, DAPI,
or 7-AAD). The model is a sum of:

- **G0/G1**: Gaussian at `g1_mean`.
- **G2/M**: Gaussian at `g2_mean ≈ 2 · g1_mean` (cells have doubled their DNA).
- **S phase**: a broadened distribution between the two peaks (here a truncated
  linear term), representing intermediate DNA content.

```python
import numpy as np

def dean_jett_fox(x, g1_mean, g1_sigma, g1_amp,
                  g2_mean, g2_sigma, g2_amp, s_amp, s_slope):
    g1 = g1_amp * np.exp(-0.5 * ((x - g1_mean) / g1_sigma) ** 2)
    g2 = g2_amp * np.exp(-0.5 * ((x - g2_mean) / g2_sigma) ** 2)
    s = np.zeros_like(x)
    left, right = g1_mean + g1_sigma, g2_mean - g2_sigma
    if right > left:
        m = (x >= left) & (x <= right)
        t = (x[m] - left) / (right - left)          # 0 → 1 across S region
        s[m] = s_amp * (1.0 + s_slope * (t - 0.5))
    return g1 + g2 + s
```

Fitting workflow: filter 1st/99th-percentile outliers, histogram (256 bins),
seed `g1_mean` from the tallest peak and `g2_mean = 2·g1_mean` via
`find_peaks`, then `scipy.optimize.curve_fit` with bounds keeping both sigmas
positive and means inside the data range. Phase fractions are the integrated
areas of the three component curves, normalized to sum to 100%.

**Quality gates:** always singlet-gate on DNA-area vs DNA-width first — doublets
of G0/G1 cells land under the G2/M peak and inflate it. A healthy fit has a
G2/G1 mean ratio near 2.0 and a low coefficient of variation on the G1 peak.

### `cell_cycle` CLI

```bash
python cell_cycle.py --fcs pi_stained.fcs --dna-channel "PI-A" --output-dir cell_cycle/
```

| Flag | Meaning |
| --- | --- |
| `--fcs` | FCS file or CSV (required). |
| `--dna-channel` | DNA channel name (e.g. `PI-A`, `FL2-A`) or column index. |
| `--output-dir` | Destination (default `cell_cycle_output`). |

Outputs: `cell_cycle_results.csv` (G0/G1, S, G2/M %), `model_parameters.csv`
(fitted params, G2/G1 ratio, convergence flag), and a histogram PNG with the
fitted components shaded. If `curve_fit` fails to converge it falls back to the
initial estimates and flags `converged = False`.

---

## Apoptosis (Annexin V / PI)

Two thresholds partition events into four states. Annexin V binds externalized
phosphatidylserine (early apoptosis); PI enters only membrane-compromised cells.

| Quadrant | Annexin V | PI | State |
| --- | --- | --- | --- |
| LL | − | − | Viable |
| LR | + | − | Early apoptotic |
| UR | + | + | Late apoptotic |
| UL | − | + | Necrotic |

```python
import numpy as np

def annexin_pi_quadrants(events, annexin_idx, pi_idx,
                         annexin_thr, pi_thr, parent_mask=None):
    if parent_mask is None:
        parent_mask = np.ones(len(events), dtype=bool)
    g = events[parent_mask]
    total = len(g)
    ann = g[:, annexin_idx] > annexin_thr
    pi = g[:, pi_idx] > pi_thr
    q = {
        "viable":          (~ann) & (~pi),
        "early_apoptotic":  ann  & (~pi),
        "late_apoptotic":   ann  &  pi,
        "necrotic":        (~ann) &  pi,
    }
    return {k: 100 * m.sum() / total if total else 0.0 for k, m in q.items()}
```

Set thresholds from an unstained/single-stain control. Report each quadrant as a
percent of the viable-gated parent. Combine early + late for a total apoptotic
fraction.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| CFSE peaks unresolved | Increase histogram bins; later generations (>4–5) often merge — focus on early divisions. Confirm labeling concentration. |
| No CFSE peaks detected | Wrong channel, or dye already fully diluted. Verify the channel and that gen-0 is on-scale. |
| Cell-cycle fit fails / G2/G1 ≠ 2 | Doublet contamination — singlet-gate on DNA-area vs DNA-width. Check PI staining is not under/over-saturated. |
| S phase implausibly large | G2/M doublets counted as S, or a poor initial `g2_mean` seed. Re-gate singlets and re-seed peaks. |
| Apoptosis quadrants shifted | Data uncompensated (Annexin↔PI spillover) or thresholds set without controls. Compensate and use single-stain controls. |
