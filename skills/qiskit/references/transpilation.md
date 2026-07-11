# Transpilation and Optimization

Transpilation rewrites an abstract circuit into one a specific device can run:
native (basis) gates only, respecting physical qubit connectivity, minimizing
depth and two-qubit-gate count on noisy hardware. Runtime primitives require an
ISA (Instruction Set Architecture) circuit — an untranspiled circuit is rejected.

## Two ways to transpile

### Preset pass manager (recommended for the Patterns workflow)

```python
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
isa = pm.run(qc)                 # accepts a circuit or a list of circuits
```

Build the pass manager once and reuse it across many circuits (e.g. every VQE
iteration) — it is the efficient, composable path.

### `transpile()` convenience function

```python
from qiskit import transpile
isa = transpile(qc, backend=backend, optimization_level=3)
```

Fine for one-off scripts; internally builds a preset pass manager.

## Optimization levels

| Level | Effort   | Use                                              |
| ----- | -------- | ------------------------------------------------ |
| 0     | none     | debugging, already-optimal circuits              |
| 1     | light    | fast iteration                                   |
| 2     | moderate | good default                                     |
| 3     | heavy    | production; best depth/gate reduction, slowest   |

## The six stages

1. **Init** — unroll to a common form, validate instructions.
2. **Layout** — assign virtual (circuit) qubits to physical qubits, weighing
   connectivity and per-qubit error rates.
3. **Routing** — insert SWAPs so every two-qubit gate acts on physically adjacent
   qubits; minimize SWAP overhead.
4. **Translation** — rewrite gates into the device's basis set (e.g. `rz, sx, x,
   cx` / `ecr`).
5. **Optimization** — cancel adjacent inverse gates, merge rotations, apply
   commutation and (levels 2-3) permutation-aware simplifications.
6. **Scheduling** (optional) — attach timing / insert delays for pulse-aware
   passes such as dynamical decoupling.

## Controlling the transpiler

```python
from qiskit.transpiler import CouplingMap

pm = generate_preset_pass_manager(
    optimization_level=3,
    backend=backend,
    initial_layout=[0, 2, 4],        # pin virtual qubits to physical 0,2,4
    seed_transpiler=42,              # reproducible layout/routing
    approximation_degree=0.99,       # 1.0 exact; lower trades accuracy for fewer gates
)

# Without a backend, specify the target abstractly:
pm = generate_preset_pass_manager(
    optimization_level=2,
    basis_gates=["cx", "rz", "sx", "x"],
    coupling_map=CouplingMap([(0, 1), (1, 2), (2, 3)]),
)
```

Prefer passing `target=backend.target` (or just `backend=`) so the transpiler
uses real gate durations and error rates rather than a topology alone.

## Analyzing the result

```python
isa = pm.run(qc)
print("depth:", isa.depth())
print("size:", isa.size())
print("ops:", isa.count_ops())
print("two-qubit gates:", isa.count_ops().get("cx", 0))  # or 'ecr' on some devices
```

Two-qubit gates are the primary error source; compare this number across
`optimization_level` and `initial_layout` choices.

## Observables must follow the layout

Transpilation relabels qubits. For an Estimator, remap the observable to match:

```python
isa_obs = observable.apply_layout(isa.layout)
```

Omitting this is the most common silent-wrong-result bug on hardware.

## Simulators benefit too

```python
from qiskit_aer import AerSimulator
sim = AerSimulator()
isa = generate_preset_pass_manager(optimization_level=3, backend=sim).run(qc)
```

Transpiling against `AerSimulator.from_backend(backend)` reproduces the real
device's basis and connectivity so local tests mirror hardware.

## Provider differences

- **IBM** superconducting devices: limited connectivity, basis like
  `{rz, sx, x, cx/ecr}`.
- **IonQ**: all-to-all connectivity, native `{gpi, gpi2, ms}`; transpile against
  the provider's target.
- **Rigetti / OQC** (via Braket): device-specific bases and coupling.

## Common issues

- **Circuit too deep after transpilation** — raise the optimization level or
  redesign with fewer entangling layers / a topology-aware ansatz.
- **Too many SWAPs inserted** — set an `initial_layout` that matches the coupling
  map, or choose a better-connected qubit subset.
- **Transpilation is slow** — reuse a pass manager, lower the level for
  iteration, and transpile lists of circuits together (Qiskit parallelizes).
- **Unexpected decompositions** — check `backend.target.operation_names`; specify
  `basis_gates` explicitly if needed.

## Best practices

- Reuse one `generate_preset_pass_manager(...)` across an iterative loop.
- Design circuits with the coupling map in mind to avoid routing blow-up.
- Minimize two-qubit gates before transpiling, not just after.
- Validate on a noisy Aer simulator built from the target backend first.
