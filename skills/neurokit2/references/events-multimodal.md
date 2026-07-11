# Events, Epochs, and Multi-Signal Integration

Two related workflows: (1) cut a continuous recording into stimulus-locked
epochs for event-related analysis, and (2) process several synchronized signals
together with the `bio_*` wrappers.

---

# Event detection and epoching

## Find events

```python
events = nk.events_find(event_channel, threshold=0.5, threshold_keep="above",
                        duration_min=1, inter_min=0)
```

Detects threshold crossings in a trigger/marker channel. Returns a dict with
`'onset'`, `'offset'`, `'duration'`, and `'label'`. `threshold='auto'` derives a
cutoff from the signal. Use `duration_min` to debounce (e.g. button presses) and
`inter_min` to enforce a refractory gap. `nk.events_plot(events, signal)`
overlays markers for QC.

## Create epochs

```python
epochs = nk.epochs_create(data, events, sampling_rate=1000,
                          epochs_start=-1.0, epochs_end=5.0,
                          event_labels=None, event_conditions=None,
                          baseline_correction=False)
```

Returns a **dict of DataFrames**, one per epoch, indexed by time relative to the
event (index 0 = onset). `epochs_start` negative = pre-stimulus baseline.
`event_labels` / `event_conditions` attach `'Label'` / `'Condition'` columns for
later grouping. `baseline_correction=True` subtracts each epoch's baseline mean.

Typical windows: visual ERP −0.2 to 1.0 s; cardiac orienting −1 to 10 s; EMG
startle −0.1 to 0.5 s; EDA SCR −1 to 10 s (slow latency and recovery).

Access and filter:

```python
epoch_1 = epochs["1"]
positive = {k: v for k, v in epochs.items() if v["Condition"][0] == "positive"}
```

Baseline-correct when isolating event-related change (always for ERPs, usually
for cardiac/EDA); skip it when absolute amplitude matters.

## Average, convert, visualize

- `nk.epochs_average(epochs, output='dict')` — grand average with `'Mean'`,
  `'SD'`, `'SE'`, `'CI_lower'`, `'CI_upper'` per time point (compute per
  condition by averaging filtered sub-dicts).
- `nk.epochs_to_df(epochs)` — stacked long DataFrame (`Epoch`, `Time`, `Label`,
  `Condition`) for pandas/seaborn or export.
- `nk.epochs_to_array(epochs, column='ECG_Rate')` — 3-D array
  `(n_epochs, n_timepoints, n_columns)` for ML.
- `nk.epochs_plot(epochs, column='ECG_Rate', condition=None)`.

## Per-signal event-related analysis

After epoching processed signals, each modality has an event-related summarizer
(all take the epochs dict): `nk.ecg_eventrelated`, `nk.ppg_eventrelated`,
`nk.rsp_eventrelated`, `nk.eda_eventrelated`, `nk.emg_eventrelated`,
`nk.eog_eventrelated`. See each modality's reference for its metric columns.

## Statistical hygiene

- 20–30+ trials/condition for stable averages; mixed-effects models handle
  variable trial counts.
- Pre-register time windows; picking windows from the observed data is circular.
- Correct for multiple comparisons across time points and signals.
- Reject artifact epochs before analysis, e.g.:

```python
clean = {k: e for k, e in epochs.items()
         if e["EDA_Phasic"].abs().max() < 5.0
         and (e["ECG_Rate"].max() - e["ECG_Rate"].min()) < 50}
results = nk.ecg_eventrelated(clean)
```

NeuroKit2 extracts these features; run the actual inferential tests in
`statistical-analysis`, `statsmodels`, or `pymc`, and classification in
`scikit-learn`.

---

# Multi-signal integration (`bio_*`)

## Process many signals at once

```python
bio_signals, bio_info = nk.bio_process(ecg=None, rsp=None, eda=None, emg=None,
                                       ppg=None, eog=None, sampling_rate=1000)
```

Each supplied signal is routed to its dedicated `*_process()` function and the
results are merged into one time-aligned DataFrame (`ECG_Clean`, `ECG_Rate`,
`RSP_Rate`, `EDA_Phasic`, ...). `bio_info` nests per-signal peak dicts, e.g.
`bio_info["ECG"]["ECG_R_Peaks"]`. Signals at different native rates are resampled
to the target `sampling_rate` internally; if you prefer, process each modality at
its native rate and merge manually with `nk.signal_resample()` + `pd.concat`.

## Analyze

```python
results = nk.bio_analyze(bio_signals, sampling_rate=1000)
```

Duration-aware (event- vs interval-related) summary across every detected
modality: ECG/PPG rate + full HRV, RSP rate + RRV, EDA SCR count/amplitude/tonic
+ sympathetic, EMG activation, EOG blink rate. When both ECG and RSP are present
it also returns cross-signal **RSA** automatically. Access columns like
`results["ECG_Rate_Mean"]`, `results["HRV_RMSSD"]`, `results["RSP_Rate_Mean"]`,
`results["SCR_Peaks_N"]`, `results["RSA"]`.

## Cross-signal features

- **RSA** — auto-computed with ECG + RSP; higher RSA = greater vagal influence.
- **ECG-derived respiration** — `nk.ecg_rsp(ecg_clean, sampling_rate)` when no
  respiration channel exists.
- **Cardio-EDA / coupling** — correlate `bio_signals["ECG_Rate"]` with
  `bio_signals["EDA_Phasic"]`, or use `nk.signal_synchrony()` for coherence /
  phase-locking.

## Multi-modal considerations

- **Synchronization** — signals from one device are inherently aligned; across
  devices, use a shared hardware trigger and verify alignment by cross-
  correlating a redundant channel.
- **Convergent vs discriminant validity** — multiple indices converging on
  "arousal" is more robust than any single one, but ECG reflects both autonomic
  branches while EDA is primarily sympathetic — they can dissociate.
- **Multiple comparisons** — more signals means more tests; use multivariate or
  pre-registered analyses and correct for Type I error.
- **Cost** — processing many channels is heavier; batch large datasets and
  downsample where the science allows.

## Key references

- Luck (2014), *An Introduction to the ERP Technique* (2nd ed.), MIT Press.
- Berntson et al. (1993), *Psychophysiology* 30(2). RSA mechanisms.
- Laborde et al. (2017), *Front. Psychol.* 8:213. HRV/vagal-tone reporting.
