---
name: spectral-analysis
version: 0.1.0
description: >-
  Frequency-domain analysis of sampled signals on the SciPy stack — FFT
  amplitude/phase spectra, power spectral density (Welch and periodogram),
  time-frequency spectrograms and continuous wavelet transforms,
  magnitude-squared coherence and cross-spectral density between two channels,
  and zero-phase Butterworth / notch filtering. Use when a time series has
  periodic, quasi-periodic, or transient oscillatory content and you need to
  find its frequencies, quantify power per band, track how spectral content
  evolves in time, compare two signals, or band-limit before further analysis.
  NOT for forecasting a series (use `timesfm-forecasting`), fitting a parametric
  model or testing peak significance rigorously (use `statistical-analysis`),
  qualitative attractor / bifurcation analysis of a dynamical system (use
  `dynamical-systems`), or curated biosignal band pipelines like EEG/ECG (use
  `neurokit2`). For unevenly sampled data, use the Lomb-Scargle path noted inside.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (SciPy, NumPy)"
---

# Spectral Analysis

## Overview

Extract the frequency content of a sampled signal `x[n]` (uniform sampling
interval `dt`, sampling rate `fs = 1/dt`). This skill covers the standard
signal-processing toolkit and when each member applies:

- **FFT** — amplitude/phase spectrum of a short, clean, stationary record.
- **PSD (Welch / periodogram)** — how power distributes over frequency, with
  segment averaging to tame noise. The default estimator for real data.
- **Spectrogram / STFT and CWT** — time-frequency maps for *non-stationary*
  signals whose spectrum changes over time (chirps, bursts, transients).
- **Coherence & cross-spectral density** — frequency-resolved coupling between
  two simultaneously recorded channels.
- **Filtering** — zero-phase band-pass / notch to isolate or remove a band.

Everything runs on `numpy.fft`, `scipy.signal`, and `matplotlib`; the continuous
wavelet path uses `PyWavelets` (SciPy removed its own CWT — see below). Deep
code, parameter tables, and theory live in `references/`; this page routes you.

## When to Use This Skill

- Finding the dominant oscillation frequency (or harmonics) in a time series.
- Computing a power spectrum of turbulence, vibration, LFP, audio, or wave data.
- Detecting transient or drifting features — a spectrogram or wavelet scalogram.
- Measuring coupling between two channels at each frequency (coherence, phase).
- Band-pass / notch / low-pass filtering before downstream analysis.

## When NOT to Use This Skill

- You want to **forecast** future values of the series — use `timesfm-forecasting`.
- You need **statistically rigorous** peak significance, confidence intervals, or
  parametric model fitting beyond the raw periodogram — use `statistical-analysis`.
- The object is a **dynamical system** and you want attractors, fixed points,
  bifurcations, or Lyapunov exponents — use `dynamical-systems`.
- You want a **curated biosignal pipeline** (EEG/ECG band power, HRV, artifact
  cleaning with physiological defaults) — use `neurokit2`.
- The signal is **unevenly sampled** — do *not* FFT it; jump to the Lomb-Scargle
  path in `references/theory-and-pitfalls.md` (`scipy.signal.lombscargle` or
  Astropy `LombScargle`; see `astropy`).

## Setup

```bash
pip install "scipy>=1.11" "numpy>=1.24" "matplotlib>=3.7" "PyWavelets>=1.5"
```

## Core Loop

The recurring pattern is the same for every estimator: **detrend → window →
transform → interpret in physical units**. Skipping the first two steps is the
most common source of wrong spectra.

```python
import numpy as np
from scipy.signal import welch

fs = 1000.0                                  # sampling rate [Hz]
t  = np.arange(0, 1, 1/fs)
x  = 1.5*np.sin(2*np.pi*50*t) + 0.8*np.sin(2*np.pi*120*t) + 0.5*np.random.randn(t.size)

# Welch PSD: detrends each segment, applies a Hann window, averages → stable estimate
freqs, psd = welch(x, fs=fs, nperseg=256, noverlap=128, window="hann",
                   detrend="constant", scaling="density")

peak_hz = freqs[np.argmax(psd)]              # dominant frequency
band_power = np.trapz(psd[(freqs>=45)&(freqs<=55)],
                      freqs[(freqs>=45)&(freqs<=55)])   # power in 45–55 Hz band
```

`welch` is the safe default: for a raw amplitude spectrum use `np.fft.rfft`
instead (recipe in the reference). Frequency resolution is `Δf = fs / nperseg`.

## Choosing a Method

| Situation | Use | Notes |
|---|---|---|
| Stationary signal, want power vs frequency | **Welch PSD** | Averaged, low-variance; the default |
| Short clean transient, want exact bins | **rfft** / periodogram | No averaging → noisy but full resolution |
| Spectrum changes over time (chirp, burst) | **Spectrogram / STFT** | Fixed time-frequency resolution box |
| Wide frequency range, sharp transients | **CWT (wavelet)** | Multi-resolution; good time res at high freq |
| Two channels, shared rhythms | **Coherence + CSD** | Magnitude-squared coherence ∈ [0, 1] |
| Isolate / remove a band | **Butterworth / notch** | Use `sosfiltfilt` for zero phase |
| Uneven / gappy sampling | **Lomb-Scargle** | Never FFT non-uniform data |

## Capabilities

Each area has a self-contained reference with runnable code and parameter
guidance. Load the one you need:

- **Estimator recipes** — full FFT (single-sided amplitude + phase),
  Welch/periodogram PSD, spectrogram and the modern `ShortTimeFFT`, continuous
  wavelet transform via `pywt.cwt`, coherence/CSD, Butterworth band-pass and
  notch filtering, and spectral peak-finding. See `references/workflows.md`.
- **Theory, parameters & pitfalls** — window functions and when to pick each,
  the resolution-vs-averaging trade-off, Nyquist/aliasing, spectral leakage,
  detrending, PSD units and Parseval normalization, the zero-padding myth,
  unevenly sampled data (Lomb-Scargle), and SciPy version/API notes.
  See `references/theory-and-pitfalls.md`.

## Signal-Processing Practice (read before trusting a spectrum)

- **Respect Nyquist.** You can only resolve frequencies below `fs/2`. Content
  above it *aliases* down and masquerades as a real peak. Low-pass (analog or
  digital) before or during acquisition if `f_max` may exceed `fs/2`.
- **Remove the DC / trend first.** A nonzero mean or slow drift dumps huge power
  into the lowest bins and leaks upward. `welch`/`periodogram` detrend per
  segment by default; for a raw FFT subtract the mean (or a linear fit) yourself.
- **Window to control leakage.** A finite record of a non-periodic tone smears
  across bins. A Hann (default) or Blackman window suppresses side-lobes at the
  cost of a wider main lobe. See the window table in the reference.
- **Resolution vs. variance is a real trade-off.** Longer `nperseg` → finer `Δf`
  but fewer averages (noisier PSD); shorter → coarser but smoother. Pick for the
  question, not by default.
- **Zero-padding does not add resolution.** It interpolates the existing
  spectrum for a smoother-looking curve; true resolution is set by record length.
- **Mind the units.** PSD with `scaling="density"` is `V²/Hz` (integrates to
  variance); `scaling="spectrum"` is `V²` (power per bin). Report which you used.
- **CWT frequencies are derived, not direct.** `pywt.cwt` returns frequencies
  from scales given `sampling_period=dt`; do not hand-convert scales yourself.

## Troubleshooting

Symptom → cause → fix for aliased peaks, a DC spike swamping the plot, leakage
smearing a sharp tone, a too-noisy or too-smooth PSD, coherence pinned at 1.0,
filter ringing/edge transients, and the removed `scipy.signal.cwt`/`morlet2`
import error: `references/theory-and-pitfalls.md`.

## Related Skills

- `dynamical-systems` — attractors, bifurcations, and Lyapunov analysis of the
  system that produced the signal.
- `statistical-analysis` — significance tests, confidence intervals, and
  parametric spectral models beyond the periodogram.
- `neurokit2` — EEG/ECG/HRV band-power pipelines with physiological defaults.
- `neuropixels-analysis` — spectral analysis of LFP / neural recordings.
- `astropy` — Lomb-Scargle periodograms for unevenly sampled astronomical data.
- `matplotlib`, `seaborn` — publication-quality spectrum and spectrogram figures.
