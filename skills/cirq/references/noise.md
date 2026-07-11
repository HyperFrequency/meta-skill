# Noise Modeling and Mitigation

Noise channels, noise models, characterization, and error mitigation. Noise
requires a `cirq.DensityMatrixSimulator` (state-vector simulators cannot
represent mixed states); see [simulation.md](simulation.md).

## Noise Channels

Each channel is a callable gate you insert like any other operation.

```python
import cirq, numpy as np
q = cirq.LineQubit(0)

cirq.depolarize(p=0.01)(q)                  # random Pauli with prob p
cirq.amplitude_damp(gamma=0.1)(q)           # T1 energy relaxation
cirq.phase_damp(gamma=0.1)(q)               # T2 dephasing
cirq.bit_flip(p=0.01)(q)                    # X error with prob p
cirq.phase_flip(p=0.01)(q)                  # Z error with prob p
cirq.generalized_amplitude_damp(p=0.1, gamma=0.2)(q)  # thermal (finite-temp)
cirq.reset(q)                               # reset to |0>

circuit = cirq.Circuit(cirq.H(q), cirq.depolarize(0.01)(q), cirq.measure(q, key="m"))
```

## Noise Models

A `NoiseModel` injects channels automatically around every operation, so you
don't hand-place them.

**Constant (same channel on every qubit):**

```python
model = cirq.ConstantQubitNoiseModel(cirq.depolarize(0.01))
cirq.DensityMatrixSimulator(noise=model).run(circuit, repetitions=1000)
```

**Gate-specific** — subclass `cirq.NoiseModel` and implement `noisy_operation`,
returning the original op plus follow-on noise:

```python
class GateNoise(cirq.NoiseModel):
    def noisy_operation(self, op):
        if len(op.qubits) == 1:
            return [op, cirq.depolarize(0.001)(op.qubits[0])]
        if len(op.qubits) == 2:
            return [op] + [cirq.depolarize(0.01)(q) for q in op.qubits]
        return op
```

**Qubit-specific** — key the noise by qubit:

```python
class QubitNoise(cirq.NoiseModel):
    def __init__(self, noise_map):
        self.noise_map = noise_map
    def noisy_operation(self, op):
        return [op] + [self.noise_map[q](q) for q in op.qubits if q in self.noise_map]

QubitNoise({q0: cirq.depolarize(0.001), q1: cirq.depolarize(0.005)})
```

**Thermal relaxation** from `T1`/`T2` and gate time:

```python
class ThermalNoise(cirq.NoiseModel):
    def __init__(self, T1, T2, gate_time):
        self.T1, self.T2, self.gate_time = T1, T2, gate_time
    def noisy_operation(self, op):
        p_amp = 1 - np.exp(-self.gate_time / self.T1)
        p_phase = 1 - np.exp(-self.gate_time / self.T2)
        extra = []
        for q in op.qubits:
            extra += [cirq.amplitude_damp(p_amp)(q), cirq.phase_damp(p_phase)(q)]
        return [op, *extra]

ThermalNoise(T1=50e-6, T2=30e-6, gate_time=25e-9)   # typical superconducting values
```

## Attaching Noise

```python
noisy = circuit.with_noise(cirq.depolarize(p=0.01))   # returns a new noisy circuit
# or pass a NoiseModel straight to the simulator (preferred for models):
cirq.DensityMatrixSimulator(noise=model).run(circuit, repetitions=1000)
```

## Readout Noise

Model measurement errors as a bit flip immediately before each `MeasurementGate`:

```python
class ReadoutNoise(cirq.NoiseModel):
    def __init__(self, p0_given_1, p1_given_0):
        self.p = (p0_given_1 + p1_given_0) / 2
    def noisy_operation(self, op):
        if isinstance(op.gate, cirq.MeasurementGate):
            return [cirq.bit_flip(self.p)(q) for q in op.qubits] + [op]
        return op
```

## Characterization

**Randomized benchmarking (RB):** apply sequences of random Clifford gates of
increasing depth, invert the sequence, and fit the survival probability
`p_survival = A * r**depth + B`. The average error per Clifford is `(1 - r)/2`
for a single qubit. RB isolates gate error from state-prep/measurement error.

**Cross-entropy benchmarking (XEB):** run random circuits, compare the measured
output distribution against the ideal simulated distribution, and estimate
fidelity from their cross-entropy. XEB captures full-circuit fidelity and is how
Google benchmarks Sycamore-class processors. Cirq ships XEB utilities under
`cirq.experiments` (e.g. `cirq.experiments.random_rotations_between_grid_interaction_layers_circuit`
and the XEB fidelity estimators) — prefer these over hand-rolled estimators.

## Error Mitigation

**Zero-noise extrapolation (ZNE):** evaluate an observable at several amplified
noise levels, then fit and extrapolate back to zero noise.

```python
from scipy.optimize import curve_fit
def zne(circuit, noise_levels, simulator, expval):
    xs, ys = [], []
    for level in noise_levels:
        res = simulator.simulate(circuit.with_noise(cirq.depolarize(level)))
        xs.append(level); ys.append(expval(res))
    (a, b, c), _ = curve_fit(lambda x, a, b, c: a * np.exp(-b * x) + c, xs, ys)
    return c    # value at zero noise
```

### Readout Error Mitigation

Build a confusion matrix by preparing each computational-basis state and
measuring, then apply its inverse to your raw probability vector:

```python
def mitigate_readout(counts, confusion_matrix):
    total = sum(counts.values())
    measured = np.array([counts.get(i, 0) / total for i in range(len(confusion_matrix))])
    corrected = np.linalg.inv(confusion_matrix) @ measured
    return {i: p for i, p in enumerate(corrected) if p > 0}
```

Inversion can produce small negative probabilities; clip or use a constrained
least-squares fit for a physical distribution.

## Hardware Noise from Calibration

`cirq-google` builds a realistic noise model directly from a processor's
published noise properties:

```python
import cirq_google
props = cirq_google.get_engine().get_processor("weber").get_device_specification()
model = cirq_google.NoiseModelFromGoogleNoiseProperties(props)
cirq.DensityMatrixSimulator(noise=model).run(circuit, repetitions=1000)
```

## Tips

- Use the density-matrix simulator for any noise; state-vector silently ignores it.
- Match the noise model to hardware via calibration data when available.
- Include every error source — gate, decoherence (T1/T2), and readout.
- Characterize before mitigating; target the dominant error source.
- Noise compounds with depth, so keep circuits shallow.
