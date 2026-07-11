# Methods — Choosing and Escalating

The polynomial null-space method in [discovery-recipe.md](discovery-recipe.md) is the
default: cheap, deterministic, and interpretable. Reach for the alternatives below when the
conserved quantity is not a low-degree polynomial or you need a closed-form expression.

## Comparison

| Method | Function class it can find | Interpretability | Cost / caveats |
|---|---|---|---|
| Polynomial null space | polynomials up to `max_degree` | high (explicit coeffs) | misses `1/r`, `sin`, rational forms |
| Enriched linear library | whatever basis you add | high | you must guess the right terms |
| Symbolic regression (PySR) | arbitrary closed forms | high | slow, stochastic, may not converge |
| Constrained SINDy | sparse invariants tied to fitted dynamics | high | needs a good candidate library |
| Neural-autoencoder invariant | arbitrary smooth `I(x)` | low (black box) | trains; needs anti-collapse constraint |
| Noether from a known symmetry | exact, from the generator | high | requires the symmetry generator up front |

## Enriched linear library (cheapest escalation)

The null-space machinery is linear in the *coefficients*, not in the features — so you can
add any nonlinear basis functions you suspect and keep the exact same SVD pipeline. This is
almost always the first thing to try when polynomials fail.

```python
# extend poly_features(...) output with problem-specific columns before the SVD, e.g.:
r = np.sqrt(x**2 + ypos**2)
extra = np.column_stack([1.0 / r, 1.0 / r**2])          # recovers Kepler energy's 1/r term
Phi = np.column_stack([Phi, extra])
names += ["1/r", "1/r^2"]
```

Good candidate enrichments: `1/r`, `1/r^2` (central forces); `sin`, `cos` of angle
variables (rotations, pendulums); `log`, `exp` (growth/decay balances); pairwise products
across subsystems (coupled invariants). Keep the library small — every added column raises
the condition number and the odds of a spurious near-null direction.

## Symbolic regression

Search directly for a closed-form `I(x)` whose time derivative vanishes. The clean
formulation minimizes the along-trajectory variance of `I` (or of `dI/dt = ∇I·f`) subject
to a non-triviality constraint so the search does not collapse to a constant. This is a
custom-objective run — delegate the actual search to the sibling skill
`symbolic-regression` (PySR under the hood) and feed it either the trajectory or, if you
know the vector field, the exact derivative expression. Expect minutes-to-hours and
non-deterministic output; always re-validate the discovered form with
`test_conservation` from [discovery-recipe.md](discovery-recipe.md).

## Constrained SINDy

`sindy-identification` fits the dynamics `dx/dt = Θ(x)·Ξ` from data. Conserved quantities
are the (approximate) left null space of the fitted feature-derivative system, and SINDy
variants (e.g. constrained / trapping formulations) can be biased toward energy-preserving
structure. Use this when you want the invariants *and* the dynamics to come from one
consistent sparse model. It needs a well-chosen candidate library, same as the polynomial
method here.

## Neural-autoencoder invariant

Parameterize `I_θ(x)` as a small MLP and minimize the variance of `I_θ` along each
trajectory, plus a constraint that prevents the trivial constant solution (e.g. fix
`‖∇I_θ‖` to unit scale, or enforce unit output variance across the whole dataset). Multiple
independent invariants are found by adding an orthogonality penalty between their gradients.
This finds arbitrary smooth invariants but yields a black-box function — post-fit, probe it
with symbolic regression or level-set plots to interpret. This is the data-driven analogue
of "AI-Poincaré"-style invariant search; treat the count of near-zero-variance networks as
an *estimate* of the number of independent conservation laws (see
[pitfalls.md](pitfalls.md) for the theoretical ceiling).

## Noether / symmetry route

If you already know a continuous symmetry (an infinitesimal generator that leaves the
dynamics invariant), the corresponding conserved quantity follows directly from Noether's
theorem — no search needed. Going the other way (invariant → symmetry) is also possible: a
discovered `I(x)` generates a symmetry via its Hamiltonian flow. For symbolic derivations
from a known Lagrangian or Hamiltonian, use `hamiltonian-mechanics` rather than any of the
data-driven methods here.
