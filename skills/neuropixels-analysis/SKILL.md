---
name: neuropixels-analysis
version: 0.1.0
description: >-
  Analyze high-density Neuropixels extracellular recordings end-to-end with
  SpikeInterface: load SpikeGLX / Open Ephys / NWB data, preprocess (highpass,
  phase-shift, common reference, bad-channel removal, destriping), estimate and
  correct probe drift, run spike sorting (Kilosort4, SpykingCircus2,
  Mountainsort5, Tridesclous2), build a SortingAnalyzer (waveforms, templates,
  correlograms, PCA), compute quality metrics (SNR, ISI-violations, presence
  ratio, amplitude cutoff), and curate units against
  Allen / IBL / Bombcell criteria before exporting to Phy or NWB. Use when the
  user mentions Neuropixels, SpikeGLX, Open Ephys, Kilosort, spike sorting,
  drift/motion correction, unit curation, or extracellular-ephys quality
  metrics. NOT for calcium imaging / two-photon, LFP or EEG spectral analysis
  without sorting, patch-clamp/intracellular traces, or downstream neuroscience
  modeling (PSTHs, decoding, connectivity) — this skill stops at curated units;
  hand the spike trains to a downstream analysis tool.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT (SpikeInterface); spike sorters carry their own licenses, e.g. Kilosort4 GPL-3.0, Bombcell GPL-3.0"
---

# Neuropixels Analysis: Spike Sorting and Unit Curation

## Overview

This skill is a **router** for the extracellular-electrophysiology pipeline that
turns raw Neuropixels voltage into a table of curated, single-unit spike trains.
Nearly every task follows the same arc:

```
load → preprocess → correct drift → spike-sort → build analyzer → quality metrics → curate → export
```

It maps that arc onto **SpikeInterface** (`spikeinterface.full as si`), the
standard open-source framework that wraps every reader, preprocessor, sorter,
postprocessor, and exporter behind one object API. The central objects are the
`Recording` (continuous traces + probe geometry), the `Sorting` (spike trains
per unit), and the `SortingAnalyzer` (waveforms, templates, metrics computed
from a sorting + recording pair). Deep parameter tables, per-stage recipes, and
troubleshooting live in `references/`.

Everything below uses real SpikeInterface APIs — there is no bespoke wrapper
package to install.

## When to Use This Skill

Trigger when the user wants to:
- Load Neuropixels data (`.ap.bin`/`.lf.bin`/`.meta` from SpikeGLX, Open Ephys
  record nodes, or NWB) and inspect probe geometry and streams
- Preprocess raw traces: highpass/bandpass filter, ADC phase-shift, common
  median reference, bad-channel detection/removal/interpolation, IBL destriping
- Detect and correct probe **drift/motion** before sorting
- Run a **spike sorter** (Kilosort4 on GPU; SpykingCircus2, Tridesclous2,
  Mountainsort5 on CPU) and compare multiple sorters
- Compute **quality metrics** (SNR, ISI-violations ratio, presence ratio,
  amplitude cutoff, isolation distance, d-prime, drift metrics)
- **Curate** units to good/MUA/noise using Allen, IBL, or strict criteria,
  Bombcell, or model-based auto-curation
- Export curated results to **Phy** for manual review or to **NWB** for sharing

## When NOT to Use This Skill

- **Calcium imaging / two-photon** — that is image data, not extracellular
  voltage; use `bioimage-analysis`.
- **LFP or EEG spectral analysis without sorting** (power spectra, coherence,
  CSD) — this skill is about single-unit spike sorting, not field potentials.
- **Patch-clamp / intracellular traces** — different acquisition and analysis
  entirely.
- **Downstream neuroscience modeling** — PSTHs, tuning curves, population
  decoding, connectivity. This skill stops at *curated spike trains*; hand the
  `Sorting` object or exported spike times to `statistical-analysis`,
  `statsmodels`, `scikit-learn`, or plot with `matplotlib`/`seaborn`.

## Install and Import

```bash
pip install "spikeinterface[full]" probeinterface neo   # core framework + I/O
pip install kilosort                                    # Kilosort4 (needs a CUDA GPU)
pip install mountainsort5                                # optional CPU sorter
pip install bombcell                                     # optional automated curation
# SpykingCircus2 and Tridesclous2 run *inside* spikeinterface[full] — no extra sorter install
```

```python
import spikeinterface.full as si          # one namespace for read/preprocess/sort/postprocess/export
import numpy as np, pandas as pd

# Set parallelism once; every heavy step (save, sort, metrics) reuses it.
si.set_global_job_kwargs(n_jobs=-1, chunk_duration="1s", progress_bar=True)
```

`spikeinterface.full` re-exports the whole API under `si.*`. Sorters are external
programs SpikeInterface shells out to — check what is actually available with
`si.installed_sorters()` before you plan a run.

## The Pipeline (capability map)

Each row is an entry point; follow the reference link for signatures, full
parameter tables, and worked examples.

| Stage | Key entry points | Depth |
|---|---|---|
| Load + inspect | `si.read_spikeglx`, `si.read_openephys`, `si.read_nwb`, `si.get_neo_streams` | `references/preprocessing.md` |
| Preprocess | `si.highpass_filter`, `si.phase_shift`, `si.detect_bad_channels`, `si.common_reference`, `si.highpass_spatial_filter` | `references/preprocessing.md` |
| Drift correction | `si.correct_motion(preset=...)`; low-level `estimate_motion`/`interpolate_motion` | `references/motion-correction.md` |
| Spike sorting | `si.run_sorter`, `si.get_default_sorter_params`, `si.compare_multiple_sorters` | `references/spike-sorting.md` |
| Postprocess | `si.create_sorting_analyzer`, `analyzer.compute([...])` | `references/quality-metrics.md` |
| Quality metrics | `analyzer.compute('quality_metrics')`, `get_extension(...).get_data()` | `references/quality-metrics.md` |
| Curation | threshold queries, Bombcell, `spikeinterface.curation`, AI-visual | `references/curation-and-export.md` |
| Export | `si.export_to_phy`, `export_to_nwb`, `si.read_phy` | `references/curation-and-export.md` |

## Minimal End-to-End Recipe

```python
import spikeinterface.full as si

# 1. Load (SpikeGLX is the most common Neuropixels format)
rec = si.read_spikeglx("/path/to/run_g0/", stream_id="imec0.ap")
# Inspect streams first if unsure: si.get_neo_streams("spikeglx", "/path/to/run_g0/")

# 2. Preprocess — phase_shift is REQUIRED for Neuropixels 1.0, harmless-to-skip for 2.0
rec = si.highpass_filter(rec, freq_min=300)
rec = si.phase_shift(rec)                                   # corrects per-channel ADC sampling offset
bad_ids, _ = si.detect_bad_channels(rec)
rec = rec.remove_channels(bad_ids)
rec = si.common_reference(rec, reference="global", operator="median")   # CMR

# 3. Correct drift (always check first — see references/motion-correction.md)
rec, motion_info = si.correct_motion(rec, preset="nonrigid_accurate", output_motion_info=True)

# 4. Sort (Kilosort4 needs a GPU; swap to a CPU sorter from si.installed_sorters())
sorting = si.run_sorter("kilosort4", rec, folder="ks4_output")

# 5. Build the analyzer and compute the extensions metrics depend on (order matters)
analyzer = si.create_sorting_analyzer(sorting, rec, sparse=True, folder="analyzer")
analyzer.compute(["random_spikes", "waveforms", "templates",
                  "noise_levels", "spike_amplitudes", "correlograms",
                  "unit_locations", "quality_metrics"])
qm = analyzer.get_extension("quality_metrics").get_data()   # pandas DataFrame, one row per unit

# 6. Curate (Allen-style conservative defaults) and export the good units
good = qm.query("presence_ratio > 0.9 and isi_violations_ratio < 0.5 and amplitude_cutoff < 0.1").index.tolist()
si.export_to_phy(analyzer.select_units(good), output_folder="phy_export")
print(f"Kept {len(good)}/{len(qm)} units")
```

Save the preprocessed recording once (`rec.save(folder="preprocessed/")`) so you
can iterate on sorting/metrics without re-running the filter chain.

## AI-Assisted Visual Curation (vendor-neutral technique)

Quantitative thresholds decide the clear cases; **borderline units are best
judged by eye** from a summary figure — the shape of the mean waveform, a clean
refractory gap in the autocorrelogram, and amplitude stability over time. When
you run inside an agent with vision (like this one), you do not need any external
vision-API wrapper:

```python
# Render a per-unit summary figure, then ask the agent to inspect it directly.
for uid in qm.query("snr > 3 and snr < 8").index:                 # the uncertain band
    si.plot_unit_summary(analyzer, unit_id=uid).figure.savefig(f"unit_{uid}.png", dpi=120)
# Then: have the model read unit_<id>.png and classify good / MUA / noise with reasoning.
```

Use vision only for the uncertain band (waste no effort on obvious good/noise
units), always combine it with the numeric metrics, and keep a human in the loop
for publication-critical work. See `references/curation-and-export.md`.

## Failure Modes and Gotchas

- **Always visualize drift before sorting.** Uncorrected drift > ~10 µm silently
  splits one neuron into several units and tanks yield. Plot the drift raster
  map first (`references/motion-correction.md`), then decide.
- **`phase_shift` is Neuropixels-1.0-specific.** NP 1.0 samples channels through
  a shared ADC at staggered times; skip the correction and you smear waveforms.
  NP 2.0 uses per-channel ADCs and does not need it.
- **Extension compute order is a dependency graph**, not a free-for-all:
  `random_spikes → waveforms → templates → noise_levels → spike_amplitudes →
  quality_metrics`; isolation-quality metrics (`isolation_distance`, `d_prime`,
  `nn_*`) additionally require `principal_components`. Passing a list to
  `analyzer.compute([...])` resolves the order for you.
- **`sparse=True` on the analyzer** is essential at 384 channels — a dense
  analyzer stores every unit on every channel and blows up memory.
- **Kilosort4 needs a real CUDA GPU.** Check `torch.cuda.is_available()`; without
  a GPU, fall back to `spykingcircus2`/`tridesclous2`/`mountainsort5` (10–50×
  slower). On GPU OOM, lower `batch_size`.
- **Too many / too few units** is usually a threshold problem, not a data
  problem: lower `Th_universal`/`Th_learned` for more spikes, raise `dmin`/`dminx`
  to merge over-split templates. See `references/spike-sorting.md`.
- **Do not double-correct.** If you run `si.correct_motion` in preprocessing,
  disable the sorter's internal drift correction (or vice-versa) — stacking both
  distorts geometry.
- **Automated curation is a starting point, not ground truth.** Document your
  exact thresholds, be conservative when uncertain, and export to Phy for human
  review on critical experiments.
- **Test on a slice first.** `rec.frame_slice(0, int(60 * rec.get_sampling_frequency()))`
  gives you 60 s to validate the whole pipeline before committing hours of GPU time.

## References

- `references/preprocessing.md` — readers per format/stream, the filter →
  phase-shift → reference → bad-channel chain, IBL destriping, whitening,
  artifact removal, probe-specific handling (NP 1.0 / 2.0 / 4-shank), saving.
- `references/motion-correction.md` — drift detection and raster map, the
  `correct_motion` preset table, the `estimate_motion`/`interpolate_motion`
  control path, DREDge / LFP estimation, and over/under-correction fixes.
- `references/spike-sorting.md` — sorter comparison, Kilosort4 parameters, CPU
  alternatives, Docker/Singularity, long recordings, multi-sorter agreement,
  and troubleshooting.
- `references/quality-metrics.md` — the SortingAnalyzer extensions and every
  metric with interpretation thresholds (contamination / completeness /
  stability / isolation) plus Allen / IBL / strict / MUA filter queries.
- `references/curation-and-export.md` — threshold curation, Bombcell 4-class
  classification, UnitMatch, the `spikeinterface.curation` merge/split API, the
  AI-visual technique in depth, and export to Phy and NWB.
