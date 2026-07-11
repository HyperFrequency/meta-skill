# Rollout Training: Data Layout, Loop, Noise, Memory

Deep detail for the autoregressive training loop. Read the SKILL.md core-principle
section first.

## Data Layout Convention

Spectral operators (FNO and relatives) apply the FFT over the spatial axis, so the
tensor must be **spatial-first** with time as a sliding channel window, not the
other way around.

```python
# Standard training layout:  [N_samples, X_spatial, T_timesteps, C_channels]
# NOT the raw simulation layout: [N_samples, T_timesteps, X_spatial, C_channels]

# Convert raw dumps (with optional temporal/spatial striding) before the DataLoader:
data = np.transpose(raw[:, ::stride_t, ::stride_x], (0, 2, 1))        # 3D: [N,T,X] -> [N,X,T]
data = np.transpose(raw[:, ::stride_t, ::stride_x, :], (0, 2, 1, 3))  # 4D: [N,T,X,C] -> [N,X,T,C]
```

If the model refuses to converge and the loss is flat, suspect a transposed axis
first — it is the most common silent bug. Loading, striding, and DataLoader
construction for PDEBench/HDF5 sources belong to the `hdf5-pde-data-loading` skill;
this convention is what to hand it.

## Full Autoregressive Rollout Loop

`init_steps` is the number of ground-truth frames given as the initial condition
(the "warmup" window the model conditions on before it starts predicting). The
window slides forward one frame at a time: drop the oldest, append the new
prediction.

```python
import torch
import torch.nn.functional as F

def rollout_train_step(model, initial_condition, ground_truth,
                       init_steps, T_total, noise_std=0.0, extra_loss=None):
    """One optimizer step over a full autoregressive rollout.

    initial_condition : [B, X, init_steps, C]  ground-truth warmup window
    ground_truth       : [B, X, T_total,   C]  full target trajectory
    extra_loss         : optional callable(pred, target) -> scalar (e.g. H1 term)
    """
    inp = initial_condition
    loss = 0.0
    for t in range(init_steps, T_total):
        pred = model(inp)                                   # [B, X, 1, C]
        target = ground_truth[:, :, t:t + 1, :]
        loss = loss + F.mse_loss(pred, target)
        if extra_loss is not None:
            loss = loss + extra_loss(pred, target)

        pred_fed = pred
        if model.training and noise_std > 0:                # inject noise on the fed-back frame only
            pred_fed = pred + noise_std * torch.randn_like(pred)
        inp = torch.cat([inp[:, :, 1:, :], pred_fed], dim=-2)  # slide window

    loss.backward()          # ONE backward for the whole rollout
    return loss.detach()
```

Notes:
- Accumulate `loss` as a running sum of Python-scalar-plus-tensor; it stays a
  tensor with an intact graph until `backward()`.
- Divide the accumulated loss by `(T_total - init_steps)` if you want the reported
  training loss comparable across different rollout lengths.
- The noise is added only to the **fed-back** copy, never to the copy scored
  against the target.

## Noise Level vs. Problem Type

| Problem character | Suggested `σ` |
|---|---|
| Very smooth, well-resolved (advection, linear diffusion) | `0` |
| Moderate dynamics (reaction-diffusion, viscous flow) | `1e-3` |
| Shock / discontinuity dominated (Burgers, Euler) | `5e-3` |
| Chaotic / turbulent | `5e-3` (tune up cautiously) |

Symptoms: rollout diverging after ~10 steps means `σ` is too low; sharp features
(shock fronts, thin reaction layers) smearing out means `σ` is too high. Sweep on
a log scale and select on the validation rollout metric, not train loss.

## Gradient and Memory Discipline

- **Never** call `loss.backward(retain_graph=True)` per timestep. Retaining the
  graph across an entire trajectory holds every intermediate activation and OOMs
  the GPU. Sum the per-step losses, backward once.
- If even a single-backward rollout OOMs on long trajectories, shorten the rollout
  window per step (curriculum: start with a few rollout steps, grow over epochs),
  or use gradient checkpointing on the operator's internal blocks.
- Detach the returned loss for logging (`loss.detach()`), otherwise you pin the
  graph in your metrics buffer.

## Pushforward / Curriculum Rollout (optional refinement)

If full-length rollout training is unstable early, start with a short rollout
(e.g. 2–4 steps) and increase the number of autoregressive steps as training
progresses. This "pushforward"-style curriculum lets the model first learn
accurate single steps, then learn to absorb its own error over longer horizons.
Combine with noise injection; the two are complementary, not redundant.
