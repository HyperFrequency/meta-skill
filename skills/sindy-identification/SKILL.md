---
name: sindy-identification
version: 0.1.0
description: >-
  Discover governing ordinary differential equations from time-series data with
  SINDy (Sparse Identification of Nonlinear Dynamics, Brunton et al. 2016) using
  the PySINDy library. Given measurements of state variables x(t), it fits a
  sparse model dx/dt = f(x) by regressing time derivatives onto a library of
  candidate functions and thresholding away small coefficients, yielding a
  compact interpretable ODE. Use when you have trajectory (time-series) data,
  believe the dynamics have a sparse closed-form representation in known state
  variables, and want the equation itself — not just a black-box predictor. Also
  covers noisy-data handling, custom/Fourier libraries, forced systems (control
  inputs), model validation by simulation, and coefficient extraction. Do NOT use
  for arbitrary free-form symbolic expressions (use `symbolic-regression` /
  PySR), steady-state-only data with no time information, stochastic systems, or
  PDE spatial-derivative discovery (that needs the weak/PDE-FIND variant, noted
  in references).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT (PySINDy)"
---

# SINDy Equation Discovery

## Overview

SINDy discovers a sparse system of ODEs, `dx/dt = f(x)`, directly from measured
trajectories. The method assembles a large library of candidate terms Θ(x)
(polynomials, trig functions, custom nonlinearities), estimates the time
derivatives `dx/dt`, and solves a sparse regression `dx/dt ≈ Θ(x) Ξ` so that
only a few coefficients in `Ξ` survive. The result is a human-readable equation
per state variable rather than a neural network.

This skill wraps the **PySINDy** library (MIT-licensed). Install with:

```bash
pip install pysindy
```

Optional extras: `pip install "pysindy[cvxpy]"` for constrained optimizers,
`pip install "pysindy[miosr]"` for the mixed-integer optimizer, and the
`derivative` package (pulled in automatically) for advanced differentiation.

## When to Use This Skill

- You have **time-series / trajectory data** and want the underlying ODE, not a
  black-box forecaster.
- You measured (or can reconstruct) the **right state variables** — the terms
  that actually drive the dynamics are expressible in what you observed.
- You believe the true dynamics are **sparse**: a handful of active terms out of
  many candidates (most physical systems are).
- Data is reasonably clean, or you can denoise / smooth the derivatives.
- You want an **interpretable, simulatable** model you can integrate forward and
  compare against ground truth.

## When NOT to Use This Skill

- You want **arbitrary symbolic expressions** (nested transcendentals, rational
  functions of unknown form) — use `symbolic-regression` with PySR instead.
  SINDy can only find terms you put in the library.
- You have **only steady-state / equilibrium data** — SINDy needs temporal
  variation to estimate `dx/dt`.
- The system is **stochastic** (SDE-driven) — standard SINDy assumes
  deterministic dynamics; noise in the state is treated as measurement noise.
- You need **spatial PDE discovery** (`u_t = f(u, u_x, u_xx, …)`) — that is the
  PDE-FIND / weak-form variant, summarized in `references/advanced.md`, not the
  basic workflow below.
- You cannot enumerate a library that contains the true terms — if the governing
  physics needs a term you never include, SINDy cannot recover it.

## Core Workflow

The standard loop is: **prepare data → choose library + optimizer → fit →
inspect → validate by simulation → tune sparsity**.

```python
import numpy as np
import pysindy as ps
from scipy.integrate import solve_ivp

# 1. Data: one trajectory of the Lorenz system on a uniform time grid
def lorenz(t, y, sigma=10, rho=28, beta=8/3):
    return [sigma*(y[1]-y[0]), y[0]*(rho-y[2])-y[1], y[0]*y[1]-beta*y[2]]

dt = 0.001
t_train = np.arange(0, 10, dt)
sol = solve_ivp(lorenz, (0, 10), [1, 1, 1], t_eval=t_train, rtol=1e-10)
x_train = sol.y.T                      # shape (n_samples, n_features) — NOT transposed

# 2/3. Configure and fit
model = ps.SINDy(
    feature_names=["x", "y", "z"],
    feature_library=ps.PolynomialLibrary(degree=2),
    optimizer=ps.STLSQ(threshold=0.1),  # sequentially-thresholded least squares
)
model.fit(x_train, t=dt)

# 4. Inspect the discovered equations
model.print()
# x' = -10.000 x + 10.000 y
# y' =  28.000 x + -1.000 y + -1.000 x z
# z' =  -2.667 z +  1.000 x y
```

Key objects, arguments, and every optimizer / library / differentiation method
are catalogued in **`references/api.md`**. Read it before changing anything
beyond `threshold` and polynomial `degree`.

### Validate by simulation (do this every time)

A model that fits derivatives well can still be dynamically wrong. Always
integrate the discovered ODE from the same initial condition and compare
trajectories:

```python
x_sim = model.simulate(x_train[0], t_train)
rmse = np.sqrt(np.mean((x_sim - x_train)**2, axis=0))
print("per-variable RMSE:", rmse)
model.score(x_train, t=dt)   # R^2 of the derivative fit
```

Full validation-plot code and coefficient-matrix extraction are in
**`references/workflows.md`**.

### Tune the sparsity threshold

The single most important knob. Too low overfits (spurious terms); too high
drops real terms. Sweep it and watch complexity vs. simulation error — the
"elbow" where error stops dropping but term count keeps falling is usually
right. See the threshold-sweep recipe in `references/workflows.md`.

## Deeper Material (references/)

- **`references/api.md`** — `ps.SINDy` constructor and methods (`fit`, `print`,
  `simulate`, `predict`, `score`, `coefficients`, `get_feature_names`,
  `complexity`); the optimizer family (STLSQ, SR3, SSR, FROLS, MIOSR,
  constrained/trapping variants, ensembling); feature libraries (Polynomial,
  Fourier, Custom, Identity, Generalized); differentiation methods; and the key
  parameter table.
- **`references/workflows.md`** — copy-paste recipes: threshold sweep, custom &
  combined libraries, noisy-data smoothing, forced systems with control inputs
  `u`, validation plotting, and coefficient extraction.
- **`references/advanced.md`** — noise-robust weak formulation, PDE discovery
  (PDE-FIND / `WeakPDELibrary`), ensembling for uncertainty, multiple
  trajectories, and common failure modes with fixes.

## Boundaries and Cross-Links

- For free-form symbolic laws where you do not know the term basis, use
  `symbolic-regression`.
- For fitting/inference on already-known model forms (parameter estimation,
  ODE fitting with priors) rather than *discovering* structure, prefer a
  Bayesian/optimization approach (see `pymc` or `statsmodels`).
- For general model interpretability of a fitted black box, see `shap`.
- SINDy needs a **uniform (or supplied) time grid**; irregular sampling requires
  passing an explicit time vector `t=` (array), not a scalar `dt`.
