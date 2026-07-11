# Theory, Parameters, and Pitfalls

The reasoning behind the estimators in `workflows.md`, the parameter choices
that matter, and a troubleshooting table.

## Sampling, Nyquist, and aliasing

- A signal sampled at rate `fs` can only represent frequencies below the
  **Nyquist frequency** `fs/2`. Anything above folds back (aliases) and appears
  as a spurious lower-frequency peak — indistinguishable from a real one after
  the fact.
- Guard rule: `fs ≥ 2·f_max`, and in practice oversample (3–5x) so a realizable
  anti-alias filter can roll off before Nyquist.
- If you suspect aliasing, resample the analog source higher or apply an analog
  low-pass *before* digitizing. No post-hoc software fix recovers aliased content.

## Spectral leakage and window functions

A finite record of a tone that is not periodic in the window smears its energy
across neighboring bins (leakage). A taper (window) that goes smoothly to zero
at the edges suppresses the far side-lobes, at the cost of a wider main lobe
(coarser peak localization). Pick by what you need to see:

| Window | Main lobe | Side-lobe suppression | Use when |
|---|---|---|---|
| `boxcar` (none) | narrowest | worst (~13 dB) | isolating two very close equal-amplitude tones |
| `hann` | moderate | ~31 dB | general-purpose default |
| `hamming` | moderate | ~43 dB | slightly better first side-lobe than Hann |
| `blackman` | wide | ~58 dB | a weak tone sits near a strong one |
| `flattop` | widest | excellent | accurate *amplitude* readout, not frequency |

Windows live in `scipy.signal.windows`; pass the name to `welch`/`spectrogram`
via `window=`.

## Frequency resolution vs. variance

- Resolution: `Δf = fs / nperseg`. To separate two peaks `δf` apart you need
  `nperseg > fs/δf` (roughly; a wider window makes it more forgiving).
- Variance: Welch averages `≈ (N - noverlap) / (nperseg - noverlap)` segments.
  More segments → smoother PSD but fewer means coarser `Δf`. This is the
  fundamental trade — resolve it in favor of the question being asked.
- 50% overlap (`noverlap = nperseg//2`) with a Hann window recovers most of the
  variance reduction without double-counting; more overlap helps marginally.
- `average="median"` in `welch` is robust when transient spikes would bias the
  mean PSD upward.

## Detrending and the DC component

A nonzero mean concentrates enormous power in bin 0 and, through leakage,
inflates the lowest frequencies. A linear trend does the same across a broader
low-frequency band. `welch`/`periodogram` apply `detrend="constant"` per
segment by default; for a raw `np.fft.rfft` subtract the mean (or fit and
remove a line) yourself before transforming.

## PSD units, scaling, and Parseval

- `scaling="density"` → power spectral **density** in `V²/Hz`. Integrating it
  over frequency returns the signal variance (Parseval). Use for broadband /
  noise-like content and for comparing across different `fs`/window lengths.
- `scaling="spectrum"` → power **spectrum** in `V²`, power concentrated per bin.
  Use for discrete tones where you want the power *of the line*.
- Amplitude vs. power: a raw single-sided FFT amplitude is `2/N · |X|` (with DC
  and Nyquist not doubled); PSD is proportional to `|X|²` normalized by `fs` and
  the window's noise-equivalent bandwidth. Report which quantity a plot shows.

## Zero-padding is interpolation, not resolution

Appending zeros before the FFT increases the number of output bins, producing a
smoother, denser-looking curve. It does **not** improve the ability to separate
two nearby frequencies — that is set only by the record length (`nperseg`).
Zero-pad to make a peak easier to read off; lengthen the record to actually
resolve more.

## Unevenly sampled data — do not FFT it

The FFT/Welch/spectrogram machinery assumes uniform `dt`. For irregular or gappy
sampling (common in astronomy, ecology, clinical data) use the **Lomb-Scargle**
periodogram, which fits sinusoids by least squares at each trial frequency:

```python
import numpy as np
from scipy.signal import lombscargle

# t_irr, y_irr are the (non-uniform) sample times and values
ang = 2*np.pi*np.linspace(0.01, 200, 5000)          # ANGULAR frequencies [rad/s]
power = lombscargle(t_irr, y_irr - y_irr.mean(), ang, normalize=True)
freqs_hz = ang / (2*np.pi)
```

`scipy.signal.lombscargle` takes **angular** frequencies and requires
mean-subtracted input. For a higher-level interface with automatic frequency
grids, false-alarm probabilities, and multi-term models, use Astropy's
`astropy.timeseries.LombScargle` (see the `astropy` skill).

## Assessing peak significance

The raw periodogram is a noisy estimate; a tall bin is not automatically a real
oscillation. Options, in rough order of rigor: (1) Welch-average and look for a
peak stable across segments; (2) compare peak height to the local noise floor;
(3) for Lomb-Scargle, use the analytic or bootstrap false-alarm probability; (4)
for formal tests, confidence intervals, or model selection, hand off to
`statistical-analysis`.

## SciPy / library version notes

- **`scipy.signal.cwt`, `morlet`, `morlet2`, `ricker` are removed** (deprecated
  1.12, removed 1.15). Use `pywt.cwt` from PyWavelets instead — see
  `workflows.md` §4. An `ImportError` on these names means SciPy ≥ 1.15.
- **`spectrogram` / `stft` / `istft` are legacy** in favor of `ShortTimeFFT`
  (SciPy ≥ 1.12). Both still work; prefer `ShortTimeFFT` for new code and when
  you need an invertible transform.
- `np.trapz` is deprecated for `np.trapezoid` in newer NumPy; either works on
  current releases.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Peak at a frequency that should not exist | Aliasing (`f > fs/2`) | Raise `fs`; anti-alias before sampling |
| Huge spike at 0 Hz swamps the plot | DC / mean not removed | `detrend="constant"` or subtract mean before FFT |
| Sharp tone smeared over many bins | Spectral leakage | Apply a window (Hann/Blackman); lengthen record |
| PSD too noisy / jagged | `nperseg` too long → few averages | Shorten `nperseg` or add overlap |
| PSD too smooth, peaks merged | `nperseg` too short → coarse `Δf` | Lengthen `nperseg` |
| Coherence is 1.0 at every frequency | Single segment (`nperseg == N`) | Shrink `nperseg` for ≥ 8 segments |
| Filtered signal has ringing / edge transients | High order or short/edgy record | Lower `order`; pad; use `sosfiltfilt` on a settled signal |
| Filtered signal is phase-shifted | One-directional filter (`sosfilt`) | Use `sosfiltfilt` / `filtfilt` for zero phase |
| `ImportError: cannot import name 'cwt'` | SciPy ≥ 1.15 removed it | Switch to `pywt.cwt` |
| Wrong Lomb-Scargle peaks | Passed Hz not angular freq, or non-zero mean | Use `2πf`; mean-subtract the input |
