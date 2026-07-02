---
name: spiking-neural-network
version: 0.1.0
description: Spiking neural networks (SNNs) for low-power and event-driven price prediction. Wraps the norse PyTorch SNN library (LIF/LIFParameters, lif_step, decode) for a minimal LIF pipeline on a synthetic signal, with snntorch noted as an alternative API. Covers rate vs. latency encoding, time-step choice, and surrogate-gradient training. Not for accuracy-maximizing tasks without hardware/event constraints—use standard CNNs or LSTMs if inference cost is not a concern.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: Apache-2.0 (norse upstream), MIT (snntorch upstream)
metadata:
    skill-author: HyperFrequency
    skill-domain: deep-learning / quant
---

# Spiking Neural Network

A router for building event-driven, low-power SNN models for tick / quote / micro-structure
data. Read this page to decide *whether* an SNN fits and *which* library to use, then jump to
the reference file for the detail you need.

## When to use

Use this skill when you want an event-driven, low-power-friendly model:

- The compute target is neuromorphic hardware (Intel Loihi, SpiNNaker, Akida) — SNNs are native there.
- The input is already event-like (level-1 quote updates, trade arrivals) and you want a model that
  consumes asynchronous events instead of resampling to a fixed grid.
- You're researching ultra-low-power inference for an embedded execution box.
- You want a bio-inspired baseline to compare against a standard CNN/RNN on the same prediction task.

Do **not** use an SNN if you just want best accuracy. On most quant tasks, a small Conv1D or LSTM
will outperform a similarly-sized SNN; SNNs win on energy/inference cost on the right hardware, not
on raw accuracy. For a standard model, reach for the sibling `pytorch-lightning` / `transformers`
skills instead. To port a strategy between frameworks, use `strategy-translator`.

## Two libraries

1. **norse** (`https://github.com/norse/norse`) — PyTorch-first, exposes `lif_step` / `LIFCell` /
   `LIFParameters`. Functional and modular: easy to compose with `torch.nn`. Preferred when you want
   SNN primitives that drop into a standard PyTorch graph.
2. **snntorch** (`https://github.com/jeshraghian/snntorch`) — Also PyTorch, slightly higher-level.
   Exposes `snn.Leaky` neurons that act like `nn.Module`s. Friendlier surrogate-gradient API
   (`surrogate.fast_sigmoid()`, `surrogate.atan()`). Good alternative if you prefer object-oriented
   neuron layers and bundled tutorials.

## Mental model in one paragraph

An SNN replaces real-valued activations with binary spikes emitted over `T` discrete time steps.
You **encode** a real-valued input window into spike trains (rate-encoding by default), **unroll** a
small LIF network over those `T` steps threading neuron state forward, and **decode** by averaging /
counting the output over time. Because the spike (Heaviside) is non-differentiable, training uses a
**surrogate gradient** (`fast_sigmoid(slope=25)`) so standard BPTT/autograd works. The payoff is
1-bit activations and graceful quantisation — i.e. energy efficiency on neuromorphic hardware — not
better accuracy.

## Reference files

- **`references/examples.md`** — install/setup, GPU notes, and two runnable minimal pipelines (norse
  functional LIF ≤60 lines; snntorch ≤15 lines). Start here to get something training.
- **`references/api-and-tuning.md`** — norse + snntorch API tables, architecture choices (`T`, `beta`,
  `v_th`, surrogate, depth, readout), common pitfalls, encoding schemes (rate / latency / population),
  production scaling, and a step-by-step diagnostics checklist for when training stalls.
- **`references/further-reading.md`** — upstream docs, adjacent libraries (Brian2, BindsNET, Nengo,
  Lava, Spyx), foundational papers, neuromorphic datasets, and last cross-check provenance.
