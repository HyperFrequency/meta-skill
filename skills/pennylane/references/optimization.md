# Optimization, Gradients, and Variational Algorithms

How PennyLane differentiates circuits, which optimizer to pick, and the two workhorse variational
algorithms (VQE, QAOA), plus the failure mode you will actually hit: barren plateaus.

## Differentiation methods

Set on the QNode via `diff_method`:

| `diff_method`      | Where it runs        | Notes |
|--------------------|----------------------|-------|
| `backprop`         | simulators only      | Fastest for many parameters; not available on hardware. |
| `adjoint`          | state-vector sims    | Memory-efficient exact gradient; simulator-only. |
| `parameter-shift`  | hardware + sims      | Analytic gradient via extra circuit evaluations; use on real devices. |
| `finite-diff`      | anywhere             | Numerical; noisy, use as a fallback. |
| `spsa`             | hardware, many params| Stochastic; cheap gradient estimate for high-dimensional cases. |

```python
@qml.qnode(dev, diff_method="parameter-shift")
def circuit(params):
    qml.RX(params[0], wires=0)
    qml.RY(params[1], wires=1)
    qml.CNOT(wires=[0, 1])
    return qml.expval(qml.PauliZ(0))

grad = qml.grad(circuit)(params)              # gradient (autograd interface)
hess = qml.jacobian(qml.grad(circuit))(params)  # Hessian
```

For torch/jax/tf interfaces, use that framework's autodiff (`loss.backward()`, `jax.grad`, a
`tf.GradientTape`) instead of `qml.grad`; PennyLane routes through the framework.

## Built-in optimizers (autograd/NumPy interface)

All follow the `opt.step(cost, params)` / `opt.step_and_cost(cost, params)` pattern and expect
`params` created with `pennylane.numpy` and `requires_grad=True`.

```python
opt = qml.GradientDescentOptimizer(stepsize=0.1)
opt = qml.AdamOptimizer(stepsize=0.01, beta1=0.9, beta2=0.999)
opt = qml.MomentumOptimizer(stepsize=0.01, momentum=0.9)
opt = qml.NesterovMomentumOptimizer(stepsize=0.01, momentum=0.9)
opt = qml.AdagradOptimizer(stepsize=0.1)
opt = qml.RMSPropOptimizer(stepsize=0.01, decay=0.9, eps=1e-8)
opt = qml.QNGOptimizer(stepsize=0.01)        # quantum natural gradient (uses metric tensor)
opt = qml.RotosolveOptimizer()               # analytic per-parameter minimization, no stepsize
opt = qml.SPSAOptimizer(maxiter=100)         # simultaneous perturbation, cheap gradients
opt = qml.QNSPSAOptimizer(stepsize=0.01)     # SPSA approximation of natural gradient
```

Guidance: `AdamOptimizer` is a safe default; `QNGOptimizer` converges faster on variational
circuits but costs metric-tensor evaluations; `RotosolveOptimizer` converges in very few steps
for circuits of single-parameter Pauli rotations; `SPSA`/`QNSPSA` shine when parameters are many
or the device is shot-noisy.

```python
params = np.array([0.1, 0.2], requires_grad=True)
for i in range(100):
    params, cost = opt.step_and_cost(circuit, params)
    if i % 10 == 0:
        print(f"step {i}: cost = {cost:.6f}")
```

For torch/jax/tf, use the native optimizer (`torch.optim.Adam`, `optax`, `tf.keras.optimizers`).

## Variational Quantum Eigensolver (VQE)

Minimize the expectation of a Hamiltonian to approximate its ground-state energy.

```python
from pennylane import qchem

symbols, coords = ["H", "H"], np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.74])
H, n_qubits = qchem.molecular_hamiltonian(symbols, coords)
dev = qml.device("default.qubit", wires=n_qubits)
hf = qchem.hf_state(electrons=2, orbitals=n_qubits)

@qml.qnode(dev)
def energy(params):
    qml.BasisState(hf, wires=range(n_qubits))
    qml.DoubleExcitation(params[0], wires=range(n_qubits))  # minimal H2 ansatz
    return qml.expval(H)

opt = qml.GradientDescentOptimizer(stepsize=0.4)
params = np.zeros(1, requires_grad=True)
for i in range(50):
    params, e = opt.step_and_cost(energy, params)
    print(f"step {i}: E = {e:.8f} Ha")
```

See `references/quantum_chemistry.md` for UCCSD, mappings, and larger molecules.

## QAOA (Quantum Approximate Optimization Algorithm)

Approximately solve combinatorial problems (e.g. MaxCut) by alternating a cost layer and a mixer
layer. PennyLane ships `qml.qaoa` helpers.

```python
import networkx as nx
from pennylane import qaoa

graph = nx.cycle_graph(4)
cost_h, mixer_h = qaoa.maxcut(graph)
n_wires = len(graph.nodes)
dev = qml.device("default.qubit", wires=n_wires)

def qaoa_layer(gamma, beta):
    qaoa.cost_layer(gamma, cost_h)
    qaoa.mixer_layer(beta, mixer_h)

@qml.qnode(dev)
def circuit(params, depth):
    for w in range(n_wires):
        qml.Hadamard(wires=w)          # equal superposition
    for d in range(depth):
        qaoa_layer(params[d], params[depth + d])
    return qml.expval(cost_h)

depth = 2
params = np.random.uniform(0, np.pi, 2 * depth, requires_grad=True)
opt = qml.AdamOptimizer(0.1)
for _ in range(100):
    params = opt.step(lambda p: circuit(p, depth), params)  # cost_h is negative -> minimizing maximizes cut
```

For a general QUBO, build the cost Hamiltonian with `qml.Hamiltonian(coeffs, observables)` from
`PauliZ` and `PauliZ @ PauliZ` terms, then reuse the same layer structure.

## Barren plateaus and initialization

Deep, hardware-efficient circuits initialized at random have gradient variance that vanishes
exponentially in qubit count — training stalls. Mitigations:

```python
# Detect: measure gradient variance across random initializations
grad_fn = qml.grad(circuit)
variances = [np.var(grad_fn(np.random.uniform(-np.pi, np.pi, n))) for _ in range(100)]
if np.mean(variances) < 1e-6:
    print("likely barren plateau")
```

- Initialize parameters **small** (e.g. `~U(-0.1, 0.1)`) or at the identity (`zeros`) rather than
  uniformly over `[-pi, pi]`.
- Keep circuits **shallow**; grow depth progressively (layerwise training).
- Use **problem-inspired ansatze** (UCCSD for chemistry, QAOA structure for optimization) instead
  of generic entangling layers.
- Prefer **local cost functions** (few-qubit observables) over global ones.

## Training strategies

- **Learning-rate decay**: rebuild the optimizer each epoch with a decayed `stepsize`, or use a
  framework scheduler under torch/jax/tf.
- **Mini-batches**: define the cost over a batch slice and step per batch; shuffle each epoch.
- **Early stopping / restarts**: track validation cost with patience; run several random restarts
  and keep the best parameters to escape local minima.
- **Gradient clipping**: compute `qml.grad`, clip by norm, apply the update manually when
  gradients spike.
