# Devices and Backends

A device is the execution target of a QNode. The same circuit runs on any device — swap the
device, keep the code. Device strings and constructor kwargs for hardware plugins are
version-sensitive; always confirm against the installed plugin's docs.

## Built-in simulators

| Device            | Kind                | Notes |
|-------------------|---------------------|-------|
| `default.qubit`   | state vector        | General purpose, pure Python; auto-detects torch/jax/tf interface. |
| `lightning.qubit` | state vector (C++)  | Faster; preferred for larger circuits; supports `adjoint`. |
| `lightning.gpu`   | state vector (GPU)  | CUDA-accelerated for large circuits (requires GPU + install). |
| `default.mixed`   | density matrix      | Supports noise channels; heavier (tracks a density matrix). |
| `default.clifford`| stabilizer          | Only Clifford gates (H, S, CNOT, ...); scales to 100s of qubits. |

```python
dev = qml.device("default.qubit", wires=4)                # analytic
dev = qml.device("default.qubit", wires=4, shots=1000)    # sampling
dev = qml.device("default.qubit", wires=["a", "b"])       # named wires
dev = qml.device("lightning.qubit", wires=24)             # fast simulator
```

Legacy note: the old `default.qubit.torch` / `.tf` / `.jax` device variants are deprecated. Use
the unified `default.qubit` and set `interface=` on the QNode (or let it auto-detect).

## Differentiation × device pairing

- Simulator + `backprop` or `adjoint` — fastest exact gradients.
- Hardware or shot-based device + `parameter-shift` (or `spsa` for many parameters).
- Choosing `backprop` on hardware fails or silently degrades — see `references/optimization.md`.

## Shots vs. analytic mode

```python
dev = qml.device("default.qubit", wires=2)               # analytic (exact expectations)

@qml.qnode(dev)
def circuit(x):
    qml.RX(x, wires=0)
    return qml.expval(qml.PauliZ(0))

circuit(0.5)                    # exact
circuit(0.5, shots=1000)        # estimate from 1000 samples (override per call)
```

Analytic mode gives exact expectation values (simulator only). Set `shots` to mimic hardware
sampling noise; `qml.sample`/`qml.counts` require shots. Use `seed=` on the device for
reproducible sampling.

## Hardware plugins (device strings vary by plugin version)

```python
# IBM Quantum (pennylane-qiskit). qiskit.ibmq is deprecated; modern route:
dev = qml.device("qiskit.remote", wires=5, backend=backend)   # backend from qiskit-ibm-runtime
dev = qml.device("qiskit.aer", wires=2)                        # local Aer simulator

# AWS Braket (amazon-braket-pennylane-plugin)
dev = qml.device("braket.local.qubit", wires=2)
dev = qml.device("braket.aws.qubit", wires=4,
                 device_arn="arn:aws:braket:::device/quantum-simulator/amazon/sv1")

# Google Cirq (pennylane-cirq)
dev = qml.device("cirq.simulator", wires=2)
dev = qml.device("cirq.qsim", wires=20)

# IonQ (pennylane-ionq) — needs an API key
dev = qml.device("ionq.simulator", wires=11, shots=1024)   # or "ionq.qpu"
```

Credentials are supplied via plugin-specific kwargs or environment variables; never hard-code API
tokens in source. Consult the plugin docs for the exact backend names available to your account.

## Choosing a device

```python
def select_device(n_qubits, use_hardware=False, noisy=False):
    if use_hardware:
        return qml.device("qiskit.remote", wires=n_qubits, backend=backend, shots=1024)
    if noisy:
        return qml.device("default.mixed", wires=n_qubits)
    if n_qubits <= 26:
        return qml.device("lightning.qubit", wires=n_qubits)
    return qml.device("default.qubit", wires=n_qubits)
```

## Performance

- **Reuse device objects** across QNodes to avoid re-initialization overhead.
- **Parameter broadcasting**: pass a leading batch dimension in the parameters and the device
  vectorizes execution — far faster than a Python loop over samples.
- **Catalyst `qjit`** compiles a QNode (and its classical control flow) ahead of time:

```python
from catalyst import qjit  # or use qml.qjit

dev = qml.device("lightning.qubit", wires=4)

@qjit
@qml.qnode(dev)
def compiled(x):
    qml.RX(x, wires=0)
    qml.Hadamard(wires=1)
    qml.CNOT(wires=[0, 1])
    return qml.expval(qml.PauliZ(0))

compiled(0.5)                       # first call compiles; later calls are fast
grad = qjit(qml.grad(compiled))     # compiled gradient
```

Compiled circuits can use `qml.for_loop` / `qml.while_loop` for control flow that stays on-device
rather than being Python-unrolled.

## Cost limits

A pure state vector needs `2**n_qubits * 16` bytes (complex128): ~16 GB at 30 qubits, ~256 GB at
34. Beyond that, exact state-vector simulation is infeasible — use `default.clifford` for Clifford
circuits, `lightning.gpu` for a speed bump, or reduce qubits via active spaces
(`references/quantum_chemistry.md`). Density-matrix simulation (`default.mixed`) roughly squares
the memory cost, so keep noisy circuits small.

## Practices

1. Prototype on `default.qubit`/`lightning.qubit`; validate before hardware.
2. Switch `diff_method` to `parameter-shift` when moving to hardware or shots.
3. Cache devices; broadcast parameters instead of looping.
4. Set `seed=` for reproducible sampling; track shot counts and hardware cost.
