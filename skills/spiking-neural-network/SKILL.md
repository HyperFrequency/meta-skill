---
name: spiking-neural-network
description: Spiking neural networks (SNNs) for low-power and event-driven price prediction. Wraps the norse PyTorch SNN library (LIF/LIFParameters, lif_step, decode) for a minimal LIF pipeline on a synthetic signal, with snntorch noted as an alternative API. Covers rate vs. latency encoding, time-step choice, and surrogate-gradient training.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: Apache-2.0 (norse upstream), MIT (snntorch upstream)
metadata:
    skill-author: HyperFrequency
    skill-domain: deep-learning / quant
---

# Spiking Neural Network

## When to use

Use this skill when you want an event-driven, low-power-friendly model for tick / quote / micro-structure data:

- The compute target is neuromorphic hardware (Intel Loihi, SpiNNaker, Akida) — SNNs are native there.
- The input is already event-like (level-1 quote updates, trade arrivals) and you want a model that consumes asynchronous events instead of resampling to a fixed grid.
- You're researching ultra-low-power inference for an embedded execution box.
- You want a bio-inspired baseline to compare against a standard CNN/RNN on the same prediction task.

Do **not** use an SNN if you just want best accuracy. On most quant tasks, a small Conv1D or LSTM will outperform a similarly-sized SNN; SNNs win on energy/inference cost on the right hardware, not on raw accuracy.

Two main libraries:

1. **norse** (`https://github.com/norse/norse`) — PyTorch-first, exposes `lif_step` / `LIFCell` / `LIFParameters`. Functional and modular: easy to compose with `torch.nn`. Preferred when you want SNN primitives that drop into a standard PyTorch graph.
2. **snntorch** (`https://github.com/jeshraghian/snntorch`) — Also PyTorch, slightly higher-level. Exposes `snn.Leaky` neurons that act like `nn.Module`s. Friendlier surrogate-gradient API (`surrogate.fast_sigmoid()`, `surrogate.atan()`). Good alternative if you prefer object-oriented neuron layers and bundled tutorials.

## Install / setup

```bash
# norse
uv pip install norse torch

# alternative — snntorch
uv pip install snntorch torch
```

GPU notes:

- Both libraries follow standard PyTorch device placement: `.to("cuda")` / `.to("cpu")`. Apple Silicon `mps` works for most operators in snntorch; norse's custom CUDA kernels are CPU/CUDA only — verify with a small test.
- SNNs unroll over `T` time steps in the forward pass. Memory grows linearly with `T`; if you OOM on GPU, cut `T` first before cutting batch size.

Verify install:

```python
import torch, norse; print(torch.__version__, norse.__version__)
# or
import snntorch as snn; print(snn.__version__)
```

## Minimal example — norse LIF pipeline on a synthetic signal (≤60 lines)

End-to-end: build a synthetic price-like signal → rate-encode to spikes → feed through a 2-layer LIF network → train to predict next-step direction.

```python
import torch, torch.nn as nn
from norse.torch.functional.lif import lif_step, LIFParameters       # unverified — see https://github.com/norse/norse/blob/main/norse/torch/functional/lif.py
from norse.torch.module.leaky_integrator import LICell               # output integrator
# (snntorch alternative: from snntorch import Leaky, surrogate)

T, BATCH, D_IN, D_HID, D_OUT = 50, 64, 8, 64, 2
device = "cuda" if torch.cuda.is_available() else "cpu"

# 1. synthetic signal: noisy sinusoid + lag-1 label (up/down)
t = torch.arange(0, 4000) / 50.0
x = torch.sin(t) + 0.3 * torch.randn_like(t)
ret = torch.diff(x)
y = (ret > 0).long()
windows = torch.stack([x[i:i + D_IN] for i in range(len(ret) - D_IN)])
labels = y[D_IN - 1:][:len(windows)]
split = int(0.8 * len(windows))

# 2. rate-encoding: convert a real-valued window into spike trains over T steps
def rate_encode(x_window, T=T):
    # x_window: (B, D_IN). Normalise to [0,1] then Bernoulli-sample per step
    p = (x_window - x_window.min()) / (x_window.max() - x_window.min() + 1e-6)
    return torch.bernoulli(p.unsqueeze(0).expand(T, *p.shape))         # (T, B, D_IN)

# 3. tiny LIF network
class SNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(D_IN, D_HID)
        self.fc2 = nn.Linear(D_HID, D_OUT)
        self.p = LIFParameters()                                       # default tau_mem, v_th, etc.
        self.li = LICell(D_OUT, D_OUT)                                 # readout integrator
    def forward(self, spikes):
        s1 = s2 = li_state = None
        out_accum = 0.0
        for t in range(spikes.shape[0]):
            z = self.fc1(spikes[t])
            z, s1 = lif_step(z, s1, p=self.p)                          # spike & state
            z = self.fc2(z)
            z, s2 = lif_step(z, s2, p=self.p)
            out, li_state = self.li(z, li_state)
            out_accum = out_accum + out
        return out_accum / spikes.shape[0]                              # average output over T

model = SNN().to(device)
opt = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.CrossEntropyLoss()

for epoch in range(10):
    idx = torch.randperm(split)
    for i in range(0, split, BATCH):
        b = idx[i:i + BATCH]
        spikes = rate_encode(windows[b]).to(device)
        yb = labels[b].to(device)
        opt.zero_grad()
        loss = loss_fn(model(spikes), yb)
        loss.backward(); opt.step()
    print(f"epoch {epoch} loss {loss.item():.4f}")

with torch.no_grad():
    test_spikes = rate_encode(windows[split:]).to(device)
    acc = (model(test_spikes).argmax(-1).cpu() == labels[split:]).float().mean()
    print("test acc", acc.item())
```

## Minimal example — snntorch alternative (≤15 lines)

```python
import snntorch as snn
from snntorch import surrogate
beta, spike_grad = 0.9, surrogate.fast_sigmoid()                       # see https://github.com/jeshraghian/snntorch/blob/master/examples/quickstart.ipynb

net = nn.Sequential(
    nn.Linear(D_IN, D_HID),
    snn.Leaky(beta=beta, spike_grad=spike_grad, init_hidden=True),
    nn.Linear(D_HID, D_OUT),
    snn.Leaky(beta=beta, spike_grad=spike_grad, init_hidden=True, output=True),
).to(device)

# forward is unrolled outside by stepping inputs T times and summing outputs
spk_out_sum = 0
for t in range(T):
    spk_out, _ = net(spikes[t])
    spk_out_sum = spk_out_sum + spk_out
loss = nn.functional.cross_entropy(spk_out_sum / T, yb)
```

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

- **Time steps `T`**: 20–50 is typical for rate-encoding. Lower `T` = faster training & inference but less expressive; higher `T` = closer to a "real-valued" net but bigger memory. Sweep `T ∈ {20, 50, 100}`.
- **Encoding**: rate-encoding (Bernoulli) is the default and matches well with real-valued inputs. Latency / temporal coding is more "neuromorphic" but harder to train and almost always lower accuracy on the same task.
- **Membrane decay `beta` (snntorch) / `tau_mem_inv` (norse)**: 0.85–0.95 is the sane band. Too high → neurons never forget, the net behaves like a sum; too low → neurons reset every step and lose context.
- **Threshold `v_th`**: 1.0 is the default and rarely worth tuning until you have a working baseline.
- **Surrogate gradient**: `fast_sigmoid(slope=25)` is the standard choice. ArcTan is a fine alternative. Don't try training without one — the Heaviside spike is non-differentiable.
- **Depth**: 2 hidden layers is plenty for return-direction tasks. SNNs are harder to train deep; if you need depth, use BPTT-friendly tricks like layer-norm-over-time and AdamW with low LR.
- **Readout**: end with a leaky-integrator (LI) layer, not another LIF — you want a real-valued output to feed `CrossEntropyLoss`.

## Common pitfalls

1. **Wrong `T` for your input.** Too few steps and rate-encoding doesn't have enough resolution to represent the input distribution; too many and training is slow. Print the average spike rate per layer — if it's <1% or >50%, something is off.
2. **Dead neurons.** Spike-rate collapses to zero in one or more layers, the gradient stops flowing, and training stalls. Check `(spikes > 0).float().mean()` per layer per epoch; if any layer is at ~0, lower `v_th` or increase upstream activation.
3. **Forgetting to reset state between batches.** State (`v_mem`, `i_syn`) persists if you reuse the same module instance without zeroing. In norse, pass `state=None` for the first time step of each batch; in snntorch with `init_hidden=True`, the module handles this — but you must call the model in fresh forward passes, not a single rolling forward.
4. **Encoding leakage.** Rate-encoding normalises a window using its own min/max, which uses future bars within the window. Fine if the window is purely past; *not* fine if you accidentally include the prediction target.
5. **Comparing against a dense baseline at the same parameter count.** A 1k-parameter LSTM crushes a 1k-parameter SNN on typical price prediction. Compare on the right axis (inference energy, not just accuracy) — otherwise SNN looks pointless.
6. **Surrogate-gradient slope too steep.** A very steep `fast_sigmoid` (`slope=50+`) gives near-step gradients and fails to train. Stick to `slope=25` unless you have a reason.

## Encoding choices in depth

The encoding step (real-valued → spikes) is where most accuracy is lost. The three canonical schemes:

| Scheme | How it works | When to use |
|---|---|---|
| **Rate** | Bernoulli-sample each step with `p = normalized(x)`. Higher value = more spikes over `T` steps. | Default; works with any real-valued input. Requires `T ≥ 20` for good resolution. |
| **Latency / time-to-first-spike** | High value = spike early, low value = spike late. One spike per neuron per window. | Energy-optimal; the closest to "neuromorphic" coding. Hard to train, lower accuracy. |
| **Population** | Spread one value across `K` neurons whose tuning curves overlap. Like a 1-D Gaussian receptive field. | Good for low-dim inputs where you want lots of effective dimensions. More params. |

For price data, rate-encoding is the right starting point. Latency-encoding is interesting when the input *is already event-like* (e.g. quote arrival times).

## Scaling to production

- **Neuromorphic hardware.** Once a model trains and runs on CPU/GPU, porting to Intel Loihi (via `nxsdk`) or Akida (via `akida` SDK) requires re-expressing the LIF parameters in the target's units. Norse has experimental Loihi export; snntorch has documented Akida targets. Both are evolving — pin the SDK version.
- **Inference latency on CPU.** A 2-layer LIF net with `T=20` and 64 hidden units runs in ~1 ms on a modern x86 core. Most of that is `lif_step` overhead — fuse with `torch.compile` if you can.
- **Spike-count readout.** For deployment, replace the integrator readout with a simple spike-count over `T` and pick `argmax`. Avoids needing real-valued output activations on neuromorphic targets.
- **Quantisation.** SNNs quantise gracefully — int8 weights and 1-bit activations (spikes!) are essentially native. This is the whole point.

## Diagnostics

When an SNN fails to train, in order:

1. Print spike rate per layer (`(spikes > 0).float().mean()`). Target: 5-30%. <1% = dead; >70% = saturated.
2. Print `loss` per epoch over 5 epochs. Flat at random-chance → check encoding, then surrogate gradient slope, then learning rate.
3. Strip to a single LIF layer + readout. If that still fails, the bug is in encoding / data, not the network.
4. Swap in `nn.ReLU` for the LIF neurons (turning it into a dense net). If the dense version works and the spiking version doesn't, the issue is `T`, `v_th`, or the surrogate.
5. Lower `T`. Counter-intuitively, `T=10` sometimes works better than `T=50` because gradient signal isn't smeared across as many steps.

## References

### Primary library
- [norse/norse on GitHub](https://github.com/norse/norse) — upstream repo, issues, releases
- [norse documentation](https://norse.github.io/norse/) — pinned to current main as of cross-check
- [jeshraghian/snntorch on GitHub](https://github.com/jeshraghian/snntorch) — alternative library; bigger tutorial set
- [snntorch documentation](https://snntorch.readthedocs.io/) — pinned to v0.9
- [snntorch tutorials directory](https://github.com/jeshraghian/snntorch/tree/master/examples) — quickstart, CNN, LSTM-equivalent (`Synaptic`), recurrent SNNs
- [PyTorch on GitHub](https://github.com/pytorch/pytorch) — the autograd substrate both libraries sit on

### Deep-dive docs (specific pages worth bookmarking)
- [norse `lif_step` source](https://github.com/norse/norse/blob/main/norse/torch/functional/lif.py) — the canonical Euler-step LIF; read once to know what `tau_mem_inv`, `v_th`, `v_reset` actually do
- [norse `LIFParameters` dataclass](https://github.com/norse/norse/blob/main/norse/torch/functional/lif.py) — the override surface for membrane dynamics
- [norse module API](https://norse.github.io/norse/auto_api/norse.torch.module.html) — `LIFCell`, `LICell`, `SequentialState` for module-based composition
- [snntorch `Leaky` API](https://snntorch.readthedocs.io/en/latest/snntorch.html#snntorch.Leaky) — `beta`, `spike_grad`, `init_hidden`, `output`; the object-oriented neuron
- [snntorch `Synaptic` API](https://snntorch.readthedocs.io/en/latest/snntorch.html#snntorch.Synaptic) — two-state neuron with synaptic current; closer to bio LIF
- [snntorch `surrogate` module](https://snntorch.readthedocs.io/en/latest/snntorch.surrogate.html) — `fast_sigmoid(slope=25)`, `atan()`, `straight_through_estimator()`
- [snntorch `spikegen` encoding](https://snntorch.readthedocs.io/en/latest/snntorch.spikegen.html) — `rate`, `latency`, `delta` encoders; what each method does to input distribution
- [snntorch quickstart notebook (CNN-SNN)](https://github.com/jeshraghian/snntorch/blob/master/examples/quickstart.ipynb) — surrogate-gradient training end to end

### Adjacent / alternative libraries
- [Brian2](https://github.com/brian-team/brian2) — full computational neuroscience simulator; bigger learning curve but the reference for biological accuracy
- [BindsNET](https://github.com/BindsNET/bindsnet) — PyTorch-based SNN library focused on STDP and biologically plausible learning rules
- [Nengo](https://github.com/nengo/nengo) — neural compiler with built-in Loihi / SpiNNaker backends; relevant when neuromorphic hardware is the deployment target
- [Lava (Intel)](https://github.com/lava-nc/lava) — Intel's open-source neuromorphic computing framework; native for Loihi 2 deployment
- [Spyx (JAX-based SNNs)](https://github.com/kmheckel/spyx) — JAX backend, faster than norse for short networks
- [Auryn](https://github.com/fzenke/auryn) — C++ HPC SNN simulator; reference for large-scale Friedemann Zenke / spike-timing experiments

### Academic papers
- Eshraghian, J. K., Ward, M., Neftci, E., Wang, X., Lenz, G., Dwivedi, G., Bennamoun, M., Jeong, D. S., & Lu, W. D. (2023). "Training Spiking Neural Networks Using Lessons From Deep Learning." *Proceedings of the IEEE* 111(9), 1016-1054. [DOI: 10.1109/JPROC.2023.3308088](https://doi.org/10.1109/JPROC.2023.3308088) / [arXiv:2109.12894](https://arxiv.org/abs/2109.12894) — the snntorch reference paper; serves as a tutorial.
- Neftci, E. O., Mostafa, H., & Zenke, F. (2019). "Surrogate Gradient Learning in Spiking Neural Networks." *IEEE Signal Processing Magazine* 36(6), 51-63. [arXiv:1901.09948](https://arxiv.org/abs/1901.09948) — the conceptual foundation for `fast_sigmoid` / `atan` surrogate gradients.
- Pfeiffer, M., & Pfeil, T. (2018). "Deep Learning With Spiking Neurons: Opportunities and Challenges." *Frontiers in Neuroscience* 12, 774. [DOI: 10.3389/fnins.2018.00774](https://doi.org/10.3389/fnins.2018.00774) — survey of how deep-learning techniques map onto SNNs.
- Davies, M., Srinivasa, N., Lin, T.-H., Chinya, G., Cao, Y., Choday, S. H., et al. (2018). "Loihi: A Neuromorphic Manycore Processor with On-Chip Learning." *IEEE Micro* 38(1), 82-99. [DOI: 10.1109/MM.2018.112130359](https://doi.org/10.1109/MM.2018.112130359) — Intel Loihi paper; relevant if hardware is the deployment target.
- Maass, W. (1997). "Networks of Spiking Neurons: The Third Generation of Neural Network Models." *Neural Networks* 10(9), 1659-1671. [DOI: 10.1016/S0893-6080(97)00011-7](https://doi.org/10.1016/S0893-6080(97)00011-7) — the theoretical motivation for SNNs; "third generation" framing.
- Wu, Y., Deng, L., Li, G., Zhu, J., & Shi, L. (2018). "Spatio-Temporal Backpropagation for Training High-Performance Spiking Neural Networks." *Frontiers in Neuroscience* 12, 331. [DOI: 10.3389/fnins.2018.00331](https://doi.org/10.3389/fnins.2018.00331) — STBP; the BPTT-over-spikes training algorithm both libraries implement.

### Tutorials & write-ups
- [snntorch tutorial series (5-part)](https://snntorch.readthedocs.io/en/latest/tutorials/index.html) — covers spike encoding, LIF, surrogate gradients, regression, CNN
- [Friedemann Zenke "spytorch" tutorial](https://github.com/fzenke/spytorch) — the original surrogate-gradient pedagogical reference; smaller and more focused than snntorch's tutorials
- [Norse "From DNN to SNN" tutorial](https://norse.github.io/norse/auto_examples/index.html) — converting a trained dense net into an equivalent SNN; useful when SNN training from scratch fails

### Standard datasets / benchmarks
- [NMNIST (Neuromorphic MNIST)](https://www.garrickorchard.com/datasets/n-mnist) — MNIST converted to event streams via saccadic camera; the "Hello, World" of neuromorphic vision
- [DVS Gesture](https://research.ibm.com/interactive/dvsgesture/) — IBM gesture recognition; standard event-camera benchmark
- [SHD (Spiking Heidelberg Digits)](https://compneuro.net/datasets/) — speech-to-spike benchmark; the audio analog of NMNIST
- [N-Caltech101](https://www.garrickorchard.com/datasets/n-caltech101) — Caltech-101 converted to event stream
- For finance: no canonical SNN dataset exists; rate-encode OHLCV windows or use trade-arrival timestamps directly as event streams

### Last cross-checked
2026-05-20 — via Context7 `/jeshraghian/snntorch` (1618 snippets, High, benchmark 84.7) + WebSearch verification of all paper DOIs/arXiv IDs.
