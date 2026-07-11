# Architectures

Full PyTorch for the shock-hardening modules. These layer onto a standard FNO;
they assume a channel-first layout `[batch, width, spatial]` inside the operator
body (the usual FNO convention). Import assumptions: `torch`, `torch.nn as nn`,
`torch.nn.functional as F`.

## The standard 1D spectral convolution (the FNO global path)

The gated block reuses the canonical FNO spectral convolution (Li et al. 2020):
transform to Fourier space with an rFFT, keep the lowest `modes` wavenumbers,
multiply each by a learned complex weight, then invert. This is the "global"
branch — it is exactly the standard FNO layer, shown here so the block below is
self-contained.

```python
class SpectralConv1d(nn.Module):
    """Standard FNO spectral convolution over the lowest `modes` wavenumbers."""
    def __init__(self, in_channels, out_channels, modes):
        super().__init__()
        self.modes = modes
        scale = 1 / (in_channels * out_channels)
        # complex weights for the retained low modes
        self.weights = nn.Parameter(
            scale * torch.rand(in_channels, out_channels, modes, dtype=torch.cfloat)
        )

    def forward(self, x):                       # x: [B, C_in, N]
        B, C, N = x.shape
        x_ft = torch.fft.rfft(x, dim=-1)        # [B, C_in, N//2 + 1]
        out_ft = torch.zeros(
            B, self.weights.shape[1], x_ft.shape[-1],
            dtype=torch.cfloat, device=x.device,
        )
        m = min(self.modes, x_ft.shape[-1])
        # multiply retained modes: einsum over channels per wavenumber
        out_ft[:, :, :m] = torch.einsum(
            "bix,iox->box", x_ft[:, :, :m], self.weights[:, :, :m]
        )
        return torch.fft.irfft(out_ft, n=N, dim=-1)   # [B, C_out, N]
```

Notes:
- `modes` truncation is what makes FNO cheap and discretization-invariant, and
  is also the source of the Gibbs limit — the retained band cannot represent a
  jump. Raising `modes` (e.g. 16 -> 32) buys a little on shock problems at
  linear cost, but does not remove the oscillation.
- For 2D/3D, swap in the corresponding `SpectralConv2d/3d` from your FNO stack
  (e.g. the `neuralop` library used by `neural-operator`); the gating idea
  below is identical.

## 1. Gated local-global FNO block

```python
class FNOBlock(nn.Module):
    """Gated local-global spectral block: global FFT path + bias + local conv."""
    def __init__(self, width, modes, local_kernel=7):
        super().__init__()
        self.spectral = SpectralConv1d(width, width, modes)          # global
        self.pointwise = nn.Conv1d(width, width, 1)                  # bias / residual path
        self.local_conv = nn.Conv1d(
            width, width, local_kernel, padding=local_kernel // 2
        )                                                            # local, shock-scale
        self.gate = nn.Parameter(torch.tensor(0.3))                  # learned blend

    def forward(self, x):                        # x: [B, width, N]
        global_out = self.spectral(x) + self.pointwise(x)
        local_out = self.local_conv(x)
        alpha = torch.sigmoid(self.gate)         # scalar in (0, 1)
        return (1 - alpha) * global_out + alpha * local_out
```

Design rationale:
- **`local_kernel=7`** spans ~7 grid cells. On a 1024-point grid with a
  ~1-cell-wide shock, that covers the shock plus its immediate neighborhood —
  enough to represent the front sharply without the ringing a global basis
  would introduce. Widen the kernel if the shock is broader or the grid coarser.
- **Scalar gate initialized at 0.3** (sigmoid(0.3) ~= 0.57) starts the block
  slightly favoring the global path, then learns the balance per layer. Keeping
  the gate scalar (rather than a spatial attention map) is the deliberate
  simplification: fewer parameters, no risk of the gate itself overfitting.
- **Observed convergence:** across a trained stack, gate values typically land
  in alpha ~ 0.3-0.6, confirming both branches carry signal — the local branch
  is not a dead appendage.
- **Lineage:** this is a simplified LOGLO-FNO (arXiv:2504.04260) — plain
  `Conv1d` instead of local *spectral* convolutions, and a scalar gate instead
  of spatial attention. The simplification trades a little peak accuracy for
  robustness and far fewer moving parts.

Apply the usual FNO activation (e.g. GELU) between stacked blocks, exactly as in
a standard FNO. A typical operator lifts the input to `width` channels with a
pointwise `fc0`, runs N `FNOBlock`s, then projects back with a small MLP head.

## 2. Reflection padding for non-periodic BCs

The FFT assumes periodicity. Under outgoing/transmissive or Dirichlet
boundaries, a feature exiting one side re-enters the other in Fourier space,
corrupting the near-boundary solution. Pad with reflection *before* the spectral
layers and crop after.

```python
class ShockTubeFNO1d(nn.Module):
    def __init__(self, width, modes, in_channels, out_channels,
                 n_blocks=4, pad_size=32):
        super().__init__()
        self.pad_size = pad_size
        self.fc0 = nn.Linear(in_channels, width)     # lift; expects channel-last input
        self.blocks = nn.ModuleList(
            [FNOBlock(width, modes) for _ in range(n_blocks)]
        )
        self.projection = nn.Sequential(
            nn.Conv1d(width, width, 1), nn.GELU(),
            nn.Conv1d(width, out_channels, 1),
        )

    def forward(self, x):                            # x: [B, N, in_channels]
        x = self.fc0(x).permute(0, 2, 1)             # -> [B, width, N]

        # reflection padding around the spectral core
        x = F.pad(x, [self.pad_size, self.pad_size], mode='reflect')
        for block in self.blocks:
            x = F.gelu(block(x))
        x = x[:, :, self.pad_size:-self.pad_size]     # crop back to N

        return self.projection(x)                     # [B, out_channels, N]
```

Why it works and how to size it:
- Reflection produces a **smooth, jump-free continuation** at each boundary;
  zero-padding instead introduces an artificial discontinuity that *adds*
  high-frequency energy — the opposite of what you want.
- Use a *meaningful* extension: `pad_size=32` on a 256-point grid is ~12.5%.
  The 2-point pad common in vanilla FNO code (~0.2%) is effectively a no-op.
- **Cost:** padding grows the spectral transform length, so compute scales with
  `(N + 2*pad_size)`; 10-15% padding is a good default, more rarely pays off.
- **Better, harder alternative:** Fourier Continuation (FC-PINO,
  arXiv:2211.15960) fits a polynomial continuation into a periodic extension
  domain — more principled than reflection, but heavier to implement. Reach for
  it only if reflection padding leaves residual boundary error.

## 3. Multi-variable systems (Euler, Navier-Stokes)

Compressible systems carry several fields (density, momentum/velocity, energy or
pressure) whose magnitudes differ by orders. A single normalization smears the
small-magnitude channel. Normalize **per channel** on input and de-normalize on
output, then run the shared shock-hardened body:

- Store per-channel mean/std (or min/max) from the training set.
- Standardize each channel independently before `fc0`.
- Predict the standardized field; invert the transform per channel at the head.
- Everything between is the same `FNOBlock` stack (optionally with reflection
  padding for a shock tube). Only the front/back normalization is
  channel-aware.

This "MultiFNO + ShockFNO" combination is what the selection table in
[diagnostics.md](diagnostics.md) recommends for Euler/NS shocks.
