---
name: pennylane
version: 0.1.0
description: >-
  Differentiable quantum programming for hybrid quantum-classical machine learning with PennyLane.
  Use to build parameterized quantum circuits (QNodes), differentiate them via backprop /
  parameter-shift / adjoint, train variational algorithms (VQE, QAOA, quantum classifiers), run
  quantum chemistry (molecular Hamiltonians, UCCSD), and stay hardware-agnostic across simulators
  (default.qubit, lightning.qubit) and IBM / AWS Braket / IonQ / Rigetti backends with PyTorch,
  JAX, or TensorFlow interfaces. Reach for it when you need automatic differentiation of quantum
  circuits, gradient-based training of circuit parameters, or a portable device layer. NOT for
  vendor-specific circuit transpilation/pulse compilation (use `qiskit` for IBM, `cirq` for
  Google), open-system master-equation dynamics without ML (use `qutip`), or classical-only ML.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: Apache-2.0 (PennyLane, PennyLaneAI/pennylane)
---

# PennyLane

## Overview

PennyLane treats a quantum circuit as a differentiable function. You wrap a Python function of
quantum gates in a `QNode` bound to a device; PennyLane then computes gradients of its
measurement outputs with respect to circuit parameters, so you can train circuits with the same
optimizers you use for neural networks. The circuit is written once and runs unchanged on a
state-vector simulator or on real quantum hardware — the device is swapped, not the code.

The core object is the QNode:

```python
import pennylane as qml
from pennylane import numpy as np

dev = qml.device("default.qubit", wires=2)   # simulator with 2 qubits

@qml.qnode(dev)
def circuit(params):
    qml.RX(params[0], wires=0)
    qml.RY(params[1], wires=1)
    qml.CNOT(wires=[0, 1])
    return qml.expval(qml.PauliZ(0))          # a differentiable scalar

opt = qml.GradientDescentOptimizer(stepsize=0.1)
params = np.array([0.1, 0.2], requires_grad=True)
for _ in range(100):
    params = opt.step(circuit, params)
```

Everything else — encodings, ansatze, chemistry, QAOA, framework interop — is built on that
loop. This file is a router; each capability links to a reference with the concrete APIs.

## When to Use This Skill

- You need to **train quantum circuit parameters by gradient descent** (variational circuits).
- You are building a **hybrid model** that mixes classical PyTorch/JAX/TensorFlow layers with a
  quantum layer and want end-to-end autodiff.
- You want **device portability**: prototype on a simulator, then run the same circuit on
  IBM/IonQ/Rigetti/Braket hardware.
- You are running **variational algorithms** — VQE for ground-state energy, QAOA for
  combinatorial optimization, quantum classifiers/kernels.
- You need **quantum chemistry** primitives (molecular Hamiltonians, Hartree-Fock states, UCCSD).
- You need circuit **gradients on hardware**, where backprop is unavailable and parameter-shift
  is required.

## When NOT to Use This Skill

- **Vendor-specific compilation, transpilation, or pulse-level scheduling** for a single
  backend — use `qiskit` (IBM) or `cirq` (Google) directly; PennyLane abstracts these away.
- **Open quantum systems / Lindblad master-equation dynamics** studied for physics rather than
  ML — use `qutip`. PennyLane's `default.mixed` handles noise channels but is not a dynamics
  solver.
- **Classical machine learning** with no quantum component — use `scikit-learn`, `pytorch`, etc.
- **Fault-tolerant / large-scale circuits** you expect to simulate exactly beyond ~30 qubits —
  state-vector cost is exponential; see `references/devices.md` for limits and Clifford/tensor
  alternatives.

## Installation

```bash
uv pip install pennylane                       # core + default.qubit / lightning.qubit
uv pip install pennylane-qiskit                # IBM Quantum backends
uv pip install amazon-braket-pennylane-plugin  # AWS Braket (IonQ, Rigetti, simulators)
uv pip install pennylane-cirq                  # Google Cirq / qsim
uv pip install pennylane-ionq                  # IonQ direct
uv pip install pennylane-catalyst              # qjit AOT/JIT compilation
```

Plugin device strings and required credentials are version-sensitive; confirm exact names
against the installed plugin's docs (see `references/devices.md`).

## Core Capabilities

Each section is a pointer to a reference file with verified APIs, parameters, and worked examples.

### 1. Circuit construction and measurement
Gates, controlled/conditional ops, state preparation, data encodings, mid-circuit measurement,
and inspection (`qml.draw`, `qml.specs`). See `references/circuits.md`.

### 2. Optimization and gradients
Built-in optimizers (Adam, QNG, Rotosolve, SPSA), differentiation methods
(`backprop` / `parameter-shift` / `adjoint` / `finite-diff`), VQE, QAOA, and barren-plateau
mitigation. See `references/optimization.md`.

### 3. Quantum machine learning
Interfaces (`torch` / `jax` / `tf`), embedding a QNode as a layer via `qml.qnn.TorchLayer` and
`qml.qnn.KerasLayer`, variational classifiers, encodings, and transfer learning. See
`references/quantum_ml.md`.

### 4. Quantum chemistry
`qml.qchem.molecular_hamiltonian`, Hartree-Fock states, UCCSD ansatz, fermion-to-qubit mappings,
active spaces, dissociation curves, and molecular properties. See `references/quantum_chemistry.md`.

### 5. Devices and backends
Simulator selection (`default.qubit`, `lightning.qubit`, `default.mixed`, `default.clifford`,
`lightning.gpu`), shots vs. analytic mode, hardware plugins, and Catalyst `qjit`. See
`references/devices.md`.

### 6. Advanced features
Templates (`StronglyEntanglingLayers`, embeddings), transforms (`cancel_inverses`,
`merge_rotations`, `metric_tensor`), noise channels, pulse programming, and resource estimation.
See `references/advanced.md`.

## Common Workflows

**Train a variational classifier** — encode features with `AngleEmbedding`, stack
`StronglyEntanglingLayers`, measure `PauliZ`, minimize a loss with `AdamOptimizer`. Full example
in `references/quantum_ml.md`.

**Find a molecular ground state (VQE)** — build the Hamiltonian, prepare the Hartree-Fock state,
apply UCCSD, and minimize `qml.expval(H)` with `step_and_cost`. Full example in
`references/quantum_chemistry.md`.

**Solve MaxCut (QAOA)** — build cost/mixer Hamiltonians with `qml.qaoa`, alternate cost and mixer
layers, optimize the angles. Full example in `references/optimization.md`.

**Swap simulator for hardware** — keep the QNode function; construct a new device
(`qml.device("qiskit.remote", ...)`) and re-bind. Switch `diff_method` to `parameter-shift`
because backprop is simulator-only. See `references/devices.md`.

## Key Gotchas

- **Backprop is simulator-only.** On real hardware (or shot-based devices) use
  `diff_method="parameter-shift"` (or `adjoint` on state-vector simulators). Choosing backprop on
  hardware fails or silently falls back.
- **Match the trainable array to the interface.** With the autograd interface use
  `pennylane.numpy` with `requires_grad=True`; with torch/jax/tf, make the parameters tensors of
  that framework so gradients flow. Mixing plain NumPy arrays breaks differentiation.
- **Barren plateaus.** Deep, randomly-initialized circuits have exponentially vanishing
  gradients. Initialize small, keep circuits shallow, or use problem-tailored ansatze. See
  `references/optimization.md`.
- **Legacy device names.** Modern `default.qubit` auto-detects the interface; the old
  `default.qubit.torch/tf/jax` variants and `qiskit.ibmq` are deprecated. Prefer the unified
  device plus a per-QNode `interface=`, and check plugin docs for current backend strings.
- **Simulation cost is exponential.** A 30-qubit state vector is ~16 GB (complex128). Use
  `lightning.qubit`/`lightning.gpu` for speed, `default.clifford` for Clifford-only circuits.

## Resources

- Documentation: https://docs.pennylane.ai
- Tutorials (Codebook): https://pennylane.ai/codebook
- Demonstrations: https://pennylane.ai/qml/demonstrations
- Source: https://github.com/PennyLaneAI/pennylane
