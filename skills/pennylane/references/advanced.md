# Advanced Features

Templates, circuit transforms, noise modeling, pulse-level control, and resource estimation.

## Templates and layers

Templates are pre-built, correctly-shaped circuit blocks. Ask a template for its expected weight
shape rather than guessing.

```python
import pennylane as qml
from pennylane import numpy as np

dev = qml.device("default.qubit", wires=4)

# Strongly entangling layers (rotations + a ring of controlled gates)
shape = qml.StronglyEntanglingLayers.shape(n_layers=3, n_wires=4)   # -> (3, 4, 3)
weights = np.random.random(shape, requires_grad=True)

@qml.qnode(dev)
def circuit(weights):
    qml.StronglyEntanglingLayers(weights, wires=range(4))
    return qml.expval(qml.PauliZ(0))
```

Other useful templates:

- `qml.BasicEntanglerLayers(weights, wires)` — single rotation per wire + CNOT ring; shape
  `(n_layers, n_wires)`.
- `qml.RandomLayers(weights, wires)` — randomly placed gates (baseline/expressivity studies).
- `qml.SimplifiedTwoDesign(initial_layer_weights, weights, wires)` — 2-design-like ansatz.
- `qml.ParticleConservingU1(weights, wires, init_state=...)` — preserves particle number
  (chemistry).
- Embeddings: `AngleEmbedding`, `AmplitudeEmbedding`, `BasisEmbedding`, `IQPEmbedding`
  (see `references/circuits.md`).

Define your own by writing a plain function of `(weights, wires)` and calling it inside a QNode.

## Transforms

Transforms rewrite or analyze circuits. Apply as decorators above the QNode.

```python
@qml.transforms.cancel_inverses     # remove adjacent inverse gates (e.g. H·H)
@qml.qnode(dev)
def c1(): ...

@qml.transforms.merge_rotations     # fuse RX(a)·RX(b) -> RX(a+b)
@qml.qnode(dev)
def c2(): ...

@qml.transforms.commute_controlled  # push single-qubit gates through controls
@qml.qnode(dev)
def c3(): ...
```

**Metric tensor** (quantum geometric tensor) — needed for quantum natural gradient:

```python
mt = qml.metric_tensor(circuit)(params)
```

**Decomposition** into a target gate set is available via `qml.transforms.decompose` (exact API
and `gate_set=` form vary by version — check the installed docs before relying on it).

## Noise modeling

Use `default.mixed` and insert noise channels between gates:

```python
dev = qml.device("default.mixed", wires=2)

@qml.qnode(dev)
def noisy():
    qml.Hadamard(wires=0)
    qml.DepolarizingChannel(0.1, wires=0)   # depolarizing
    qml.CNOT(wires=[0, 1])
    qml.AmplitudeDamping(0.05, wires=0)     # energy relaxation (T1)
    qml.PhaseDamping(0.05, wires=1)         # dephasing (T2)
    qml.BitFlip(0.01, wires=0)
    qml.PhaseFlip(0.01, wires=1)
    return qml.expval(qml.PauliZ(0))
```

Custom channels via Kraus operators:

```python
def depolarizing_kraus(p):
    K0 = np.sqrt(1 - p) * np.eye(2)
    K1 = np.sqrt(p / 3) * np.array([[0, 1], [1, 0]])       # X
    K2 = np.sqrt(p / 3) * np.array([[0, -1j], [1j, 0]])    # Y
    K3 = np.sqrt(p / 3) * np.array([[1, 0], [0, -1]])      # Z
    return [K0, K1, K2, K3]

qml.QubitChannel(depolarizing_kraus(0.1), wires=0)
```

PennyLane also has a higher-level `qml.NoiseModel` for attaching noise to gate types
programmatically; consult the docs for the current constructor.

## Pulse programming

`qml.pulse` expresses time-dependent Hamiltonian evolution for hardware close to the metal
(analog control). Build a parameterized Hamiltonian with time-dependent coefficients and evolve
it with `qml.evolve`. The exact `qml.pulse` API (constant/`rect`/callable envelopes,
`ParametrizedHamiltonian`) is subsystem-specific and version-sensitive — treat pulse-level work as
an advanced, docs-driven task rather than copy-paste.

## Resource estimation

```python
specs = qml.specs(circuit)(params)
# dict-like summary: gate counts/types, circuit depth, wire count, num_trainable_params
print(specs)
```

`qml.specs` is the reliable way to profile gate counts and depth before running on hardware.
Print the result to see the current schema; key names have changed across versions, so avoid
hard-coding them. For back-of-envelope simulation cost, a state vector is `2**n_qubits * 16` bytes
(complex128) — see `references/devices.md`.

## Practices

1. Reach for templates first; use `Template.shape(...)` to size weights correctly.
2. Apply `cancel_inverses` / `merge_rotations` before hardware execution to cut depth.
3. Model noise on `default.mixed` when studying hardware behavior; keep such circuits small.
4. Profile with `qml.specs` before submitting to a real device.
5. Treat pulse control and version-specific transform/noise APIs as docs-driven — verify
   signatures against the installed PennyLane version.
