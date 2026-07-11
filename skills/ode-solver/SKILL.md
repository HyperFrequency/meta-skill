---
name: ode-solver
version: 0.1.0
description: >-
  Integrate systems of ordinary differential equations with SciPy — initial
  value problems (IVP), boundary value problems (BVP), stiff and non-stiff
  systems, event/root detection during a run, energy-conserving symplectic
  integration for Hamiltonian dynamics, parameter sweeps, and phase-space
  analysis. Use when you have a well-posed ODE dx/dt = f(t, x) (physics,
  engineering, dynamical systems, chemical kinetics, control) and need to
  integrate it, choose the right solver, tune tolerances, or catch events.
  Do NOT use for PDEs with spatial derivatives, for fitting ODE parameters to
  measured data, or for discovering the governing equations from data — do
  those elsewhere and integrate the resulting system here.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (SciPy / NumPy)"
---

# ODE Solver

## Overview

Integrate ordinary differential equations using SciPy's `scipy.integrate`
solvers. This skill routes you through the four decisions that determine
whether an ODE integration is correct and cheap: **which solver** (stiff vs
non-stiff), **which tolerances** (`rtol`/`atol`/`max_step`), **how to catch
events** (roots of a state function), and **how to preserve invariants** (a
symplectic integrator for Hamiltonian systems). Everything wraps
`solve_ivp`, `solve_bvp`, and a hand-rolled leapfrog stepper.

The body below is a router. Runnable end-to-end recipes, the full method
table, tuning semantics, and troubleshooting live in `references/`.

## When to Use This Skill

- An initial value problem: `dy/dt = f(t, y)` with a known state at `t0`.
- A two-point boundary value problem: constraints at both endpoints.
- A stiff system (chemical kinetics, RC circuits, reaction networks) where an
  explicit solver stalls.
- Systems with discrete events: bounce, threshold crossing, apex, switching
  dynamics — where you need the exact time/state at the crossing.
- Hamiltonian / conservative systems that must conserve energy over long
  integrations (orbital mechanics, molecular dynamics, pendulums).
- Sweeping a parameter across an ODE family and comparing trajectories.

## When NOT to Use This Skill

- **PDEs** (derivatives in space and time — heat, wave, Navier–Stokes). Use a
  PDE approach such as `autoregressive-neural-pde-solver`, or method-of-lines
  discretization before returning here.
- **Fitting ODE parameters to data.** Estimate parameters with
  `bayesian-inference` / `pymc` (or a least-squares fit), then integrate the
  fitted system here.
- **Discovering the governing equations from data.** Use
  `conservation-law-discovery` (SINDy / symbolic regression) first.
- **Discrete-event / agent simulations** with no continuous dynamics — use
  `simpy`.

## Core Capabilities

Each capability names the exact API and key parameters. Copy-paste code for
all of them is in `references/recipes.md`.

### Initial value problems

`scipy.integrate.solve_ivp(fun, t_span, y0, method='RK45', t_eval=..., rtol=,
atol=, events=, dense_output=)`. `fun(t, y)` returns `dy/dt` as a length-`n`
array; `y0` is the initial state. Read results from `sol.t`, `sol.y`
(shape `(n, len(sol.t))`), `sol.success`, `sol.message`. Set `t_eval` for the
output grid you want (it does not change the internal steps). See
`references/recipes.md` (Recipe 1).

### Stiff systems

Switch to an implicit solver: `method='Radau'` (implicit Runge–Kutta) or
`method='BDF'` (multistep) — or `method='LSODA'` to auto-detect. Signs of
stiffness: an explicit run takes enormous step counts or fails, the system
has widely separated timescales, or the Jacobian has large-magnitude negative
eigenvalues. Passing an analytic `jac=` speeds `Radau`/`BDF` substantially.
Detection heuristics and the full method table are in
`references/methods-and-tuning.md`.

### Event / root detection

Pass `events=` a callable (or list) `g(t, y)`; the solver locates each sign
change of `g`. Set `g.terminal = True` to stop at the first hit and
`g.direction = +1/-1` to select crossing direction. Times and states land in
`sol.t_events` / `sol.y_events`. Keep `max_step` below the event's timescale
so a fast crossing is not stepped over. Recipe 3 in `references/recipes.md`.

### Hamiltonian / symplectic integration

For long-time energy conservation, do **not** use `solve_ivp` — non-symplectic
solvers drift in energy. Use the leapfrog (Störmer–Verlet) stepper: half-kick
momentum, full-drift position, half-kick momentum. It is 2nd-order and
conserves a shadow Hamiltonian. Full implementation (with a Kepler-orbit
example) is Recipe 4 in `references/recipes.md`. For symbolic derivation of
`∂H/∂q`, `∂H/∂p`, use `sympy`.

### Boundary value problems

`scipy.integrate.solve_bvp(fun, bc, x, y_init)`, where `fun(x, y)` returns a
`(n, m)` stack of derivatives, `bc(ya, yb)` returns the residuals of the
boundary conditions, and `y_init` is an initial guess on mesh `x`. Convergence
depends heavily on the guess. Recipe 5.

### Parameter sweeps & phase space

Bind parameters with `functools.partial(fun, param=value)` and loop
`solve_ivp` over the values; overlay `sol.y[0]` vs `sol.t`, or plot `sol.y[0]`
vs `sol.y[1]` for a phase portrait. Recipe 6. Plot with `matplotlib`.

## Method Selection (quick reference)

| Method | Class | Use when |
|---|---|---|
| `RK45` | non-stiff | default general-purpose choice |
| `DOP853` | non-stiff, high order | long/reference integrations needing tight accuracy |
| `Radau` / `BDF` | stiff (implicit) | explicit solver stalls; separated timescales |
| `LSODA` | auto stiff/non-stiff | stiffness unknown |
| leapfrog / Verlet | symplectic | Hamiltonian systems, long-time energy conservation |

Full table (including `RK23`), tolerance semantics (`rtol` vs `atol`,
`max_step`, `first_step`), and `dense_output` guidance:
`references/methods-and-tuning.md`.

## Validate Before You Trust a Solution

Never report an integration without a convergence check. Minimum bar:
`sol.success is True`, the solution is unchanged when you halve `max_step` (or
tighten `rtol`/`atol`), and — for conservative systems — the invariant
(energy, momentum, `sindy`-found quantity) holds to tolerance. Full checklist
and a symptom→cause→fix troubleshooting table are in
`references/validation-and-troubleshooting.md`.

## References

- `references/recipes.md` — runnable code for all six capabilities.
- `references/methods-and-tuning.md` — full method table, tolerance and step
  control, Jacobians, stiffness detection.
- `references/validation-and-troubleshooting.md` — validation checklist and
  troubleshooting table.

## Related Skills

- `sympy` — derive Jacobians, `∂H/∂q`, and analytic reference solutions.
- `conservation-law-discovery` — recover governing equations before integrating.
- `bayesian-inference` / `pymc` — fit ODE parameters to data.
- `autoregressive-neural-pde-solver` — spatial-derivative (PDE) problems.
- `dimensional-analysis` — nondimensionalize a system before integrating.
- `matplotlib` — trajectory and phase-portrait plots.
