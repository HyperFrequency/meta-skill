# EEG: Band Power, Quality, Source, and Microstates

NeuroKit2 covers spectral power, channel QC, re-referencing, source estimation,
and microstate analysis, and bridges to MNE-Python for montage-heavy work. For
serious preprocessing (filtering montages, ICA artifact removal, epoched ERPs),
drive MNE directly and hand NeuroKit2 the cleaned arrays.

## Spectral and topographic

- `nk.eeg_power(eeg, sampling_rate, channels, frequency_bands=...)` — power per
  channel × band. Default bands: Delta (0.5–4), Theta (4–8), Alpha (8–13),
  Beta (13–30), Gamma (30–45) Hz. Columns are `Channel_Band` (e.g. `Fz_Alpha`).
- `nk.eeg_badchannels(eeg, sampling_rate, bad_threshold=2)` — flag flat/noisy/
  outlier channels by z-scored statistics; returns channel names to interpolate
  or drop.
- `nk.eeg_rereference(eeg, reference='average', robust=False)` — re-reference to
  `'average'`, `'REST'`, `'bipolar'`, or a named channel. Average reference is
  standard for high-density montages; REST approximates an infinity reference.
- `nk.eeg_gfp(eeg)` — Global Field Power: the SD across electrodes per time
  point. GFP peaks mark moments of stable topography and seed microstate
  extraction.
- `nk.eeg_diss(eeg1, eeg2, method='gfp')` — topographic dissimilarity between
  field configurations; used for microstate transitions and template matching.
- `nk.eeg_simulate(duration, sampling_rate, n_channels=...)` — synthetic EEG.

## Source localization

- `nk.eeg_source(eeg, method='sLORETA')` — scalp-to-source reconstruction.
  Methods: `'sLORETA'`, `'MNE'` (minimum-norm), `'dSPM'`, `'eLORETA'`. Requires a
  forward model (lead field), co-registered electrode positions, and a head
  model.
- `nk.eeg_source_extract(sources, regions=[...])` — ROI time series from atlases
  (Desikan-Killiany, Destrieux, AAL) or Brodmann areas.

## Microstates

Microstates are ~80–120 ms periods of quasi-stable scalp topography, usually
reduced to 4–7 classes (commonly A/B/C/D). Standard pipeline:

```python
cleaned = nk.microstates_clean(eeg, sampling_rate=250)      # band-pass, avg ref
k = nk.microstates_findnumber(cleaned, show=True)           # GEV / KL criterion
ms = nk.microstates_segment(cleaned, n_microstates=k,       # cluster templates
                            sampling_rate=250, method="kmod")
ms = nk.microstates_classify(ms)                            # relabel to A/B/C/D
static = nk.microstates_static(ms)                          # duration/coverage
dynamic = nk.microstates_dynamic(ms)                        # transitions
nk.microstates_plot(ms, cleaned)
```

- `microstates_segment(...)` clustering `method=`: `'kmod'` (modified,
  polarity-invariant k-means; default and most common), `'kmeans'`,
  `'kmedoids'`, `'pca'`, `'ica'`, `'aahc'`. Returns `'maps'`, `'labels'`,
  `'gfp'`, `'gev'`. Increase `n_inits` for stability.
- `microstates_findnumber(...)` — Global Explained Variance elbow (aim 70–80%)
  and Krzanowski-Lai criterion.
- `microstates_static(...)` — per-class **duration** (ms), **occurrence** (/s),
  **coverage** (%), **GEV**.
- `microstates_dynamic(...)` — transition matrix, transition rate, entropy of
  transitions, Markov test.
- `microstates_peaks(...)` — GFP-peak indices (microstates are typically fit at
  GFP peaks to cut noise and cost).

## MNE bridges

- `nk.mne_data(dataset='sample')` — sample datasets (`'sample'`, `'ssvep'`,
  `'eegbci'`).
- `nk.mne_to_df(raw)` / `nk.mne_to_dict(epochs)` — MNE → NeuroKit-friendly.
- `nk.mne_channel_extract(raw, [...])` / `nk.mne_channel_add(raw, data, ch_name)`.
- `nk.mne_crop(raw, tmin, tmax)`; `nk.mne_templateMRI()` — fsaverage template for
  source analysis without an individual MRI.

## Practical guidance

- **Sampling**: ≥ 100 Hz for power; 250–500 Hz standard; 1000+ Hz for fine
  temporal dynamics.
- **Duration**: ≥ 2 min for stable power; 2–5+ min for microstates; ERPs need
  ≥ ~30 trials per condition.
- **Artifacts**: remove blinks via ICA/regression (see `emg-eog.md` for EOG
  channels), high-pass ≥ 1 Hz for muscle, notch at 50/60 Hz, interpolate bad
  channels before analysis.
- **Power workflow**: `signal_filter` band-pass → `eeg_badchannels` (interpolate)
  → `eeg_rereference('average')` → `eeg_power`.

## Key references

- Michel & Koenig (2018), *NeuroImage* 180. Microstate review.
- Pascual-Marqui et al. (1995), *IEEE TBME* 42(7). Microstate segmentation.
- Gramfort et al. (2013), *Front. Neurosci.* 7:267. MNE-Python.
