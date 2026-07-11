# Estimator Recipes

Runnable code for each spectral estimator. All examples assume a uniformly
sampled 1-D array `x` with sampling rate `fs` (Hz) and `dt = 1/fs`. Import
`numpy as np` and `matplotlib.pyplot as plt` at the top.

A reusable test signal:

```python
import numpy as np
fs = 1000.0
t  = np.arange(0, 1, 1/fs)
x  = 1.5*np.sin(2*np.pi*50*t) + 0.8*np.sin(2*np.pi*120*t) + 0.5*np.random.randn(t.size)
```

## 1. FFT — single-sided amplitude and phase

Use for a short, stationary, low-noise record when you want the exact bins.
`rfft`/`rfftfreq` return only the non-negative half of the spectrum for a
real input.

```python
x = x - x.mean()                       # remove DC before the raw FFT
N = x.size
X = np.fft.rfft(x)
freqs = np.fft.rfftfreq(N, d=1/fs)

amp = (2.0 / N) * np.abs(X)            # single-sided amplitude...
amp[0] /= 2                            # ...but DC is not doubled
if N % 2 == 0:                         # ...nor is the Nyquist bin (even N)
    amp[-1] /= 2
phase = np.angle(X)                    # radians; only meaningful where amp is large
```

The `2/N` scaling recovers the true sinusoid amplitude; without the DC/Nyquist
correction those two bins are overstated by 2x.

## 2. Power spectral density — Welch and periodogram

Welch splits the record into overlapping windowed segments and averages their
periodograms, trading frequency resolution for a lower-variance estimate. The
periodogram is the single-segment (no averaging) limit — full resolution, high
variance.

```python
from scipy.signal import welch, periodogram

f_w, psd_w = welch(x, fs=fs, nperseg=256, noverlap=128, window="hann",
                   detrend="constant", scaling="density")   # V^2/Hz
f_p, psd_p = periodogram(x, fs=fs, window="boxcar", scaling="density")
```

Key `welch` parameters:

| Parameter | Meaning | Guidance |
|---|---|---|
| `nperseg` | segment length | resolution `Δf = fs/nperseg`; power of two is fast |
| `noverlap` | samples shared between segments | default `nperseg//2` (50%) |
| `window` | taper | `"hann"` default; `"blackman"` for deeper side-lobe suppression |
| `detrend` | per-segment detrend | `"constant"` (mean) or `"linear"`; `False` to disable |
| `scaling` | `"density"` → V²/Hz, `"spectrum"` → V² | density integrates to variance |
| `average` | `"mean"` or `"median"` | `"median"` is robust to transient spikes |

Integrate a density PSD over a band to get band power:

```python
band = (f_w >= 45) & (f_w <= 55)
band_power = np.trapz(psd_w[band], f_w[band])         # variance in 45–55 Hz
```

## 3. Spectrogram / STFT — time-frequency for non-stationary signals

The spectrogram slides a windowed FFT along the record. Window length fixes the
time-frequency resolution box: longer window → finer frequency, coarser time.

```python
from scipy.signal import spectrogram

# chirp: instantaneous frequency sweeps 10 → 200 Hz
tc = np.linspace(0, 2, 8000)
chirp = np.sin(2*np.pi * (10*tc + 47.5*tc**2))

f, tseg, Sxx = spectrogram(chirp, fs=4000, nperseg=256, noverlap=200,
                           window="hann", scaling="density")   # Sxx: V^2/Hz

plt.pcolormesh(tseg, f, 10*np.log10(Sxx + 1e-20), shading="gouraud", cmap="inferno")
plt.ylabel("Frequency [Hz]"); plt.xlabel("Time [s]")
plt.colorbar(label="PSD [dB/Hz]")
```

**Modern API (SciPy ≥ 1.12): `ShortTimeFFT`.** `spectrogram`, `stft`, and
`istft` are now legacy; new code should prefer `ShortTimeFFT`, which is explicit
about hop size, scaling, and boundary handling.

```python
from scipy.signal import ShortTimeFFT
from scipy.signal.windows import gaussian

win = gaussian(256, std=40, sym=True)
SFT = ShortTimeFFT(win, hop=32, fs=4000, scale_to="psd")
Sx  = SFT.spectrogram(chirp)                 # 2-D array; SFT.f, SFT.t give the axes
```

Either API is acceptable; use `ShortTimeFFT` for new work and when you need
invertibility (`SFT.stft` / `SFT.istft`).

## 4. Continuous wavelet transform (CWT)

Wavelets give multi-resolution time-frequency analysis: good frequency
resolution at low frequencies and good time resolution at high frequencies —
better than a fixed STFT window for signals with features across many scales.

**Use PyWavelets, not SciPy.** `scipy.signal.cwt`, `morlet2`, `ricker`, and
`morlet` were deprecated in SciPy 1.12 and **removed in SciPy 1.15**. The
maintained path is `pywt.cwt`.

```python
import pywt

scales = np.geomspace(1, 128, num=100)                   # small scale = high freq
coef, freqs = pywt.cwt(x, scales, "cmor1.5-1.0", sampling_period=1/fs)
# coef: complex, shape (len(scales), len(x)); freqs: Hz, already scale-converted

plt.pcolormesh(t, freqs, np.abs(coef), shading="gouraud", cmap="viridis")
plt.ylabel("Frequency [Hz]"); plt.xlabel("Time [s]"); plt.ylim(0, 200)
plt.colorbar(label="|CWT|")
```

- `"cmor1.5-1.0"` is a complex Morlet (`cmorB-C`: `B` bandwidth, `C` center
  frequency) — the usual choice for oscillatory analysis; `"morl"` is real.
- Let `pywt.cwt` return `freqs` (it applies `scale2frequency / sampling_period`).
  Do not hand-derive frequencies from scales.
- Edge effects grow with scale; the low-frequency edges lie in the cone of
  influence and should not be over-interpreted.

## 5. Coherence and cross-spectral density

For two channels sampled together, magnitude-squared coherence `Cxy(f) ∈ [0,1]`
measures the linear coupling at each frequency; the cross-spectral density
carries the relative phase (lag) between them.

```python
from scipy.signal import coherence, csd

y = 1.2*np.sin(2*np.pi*50*t + 0.3) + 0.6*np.random.randn(t.size)

f_c, Cxy = coherence(x, y, fs=fs, nperseg=256)           # 0..1
f_s, Pxy = csd(x, y, fs=fs, nperseg=256)                 # complex
lag_phase = np.angle(Pxy)                                # radians at each f_s
```

Coherence requires averaging over multiple segments — with `nperseg == len(x)`
(a single segment) it is identically 1 at every frequency and meaningless.
Choose `nperseg` so you have at least ~8 segments.

## 6. Filtering — Butterworth band-pass and notch

Use second-order-sections (`output="sos"`) for numerical stability, and
`sosfiltfilt` for **zero-phase** filtering (forward-backward → no group delay,
but doubles the effective order and needs a settled signal at the edges).

```python
from scipy.signal import butter, sosfiltfilt, iirnotch, filtfilt

def bandpass(data, low, high, fs, order=4):
    sos = butter(order, [low, high], btype="band", fs=fs, output="sos")
    return sosfiltfilt(sos, data)

isolated = bandpass(x, 45, 55, fs)                       # keep 45–55 Hz

# Notch out mains interference at 60 Hz
b, a = iirnotch(w0=60.0, Q=30.0, fs=fs)
clean = filtfilt(b, a, x)
```

Passing `fs=` to `butter`/`iirnotch` lets you specify cutoffs in Hz directly —
no manual division by the Nyquist frequency. Increase `order` for a sharper
transition band (at the cost of more ringing near sharp edges).

## 7. Peak finding

Locate spectral peaks with height/prominence/spacing constraints instead of a
bare `argmax`, which only returns the single largest bin.

```python
from scipy.signal import find_peaks

idx, props = find_peaks(psd_w, height=psd_w.max()*0.05,
                        distance=int(2/(f_w[1]-f_w[0])))   # ≥2 Hz apart
peak_freqs = f_w[idx]
```
