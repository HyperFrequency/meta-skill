# Circuit Construction and Measurement

Gates, state preparation, measurements, data encodings, dynamic circuits, and inspection. All
gates are queued inside a `QNode` (a function decorated with `@qml.qnode(dev)`); the return value
is one or more measurement processes.

## Single-qubit gates

```python
qml.PauliX(wires=0); qml.PauliY(wires=0); qml.PauliZ(wires=0)
qml.Hadamard(wires=0)
qml.S(wires=0); qml.T(wires=0)
qml.PhaseShift(phi, wires=0)
qml.RX(theta, wires=0); qml.RY(theta, wires=0); qml.RZ(theta, wires=0)  # parameterized
qml.Rot(phi, theta, omega, wires=0)   # ZYZ Euler rotation
qml.U3(theta, phi, delta, wires=0)    # general single-qubit unitary
```

## Multi-qubit gates

```python
qml.CNOT(wires=[0, 1])           # control=0, target=1
qml.CZ(wires=[0, 1])
qml.SWAP(wires=[0, 1])
qml.CRX(theta, wires=[0, 1]); qml.CRY(theta, wires=[0, 1]); qml.CRZ(theta, wires=[0, 1])
qml.IsingXX(phi, wires=[0, 1]); qml.IsingYY(...); qml.IsingZZ(...)
qml.Toffoli(wires=[0, 1, 2])     # CCNOT
qml.MultiControlledX(wires=[0, 1, 2, 3])   # controls + target as the wire list
qml.MultiRZ(theta, wires=[0, 1, 2])
```

## Controlled and conditional operations

```python
# Controlled version of any operation
qml.ctrl(qml.RX, control=0)(0.5, wires=1)
qml.ctrl(qml.RY, control=[0, 1])(0.3, wires=2)                 # multiple controls
qml.ctrl(qml.Hadamard, control=0, control_values=[0])(wires=2) # activate on |0>

# Classically-controlled on a mid-circuit measurement
m = qml.measure(0)
qml.cond(m, qml.PauliX)(wires=1)
```

## State preparation

```python
qml.BasisState([1, 0, 1], wires=[0, 1, 2])         # |101>
qml.StatePrep([0.5, 0.5, 0.5, 0.5], wires=[0, 1])  # arbitrary normalized state (2 qubits)
qml.MottonenStatePreparation(amplitudes, wires=[0, 1])  # explicit amplitude-encoding routine
```

`qml.StatePrep` is the modern general-purpose amplitude loader; `MottonenStatePreparation` is the
underlying decomposition. Amplitudes must be normalized and of length `2**len(wires)`.

## Measurements

A QNode may return any of these (or a list/tuple of them):

```python
qml.expval(qml.PauliZ(0))                 # expectation value in [-1, 1]
qml.expval(qml.PauliZ(0) @ qml.PauliZ(1)) # tensor-product observable
qml.var(qml.PauliZ(0))                    # variance
qml.probs(wires=[0, 1])                   # [p(00), p(01), p(10), p(11)]
qml.state()                               # full state vector (simulator, analytic only)
qml.sample(qml.PauliZ(0))                 # raw samples (device must have shots)
qml.counts(wires=[0, 1])                  # dict of bitstring -> count (needs shots)
```

`qml.state()` and analytic `expval` require a shot-free (analytic) device. `sample`/`counts`
require `shots` set on the device or passed at call time.

## Data encodings

Choosing how classical data enters the circuit is a core modeling decision.

```python
# Angle encoding: one feature per rotation angle (n features -> n qubits)
for i, x_i in enumerate(x):
    qml.RY(x_i, wires=i)
# Or the template: qml.AngleEmbedding(x, wires=range(n), rotation="Y")

# Amplitude encoding: 2**n features into n qubits (needs normalization)
qml.AmplitudeEmbedding(x, wires=range(n), normalize=True)

# Basis encoding: binary features into computational basis
qml.BasisEmbedding(bits, wires=range(n))

# IQP encoding: Hadamards + diagonal ZZ interactions (harder-to-simulate feature map)
qml.IQPEmbedding(x, wires=range(n), n_repeats=2)
```

## Dynamic and mid-circuit measurement

```python
@qml.qnode(dev)
def adaptive():
    qml.Hadamard(wires=0)
    m = qml.measure(0)                 # mid-circuit measurement -> MeasurementValue
    qml.cond(m, qml.PauliX)(wires=1)   # feed-forward correction
    return qml.expval(qml.PauliZ(1))
```

Compiled control flow (unrolled at trace time or with Catalyst) uses `qml.for_loop` /
`qml.while_loop`; see `references/devices.md` for `qjit`.

## Inspection and debugging

```python
print(qml.draw(circuit)(params))          # text diagram
fig, ax = qml.draw_mpl(circuit)(params)   # matplotlib diagram

specs = qml.specs(circuit)(params)        # dict: gate counts, depth, num_trainable_params, ...
```

`qml.specs` returns a resource summary (gate types/sizes, circuit depth, wire count, trainable
parameter count). Exact keys vary by PennyLane version; print `specs` to see the current schema
rather than hard-coding key names.

## Reusable patterns

```python
# Bell state
qml.Hadamard(wires=0); qml.CNOT(wires=[0, 1])          # (|00> + |11>)/sqrt(2)

# GHZ state on n qubits
qml.Hadamard(wires=0)
for i in range(n - 1):
    qml.CNOT(wires=[0, i + 1])

# Quantum Fourier Transform is available as a template:
qml.QFT(wires=range(n))
```

## Practices

1. Prefer templates (`AngleEmbedding`, `StronglyEntanglingLayers`, `qml.QFT`) over hand-rolled
   loops — they carry correct shapes and decompositions.
2. Keep depth low to limit decoherence on hardware and simulation cost.
3. Match the encoding to the data: amplitude encoding is compact but expensive to load; angle
   encoding is cheap and hardware-friendly.
4. Observables must be Hermitian; build composite ones with `@` (tensor product) or
   `qml.Hamiltonian`.
