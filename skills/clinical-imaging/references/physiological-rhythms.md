# Physiological Signals: Hemodynamics, Cosinor, Ciliary Beat

Time-series and periodic-signal biomarkers. All examples use `scipy.signal`,
`scipy.optimize`, `scipy.stats`, and `numpy.fft`.

## 1. Hemodynamic Parameters from Blood-Pressure Waveforms

Beat-by-beat systolic/diastolic pressure, MAP, pulse pressure, and heart rate
from a continuous arterial pressure trace (mmHg).

```python
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

def analyze_blood_pressure(pressure, fs_hz, lowpass_hz=20.0):
    """pressure: 1D mmHg array. fs_hz: sampling rate. Returns hemodynamics dict."""
    # Light low-pass to suppress dicrotic-notch false peaks (zero-phase filtfilt)
    b, a = butter(4, lowpass_hz / (fs_hz / 2), btype="low")
    sig = filtfilt(b, a, pressure)

    min_dist = int(0.5 * fs_hz)  # >=0.5 s between beats -> <=120 bpm ceiling
    peaks, _ = find_peaks(sig, distance=min_dist, prominence=20, height=60)
    troughs, _ = find_peaks(-sig, distance=min_dist)

    systolic = sig[peaks]
    diastolic = []                       # match each systolic peak to next trough
    for p in peaks:
        later = troughs[troughs > p]
        if later.size:
            diastolic.append(sig[later[0]])
    diastolic = np.array(diastolic[:len(systolic)])
    systolic = systolic[:len(diastolic)]

    pulse_pressure = systolic - diastolic
    map_pressure = diastolic + pulse_pressure / 3.0          # MAP ~ DBP + PP/3
    hr = 60.0 / (np.diff(peaks) / fs_hz)                     # bpm

    return {
        "systolic_mmHg": float(np.mean(systolic)),
        "diastolic_mmHg": float(np.mean(diastolic)),
        "MAP_mmHg": float(np.mean(map_pressure)),
        "pulse_pressure_mmHg": float(np.mean(pulse_pressure)),
        "heart_rate_bpm": float(np.mean(hr)),
        "heart_rate_std_bpm": float(np.std(hr)),
        "n_beats": int(peaks.size),
    }
```

**Notes**
- CSV input usually has a `pressure` column (± a `time` column); if only
  `pressure` is present, synthesize time from `fs_hz`.
- Tune `prominence`/`height` to the recording's amplitude; a flat or clipped
  arterial line will silently drop beats.
- MAP via `DBP + PP/3` is the standard clinical approximation; for high fidelity
  integrate the waveform over each cardiac cycle instead.

## 2. Cosinor Analysis for Circadian / Ultradian Rhythms

Fit `Y(t) = MESOR + Amplitude·cos(2π·t/T + acrophase)` and test rhythm
significance. Use the **linearized** reparameterization — it is a stable linear
least-squares problem instead of a fragile nonlinear fit:

```
Y = M + β·cos(2π t/T) + γ·sin(2π t/T)
Amplitude = sqrt(β² + γ²)   Acrophase = atan2(-γ, β)
```

```python
import numpy as np
from scipy.stats import f as f_dist

def cosinor_analysis(time_hours, values, period=24.0):
    """time_hours, values: 1D arrays. period: assumed cycle length (h)."""
    t = np.asarray(time_hours, float)
    y = np.asarray(values, float)
    w = 2 * np.pi / period

    # Design matrix [1, cos, sin] -> linear least squares
    X = np.column_stack([np.ones_like(t), np.cos(w * t), np.sin(w * t)])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    mesor, beta, gamma = coef

    amplitude = np.hypot(beta, gamma)
    acrophase = np.arctan2(-gamma, beta)          # radians, peak phase (lag)
    peak_hours = (-acrophase / w) % period         # clock time of peak

    pred = X @ coef
    ss_res = np.sum((y - pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # F-test: fitted (2 extra params) vs mean-only null model
    n = y.size
    f_stat = ((ss_tot - ss_res) / 2) / (ss_res / (n - 3)) if n > 3 else np.nan
    p_value = 1 - f_dist.cdf(f_stat, 2, n - 3) if n > 3 else np.nan

    return {
        "MESOR": float(mesor),
        "amplitude": float(amplitude),
        "acrophase_rad": float(acrophase),
        "peak_time_h": float(peak_hours),
        "period_h": period,
        "r_squared": float(r2),
        "f_statistic": float(f_stat),
        "p_value": float(p_value),
        "significant": bool(p_value < 0.05),
    }
```

**Notes**
- Sample ≥2 full cycles; sparse or single-cycle data makes acrophase unreliable.
- If a 24 h fit is non-significant, retry with `period=12` (ultradian) before
  concluding "arrhythmic".
- With `acrophase = atan2(-γ, β)` (the phase φ in `M + A·cos(ωt + φ)`, a negative
  lag), the peak occurs at `ωt + φ = 0`, so peak time = `-acrophase/ω` (mod T) —
  note the leading minus. Report acrophase as a clock time, not raw radians.

## 3. Ciliary Beat Frequency (CBF) via FFT

Dominant beat frequency of intensity oscillations from high-speed video. Apply a
window to reduce spectral leakage and restrict the peak search to a physiological
band.

```python
import cv2
import numpy as np
from scipy.signal import windows

def load_gray_frames(video_path, roi=None):
    cap = cv2.VideoCapture(video_path)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(float)
        if roi:
            x, y, w, h = roi
            g = g[y:y+h, x:x+w]
        frames.append(g)
    cap.release()
    return np.array(frames)

def measure_cbf(frames, fps, min_freq=2.0, max_freq=None):
    """frames: (T,H,W) grayscale. Returns (global_cbf_hz, freqs, power)."""
    n = len(frames)
    ts = frames.mean(axis=(1, 2))                 # global mean-intensity series
    ts = (ts - ts.mean()) * windows.hann(n)       # detrend + Hann window
    power = np.abs(np.fft.rfft(ts)) ** 2
    freqs = np.fft.rfftfreq(n, d=1 / fps)

    hi = max_freq if max_freq is not None else fps / 2
    band = (freqs >= min_freq) & (freqs <= hi)
    cbf = freqs[band][np.argmax(power[band])]
    return float(cbf), freqs, power
```

Per-ROI spatiotemporal map (coarse grid for speed):

```python
def cbf_map(frames, fps, step=4, min_freq=2.0, max_freq=None):
    T, H, W = frames.shape
    out = np.zeros((H, W))
    win = windows.hann(T)
    freqs = np.fft.rfftfreq(T, d=1 / fps)
    hi = max_freq if max_freq is not None else fps / 2
    band = (freqs >= min_freq) & (freqs <= hi)
    for y in range(0, H, step):
        for x in range(0, W, step):
            s = frames[:, y, x]
            p = np.abs(np.fft.rfft((s - s.mean()) * win)) ** 2
            out[y, x] = freqs[band][np.argmax(p[band])]
    return out
```

**Notes**
- Nyquist: `fps` must exceed 2× the highest expected CBF. Human respiratory CBF
  is ~5–20 Hz, so record at ≥40 fps (250–500 fps typical).
- A peak locked to mains frequency (50/60 Hz) or near Nyquist is an artifact —
  verify `fps` and that the ROI contains actively beating cilia.
- Longer recordings give finer frequency resolution (`Δf = fps/n`).
