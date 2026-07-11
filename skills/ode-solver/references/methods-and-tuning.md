# ODE Solver — Methods & Tuning

Full solver selection, tolerance/step semantics, Jacobians, and stiffness
detection for `scipy.integrate.solve_ivp` (and `solve_bvp`).

## Method selection

| `method` | Class / order | Use when |
|---|---|---|
| `RK45` | explicit RK, order 5(4) | Default. General non-stiff problems. |
| `RK23` | explicit RK, order 3(2) | Quick, low-accuracy estimates. |
| `DOP853` | explicit RK, order 8 | High accuracy: long integrations, reference solutions, smooth systems. |
| `Radau` | implicit RK (order 5) | Stiff systems; good for moderate size, needs a Jacobian solve per step. |
| `BDF` | implicit multistep (var. order 1–5) | Large stiff systems; efficient when the rhs is expensive. |
| `LSODA` | Adams / BDF auto-switch | Stiffness unknown or changes over the interval. |
| leapfrog / Verlet | symplectic, order 2 | Hamiltonian systems needing long-time energy conservation (hand-rolled, see recipes). |

Rules of thumb:
- Start with `RK45`. If it is slow or fails, suspect stiffness and try `Radau`
  or `LSODA`.
- Reach for `DOP853` only when you need very tight accuracy on a smooth,
  non-stiff system; it is wasteful otherwise.
- For anything that must conserve an invariant over many periods, prefer a
  symplectic integrator over tightening tolerances on a non-symplectic one.

## Tolerances: `rtol` and `atol`

The local error target for component `i` is roughly
`atol + rtol * abs(y[i])`.

- `rtol` (default `1e-3`) controls relative accuracy — the number of correct
  significant digits. Tighten to `1e-8`…`1e-10` for quantitative work.
- `atol` (default `1e-6`) sets the floor near zero crossings; set it well below
  the smallest magnitude that matters, per component if scales differ
  (`atol` may be an array).
- Tightening tolerances costs more steps. If a solution changes when you go
  from `rtol=1e-6` to `1e-9`, it was not converged — keep tightening until it
  stops moving.

## Step control

- `max_step` — hard cap on the internal step size. Use it to (a) stop an
  explicit solver from stepping over a fast event, and (b) force resolution
  through a stiff transient. It does **not** set the output grid.
- `first_step` — initial step; usually leave to the solver.
- `t_eval` — the times at which output is *returned*. It is decoupled from the
  internal steps and does not affect accuracy. Omit it to get the solver's
  natural steps.
- `dense_output=True` — build a continuous interpolant; then call `sol.sol(t)`
  at arbitrary times (also underlies precise event location).

## Jacobians

For `Radau` / `BDF`, supplying `jac` (the matrix `∂f_i/∂y_j`) avoids finite
differencing and can cut cost dramatically. It may be:
- a constant array (linear systems),
- a callable `jac(t, y)` returning an `(n, n)` array,
- a sparse matrix (or `jac_sparsity` pattern) for large systems.

Derive it symbolically with `sympy` and `sympy.lambdify` when the algebra is
tedious.

## Detecting stiffness

A system is stiff when stability, not accuracy, forces tiny steps. Signals:
- An explicit solver (`RK45`) reports a very large `sol.nfev`, crawls, or
  returns `success=False`.
- The system has widely separated timescales (fast decays alongside slow
  drift).
- The Jacobian has eigenvalues with large negative real parts (ratio of
  largest to smallest |real part| is large).

Cheap test: run the interval with `RK45` and with `LSODA`; if `LSODA` finishes
in far fewer evaluations, the problem is stiff — commit to `Radau`/`BDF`.

## `solve_bvp` notes

- Collocation solver; `fun(x, y)` and `bc(ya, yb)` are vectorized over the
  mesh. Convergence is dominated by the quality of `y_init`.
- `max_nodes` caps mesh refinement; raise it if `sol.status == 1`.
- `sol.status`: 0 converged, 1 max nodes exceeded, 2 singular Jacobian.
- `tol` sets the target residual of the collocation solution.
