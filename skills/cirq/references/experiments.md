# Experiments and Algorithms

Structuring quantum experiments, collecting sweep data, and implementing the
common variational and estimation algorithms.

## Experiment Structure

Separate the three phases so each is independently reproducible: build the
circuit, collect data, analyze. The ReCirq research library (github.com/
quantumlib/ReCirq) formalizes this with `tasks.py` (parameterized work items),
`data_collection.py`, and `analysis.py` — a good template even without ReCirq.

```python
import cirq, numpy as np, pandas as pd, sympy

def build(qubits, theta, phi):
    return cirq.Circuit(
        cirq.ry(theta)(qubits[0]), cirq.rz(phi)(qubits[1]),
        cirq.CNOT(qubits[0], qubits[1]),
        cirq.measure(*qubits, key="result"),
    )
```

## Sweep-Based Data Collection

Use symbolic parameters plus a sweep so the whole grid runs in one call (see
[simulation.md](simulation.md)):

```python
theta, phi = sympy.symbols("theta phi")
qubits = cirq.LineQubit.range(2)
circuit = build(qubits, theta, phi)
sweep = cirq.Product(cirq.Linspace("theta", 0, np.pi, 20),
                     cirq.Linspace("phi", 0, 2 * np.pi, 20))

rows = []
for params, res in zip(sweep, cirq.Simulator().run_sweep(circuit, sweep, repetitions=1000)):
    rows.append({"theta": params["theta"], "phi": params["phi"],
                 "counts": dict(res.histogram(key="result"))})
pd.DataFrame(rows).to_csv("experiment.csv", index=False)
```

For CPU-bound independent tasks (e.g. many distinct circuits) parallelize with
`multiprocessing.Pool`, giving each worker its own simulator.

## VQE — Variational Quantum Eigensolver

Minimize the expectation of a Hamiltonian over a parameterized ansatz.

```python
import scipy.optimize

qubits = cirq.LineQubit.range(2)
H = cirq.PauliSum.from_pauli_strings([
    cirq.PauliString({qubits[0]: cirq.Z}),
    cirq.PauliString({qubits[1]: cirq.Z}),
    cirq.PauliString({qubits[0]: cirq.Z, qubits[1]: cirq.Z}),
])

def ansatz(theta):
    return cirq.Circuit(cirq.X(qubits[1]), cirq.ry(theta)(qubits[0]),
                        cirq.CNOT(qubits[0], qubits[1]))

def energy(params):
    res = cirq.Simulator().simulate(ansatz(params[0]))
    e = H.expectation_from_state_vector(
        res.final_state_vector,
        qubit_map={q: i for i, q in enumerate(qubits)})
    return e.real

opt = scipy.optimize.minimize(energy, [0.0], method="COBYLA")
print(opt.fun, opt.x)
```

`method="COBYLA"` and `"SPSA"`-style optimizers suit noisy, gradient-free cost
landscapes. `expectation_from_state_vector` needs a `qubit_map` fixing each
qubit's index in the state vector.

## QAOA — MaxCut

Alternate a problem (cost) layer and a mixer layer `p` times, optimizing the
`2p` angles.

```python
import networkx as nx

def qaoa_circuit(graph, params, p):
    qubits = cirq.LineQubit.range(graph.number_of_nodes())
    c = cirq.Circuit(cirq.H(q) for q in qubits)
    for layer in range(p):
        gamma, beta = params[layer], params[p + layer]
        for i, j in graph.edges():
            c.append(cirq.ZZPowGate(exponent=gamma)(qubits[i], qubits[j]))
        c.append(cirq.rx(2 * beta)(q) for q in qubits)
    c.append(cirq.measure(*qubits, key="result"))
    return c

graph, p = nx.cycle_graph(4), 2
def cost(params):
    res = cirq.Simulator().run(qaoa_circuit(graph, params, p), repetitions=1000)
    total = 0
    for value, count in res.histogram(key="result").items():
        bits = [(value >> i) & 1 for i in range(graph.number_of_nodes())]
        total += sum(bits[i] != bits[j] for i, j in graph.edges()) * count
    return -total / 1000
opt = scipy.optimize.minimize(cost, np.random.random(2 * p) * np.pi, method="COBYLA")
```

## QPE — Quantum Phase Estimation

Estimate the eigenphase of a unitary using a register of counting qubits, powered
controlled-`U`s, and an inverse QFT.

```python
def qpe_circuit(unitary_gate, prepare_eigenstate, n_counting):
    counting = cirq.LineQubit.range(n_counting)
    target = cirq.LineQubit(n_counting)
    c = cirq.Circuit(prepare_eigenstate(target), (cirq.H(q) for q in counting))
    for i, q in enumerate(counting):
        power = 2 ** (n_counting - 1 - i)
        c.append(cirq.ControlledGate(unitary_gate)(q, target) for _ in range(power))
    c.append(inverse_qft(counting))
    c.append(cirq.measure(*counting, key="phase"))
    return c

def inverse_qft(qubits):
    ops = [cirq.SWAP(qubits[i], qubits[-i - 1]) for i in range(len(qubits) // 2)]
    for i in range(len(qubits)):
        for j in range(i):
            ops.append(cirq.CZPowGate(exponent=-1 / 2 ** (i - j))(qubits[j], qubits[i]))
        ops.append(cirq.H(qubits[i]))
    return ops
```

For a base gate raised to a power, `unitary_gate ** power` is usually cheaper than
repeating a controlled gate `power` times.

## Analysis

```python
def stats(result):
    counts = result.histogram(key="result")
    total = sum(counts.values())
    probs = {s: c / total for s, c in counts.items()}
    entropy = -sum(p * np.log2(p) for p in probs.values() if p > 0)
    likely = max(counts.items(), key=lambda kv: kv[1])
    return {"probs": probs, "entropy": entropy, "argmax": likely[0]}

def state_fidelity(a, b):                      # |<a|b>|^2
    return abs(np.vdot(a, b)) ** 2

def classical_fidelity(counts1, counts2):      # Bhattacharyya on distributions
    t1, t2 = sum(counts1.values()), sum(counts2.values())
    p1 = {k: v / t1 for k, v in counts1.items()}
    p2 = {k: v / t2 for k, v in counts2.items()}
    return sum(np.sqrt(p1.get(s, 0) * p2.get(s, 0)) for s in p1.keys() | p2.keys()) ** 2
```

## Tips

- Keep build / collect / analyze in separate functions; adopt ReCirq's task
  layout for larger studies.
- Sweep instead of looping `run`; save intermediate results to disk frequently.
- Record metadata (parameters, timestamps, package versions) alongside data.
- Validate the whole pipeline on a simulator before spending hardware time
  (see [hardware.md](hardware.md)).
- Gradient-free optimizers (COBYLA, SPSA) tolerate the sampling noise in
  measured cost functions better than gradient methods.
