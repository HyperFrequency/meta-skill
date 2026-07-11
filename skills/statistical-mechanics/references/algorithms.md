# Algorithms: Metropolis & Wolff for the Ising Model

Reference implementation in plain NumPy. Periodic boundary conditions, coupling
`J > 0` (ferromagnetic), temperature in units of `J/k_B`.

## The model

Hamiltonian on a square lattice:

```
H = -J Σ_⟨ij⟩ s_i s_j ,   s_i ∈ {-1, +1}
```

`⟨ij⟩` runs over nearest-neighbor pairs. `β = 1/T` (with `k_B = 1`). Each
Metropolis **sweep** attempts `L²` single-spin flips; a Wolff **step** builds and
flips one cluster.

## IsingModel + simulate

```python
import numpy as np


class IsingModel:
    """2D Ising model on an L×L torus (periodic boundaries)."""

    def __init__(self, L, T, J=1.0, rng=None):
        self.L = L
        self.T = T
        self.J = J
        self.beta = 1.0 / T
        self.rng = rng or np.random.default_rng()
        self.spins = self.rng.choice([-1, 1], size=(L, L))

    def energy(self):
        """Total energy H = -J Σ_⟨ij⟩ s_i s_j (each bond counted once)."""
        s = self.spins
        # np.roll shifts by one site; summing over axis 0 and axis 1 counts
        # each of the two bond directions exactly once per site.
        return -self.J * np.sum(s * np.roll(s, 1, axis=0) +
                                s * np.roll(s, 1, axis=1))

    def magnetization(self):
        """Net (signed) magnetization Σ s_i."""
        return np.sum(self.spins)

    def metropolis_sweep(self):
        """One sweep = L² single-spin flip attempts with the Metropolis rule."""
        L = self.L
        for _ in range(L * L):
            i, j = self.rng.integers(0, L, size=2)
            s = self.spins[i, j]
            neighbor_sum = (self.spins[(i + 1) % L, j] + self.spins[(i - 1) % L, j] +
                            self.spins[i, (j + 1) % L] + self.spins[i, (j - 1) % L])
            delta_energy = 2 * self.J * s * neighbor_sum
            if delta_energy <= 0 or self.rng.random() < np.exp(-self.beta * delta_energy):
                self.spins[i, j] = -s

    def wolff_step(self):
        """One Wolff cluster flip. Fast near T_c (no critical slowing down)."""
        L = self.L
        p_add = 1.0 - np.exp(-2.0 * self.beta * self.J)  # bond activation prob

        seed = tuple(self.rng.integers(0, L, size=2))
        cluster_spin = self.spins[seed]
        cluster = {seed}
        stack = [seed]

        while stack:
            ci, cj = stack.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbor = ((ci + di) % L, (cj + dj) % L)
                if (neighbor not in cluster and
                        self.spins[neighbor] == cluster_spin and
                        self.rng.random() < p_add):
                    cluster.add(neighbor)
                    stack.append(neighbor)

        for site in cluster:
            self.spins[site] = -self.spins[site]


def simulate(L, T, n_equil=1000, n_measure=5000, algorithm="metropolis", rng=None):
    """Equilibrate, then measure. Returns per-spin observables + errors.

    Note: the reported *_std values are naive standard errors and IGNORE
    autocorrelation between samples — they underestimate the true error near
    T_c. Correct them with the integrated autocorrelation time; see
    error-analysis.md.
    """
    model = IsingModel(L, T, rng=rng)
    step = model.wolff_step if algorithm == "wolff" else model.metropolis_sweep
    N = L * L

    for _ in range(n_equil):          # burn-in — do NOT measure here
        step()

    energy_samples = np.empty(n_measure)
    mag_samples = np.empty(n_measure)
    for k in range(n_measure):
        step()
        energy_samples[k] = model.energy() / N
        mag_samples[k] = abs(model.magnetization()) / N

    return {
        "E_mean": energy_samples.mean(),
        "E_std": energy_samples.std() / np.sqrt(n_measure),
        "M_mean": mag_samples.mean(),
        "M_std": mag_samples.std() / np.sqrt(n_measure),
        "C": N * energy_samples.var() / T ** 2,   # specific heat per spin
        "chi": N * mag_samples.var() / T,          # susceptibility per spin
        "M2": (mag_samples ** 2).mean(),           # for the Binder cumulant
        "M4": (mag_samples ** 4).mean(),
        "spins": model.spins.copy(),
    }
```

## Why the update rules are correct

- **Metropolis acceptance** `min(1, exp(-βΔE))` satisfies detailed balance with
  the Boltzmann distribution; the local energy change for flipping one spin is
  `ΔE = 2 J s_i · (sum of its 4 neighbors)`.
- **Wolff bond probability** `p_add = 1 - exp(-2βJ)` is the value that makes the
  cluster move exactly satisfy detailed balance for Ising; every accepted
  cluster is flipped unconditionally (acceptance = 1). This is why Wolff avoids
  the vanishing acceptance / long autocorrelation that plagues Metropolis at
  criticality.

## Sweeps vs steps — comparing costs

A Metropolis sweep touches `L²` spins; a Wolff step touches one cluster whose
size grows toward `L²` near `T_c`. When comparing autocorrelation or wall-clock
between algorithms, compare *per unit of computational work*, not per "step" —
a Wolff step near criticality does far more decorrelation than one Metropolis
sweep.

## Extending to other models (capability notes)

These are the standard generalizations; implement the specifics for your model
rather than assuming a drop-in API:

- **q-state Potts:** spins take `q` values; `H = -J Σ δ(s_i, s_j)`. Metropolis
  proposes a new random state; the Wolff/Swendsen-Wang bond probability becomes
  `1 - exp(-βJ)` between equal-valued neighbors.
- **XY / Heisenberg (continuous spins):** spins are unit vectors (`O(2)`/`O(3)`).
  Metropolis proposes a small random rotation; Wolff reflects spins about a
  random hyperplane with bond probability depending on the projected coupling.
  These have no spontaneous magnetization in 2D for `O(n≥2)` (Mermin-Wagner);
  the 2D XY model instead shows a Kosterlitz-Thouless transition.

Keep the same equilibrate-then-measure discipline and autocorrelation analysis
regardless of model.
