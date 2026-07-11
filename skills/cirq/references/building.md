# Building Circuits

How to construct circuits in Cirq: qubits, gates, parameterization, custom gates,
moments, serialization, qudits, and observables.

## Qubits

Pick the qubit class that matches your topology; it determines how devices and
transformers reason about connectivity.

```python
import cirq

cirq.GridQubit(row=0, col=1)   # 2D grid — mirrors superconducting hardware
cirq.GridQubit.square(2)       # 2x2 block of GridQubits
cirq.GridQubit.rect(2, 3)      # 2 rows x 3 cols
cirq.LineQubit(3)              # 1D line, index 3
cirq.LineQubit.range(5)        # [LineQubit(0) .. LineQubit(4)]
cirq.NamedQubit("ancilla")     # arbitrary label, no implied geometry
```

Qubits are immutable and hashable; sort a set with `sorted(...)` for a
deterministic order.

## Gates and Operations

A *gate* is applied to qubits to produce an *operation*. Most common gates are
module-level callables.

```python
# Single-qubit
cirq.X(q); cirq.Y(q); cirq.Z(q)          # Paulis
cirq.H(q)                                # Hadamard
cirq.S(q); cirq.T(q)                     # sqrt(Z), 4th-root(Z)
cirq.rx(angle)(q); cirq.ry(angle)(q); cirq.rz(angle)(q)   # axis rotations

# Two-qubit
cirq.CNOT(control, target)               # cirq.CX is an alias
cirq.CZ(q0, q1)
cirq.SWAP(q0, q1); cirq.ISWAP(q0, q1)
cirq.CZPowGate(exponent=0.5)(q0, q1)     # partial CZ

# Powered gates: X**0.5 is sqrt(X); ZPowGate/XPowGate/YPowGate generalize
(cirq.X**0.5)(q)
```

Measurement collapses qubits into a named classical register:

```python
cirq.measure(q, key="m")                 # one qubit
cirq.measure(q0, q1, q2, key="result")   # joint register
cirq.measure(*qubits, key="final")       # all qubits
```

## Assembling a Circuit

```python
circuit = cirq.Circuit()
circuit.append([cirq.H(q0), cirq.CNOT(q0, q1), cirq.measure(q0, q1, key="result")])

# or directly from an OP_TREE
circuit = cirq.Circuit(cirq.H(q0), cirq.CNOT(q0, q1))

circuit1 + circuit2                      # concatenate
circuit.insert(index, operation)
circuit.append(ops, strategy=cirq.InsertStrategy.NEW_THEN_INLINE)
```

`InsertStrategy` controls packing: `EARLIEST` (default, greedy left-pack),
`NEW_THEN_INLINE`, and `NEW` (each op in its own moment).

## Parameterized Gates

Use `sympy` symbols to defer angle values, then resolve or sweep.

```python
import sympy
theta, phi = sympy.symbols("theta phi")
circuit = cirq.Circuit(cirq.rx(theta)(q0), cirq.ry(phi)(q1), cirq.CNOT(q0, q1))

resolved = cirq.resolve_parameters(circuit, {"theta": 0.5, "phi": 1.2})
```

A circuit with unresolved symbols must be resolved (or run through a sweep,
see [simulation.md](simulation.md)) before `simulate`/`run`.

## Custom Gates

**From a unitary matrix:**

```python
import numpy as np
u = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])
gate = cirq.MatrixGate(u)
op = gate(q0, q1)
```

**By subclassing `cirq.Gate`** — supply a decomposition and diagram info so the
gate compiles and prints cleanly:

```python
class MyGate(cirq.Gate):
    def _num_qubits_(self):
        return 1
    def _decompose_(self, qubits):
        (q,) = qubits
        return [cirq.H(q), cirq.T(q), cirq.H(q)]
    def _circuit_diagram_info_(self, args):
        return "MyGate"
```

Implement `_unitary_` instead of `_decompose_` if you want simulators to use the
matrix directly. `cirq.decompose(circuit)` expands custom gates into primitives.

## Moments

A `Moment` is a set of operations on disjoint qubits that execute in parallel;
circuit depth is the number of moments.

```python
circuit = cirq.Circuit(
    cirq.Moment(cirq.H(q0), cirq.H(q1)),
    cirq.Moment(cirq.CNOT(q0, q1)),
)
for i, moment in enumerate(circuit):
    print(i, moment)
```

## Serialization

```python
# OpenQASM 2.0
qasm_str = circuit.to_qasm()
from cirq.contrib.qasm_import import circuit_from_qasm
circuit = circuit_from_qasm(qasm_str)

# Cirq JSON (round-trips full fidelity, including custom gates registered with Cirq)
json_str = cirq.to_json(circuit)
circuit = cirq.read_json(json_text=json_str)
```

## Qudits

Higher-dimensional systems use `LineQid`/`GridQid` and gates that declare a
`_qid_shape_`:

```python
qutrit = cirq.LineQid(0, dimension=3)

class QutritX(cirq.Gate):
    def _qid_shape_(self):
        return (3,)
    def _unitary_(self):
        return np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]])

circuit = cirq.Circuit(QutritX()(qutrit))
```

## Observables

Pauli operators compose into `PauliString`s and `PauliSum`s, used for expectation
values (see [simulation.md](simulation.md)) and Hamiltonians (see
[experiments.md](experiments.md)):

```python
obs = cirq.Z(q0)                          # single Pauli
obs = cirq.X(q0) * cirq.Y(q1) * cirq.Z(q2)  # PauliString (tensor product)
obs = 0.5 * cirq.X(q0) + 0.3 * cirq.Z(q1)   # PauliSum (linear combination)
```

## Reusable Patterns

```python
def bell_state():
    a, b = cirq.LineQubit.range(2)
    return cirq.Circuit(cirq.H(a), cirq.CNOT(a, b))

def ghz(qubits):
    c = cirq.Circuit(cirq.H(qubits[0]))
    c.append(cirq.CNOT(qubits[i], qubits[i + 1]) for i in range(len(qubits) - 1))
    return c

def qft(qubits):
    c = cirq.Circuit()
    for i, q in enumerate(qubits):
        c.append(cirq.H(q))
        for j in range(i + 1, len(qubits)):
            c.append(cirq.CZPowGate(exponent=1 / 2 ** (j - i))(qubits[j], q))
    for i in range(len(qubits) // 2):
        c.append(cirq.SWAP(qubits[i], qubits[-i - 1]))
    return c
```

## Tips

- Match the qubit class to the target device topology so routing and validation
  behave predictably.
- Keep circuit builders as pure functions of their parameters for reproducibility.
- Give every measurement a descriptive `key`; results are looked up by key.
- Provide `_circuit_diagram_info_` on custom gates so `print(circuit)` stays legible.
