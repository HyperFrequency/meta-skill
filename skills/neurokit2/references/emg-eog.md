# EMG (Muscle) and EOG (Eye) Signals

Two peripheral modalities that share the clean → detect → analyze shape. EMG
targets muscle-activation timing and intensity; EOG targets blinks and gross eye
movements.

---

# Electromyography (EMG)

Surface EMG records skeletal-muscle electrical activity: zero-mean oscillations
whose amplitude tracks contraction strength. Analysis rectifies and smooths the
raw signal into a **linear envelope**, then detects activation bursts.

## Pipeline

```python
signals, info = nk.emg_process(emg, sampling_rate=1000)
```

Runs clean (high-pass + detrend) → amplitude envelope → activation detection →
onset/offset. `signals`: `EMG_Clean`, `EMG_Amplitude`, `EMG_Activity` (0/1),
`EMG_Onsets`, `EMG_Offsets`.

- `nk.emg_clean(emg, sampling_rate)` — 4th-order Butterworth high-pass (~100 Hz,
  BioSPPy) + detrend. Removes motion artifacts (< 20 Hz) and ECG contamination
  in trunk muscles; EMG content is ~20–500 Hz (dominant 50–150 Hz).
- `nk.emg_amplitude(emg_cleaned, sampling_rate)` — full-wave rectify + low-pass
  (10–20 Hz) → smooth envelope proxying force.
- `nk.emg_activation(emg_amplitude, sampling_rate, method='threshold', threshold='auto', duration_min=0.05)`
  — returns `(activity, info)` with onset/offset indices. Methods:
  `'threshold'` (`'auto'` = e.g. mean+1SD, or a float), `'mixture'` (2-cluster
  GMM, adaptive), `'changepoint'`, `'bimodal'` (Silva 2013). `duration_min` (s)
  rejects brief spurious bursts.

## Analysis

- `nk.emg_analyze(signals, sampling_rate)` — duration-aware dispatch.
- `nk.emg_eventrelated(epochs)` — `EMG_Activation` (0/1), `EMG_Amplitude_Mean`,
  `EMG_Amplitude_Max`, `EMG_Bursts`, `EMG_Onset_Latency`. Good for startle
  (orbicularis oculi) and facial-EMG valence (corrugator = frown, zygomaticus =
  smile).
- `nk.emg_intervalrelated(signals, sampling_rate)` — `EMG_Bursts_N`,
  `EMG_Amplitude_Mean`, activation vs rest durations.
- `nk.emg_simulate(duration, sampling_rate, burst_number=..., noise=..., random_state=...)`,
  `nk.emg_plot(signals, info, static=True)`.

## Guidance

- Sampling: ≥ 500 Hz (surface 1000–2000 Hz); intramuscular single-unit needs
  10+ kHz (out of scope here).
- Placement: bipolar over muscle belly, aligned to fibers, ~10–20 mm spacing
  (SENIAM), reference over bone.
- **%MVC normalization** enables cross-subject comparison:
  `normalized = amplitude / max(mvc_amplitude) * 100` from a separate maximum-
  voluntary-contraction trial.
- Watch ECG bleed-through (proximal muscles), motion artifacts, and cross-talk
  from adjacent muscles. Frequency-domain fatigue analysis (median-frequency
  shift) needs ≥ 1 s windows and is not part of the basic NeuroKit2 functions.

## EMG references

- Fridlund & Cacioppo (1986), *Psychophysiology* 23(5).
- Hermens et al. (2000), *J. Electromyogr. Kinesiol.* 10(5). SENIAM.

---

# Electrooculography (EOG)

EOG records the corneo-retinal potential, so eye rotation and eyelid movement
produce voltage changes. NeuroKit2 focuses on **blink** detection and rate; it
also serves EEG blink-artifact removal.

## Pipeline

```python
signals, info = nk.eog_process(eog, sampling_rate=500, method="neurokit")
```

Runs clean → blink detection → blink rate. `signals`: `EOG_Clean`, `EOG_Blinks`
(0/1), `EOG_Rate` (blinks/min). Pipeline/detection `method=`: `'neurokit'`,
`'agarwal2019'`, `'mne'`, `'brainstorm'`, `'kong1998'`.

- `nk.eog_clean(eog, sampling_rate, method='neurokit')` — band-pass (~0.1–1 Hz
  high-pass, 10–20 Hz low-pass) preserving the 100–400 ms blink waveform.
- `nk.eog_peaks(eog_cleaned, sampling_rate, method='neurokit', threshold=0.33)`
  — blink peaks; detectors `'neurokit'`, `'mne'`, `'brainstorm'`, `'blinker'`
  (Kleifges 2017). `threshold` is a fraction of max amplitude (0.2–0.5 typical).
- `nk.eog_findpeaks(...)` low-level variant.

## Features and analysis

- `nk.eog_features(signals, sampling_rate)` — per-blink amplitude-velocity ratio
  (AVR, discriminates blinks from artifacts), blink-amplitude ratio, duration
  stats, peak amplitude and velocity. Drowsiness lengthens blinks.
- `nk.eog_rate(blinks, sampling_rate, desired_length=None)` — blinks/min.
- `nk.eog_analyze` / `eog_eventrelated` (`EOG_Blinks_N`, `EOG_Rate_Mean`,
  `EOG_Blink_Presence`) / `eog_intervalrelated` (`EOG_Blinks_N`,
  `EOG_Rate_Mean/SD`, duration/amplitude means).
- `nk.eog_plot(signals, info)`.

## Guidance

- Sampling: ≥ 100 Hz for blinks; 250–500 Hz research; 1000 Hz for saccade
  waveforms.
- Placement: **VEOG** (above/below one eye) is most sensitive to blinks;
  **HEOG** (outer canthi) captures horizontal movement. Frontal EEG (Fp1/Fp2)
  can proxy EOG for artifact correction.
- Typical blink rate: 15–20/min at rest; 5–10/min reading (suppressed);
  20–30/min conversation; > 30/min stress or dry eye. Blink duration
  100–400 ms; prolonged (> 500 ms) signals drowsiness.
- **EEG artifact removal**: prefer ICA — run ICA on EEG including EOG channels,
  identify EOG-correlated components, remove them (via MNE). Regression is a
  simpler fallback.
- EOG resolves blinks and gross eye movements only; detailed saccade/fixation
  analysis needs video/infrared eye tracking.

## EOG references

- Kleifges et al. (2017), *Front. Neurosci.* 11:12. BLINKER.
- Kong & Wilson (1998), *Behav. Res. Methods* 30(4). EOG blink detection.
