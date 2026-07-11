---
name: hamiltonian-mechanics
version: 0.1.0
description: >-
  Integrate conservative (energy-preserving) Hamiltonian systems with symplectic
  integrators that preserve phase-space structure and keep energy error bounded over
  exponentially long times — leapfrog / Störmer–Verlet (2nd order), Yoshida & Ruth
  compositions (4th order and higher), operator splitting, N-body gravitational /
  Coulomb dynamics, and phase-space diagnostics (energy-drift checks, Poincaré surfaces
  of section, KAM tori). Also covers the analytic side: Hamilton's equations, Poisson
  brackets, canonical transformations, and action-angle variables. Use for long-time
  orbital or molecular-dynamics integration where RK45 energy drift is unacceptable, or
  to map a system's phase-space structure. NOT for dissipative, driven, or stiff systems,
  nor when you need adaptive error-controlled stepping (use a standard ODE solver /
  `ode-solver`); NOT for discovering invariants from trajectory data
  (use `conservation-law-discovery`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (NumPy, SciPy), Matplotlib (PSF-based)"
---

# Hamiltonian Mechanics

## Overview

Solve Hamilton's equations of motion

```
q̇ =  ∂H/∂p        ṗ = -∂H/∂q
```

with **symplectic integrators** — time-stepping maps that exactly preserve the
symplectic 2-form of phase space. For a conservative system this buys the property that
matters most over long runs: the total energy does not drift secularly. It oscillates
inside a narrow band whose width scales as `dt^order`, no matter how many steps you take.
A non-symplectic method of the *same* order (RK4, RK45) instead lets energy walk away
linearly, so orbits spiral in or out and phase-space structure dissolves.

This skill covers the integrators (leapfrog through 4th-order compositions), the diagnostics
that tell you whether a long run is trustworthy (energy drift, Poincaré sections, KAM tori),
and the analytic machinery (Poisson brackets, canonical transformations, action-angle
variables) used to reason about the system before you integrate.

## When to Use This Skill

- **Conservative** systems — no friction, drag, or driving. The Hamiltonian has no explicit
  time dependence, or you accept adiabatic slow drive.
- **Long-time integration**: thousands of orbits, nanoseconds of molecular dynamics, secular
  celestial-mechanics runs — anywhere `10^5`–`10^9` steps accumulate.
- **N-body** gravitational or Coulomb problems.
- Standard RK45/Radau shows unacceptable **energy drift** over your integration window.
- You are mapping **phase-space structure** — regular vs chaotic regions, KAM tori,
  resonance overlap, Poincaré sections.

## When NOT to Use This Skill

- The system is **dissipative or driven** (friction, radiation reaction, external forcing) —
  energy is *supposed* to change; use an adaptive ODE solver (`ode-solver`, `solve_ivp`).
- The system is **stiff** — symplectic methods here are explicit and CFL-limited; a stiff
  problem forces `dt` so small it is pointless. Use an implicit solver (Radau, BDF).
- You need **adaptive, error-controlled time-stepping** — standard symplectic integrators
  use a *fixed* `dt` (variable steps break symplecticity unless done carefully; see the
  time-transformed leapfrog note in [references/integrators.md](references/integrators.md)).
- You want to **discover** conserved quantities or the equations of motion from data — for
  invariants that is `conservation-law-discovery`; for the dynamics themselves use a
  system-identification method (SINDy, symbolic regression). Not this skill.

## The one idea to keep: bounded, not zero, energy error

A symplectic integrator does not conserve the true `H`. It *exactly* conserves a nearby
"shadow" Hamiltonian `H̃ = H + dt^order·(correction) + …`. Because the numerical trajectory
stays on level sets of `H̃`, the measured `H` stays within `O(dt^order)` of its initial value
forever — it never drifts. This is why leapfrog beats RK4 by orders of magnitude over long
runs even though RK4 is higher order per step. The backward-error argument is in
[references/theory.md](references/theory.md).

## Workflow

### 1. Split the Hamiltonian, then pick an integrator

The explicit integrators below are symplectic **only when `H` is separable**,
`H(q,p) = T(p) + V(q)` (kinetic + potential). Almost all mechanics problems are. If yours is
non-separable (e.g. magnetic vector potential, relativistic), see the extended-phase-space
and implicit options in [references/integrators.md](references/integrators.md) — do **not**
just plug a non-separable `H` into the code below and assume it stays symplectic.

### 2. Leapfrog — the default

Kick–drift–kick Störmer–Verlet: 2nd order, one force evaluation per step, symplectic and
time-reversible. Start here for essentially every problem.

```python
import numpy as np

def leapfrog(force, q0, p0, dt, n_steps, mass=1.0):
    """KDK Störmer–Verlet for separable H = p²/(2m) + V(q).

    `force(q)` returns -dV/dq (= ṗ). Positions and momenta are stored at the
    same integer times; the split half-kick is what keeps the map symplectic.
    """
    q = np.empty((n_steps + 1,) + np.shape(q0))
    p = np.empty_like(q)
    q[0], p[0] = q0, p0
    a = force(q0)                       # carry force across steps: 1 eval/step
    for i in range(n_steps):
        p_half   = p[i] + 0.5 * dt * a
        q[i + 1] = q[i] + dt * p_half / mass
        a        = force(q[i + 1])
        p[i + 1] = p_half + 0.5 * dt * a
    return q, p
```

The general (`∂H/∂q`, `∂H/∂p`) form and a worked Kepler-orbit example with the energy plot
are in [references/integrators.md](references/integrators.md).

### 3. Yoshida 4th order — when 2nd order is not accurate enough

Compose three leapfrog sub-steps with Yoshida's coefficients to cancel the leading error
term: 4th-order accuracy, still symplectic, ~3 force evaluations per step. Reach for it when
leapfrog needs an impractically small `dt` to hit your energy tolerance. Full implementation
(and 6th/8th-order compositions) in [references/integrators.md](references/integrators.md).

### 4. N-body — assemble the forces, reuse one integrator

For N interacting bodies, write a vectorized `acceleration(q)` and drive it with the same KDK
leapfrog. **Soften the potential** (`1/r → 1/√(r²+ε²)`) or close encounters blow up. The
full vectorized N-body loop and the figure-8 three-body test case are in
[references/integrators.md](references/integrators.md).

### 5. Diagnose the run before trusting it

- **Energy drift** — compute `H` along the trajectory; for a good symplectic run
  `max|ΔH/H₀|` is small and *bounded* (oscillates, no trend). A monotone trend means you are
  accidentally using a non-symplectic method or a non-separable `H`.
- **Poincaré surface of section** — collect phase-space points each time a chosen coordinate
  crosses a plane; closed curves are KAM tori (regular motion), scattered clouds are chaos.

Both, plus Lyapunov-exponent and action-variable estimates, are in
[references/diagnostics.md](references/diagnostics.md).

## Choosing an integrator

| Method | Order | Long-run energy | Force evals/step | Use when |
|---|---|---|---|---|
| Euler / RK4 (non-symplectic) | 1 / 4 | **drifts** — never bounded | 1 / 4 | never, for Hamiltonian systems |
| Leapfrog / Störmer–Verlet | 2 | bounded `O(dt²)` | 1 | default |
| Ruth 3rd order | 3 | bounded `O(dt³)` | 3 | rarely — Yoshida4 dominates it |
| Yoshida 4th order | 4 | bounded `O(dt⁴)` | 3 | tight energy tolerance |
| Yoshida 6th/8th order | 6 / 8 | bounded | 7 / 15 | extreme accuracy, smooth forces |

> Note: SciPy's `solve_ivp` ships **no** symplectic integrators — every method it offers is
> non-symplectic and will drift on a long conservative run. Use the code in this skill, or a
> dedicated package, instead.

## Pitfalls

| Symptom | Cause / fix |
|---|---|
| Energy drifts monotonically | Non-symplectic method, or a non-separable `H` in the explicit scheme — switch to leapfrog on a separable split, or an implicit method. |
| Close encounter → NaN / blowup | Unsoftened `1/r` singularity — soften (`1/√(r²+ε²)`) or shrink `dt` locally with a time-transformed leapfrog. |
| Poincaré section looks smeared | `dt` too large — accuracy improves with smaller `dt` even though symplecticity holds at any `dt`; also interpolate crossings, don't snap to samples. |
| "I need an adaptive step" | Fixed-step is inherent to symplecticity; use a time-transformed / regularized leapfrog (Mikkola–Aarseth) — see [references/integrators.md](references/integrators.md). |

## Analytic tools

Before (or instead of) integrating, reason about the system symbolically: Hamilton's
equations from a Lagrangian via the Legendre transform, **Poisson brackets** `{f, g}` to test
whether a quantity is conserved (`{f, H} = 0`) or two observables commute, **canonical
transformations** and generating functions to simplify `H`, and **action-angle variables**
`(J, θ)` for integrable systems. Definitions, a SymPy Poisson-bracket helper, and the
action-integral recipe are in [references/theory.md](references/theory.md). To find invariants
numerically from trajectories instead, use `conservation-law-discovery`.

## References

- [references/integrators.md](references/integrators.md) — general leapfrog, worked Kepler
  example, Yoshida 4th/6th/8th order, operator-splitting theory, separable vs non-separable
  `H`, force softening, the full vectorized N-body loop with the figure-8 test, and
  time-transformed / adaptive leapfrog.
- [references/diagnostics.md](references/diagnostics.md) — energy-drift measurement and plot,
  the full Poincaré surface-of-section routine (with crossing interpolation), reading tori
  vs chaos, Lyapunov-exponent estimation, and numerical action variables.
- [references/theory.md](references/theory.md) — Hamilton's equations and the Legendre
  transform, Poisson brackets (with SymPy), canonical transformations and generating
  functions, the symplectic 2-form, backward-error / shadow-Hamiltonian explanation of bounded
  energy error, action-angle variables, and the KAM theorem with the Chirikov resonance-overlap
  criterion.
