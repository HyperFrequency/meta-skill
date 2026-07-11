# FNO hyperparameters, metrics, and troubleshooting

## Key hyperparameters (FNO / TFNO)

| Parameter | Typical range | Effect |
|---|---|---|
| `n_modes` (per dim) | 8–32 | Fourier modes kept = frequency resolution. Too few → over-smoothed, blurry output; too many → overfitting and wasted parameters. Cannot exceed `grid_size // 2`. |
| `hidden_channels` | 32–128 | Network width. More capacity, more memory. |
| `n_layers` | 4–6 | Spectral-conv depth. Deeper helps complex maps, slower to train. |
| `lifting_channels` / `projection_channels` | 128–256 | Width of the pointwise MLPs in/out of the spectral blocks. |
| learning rate | 1e-3 → 1e-4 | Adam; decay with StepLR or cosine annealing. |
| batch size | 16–64 | Larger is more stable; bounded by GPU memory. |
| weight decay | 1e-5 → 1e-4 | Regularization; raise it if the test gap grows. |
| training samples | 500–5000+ | More solved instances → better generalization; the usual bottleneck is data-generation cost. |
| `factorization`, `rank` (TFNO) | `'tucker'`, 0.05–0.5 | Compresses spectral weights; lower rank = fewer params, some accuracy loss. |

## Data and normalization

- **Normalize inputs and outputs** to zero mean / unit variance. Fit statistics on
  the training split only; de-normalize predictions before reporting physical error.
  The library `data_processor` from `load_*` datasets does this for you.
- **Sample parameters across the range you care about.** The operator only
  generalizes within the distribution of initial/boundary conditions and
  coefficients it saw. Test explicitly on out-of-distribution inputs to find limits.
- **Non-periodic boundaries:** append normalized coordinate channels (a grid of
  `x`, `y`) to the input so the model can localize; a plain FNO otherwise assumes
  periodicity.
- **Multiple input fields** (e.g. coefficient + forcing) stack along the channel
  axis: `in_channels` = number of stacked fields.

## Metrics

- **Relative L2** (`LpLoss(d, p=2)`): scale-invariant, the standard operator metric.
  Prefer it over raw MSE, whose magnitude depends on the field's scale.
- **H1 / Sobolev** (`H1Loss(d)`): also penalizes the gradient error, rewarding
  correct fine-scale structure. Training on H1 often sharpens FNO predictions.
- Report per-instance relative error distribution (mean *and* worst-case), not just
  the mean — surrogates used in optimization loops are exposed to their tails.

## Troubleshooting

| Symptom | Likely cause → fix |
|---|---|
| Training loss won't decrease | LR too high/low, or a data-loading bug. Lower LR, confirm shapes are channel-first `(B, C, *spatial)`, verify normalization. |
| Predictions smooth but wrong / miss sharp features | Too few `n_modes` (spectral bias). Increase `n_modes` and/or train on `H1Loss`. |
| Low train error, high test error | Overfitting. Add weight decay, reduce `hidden_channels`/`n_modes`, or generate more training instances. |
| `RuntimeError` on channel dim / garbage output | Channel-last input. Modern FNO is channel-first: reshape to `(B, in_channels, *spatial)`. |
| Import error on `neuraloperator.models` or `FNO1d` | Wrong namespace/old API. Use `from neuralop.models import FNO` with `n_modes=(...)`. |
| CUDA out of memory | Reduce batch size, `hidden_channels`, or `n_modes`; consider TFNO for a smaller parameter count. |
| Bad accuracy at a resolution not seen in training | Zero-shot super-resolution exposes frequencies beyond `n_modes`, or the input was not consistently normalized. Validate on a held-out high-res set; retrain with more modes if needed. |
| Wrong near domain edges (non-periodic problem) | FNO assumes periodicity. Add coordinate channels, pad the domain, or use a boundary-aware variant. |
| Discontinuous / shock solutions blur | Global Fourier bases smear discontinuities. Consider more modes, an H1 loss, or a shock-aware operator variant; a spectral operator is not ideal for strong shocks. |

## Practical order of operations

1. Start with **FNO** on a regular grid — the simplest robust choice.
2. Get a baseline with modest settings (`n_modes=16`, `hidden_channels=64`,
   `n_layers=4`) and normalized data.
3. If under-resolved (blurry), raise `n_modes`; if overfitting, add regularization
   or data.
4. Only move to TFNO/UNO/GINO/DeepONet when FNO's assumptions (regular grid,
   periodicity) genuinely do not hold — see
   [architectures.md](architectures.md).
