# Population & Community Dynamics Simulation

Deterministic ODE systems and exact stochastic simulation for microbial
populations. Deterministic models (`scipy.integrate.solve_ivp`) are appropriate
for large populations; the Gillespie SSA is appropriate when molecule/individual
counts are small and demographic noise matters.

## Generalized Lotka-Volterra (n species)

`dN_i/dt = r_i * N_i * (1 - (sum_j alpha_ij * N_j) / K_i)`, where `alpha_ij` is
the per-capita effect of species `j` on species `i` (diagonal typically 1.0 for
self-limitation).

```python
import numpy as np
from scipy.integrate import solve_ivp

def lotka_volterra(t, N, r, K, alpha):
    """Vectorized generalized LV. alpha[i,j] = effect of j on i."""
    return r * N * (1 - (alpha @ N) / K)

r = np.array([0.5, 0.4, 0.3])
K = np.array([1000, 800, 600])
alpha = np.array([
    [1.0, 0.5, 0.1],   # species 1: self-limitation + competition from 2, 3
    [0.3, 1.0, 0.4],
    [0.2, 0.6, 1.0],
])
sol = solve_ivp(lotka_volterra, [0, 200], [10, 10, 10], args=(r, K, alpha),
                t_eval=np.linspace(0, 200, 1000), method='RK45')
print("final:", sol.y[:, -1].round(1))
```

Interaction-matrix sign conventions (with positive `alpha`, larger `alpha_ij`
means stronger suppression of `i` by `j`): competition = both off-diagonals
positive; mutualism = model with negative off-diagonal `alpha` (a `-` term
raises the effective carrying capacity); predation = asymmetric signs.

### Local stability of a coexistence equilibrium

Evaluate the Jacobian at the interior equilibrium and check that all eigenvalues
have negative real part. A quick surrogate on the community matrix:

```python
A = np.diag(1 / K) @ alpha
eig = np.linalg.eigvals(A)
print("stable" if np.all(eig.real > 0) else "unstable")
```

For a rigorous answer, compute the equilibrium `N*` (solve `alpha @ N = K`) and
the Jacobian `J_ij = ∂(dN_i/dt)/∂N_j` at `N*`, then require `max Re(eig(J)) < 0`.

## Simplified anaerobic digestion (ADM1-lite)

Five-state biogas model: substrate `S`, acidogen biomass `Xa`, methanogen
biomass `Xm`, volatile fatty acids `VFA`, cumulative methane `CH4`. Hydrolysis
is first-order; growth follows Monod kinetics; methanogenesis is inhibited by
VFA accumulation.

```python
def adm1_simplified(t, y, params):
    S, Xa, Xm, VFA, CH4 = y
    p = params
    r_hyd  = p['k_hyd'] * S
    r_acid = p['mu_a'] * (S   / (p['Ks_a'] + S))   * Xa
    inhib  = p['Ki'] / (p['Ki'] + VFA)             # non-competitive VFA inhibition
    r_meth = p['mu_m'] * (VFA / (p['Ks_m'] + VFA)) * Xm * inhib
    return [
        -r_hyd - r_acid / p['Y_a'],                # dS
        p['Y_a'] * r_acid - p['kd'] * Xa,          # dXa
        p['Y_m'] * r_meth - p['kd'] * Xm,          # dXm
        r_acid - r_meth / p['Y_m'],                # dVFA
        r_meth,                                     # dCH4
    ]

params = {'k_hyd': 0.25, 'mu_a': 0.5, 'Ks_a': 200, 'mu_m': 0.2, 'Ks_m': 50,
          'Y_a': 0.1, 'Y_m': 0.05, 'kd': 0.02, 'Ki': 3000}
sol = solve_ivp(adm1_simplified, [0, 60], [5000, 100, 50, 100, 0],
                args=(params,), t_eval=np.linspace(0, 60, 300), method='RK45')
print(f"CH4 produced: {sol.y[4, -1]:.0f} mg/L")
```

This is a teaching-scale reduction, not the full 24-state IWA ADM1. Use it for
qualitative yield trends and inhibition behavior, not regulatory-grade design.

## Gillespie Stochastic Simulation Algorithm (exact SSA)

Simulates a well-mixed reaction network exactly: at each step, draw the waiting
time to the next reaction from an exponential with rate = total propensity, then
choose which reaction fires proportional to its propensity.

```python
import numpy as np

def gillespie_ssa(propensity_func, stoich_matrix, x0, t_end, max_steps=100000):
    """Exact SSA.
    propensity_func(x) -> 1D array of reaction rates.
    stoich_matrix[reaction] -> integer state-change vector.
    Returns (times, states) as arrays.
    """
    t = 0.0
    x = np.array(x0, dtype=float)
    times, states = [t], [x.copy()]
    for _ in range(max_steps):
        props = propensity_func(x)
        total = props.sum()
        if total <= 0 or t >= t_end:
            break
        t += np.random.exponential(1 / total)          # time to next reaction
        if t > t_end:
            break
        reaction = np.searchsorted(np.cumsum(props), np.random.uniform(0, total))
        reaction = min(reaction, len(props) - 1)         # guard float rounding
        x = np.clip(x + stoich_matrix[reaction], 0, None)
        times.append(t); states.append(x.copy())
    return np.array(times), np.array(states)
```

### Example: density-dependent birth-death-immigration

```python
def propensities(x):
    N = x[0]
    return np.array([0.5 * N,               # birth
                     0.01 * N * (N - 1),     # density-dependent death
                     5.0])                   # immigration
stoich = np.array([[1], [-1], [1]])

finals = []
for _ in range(200):                         # ensemble
    _, states = gillespie_ssa(propensities, stoich, [10], t_end=50)
    finals.append(states[-1, 0])
print(f"mean final N = {np.mean(finals):.1f} +/- {np.std(finals):.1f}")
```

### Scaling and approximations

- **Ensemble size** — run >100 (ideally >1000) trajectories before trusting
  means, variances, or extinction probabilities. One trajectory is a sample, not
  a result.
- **Large populations (>~10^4)** — exact SSA becomes slow because step size
  shrinks with total propensity. Switch to **tau-leaping** (fire many reactions
  per fixed `tau` using Poisson draws) or a **mean-field ODE + analytic noise**
  (Langevin / linear-noise) approximation.
- **Stiff / disparate timescales** — the SSA handles stiffness naturally but
  spends most steps on the fast reactions; consider slow-scale SSA if a few fast
  reactions dominate.

## ODE solver selection

- `method='RK45'` (default) — non-stiff systems; most growth/community models.
- `method='BDF'` or `'Radau'` — stiff systems (widely separated rates, e.g.
  digestion or tightly coupled multi-species models) that integrate slowly or
  oscillate numerically.
- Use `events=` to stop or record when a population crosses zero, and `dense_output=True`
  for a continuous interpolant.
- If populations go negative, reduce tolerances (`rtol`, `atol`) or add an
  extinction event that clamps at zero — negative populations are a numerical
  artifact, not a model prediction.

## Reference

- Gillespie (2007), *Annu. Rev. Phys. Chem.* 58:35-55,
  doi:10.1146/annurev.physchem.58.032806.104637.
- Batstone et al. (2002), IWA Anaerobic Digestion Model No. 1 (ADM1) — the full
  model this section reduces.
- `scipy.integrate.solve_ivp` documentation.
