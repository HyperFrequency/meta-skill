---
name: wave-propagation
version: 0.1.0
description: >-
  Time-domain simulation of wave propagation on the scientific-Python stack
  (numpy/scipy/matplotlib): explicit finite-difference time-domain (FDTD)
  solvers for the scalar wave equation in 1D/2D/3D, pseudospectral solvers on
  periodic domains, Ricker/Gaussian/tone-burst sources, absorbing (Mur/PML),
  reflecting, and periodic boundaries, heterogeneous and layered media,
  scattering, and numerical-dispersion measurement via a space-time FFT. Use to
  model acoustic, seismic, or scalar electromagnetic pulses, resonances and
  standing waves, waveguides and cavities, and scattering from obstacles, or to
  diagnose CFL blow-up and grid dispersion. NOT for frequency-domain / Helmholtz
  or eigenmode problems (use a spectral eigensolver), full vector Maxwell device
  design (use meep or an FDTD-EM package), ray / geometric optics, or fitting a
  wave model to measured data.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Wave Propagation Simulation

## Overview

Propagate waves *in the time domain* by marching a discretized wave equation
forward step by step. The workhorse is **FDTD** (finite-difference time-domain):
approximate the second derivatives of the scalar wave equation

```
∂²u/∂t² = c² ∇²u        (+ a source term s(x, t))
```

on a regular grid and update with an explicit leapfrog stencil. On periodic
domains a **pseudospectral** solver replaces the spatial finite difference with
an FFT, giving near-exact spatial accuracy at the cost of requiring periodicity.

Everything here runs on `numpy` + `matplotlib` (with `scipy` for optional
helpers) — no compiled EM package is needed for scalar acoustic/seismic work.
The scalar field `u` models acoustic pressure, out-of-plane displacement, a
seismic scalar wave, or a single transverse electric field component. Two facts
govern every simulation: the **CFL condition** (get it wrong and the run
explodes) and **numerical dispersion** (too few grid points per wavelength and
fast modes travel at the wrong speed). Both are covered below and in the
references.

## When to Use This Skill

- Simulating a **pulse or wavefront** propagating through 1D/2D/3D acoustic,
  seismic, or scalar-EM media.
- **Scattering** of a wave from obstacles, apertures, or an inclusion of
  different wave speed.
- **Resonance / standing waves** in a cavity or duct; **waveguide** mode
  propagation.
- **Layered or heterogeneous media** — reflection/transmission at interfaces,
  velocity gradients, seismic layer models.
- Measuring the **numerical dispersion relation** ω(k) of a scheme, or debugging
  why a simulation blew up or reflected off its own boundary.

## When NOT to Use This Skill

- You want **steady-state / single-frequency** fields or **eigenmodes** (cavity
  resonant frequencies, waveguide cutoffs) — solve the Helmholtz equation or an
  eigenvalue problem instead; time-marching to steady state is wasteful.
- You need **full vector Maxwell** device simulation (photonic crystals,
  metamaterials, antennas with dispersive/anisotropic materials) — use a
  dedicated package (`meep`, `fdtdz`, `gprMax`). The scalar solver here is a
  teaching/prototyping tool, not a production EM engine.
- The wavelength is tiny relative to the domain and phase detail does not
  matter — use **ray / geometric optics** or acoustics instead.
- You want to **fit** wave-model parameters (velocity, attenuation) to measured
  traces — that is inversion/inference; pair a solver here with
  `bayesian-inference` or `statistical-analysis`.
- The governing PDE is not a wave equation (diffusion, advection-only,
  reaction-diffusion) — use `pde-solver`.

## Setup

```bash
pip install "numpy>=1.24" "scipy>=1.11" "matplotlib>=3.7"
```

## Core Loop (1D FDTD leapfrog)

The pattern under every solver here: keep three time levels of the field and
apply the explicit second-order stencil to the interior, then fix up the
boundaries. `r2 = (c·dt/dx)²` is the squared Courant number.

```python
import numpy as np

def wave_1d_step(u_prev, u_curr, r2):
    """One leapfrog update of the interior; boundaries handled by the caller."""
    u_next = np.empty_like(u_curr)
    u_next[1:-1] = (2*u_curr[1:-1] - u_prev[1:-1]
                    + r2 * (u_curr[2:] - 2*u_curr[1:-1] + u_curr[:-2]))
    return u_next
```

The full time loop — CFL-safe `dt`, a Ricker source injected as `dt²·s(t)`, and
a first-order Mur absorbing boundary — is in
`references/fdtd-solvers.md`, along with the 2D and 3D versions.

## The CFL Stability Condition (read this first)

An explicit FDTD scheme is **conditionally stable**: the time step must be small
enough that the numerical domain of dependence contains the physical one.
Violate it by any margin and the field grows without bound within a few steps.

| Dimension | Stability bound            | Practical `dt`                       |
| --------- | -------------------------- | ------------------------------------ |
| 1D        | `c·dt/dx ≤ 1`              | `dt = CFL · dx / c`, CFL ≈ 0.9       |
| 2D        | `c·dt/dx ≤ 1/√2`           | `dt = CFL · dx / (c·√2)`, CFL ≈ 0.7  |
| 3D        | `c·dt/dx ≤ 1/√3`           | `dt = CFL · dx / (c·√3)`, CFL ≈ 0.6  |

Use `c = c_max` (the fastest wave speed anywhere in the grid) for heterogeneous
media. A CFL below 1 is required for stability but does **not** buy accuracy —
that is set by grid resolution (next section).

## Capabilities

Each area has a self-contained reference with runnable code, parameters, and the
underlying numerics. Load the one you need:

- **FDTD solvers (1D / 2D / 3D)** — full time loops, the Ricker/Gaussian source
  injection, snapshot capture, and imshow/line plotting.
  See `references/fdtd-solvers.md`.
- **Pseudospectral solver & numerical dispersion** — FFT-based spatial
  derivatives on periodic domains, the space-time-FFT method for measuring ω(k),
  and the points-per-wavelength rule for controlling grid dispersion.
  See `references/spectral-and-dispersion.md`.
- **Boundary conditions** — fixed (Dirichlet), free (Neumann), periodic, the
  first- and second-order **Mur** absorbing conditions, and the concept and
  layout of a **PML** (perfectly matched layer). Comparison of reflection
  levels. See `references/boundary-conditions.md`.
- **Sources & media** — source-wavelet catalogue (Ricker, Gaussian, tone
  burst, plane wave), heterogeneous / layered velocity models, and how the
  scalar scheme extends to **vector EM (Yee staggered grid)** and **elastic
  (velocity-stress)** systems. See `references/sources-and-media.md`.

## Recommended Workflow

1. **Nondimensionalize** so `c`, `dx`, and the domain size are O(1) — fewer
   unit pitfalls. See `dimensional-analysis`.
2. **Resolve the shortest wavelength.** Pick `dx ≤ λ_min / 10` (10–20 points per
   wavelength); `λ_min = c_min / f_max`. This controls accuracy.
3. **Set `dt` from the CFL table** using `c_max`. Print the Courant number to
   confirm it is below the bound.
4. **Choose a boundary** matching the physics: absorbing (Mur/PML) for open
   domains, fixed/free for walls, periodic for tiling.
5. **Inject a smooth, band-limited source** (Ricker/Gaussian) — a sharp impulse
   excites the poorly-resolved high-`k` modes and rings.
6. **March, snapshot, and sanity-check**: energy should be conserved (closed,
   lossless boundaries) or decay monotonically (absorbing). If it grows, the CFL
   is violated.
7. **If phase speed looks wrong**, measure the dispersion relation and refine
   `dx`.

## Numerical Practice (pitfalls that bite)

- **CFL is necessary, not sufficient.** A stable run can still be inaccurate
  from under-resolution. Resolution fixes dispersion; CFL only fixes blow-up.
- **Match `c_max` to the CFL, `c_min` to the resolution.** In layered media the
  fast layer sets `dt`; the slow layer (shortest wavelength) sets `dx`.
- **Absorbing boundaries are imperfect.** First-order Mur reflects strongly at
  oblique incidence; use a PML when boundary reflections would contaminate the
  result. See `references/boundary-conditions.md`.
- **Inject the source as `dt²·s(t)`** in the leapfrog update (it enters the
  discretized `∂²u/∂t²`), not as a raw additive value.
- **Spectral solvers demand periodicity.** A non-periodic field aliases and
  produces Gibbs ringing; taper or window if you must approximate an open domain.

## Troubleshooting

Symptom → cause → fix for blow-ups, boundary reflections, grid dispersion, and
spectral ringing: `references/troubleshooting.md`.

## Related Skills

- `pde-solver` — general (non-wave) time-dependent and elliptic PDEs.
- `spectral-analysis` — analyze frequency/wavenumber content of the resulting
  time series and fields.
- `dimensional-analysis` — nondimensionalize before simulating.
- `fluid-dynamics` — nonlinear/compressible flow where waves are one ingredient.
- `neural-operator`, `autoregressive-neural-pde-solver` — learned surrogates for
  wave/PDE fields once a classical solver provides training data.
