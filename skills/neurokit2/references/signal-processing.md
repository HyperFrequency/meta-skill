# General Signal Processing

Modality-agnostic utilities that operate on any 1-D series. The signal-specific
pipelines are built on these, but you can call them directly for custom
preprocessing or non-physiological data.

## Filtering and cleaning

- `nk.signal_filter(signal, sampling_rate, lowcut=None, highcut=None, method='butterworth', order=5)`
  — the filter type follows the cutoffs: `highcut` only = low-pass, `lowcut`
  only = high-pass, both = band-pass. Methods: `'butterworth'` (safe default),
  `'bessel'` (linear phase), `'chebyshev1/2'`, `'elliptic'`, `'powerline'`
  (50/60 Hz notch via `powerline=`). Higher `order` = steeper rolloff but more
  ringing; 2–5 is typical for physiological signals.
- `nk.signal_sanitize(signal, interpolate=True)` — strip NaN/inf, optionally
  interpolate.
- `nk.signal_resample(signal, sampling_rate, desired_sampling_rate, method='interpolation')`
  — `'interpolation'` (cubic spline), `'FFT'`, `'poly'` (best for downsampling).
- `nk.signal_fillmissing(signal, method='linear')` — `'linear'`, `'nearest'`,
  `'pad'`, `'cubic'`, `'polynomial'`.
- `nk.signal_flatline(signal, duration, sampling_rate)` — boolean mask of
  constant-signal (sensor-failure) regions.
- `nk.signal_smooth(signal, method='convolution', kernel='boxzen', size=10)` —
  `'convolution'` (boxcar/gaussian/hann/...), `'median'`, `'savgol'` (peak-
  preserving), `'loess'`.

## Transformation and decomposition

- `nk.signal_detrend(signal, method='polynomial', order=1)` — `'polynomial'`,
  `'loess'`, `'tarvainen2002'` (smoothness-priors, good for HRV).
- `nk.signal_decompose(signal, sampling_rate, method='emd')` — data-adaptive
  decomposition. `'emd'` → Intrinsic Mode Functions (high→low frequency);
  `'ssa'` → trend/oscillation/noise via trajectory-matrix eigendecomposition.
  `nk.signal_recompose(components, indices=[...])` reconstructs from selected
  components (adaptive filtering).
- `nk.signal_binarize(signal, method='threshold', threshold=0.5)` — to 0/1 via
  `'threshold'`, `'median'`, `'mean'`, `'quantile'`.
- `nk.signal_interpolate(x, y, x_new=None, method='quadratic')`,
  `nk.signal_merge(...)` — align/combine series on different time bases.

## Peaks

- `nk.signal_findpeaks(signal, height_min=None, height_max=None, relative_height_min=None, relative_height_max=None)`
  — generic local maxima; also `threshold` (prominence) and `distance`
  (min samples apart). Returns `'Peaks'`, `'Height'`, `'Distance'`.
- `nk.signal_fixpeaks(peaks, sampling_rate, iterative=True, method='Kubios', interval_min=None, interval_max=None)`
  — correct implausible/missing/duplicate peaks. Methods: `'Kubios'` (default),
  `'Malik1996'`, `'Kamath1993'`. This is the engine behind R-R artifact
  correction.

## Spectral and rate analysis

- `nk.signal_rate(peaks, sampling_rate, desired_length=None)` — events/min from
  inter-event intervals.
- `nk.signal_period(signal, sampling_rate, method='autocorrelation')` — dominant
  period/frequency; `'autocorrelation'` or `'powerspectraldensity'`.
- `nk.signal_phase(signal, method='hilbert')` — instantaneous phase (`'hilbert'`
  or `'wavelet'`) for phase-locking / PAC.
- `nk.signal_psd(signal, sampling_rate, method='welch', max_frequency=None)` —
  returns `(psd, freqs)`. Methods `'welch'`, `'multitapers'`, `'lomb'`, `'burg'`.
- `nk.signal_power(signal, sampling_rate, frequency_bands={...}, method='welch')`
  — absolute/relative power per named band (e.g. HRV VLF/LF/HF).
- `nk.signal_autocor(signal, lag=..., show=False)`,
  `nk.signal_zerocrossings(signal)` — periodicity and rough frequency.
- `nk.signal_timefrequency(signal, sampling_rate, method='stft', max_frequency=...)`
  — spectrogram; `'stft'` or `'cwt'`. Returns `(tf, time, freq)`.

## Change detection and synchrony

- `nk.signal_changepoints(signal, penalty=10, method='pelt')` — abrupt mean/
  variance shifts (`'pelt'` exact, `'binseg'` faster). Higher penalty = fewer
  changepoints; use to auto-segment states.
- `nk.signal_synchrony(signal1, signal2, method='correlation')` — coupling via
  `'correlation'`, `'coherence'`, `'mutual_information'`, or `'phase'` (phase-
  locking value). For heart-brain, inter-brain, or multi-channel coordination.

## Testing helpers

- `nk.signal_distort(signal, sampling_rate, noise_amplitude=..., noise_frequency=..., artifacts_amplitude=...)`
  and `nk.signal_noise(signal, sampling_rate, noise_type='gaussian', amplitude=...)`
  (`'gaussian'`, `'pink'`, `'brown'`, `'powerline'`) — inject controlled noise
  for robustness testing.
- `nk.signal_surrogate(signal, method='IAAFT')` — surrogate data preserving
  amplitude distribution + spectrum (`'IAAFT'`) or a shuffle, for nonlinearity
  null tests.
- `nk.signal_simulate(duration, sampling_rate, frequency=[...], amplitude=[...], noise=...)`,
  `nk.signal_plot(signal, sampling_rate, peaks=None)`.

## Practical tips

- Set `lowcut` below and `highcut` above the band of interest; start `order` at
  2–5. Filtering distorts signal edges — pad then trim, or discard the first and
  last seconds. Downsample early to speed a pipeline. A typical chain:

```python
sig = nk.signal_sanitize(raw)
sig = nk.signal_filter(sig, sampling_rate=1000, lowcut=0.5, highcut=40)
sig = nk.signal_detrend(sig, method="polynomial", order=1)
```

## Key references

- Tarvainen et al. (2002), *IEEE TBME* 49(2). Smoothness-priors detrending.
- Huang et al. (1998), *Proc. R. Soc. A* 454. Empirical mode decomposition.
