# Multi-Component Loss Functions

Targeted loss terms that fix where plain MSE fails for PDE surrogates: spatial
gradients, high frequencies, and domain boundaries. Add each as a weighted term
on top of the base MSE.

All functions below assume `pred` and `target` have the spatial axis at dim 1
(e.g. shape `[B, X, C]` for a single predicted frame). Adjust the axis if your
frame layout differs.

## Sobolev H1 (Spatial Gradient Penalty)

Penalizes errors in the spatial derivative. Critical for steep gradients, reaction
fronts, and shocks, where two fields can have similar pointwise MSE but very
different slopes.

```python
import torch.nn.functional as F

def h1_loss(pred, target):
    """Penalize errors in the first spatial difference."""
    grad_pred = pred[:, 1:, :] - pred[:, :-1, :]
    grad_tgt  = target[:, 1:, :] - target[:, :-1, :]
    return F.mse_loss(grad_pred, grad_tgt)

# Combine:  loss = mse_loss + 0.05 * h1_loss(pred, target)
```

Typical weight: `0.05`–`0.1`. Raise it if fronts are visibly smeared; lower it if
the field becomes noisy/oscillatory (over-penalized gradients inject spurious
high-frequency content).

## Frequency-Banded Loss

Splits the real FFT of the field into contiguous frequency bands and weights the
higher bands more, counteracting MSE's bias toward low-frequency (smooth) content.

```python
import torch

def frequency_loss(pred, target, weights=(1.0, 2.0, 4.0)):
    """Weighted L1 error in Fourier space, higher weight on high-frequency bands."""
    pred_ft = torch.fft.rfft(pred, dim=1)
    tgt_ft  = torch.fft.rfft(target, dim=1)
    n = pred_ft.shape[1]
    bin_size = n // len(weights)
    loss = 0.0
    for i, w in enumerate(weights):
        start = i * bin_size
        end = (i + 1) * bin_size if i < len(weights) - 1 else n   # last band takes the remainder
        loss = loss + w * torch.abs(pred_ft[:, start:end] - tgt_ft[:, start:end]).mean()
    return loss

# Combine:  loss = mse_loss + 0.1 * frequency_loss(pred, target)
```

Typical overall weight: `0.1`. More bands with a steeper weight ramp
(e.g. `(1, 2, 4, 8)`) push harder on fine structure; use it for turbulent or
shock-rich fields, back off for smooth ones.

## Boundary-Aware Loss (Non-Periodic BCs)

Spectral operators assume periodicity and lose accuracy near non-periodic domain
edges. Build an element-wise spatial weight that upweights a boundary band and
apply it to the squared error.

```python
import torch

def boundary_weighted_mse(pred, target, edge_frac=0.1, edge_weight=2.0):
    """MSE with the outer `edge_frac` of the domain on each side upweighted."""
    spatial_dim = pred.shape[1]
    bw = max(1, int(edge_frac * spatial_dim))          # boundary band width
    weight = torch.ones(spatial_dim, device=pred.device)
    weight[:bw] = edge_weight
    weight[-bw:] = edge_weight
    weight = weight / weight.mean()                    # keep overall loss scale stable
    weight = weight.view(1, spatial_dim, 1)            # broadcast over [B, X, C]
    return (weight * (pred - target) ** 2).mean()
```

Normalizing by `weight.mean()` keeps the loss magnitude comparable to plain MSE so
you do not have to re-tune the learning rate. Use `2×` at the edges as a default;
raise it only if boundary error dominates the residual maps.

## Recommended Combinations by Problem Type

| Problem type | MSE | H1 weight | Freq weight | Noise σ | Boundary |
|---|---|---|---|---|---|
| Smooth (advection, diffusion) | yes | — | — | — | — |
| Reaction-diffusion | yes | 0.1 | — | 1e-3 | — |
| Shocks (Burgers, Euler) | yes | 0.05 | 0.1 | 5e-3 | — |
| Non-periodic BCs | yes | 0.05 | — | 1e-3 | 2× at edges |
| Multi-variable coupled | yes | 0.05 | — | 1e-3 | — |

Start from the row closest to your problem, then adjust one term at a time and
select on the validation rollout metric. Adding every term at once makes it
impossible to attribute a change; the base MSE plus one targeted term is usually
enough.
