# Pitfalls, Validation, and Boundaries

Conservation discovery is a chain of numerical amplifications: integrator error →
derivative error → null-space error. Each failure below produces confident-looking garbage.
Work through them before trusting any result.

## Trajectory precision sets the ceiling

The method can never resolve conservation better than the trajectory itself is integrated.

- Use tight tolerances (`rtol=1e-12, atol=1e-14`) or a **symplectic / structure-preserving
  integrator** for Hamiltonian systems — standard RK45 slowly leaks energy and will make a
  truly conserved quantity look like it drifts.
- Sample uniformly and densely in time; sparse sampling wrecks finite-difference
  derivatives.
- Diagnostic: if a *known* invariant (energy, momentum) shows drift above ~1e-6, fix the
  integrator before searching for new invariants — the search is running on sand.

## Derivative noise

Finite differences (`np.gradient`) amplify sampling noise and are worst at the trajectory
endpoints.

- **Trim edges** (`trim=10` samples in the recipe) before the SVD.
- Prefer **spline or spectral (FFT) derivatives** for smooth, uniformly sampled data.
- Best of all: if you know the vector field `f`, compute **exact derivatives**
  `dΦ/dt = J_Φ(x)·f(x)` and skip differentiation entirely (see
  [discovery-recipe.md](discovery-recipe.md) §5). This removes the dominant error term and
  the need to trim.

## Trivial invariants

The constant feature `1` has zero time derivative, so it is *always* a perfect null vector.
It is a gauge freedom (any invariant plus a constant is still an invariant), not a
discovery. Exclude the constant column from the derivative matrix before the SVD (the recipe
does this with `dPhi_dt[..., 1:]`), then re-insert its slot when reconstructing `I`.

## Degenerate and redundant invariants

The near-null subspace often contains several vectors that are **functions of the same
underlying invariants** — e.g. `E`, `E²`, and `E·L` all appear once you include enough
monomials. Consequences and fixes:

- Any *smooth function of an invariant is itself an invariant*, so raw counts of small
  singular values over-report the number of laws.
- Orthogonalize the candidate subspace and rank-check it; report **functionally independent**
  invariants (check that their gradients `∇I_k` are linearly independent across the sampled
  states, i.e. the Jacobian of `[I_1,…,I_k]` has full row rank almost everywhere).

## Single-trajectory spurious invariants

On one orbit the state traces a low-dimensional curve, so **many** functions happen to be
constant along it that are not invariants of the system. This is the most common way to
fool yourself.

- Always validate candidates on trajectories from **different initial conditions**.
- Better: pool multiple trajectories into one feature/derivative matrix *before* the SVD
  (see the `multi_trajectory_invariants` recipe) so only globally valid invariants have a
  small singular value.

## How many independent invariants can exist

Use these ceilings as a sanity check on your candidate count:

- An autonomous system with an `n`-dimensional state has at most `n−1` functionally
  independent time-independent invariants (the trajectory itself fills one dimension).
- A Hamiltonian system with `n` degrees of freedom (`2n`-dimensional phase space) is
  **Liouville-integrable** if it has `n` independent invariants in involution; it is
  **superintegrable** with up to `2n−1` (Kepler and the isotropic oscillator are the
  classic examples — the Laplace–Runge–Lenz vector is the "extra" one).
- If your method reports more independent invariants than these bounds allow, you are
  seeing numerical artifacts or redundant functions — recount after orthogonalizing.

## Conditioning and normalization

- Scale each state variable to O(1) before building `Φ`; mixed scales (positions ~1,
  velocities ~100) blow up the condition number of the feature matrix and create spurious
  near-null directions.
- Watch `np.linalg.cond(Phi)`; if it is very large (≫ 1e8), the SVD threshold `tol_ratio`
  becomes meaningless — reduce `max_degree` or rescale.

## Threshold selection

The cutoff `tol_ratio = 1e-6` (relative to the largest singular value) is a heuristic. Look
for a **gap** in the singular-value spectrum rather than trusting a fixed number: genuine
invariants sit well below a clear step down from the "active" directions. If there is no
gap, there is probably no low-order invariant in your library — enrich it
([methods.md](methods.md)) or accept that none exists.

## When nothing is conserved (and that is correct)

Dissipative (friction, drag) and stochastic (noise-driven) systems have **no exact
invariants** — a null result is the right answer, not a failure of the method. Do not force
a "conserved quantity" out of such data. Slowly varying **adiabatic invariants** may exist
under slow parameter drift, but separating them from noise requires dedicated methods and is
out of scope here; `bayesian-inference` and `dynamical-systems` are better starting points
for noisy or driven systems.
