# Primitives: Sampler and Estimator

Primitives are the execution interface. Two kinds, one V2 API surface:

- **Sampler** — samples a circuit's classical registers, returning bitstring
  counts / probability distributions. Use for measurement outcomes, search and
  optimization algorithms.
- **Estimator** — computes expectation values `<psi|O|psi>` of observables
  (`SparsePauliOp`). Use for energies, physical observables, VQE cost functions.

Qiskit standardized on **V2** primitives (`BaseSamplerV2`, `BaseEstimatorV2`).
The reference (local) implementations are `StatevectorSampler` /
`StatevectorEstimator`; the hardware implementations are `SamplerV2` /
`EstimatorV2` in `qiskit_ibm_runtime`. Both share the PUB-based `run` API below.

## PUBs — the input unit

A primitive's `run` takes a list of **PUBs** (Primitive Unified Blocs):

- Sampler PUB: `circuit`, or `(circuit, parameter_values)`.
- Estimator PUB: `(circuit, observables)`, or `(circuit, observables, parameter_values)`.

Each PUB yields one entry in the result list, in order.

## Sampler

```python
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

qc = QuantumCircuit(2)
qc.h(0); qc.cx(0, 1); qc.measure_all()

sampler = StatevectorSampler()
result = sampler.run([qc], shots=1024).result()

counts = result[0].data.meas.get_counts()   # {'00': 523, '11': 501}
```

`data.meas` names the classical register created by `measure_all()`. If you
build your own `ClassicalRegister("c", n)` and `measure(...)` into it, read
`result[0].data.c.get_counts()` instead.

### Multiple circuits

```python
job = sampler.run([qc1, qc2], shots=1000)
res = job.result()
c1 = res[0].data.meas.get_counts()
c2 = res[1].data.meas.get_counts()
```

### Parameter binding

```python
import numpy as np
from qiskit.circuit import Parameter

theta = Parameter("theta")
qc = QuantumCircuit(1); qc.ry(theta, 0); qc.measure_all()

values = [[0.0], [np.pi/4], [np.pi/2]]        # one row per parameter set
result = sampler.run([(qc, values)], shots=1024).result()
# result[0].data.meas is now array-shaped over the 3 parameter sets
```

## Estimator

The circuit carries **no measurements**; the observable defines the measurement.

```python
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp

qc = QuantumCircuit(2)
qc.h(0); qc.cx(0, 1)                # no measure_all()

observable = SparsePauliOp(["ZZ", "XX"])
estimator = StatevectorEstimator()
result = estimator.run([(qc, observable)]).result()

evs = result[0].data.evs           # expectation value(s)
```

### Multiple observables / parameters

```python
obs1, obs2 = SparsePauliOp(["ZZ"]), SparsePauliOp(["XX"])
result = estimator.run([(qc, obs1), (qc, obs2)]).result()
ev1, ev2 = result[0].data.evs, result[1].data.evs

# parameterized:
values = [[0.0], [np.pi/4], [np.pi/2], [np.pi]]
result = estimator.run([(pqc, obs1, values)]).result()   # evs array over the sweep
```

## Runtime primitives (hardware)

Same API; swap the class and pass a backend/session/batch via `mode=`. Circuits
must be transpiled to ISA first (`references/transpilation.md`).

```python
from qiskit_ibm_runtime import SamplerV2 as Sampler, EstimatorV2 as Estimator

sampler = Sampler(mode=backend)
result = sampler.run([isa_circuit], shots=1024).result()

estimator = Estimator(mode=backend)
result = estimator.run([(isa_circuit, isa_observable)]).result()
```

**Critical:** when using the runtime Estimator, transform the observable onto the
transpiled circuit's physical-qubit layout, or the expectation value is silently
wrong:

```python
isa_observable = observable.apply_layout(isa_circuit.layout)
```

## Reading results and metadata

### Sampler

```python
counts = result[0].data.meas.get_counts()
probs  = {k: v / sum(counts.values()) for k, v in counts.items()}
meta   = result[0].metadata
```

### Estimator

```python
evs  = result[0].data.evs
stds = result[0].data.stds     # standard error, when available
meta = result[0].metadata
```

## Migration notes (V1 -> V2)

- Reference primitives renamed: `Sampler` -> `StatevectorSampler`,
  `Estimator` -> `StatevectorEstimator`.
- Result access changed: V1 `.result().quasi_dists[0]` /
  `.result().values` -> V2 `result[0].data.<creg>.get_counts()` /
  `result[0].data.evs`.
- Inputs are PUBs (tuples), not separate `circuits=`, `observables=`,
  `parameter_values=` argument lists.
