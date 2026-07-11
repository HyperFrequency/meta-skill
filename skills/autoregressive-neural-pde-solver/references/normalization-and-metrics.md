# Per-Channel Normalization, nRMSE, and Data Splits

How to normalize coupled multi-variable systems, compute the benchmark metric
correctly, and split data so reported numbers are honest.

## Per-Channel Normalization

When PDE variables live on different scales (density ~O(6), velocity ~O(0.5),
pressure ~O(59)), an unnormalized loss is dominated by the largest-scale variable
and the model effectively ignores the rest. Standardize **each channel
independently** using statistics computed from the **training split only** — never
from val/test, which would leak information.

```python
# Compute from TRAINING data only, reduce over sample/spatial/time axes, keep channel
ch_mean = train_data.mean(dim=(0, 1, 2))          # [C]
ch_std  = train_data.std(dim=(0, 1, 2)) + 1e-8    # [C]  (epsilon guards constant channels)

# Apply the SAME stats to train, val, and test
data_normalized = (data - ch_mean) / ch_std

def denormalize(x):
    """Map a normalized tensor back to physical scale; handles CPU/GPU placement."""
    return x * ch_std.to(x.device) + ch_mean.to(x.device)
```

Train and compute the loss in normalized space, but **denormalize predictions and
targets back to original scale before computing any reported metric** — otherwise
your nRMSE is in standardized units and not comparable to published baselines.

```python
preds_orig   = denormalize(preds)
targets_orig = denormalize(targets)
# compute nRMSE on *_orig, not on the normalized tensors
```

## nRMSE: Two Valid Definitions

PDEBench-style leaderboards report nRMSE, but more than one formula is in
circulation and they can differ by 5–10% on the same predictions. Compute **both**
and confirm you beat the baseline under **both** before claiming an improvement.

`init_step` skips the ground-truth warmup frames so the metric scores only the
model's own rollout.

```python
import torch

def calc_nrmse_pertimestep(preds, targets, init_step=10):
    """Per-timestep RMSE / RMS, averaged over (N, C, T). Common in code releases.
    preds, targets: [N, X, T, C]"""
    p  = preds[:, :, init_step:, :].permute(0, 3, 1, 2)    # -> [N, C, X, T]
    tg = targets[:, :, init_step:, :].permute(0, 3, 1, 2)
    err = torch.sqrt(torch.mean((p - tg) ** 2, dim=2))     # RMSE over space: [N, C, T]
    nrm = torch.sqrt(torch.mean(tg ** 2, dim=2)) + 1e-20
    return torch.mean(err / nrm).item()

def calc_nrmse_frobenius(preds, targets, init_step=10):
    """Per-sample Frobenius-norm ratio. The canonical PDEBench definition.
    preds, targets: [N, X, T, C]"""
    p  = preds[:, :, init_step:, :]
    tg = targets[:, :, init_step:, :]
    per_sample = torch.sqrt(((p - tg) ** 2).sum(dim=(1, 2, 3))) / \
                 (torch.sqrt((tg ** 2).sum(dim=(1, 2, 3))) + 1e-20)
    return per_sample.mean().item()
```

Record both, and state which one you compare against, e.g.:

```json
{"nrmse_pertimestep": 0.041, "nrmse_frobenius": 0.038, "metric_note": "both beat baseline"}
```

The `+1e-20` guards against divide-by-zero on trajectories whose target norm is
(near) zero; do not drop it.

## Train / Val / Test Discipline

Three disjoint splits. Select model checkpoints on **validation**; evaluate the
**test** split **exactly once**, at the very end, for the number you report.
Selecting checkpoints on test (or peeking at it repeatedly) produces optimistic,
non-reproducible metrics — the most common way methods papers overstate results.

```python
N_TRAIN, N_VAL, N_TEST = 8000, 1000, 1000
train_data = data[:N_TRAIN]
val_data   = data[N_TRAIN:N_TRAIN + N_VAL]              # checkpoint selection
test_data  = data[N_TRAIN + N_VAL:N_TRAIN + N_VAL + N_TEST]   # final metric, evaluated ONCE

# During training: score val_loader each epoch, keep the best-val checkpoint.
# After training: load best-val checkpoint, run test_loader once, report that number.
```

Compute normalization statistics from `train_data` only (see above), then apply
them to `val_data` and `test_data`.
