# Electrodermal Activity (EDA / GSR / Skin Conductance)

EDA measures skin electrical conductance, driven by sweat-gland activity and
therefore sympathetic arousal. The signal splits into a slow **tonic** level
(SCL, baseline arousal) and fast **phasic** responses (SCRs, event-related).

## One-call pipeline

```python
signals, info = nk.eda_process(eda, sampling_rate=100, method="neurokit")
```

Runs clean → tonic/phasic decomposition → SCR detection → SCR feature
extraction. `signals` columns include `EDA_Clean`, `EDA_Tonic`, `EDA_Phasic`,
`SCR_Onsets`, `SCR_Peaks`, `SCR_Height`, `SCR_Amplitude`, `SCR_RiseTime`,
`SCR_RecoveryTime`. Pipeline `method=`: `'neurokit'` (cvxEDA + NeuroKit peaks)
or `'biosppy'`.

## Stage functions

- `nk.eda_clean(eda, sampling_rate, method='neurokit')` — low-pass Butterworth
  (`'neurokit'` 3 Hz, `'biosppy'` 5 Hz). Cleaning is skipped automatically below
  ~7 Hz sampling since the signal is already band-limited.
- `nk.eda_phasic(eda_cleaned, sampling_rate, method='cvxeda')` — returns
  `(tonic, phasic)`. Methods: `'cvxeda'` (convex-optimization sparse driver,
  Greco 2016 — most accurate, slowest), `'smoothmedian'` (fast, coarse),
  `'highpass'` (0.05 Hz, Biopac-style), `'sparseda'`.
- `nk.eda_peaks(eda_phasic, sampling_rate, method='neurokit', amplitude_min=0.1)`
  — detect SCRs. Detectors: `'neurokit'`, `'gamboa2008'`, `'kim2004'`,
  `'vanhalem2020'`, `'nabian2018'`. Returns `SCR_Onsets`, `SCR_Peaks`,
  `SCR_Height`, `SCR_Amplitude`, `SCR_RiseTime`, `SCR_RecoveryTime`. Tune
  `amplitude_min` (µS): too low invites noise; too high drops small valid SCRs.

## Analysis

- `nk.eda_analyze(signals, sampling_rate)` — duration-aware dispatch.
- `nk.eda_eventrelated(epochs)` — per epoch: `EDA_SCR` (0/1), `SCR_Amplitude`,
  `SCR_Peak_Amplitude`, `SCR_RiseTime`, `SCR_RecoveryTime`, `SCR_Latency`,
  `EDA_Tonic`. Expect SCR latency 1–3 s after stimulus; epoch ~ −1 to 10 s.
- `nk.eda_intervalrelated(signals, sampling_rate)` — `SCR_Peaks_N`,
  `SCR_Peaks_Amplitude_Mean`, `EDA_Tonic_Mean/SD`, `EDA_Sympathetic`,
  `EDA_SympatheticN`, `EDA_Autocorrelation`, phasic summary stats.

## Specialized

- `nk.eda_sympathetic(signals, sampling_rate, method='posada')` — sympathetic
  index from spectral power in 0.045–0.25 Hz. Methods `'posada'`
  (Posada-Quintero 2016) or `'ghiasi'`. **Requires ≥ 64 s** for band resolution.
  Returns `EDA_Sympathetic` and normalized `EDA_SympatheticN` (0–1).
- `nk.eda_autocor(eda_phasic, sampling_rate, lag=4)` — temporal regularity at a
  given lag (s).
- `nk.eda_changepoints(eda_phasic, penalty=10000)` — abrupt mean/variance
  shifts; higher penalty = fewer, more robust changepoints.
- `nk.eda_simulate(duration, sampling_rate, scr_number=..., noise=..., drift=...)`,
  `nk.eda_plot(signals, info, static=True)` (Plotly when `static=False`).

## Timing and acquisition

- SCR latency 1–3 s; rise 0.5–3 s; recovery (to 50%) 2–10 s; detection
  threshold ~0.01–0.05 µS.
- Sampling: ≥ 10 Hz enough for slow SCRs; 20–100 Hz standard.
- Duration: event-related 10–20 s/trial; interval-related ≥ 60 s; sympathetic
  index ≥ 64 s.
- Placement: palmar (finger phalanges) or plantar; avoid hairy/low-gland skin;
  allow 5–10 min adaptation.

## Failure modes

- **Flat signal** — electrode contact/gel, placement, or too-short adaptation.
- **Baseline drift** — normal over minutes; separate with `eda_phasic()`;
  excessive drift signals polarization/poor contact.
- **Non-responders** — ~5–10% of people show minimal EDA; not equipment failure.
- **Motion/electrical noise** — minimize movement, check grounding, control room
  temperature.

## Interpretation

- SCR amplitude: 0.01–0.05 µS small, 0.05–0.2 moderate, > 0.2 large; normalize
  within subject.
- SCR frequency: ~1–3/min at rest, > 5/min stressed; "non-specific" SCRs occur
  without an identifiable stimulus.
- Tonic SCL: 2–20 µS, highly individual; within-subject change beats absolute
  level. EDA indexes arousal, not emotional valence.

## Key references

- Boucsein (2012), *Electrodermal Activity* (2nd ed.), Springer.
- Greco et al. (2016), *IEEE TBME* 63(4). cvxEDA.
- Posada-Quintero et al. (2016), *Ann. Biomed. Eng.* 44(10). Sympathetic PSD.
