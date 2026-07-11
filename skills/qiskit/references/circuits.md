# Building Quantum Circuits

Construct circuits with `QuantumCircuit`: allocate qubits/clbits, apply gates,
add measurements, compose, and parameterize.

## Creating a circuit

```python
from qiskit import QuantumCircuit

qc = QuantumCircuit(3)       # 3 qubits, no classical bits
qc = QuantumCircuit(3, 3)    # 3 qubits + 3 classical bits (for measurement)
```

Qubits and clbits are indexed from 0. Gate methods mutate the circuit in place
and return it, so calls chain.

## Single-qubit gates

```python
from math import pi

qc.x(0); qc.y(1); qc.z(2)     # Pauli X / Y / Z
qc.h(0)                       # Hadamard -> superposition
qc.s(0); qc.sdg(0)            # S = sqrt(Z) and its inverse
qc.t(0); qc.tdg(0)            # T = sqrt(S) and its inverse
qc.p(pi/4, 0)                 # phase gate, arbitrary angle
qc.rx(pi/2, 0)                # rotation about X
qc.ry(pi/4, 1)                # rotation about Y
qc.rz(pi/3, 2)                # rotation about Z
```

## Multi-qubit gates

```python
qc.cx(0, 1)        # CNOT: control 0, target 1
qc.cy(0, 1)        # controlled-Y
qc.cz(0, 1)        # controlled-Z
qc.ch(0, 1)        # controlled-Hadamard
qc.cp(pi/2, 0, 1)  # controlled-phase
qc.swap(0, 1)      # SWAP
qc.ccx(0, 1, 2)    # Toffoli (CCX): controls 0,1 target 2
qc.mcx([0, 1, 2], 3)  # multi-controlled X: controls 0,1,2 target 3
```

Two-qubit gates dominate hardware error budgets — minimize them (see
`references/transpilation.md`).

## Measurements and barriers

```python
qc.measure_all()             # append a classical register 'meas' and measure every qubit
qc.measure(0, 0)             # measure qubit 0 into clbit 0
qc.measure([0, 1], [0, 1])   # measure qubits 0,1 into clbits 0,1

qc.barrier()                 # optimization/visual barrier across all qubits
qc.barrier([0, 1])           # on specific qubits
qc.barrier(label="init")
```

After `measure_all()` the classical register is named `meas`; that is the name
you use when reading Sampler results: `result[0].data.meas.get_counts()`. For an
Estimator, do **not** add measurements — the observable defines what is measured.

## Composition

```python
sub = QuantumCircuit(2); sub.cx(0, 1)

qc.compose(sub, inplace=True)         # append sub onto qc
qc.compose(sub, qubits=[1, 2], inplace=True)  # map sub's qubits 0,1 to qc's 1,2

both = a.tensor(b)                    # tensor product -> a on high qubits, b on low
```

`compose` returns a new circuit unless `inplace=True`. `append` adds an
instruction/gate object; `compose` splices another circuit's data.

## Circuit inspection

```python
qc.num_qubits
qc.num_clbits
qc.depth()        # critical path length (layers)
qc.size()         # total gate count
qc.count_ops()    # {'h': 1, 'cx': 2, 'measure': 3, ...}
```

`count_ops().get('cx', 0)` gives the two-qubit-gate count — the number to drive
down before hardware execution.

## Parameterized circuits

Use `Parameter` / `ParameterVector` to defer gate angles, then bind them at
run time. Essential for variational algorithms.

```python
from qiskit.circuit import Parameter, ParameterVector

theta = Parameter("theta")
qc = QuantumCircuit(1)
qc.ry(theta, 0)

bound = qc.assign_parameters({theta: 3.14159 / 4})

# Many parameters at once:
params = ParameterVector("p", length=4)
ansatz = QuantumCircuit(2)
for i, p in enumerate(params):
    ansatz.ry(p, i % 2)
```

Runtime primitives can take a parameterized circuit plus an array of parameter
values in one PUB (see `references/primitives.md`); you do not always need to
`assign_parameters` yourself.

## Library circuits and templates

`qiskit.circuit.library` ships standard building blocks — QFT, feature maps
(`ZZFeatureMap`), hardware-efficient ansaetze (`RealAmplitudes`, `EfficientSU2`),
and arithmetic circuits. In recent Qiskit releases many of these class-based
constructors are being superseded by function equivalents (e.g. `qft`,
`zz_feature_map`, `efficient_su2`); check the installed version's library docs
for the current spelling.

## Common utilities

```python
qc.inverse()      # reverse/adjoint of the circuit
qc.decompose()    # expand composite gates one level toward basis gates
qc.draw("mpl")    # visualize (see references/visualization.md)
```

## Example: Quantum Fourier Transform

```python
from math import pi

def qft(n):
    qc = QuantumCircuit(n)
    for j in range(n):
        qc.h(j)
        for k in range(j + 1, n):
            qc.cp(pi / 2 ** (k - j), k, j)
    return qc
```
