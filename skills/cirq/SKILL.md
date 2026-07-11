---
name: cirq
version: 0.1.0
description: >-
  Google Quantum AI's Cirq framework for designing, simulating, transforming, and
  running gate-level quantum circuits in Python. Use when you build explicit
  qubit-and-gate circuits, target Google / IonQ / AQT / Pasqal / Azure hardware,
  model device noise with density-matrix or Clifford simulators, compile circuits
  to a hardware-native gateset, or run characterization and variational experiments
  (randomized benchmarking, XEB, VQE, QAOA, QPE). Not for IBM-centric workflows or
  Qiskit Runtime (use `qiskit`), autodiff-based quantum machine learning (use
  `pennylane`), open-system Hamiltonian / master-equation physics without circuits
  (use `qutip`), or purely classical ML.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: Apache-2.0
---

# Cirq

## Overview

Cirq is Google Quantum AI's open-source Python library for writing quantum
programs at the level of individual qubits and gates. You describe a `Circuit`
as a sequence of `Moment`s (columns of simultaneous operations), then run it on a
local simulator or submit it to real hardware. Cirq's distinguishing strengths
are its explicit device / topology model, first-class noise channels with a
density-matrix simulator, a composable transformer framework for compiling to a
hardware gateset, and tight integration with Google Quantum AI processors.

This skill routes you to focused references for each subsystem. Read the router,
then open the reference for the task at hand — do not load everything up front.

## When to Use This Skill

- Building explicit gate-level circuits (Hadamards, CNOTs, rotations, custom
  unitaries, qudits) where you control the exact operations and their timing.
- Targeting Google Quantum AI (`cirq-google`), IonQ, AQT, Pasqal, or Azure
  Quantum hardware, including qubit selection from calibration data.
- Modelling realistic noise — depolarizing, amplitude/phase damping, thermal,
  readout — and simulating it with the density-matrix simulator.
- Compiling / optimizing a circuit to a device's native gateset and connectivity
  (gate merging, Z-ejection, routing, SWAP insertion).
- Running characterization (randomized benchmarking, cross-entropy benchmarking)
  or variational algorithms (VQE, QAOA, QPE) with parameter sweeps.

## When NOT to Use This Skill

- IBM Quantum hardware, Qiskit Runtime primitives, or Qiskit's transpiler — use
  `qiskit`.
- Differentiable/autodiff quantum machine learning where gradients flow through a
  PyTorch/TensorFlow/JAX layer — use `pennylane`.
- Open-system dynamics, Lindblad master equations, or continuous-time Hamiltonian
  evolution that is not expressed as a gate circuit — use `qutip`.
- Purely classical ML, optimization, or data analysis — no quantum layer needed.

## Installation

```bash
uv pip install cirq                 # core + local simulators
uv pip install cirq-google          # Google Quantum Engine
uv pip install cirq-ionq            # IonQ trapped-ion
uv pip install cirq-aqt             # Alpine Quantum Technologies
uv pip install cirq-pasqal          # Pasqal neutral atoms
uv pip install azure-quantum cirq   # Azure Quantum (IonQ / Quantinuum backends)
```

## Quick Start

```python
import cirq

q0, q1 = cirq.LineQubit.range(2)
bell = cirq.Circuit(
    cirq.H(q0),                       # superposition
    cirq.CNOT(q0, q1),                # entangle
    cirq.measure(q0, q1, key="result"),
)

result = cirq.Simulator().run(bell, repetitions=1000)
print(result.histogram(key="result"))   # ~50/50 between 0 (00) and 3 (11)
```

Parameterized circuits use `sympy` symbols and a sweep object instead of many
individual runs:

```python
import sympy, numpy as np

theta = sympy.Symbol("theta")
circuit = cirq.Circuit(cirq.ry(theta)(q0), cirq.measure(q0, key="m"))
sweep = cirq.Linspace("theta", start=0, stop=2 * np.pi, length=20)
for params, res in zip(sweep, cirq.Simulator().run_sweep(circuit, sweep, repetitions=1000)):
    print(params["theta"], res.histogram(key="m"))
```

## Capabilities

Each area has a dedicated reference. Open the one you need:

- **Build circuits** — qubit types (`GridQubit`, `LineQubit`, `NamedQubit`,
  `LineQid`), gate zoo, parameterization, custom gates and decomposition,
  moments, QASM/JSON I/O, Pauli observables. See
  [references/building.md](references/building.md).
- **Simulate** — state-vector vs density-matrix vs Clifford simulators, sampling,
  expectation values, parameter sweeps (`Linspace`, `Product`, `Zip`), custom
  initial states, moment-by-moment stepping, memory limits. See
  [references/simulation.md](references/simulation.md).
- **Transform / compile** — the transformer framework, gate merging, Z/phase
  ejection, `optimize_for_target_gateset`, KAK-based two-qubit compilation,
  routing to device connectivity, custom transformers and pipelines. See
  [references/transformation.md](references/transformation.md).
- **Run on hardware** — device metadata and validation, calibration-driven qubit
  selection, provider setup (Google, IonQ, Azure, AQT, Pasqal), job management,
  batching, hardware-aware optimization. See
  [references/hardware.md](references/hardware.md).
- **Model noise** — noise channels, constant/gate-specific/qubit-specific/thermal
  noise models, readout error, RB and XEB characterization, zero-noise
  extrapolation and readout mitigation, hardware noise from calibration. See
  [references/noise.md](references/noise.md).
- **Run experiments** — experiment structure, task-based and parallel data
  collection, VQE/QAOA/QPE templates, statistical analysis and fidelity. See
  [references/experiments.md](references/experiments.md).

## Choosing a Simulator

| Situation | Simulator | Cost |
| --- | --- | --- |
| Pure state, no noise | `cirq.Simulator()` (state vector) | `O(2^n)` memory |
| Mixed state / any noise channel | `cirq.DensityMatrixSimulator()` | `O(2^{2n})` memory |
| Only Clifford gates (H, S, CNOT, Pauli) | `cirq.CliffordSimulator()` | polynomial |

State-vector memory is `2^n * 16` bytes (complex128): ~16 MB at 20 qubits,
~16 GB at 30. Density-matrix squares that, so it caps out near ~12-14 qubits.
Reach for the density-matrix simulator only when you actually need mixed states.

## Common Pitfalls

- **Noise silently ignored.** `cirq.Simulator()` cannot represent mixed states;
  noise channels only take effect under `DensityMatrixSimulator` (or a stochastic
  trajectory simulator). See [references/noise.md](references/noise.md).
- **Device validation errors.** A circuit that runs in simulation may violate a
  device's gateset or connectivity. Inspect `device.metadata.nx_graph`, compile
  with `optimize_for_target_gateset`, then call `device.validate_circuit(...)`
  before submitting. See [references/hardware.md](references/hardware.md).
- **Circuit too deep for hardware.** Merge single-qubit gates, eject Z gates, and
  drop negligible operations to cut depth. See
  [references/transformation.md](references/transformation.md).
- **Histogram keys are integers.** `result.histogram(key=...)` returns the
  measured multi-qubit value as a single integer (big-endian over the measured
  qubits), not a bitstring — decode bits yourself when needed.
- **Symbols left unresolved.** A circuit containing `sympy` symbols must be run
  through a sweep or `cirq.resolve_parameters(...)` before `simulate`/`run`.

## Additional Resources

- Official docs: https://quantumai.google/cirq
- API reference: https://quantumai.google/reference/python/cirq
- ReCirq (research experiments): https://github.com/quantumlib/ReCirq
