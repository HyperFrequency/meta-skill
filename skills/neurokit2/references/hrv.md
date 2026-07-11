# Heart-Rate Variability (HRV)

HRV quantifies beat-to-beat variation in the NN (normal-to-normal) interval
series, reflecting autonomic regulation. Input is a peaks dict (with
`ECG_R_Peaks` or `PPG_Peaks`) or a bare array of peak sample indices.

## All-domain wrapper

```python
hrv = nk.hrv(peaks, sampling_rate=1000, show=False)
```

Returns a one-row DataFrame combining `nk.hrv_time()`, `nk.hrv_frequency()`, and
`nk.hrv_nonlinear()`. Use it for exploration; call individual domains when you
need control over parameters.

## Time domain — `nk.hrv_time(peaks, sampling_rate)`

Computed from NN intervals directly.

- `HRV_MeanNN`, `HRV_SDNN` (total variability; ≥ 5 min short-term, 24 h long-term),
  `HRV_RMSSD` (successive-difference RMS; parasympathetic, stable in short records).
- `HRV_SDSD`, `HRV_pNN50`, `HRV_pNN20` (successive-difference measures; pNN20 is
  more sensitive than pNN50).
- `HRV_CVNN` (SDNN/MeanNN), `HRV_CVSD` (RMSSD/MeanNN) — normalized, good for
  cross-subject comparison.
- Robust stats: `HRV_MedianNN`, `HRV_MadNN`, `HRV_MCVNN`, `HRV_IQRNN`.
- Geometric: `HRV_TINN` (triangular interpolation), `HRV_HTI` (triangular index).

## Frequency domain — `nk.hrv_frequency(peaks, sampling_rate)`

Default bands (Hz): `ulf=(0, 0.0033)`, `vlf=(0.0033, 0.04)`, `lf=(0.04, 0.15)`,
`hf=(0.15, 0.4)`, `vhf=(0.4, 0.5)`. Key metrics:

- Absolute power (ms²): `HRV_ULF`, `HRV_VLF`, `HRV_LF`, `HRV_HF`, `HRV_VHF`,
  `HRV_TP` (total power), `HRV_LFHF` (LF/HF ratio).
- Normalized: `HRV_LFn = LF/(LF+HF)`, `HRV_HFn = HF/(LF+HF)`, `HRV_LnHF`.
- Peaks: `HRV_LFpeak`, `HRV_HFpeak`.

Set `psd_method=`:

- `'welch'` (default) — windowed FFT, smooth, standard.
- `'lomb'` — Lomb-Scargle; handles uneven sampling, no interpolation, robust to
  artifacts.
- `'multitapers'` — best variance/bias tradeoff, slower.
- `'burg'` (with `order=`, e.g. 16) — parametric AR, smooth peaks.

**Interpretation caution.** HF is a reliable vagal index; LF mixes sympathetic
and parasympathetic influence, so read LF/HF as "sympathovagal balance" only
loosely — controlled respiration strongly affects HF. Minimum ~60 s for LF/HF;
5 min per Task Force standards; 24 h for ULF.

## Nonlinear domain — `nk.hrv_nonlinear(peaks, sampling_rate)`

**Poincaré geometry** (NN(i+1) vs NN(i)):

- `HRV_SD1` (short-term, ⟂ to identity; ≈ RMSSD/√2), `HRV_SD2` (long-term),
  `HRV_SD1SD2` / `HRV_SD2SD1` ratios, `HRV_S` (ellipse area π·SD1·SD2),
  `HRV_CSI`, `HRV_CVI`, `HRV_CSI_Modified`.

**Heart-rate asymmetry** (accelerations vs decelerations): `HRV_GI`, `HRV_SI`,
`HRV_AI`, `HRV_PI`, `HRV_C1d/C2d/C1a/C2a`, `HRV_SD1d/SD1a/SD2d/SD2a`. Healthy
records show asymmetry; clinical populations lose it.

**Entropy**: `HRV_ApEn`, `HRV_SampEn`, `HRV_MSE`, `HRV_FuzzyEn`, `HRV_ShanEn`
(lower = more regular/predictable).

**Fractal**: `HRV_DFA_alpha1` (short-term scaling, 4–11 beats; ≈ 1 healthy,
reduced in disease), `HRV_DFA_alpha2` (> 11 beats), `HRV_DFA_alpha1alpha2`,
`HRV_CorDim`, `HRV_HFD`, `HRV_PFD`, `HRV_KFD`, `HRV_Hurst`, `HRV_LZC`, `HRV_MFDFA`.

**Fragmentation**: `HRV_PIP` (inflection-point %, ~50% normal, >70% fragmented),
`HRV_IALS`, `HRV_PSS`, `HRV_PAS` — an independent cardiovascular-risk signal.

## Specialized

- `nk.hrv_rsa(peaks, rsp_signal, sampling_rate, method='porges1980')` —
  respiratory sinus arrhythmia. `'porges1980'` (Porges-Bohrer band-pass) or
  `'harrison2021'` (peak-to-trough per breath). Needs synchronized ECG + RSP and
  several breath cycles.
- `nk.hrv_rqa(peaks, sampling_rate)` — recurrence quantification: `RQA_RR`,
  `RQA_DET`, `RQA_LMean/LMax`, `RQA_ENTR`, `RQA_LAM`, `RQA_TT`.

## Working from intervals, not peaks

- `nk.intervals_process(rr_intervals, interpolate=False, interpolate_sampling_rate=1000)`
  — drop implausible intervals (< 300 ms or > 2000 ms), optional interpolation
  and detrending.
- `nk.intervals_to_peaks(rr_intervals, sampling_rate=1000)` — convert imported
  RR/NN series from external HRV devices into peak indices for `nk.hrv()`.

## Minimum recording durations

| Metric group | Minimum | Optimal |
|---|---|---|
| RMSSD, pNN50 | 30 s | 5 min |
| SDNN | 5 min | 5 min (short) / 24 h (long) |
| LF, HF | 2 min | 5 min |
| VLF | 5 min | 10+ min |
| ULF | 24 h | 24 h |
| ApEn / SampEn | 100–300 beats | 500+ beats |
| DFA | 300 beats | 1000+ beats |

## Artifact hygiene

Detect peaks with `correct_artifacts=True` (see `cardiac.md`) or clean an
interval series with `nk.intervals_process()`. Inspect the tachogram for jumps
and missing beats before trusting frequency-domain output. HRV has large
between-subject variance — within-subject change is more interpretable than an
absolute value; control for age, posture, breathing rate, and time of day.

## Key references

- Task Force ESC/NASPE (1996), *Circulation* 93(5). Measurement standards.
- Shaffer & Ginsberg (2017), *Front. Public Health* 5:258. Metrics and norms.
- Peng et al. (1995), *Chaos* 5(1). DFA scaling exponents.
- Costa et al. (2005), *Phys. Rev. E* 71(2). Multiscale entropy.
