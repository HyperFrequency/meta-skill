# Diagnostics, resolution, and losses

Tools to (a) localize *where* an operator fails, (b) choose grid resolution from
the physics, (c) pick shock-aware training losses, and (d) select an
architecture per regime.

## Frequency-band error analysis

A single scalar error hides the failure mode. Split the error by wavenumber band
with an rFFT: low-band captures large-scale structure, high-band captures the
discontinuity. On shock problems the error is almost entirely high-band, which
tells you the Gibbs limit — not undertraining — is the bottleneck.

```python
import torch

def frequency_band_errors(
    pred, target,
    bands={"low": (0, 5), "mid": (5, 13), "high": (13, None)},
):
    """Relative spectral error per wavenumber band. pred/target: [B, N] real fields."""
    pred_ft = torch.fft.rfft(pred, dim=1)
    tgt_ft = torch.fft.rfft(target, dim=1)
    n_modes = pred_ft.shape[1]

    errors = {}
    for name, (lo, hi) in bands.items():
        hi = hi or n_modes
        err = torch.abs(pred_ft[:, lo:hi] - tgt_ft[:, lo:hi]).mean().item()
        nrm = torch.abs(tgt_ft[:, lo:hi]).mean().item() + 1e-20
        errors[name] = {"abs": err, "rel": err / nrm}
    return errors
```

Typical shock-problem signature:

| Band | Wavenumbers | Rel. error | Reading |
|---|---|---|---|
| Low | k = 0-4 | ~0.1% | Excellent — bulk / large-scale structure captured |
| Mid | k = 5-12 | ~5-10% | Moderate — shock-scale features, partly resolved |
| High | k >= 13 | ~30% | Worst — Gibbs oscillations dominate the residual |

Use it as a decision rule: if high-band error is the largest term and stays high
after training, adding modes or epochs will not save you — add resolution
(below), add the local-conv branch, or change representation
([literature.md](literature.md)). Rising high-band error over training epochs
also flags overfitting to sharp features.

## Resolution scaling

Resolution is the single biggest factor for shocks. The viscous shock width
scales as ~ nu/U; you must place enough cells across that width, or the operator
never sees a resolvable front.

| Viscosity nu | Shock width | Min grid points | Recommendation |
|---|---|---|---|
| 0.1 | ~0.1 | ~100 | 256 is fine |
| 0.01 | ~0.01 | ~1000 | 512 minimum, 1024 better |
| 0.001 | ~0.001 | ~10000 | 1024 (full native); needs A100-class memory |
| inviscid | 0 (true discontinuity) | infinite | As high as affordable; 256-1024 |

- **Memory/compute:** doubling spatial resolution roughly doubles memory and
  per-epoch compute (1D); in 2D it quadruples. Reflection padding adds a further
  `(N + 2*pad)/N` factor to the spectral transforms.
- For truly inviscid problems the discontinuity is infinitely sharp; you can
  never fully resolve it, so expect a residual high-band error floor and pick
  the highest resolution your hardware allows.
- Stream large high-resolution datasets with `hdf5-pde-data-loading` rather than
  loading them into RAM.

## Shock-aware training losses

Plain L2 in physical space under-weights the very features you care about.
Combine (do not replace L2 outright):

- **H1 / Sobolev loss** — adds the L2 error of the spatial derivative
  (`torch.gradient` or a finite-difference stencil), penalizing a smeared or
  misplaced front far more than pointwise L2 does. The most impactful single
  addition for moderate-viscosity problems.
- **Frequency-domain loss** — an L2 term on `rfft(pred) - rfft(target)`,
  optionally band-weighted to up-weight the mid/high bands the diagnostic above
  flags as weak. Directly targets the Gibbs residual.
- **Boundary-consistency loss** — for non-periodic BCs, penalize deviation from
  the known boundary condition (e.g. fixed inflow state, zero-gradient
  outflow) at the domain edges after cropping the reflection pad.
- **Noise injection** — small input perturbations during training regularize
  sharp-feature overfitting on moderate-viscosity data.

Weight these as auxiliary terms (start ~0.1-0.5 relative to the primary L2/H1
term) and watch the per-band diagnostic to confirm the intended band improves.

## Architecture selection per regime

| Problem | Architecture | Key features |
|---|---|---|
| Moderate viscosity (nu = 0.01-0.1) | Enhanced FNO | More modes (~32), H1 loss, noise injection |
| Low viscosity (nu <= 0.001) | ShockFNO | Local-conv branch (gated block), frequency loss, full resolution |
| Multi-variable shocks (Euler, NS) | MultiFNO + ShockFNO | Per-channel normalization + local-conv branch |
| Non-periodic BCs (outgoing/transmissive) | ShockTubeFNO | Reflection padding + boundary loss |
| Riemann / shock-tube | ShockTubeFNO | All of the above combined |

"ShockFNO" here means the gated local-global block; "ShockTubeFNO" wraps that
block in reflection padding. Both are in
[architectures.md](architectures.md).
