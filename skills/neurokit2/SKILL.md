---
name: neurokit2
version: 0.1.0
description: >-
  Biosignal (physiological signal) processing toolkit wrapping the NeuroKit2
  Python library for ECG, PPG, HRV, EEG, EDA, RSP, EMG, and EOG data. Use when
  cleaning raw physiological recordings; detecting R-peaks, pulses, blinks, or
  muscle activations; computing heart-rate variability, breathing rate, skin-
  conductance responses, EEG band power or microstates, or entropy/fractal
  complexity; and when building event-related (stimulus-locked) or interval-
  related (resting-state) analyses over one or many synchronized signals. Fits
  psychophysiology, affective computing, wearable/HCI, and clinical-monitoring
  pipelines. Do NOT use for raw neural spike sorting or high-density
  electrophysiology (use dedicated electrophysiology tools), for medical
  diagnosis or treatment decisions, for generic non-physiological time-series
  forecasting, or for statistical hypothesis testing of the extracted features
  themselves — route those to `statistical-analysis`, `statsmodels`, `pymc`, or
  `scikit-learn`.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: MIT
---

# NeuroKit2

## Overview

NeuroKit2 (`import neurokit2 as nk`) is a Python toolbox for processing and
analyzing physiological signals. This skill routes you through its API for the
full biosignal lifecycle: clean a raw trace, detect physiological events
(heartbeats, breaths, skin-conductance responses, blinks, muscle bursts),
extract domain features, and summarize them per condition or per recording.

Two design facts shape almost every workflow:

- **Every modality follows the same three-stage shape**: `nk.<sig>_clean()` →
  `nk.<sig>_peaks()` (or activation/blink detection) → feature functions, with a
  one-call `nk.<sig>_process()` wrapper that runs the whole pipeline and returns
  `(signals_df, info_dict)`. `signals_df` is a pandas DataFrame (one row per
  sample, columns like `ECG_Clean`, `ECG_R_Peaks`, `ECG_Rate`); `info_dict`
  holds event indices and the parameters used.
- **Analysis auto-selects a mode by duration.** `nk.<sig>_analyze()` and
  `nk.bio_analyze()` run **event-related** analysis for segments < 10 s
  (stimulus-locked, epoch-based) and **interval-related** analysis for ≥ 10 s
  (resting state / continuous). You can also call the mode explicitly with
  `nk.<sig>_eventrelated(epochs)` or `nk.<sig>_intervalrelated(signals)`.

## When to Use This Skill

- Processing **cardiac** signals: ECG or PPG cleaning, R-peak / systolic-peak
  detection, waveform delineation, heart rate. See `references/cardiac.md`.
- Computing **heart-rate variability** across time, frequency, and nonlinear
  domains, RSA, or RQA. See `references/hrv.md`.
- Analyzing **EEG**: band power, bad-channel detection, re-referencing, source
  localization, or microstate segmentation. See `references/eeg.md`.
- **Electrodermal** (EDA/GSR) tonic/phasic decomposition and SCR detection. See
  `references/eda.md`.
- **Respiratory** rate, amplitude, RRV, and RVT (fMRI regressor). See
  `references/rsp.md`.
- **EMG** muscle-activation detection and **EOG** blink analysis. See
  `references/emg-eog.md`.
- Generic **signal utilities** — filtering, resampling, decomposition, PSD,
  peak correction — on any 1-D series. See `references/signal-processing.md`.
- **Complexity/entropy/fractal** measures on any signal. See
  `references/complexity.md`.
- **Event-related** epoching and **multi-signal** (`bio_process`) integration.
  See `references/events-multimodal.md`.

## When NOT to Use This Skill

- **Not for raw single-unit / high-density electrophysiology** (spike sorting,
  Neuropixels, LFP). NeuroKit2 targets scalp EEG and peripheral autonomic
  signals, not intracortical spikes.
- **Not a diagnostic device.** Outputs are research features, not clinical
  decisions. Do not use for medical diagnosis or treatment.
- **Not a statistics or ML engine.** NeuroKit2 extracts features; testing them
  (ANOVA, mixed models, classification) belongs in `statistical-analysis`,
  `statsmodels`, `pymc`, or `scikit-learn`.
- **Not a general forecaster.** For non-physiological time-series prediction use
  `timesfm-forecasting` or `statsmodels`.
- **Not deep EEG preprocessing on its own.** For montage handling, ICA, and
  epoched ERP infrastructure NeuroKit2 leans on MNE-Python; use MNE directly for
  heavy EEG pipelines (NeuroKit2 provides `mne_*` bridge helpers).

## Core Capabilities

Each area below is a pointer; open the linked reference for exact signatures,
method options, parameter defaults, duration requirements, and troubleshooting.

### Cardiac (ECG / PPG)

`nk.ecg_process(ecg, sampling_rate)` and `nk.ppg_process(ppg, sampling_rate)`
run cleaning, peak detection, rate, quality, and (ECG) P-QRS-T delineation.
Pick a detector via `method=` (13+ R-peak algorithms; `'neurokit'`,
`'pantompkins1985'`, etc.), enable `correct_artifacts=True` for ectopic-beat
correction, and use `nk.ecg_rsp()` to derive respiration from ECG. Full detail:
`references/cardiac.md`.

### Heart-Rate Variability

`nk.hrv(peaks, sampling_rate)` returns all indices at once; call
`nk.hrv_time()`, `nk.hrv_frequency()`, `nk.hrv_nonlinear()`, `nk.hrv_rsa()`, or
`nk.hrv_rqa()` for a single domain. Watch minimum-duration requirements (RMSSD
tolerates < 5 min; SDNN and frequency bands need more). Indices, bands, and
interpretation: `references/hrv.md`.

### EEG and Microstates

`nk.eeg_power()`, `nk.eeg_badchannels()`, `nk.eeg_rereference()`, `nk.eeg_gfp()`,
`nk.eeg_source()`, and the `nk.microstates_*` family (segment → classify →
static/dynamic metrics), plus `nk.mne_*` bridges to MNE-Python. See
`references/eeg.md`.

### Electrodermal Activity

`nk.eda_process()`, `nk.eda_phasic()` (cvxEDA and alternatives),
`nk.eda_peaks()` for SCRs, and `nk.eda_sympathetic()` for the frequency-band
sympathetic index (needs ≥ 64 s). See `references/eda.md`.

### Respiration

`nk.rsp_process()`, `nk.rsp_rate()`, `nk.rsp_amplitude()`, `nk.rsp_rrv()`, and
`nk.rsp_rvt()`. See `references/rsp.md`.

### EMG and EOG

`nk.emg_process()` with `nk.emg_activation()` (threshold, GMM, changepoint,
bimodal) for muscle bursts, and `nk.eog_process()` / `nk.eog_peaks()` for blink
detection and rate. See `references/emg-eog.md`.

### Generic Signal Processing

`nk.signal_filter()`, `nk.signal_resample()`, `nk.signal_detrend()`,
`nk.signal_decompose()` (EMD/SSA), `nk.signal_findpeaks()`,
`nk.signal_fixpeaks()`, `nk.signal_psd()`, `nk.signal_power()`. See
`references/signal-processing.md`.

### Complexity and Entropy

`nk.complexity()` for a broad sweep, plus targeted `nk.entropy_*`,
`nk.fractal_*`, `nk.complexity_lyapunov()`, `nk.complexity_lempelziv()`, and
`nk.fractal_dfa()`. Optimize embedding parameters first with
`nk.complexity_delay()` / `nk.complexity_dimension()` /
`nk.complexity_tolerance()`. See `references/complexity.md`.

### Events, Epochs, and Multi-Signal

`nk.events_find()` → `nk.epochs_create()` → `nk.epochs_average()` for stimulus-
locked analysis, and `nk.bio_process(ecg=, rsp=, eda=, ...)` /
`nk.bio_analyze()` for one-call multi-modal processing (auto-computes RSA when
ECG + RSP are present). See `references/events-multimodal.md`.

## Installation

```bash
uv pip install neurokit2
```

MNE-Python (`uv pip install mne`) is required only for the EEG source/microstate
and `mne_*` bridge functions. cvxEDA phasic decomposition pulls in `cvxopt`.

## Quick Start

```python
import neurokit2 as nk

# Simulate 60 s of ECG at 1000 Hz (or load your own array)
ecg = nk.ecg_simulate(duration=60, sampling_rate=1000, heart_rate=70)

# One-call pipeline: clean, detect R-peaks, rate, quality, delineate
signals, info = nk.ecg_process(ecg, sampling_rate=1000)

# HRV across all domains from the detected R-peaks
hrv = nk.hrv(info["ECG_R_Peaks"], sampling_rate=1000)

# Duration-aware summary (>= 10 s -> interval-related)
summary = nk.ecg_analyze(signals, sampling_rate=1000)
```

Sampling rate is a required argument almost everywhere and must match the
signal — passing the wrong rate silently corrupts every rate/frequency result.

## References

- `references/cardiac.md` — ECG & PPG cleaning, peak detection, delineation,
  quality, cardiac phase, ECG-derived respiration, simulation.
- `references/hrv.md` — HRV time / frequency / nonlinear indices, RSA, RQA,
  interval preprocessing, duration requirements.
- `references/eeg.md` — band power, channel QC, re-referencing, GFP,
  dissimilarity, source localization, microstates, MNE bridges.
- `references/eda.md` — tonic/phasic decomposition, SCR detection, sympathetic
  index, autocorrelation, changepoints.
- `references/rsp.md` — cleaning, peak/trough detection, rate, amplitude, phase,
  RRV, RVT, RAV.
- `references/emg-eog.md` — EMG amplitude & activation detection; EOG blink
  detection, features, and rate.
- `references/signal-processing.md` — filtering, resampling, detrending,
  decomposition, peaks, PSD, changepoints, synchrony, time-frequency.
- `references/complexity.md` — entropy, fractal dimensions, nonlinear dynamics,
  information theory, parameter optimization, length requirements.
- `references/events-multimodal.md` — event detection, epoching, averaging, and
  `bio_process` / `bio_analyze` multi-signal integration.

## Additional Resources

- Documentation: https://neuropsychology.github.io/NeuroKit/
- Repository: https://github.com/neuropsychology/NeuroKit
- Citation: Makowski, D., et al. (2021). NeuroKit2: A Python toolbox for
  neurophysiological signal processing. *Behavior Research Methods*.
  https://doi.org/10.3758/s13428-020-01516-y
