---
name: pde-solver
version: 0.1.0
description: >-
  Solve partial differential equations numerically on simple geometries with classical
  schemes and physics-informed neural networks. Covers finite differences
  (explicit/implicit/Crank–Nicolson), Fourier and Chebyshev spectral methods, the Method of
  Lines with SciPy's solve_ivp, and PINNs via DeepXDE — for elliptic (Laplace/Poisson),
  parabolic (heat/diffusion), and hyperbolic (wave) equations in 1D/2D/3D with Dirichlet,
  Neumann, or periodic boundary conditions, plus inverse parameter-discovery problems. Use to
  solve or validate a PDE on a rectangle/box/periodic domain, pick a stable time-stepping
  scheme, or set up a PINN. NOT for learned autoregressive neural-operator surrogates (use
  `autoregressive-neural-pde-solver`), complex unstructured-mesh geometries (use a finite-
  element package like FEniCS/dolfinx), turbulent Navier–Stokes flows (use `fluid-dynamics`),
  or pure ODE systems with no spatial derivative (integrate directly with solve_ivp).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (NumPy, SciPy); LGPL-2.1 (DeepXDE)"
---

# PDE Solver

## Overview

Solve partial differential equations by discretizing space and time and reducing the problem
to linear algebra or an ODE system — or, when meshing is impractical, by training a network
to satisfy the equation. This skill covers the three classical families (finite differences,
spectral methods, the Method of Lines) plus physics-informed neural networks, across the
standard equation classes:

- **Elliptic** — steady state, no time (Laplace `∇²u = 0`, Poisson `∇²u = f`). Solve a linear
  system once.
- **Parabolic** — diffusion in time (heat, reaction–diffusion). March in time; watch stability.
- **Hyperbolic** — wave propagation (`u_tt = c²∇²u`, advection). Finite CFL, no smoothing.

Everything here assumes a **simple, structured geometry** (interval, rectangle, box, or
periodic domain). The depth — full method code, DeepXDE API, and the stability/validation
playbook — lives in `references/`; this page routes you to the right one.

## When to Use This Skill

- Solving any PDE in physics/engineering on a rectangle, box, or periodic domain (heat, wave,
  Poisson/Laplace, advection–diffusion, Schrödinger, etc.).
- Steady-state **or** time-dependent problems in 1D, 2D, or 3D.
- Choosing a stable, accurate scheme and diagnosing a solution that blew up or won't converge.
- **Inverse problems** — recovering an unknown coefficient or source from measured data (PINN).
- Validating a numerical solution against an analytical or manufactured reference.

## When NOT to Use This Skill

- **Learned neural-operator surrogates** (FNO/DeepONet) trained on trajectory data and rolled
  out in time — a supervised, not residual-based, paradigm → `autoregressive-neural-pde-solver`.
- **Complex/unstructured/curved geometries** needing unstructured meshes → finite elements
  (FEniCS / `dolfinx`), which structured-grid methods here do not cover.
- **Turbulent or high-Reynolds fluid flows** on periodic domains → `fluid-dynamics`.
- **A pure ODE system** with no spatial derivative → integrate directly with SciPy `solve_ivp`.
- **Non-dimensionalizing** the equation before you solve → `dimensional-analysis`.
- **Symbolic/analytical** closed-form solutions → `sympy`.

## Method Selection

| Problem | Simple geometry | Complex geometry | Inverse problem |
|---|---|---|---|
| 1D steady | Finite differences | FEM (FEniCS) | PINN (DeepXDE) |
| 1D transient | MOL + `solve_ivp` | FEM | PINN |
| 2D steady | Finite differences / spectral | FEM | PINN |
| 2D transient | MOL (implicit) or ADI | FEM | PINN |
| 3D | Spectral if periodic | FEM | PINN |

Rule of thumb: **finite differences** for a first solve on a grid, **spectral** for smooth
periodic problems (exponential accuracy), **Method of Lines** as the best general-purpose
transient solver (adaptive time step, no hand-derived CFL), and **PINNs** only when meshing
fails or you are solving an inverse problem.

## Finite Differences

Replace derivatives with stencils on a uniform grid. Explicit schemes are simplest but
CFL-limited; implicit (Crank–Nicolson, backward Euler) are unconditionally stable. Canonical
explicit 1D heat solver with its stability guard:

```python
import numpy as np

def heat_1d_explicit(L=1.0, T=0.5, alpha=0.01, Nx=100, Nt=5000):
    dx, dt = L / Nx, T / Nt
    r = alpha * dt / dx**2
    if r > 0.5:                                   # CFL: explicit heat needs r ≤ 0.5
        raise ValueError(f"CFL violated: r={r:.4f} > 0.5. Reduce dt or coarsen space.")
    x = np.linspace(0, L, Nx + 1)
    u = np.sin(np.pi * x / L)                     # initial condition; u=0 at both ends
    for _ in range(Nt):
        u[1:-1] += r * (u[2:] - 2 * u[1:-1] + u[:-2])
    return x, u
```

Crank–Nicolson and backward-Euler solvers, the 2D Poisson Kronecker-product sparse solve,
Neumann/periodic boundary handling, and iterative solvers (CG/GMRES + preconditioners) for
large systems are in **[references/classical-methods.md](references/classical-methods.md)**.

## Spectral Methods

For smooth solutions on periodic domains, expand in a Fourier basis so differentiation is
multiplication by `ik` — accuracy is exponential in the number of modes. Use Chebyshev
collocation for bounded non-periodic domains, and the 2/3 dealiasing rule for nonlinear
terms. The Fourier pseudospectral wave-equation solver and Chebyshev/dealiasing notes are in
**[references/classical-methods.md](references/classical-methods.md)**.

## Method of Lines

Discretize space only, leaving a coupled ODE system `du/dt = f(t, u)`, then hand it to an
adaptive integrator — the recommended approach for transient PDEs on simple grids.

```python
from scipy.integrate import solve_ivp
# rhs(t, u) applies the spatial stencil; diffusion is stiff → use an implicit integrator
sol = solve_ivp(rhs, (0, T), u0_interior, method="BDF", rtol=1e-8, atol=1e-10)
```

Diffusion-discretized systems are **stiff** — use `method="BDF"`/`"Radau"`, not `RK45`. Full
1D/2D MOL patterns are in **[references/classical-methods.md](references/classical-methods.md)**.

## Physics-Informed Neural Networks (DeepXDE)

`pip install deepxde`. Train a network to minimize the PDE residual on collocation points
plus BC/IC error — no mesh. Best for **inverse problems**, irregular domains, and high
dimensions; usually slower and less accurate than finite differences on simple forward
problems. Standard recipe: Adam to reach a good region, then L-BFGS to polish.

```python
import deepxde as dde
def pde(x, y):                                   # e.g. Laplace: u_xx + u_yy = 0
    return dde.grad.hessian(y, x, i=0, j=0) + dde.grad.hessian(y, x, i=1, j=1)
# geom + dde.icbc.DirichletBC(...) → dde.data.PDE → dde.nn.FNN → dde.Model
# model.compile("adam", lr=1e-3); model.train(iterations=10000)
# model.compile("L-BFGS"); model.train()
```

Full forward and **inverse** (recover an unknown coefficient via `dde.Variable` +
`PointSetBC` observations) workflows, time-dependent setups, hard-constrained BCs, loss
weighting, and RAR are in **[references/pinns-deepxde.md](references/pinns-deepxde.md)**.

## Stability and Validation

Never trust a solution until it is stable, convergent, and consistent. Explicit schemes are
CFL-limited (`r = αΔt/Δx² ≤ 0.5` for heat; `cΔt/Δx ≤ 1` for waves); implicit and adaptive
methods lift that limit. Always run a **mesh-convergence study** (halve `Δx`, confirm the
error drops at the scheme's order) and check the solution satisfies its BCs and conservation
laws. The full stability table, convergence/manufactured-solution recipes, the validation
checklist, and a symptom→cause→fix troubleshooting table are in
**[references/stability-and-validation.md](references/stability-and-validation.md)**.

## References

- **[references/classical-methods.md](references/classical-methods.md)** — finite differences
  (explicit/implicit/Crank–Nicolson, 2D Poisson, BC handling, iterative solvers), Fourier &
  Chebyshev spectral methods, and the Method of Lines.
- **[references/pinns-deepxde.md](references/pinns-deepxde.md)** — DeepXDE forward and inverse
  PINN workflows, time-dependent problems, training tips, and when PINNs are the wrong tool.
- **[references/stability-and-validation.md](references/stability-and-validation.md)** —
  stability/CFL conditions, mesh convergence, MMS, the validation checklist, and troubleshooting.

## Related Skills

- `autoregressive-neural-pde-solver` — learned neural-operator surrogates (FNO/DeepONet) for
  time-dependent PDEs, trained on trajectory data and rolled out in time.
- `fluid-dynamics` — turbulent / high-Reynolds Navier–Stokes and specialist flow solvers.
- `ode-solver` — pure ODE/IVP systems (what a PDE becomes after the Method of Lines).
- `dimensional-analysis` — non-dimensionalize the PDE and find its controlling groups first.
- `sympy` — symbolic/analytical solutions and manufactured-solution source terms.
