# Simulation

Running circuits on Cirq's local simulators: exact state vectors, density
matrices, sampling, expectation values, parameter sweeps, and performance.

## Simulator Choice

| Simulator | Represents | Use when | Cost |
| --- | --- | --- | --- |
| `cirq.Simulator()` | pure state vector | no noise, pure state | `O(2^n)` |
| `cirq.DensityMatrixSimulator()` | density matrix | any noise / mixed state | `O(2^{2n})` |
| `cirq.CliffordSimulator()` | stabilizer tableau | Clifford-only circuits | polynomial |

`run` samples measurements (needs a `measure` op); `simulate` returns the full
final state (drop measurements first).

## Sampling with `run`

```python
import cirq
circuit = cirq.Circuit(
    cirq.H(q0), cirq.CNOT(q0, q1), cirq.measure(q0, q1, key="result")
)
result = cirq.Simulator().run(circuit, repetitions=10000)

result.histogram(key="result")     # {int_value: count}; value is big-endian over measured qubits
result.measurements["result"]      # ndarray, shape (repetitions, num_qubits)
```

## Full-State Access with `simulate`

```python
res = cirq.Simulator().simulate(circuit_without_measurement)
sv = res.final_state_vector         # complex128 ndarray of length 2^n
sv[0], sv[3]                        # amplitudes of |00> and |11>

dm = cirq.DensityMatrixSimulator().simulate(circuit).final_density_matrix
```

Convert amplitudes to probabilities with `np.abs(sv) ** 2`.

## Moment-by-Moment Stepping

```python
for step in cirq.Simulator().simulate_moment_steps(circuit):
    print(step.state_vector())      # state after each moment
```

## Expectation Values

Pass observables directly instead of hand-rolling measurement post-processing:

```python
zz = cirq.PauliString({q0: cirq.Z, q1: cirq.Z})
vals = cirq.Simulator().simulate_expectation_values(circuit, observables=[zz])
print(vals[0])                      # <ZZ>
```

For an arbitrary observable against a known state vector, use
`observable.expectation_from_state_vector(state_vector, qubit_map=...)` (see
[experiments.md](experiments.md)).

## Parameter Sweeps

Sweeps run one compiled circuit across many parameter values — far cheaper than
looping over `run`.

```python
import sympy, numpy as np
theta, phi = sympy.symbols("theta phi")
circuit = cirq.Circuit(cirq.ry(theta)(q0), cirq.rz(phi)(q1), cirq.measure(q0, q1, key="m"))

# single axis
sweep = cirq.Linspace("theta", start=0, stop=2 * np.pi, length=50)

# Cartesian product (all combinations)
sweep = cirq.Product(cirq.Linspace("theta", 0, np.pi, 10),
                     cirq.Linspace("phi", 0, 2 * np.pi, 10))

# zipped (paired, same length)
sweep = cirq.Zip(cirq.Linspace("theta", 0, np.pi, 20),
                 cirq.Linspace("phi", 0, 2 * np.pi, 20))

# explicit points
sweep = cirq.Points("theta", [0.0, 0.5, 1.0])

results = cirq.Simulator().run_sweep(circuit, params=sweep, repetitions=1000)
for params, res in zip(sweep, results):
    print(params["theta"], res.histogram(key="m"))
```

Prefer `run_sweep(circuit, sweep, ...)` over a Python loop of `run` calls; the
simulator amortizes setup across the sweep.

## Noisy Simulation

Noise channels are only honored by the density-matrix simulator (or a stochastic
trajectory run). See [noise.md](noise.md) for channels and models.

```python
noisy = circuit.with_noise(cirq.depolarize(p=0.01))
cirq.DensityMatrixSimulator().run(noisy, repetitions=1000)

# or attach a NoiseModel to the simulator itself
model = cirq.ConstantQubitNoiseModel(cirq.depolarize(0.01))
cirq.DensityMatrixSimulator(noise=model).run(circuit, repetitions=1000)
```

## Custom Initial State

```python
init = np.array([1, 0, 0, 1]) / np.sqrt(2)     # (|00> + |11>) / sqrt(2)
cirq.Simulator().simulate(circuit, initial_state=init)
```

You can also pass an integer computational-basis index as `initial_state`.

## Stabilizer (Clifford) Simulation

Circuits containing only H, S, CNOT, and Paulis simulate in polynomial time:

```python
clifford = cirq.Circuit(cirq.H(q0), cirq.S(q1), cirq.CNOT(q0, q1),
                        cirq.measure(q0, q1, key="result"))
cirq.CliffordSimulator().run(clifford, repetitions=1000)
```

Any non-Clifford gate (e.g. `T`, arbitrary rotation) forces you back to the
state-vector simulator.

## Performance and Memory

- State-vector memory is `2^n * 16` bytes (complex128): ~16 MB at 20 qubits,
  ~16 GB at 30. Density matrices square this exponent, capping near ~12-14 qubits.
- Batch with `run_sweep`; do not loop `run`.
- Use `Simulator` for pure states; switch to `DensityMatrixSimulator` only when
  you genuinely need mixed states or noise.
- Reduce `repetitions` to trade sampling accuracy for speed; standard error on a
  probability scales as `1/sqrt(repetitions)`.

```python
n = 20
print(f"{2**n * 16 / 1e9:.3f} GB state vector")
```
