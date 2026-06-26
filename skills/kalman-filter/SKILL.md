---
name: kalman-filter
description: Linear and Extended Kalman filtering for online state estimation on time-series. Use for pairs-trading hedge-ratio tracking, online mean / drift estimation, smoothing a noisy mid-price, or fusing multiple price feeds. Prefer filterpy (rlabbe/filterpy) — actively maintained, full EKF/UKF/IMM stack. pykalman is canonical but stale; only reach for it when you need its EM parameter-learning loop on a linear model.
allowed-tools: Read, Write, Edit, Bash
license: MIT
metadata:
    skill-author: HyperFrequency
---

# Kalman Filter: Online State Estimation for Quant Time-Series

## Overview

A Kalman filter maintains a Gaussian belief over a hidden state given a stream of noisy measurements, optimally weighting model predictions vs new observations by their relative uncertainties. For quant work, the state is typically something we want to track but can only observe indirectly: a slow-moving mean, an OLS-style hedge ratio between two assets, an underlying mid-price hidden under microstructure noise, or a Greek that drifts faster than we can re-estimate by OLS.

Two libraries cover the Python ecosystem:

- **`filterpy`** (Roger Labbe) — actively maintained. Provides `KalmanFilter`, `ExtendedKalmanFilter`, `UnscentedKalmanFilter`, `IMMEstimator`, `Q_discrete_white_noise`, `batch_filter`, `rts_smoother`. Companion to the free book *Kalman and Bayesian Filters in Python*. **Default choice.**
- **`pykalman`** — canonical but largely stale (sporadic maintenance, older NumPy/SciPy assumptions). Distinct feature: a built-in **EM algorithm** that learns transition/observation matrices and covariances from data via `kf.em(observations, n_iter=...)`. Use it when you want EM-learned parameters on a linear Gaussian model; otherwise prefer filterpy.

## When to Use This Skill

- **Pairs-trading hedge-ratio tracking.** Treat the OLS slope `beta` between two prices as a hidden state evolving as a random walk; observe `y_t = beta_t * x_t + noise`. Run a Kalman filter to update `beta_t` online — much faster-adapting than rolling OLS, and gives a calibrated `P_t` you can size positions against.
- **Online mean / drift estimation.** State = unknown drift of a return series. Each new observation nudges the estimate; no fixed window, no abrupt drop-off when an old bar exits a rolling window.
- **Smoothing a noisy mid-price.** State = `(true_price, velocity)` constant-velocity model; observation = noisy quote. Output is a smooth, latency-friendly price estimate with explicit uncertainty.
- **Sensor / feed fusion.** Multiple exchanges quoting the same asset — model each as a noisy observation of one shared true price and let the filter weight them by `R` (per-feed measurement variance).

## Install / Setup

```bash
pip install filterpy numpy matplotlib
# Optional, only if you need EM parameter learning:
pip install pykalman
```

filterpy depends on NumPy + SciPy only. pykalman has had install friction on newer NumPy versions in the past — pin it explicitly if you adopt it. (Unverified for the latest pykalman release; check the project's issue tracker.)

## Minimal Example: Constant-Velocity Tracker on a Noisy Series

```python
import numpy as np
import matplotlib.pyplot as plt
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise

# 1. Synthetic "true" series + noisy observations
rng = np.random.default_rng(0)
n, dt = 200, 1.0
true_pos = np.cumsum(0.05 + 0.01 * rng.standard_normal(n))  # drifting random walk
z = true_pos + rng.normal(0, 1.0, size=n)                   # noisy measurements

# 2. Build a 2-state (position, velocity) constant-velocity KF
kf = KalmanFilter(dim_x=2, dim_z=1)
kf.x = np.array([[z[0]], [0.0]])                # initial state
kf.F = np.array([[1.0, dt],                     # state transition
                 [0.0, 1.0]])
kf.H = np.array([[1.0, 0.0]])                   # we only observe position
kf.P *= 10.0                                    # initial state uncertainty
kf.R = np.array([[1.0]])                        # measurement noise variance
kf.Q = Q_discrete_white_noise(dim=2, dt=dt, var=0.01)  # process noise

# 3. Run predict / update over the stream
filtered = np.zeros(n)
for i, zi in enumerate(z):
    kf.predict()
    kf.update(np.array([[zi]]))
    filtered[i] = kf.x[0, 0]

# 4. Plot
plt.figure(figsize=(10, 4))
plt.plot(true_pos, label='true', linewidth=2)
plt.plot(z, '.', alpha=0.3, label='noisy obs')
plt.plot(filtered, label='Kalman estimate')
plt.legend(); plt.tight_layout(); plt.show()
```

For an Extended Kalman Filter, swap to `filterpy.kalman.ExtendedKalmanFilter` and supply nonlinear `fx`, `hx` plus their Jacobians `F_jacobian`, `HJacobian` at the current state.

## Second Example: Online Hedge Ratio for Pairs Trading

The hedge ratio between two cointegrated assets isn't constant — model it as a random walk and let the filter update it bar-by-bar.

```python
import numpy as np
from filterpy.kalman import KalmanFilter

# Synthetic cointegrated pair: y_t = beta_t * x_t + intercept + noise
rng = np.random.default_rng(1)
n = 500
x = np.cumsum(rng.standard_normal(n)) + 50.0
true_beta = 1.5 + 0.001 * np.arange(n)                # slow drift
y = true_beta * x + 2.0 + rng.normal(0, 0.5, size=n)  # noisy linear

# State = [beta, intercept]; obs row H_t = [x_t, 1.0] is time-varying
kf = KalmanFilter(dim_x=2, dim_z=1)
kf.x = np.array([[1.0], [0.0]])
kf.F = np.eye(2)                                       # random walk
kf.P *= 100.0                                          # weak prior
kf.R = np.array([[0.5 ** 2]])                          # measurement noise
kf.Q = np.eye(2) * 1e-5                                # state drift

betas = np.zeros(n)
for i in range(n):
    kf.H = np.array([[x[i], 1.0]])                     # update H each step!
    kf.predict()
    kf.update(np.array([[y[i]]]))
    betas[i] = kf.x[0, 0]
# betas now tracks true_beta with a short adaptation lag
```

Key trick: `H` is **reassigned every step** to the current regressors. The state vector *is* the regression coefficients.

## Key API Surface

### filterpy

| Class / Function | Purpose |
|---|---|
| `filterpy.kalman.KalmanFilter(dim_x, dim_z, dim_u=0)` | Linear KF. Attributes: `x, F, H, P, R, Q, B`. |
| `kf.predict(u=0)` / `kf.update(z)` | Standard predict / update steps. |
| `kf.batch_filter(zs)` | Run the filter over an array/list of measurements; returns means + covariances. |
| `kf.rts_smoother(means, covariances)` | Rauch-Tung-Striebel offline smoother — strictly better than filtered estimates when used post-hoc. |
| `filterpy.kalman.ExtendedKalmanFilter(dim_x, dim_z)` | EKF. Provide `fx`, `hx` plus Jacobian callables to `predict_update`. |
| `filterpy.kalman.UnscentedKalmanFilter` | UKF — derivative-free alternative to EKF, often more stable. |
| `filterpy.kalman.IMMEstimator` | Interacting Multiple Model — bank of filters for regime switching. |
| `filterpy.common.Q_discrete_white_noise(dim, dt, var, block_size=1)` | Build a discrete-time white-noise process-noise matrix. |

### pykalman (when you need EM)

| Class / Method | Purpose |
|---|---|
| `pykalman.KalmanFilter(...)` | Linear KF with optional EM learning. |
| `kf.em(observations, n_iter=10, em_vars=[...])` | Learn unknown parameters (transition matrices, covariances, initial state) via Expectation-Maximization. |
| `kf.filter(observations)` / `kf.smooth(observations)` | Forward filter / forward+backward smoother. |
| `kf.filter_update(mean, cov, observation)` | One-step online update — analogue of filterpy's `predict + update`. |
| `pykalman.UnscentedKalmanFilter` | Nonlinear variant via sigma-point propagation. |

## Online vs Offline Use

- **Online (live trading / streaming).** Use `predict()` + `update()` per bar. Filtered state at time `t` depends only on observations up to `t` — safe for live signals.
- **Offline (research, post-trade attribution).** Use `batch_filter(zs)` then `rts_smoother(...)` for the best retrospective estimate at every step. The smoother propagates information *backwards* from later observations, so smoothed estimates are strictly better than filtered ones — but they encode future info and **cannot be used to generate signals you would trade in real time**.

```python
# Offline smoother — research only, not a backtest signal.
means, covs, _, _ = kf.batch_filter(zs)
smoothed_means, smoothed_covs, _, _ = kf.rts_smoother(means, covs)
```

## EKF Sketch (Nonlinear Observation)

When the measurement is a nonlinear function of state — e.g. `z = sigma * sqrt(S^2 + epsilon)` for an implied-vol-like observation — switch to `ExtendedKalmanFilter` and provide `hx(x)` plus a Jacobian `HJacobian(x)`.

```python
from filterpy.kalman import ExtendedKalmanFilter
import numpy as np

ekf = ExtendedKalmanFilter(dim_x=2, dim_z=1)
ekf.x = np.array([1.0, 0.1])
ekf.F = np.eye(2)
ekf.P *= 1.0
ekf.R = np.array([[0.01]])
ekf.Q = np.eye(2) * 1e-4

def hx(x): return np.array([np.sqrt(x[0] ** 2 + 1e-6)])
def HJacobian(x): return np.array([[x[0] / np.sqrt(x[0] ** 2 + 1e-6), 0.0]])

# Per step: ekf.predict(); ekf.update(z, HJacobian, hx)
```

Verify the Jacobian against `scipy.optimize.approx_fprime` before trusting the filter.

## Choosing Parameters (Q and R)

The two knobs that decide whether the filter is useful or useless.

- **`R` (measurement noise variance).** Estimate from data: compute the variance of `observation - rolling_mean(observation, w)` for a small window `w`, or use the empirical variance of bid/ask half-spread for tick data. Wrong `R` is usually less catastrophic than wrong `Q`.
- **`Q` (process noise covariance).** Controls how quickly the filter can adapt. Larger `Q` -> faster adaptation, noisier estimate. Smaller `Q` -> smoother, slower to react to genuine regime changes. For a position/velocity model use `Q_discrete_white_noise(dim=2, dt=dt, var=q_var)` and tune `q_var` on a holdout.
- **Validation heuristic — NIS test.** Compute the normalized innovation squared `nis = y' @ inv(S) @ y` each step (innovation `y = z - H @ x_pred`, innovation cov `S = H @ P_pred @ H' + R`). Over many steps, mean(NIS) should be ~`dim_z` and 95% of values inside `chi2.ppf([0.025, 0.975], dim_z)`. Persistent overshoot means `Q` or `R` underestimated.
- **`P` (initial state covariance).** Set large (`P *= 100` or `1000`) when you genuinely don't know the initial state — the filter will tighten it quickly.
- **EM as an alternative.** If you don't want to hand-tune, pykalman's `kf.em(observations, em_vars=['transition_covariance', 'observation_covariance'], n_iter=10)` will learn `Q` and `R` (and other parameters) from data. Cheaper than grid search; just remember it assumes the model structure is correct.

## Common Pitfalls

1. **Filter divergence from over-tight Q.** If `Q` is too small relative to actual state dynamics, predicted covariance shrinks, the Kalman gain heads toward zero, and the filter ignores new measurements while drifting with `F @ x`. Look for `P` collapsing toward 0 and innovations growing — that's divergence. Bump `Q` up.
2. **Rank-deficient or near-singular `H`.** When `H @ P @ H' + R` becomes numerically singular (e.g. you accidentally use the same measurement twice with `R=0`), `inv(S)` blows up. Always keep `R` positive-definite; use the Joseph form or `filterpy`'s `update` (which uses a numerically safer formulation) over hand-rolled Riccati updates.
3. **Forgetting that this is a state-space model, not regression.** The "hedge ratio Kalman filter" pattern requires the state vector to *be* the regression coefficients and the observation row of `H` to *be* the current regressor values — `H_t = np.array([[x_t, 1.0]])`. People often try to plug residuals as observations and wonder why it diverges.
4. **EKF Jacobian errors.** For nonlinear models, the EKF needs `F_jacobian` and `H_jacobian` evaluated at the current state. A miscoded Jacobian (wrong sign, wrong row/col layout) produces a filter that looks like it works for a few steps then diverges silently. Cross-check Jacobians with `scipy.optimize.approx_fprime` or use UKF instead — no Jacobians required.
5. **Look-ahead via smoothing.** RTS smoother (`kf.rts_smoother`, `kf.smooth`) uses *future* observations to refine past states. Excellent for research; **never** use smoothed estimates in a live backtest signal — they leak.

## References

### Primary libraries
- [rlabbe/filterpy](https://github.com/rlabbe/filterpy) — upstream repo (issues, releases); KF, EKF, UKF, IMM, particle, alpha-beta-gamma all live here
- [filterpy docs](https://filterpy.readthedocs.io/en/latest/) — current channel
- [filterpy examples directory](https://github.com/rlabbe/filterpy/tree/master/filterpy/kalman/tests) — runnable tests that double as worked examples
- [pykalman/pykalman](https://github.com/pykalman/pykalman) — alternative with EM-based parameter learning; lighter API surface than filterpy
- [pykalman docs](https://pykalman.github.io/) — covers `KalmanFilter`, `UnscentedKalmanFilter`, `AdditiveUnscentedKalmanFilter`

### Deep-dive docs (specific pages worth bookmarking)
- [filterpy `KalmanFilter` class](https://filterpy.readthedocs.io/en/latest/kalman/KalmanFilter.html) — `predict`, `update`, `batch_filter`, `rts_smoother`; the canonical API
- [filterpy `ExtendedKalmanFilter`](https://filterpy.readthedocs.io/en/latest/kalman/ExtendedKalmanFilter.html) — needs `HJacobian` + `Hx` callbacks; the most common source of silent divergence
- [filterpy `UnscentedKalmanFilter`](https://filterpy.readthedocs.io/en/latest/kalman/UnscentedKalmanFilter.html) — Jacobian-free alternative to EKF; usually safer for nonlinear models
- [filterpy `MerweScaledSigmaPoints`](https://filterpy.readthedocs.io/en/latest/kalman/sigma_points.html) — `alpha`, `beta`, `kappa`; the sigma-point parameterisation that drives UKF behaviour
- [filterpy `IMMEstimator`](https://filterpy.readthedocs.io/en/latest/kalman/IMMEstimator.html) — Interacting Multiple Model filter; the right tool when you have regime switches (trending vs mean-reverting)
- [filterpy particle filter (`Particle.py`)](https://filterpy.readthedocs.io/en/latest/monte_carlo/resampling.html) — for non-Gaussian / multi-modal posteriors when KF assumptions break
- [pykalman EM (`KalmanFilter.em`)](https://pykalman.github.io/#pykalman.KalmanFilter.em) — maximum-likelihood estimation of `F`, `H`, `Q`, `R` from data; useful when you don't know noise covariances a priori
- [statsmodels state-space models](https://www.statsmodels.org/stable/statespace.html) — the statsmodels Kalman filter underlies SARIMAX, unobserved-components, dynamic factor models

### Adjacent / alternative libraries
- [`statsmodels.tsa.statespace`](https://www.statsmodels.org/stable/statespace.html) — when you want Kalman *inside* an econometric model (SARIMAX, UnobservedComponents, dynamic-factor)
- [`stonesoup`](https://github.com/dstl/stonesoup) — UK DSTL's Bayesian tracking framework; richer multi-target tracking on top of KF/EKF/UKF/particle
- [`numpyro` / `pymc`](https://github.com/pymc-devs/pymc) — Bayesian state-space when you want full posterior + hierarchical priors, not point estimates
- [`tinygp`](https://github.com/dfm/tinygp) — Gaussian-process equivalents; when a stationary GP would describe the signal better than a state-space model

### Academic papers
- Kalman, R. E. (1960). "A New Approach to Linear Filtering and Prediction Problems." *Journal of Basic Engineering* 82(1), 35–45. [doi:10.1115/1.3662552](https://doi.org/10.1115/1.3662552) — the original Kalman paper; defines the recursive linear MMSE filter
- Julier, S. J. & Uhlmann, J. K. (1997). "A New Extension of the Kalman Filter to Nonlinear Systems." *SPIE 1997*. [doi:10.1117/12.280797](https://doi.org/10.1117/12.280797) — the UKF / sigma-point construction
- Wan, E. A. & van der Merwe, R. (2000). "The Unscented Kalman Filter for Nonlinear Estimation." *IEEE 2000 Adaptive Systems for Signal Processing*. [doi:10.1109/ASSPCC.2000.882463](https://doi.org/10.1109/ASSPCC.2000.882463) — practical UKF tuning (`α`, `β`, `κ`)
- Rauch, H. E., Tung, F., Striebel, C. T. (1965). "Maximum Likelihood Estimates of Linear Dynamic Systems." *AIAA Journal* 3(8), 1445–1450. [doi:10.2514/3.3166](https://doi.org/10.2514/3.3166) — the RTS smoother (the offline + backward-pass version of the KF)

### Tutorials & write-ups
- [Roger Labbe — *Kalman and Bayesian Filters in Python*](https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python) — free book by the filterpy author; chapters 1–10 are the best practical Kalman tutorial in existence
- [Welch & Bishop, "An Introduction to the Kalman Filter"](https://www.cs.unc.edu/~welch/media/pdf/kalman_intro.pdf) — short, classic, technically careful introduction
- [Quantopian / pairs-trading Kalman cookbook](https://github.com/quantopian/research_public) — pattern for treating the hedge ratio as a hidden state

### Last cross-checked
2026-05-20 — via Context7 `/rlabbe/filterpy` + `/pykalman/pykalman`; Auggie not indexed.
