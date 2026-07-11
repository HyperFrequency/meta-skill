# Transformation and Compilation

Optimizing, decomposing, compiling, and routing circuits with Cirq's transformer
framework. A *transformer* is a callable `Circuit -> Circuit`; the built-ins are
exposed at the top level (`cirq.<name>`).

## Built-in Transformers

```python
import cirq, numpy as np

# Compile to a target gateset (decompose + optimize)
optimized = cirq.optimize_for_target_gateset(circuit, gateset=cirq.CZTargetGateset())
optimized = cirq.optimize_for_target_gateset(circuit, gateset=cirq.SqrtIswapTargetGateset())

# Fuse runs of single-qubit gates into one PhasedXZ gate
merged = cirq.merge_single_qubit_gates_to_phxz(circuit)

# Fuse adjacent k-qubit unitaries
merged = cirq.merge_k_qubit_unitaries(circuit, k=2)

# Remove operations below a tolerance (e.g. tiny rotations)
cleaned = cirq.drop_negligible_operations(circuit, atol=1e-8)

# Structural cleanup
cleaned = cirq.drop_empty_moments(circuit)
```

Common target gatesets: `cirq.CZTargetGateset`, `cirq.SqrtIswapTargetGateset`,
`cirq.CliffordTargetGateset`, and hardware-specific ones such as
`cirq_google.SycamoreTargetGateset` (see [hardware.md](hardware.md)).

## Z-Gate and Phase Optimization

```python
ejected = cirq.eject_z(circuit)                     # push Z gates toward the end
ejected = cirq.eject_phased_paulis(circuit, atol=1e-8)  # consolidate phased Paulis
```

`eject_z` commutes virtual-Z rotations through the circuit so they can often be
absorbed into gate frames for free on hardware.

## Gate Decomposition

```python
# Expand custom / composite gates into primitives
decomposed = cirq.decompose(circuit)

# Decompose only down to gates a predicate accepts
decomposed = cirq.decompose(circuit, keep=lambda op: len(op.qubits) <= 2)
```

A custom gate participates by implementing `_decompose_` (see
[building.md](building.md)); `optimize_for_target_gateset` then rewrites it into
the chosen gateset.

## KAK Decomposition (Two-Qubit Compilation)

Any two-qubit unitary factors into single-qubit rotations around a canonical
`XX + YY + ZZ` interaction. Use `cirq.kak_decomposition` to inspect or rebuild it:

```python
kak = cirq.kak_decomposition(unitary_4x4)
kak.single_qubit_operations_before   # tuple of 2x2 matrices
kak.interaction_coefficients         # (x, y, z) canonical-class coordinates
kak.single_qubit_operations_after
```

In practice prefer `optimize_for_target_gateset` for end-to-end two-qubit
compilation; reach for the raw KAK data only for custom synthesis.

## Custom Transformers

Decorate a `Circuit -> Circuit` function with `@cirq.transformer`; use
`cirq.map_operations` for local rewrites.

```python
@cirq.transformer
def replace_h_with_ry(circuit, *, context=None):
    def rewrite(op, _):
        if isinstance(op.gate, cirq.HPowGate):
            return cirq.ry(np.pi / 2)(op.qubits[0])
        return op
    return cirq.map_operations(circuit, rewrite).unfreeze(copy=False)
```

`map_operations` walks every operation and substitutes the return value; pass
`deep=True` to descend into `CircuitOperation` subcircuits.

## Routing to Device Connectivity

When logical two-qubit gates act on non-adjacent physical qubits, insert SWAPs to
satisfy the device's connectivity graph.

```python
import networkx as nx
device_graph = cirq_google.Sycamore.metadata.nx_graph   # or any nx.Graph of allowed edges
router = cirq.RouteCQC(device_graph)
routed = router(circuit)
```

`RouteCQC` maps logical qubits to physical qubits and adds SWAP networks; follow
with `optimize_for_target_gateset` to express the SWAPs in the native gateset,
then validate against the device (see [hardware.md](hardware.md)).

## Pipelines

Compose transformers into a single reusable pass:

```python
@cirq.transformer
def optimize_pipeline(circuit, *, context=None):
    circuit = cirq.merge_single_qubit_gates_to_phxz(circuit)
    circuit = cirq.drop_negligible_operations(circuit)
    circuit = cirq.eject_z(circuit)
    circuit = cirq.drop_empty_moments(circuit)
    return circuit
```

## Measuring Improvement

```python
def gate_counts(circuit):
    counts = {}
    for moment in circuit:
        for op in moment:
            name = type(op.gate).__name__
            counts[name] = counts.get(name, 0) + 1
    return counts

print("depth", len(circuit), "->", len(optimized))   # len(circuit) == number of moments
print(gate_counts(circuit), gate_counts(optimized))
```

## Tips

- Reach for built-in transformers before writing custom ones.
- Always re-validate against the target device after transforming.
- Track depth (`len(circuit)`) and two-qubit gate count — two-qubit gates
  dominate hardware error, so minimizing them matters most.
- Test transformers on small circuits and confirm the unitary is preserved with
  `cirq.allclose_up_to_global_phase(cirq.unitary(a), cirq.unitary(b))`.
