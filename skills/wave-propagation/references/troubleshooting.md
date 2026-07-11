# Troubleshooting

Symptom → cause → fix for the failures that actually occur in FDTD/spectral wave
runs.

| Symptom                                        | Cause                                                                 | Fix                                                                                          |
| ---------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Field values → `inf`/`nan` within a few steps  | **CFL violated** — `dt` too large for `dx` and `c_max`                | Reduce `dt` below the CFL bound (`c·dt/dx ≤ 1, 1/√2, 1/√3` in 1/2/3D); use `c_max`, not mean `c` |
| Slow blow-up over many steps                    | CFL marginally satisfied, or an unstable boundary/PML term            | Drop the Courant number to ~0.9× the bound; check the boundary update and `σ_max`            |
| Wave reflects off the domain edge               | Reflecting boundary where you wanted an open one, or weak absorber     | Use Mur (1D) or a PML (2D/3D); thicken the layer; verify with the energy decay check         |
| Reflection only at oblique angles (2D/3D)       | First-order Mur reflects off-normal waves                             | Switch to a PML or second-order Mur; enlarge the domain so wavefronts hit near-normal        |
| Wave travels at the wrong (too slow) speed      | **Numerical dispersion** — too few points per wavelength              | Refine `dx` to ≥10–20 points/λ_min (`λ_min = c_min/f_max`); or use a higher-order/spectral scheme |
| High-frequency ripples trailing the pulse       | Sharp/impulsive source excites unresolved high-`k` modes             | Use a smooth band-limited wavelet (Ricker/Gaussian); lower the source peak frequency          |
| Gibbs ringing across the whole domain (spectral)| Field is **not periodic** — FFT wrap-around aliasing                 | Enforce periodicity, add a sponge/damping zone, or window the field near the edges            |
| Nonzero jolt at `t=0`                            | Source wavelet not ~0 at `t=0` — injects a step                     | Shift the wavelet center `t0` (≈`1/f` Ricker, `3–4σ` Gaussian) so it starts near zero         |
| Energy grows in a closed lossless domain        | CFL violation or an inconsistent boundary corner                    | Re-check CFL; apply the boundary consistently at corners; run the energy diagnostic           |
| Interface reflects "too much"                    | This is real physics, not a bug — impedance contrast reflects       | Compare against `(c2-c1)/(c2+c1)`; if truly spurious, resolve the interface over more cells    |
| 3D run exhausts memory                           | Three `N³` float64 grids cost `24·N³` bytes                          | Use `float32`, shrink `N`, or move to `cupy`/`jax` on GPU; the CFL/physics are unchanged       |
| Result changes when you change only `dx`         | Under-resolution — solution not yet converged                       | Halve `dx` (rescale `dt` accordingly) and confirm the result stops changing (grid convergence) |

## Quick diagnostic checklist

1. **Print the Courant number** `c_max·dt/dx` at startup and confirm it is below
   the dimensional bound. This catches most blow-ups instantly.
2. **Print points per wavelength** `λ_min/dx = c_min/(f_max·dx)`; want ≥10.
3. **Run the energy diagnostic** (see `fdtd-solvers.md`) — the single most
   informative check: conserved (lossless) or monotonically decaying (absorbing);
   anything else is a bug.
4. **Grid-convergence test**: rerun at half `dx` (and the matching `dt`); a
   converged solution barely moves. If it moves a lot, you were under-resolved.
