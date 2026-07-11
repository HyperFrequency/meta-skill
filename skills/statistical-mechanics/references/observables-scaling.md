# Observables, Phase Transitions & Finite-Size Scaling

Assumes the `IsingModel` + `simulate()` from `algorithms.md`.

## Observable definitions (per spin)

For `N = L²` spins at temperature `T` (units `J/k_B`, `k_B = 1`):

| Observable | Formula | Notes |
|---|---|---|
| Energy | `⟨E⟩/N` | from `H = -J Σ_⟨ij⟩ s_i s_j` |
| Magnetization | `⟨|M|⟩/N` | absolute value on finite lattices |
| Specific heat | `C = N·Var(E_per_spin)/T²` | fluctuation-dissipation |
| Susceptibility | `χ = N·Var(|M|_per_spin)/T` | uses \|M\| fluctuations |
| Binder cumulant | `U₄ = 1 − ⟨M⁴⟩/(3⟨M²⟩²)` | dimensionless; crossing = `T_c` |

**Why `|M|`, not `M`:** by up/down symmetry the signed magnetization averages to
zero on any finite lattice, so `⟨M⟩` is a useless order parameter. `⟨|M|⟩`
tracks the ordered/disordered transition. (The `|M|` choice does bias `χ`
slightly at small `L`; the Binder cumulant avoids that bias and is the cleaner
`T_c` estimator.)

**Fluctuation-dissipation intuition:** `C` and `χ` are variances, so they *peak*
where fluctuations are largest — at the transition. That peak, not the
magnetization curve, is your `T_c` locator on finite lattices.

## Workflow 1 — Locate the transition (temperature sweep)

```python
import numpy as np

T_c_exact = 2 / np.log(1 + np.sqrt(2))   # ≈ 2.269 (Onsager, 2D Ising)

L = 32
temperatures = np.linspace(1.5, 3.5, 30)
sweep = [simulate(L, T, n_equil=2000, n_measure=5000, algorithm="wolff")
         for T in temperatures]

chi = np.array([r["chi"] for r in sweep])
T_c_estimate = temperatures[np.argmax(chi)]     # susceptibility peak
print(f"T_c (exact)   = {T_c_exact:.4f}")
print(f"T_c (peak,L={L}) = {T_c_estimate:.4f}")   # biased high on small L
```

Plot `⟨E⟩/N`, `⟨|M|⟩/N`, `C`, and `χ` vs `T` (use the `matplotlib` skill). You
should see: energy rising smoothly, magnetization collapsing near `T_c`, and
sharp peaks in `C` and `χ` that grow with `L`. The peak location drifts toward
the true `T_c` as `L → ∞` — that drift is the subject of finite-size scaling.

## Workflow 2 — Finite-size scaling & critical exponents

Run the sweep for several `L` and study how the peaks sharpen and shift.

```python
def finite_size_scaling(sizes, temperatures, n_equil=3000, n_measure=10000):
    runs = {}
    for L in sizes:
        runs[L] = [simulate(L, T, n_equil, n_measure, algorithm="wolff")
                   for T in temperatures]
        chi = [r["chi"] for r in runs[L]]
        T_peak = temperatures[int(np.argmax(chi))]
        print(f"L={L:3d}: χ peak at T ≈ {T_peak:.3f}")
    return runs

# sizes = [8, 16, 32, 64]
# T_range = np.linspace(2.0, 2.6, 20)
# runs = finite_size_scaling(sizes, T_range)
```

Two standard ways to extract `T_c` and exponents from `runs`:

1. **Binder crossing.** Plot `U₄(T)` for each `L`; the curves cross at a nearly
   `L`-independent point → `T_c`. Robust and needs no exponent input.
2. **Data collapse.** Finite-size scaling predicts, near `T_c` with `t = (T−T_c)/T_c`:
   - `χ(L,T) = L^{γ/ν} · f_χ( t · L^{1/ν} )`
   - `⟨|M|⟩(L,T) = L^{-β/ν} · f_M( t · L^{1/ν} )`
   - `C(L,T) = L^{α/ν} · f_C( t · L^{1/ν} )`

   Plotting the rescaled quantities against `t·L^{1/ν}` should collapse all `L`
   onto one curve when `T_c` and the exponents are correct. Tune them until the
   collapse is tight (grid search or a collapse-quality objective).

## Exact 2D Ising critical exponents (validation targets)

| Exponent | Symbol | Exact value | Scaling relation |
|---|---|---|---|
| Specific heat | α | 0 (logarithmic) | `C ~ |T − T_c|^{-α}` |
| Order parameter | β | 1/8 | `M ~ (T_c − T)^{β}` |
| Susceptibility | γ | 7/4 | `χ ~ |T − T_c|^{-γ}` |
| Correlation length | ν | 1 | `ξ ~ |T − T_c|^{-ν}` |
| Critical isotherm | δ | 15 | `M ~ H^{1/δ}` at `T = T_c` |

These satisfy the hyperscaling relations `α = 2 − dν` and `γ = β(δ − 1)` in
`d = 2`. Reproducing `β = 1/8` and `γ = 7/4` from a data collapse is the gold
standard for validating a Monte Carlo pipeline.

## Practical notes

- The `α = 0` (log) specific-heat divergence is subtle — the peak grows only as
  `ln L`, so it is easy to miss on small lattices.
- Susceptibility peaks scale as `L^{γ/ν} = L^{7/4}`, so `χ` grows dramatically
  with `L`; use it to check your scaling code is wired correctly.
- Always overlay the exact `T_c ≈ 2.269` line when plotting — a peak far from it
  signals an equilibration or measurement bug, not new physics.
