---
name: fluid-dynamics
version: 0.1.0
description: >-
  Solve the incompressible Navier-Stokes equations with finite-difference
  methods in NumPy/SciPy: lid-driven cavity and channel flow via the
  vorticity-streamfunction formulation, flow past obstacles with an
  immersed-boundary penalty, Poisson streamfunction/pressure solves
  (Jacobi/SOR/FFT), plus diagnostics for drag, lift, vorticity, energy spectra
  and Reynolds stresses. Use when prototyping 2D incompressible CFD,
  teaching or benchmarking a solver against Ghia cavity data, analysing wakes
  and vortex shedding, or extracting turbulence statistics from a velocity
  field. Not for high-resolution periodic-domain pseudospectral turbulence
  (use `fluidsim`), compressible or shock-dominated flows needing Riemann
  solvers (use a dedicated compressible/Godunov solver), or 3D
  unstructured-mesh geometries (use OpenFOAM/FEniCS).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Fluid Dynamics (CFD)

## Overview

Simulate and analyse incompressible viscous flow by integrating the
Navier-Stokes equations on a structured grid. The default engine is the
**vorticity-streamfunction** formulation, which eliminates pressure and
enforces incompressibility automatically in 2D — the fastest path to a correct
lid-driven cavity, channel flow, or wake. You get compact NumPy/SciPy solvers
(no external CFD package required), stability guards, published-benchmark
validation, and post-processing for the quantities practitioners actually
report: drag, lift, vorticity fields, energy spectra, and Reynolds stresses.

This SKILL.md is a router. Runnable solvers, diagnostics, and the failure-mode
catalogue live in `references/` — read the file named by the workflow you need.

## When to Use This Skill

- Prototyping **2D incompressible flow**: lid-driven cavity, plane channel /
  Poiseuille flow, jets, shear layers.
- Simulating **flow past a bluff body** (cylinder, plate) and studying vortex
  shedding, wake structure, or the Strouhal number.
- Computing **integral loads** — drag and lift — from a resolved velocity field.
- Extracting **turbulence statistics**: kinetic-energy spectrum, Reynolds
  stresses, turbulent kinetic energy, vorticity distribution.
- **Teaching or verifying** a solver against the Ghia et al. (1982) cavity
  benchmark or an analytic Poiseuille profile.

## When NOT to Use This Skill

- **High-resolution periodic-domain turbulence** (homogeneous isotropic, forced
  2D/3D). Use `fluidsim` — its FFT-based pseudospectral core is far faster and
  more accurate on periodic boxes.
- **Compressible or shock-dominated flow** (transonic, supersonic, blast). You
  need a conservative Riemann/Godunov scheme; use a purpose-built compressible
  solver (finite-volume Godunov/WENO), not this incompressible core.
- **Complex 3D geometry / unstructured meshes** (airfoils with boundary layers,
  internal manifolds). Use OpenFOAM or FEniCS with body-fitted or unstructured
  discretisation.
- **Learned surrogates** for a PDE you will query many times — see
  `autoregressive-neural-pde-solver`.

## Choosing a Formulation

| Situation | Formulation | Reference |
|---|---|---|
| 2D, single-body or cavity, incompressible | Vorticity-streamfunction | `references/incompressible-solvers.md` |
| 2D with obstacles / open boundaries | Primitive-variable + immersed boundary (penalty) | `references/incompressible-solvers.md` |
| Need pressure explicitly (forces on wall) | Primitive-variable projection (Chorin) | `references/incompressible-solvers.md` |
| Periodic box, spectral accuracy | Delegate to `fluidsim` | — |

The vorticity-streamfunction form (`∂ω/∂t + u·∇ω = ν∇²ω`, `∇²ψ = -ω`,
`u = ∂ψ/∂y`, `v = -∂ψ/∂x`) is the recommended starting point: it is
divergence-free by construction and needs only one Poisson solve per step.

## Quick Start: Lid-Driven Cavity

Minimal, correct vorticity-streamfunction core at `Re = 100`. Full plotting,
the Ghia benchmark overlay, and SOR/FFT-accelerated Poisson solves are in
`references/incompressible-solvers.md`.

```python
import numpy as np

def lid_driven_cavity(N=64, Re=100, dt=1e-3, n_steps=30000, poisson_iters=50):
    dx = 1.0 / (N - 1)
    U_lid = 1.0
    omega = np.zeros((N, N))   # vorticity  (indexed [j=y, i=x])
    psi = np.zeros((N, N))     # streamfunction

    # Stability guards (see references/validation-and-troubleshooting.md)
    assert U_lid * dt / dx < 1.0, "advective CFL violated"
    assert dt / (Re * dx**2) < 0.25, "diffusion number too large"

    for step in range(n_steps):
        # 1. Poisson solve  ∇²ψ = -ω   (Jacobi; swap for SOR/FFT for speed)
        for _ in range(poisson_iters):
            psi[1:-1, 1:-1] = 0.25 * (
                psi[1:-1, 2:] + psi[1:-1, :-2] +
                psi[2:, 1:-1] + psi[:-2, 1:-1] +
                dx**2 * omega[1:-1, 1:-1]
            )

        # 2. Vorticity boundary conditions (Thom's first-order formula)
        omega[0, :]  = -2 * psi[1, :]  / dx**2                      # bottom
        omega[-1, :] = -2 * psi[-2, :] / dx**2 - 2 * U_lid / dx     # top (lid)
        omega[:, 0]  = -2 * psi[:, 1]  / dx**2                      # left
        omega[:, -1] = -2 * psi[:, -2] / dx**2                      # right

        # 3. Velocity from streamfunction
        u = np.zeros_like(psi); v = np.zeros_like(psi)
        u[1:-1, 1:-1] =  (psi[2:, 1:-1] - psi[:-2, 1:-1]) / (2 * dx)
        v[1:-1, 1:-1] = -(psi[1:-1, 2:] - psi[1:-1, :-2]) / (2 * dx)

        # 4. Advection + diffusion of interior vorticity (explicit FTCS)
        adv = (u[1:-1, 1:-1] * (omega[1:-1, 2:] - omega[1:-1, :-2]) / (2 * dx) +
               v[1:-1, 1:-1] * (omega[2:, 1:-1] - omega[:-2, 1:-1]) / (2 * dx))
        lap = (omega[1:-1, 2:] + omega[1:-1, :-2] +
               omega[2:, 1:-1] + omega[:-2, 1:-1] -
               4 * omega[1:-1, 1:-1]) / dx**2
        omega[1:-1, 1:-1] += dt * (-adv + lap / Re)

    return psi, omega
```

## Capability Map

- **Solvers** — lid-driven cavity, Poiseuille channel, flow past a cylinder
  (penalty immersed boundary), primitive-variable projection, and Poisson
  accelerators (Jacobi → SOR → FFT): `references/incompressible-solvers.md`.
- **Diagnostics** — drag/lift by control-volume momentum balance, vorticity and
  Q-criterion, energy spectrum, Reynolds stresses, TKE, streamline/quiver
  plots: `references/diagnostics-and-turbulence.md`.
- **Validation & failure modes** — CFL and diffusion-number limits, the
  divergence-free check, Ghia benchmark, flow-regime map, and a
  symptom → fix troubleshooting table: `references/validation-and-troubleshooting.md`.

## Non-Negotiable Sanity Checks

Before trusting any result, confirm all four (details and code in
`references/validation-and-troubleshooting.md`):

1. **Stability** — `|u|·dt/dx < 1` (advective CFL) and `dt/(Re·dx²) < 0.25`
   (explicit diffusion) hold at the actual peak velocity, not the nominal one.
2. **Incompressibility** — `max|∇·u|` stays near machine/discretisation noise.
3. **Convergence** — steady runs reach a plateau in `max|ω|`; refine the grid
   until the reported quantity (e.g. cavity centerline) stops moving.
4. **Benchmark** — cavity centerline profiles match Ghia et al. (1982) at the
   same `Re`.

## Related Skills

- `fluidsim` — pseudospectral solver for periodic-domain turbulence; use it
  instead of this skill whenever the domain is a periodic box.
- `dimensional-analysis` — derive Reynolds, Strouhal, and other non-dimensional
  groups before choosing grid and time step.
- `conservation-law-discovery` / `autoregressive-neural-pde-solver` — data-driven
  and learned-surrogate approaches to flow PDEs.
- `matplotlib` — publication-quality rendering of the fields this skill produces.
