---
name: wavelet-decomposition
version: 0.1.0
description: Discrete (DWT) and continuous (CWT) wavelet decomposition via PyWavelets. Use when denoising OHLCV/return series before feeding a model, extracting multi-scale features (regime-band approximation + high-frequency details), or visualizing a time-frequency map of a price chirp. Pairs well with statsmodels/sklearn downstream. For Kalman-style online state tracking, see the kalman-filter skill instead.
allowed-tools: Read, Write, Edit, Bash
license: MIT
metadata:
    skill-author: HyperFrequency
---

# Wavelet Decomposition for Time-Series (PyWavelets)

## Overview

PyWavelets (`pywt`) provides forward/inverse Discrete Wavelet Transform (DWT) and Continuous Wavelet Transform (CWT) in 1D/2D/nD with 100+ built-in wavelet filters (Daubechies, Symlets, Coiflets, Morlet, Mexican Hat, etc.). For quant work it is the standard tool for splitting a price or return series into a smooth approximation plus detail bands at multiple scales, then either thresholding the detail coefficients to denoise or feeding the bands to a downstream model as features.

## When to Use This Skill

- **Denoise OHLCV / returns before model training.** Apply `wavedec` with a smooth wavelet (e.g. `'sym8'`), soft-threshold the detail coefficients using a VisuShrink estimate, then `waverec` back to a denoised series before computing indicators or training a forecaster.
- **Multi-scale features.** Decompose returns into approximation + per-level detail bands (cD1 ~ highest-frequency noise, cD4 ~ slow regime moves) and feed each band as a separate feature column to a tree model or neural net.
- **Time-frequency localization (CWT).** Use `pywt.cwt` with Morlet to produce a scalogram showing when high-frequency volatility bursts occur in a chirp-like price series — useful for regime/event detection where Fourier loses temporal info.
- **Compression / dimensionality reduction.** Keep only the largest-magnitude coefficients and reconstruct, getting a parsimonious representation of a long series.

## Install / Setup

```bash
pip install PyWavelets matplotlib numpy
# Conda alternative:
# conda install -c conda-forge pywavelets
```

PyWavelets v1.9.0 supports NumPy 2.x. No GPU dependency. CWT with `method='fft'` is faster for long signals.

## Minimal Example: Denoising a Price Series with DWT

```python
import numpy as np
import pywt
import matplotlib.pyplot as plt

# 1. Synthetic "price" = trend + cycle + noise (replace with real close series)
rng = np.random.default_rng(0)
t = np.linspace(0, 1, 1024)
clean = 100 + 5 * t + 2 * np.sin(2 * np.pi * 5 * t)
price = clean + rng.normal(0, 0.6, size=t.size)

# 2. Multilevel decomposition with Daubechies-4
wavelet = 'db4'
level = 4
coeffs = pywt.wavedec(price, wavelet, mode='symmetric', level=level)
# coeffs = [cA4, cD4, cD3, cD2, cD1]

# 3. VisuShrink threshold from finest detail band
sigma = np.median(np.abs(coeffs[-1])) / 0.6745
threshold = sigma * np.sqrt(2 * np.log(len(price)))

# 4. Soft-threshold details, keep approximation as-is
denoised_coeffs = [coeffs[0]] + [
    pywt.threshold(c, threshold, mode='soft') for c in coeffs[1:]
]
denoised = pywt.waverec(denoised_coeffs, wavelet, mode='symmetric')[: len(price)]

# 5. Plot bands + denoised vs noisy
fig, axes = plt.subplots(level + 2, 1, figsize=(10, 8), sharex=False)
axes[0].plot(t, price, label='noisy'); axes[0].plot(t, denoised, label='denoised'); axes[0].legend()
axes[1].plot(coeffs[0]); axes[1].set_ylabel(f'cA{level}')
for i, cd in enumerate(coeffs[1:], start=1):
    axes[i + 1].plot(cd); axes[i + 1].set_ylabel(f'cD{level - i + 1}')
plt.tight_layout(); plt.show()
```

WARNING: in a live/backtest context, `mode='symmetric'` reflects the signal at the right edge — that introduces look-ahead. See **Common Pitfalls** below.

## Second Example: CWT Scalogram for Time-Frequency Localization

Use when you want to see *when* high-frequency volatility appears, not just *that* it appears. Good for event/regime detection that Fourier flattens out.

```python
import numpy as np
import pywt
import matplotlib.pyplot as plt

# Chirp-like return series: frequency rises over time
n = 1024
dt = 1.0 / 252  # daily bars
t = np.arange(n) * dt
freq_t = np.linspace(2, 30, n)               # cycles per year, time-varying
returns = 0.01 * np.cos(2 * np.pi * freq_t * t) + 0.002 * np.random.default_rng(0).standard_normal(n)

# Log-spaced scales covering the frequency band of interest
scales = np.logspace(np.log10(1), np.log10(128), 64)
coefs, freqs = pywt.cwt(returns, scales, 'morl', sampling_period=dt, method='fft')

# Scalogram (|coefficients|) — rows = scale/freq, cols = time
plt.figure(figsize=(10, 4))
plt.imshow(np.abs(coefs), aspect='auto',
           extent=[t[0], t[-1], freqs[-1], freqs[0]], cmap='viridis')
plt.colorbar(label='|CWT|'); plt.ylabel('frequency (cycles / year)')
plt.xlabel('time (years)'); plt.tight_layout(); plt.show()
```

The bright band sloping upward shows the chirp's frequency increasing through time — Fourier would only show all frequencies present in aggregate.

## Workflow: Multi-Scale Features for a Downstream Model

1. On each rolling window ending at bar `t`, run `pywt.wavedec(window, 'sym8', level=4)`.
2. Reconstruct *each band individually* by zeroing out the other coefficient arrays and calling `pywt.waverec`. This gives you N+1 same-length series: one approximation, N detail bands.
3. Take the last value of each reconstructed band as the feature row at time `t` (avoids ragged output and ensures only past data is used in this window).
4. Concatenate over time -> a `(T, N+1)` feature matrix. Use as inputs to an XGBoost / linear / NN forecaster of next-bar return.
5. Validate with a strict walk-forward split. Compare lift against the raw-return baseline; if bands don't beat raw, the wavelet step is buying nothing.

## Key API Surface

| Function / Class | Purpose |
|---|---|
| `pywt.wavedec(data, wavelet, mode, level)` | Multilevel DWT decomposition. Returns `[cA_n, cD_n, ..., cD_1]`. |
| `pywt.waverec(coeffs, wavelet, mode)` | Inverse multilevel DWT. Reconstructs (possibly modified) signal. |
| `pywt.dwt(data, wavelet, mode)` / `pywt.idwt` | Single-level forward / inverse DWT. |
| `pywt.dwt_max_level(data_len, wavelet)` | Max safe decomposition level for a given length and filter. |
| `pywt.threshold(data, value, mode)` | Soft / hard / garrote / greater / less thresholding of coefficient arrays. |
| `pywt.threshold_firm(data, low, high)` | Two-threshold firm (semi-soft) shrinkage. |
| `pywt.cwt(data, scales, wavelet, sampling_period, method)` | Continuous Wavelet Transform. Returns `(coefs, frequencies)`. |
| `pywt.scale2frequency(wavelet, scale)` / `pywt.frequency2scale` | Convert between CWT scale and physical frequency. |
| `pywt.Wavelet(name)` / `pywt.ContinuousWavelet(name)` | Wavelet objects (filter banks). |
| `pywt.wavelist(kind='discrete'\|'continuous')` | List available wavelet names. |
| `pywt.Modes.modes` | Available boundary modes (`'symmetric'`, `'periodic'`, `'zero'`, `'reflect'`, `'periodization'`, `'antireflect'`, etc.). |

## Choosing Parameters

**Wavelet family (DWT, OHLCV).** Start with `'db4'` or `'sym8'` for smooth price series. Daubechies (`db`) wavelets are compactly supported and orthogonal; Symlets (`sym`) are near-symmetric Daubechies variants with less phase distortion — usually preferred when the reconstructed series will be plotted alongside the raw series. For very smooth approximations consider `'coif5'`. For sparse, spiky returns try `'haar'` (db1) — fast, but blocky reconstruction.

**Level.** `pywt.dwt_max_level(N, wavelet)` gives the absolute ceiling, but you rarely want to go that deep. For daily OHLCV with N around 1000–5000 bars, levels 4–6 is typical: cD1–cD3 capture short-term noise, cD4+ captures multi-day regime moves. Each extra level halves resolution in the approximation.

**Threshold.** `sigma = median(|cD1|) / 0.6745` is the standard MAD-based noise estimate. `threshold = sigma * sqrt(2 * log(N))` is VisuShrink (universal threshold). Use soft mode for smoother reconstructions, hard mode if you want to keep large jumps undistorted.

**Boundary mode.** `'symmetric'` (default) is best for offline analysis. For causal / online use, see pitfalls below — `'periodization'` keeps coefficient lengths short but distorts edges; `'zero'` is honest but introduces edge artifacts. There is no truly causal DWT in `pywt`; a common workaround is to recompute the transform on each rolling window of historical data.

**CWT scales.** `np.logspace(log10(s_min), log10(s_max), n)` over scales 1..N/4 is a reasonable default. Use `pywt.scale2frequency('morl', scale) / dt` to map scales to Hz, then pick a scale range covering the frequency band you care about.

**Validation.** Track reconstruction error `np.max(np.abs(signal - pywt.waverec(coeffs, w)))` — should be ~1e-12 for orthogonal wavelets if no thresholding is applied. Track denoised-vs-clean RMSE on a synthetic benchmark before trusting on live data. For features, evaluate downstream model lift, not in-sample SNR.

### Cheatsheet: Picking a Wavelet Family

| Family prefix | Typical use | Properties |
|---|---|---|
| `haar` / `db1` | Jump detection, fastest | Discontinuous, blocky reconstruction. |
| `db2`–`db10` | General-purpose denoising | Orthogonal, compactly supported, asymmetric. |
| `sym4`–`sym10` | Smoothed price denoising | Near-symmetric Daubechies; less phase distortion than `db`. |
| `coif1`–`coif5` | Very smooth approximation | Longer support, more vanishing moments. |
| `bior` / `rbior` | When you want different filters for decomp vs reconstruction | Biorthogonal — exact reconstruction without orthogonality constraint. |
| `morl` (CWT) | Time-frequency localization | Complex Morlet — good frequency resolution. |
| `mexh` (CWT) | Spike / edge detection | Mexican Hat — real-valued, sharp peaks. |
| `cmor`, `gausN` (CWT) | Tunable bandwidth | Complex Morlet with adjustable center frequency. |

`pywt.wavelist(kind='discrete')` and `pywt.wavelist(kind='continuous')` enumerate everything available at runtime.

## Common Pitfalls

1. **Look-ahead via symmetric padding.** Default `mode='symmetric'` reflects the signal at the right boundary, meaning the last few coefficients (and the last few reconstructed samples) are functions of *future* values that the live trader does not have. For any backtest or live use, recompute the DWT on a rolling window ending at `t` and only use the latest reconstructed point at `t` — never decompose the whole series at once and slice. (Unverified: a fully causal DWT variant exists in research literature but is not in `pywt`.)
2. **Length mismatch after `waverec`.** Reconstruction length can be off by 1 from the original due to filter-length parity. Always slice: `denoised = pywt.waverec(...)[: len(original)]`.
3. **Choosing too many levels.** Going to `dwt_max_level` produces an approximation of only a few samples; downstream interpretation breaks and threshold estimates become unstable. Cap at 4–6 for typical bar counts.
4. **Thresholding the approximation.** Only threshold detail coefficients (`coeffs[1:]`). Touching `coeffs[0]` distorts the trend.
5. **Misreading CWT scales as frequency.** Scale is inversely related to frequency but with a wavelet-specific constant (the central frequency). Use `pywt.scale2frequency` rather than assuming `f = 1 / scale`.
6. **Wavelet-family mismatch with assumptions.** `'haar'` produces piecewise-constant reconstructions that look like staircases — fine for jump detection, bad if you want a smooth denoised price for an SMA crossover system.
7. **Treating CWT output as features without normalization.** CWT coefficient magnitudes scale with wavelet energy at each scale and aren't directly comparable across rows of the scalogram. If you flatten the scalogram into ML features, normalize per-scale (e.g. divide each row by its standard deviation) or use `np.abs(coefs) ** 2` (energy) for a more interpretable comparison across scales.

## Quick Sanity Checks

Before reporting any wavelet-based result, run these three checks:

- `pywt.wavedec` then `pywt.waverec` on the raw input with no thresholding — max abs difference should be ~1e-12 for orthogonal wavelets like `db`/`sym`. If it's larger, the boundary mode or wavelet choice is causing exact-reconstruction failure.
- Re-compute the DWT on `signal[:-1]` (drop the last bar) and compare the second-to-last reconstructed value to the same point in the original full-signal DWT. If they differ noticeably, you have boundary look-ahead and any backtest using this reconstruction is leaking future info.
- Plot the denoised series on top of raw and zoom in on a known spike — a good denoiser smooths microstructure noise but preserves the spike timing. A staircased or shifted spike is a red flag.

## References

### Primary library
- [PyWavelets/pywt](https://github.com/PyWavelets/pywt) — upstream repo (issues, releases, the C/Cython kernel that powers the Python API)
- [PyWavelets docs](https://pywavelets.readthedocs.io/en/latest/) — cross-checked against `1.9.0` (current at the time of this skill)
- [Installing PyWavelets](https://pywavelets.readthedocs.io/en/latest/install.html) — covers pip + conda; conda-forge usually has the fresher wheel for Apple silicon
- [Demo gallery](https://pywavelets.readthedocs.io/en/latest/regression/index.html) — runnable demos in the docs
- [Changelog](https://pywavelets.readthedocs.io/en/latest/index.html#release-notes) — wavelet families occasionally get added or have their filter coefficients corrected

### Deep-dive docs (specific pages worth bookmarking)
- [`pywt.wavedec` / `pywt.waverec`](https://pywavelets.readthedocs.io/en/latest/ref/dwt-discrete-wavelet-transform.html) — multilevel DWT and inverse; the workhorses for denoising
- [Signal extension modes](https://pywavelets.readthedocs.io/en/latest/ref/signal-extension-modes.html) — `symmetric`, `periodization`, `zero`, `constant`; mis-matching modes between `wavedec` and `waverec` is a common boundary-leakage source
- [`pywt.threshold`](https://pywavelets.readthedocs.io/en/latest/ref/thresholding-functions.html) — `soft`, `hard`, `garrote`, `greater`, `less`; the differences matter for spike preservation
- [Stationary (a-trous) wavelet transform](https://pywavelets.readthedocs.io/en/latest/ref/swt-stationary-wavelet-transform.html) — `pywt.swt` / `iswt`; translation-invariant; the right tool when you're going to feed coefficients to an ML model
- [Continuous wavelet transform (CWT)](https://pywavelets.readthedocs.io/en/latest/ref/cwt.html) — `pywt.cwt`; spectrograms for non-stationary signals (regime detection)
- [Wavelet packets](https://pywavelets.readthedocs.io/en/latest/ref/wavelet-packets.html) — `pywt.WaveletPacket`; full decomposition tree (vs DWT's approximation-only deeper split)
- [Wavelet families](https://pywavelets.readthedocs.io/en/latest/ref/wavelets.html) — `db`, `sym`, `coif`, `bior`, `rbio`, `dmey`, `haar`, `meyr`; quants almost always want `db4` / `sym8` / `coif5` for time-domain work

### Adjacent / alternative libraries
- [`scipy.signal.cwt` / `scipy.signal.ricker`](https://docs.scipy.org/doc/scipy/reference/signal.html) — minimal CWT inside SciPy; no DWT support, but good for one-off Morlet / Ricker plots
- [`ssqueezepy`](https://github.com/OverLordGoldDragon/ssqueezepy) — synchrosqueezed CWT/STFT; sharper time-frequency localisation than vanilla CWT
- [`wavelets`](https://github.com/aaren/wavelets) — Torrence-and-Compo style CWT with significance testing; the climate-science default port
- [`pytorch-wavelets`](https://github.com/fbcotter/pytorch_wavelets) — DWT as a differentiable `nn.Module`; needed if you want wavelet layers inside a network

### Academic papers
- Mallat, S. G. (1989). "A Theory for Multiresolution Signal Decomposition: The Wavelet Representation." *IEEE Transactions on Pattern Analysis and Machine Intelligence* 11(7), 674–693. [doi:10.1109/34.192463](https://doi.org/10.1109/34.192463) — the pyramidal DWT algorithm `pywt.wavedec` implements
- Daubechies, I. (1988). "Orthonormal bases of compactly supported wavelets." *Communications on Pure and Applied Mathematics* 41(7), 909–996. [doi:10.1002/cpa.3160410705](https://doi.org/10.1002/cpa.3160410705) — the construction behind the `db1`–`db20` family
- Donoho, D. L. & Johnstone, I. M. (1994). "Ideal spatial adaptation by wavelet shrinkage." *Biometrika* 81(3), 425–455. [doi:10.1093/biomet/81.3.425](https://doi.org/10.1093/biomet/81.3.425) — the universal threshold (`σ √(2 log N)`) used in most wavelet denoisers
- Torrence, C. & Compo, G. P. (1998). "A Practical Guide to Wavelet Analysis." *Bulletin of the American Meteorological Society* 79(1), 61–78. [doi:10.1175/1520-0477(1998)079<0061:APGTWA>2.0.CO;2](https://doi.org/10.1175/1520-0477(1998)079%3C0061:APGTWA%3E2.0.CO;2) — the canonical reference for CWT with significance testing (cone of influence, red-noise nulls)

### Tutorials & write-ups
- [Wavelet browser (pybytes)](http://wavelets.pybytes.com/) — interactive viewer of every PyWavelets filter family
- [PyWavelets gallery](https://pywavelets.readthedocs.io/en/latest/regression/index.html) — official, end-to-end signal demos

### Last cross-checked
2026-05-20 — via Context7 `/pywavelets/pywt` (v1.9.0) + `/websites/pywavelets_readthedocs_io_en`; Auggie not indexed.
