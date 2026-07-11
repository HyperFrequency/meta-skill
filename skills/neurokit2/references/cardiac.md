# Cardiac Signals: ECG and PPG

Electrocardiography (ECG) records the heart's electrical activity;
photoplethysmography (PPG) records peripheral blood-volume pulses optically
(fingertip, wrist, earlobe). Both give heart rate and feed HRV, but ECG resolves
the P-QRS-T waveform while PPG resolves the systolic pulse and dicrotic notch.

All functions take `sampling_rate` in Hz and most accept `method=`.

## ECG one-call pipeline

```python
signals, info = nk.ecg_process(ecg, sampling_rate=1000, method="neurokit")
```

Runs: clean → R-peak detection → instantaneous rate → per-beat quality →
P/Q/S/T delineation → cardiac phase. `signals` is a DataFrame (`ECG_Raw`,
`ECG_Clean`, `ECG_R_Peaks`, `ECG_Rate`, `ECG_Quality`, phase columns); `info`
carries `ECG_R_Peaks` indices and parameters. `method` selects the whole
pipeline flavor: `'neurokit'` (default), `'biosppy'`, `'pantompkins1985'`,
`'hamilton2002'`, `'elgendi2010'`, `'engzeemod2012'`.

### Stage functions

- `nk.ecg_clean(ecg, sampling_rate, method='neurokit', powerline=50)` —
  method-specific filtering. `'neurokit'` = 0.5 Hz high-pass Butterworth +
  powerline removal; band-pass variants exist per method. Set `powerline=60`
  outside 50 Hz mains regions.
- `nk.ecg_peaks(ecg_cleaned, sampling_rate, method='neurokit', correct_artifacts=False)`
  — returns `(peaks_dict, info)` with `'ECG_R_Peaks'`. 13+ detectors:
  `'neurokit'`, `'pantompkins1985'`, `'hamilton2002'`, `'christov2004'`,
  `'gamboa2008'`, `'elgendi2010'`, `'engzeemod2012'`, `'kalidas2017'`,
  `'martinez2004'`, `'rodrigues2021'`, `'koka2022'`, `'promac'`.
  `correct_artifacts=True` applies Lipponen & Tarvainen (2019) beat-classification
  correction (ectopic, long/short, missed beats).
- `nk.ecg_delineate(ecg_cleaned, rpeaks, sampling_rate, method='dwt')` — returns
  `(waves, waves_peak)`. Locates `ECG_P_Peaks/Onsets/Offsets`, `ECG_Q_Peaks`,
  `ECG_S_Peaks`, `ECG_T_Peaks/Onsets/Offsets`, and QRS on/offsets. Methods:
  `'dwt'` (discrete wavelet, default), `'cwt'` (Martinez 2004), `'peak'` (simple).
  Needs ≥ 500 Hz for reliable wave boundaries.
- `nk.ecg_quality(ecg, rpeaks=None, sampling_rate, method='averageQRS')` — per-
  beat quality 0–1 via template correlation (Zhao & Zhang 2018); `> 0.6` is a
  common "good beat" cutoff. `method='zhao2018'` gives a multi-index rating.

### ECG utilities

- `nk.ecg_rate(peaks, sampling_rate, desired_length=None)` — BPM from R-R
  intervals (60 / IBI), optionally interpolated to signal length.
- `nk.ecg_phase(ecg_cleaned, rpeaks, delineate_info)` — atrial/ventricular
  systole vs diastole and phase-completion (0–1); useful for cardiac-gated
  stimulus timing.
- `nk.ecg_segment(ecg_cleaned, rpeaks, sampling_rate)` — dict of single-beat
  epochs for morphology comparison.
- `nk.ecg_invert(ecg, sampling_rate)` — detect and flip inverted leads; returns
  `(corrected, is_inverted)`.
- `nk.ecg_rsp(ecg_cleaned, sampling_rate, method='vangent2019')` — ECG-derived
  respiration (band-pass of the modulation); methods `'vangent2019'`,
  `'charlton2016'`, `'soni2019'`. Use when no direct respiration channel exists.
- `nk.ecg_simulate(duration, sampling_rate, heart_rate=70, method='ecgsyn', noise=0.01, random_state=None)`
  — synthetic ECG. `'ecgsyn'` (McSharry 2003 dynamical model) is realistic;
  `'simple'` is faster and coarser.
- `nk.ecg_plot(signals, info)` — cleaned trace, R-peaks, rate, quality overlay.

### ECG analysis

- `nk.ecg_analyze(signals, sampling_rate, method='auto')` — auto event- vs
  interval-related by duration (< 10 s vs ≥ 10 s).
- `nk.ecg_eventrelated(epochs)` — per-epoch `ECG_Rate_Baseline`,
  `ECG_Rate_Min/Max`, cardiac phase at onset; for stimulus-locked trials.
- `nk.ecg_intervalrelated(signals, sampling_rate)` — `ECG_Rate_Mean` plus the
  full `hrv()` battery; for resting/continuous recordings.

## PPG pipeline

```python
signals, info = nk.ppg_process(ppg, sampling_rate=100, method="elgendi")
```

Cleans, detects systolic peaks, computes rate and quality. `signals`:
`PPG_Clean`, `PPG_Peaks`, `PPG_Rate`, `PPG_Quality`. Pipeline `method=`:
`'elgendi'` (default, robust) or `'nabian2018'`.

- `nk.ppg_clean(ppg, sampling_rate, method='elgendi')` — Elgendi = 0.5–8 Hz
  band-pass Butterworth.
- `nk.ppg_peaks(ppg_cleaned, sampling_rate, method='elgendi', correct_artifacts=False)`
  — systolic peaks; detectors `'elgendi'`, `'bishop'`, `'nabian2018'`, `'scipy'`.
- `nk.ppg_quality(ppg, sampling_rate, method='averageQRS')` — per-pulse 0–1
  (template) or `'dissimilarity'`.
- `nk.ppg_segment(ppg_cleaned, peaks, sampling_rate)` — per-pulse epochs for
  pulse-wave morphology.
- `nk.ppg_simulate(duration, sampling_rate, heart_rate=70, noise=0.1, random_state=None)`,
  `nk.ppg_plot(signals, info)`, and `nk.ppg_analyze` / `ppg_eventrelated` /
  `ppg_intervalrelated` mirror the ECG analysis functions.

### PPG-derived HRV

PPG peaks feed `nk.hrv()` directly:

```python
signals, info = nk.ppg_process(ppg, sampling_rate=100)
hrv = nk.hrv(info["PPG_Peaks"], sampling_rate=100)
```

PPG-HRV is generally valid for time and frequency domains but differs slightly
from ECG-HRV because of pulse-transit-time variability. Prefer ECG for clinical
HRV; PPG is fine for research and wearables. PPG is far more motion-sensitive —
gate on `PPG_Quality`.

## Duration and sampling guidance

- R-peak detection: ≥ 250 Hz (ECG); ≥ 20–50 Hz for PPG rate.
- Waveform delineation: ≥ 500 Hz (ECG); detailed morphology 2000+ Hz.
- Basic heart rate: ≥ 10 s. HRV time domain: ≥ 60 s. HRV frequency: 1–5 min.
  Ultra-low-frequency HRV: ≥ 24 h.

## Failure modes and fixes

- **Poor R-peak detection** — try `method='pantompkins1985'`, confirm
  `sampling_rate` ≥ 250 Hz, check for inversion with `nk.ecg_invert()`, and set
  `correct_artifacts=True`.
- **Missing P/T waves** — raise sampling rate to ≥ 500 Hz, try `method='cwt'`,
  and verify beat quality before delineating.
- **Noisy trace** — match the cleaning method to the noise, set the right
  `powerline` frequency, and drop low-quality beats.
- **PPG dropouts / motion** — filter by `PPG_Quality`; do not trust HRV from
  segments below the quality threshold.

## ECG + RSP (respiratory sinus arrhythmia)

```python
ecg_sig, ecg_info = nk.ecg_process(ecg, sampling_rate=1000)
rsp_sig, rsp_info = nk.rsp_process(rsp, sampling_rate=1000)
rsa = nk.hrv_rsa(ecg_info["ECG_R_Peaks"], rsp_sig["RSP_Clean"], sampling_rate=1000)
```

For multi-signal convenience see `events-multimodal.md`.

## Key references

- Pan & Tompkins (1985), *IEEE TBME* 32(3). Real-time QRS detection.
- Martinez et al. (2004), *IEEE TBME* 51(4). Wavelet ECG delineator.
- Lipponen & Tarvainen (2019), *J. Med. Eng. Technol.* 43(3). Artifact correction.
- Elgendi et al. (2013), *PLoS ONE* 8(10). PPG systolic peak detection.
