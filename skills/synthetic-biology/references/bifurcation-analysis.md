# Bifurcation Analysis

Locate where a gene circuit changes qualitative behavior as one parameter is
varied — in particular the saddle-node points where a bistable toggle collapses
to (or emerges from) monostability. The method is a numerical parameter sweep:
at each parameter value, integrate to steady state from many initial conditions
and count the distinct attractors. For the inducible circuit the same machinery
produces a dose-response curve and EC50.

Uses the circuit ODEs from `gene-circuits.md`, plus SciPy, NumPy, and pandas.

## Convergence-checked steady-state finder

Long-time integration to steady state, verifying the derivative has actually
vanished; if not, integrate longer before accepting the point.

```python
import numpy as np
from scipy.integrate import solve_ivp

def find_steady_state(ode_func, y0, params, t_max=5000.0):
    sol = solve_ivp(ode_func, (0, t_max), y0, args=(params,), method="RK45",
                    rtol=1e-9, atol=1e-11, max_step=t_max / 200)
    if not sol.success:
        return None
    final = sol.y[:, -1]
    if max(abs(d) for d in ode_func(t_max, final, params)) > 1e-4:   # not settled
        sol2 = solve_ivp(ode_func, (0, t_max * 5), final.tolist(), args=(params,),
                         method="RK45", rtol=1e-10, atol=1e-12, max_step=t_max / 100)
        if sol2.success:
            final = sol2.y[:, -1]
    return final
```

## Finding all steady states (toggle)

A bistable system has two stable attractors, so a single start finds only one.
Probe with **biased** initial conditions (gene-1-high, gene-2-high, symmetric,
low) plus random starts, then deduplicate within a tolerance. Seed the RNG for
reproducibility.

```python
def find_all_steady_states_toggle(params, n_trials=30):
    rng = np.random.RandomState(42)
    seeds = [[10, .1, 10, .1], [.1, 10, .1, 10], [5, 5, 5, 5], [.1, .1, .1, .1]]
    seeds += [rng.uniform(0, 15, 4).tolist() for _ in range(n_trials - len(seeds))]
    found = []
    for y0 in seeds:
        r = find_steady_state(toggle_switch_odes, y0, params)
        if r is None or r[2] < -0.01 or r[3] < -0.01:
            continue
        p1, p2 = max(0, float(r[2])), max(0, float(r[3]))
        if not any(abs(p1-a) < 0.05 and abs(p2-b) < 0.05 for a, b in found):
            found.append((p1, p2))
    return sorted(found, key=lambda x: x[0])
```

Two entries ⇒ bistable; one ⇒ monostable. Tighten the dedup tolerance (0.05) if
attractors are close; raise `n_trials` if you suspect a missed basin.

## Parameter sweep and aliases

Sweep with `np.linspace(lo, hi, steps)`. Support convenient **aliases** so a
single canonical name updates the symmetric pair:

```python
TOGGLE_ALIASES    = {"alpha": ["alpha1", "alpha2"], "n": ["n1", "n2"], "K": ["K1", "K2"]}
INDUCIBLE_ALIASES = {"alpha": ["alpha_max"], "K": ["K_ind"]}

def sweep_toggle(base, param, lo, hi, steps):
    names = TOGGLE_ALIASES.get(param, [param])
    rows = []
    for val in np.linspace(lo, hi, steps):
        params = {**base, **{nm: val for nm in names}}
        ss = find_all_steady_states_toggle(params, n_trials=20)
        if not ss:
            rows.append({"param_value": val, "p1_ss": np.nan, "p2_ss": np.nan,
                         "state_index": 0, "n_states": 0})
        else:
            rows += [{"param_value": val, "p1_ss": a, "p2_ss": b,
                      "state_index": i, "n_states": len(ss)} for i, (a, b) in enumerate(ss)]
    return rows
```

The inducible sweep is monostable, so it records a single `(m_ss, p_ss)` per
value — a dose-response curve when swept over `inducer`.

## Detecting bifurcation points

A saddle-node bifurcation sits between two consecutive parameter values whose
steady-state **count** differs. Report the midpoint and direction:

```python
def detect_bifurcations(rows):
    n_by_val = {}
    for r in rows:                                    # first n_states seen per value
        n_by_val.setdefault(r["param_value"], r["n_states"])
    vals = sorted(n_by_val)
    out = []
    for i in range(1, len(vals)):
        prev, cur = n_by_val[vals[i-1]], n_by_val[vals[i]]
        if prev != cur and prev > 0 and cur > 0:
            mid = (vals[i-1] + vals[i]) / 2
            kind = f"monostable -> {cur} states" if cur > prev else f"{prev} states -> monostable"
            out.append((mid, f"saddle-node ({kind})"))
    return out
```

Resolution of the bifurcation location is limited by the sweep step — increase
`steps` near a detected transition to pin it down.

## Inducible readouts: dynamic range & EC50

```python
import pandas as pd
df = pd.DataFrame(inducible_rows).dropna(subset=["p_ss"])
p_min, p_max = df["p_ss"].min(), df["p_ss"].max()
dynamic_range = p_max / p_min if p_min > 1e-10 else float("inf")
p_half = (p_max + p_min) / 2
ec50 = float(df.loc[(df["p_ss"] - p_half).abs().idxmin(), "param_value"])
```

`EC50` is the inducer concentration at half-maximal response; `dynamic_range` is
the fold span from basal to saturated — both are the key handles for tuning an
inducible system.

## Notes & limits

- This is a **numerical continuation by brute-force sweep**, not formal
  bifurcation continuation (no AUTO/pseudo-arclength). It finds *stable* branches
  only; unstable saddle branches between the two stable states are not traced.
- Because stability is inferred from "the integrator settles here", weakly
  unstable states can masquerade as stable — corroborate with a Jacobian
  eigenvalue check at the reported fixed points if it matters.
- Cost scales as `steps × n_trials × integration`; start coarse, then refine
  around transitions.
- Persist results to CSV (`param_value`, `p*_ss`, `state_index`, `n_states`) so
  a diagram can be plotted separately — hand plotting to `matplotlib`.
