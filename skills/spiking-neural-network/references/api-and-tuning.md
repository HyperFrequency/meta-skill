# SNN API surface, tuning, and diagnostics

## Key API surface

### norse (functional + module APIs)

| Symbol | What it does |
|---|---|
| `norse.torch.functional.lif.lif_step(z, state, p)` | One-step LIF neuron update (Euler). Returns `(spikes, new_state)`. |
| `norse.torch.functional.lif.LIFParameters` | Dataclass: `tau_mem_inv`, `tau_syn_inv`, `v_th`, `v_reset`. Override fields to tune dynamics. |
| `norse.torch.module.lif.LIFCell` | Module wrapper around `lif_step` for use in `nn.Sequential`-style code. |
| `norse.torch.module.leaky_integrator.LICell` | Leaky integrator (no spike) — standard readout layer for classification. |
| `norse.torch.module.SequentialState` | Equivalent of `nn.Sequential` that threads neuron state through layers. |

### snntorch

| Symbol | What it does |
|---|---|
| `snntorch.Leaky(beta, spike_grad, init_hidden, output)` | LIF neuron as an `nn.Module`. `beta` is the membrane decay. |
| `snntorch.Synaptic(alpha, beta, ...)` | Two-state neuron with synaptic current — closer to bio LIF. |
| `snntorch.surrogate.fast_sigmoid(slope=25)` | Standard surrogate gradient for backprop through the spike non-linearity. |
| `snntorch.surrogate.atan()` | ArcTan surrogate — smoother gradient, slightly better convergence on some tasks. |
| `snntorch.spikegen.rate(x, num_steps=T)` | Rate-encode tensor `x` to spike trains. |
| `snntorch.spikegen.latency(x, num_steps=T)` | Latency-encode (first-spike-time) tensor `x`. |

## Architecture choices

- **Time steps `T`**: 20–50 is typical for rate-encoding. Lower `T` = faster training & inference
  but less expressive; higher `T` = closer to a "real-valued" net but bigger memory. Sweep `T ∈ {20, 50, 100}`.
- **Encoding**: rate-encoding (Bernoulli) is the default and matches well with real-valued inputs.
  Latency / temporal coding is more "neuromorphic" but harder to train and almost always lower
  accuracy on the same task.
- **Membrane decay `beta` (snntorch) / `tau_mem_inv` (norse)**: 0.85–0.95 is the sane band. Too
  high → neurons never forget, the net behaves like a sum; too low → neurons reset every step and
  lose context.
- **Threshold `v_th`**: 1.0 is the default and rarely worth tuning until you have a working baseline.
- **Surrogate gradient**: `fast_sigmoid(slope=25)` is the standard choice. ArcTan is a fine
  alternative. Don't try training without one — the Heaviside spike is non-differentiable.
- **Depth**: 2 hidden layers is plenty for return-direction tasks. SNNs are harder to train deep;
  if you need depth, use BPTT-friendly tricks like layer-norm-over-time and AdamW with low LR.
- **Readout**: end with a leaky-integrator (LI) layer, not another LIF — you want a real-valued
  output to feed `CrossEntropyLoss`.

## Common pitfalls

1. **Wrong `T` for your input.** Too few steps and rate-encoding doesn't have enough resolution to
   represent the input distribution; too many and training is slow. Print the average spike rate per
   layer — if it's <1% or >50%, something is off.
2. **Dead neurons.** Spike-rate collapses to zero in one or more layers, the gradient stops flowing,
   and training stalls. Check `(spikes > 0).float().mean()` per layer per epoch; if any layer is at
   ~0, lower `v_th` or increase upstream activation.
3. **Forgetting to reset state between batches.** State (`v_mem`, `i_syn`) persists if you reuse the
   same module instance without zeroing. In norse, pass `state=None` for the first time step of each
   batch; in snntorch with `init_hidden=True`, the module handles this — but you must call the model
   in fresh forward passes, not a single rolling forward.
4. **Encoding leakage.** Rate-encoding normalises a window using its own min/max, which uses future
   bars within the window. Fine if the window is purely past; *not* fine if you accidentally include
   the prediction target.
5. **Comparing against a dense baseline at the same parameter count.** A 1k-parameter LSTM crushes a
   1k-parameter SNN on typical price prediction. Compare on the right axis (inference energy, not just
   accuracy) — otherwise SNN looks pointless.
6. **Surrogate-gradient slope too steep.** A very steep `fast_sigmoid` (`slope=50+`) gives near-step
   gradients and fails to train. Stick to `slope=25` unless you have a reason.

## Encoding choices in depth

The encoding step (real-valued → spikes) is where most accuracy is lost. The three canonical schemes:

| Scheme | How it works | When to use |
|---|---|---|
| **Rate** | Bernoulli-sample each step with `p = normalized(x)`. Higher value = more spikes over `T` steps. | Default; works with any real-valued input. Requires `T ≥ 20` for good resolution. |
| **Latency / time-to-first-spike** | High value = spike early, low value = spike late. One spike per neuron per window. | Energy-optimal; the closest to "neuromorphic" coding. Hard to train, lower accuracy. |
| **Population** | Spread one value across `K` neurons whose tuning curves overlap. Like a 1-D Gaussian receptive field. | Good for low-dim inputs where you want lots of effective dimensions. More params. |

For price data, rate-encoding is the right starting point. Latency-encoding is interesting when the
input *is already event-like* (e.g. quote arrival times).

## Scaling to production

- **Neuromorphic hardware.** Once a model trains and runs on CPU/GPU, porting to Intel Loihi (via
  `nxsdk`) or Akida (via `akida` SDK) requires re-expressing the LIF parameters in the target's units.
  Norse has experimental Loihi export; snntorch has documented Akida targets. Both are evolving — pin
  the SDK version.
- **Inference latency on CPU.** A 2-layer LIF net with `T=20` and 64 hidden units runs in ~1 ms on a
  modern x86 core. Most of that is `lif_step` overhead — fuse with `torch.compile` if you can.
- **Spike-count readout.** For deployment, replace the integrator readout with a simple spike-count
  over `T` and pick `argmax`. Avoids needing real-valued output activations on neuromorphic targets.
- **Quantisation.** SNNs quantise gracefully — int8 weights and 1-bit activations (spikes!) are
  essentially native. This is the whole point.

## Diagnostics

When an SNN fails to train, in order:

1. Print spike rate per layer (`(spikes > 0).float().mean()`). Target: 5-30%. <1% = dead; >70% = saturated.
2. Print `loss` per epoch over 5 epochs. Flat at random-chance → check encoding, then surrogate
   gradient slope, then learning rate.
3. Strip to a single LIF layer + readout. If that still fails, the bug is in encoding / data, not the network.
4. Swap in `nn.ReLU` for the LIF neurons (turning it into a dense net). If the dense version works and
   the spiking version doesn't, the issue is `T`, `v_th`, or the surrogate.
5. Lower `T`. Counter-intuitively, `T=10` sometimes works better than `T=50` because gradient signal
   isn't smeared across as many steps.
