# Quality Metrics Reference

Quality metrics quantify how well each sorted unit represents a single neuron.
They fall into four questions:

| Category | Question | Key metrics |
|---|---|---|
| Contamination (Type I) | Are spikes from >1 neuron? | ISI-violations, SNR, isolation distance, L-ratio, d-prime |
| Completeness (Type II) | Are we missing spikes? | amplitude cutoff, presence ratio |
| Stability | Is the unit stable over time? | drift metrics, amplitude CV |
| Isolation | Is the cluster separable? | silhouette, nearest-neighbor hit/miss |

## The SortingAnalyzer

Everything downstream of sorting flows through a `SortingAnalyzer` created from a
`Sorting` + `Recording` pair. Use `sparse=True` at high channel counts.

```python
import spikeinterface.full as si

analyzer = si.create_sorting_analyzer(sorting, recording, sparse=True,
                                      format="binary_folder", folder="analyzer/")
```

### Extensions (compute in dependency order)

Passing a list resolves the order automatically:

```python
analyzer.compute([
    "random_spikes",          # subsample spikes for waveform extraction
    "waveforms",              # per-spike snippets
    "templates",              # mean/std waveform per unit
    "noise_levels",           # channel noise (SNR denominator)
    "spike_amplitudes",       # amplitude per spike (drift/cutoff)
    "correlograms",           # auto/cross-correlograms (refractory gap)
    "unit_locations",         # estimated unit position
    "principal_components",   # REQUIRED for isolation-quality metrics
    "quality_metrics",
])

qm = analyzer.get_extension("quality_metrics").get_data()   # DataFrame, one row per unit
analyzer.save_as(folder="analyzer_saved/", format="binary_folder")
```

Compute a chosen subset:

```python
analyzer.compute("quality_metrics", metric_names=[
    "firing_rate", "snr", "isi_violations_ratio", "presence_ratio", "amplitude_cutoff"])
```

## Metric definitions and thresholds

### Contamination

**ISI-violations ratio** — fraction of spikes inside the ~1.5 ms refractory
period. `analyzer.compute("quality_metrics", metric_names=["isi_violations_ratio"], isi_threshold_ms=1.5)`

| Value | Meaning |
|---|---|
| < 0.01 | excellent single unit |
| 0.01–0.1 | minor contamination |
| 0.1–0.5 | likely multi-unit |
| > 0.5 | poor / MUA |

**SNR** — peak template amplitude / background noise.

| Value | Meaning |
|---|---|
| > 10 | excellent |
| 5–10 | good |
| 2–5 | acceptable |
| < 2 | probably noise |

**Isolation distance** (Mahalanobis, needs PCA): > 50 well-isolated, 20–50
moderate, < 20 poor. **L-ratio:** < 0.05 clean. **d-prime:** > 8 excellent
separation, < 5 poor.

### Completeness

**Amplitude cutoff** — estimated fraction of spikes below the detection
threshold. `peak_sign="neg"` for typical negative spikes.

| Value | Meaning |
|---|---|
| < 0.01 | nearly complete (use for precise-timing analyses) |
| 0.01–0.1 | good |
| > 0.2 | many missed spikes |

**Presence ratio** — fraction of recording bins containing spikes
(`bin_duration_s=60`). > 0.99 excellent, 0.9–0.99 good, < 0.8 the unit likely
drifted out.

### Stability

**Drift metrics** (`drift_ptp`, `drift_std`, `drift_mad`, µm): `drift_ptp < 40`
is good. **Amplitude CV:** < 0.25 very stable, > 0.5 unstable (drift or
contamination).

### Isolation / cluster quality

**Silhouette:** > 0.5 well-defined. **Nearest-neighbor:** `nn_hit_rate > 0.9`
and `nn_miss_rate < 0.1` (both need PCA).

## Standard filter criteria

Curation is a query over the metrics DataFrame — pick a published standard or set
your own and **document it**.

```python
# Allen Institute (conservative default)
allen = qm.query("presence_ratio > 0.95 and isi_violations_ratio < 0.5 and amplitude_cutoff < 0.1").index.tolist()

# IBL reproducible-ephys
ibl = qm.query("presence_ratio > 0.9 and isi_violations_ratio < 0.1 and amplitude_cutoff < 0.1 and firing_rate > 0.1").index.tolist()

# Strict single-unit (precise-timing / spike-timing work)
strict = qm.query(
    "snr > 5 and presence_ratio > 0.99 and isi_violations_ratio < 0.01 and "
    "amplitude_cutoff < 0.01 and isolation_distance > 20 and drift_ptp < 40").index.tolist()

# Include multi-unit activity
mua = qm.query("snr > 2 and presence_ratio > 0.5 and isi_violations_ratio < 1.0").index.tolist()
```

## Visualization

```python
si.plot_quality_metrics(analyzer)         # metric overview
si.plot_unit_summary(analyzer, unit_id=0) # waveform + ACG + amplitudes for one unit

# Custom metric histograms with threshold lines
import matplotlib.pyplot as plt
for metric, thr in [("snr", 5), ("isi_violations_ratio", 0.01), ("presence_ratio", 0.9)]:
    ax = qm[metric].dropna().hist(bins=50)
    ax.axvline(thr, color="r", ls="--")
```

## References

- Quality-metrics module:
  https://spikeinterface.readthedocs.io/en/stable/modules/qualitymetrics.html
- Hill et al. (2011), *J Neurosci* — quality metrics for spike sorting
- Siegle et al. (2021), *Nature* — Allen mouse visual-system survey (metric standards)
