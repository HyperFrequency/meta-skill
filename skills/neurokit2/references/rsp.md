# Respiratory Signals (RSP)

Respiration analysis covers breathing rate, amplitude (depth), phase, and
variability. It couples tightly to cardiac activity (RSA), emotion, and fMRI
confound modeling. A respiratory cycle runs trough → peak (inhalation) → trough
(exhalation).

## One-call pipeline

```python
signals, info = nk.rsp_process(rsp, sampling_rate=100, method="khodadad2018")
```

Runs clean → peak/trough detection → rate → amplitude → phase → RVT. `signals`
columns: `RSP_Clean`, `RSP_Peaks`, `RSP_Troughs`, `RSP_Rate` (breaths/min),
`RSP_Amplitude`, `RSP_Phase` (0 inspiration / 1 expiration),
`RSP_Phase_Completion`, `RSP_RVT`. Pipeline `method=`: `'khodadad2018'`
(default, robust) or `'biosppy'`.

## Stage functions

- `nk.rsp_clean(rsp, sampling_rate, method='khodadad2018')` — low-pass
  Butterworth; `'biosppy'` alternative; `'hampel'` for spike/artifact-robust
  median filtering.
- `nk.rsp_peaks(rsp_cleaned, sampling_rate, method='khodadad2018')` — returns
  `(peaks, info)` with `RSP_Peaks` (exhalation maxima) and `RSP_Troughs`
  (inhalation minima). Detectors: `'khodadad2018'`, `'biosppy'`, `'scipy'`.
- `nk.rsp_findpeaks(...)` (low-level) and `nk.rsp_fixpeaks(peaks, sampling_rate)`
  (drop implausible intervals, interpolate missing, remove false peaks).

## Feature extraction

- `nk.rsp_rate(peaks, sampling_rate, desired_length=None)` — instantaneous BPM.
- `nk.rsp_amplitude(rsp_cleaned, peaks)` — peak-to-trough depth per breath.
- `nk.rsp_phase(rsp_cleaned, peaks, sampling_rate)` — binary phase +
  completion (0–1) for respiration-gated averaging.
- `nk.rsp_symmetry(rsp_cleaned, peaks)` — peak-trough and rise-decay symmetry.
- `nk.rsp_rrv(peaks, sampling_rate)` — respiratory rate variability (analogue of
  HRV): `RRV_SDBB`, `RRV_RMSSD`, `RRV_MeanBB`, and frequency-domain metrics.
  Needs ≥ 2–3 min.
- `nk.rsp_rvt(rsp_cleaned, peaks, sampling_rate)` — respiratory volume per time,
  a common **fMRI BOLD confound regressor** (Birn et al.).
- `nk.rsp_rav(amplitude, sampling_rate)` — respiratory amplitude variability
  (SD, CV, range).

## Analysis

- `nk.rsp_analyze(signals, sampling_rate)` — duration-aware dispatch.
- `nk.rsp_eventrelated(epochs)` — `RSP_Rate_Mean`, `RSP_Rate_Min/Max`,
  `RSP_Amplitude_Mean`, phase at onset.
- `nk.rsp_intervalrelated(signals, sampling_rate)` — `RSP_Rate_Mean/SD`,
  `RSP_Amplitude_Mean`, RRV and RAV indices. Needs ≥ 60 s (5–10 min optimal).

## Simulation and plotting

- `nk.rsp_simulate(duration, sampling_rate, respiratory_rate=15, method='sinusoidal', noise=0.1, random_state=None)`
  — `'sinusoidal'` (fast) or `'breathmetrics'` (realistic).
- `nk.rsp_plot(signals, info, static=True)`.

## Practical guidance

- Sampling: ≥ 10 Hz for rate; 50–100 Hz standard.
- Duration: rate ≥ 10 s; RRV ≥ 2–3 min; resting 5–10 min.
- Typical rate: 12–20 BPM at rest; < 10 slow/meditative; > 25 exercise/anxiety.
  Resonance-frequency breathing is ~6 BPM.
- Sensors: strain/piezo belt (chest/abdomen, most common), thermistor (airflow),
  capnography (end-tidal CO₂, gold standard), impedance pneumography (from ECG
  electrodes, convenient but coarser).

## Failure modes

- **Irregular breathing** (sighs, speech, swallowing) is normal in awake
  subjects — annotate or model as events rather than forcing regularity.
- **Shallow / low-amplitude** — check belt tightness and placement; raise gain.
- **Movement spikes** — use `method='hampel'` cleaning and `rsp_fixpeaks()`.

## RSP + ECG

```python
rsa = nk.hrv_rsa(ecg_info["ECG_R_Peaks"], rsp_sig["RSP_Clean"], sampling_rate=1000)
# or one call:
bio_signals, bio_info = nk.bio_process(ecg=ecg, rsp=rsp, sampling_rate=1000)
```

See `hrv.md` (RSA) and `events-multimodal.md`.

## Key references

- Grossman & Taylor (2007), *Biol. Psychol.* 74(2). RSA and vagal tone.
- Birn et al. (2006), *NeuroImage* 31(4). RVT for fMRI confound removal.
