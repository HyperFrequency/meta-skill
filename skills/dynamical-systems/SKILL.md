---
name: dynamical-systems
version: 0.1.0
description: >-
  Qualitative and quantitative analysis of nonlinear dynamical systems with
  scipy/numpy/matplotlib — phase portraits, fixed-point finding and eigenvalue
  classification, local stability, bifurcation diagrams, parameter continuation,
  Poincaré sections, Lyapunov exponents, and chaos detection. Use for autonomous
  or non-autonomous ODE systems and iterated maps where attractors, limit
  cycles, chaos, or parameter-dependent transitions matter. NOT for solving a
  single initial-value problem just to get one trajectory (use an ODE solver
  directly), for PDEs / spatially-extended field equations, for fitting model
  parameters to data, or for symbolically deriving equations of motion.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Dynamical Systems Analysis

## Overview

Study the *qualitative* behavior of nonlinear systems `dy/dt = f(y, t; p)` (and
iterated maps `y_{n+1} = g(y_n; p)`) rather than a single numerical trajectory.
This skill covers the standard toolkit: draw the flow in phase space, locate and
classify fixed points from the Jacobian spectrum, track how structure changes as
a parameter `p` varies (bifurcations), reduce a flow to a map via a Poincaré
section, and quantify sensitivity to initial conditions with Lyapunov exponents.

Everything runs on the scientific Python stack — `scipy.integrate.solve_ivp`,
`scipy.optimize.fsolve`, `numpy.linalg`, and `matplotlib`. No specialized
continuation package is required for the common cases; where you outgrow these
primitives, the references point you to the right dedicated tool.

## When to Use This Skill

- Visualizing the flow of a 2D or 3D system (phase portrait, streamlines, sample orbits).
- Finding fixed/equilibrium points and classifying them (node, saddle, spiral, center) from Jacobian eigenvalues.
- Assessing **local stability** of an equilibrium or the effect of a parameter on it.
- Building a **bifurcation diagram** for an iterated map or continuing fixed points of a flow as a parameter varies.
- Detecting and characterizing **chaos** — largest Lyapunov exponent, Lyapunov time, sensitivity to initial conditions.
- Reducing a periodic/chaotic flow to a **Poincaré map** to study periodicity, limit cycles, and period-doubling.

## When NOT to Use This Skill

- You just need the trajectory `y(t)` from one initial condition — call `solve_ivp` directly; you do not need phase-space machinery.
- The model is a **PDE** or otherwise spatially extended (fields, reaction-diffusion, fluids). This skill is for finite-dimensional ODEs/maps.
- You want to **fit** the parameters `p` to measured data — that is inference, not dynamics; use `bayesian-inference` or `statistical-analysis`.
- You want to **discover** the governing equations or a conserved quantity from data — see `conservation-law-discovery` (and symbolic-regression tooling).
- You need rigorous global continuation (fold/Hopf tracking, two-parameter bifurcation sets) at research grade — reach for AUTO-07p / MatCont / PyDSTool; this skill's continuation is the natural-parameter, single-branch kind.

## Setup

```bash
pip install "scipy>=1.11" "numpy>=1.24" "matplotlib>=3.7"
```

## Core Loop (find and classify an equilibrium)

The recurring pattern — integrate to see the flow, solve `f(y)=0` for equilibria,
then read stability off the Jacobian's eigenvalues:

```python
import numpy as np
from scipy.optimize import fsolve

mu = 1.0
def f(y):                              # Van der Pol as first-order system
    x, v = y
    return [v, mu * (1 - x**2) * v - x]

fp = fsolve(f, [0.0, 0.0])                        # equilibrium near the origin
J  = np.array([[0.0, 1.0],
               [-2*mu*fp[0]*fp[1] - 1.0, mu*(1 - fp[0]**2)]])  # analytic Jacobian
eigs = np.linalg.eigvals(J)                       # sign of Re(eigs) → stability
```

Real eigenvalues, all negative → stable node; mixed sign → saddle; complex with
positive real part → unstable spiral (the seed of a Hopf-born limit cycle). The
full decision table and a reusable `classify_fixed_point` live in the reference.

## Capabilities

Each area has a self-contained reference with runnable code, parameter guidance,
and the underlying theory. Load the one you need:

- **Phase portraits & fixed points** — vector fields, streamlines, sampling
  orbits, multi-start equilibrium search, analytic vs. finite-difference
  Jacobians, and the 2D classification table.
  See `references/phase-space-and-fixed-points.md`.
- **Bifurcation analysis** — logistic-map bifurcation diagrams, natural-parameter
  continuation of flow equilibria with on-the-fly stability, and how to
  recognize saddle-node / transcritical / pitchfork / Hopf / period-doubling.
  See `references/bifurcation-analysis.md`.
- **Chaos, Lyapunov exponents & Poincaré sections** — largest exponent via the
  Benettin variational method, the full spectrum via QR reorthonormalization,
  Lyapunov time, and precise Poincaré crossings (manual interpolation and the
  `solve_ivp` event API). See `references/chaos-lyapunov-poincare.md`.

## Recommended Workflow

1. **Nondimensionalize first.** Rescale time and states to collapse redundant
   parameters before any analysis — fewer parameters means a cleaner bifurcation
   study. See `dimensional-analysis`.
2. **Look before you compute.** Draw the phase portrait / vector field to see
   the number and rough location of equilibria and any limit cycles.
3. **Locate & classify equilibria** with a multi-start `fsolve` grid, then the
   Jacobian eigenvalues.
4. **Sweep the parameter** — bifurcation diagram (maps) or continuation (flows) —
   to map stability transitions.
5. **If aperiodic, test for chaos** — compute the largest Lyapunov exponent over
   10–100 Lyapunov times and confirm it is robustly positive.
6. **Reduce with a Poincaré section** to inspect periodicity and period-doubling
   cascades.

## Numerical Practice (read before trusting a result)

- **Tight tolerances for chaos/Lyapunov work.** Use `rtol=1e-9…1e-11`; loose
  tolerances corrupt the exponent. For stiff systems switch `method='Radau'` or
  `'LSODA'` instead of the default `'RK45'`.
- **Discard transients.** Attractor statistics, bifurcation iterates, and
  Lyapunov sums must be taken after the trajectory settles onto the attractor.
- **Multi-start equilibrium search.** `fsolve` finds one root near its guess;
  seed it from a grid to catch every equilibrium, and always verify `f(y*)≈0`.
- **Centers are fragile.** Pure-imaginary eigenvalues (a "center") only imply
  closed orbits in conservative systems; nonlinear terms can turn a linear
  center into a weak spiral. Confirm with a conserved quantity — see
  `conservation-law-discovery`.

## Troubleshooting

Symptom-cause-fix table for non-converging solvers, sparse Poincaré sections,
drifting Lyapunov estimates, missing continuation branches, and stiff-system
blowups: `references/troubleshooting.md`.

## Related Skills

- `dimensional-analysis` — reduce parameters before a bifurcation study.
- `conservation-law-discovery` — confirm centers / integrable structure.
- `bayesian-inference`, `statistical-analysis` — estimate model parameters from data.
