---
name: qiskit
version: 0.1.0
description: >-
  Qiskit is IBM's open-source Python SDK for quantum computing: build circuits
  from gates, transpile them to a device's native gate set and connectivity, and
  execute on local simulators or IBM Quantum hardware through Runtime primitives.
  Use it to construct and parameterize `QuantumCircuit`s; run a Sampler (bitstring
  distributions) or an Estimator (expectation values of Pauli observables);
  transpile with optimization levels, coupling maps, and preset pass managers to
  ISA circuits; run on IBM backends with Sessions (iterative) or Batch (parallel)
  and resilience-level error mitigation; and implement VQE, QAOA, Grover, quantum
  chemistry (Qiskit Nature) and QML (Qiskit ML). Follow the Map -> Optimize ->
  Execute -> Post-process pattern. NOT for Google/AWS hardware via Cirq (use
  `cirq`), autodiff/gradient-based quantum ML (use `pennylane`), open-quantum-
  system master-equation simulation (use `qutip`), or classical ML/linear algebra.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Qiskit (Apache-2.0)"
---

# Qiskit

## Overview

Qiskit is a Python SDK for gate-model quantum computing. You describe an
algorithm as a `QuantumCircuit`, **transpile** it into an ISA (Instruction Set
Architecture) circuit that respects a target device's native gates and qubit
connectivity, then **execute** it with a *primitive* — a `Sampler` for
measurement bitstrings or an `Estimator` for expectation values of observables.
The same code runs on a local simulator or on real IBM Quantum hardware via
Qiskit Runtime; only the primitive's backend changes.

This skill is a **router**. It gives the mental model, an install and quick-start
path, a capability map, and the failure modes that bite in practice, then
delegates the deep API surface, gate tables, and worked algorithms to
`references/`. Read the matching reference before writing nontrivial code.

The whole workflow reduces to four stages (**Qiskit Patterns**):

```
Problem -> [Map] -> [Optimize] -> [Execute] -> [Post-process] -> Solution
          circuits   transpile     primitives   classical analysis
          + operators to ISA
```

## When to Use This Skill

- Build, parameterize, or compose **quantum circuits** and gates.
- Run a **Sampler** (bitstring counts / probabilities) or an **Estimator**
  (expectation value of a `SparsePauliOp`) on a simulator or hardware.
- **Transpile** a circuit for a device — optimization levels 0-3, custom
  coupling maps, initial layout, basis-gate translation, preset pass managers.
- Execute on **IBM Quantum hardware** with Runtime primitives, using Sessions
  for iterative variational loops or Batch for independent parallel jobs.
- Apply **error mitigation** (readout, ZNE, PEC) via resilience levels.
- Implement variational and search algorithms — **VQE, QAOA, Grover** — or use
  the domain packages **Qiskit Nature** (chemistry), **Qiskit Machine Learning**,
  and **Qiskit Optimization**.
- **Visualize** circuits, measurement histograms, and quantum states
  (Bloch sphere, state city, QSphere).

## When NOT to Use This Skill

- Targeting **Google or AWS Braket hardware through Cirq**, or you want Cirq's
  moment/scheduling model -> use `cirq`.
- Doing **gradient-based / autodifferentiable quantum ML** where you need
  parameter-shift or backprop through circuits into a PyTorch/JAX graph -> use
  `pennylane`.
- Simulating **open quantum systems** — Lindblad / master-equation dynamics,
  decoherence, steady states of noisy Hamiltonians -> use `qutip`.
- Plain **classical** machine learning, linear algebra, or plotting — quantum
  primitives add nothing; use the relevant classical tool (e.g. `scikit-learn`,
  `matplotlib`).

## Install and Authenticate

```bash
uv pip install qiskit qiskit-ibm-runtime
uv pip install "qiskit[visualization]" qiskit-aer   # plots + fast local simulator
```

You need **no account** to build circuits and run local simulators. To reach IBM
hardware, save credentials once (the current IBM Quantum Platform channel is
`ibm_quantum_platform`; the legacy `ibm_quantum` channel was retired in 2025):

```python
from qiskit_ibm_runtime import QiskitRuntimeService
QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform",
    token="<API_KEY>",
    instance="<CRN-or-instance>",
    overwrite=True,
)
```

Full account, environment-variable, and provider details: `references/setup-and-backends.md`.

## Quick Start — Bell state on a local simulator

```python
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

qc = QuantumCircuit(2)
qc.h(0)            # superposition on qubit 0
qc.cx(0, 1)        # entangle qubits 0 and 1
qc.measure_all()

sampler = StatevectorSampler()
result = sampler.run([qc], shots=1024).result()
counts = result[0].data.meas.get_counts()   # ~ {'00': 512, '11': 512}
```

## Capability Map

| You want to...                                             | Read                                  |
| ---------------------------------------------------------- | ------------------------------------- |
| Install, authenticate, pick/inspect a backend, run Aer, use IonQ/Braket, manage jobs, Sessions/Batch, error mitigation | `references/setup-and-backends.md`    |
| Build circuits: gates, measurements, composition, parameters | `references/circuits.md`             |
| Run Sampler/Estimator (V2), bind parameters, read results  | `references/primitives.md`            |
| Transpile: optimization levels, pass managers, layout, ISA | `references/transpilation.md`         |
| Full Map->Optimize->Execute->Post-process recipes + VQE/QAOA/Grover, chemistry, QML, optimization | `references/patterns-and-algorithms.md` |
| Draw circuits, plot histograms, visualize states           | `references/visualization.md`         |

## Critical Gotchas

These are the mistakes that produce silent wrong results, not just errors:

- **Transpile before running on hardware.** A raw circuit uses abstract gates and
  all-to-all connectivity that no device has. Always produce an ISA circuit first
  (see `references/transpilation.md`). Runtime primitives reject non-ISA circuits.
- **Match observables to the ISA layout.** With `EstimatorV2`, after transpiling
  the circuit you must map the observable onto the same physical qubits:
  `isa_obs = observable.apply_layout(isa_circuit.layout)`. Skipping this measures
  the wrong qubits and returns a plausible-looking but wrong expectation value.
- **V2 result access differs from V1.** Read Sampler counts via
  `result[0].data.<creg>.get_counts()` (the classical register is named `meas`
  after `measure_all()`), and Estimator values via `result[0].data.evs`. The old
  `.quasi_dists` / `.values` V1 paths are gone.
- **Estimator circuits must not contain measurements**; the observable defines what
  is measured. Sampler circuits **must** contain measurements.
- **Choose the execution mode deliberately:** Session for iterative loops (VQE,
  QAOA) to hold the backend between jobs, Batch for many independent circuits,
  a single job for one-off runs.

## References

- `references/setup-and-backends.md` — installation, IBM auth, backend selection and properties, Aer + GPU simulation, third-party providers, job management, Session/Batch, error mitigation.
- `references/circuits.md` — gate catalog, measurements, barriers, composition, circuit properties, parameterized and templated circuits.
- `references/primitives.md` — Sampler and Estimator V2, local vs Runtime primitives, parameter binding, result and metadata processing.
- `references/transpilation.md` — why/how transpilation works, optimization levels, the six stages, preset pass managers, layout and basis-gate control, analysis.
- `references/patterns-and-algorithms.md` — the four-step pattern end to end, VQE/QAOA/Grover, Qiskit Nature chemistry, Qiskit ML, Qiskit Optimization, time evolution.
- `references/visualization.md` — circuit drawings (text/mpl/latex), histograms, Bloch/state-city/QSphere, gate/error maps, publication styling.
