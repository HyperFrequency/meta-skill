---
name: conservation-law-discovery
version: 0.1.0
description: >-
  Discover conserved quantities (integrals of motion) and their hidden symmetries directly
  from trajectory data, without knowing the equations of motion. Builds a candidate-function
  library, finds combinations whose time derivative vanishes along trajectories via an SVD
  null-space of dΦ/dt, and validates them across multiple trajectories. Use when you have
  numerically integrated or measured trajectories and want to find or verify energy /
  momentum / angular-momentum or custom invariants, expose approximate symmetries, or check
  that a simulation conserves what it should. NOT for fitting the dynamics themselves (use
  `sindy-identification` or `symbolic-regression`), for stochastic or dissipative systems
  where nothing is conserved, or for symbolic Noether derivations from a known Lagrangian
  (use `hamiltonian-mechanics`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (NumPy, SciPy)"
---

# Conservation Law Discovery

## Overview

Given a sampled trajectory `x(t)` from a dynamical system, find scalar functions `I(x)`
that stay constant along the flow — `dI/dt = 0`. These integrals of motion (energy,
momentum, angular momentum, or system-specific invariants) are the data-side shadow of the
system's continuous symmetries (Noether's theorem) and are among the sharpest checks you
can run on a simulator or a learned model.

The core engine is linear-algebraic and needs no knowledge of the governing equations:

1. Build a **feature library** `Φ(x)` — a set of candidate basis functions (monomials by
   default) evaluated at every sample.
2. Form the **time-derivative matrix** `Ψ = dΦ/dt` along the trajectory.
3. A conserved quantity `I = Φ·c` satisfies `Ψ·c ≈ 0` for all `t`, so its coefficient
   vector `c` lives in the **null space of `Ψ`**. Read the candidates off the small
   singular values of an SVD.
4. **Validate** every candidate on held-out samples and, critically, on trajectories from
   *different* initial conditions — a quantity constant on one orbit is not yet an invariant
   of the system.

## When to Use This Skill

- You have numerically integrated or measured trajectories and want to **find** unknown
  conserved quantities.
- You want to **verify** that a simulation conserves energy / momentum / a known invariant,
  and quantify the drift.
- You suspect a **hidden symmetry** or extra integral of motion (superintegrability, e.g.
  the Laplace–Runge–Lenz vector in the Kepler problem) and want data-driven evidence.
- You need a **regression gate** on a learned dynamics model: does it preserve the
  invariants the true system has?

## When NOT to Use This Skill

- You want the **equations of motion** themselves, not their invariants — use
  `sindy-identification` or `symbolic-regression`.
- The system is **stochastic or dissipative** (friction, noise, driving) so nothing is
  exactly conserved — at best you can look for slowly varying adiabatic quantities, which
  this method will not cleanly separate from noise.
- You have a **known Lagrangian / Hamiltonian** and want a symbolic Noether derivation —
  work analytically; see `hamiltonian-mechanics`.
- Your data is a handful of noisy points with no reliable time derivative — conservation
  discovery amplifies derivative noise; get accurate, densely sampled trajectories first.

## Prerequisites: trajectory accuracy dominates everything

Conservation discovery is only as good as the trajectory it runs on. A loose integrator
manufactures fake drift and hides real invariants under numerical noise.

- Integrate with tight tolerances (`solve_ivp(..., rtol=1e-12, atol=1e-14)`) or a
  symplectic integrator for Hamiltonian systems.
- Sample densely and uniformly in time so finite-difference derivatives are meaningful.
- **If you know the vector field `f`, do not finite-difference at all** — compute exact
  derivatives `dΦ/dt = J_Φ(x)·f(x)`. This removes the single largest error source. See
  [references/pitfalls.md](references/pitfalls.md).

## Workflow

### 1. Check the known invariants first

Before searching, compute the textbook invariants and look at their relative drift. This
sanity-checks your trajectory precision and often answers the question outright.

```python
def relative_drift(I_values):
    return I_values.std() / (abs(I_values.mean()) + 1e-15)
# conserved  ⇢  relative_drift ≲ 1e-6 for a well-integrated trajectory
```

Full Kepler example (energy, angular momentum, Laplace–Runge–Lenz), plus the drift-plot
recipe, is in [references/discovery-recipe.md](references/discovery-recipe.md).

### 2. Discover invariants via the null space of `dΦ/dt`

Build a monomial library, take its time derivative, and SVD it. Each right-singular vector
with a near-zero singular value is a candidate invariant's coefficient vector.

```python
import numpy as np

# Phi: (T, M) feature matrix of monomials in the state variables
# dPhi_dt: (T, M) their time derivatives (exact if the vector field is known)
# Drop the constant column (index 0) from the DERIVATIVE matrix — it is trivially conserved.
U, S, Vt = np.linalg.svd(dPhi_dt[trim:-trim, 1:], full_matrices=False)  # trim edge samples
tol = 1e-6 * S[0]
n_conserved = int((S < tol).sum())
candidates = Vt[-n_conserved:]        # coefficient vectors, one invariant per row
```

The full `poly_features` builder and `find_polynomial_invariant` function (with degeneracy
handling and human-readable expression printing) are in
[references/discovery-recipe.md](references/discovery-recipe.md).

### 3. Validate every candidate

A small singular value is necessary, not sufficient. For each candidate `I = Φ·c`:

- **Held-out drift:** recompute `relative_drift(I)` on a trajectory segment not used to
  fit `c`.
- **Cross-orbit test (the decisive one):** evaluate `I` on trajectories from *different*
  initial conditions. A true integral of motion is conserved on every orbit; a single-orbit
  fit is not. Stack multiple trajectories into `Φ`/`Ψ` before the SVD to find only the
  global invariants.
- **Independence:** an `n`-dimensional autonomous phase space admits at most `n−1`
  functionally independent invariants; extras are functions of the ones you found (e.g. `E`
  and `E²`). Orthogonalize / rank-check the candidate subspace.

The `test_conservation` helper and the multi-trajectory global-invariant recipe are in
[references/discovery-recipe.md](references/discovery-recipe.md).

### 4. Escalate when the polynomial library fails

If no invariant appears, the conserved quantity may be non-polynomial (rational,
trigonometric, `1/r`). Choose a stronger method — trade-offs and API sketches in
[references/methods.md](references/methods.md):

| Method | Finds | Cost |
|---|---|---|
| Polynomial null space (default) | polynomial invariants | cheap, interpretable |
| Enriched library (add `1/r`, `sin`, `cos`) | known non-polynomial forms | cheap if you guess the terms |
| Symbolic regression (`symbolic-regression`, PySR) | arbitrary closed forms | slow, human-readable |
| Constrained SINDy (`sindy-identification`) | sparse invariants tied to the fitted dynamics | needs a good library |
| Neural-autoencoder invariant | arbitrary smooth invariants | trains, hard to interpret |

## Pitfalls (read before trusting a result)

- **The constant feature is trivially conserved** — exclude column `1` from the derivative
  matrix or it dominates the null space.
- **Single-trajectory spurious invariants** — any function constant along one orbit passes;
  always cross-validate across initial conditions.
- **Finite-difference noise** at endpoints — trim edges, or use spline/spectral derivatives,
  or exact `J_Φ·f`.
- **Poor conditioning** — normalize state variables to O(1) before building `Φ`.

Full failure-mode catalogue, conditioning fixes, and the invariant-counting rules are in
[references/pitfalls.md](references/pitfalls.md).

## References

- [references/discovery-recipe.md](references/discovery-recipe.md) — runnable code: Kepler
  drift check, polynomial null-space finder, candidate tester, multi-trajectory global
  discovery, exact-derivative path.
- [references/methods.md](references/methods.md) — method comparison, enriched libraries,
  symbolic regression, constrained SINDy, neural-autoencoder and Noether/symmetry
  approaches, with API sketches.
- [references/pitfalls.md](references/pitfalls.md) — precision requirements, derivative
  noise, trivial/degenerate/spurious invariants, conditioning, and how many independent
  invariants a system can have.
