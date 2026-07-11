---
name: statistical-mechanics
version: 0.1.0
description: >-
  Monte Carlo simulation of classical equilibrium statistical-mechanics spin
  models (Ising, Potts, XY, Heisenberg) with the Metropolis-Hastings and Wolff
  cluster algorithms. Measures thermodynamic observables (energy, magnetization,
  specific heat, susceptibility, Binder cumulant), locates critical
  temperatures, and runs finite-size scaling to extract critical exponents. Use
  when you need to simulate a lattice spin system at thermal equilibrium, map a
  phase diagram, study a continuous phase transition, or estimate critical
  exponents from first principles. NOT for quantum/path-integral Monte Carlo,
  molecular dynamics or continuous-particle systems, off-lattice models,
  non-equilibrium or driven dynamics, or when a closed-form/mean-field answer
  already settles the question — this covers classical, equilibrium, lattice
  spin Monte Carlo only.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Statistical Mechanics (Monte Carlo)

## Overview

Sample the equilibrium (Boltzmann) distribution of a classical lattice spin
model with Markov-chain Monte Carlo, then estimate thermodynamic observables as
ensemble averages. The canonical target is the 2D Ising model, whose exact
Onsager solution (`T_c = 2/ln(1+√2) ≈ 2.269 J/k_B`) makes it the standard
proving ground, but the same machinery drives Potts, XY, and Heisenberg models.
Two update algorithms cover most needs: single-spin **Metropolis-Hastings** for
generality, and the **Wolff cluster** algorithm to beat critical slowing down
near a continuous phase transition.

Everything here is plain NumPy — no external simulation engine. Deep code,
formulas, and diagnostics live in `references/`; this file is the router.

## When to Use This Skill

- Simulating a lattice spin model (Ising, Potts, XY, Heisenberg) at thermal equilibrium.
- Locating a critical temperature `T_c` from a susceptibility or specific-heat peak.
- Computing thermodynamic observables: energy, magnetization, specific heat, susceptibility, Binder cumulant.
- Mapping a temperature (or field) sweep into a phase diagram.
- Running finite-size scaling across several lattice sizes `L` to extract critical exponents.
- Teaching or validating a Monte Carlo pipeline against an exactly solved model.

## When NOT to Use This Skill

- **Quantum systems** needing path-integral or determinantal QMC — this is classical Monte Carlo only.
- **Continuous-particle / off-lattice** systems (Lennard-Jones fluids, biomolecules) — use molecular dynamics or continuous MC, not spin updates.
- **Non-equilibrium / driven** dynamics (Kawasaki drive, quenches, aging) — the algorithms here assume detailed balance toward equilibrium.
- **Real-time quantum dynamics** or open-system evolution.
- When a **mean-field or closed-form** result already answers the question — don't spin up a simulation for a mean-field estimate.
- Pure data plotting or curve fitting with no sampling — use `matplotlib` / `scientific-visualization` directly.

## Mental Model

1. **Boltzmann weight.** Configurations occur with probability `∝ exp(-βH)`, `β = 1/(k_B T)`. You never enumerate states; you sample them.
2. **Importance sampling.** A Markov chain that satisfies detailed balance visits configurations with the right frequency, so a simple average over chain samples estimates `⟨O⟩`.
3. **Equilibrate, then measure.** Discard an initial burn-in (equilibration) window, then collect samples. Do not measure during burn-in.
4. **Autocorrelation is the enemy.** Successive samples are correlated. Naive `std/√N` error bars are too optimistic; correct with the integrated autocorrelation time `τ` (see `references/error-analysis.md`).

## Choosing an Algorithm

| Situation | Algorithm | Why |
|---|---|---|
| General model, away from `T_c`, arbitrary interactions/fields | **Metropolis-Hastings** | Simple, always applicable; one sweep = `L²` flip attempts |
| Near a continuous transition (`T ≈ T_c`) | **Wolff cluster** | Flips whole correlated clusters; largely removes critical slowing down (dynamic exponent `z` drops from ~2 to ~0) |
| External field, or models where clusters are ill-defined | **Metropolis** | Cluster construction assumes zero/simple field and specific symmetry |
| Ising/Potts at criticality, large `L` | **Wolff** (or Swendsen-Wang) | Decorrelates orders of magnitude faster |

Rule of thumb: prototype with Metropolis, switch to Wolff the moment you work
near `T_c` or see runaway equilibration times. Full implementations of both are
in `references/algorithms.md`.

## Quickstart

The reference implementation exposes an `IsingModel` class and a `simulate(...)`
driver (both in `references/algorithms.md`). Typical use:

```python
# See references/algorithms.md for the full IsingModel + simulate definitions.
result = simulate(L=32, T=2.4, n_equil=2000, n_measure=5000, algorithm="wolff")
print(result["E_mean"], result["M_mean"], result["C"], result["chi"])
```

`result` carries energy and |magnetization| per spin (with jackknife-style
errors), specific heat `C`, susceptibility `chi`, and the final spin
configuration.

## Observables (per spin)

- **Energy** `⟨E⟩/N` from `H = -J Σ_⟨ij⟩ s_i s_j`.
- **Magnetization** `⟨|M|⟩/N` — always take the absolute value on finite lattices; unsigned `M` fluctuates around 0 by symmetry.
- **Specific heat** `C = N·Var(E_per_spin)/T²` (fluctuation-dissipation).
- **Susceptibility** `χ = N·Var(|M|_per_spin)/T`.
- **Binder cumulant** `U = 1 − ⟨M⁴⟩/(3⟨M²⟩²)` — its size-independent crossing pinpoints `T_c` cleanly.

Derivations, exact code, and the temperature-sweep + finite-size-scaling
workflows are in `references/observables-scaling.md`.

## Core Workflows

- **Locate a phase transition** → temperature sweep, find the susceptibility/specific-heat peak, compare to the exact `T_c`. See `references/observables-scaling.md`.
- **Extract critical exponents** → finite-size scaling across `L ∈ {8,16,32,64}`, data collapse against the exact 2D Ising exponents (`β=1/8, γ=7/4, ν=1`). See `references/observables-scaling.md`.
- **Trust your error bars** → measure the integrated autocorrelation time, thin or block your samples, verify equilibration. See `references/error-analysis.md`.

## References

- `references/algorithms.md` — full `IsingModel` class, Metropolis + Wolff updates, the `simulate()` driver, and notes on extending to Potts/XY/Heisenberg.
- `references/observables-scaling.md` — observable formulas and code, temperature-sweep phase-transition workflow, finite-size scaling, and the exact 2D Ising critical-exponent table.
- `references/error-analysis.md` — integrated autocorrelation time, correct error estimation, equilibration diagnostics, and a troubleshooting table.

## Related Skills

- `matplotlib` / `scientific-visualization` — plot sweeps, collapses, and spin snapshots.
- `statistical-analysis` — bootstrap/jackknife resampling and hypothesis testing on the resulting estimates.
- `pymc` — Bayesian sampling when you need posterior inference rather than physical equilibrium ensembles.
