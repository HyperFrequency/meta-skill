---
name: dimensional-analysis
version: 0.1.0
description: >-
  Systematic dimensional analysis for physics and engineering computations. Apply the
  Buckingham Pi theorem to find the dimensionless groups that govern a problem (via the null
  space of the dimension matrix), non-dimensionalize equations to expose their controlling
  parameters, validate unit consistency and check derived formulas with `pint`, and compute
  the standard dimensionless numbers (Re, Ma, Pr, Ra, Pe, Fr, We...) with flow-regime
  interpretation. Use before running any physics computation to catch unit errors, to reduce
  a parameter sweep to its irreducible dimensionless axes, to decide which physical effects
  dominate, or to non-dimensionalize a PDE before solving. NOT for pure symbolic algebra
  unrelated to units (use `sympy`), for discovering the governing equations or conserved
  quantities themselves from data (use `conservation-law-discovery`), or for numerically
  solving the resulting PDE (use `autoregressive-neural-pde-solver`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (pint, SymPy, NumPy)"
---

# Dimensional Analysis

## Overview

Every physical equation must be dimensionally homogeneous, and every physical result is
governed by a smaller set of dimensionless groups than it has raw variables. This skill turns
that structure into four concrete, mechanical operations you run *before* committing to a
computation:

1. **Buckingham Pi** — count and construct the dimensionless groups a problem depends on, so
   a study of `n` variables collapses to `n − rank` dimensionless axes.
2. **Unit validation** — carry units through a calculation with `pint` so a `kg + m/s`
   mistake fails loudly instead of producing a plausible wrong number.
3. **Non-dimensionalization** — rescale the governing equations by characteristic scales so
   the controlling ratios (Reynolds, Péclet, ...) appear as explicit coefficients.
4. **Dimensionless numbers** — compute the standard groups from physical parameters and read
   off the regime (laminar/turbulent, diffusion/advection dominated, etc.).

All of it rests on the fundamental dimensions **M** (mass), **L** (length), **T** (time),
**Θ** (temperature), **I** (current), **N** (amount), **J** (luminous intensity). The full
dimension/unit table lives in
[references/dimensionless-numbers.md](references/dimensionless-numbers.md).

## When to Use This Skill

- **Before any physics computation** — verify the formula you are about to evaluate is
  dimensionally consistent, and that your inputs carry the units you assume.
- **Reducing a parameter sweep** — `n` physical parameters usually reduce to `n − rank`
  dimensionless groups; sweep those instead and cut the study's dimensionality.
- **Deciding which effects dominate** — compute the relevant dimensionless numbers and
  compare (e.g. `Re ≫ 1` ⇒ inertia beats viscosity; `Pe ≫ 1` ⇒ advection beats diffusion).
- **Non-dimensionalizing a PDE** before handing it to a solver, so the equation is stated in
  its natural O(1) variables and its stiffness/controlling ratios are explicit.
- **Sanity-checking a derived formula** — confirm both sides of an equation, or the argument
  of an `exp`/`log`, are dimensionally what they should be.

## When NOT to Use This Skill

- **Pure symbolic algebra** with no unit content (solving, simplifying, series) — use
  `sympy` directly.
- **Discovering the equations or invariants themselves** from trajectory/measurement data —
  use `conservation-law-discovery` (integrals of motion) or a system-identification method.
- **Numerically solving** the non-dimensional PDE you produced — use
  `autoregressive-neural-pde-solver`, or a classical solver.
- **Getting a numeric answer** — dimensional analysis fixes the *form* `Π₁ = f(Π₂, ...)` and
  the scaling, but never the dimensionless constants (the `2π`, the `C_D(Re)` curve). Those
  need experiment, simulation, or full theory.

## Workflow

### 1. Find the dimensionless groups (Buckingham Pi)

Assemble the variables with their dimension exponents, build the dimension matrix `D`
(one row per fundamental dimension, one column per variable), and read the Pi groups off its
null space. The number of independent groups is `n_vars − rank(D)`.

```python
import numpy as np
from sympy import Matrix

# Drag on a sphere: F depends on velocity v, diameter d, density rho, viscosity mu
variables = {
    'F':   {'M': 1, 'L': 1, 'T': -2},
    'v':   {'L': 1, 'T': -1},
    'd':   {'L': 1},
    'rho': {'M': 1, 'L': -3},
    'mu':  {'M': 1, 'L': -1, 'T': -1},
}
dims = ['M', 'L', 'T']
D = np.array([[variables[v].get(d, 0) for v in variables] for d in dims], float)

n_pi = len(variables) - np.linalg.matrix_rank(D)      # -> 2 groups
null = Matrix(D).nullspace()                          # exact rational exponent vectors
# Π1 = F / (rho v^2 d^2)  (drag coefficient C_D);  Π2 = rho v d / mu  (Reynolds number)
# Conclusion: C_D = f(Re)
```

Use exact rational arithmetic (SymPy `Matrix.nullspace()`), not a floating-point SVD, so the
exponents come out as clean rationals. The full `buckingham_pi()` printer, how to choose
repeating variables to get *named* groups, and degenerate/over-determined cases are in
[references/buckingham-pi.md](references/buckingham-pi.md).

### 2. Validate units and check formulas (pint)

Attach units to every quantity and let `pint` enforce homogeneity. Adding incompatible
dimensions raises `DimensionalityError` instead of silently succeeding.

```python
import pint
ureg = pint.UnitRegistry(); Q_ = ureg.Quantity

KE = 0.5 * Q_(2.0, 'kg') * Q_(3.0, 'm/s')**2
print(KE.to('J'))                      # 9.0 joule  -- dimensions check out

Q_(2, 'kg') + Q_(3, 'm/s')             # raises pint.DimensionalityError
```

`pint` also converts between unit systems (`force.to('dyn')`, `.to('lbf')`) and, given a
string formula plus per-variable units, will tell you the resulting dimension so you can
confirm a derived expression. The formula-checker helper and unit-system conversion recipes
are in [references/units-and-checking.md](references/units-and-checking.md).

### 3. Non-dimensionalize the governing equations

Substitute each variable by `characteristic_scale × dimensionless_variable`, then divide
through by a common prefactor. The controlling dimensionless groups fall out as the
coefficients that remain.

```
Navier–Stokes:  rho (∂u/∂t + u·∇u) = -∇p + mu ∇²u
scales:  x* = x/L,  t* = tU/L,  u* = u/U,  p* = p/(rho U²)
becomes: ∂u*/∂t* + u*·∇*u* = -∇*p* + (1/Re) ∇*²u*   with  Re = rho U L / mu
```

Choosing the scales is the whole art: pick each characteristic scale from the physics of the
problem (imposed velocity, domain size, diffusion time `L²/α`, ...). Worked derivations for
advection–diffusion, the pendulum, and how to estimate characteristic scales when they are
not handed to you are in [references/units-and-checking.md](references/units-and-checking.md).

### 4. Compute dimensionless numbers and read the regime

Given physical parameters, compute the standard groups and interpret the ratio.

```python
# Water in a 5 cm pipe at 2 m/s
rho, v, L, mu = 998, 2.0, 0.05, 1.0e-3
Re = rho * v * L / mu                   # 9.98e4
# Re < 2300 laminar | 2300-4000 transitional | > 4000 turbulent  -> turbulent
```

The full catalogue (Re, Ma, Pr, Ra, Pe, Sc, Kn, Fr, We, St, Nu, ...) with formulas, physical
meaning, the `dimensionless_numbers()` computation helper, and regime thresholds is in
[references/dimensionless-numbers.md](references/dimensionless-numbers.md).

## Pitfalls

- **Missing a governing variable** inflates or deflates the Pi count. If your groups do not
  match known physics, you probably omitted a relevant quantity (or included an irrelevant
  one). Buckingham tells you *how many* groups exist, not *which* variables matter.
- **Non-unique groups.** The null space has a basis, not a canonical answer — any invertible
  combination of the Pi groups is equally valid. Choose repeating variables to recover the
  conventional named groups (see the reference).
- **Angles, counts, and logs.** Radians and pure counts are dimensionless; arguments of
  `exp`, `log`, `sin` must be dimensionless — a good place to catch a scaling error.
- **Temperature offsets.** `pint` distinguishes absolute (K) from offset (°C) units; use
  kelvin for ratios and multiplicative work to avoid offset-unit errors.
- **Dimensional analysis fixes form, not constants.** It gives `C_D = f(Re)`, never the
  `f`. Do not over-claim a result the method cannot deliver.

## References

- [references/buckingham-pi.md](references/buckingham-pi.md) — full `buckingham_pi()`
  implementation, the dimension-matrix / null-space method, choosing repeating variables to
  get named groups, worked examples (drag, pendulum, pipe flow), and degenerate cases.
- [references/units-and-checking.md](references/units-and-checking.md) — `pint` quantity
  arithmetic, `DimensionalityError` handling, the string-formula dimension checker, unit-
  system conversion, and non-dimensionalization / characteristic-scale recipes.
- [references/dimensionless-numbers.md](references/dimensionless-numbers.md) — fundamental
  dimensions table, the full dimensionless-number catalogue with meanings, the
  `dimensionless_numbers()` helper, and flow/transport regime thresholds.
