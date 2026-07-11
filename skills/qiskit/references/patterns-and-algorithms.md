# Patterns and Algorithms

The **Qiskit Patterns** workflow and concrete algorithm implementations (VQE,
QAOA, Grover) plus the domain ecosystem packages (Nature, Machine Learning,
Optimization).

## The four-step pattern

```
Problem -> [Map] -> [Optimize] -> [Execute] -> [Post-process] -> Solution
```

1. **Map** — encode the problem as circuits and operators (Hamiltonians,
   ansaetze, feature maps). Decide Sampler (bitstrings) vs Estimator (expectation
   values).
2. **Optimize** — transpile to ISA circuits for the target
   (`references/transpilation.md`); remap observables with `apply_layout`.
3. **Execute** — run with primitives (`references/primitives.md`), choosing
   Session (iterative) or Batch (parallel) mode.
4. **Post-process** — turn measurements into an answer with classical compute.

## VQE (Variational Quantum Eigensolver)

Finds the lowest eigenvalue of a Hamiltonian via a hybrid quantum-classical loop.
The current idiom is a manual loop over a Runtime `EstimatorV2` and a classical
optimizer (the old `qiskit_algorithms.VQE` class is deprecated).

```python
import numpy as np
from scipy.optimize import minimize
from qiskit.circuit.library import EfficientSU2
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2 as Estimator, Session

hamiltonian = SparsePauliOp(["ZZ", "XX", "IZ", "ZI"], coeffs=[0.5, 0.2, 0.3, 0.3])
ansatz = EfficientSU2(hamiltonian.num_qubits)

pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
isa_ansatz = pm.run(ansatz)
isa_ham = hamiltonian.apply_layout(isa_ansatz.layout)   # remap to physical qubits

def cost(params, estimator):
    pub = (isa_ansatz, isa_ham, params)
    return estimator.run([pub]).result()[0].data.evs

with Session(backend=backend) as session:
    estimator = Estimator(mode=session)
    x0 = 2 * np.pi * np.random.random(ansatz.num_parameters)
    res = minimize(cost, x0, args=(estimator,), method="COBYLA")

print("ground-state energy:", res.fun)
```

Bind parameters through the PUB (`(circuit, observable, params)`) rather than
`assign_parameters` each iteration — the parameterized ISA circuit is transpiled
once and reused.

## QAOA (Quantum Approximate Optimization Algorithm)

Combinatorial optimization (MaxCut, portfolio selection, scheduling). Build cost
and mixer layers, then optimize the layer angles like VQE.

```python
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector

def qaoa_maxcut(graph, p):
    n = graph.number_of_nodes()
    qc = QuantumCircuit(n)
    betas, gammas = ParameterVector("b", p), ParameterVector("g", p)
    qc.h(range(n))                              # uniform superposition
    for layer in range(p):
        for u, v in graph.edges():              # cost (problem) Hamiltonian
            qc.cx(u, v); qc.rz(2 * gammas[layer], v); qc.cx(u, v)
        for q in range(n):                      # mixer Hamiltonian
            qc.rx(2 * betas[layer], q)
    return qc
```

For MaxCut, use a Sampler and evaluate the cut value of sampled bitstrings, or an
Estimator with the cost Hamiltonian as the objective.

## Grover's algorithm

Quadratic speedup for unstructured search. Alternate an oracle (phase-flips
marked states) with the diffusion operator ~ sqrt(N) times.

```python
import numpy as np
from qiskit import QuantumCircuit

def diffusion(n):
    qc = QuantumCircuit(n)
    qc.h(range(n)); qc.x(range(n))
    qc.h(n - 1); qc.mcx(list(range(n - 1)), n - 1); qc.h(n - 1)
    qc.x(range(n)); qc.h(range(n))
    return qc

# For a marked-state oracle use the same phase-kickback pattern, or the
# library helper qiskit.circuit.library.GroverOperator / grover_operator.
n = 3
iterations = int(np.floor(np.pi / 4 * np.sqrt(2 ** n)))   # optimal count
```

## Chemistry — Qiskit Nature

Separately versioned package; APIs shift between releases, so confirm against the
installed `qiskit-nature` docs. Typical H2 ground-state flow:

```bash
uv pip install qiskit-nature pyscf
```

```python
from qiskit_nature.second_q.drivers import PySCFDriver
from qiskit_nature.second_q.mappers import JordanWignerMapper

driver = PySCFDriver(atom="H 0 0 0; H 0 0 0.735", basis="sto3g")
problem = driver.run()
mapper = JordanWignerMapper()
qubit_hamiltonian = mapper.map(problem.hamiltonian.second_q_op())
# feed qubit_hamiltonian + an ansatz (e.g. UCCSD) into the VQE loop above,
# then add problem.nuclear_repulsion_energy to the electronic energy.
```

Fermion-to-qubit mappers trade qubit count for locality: `JordanWignerMapper`
(simple), `ParityMapper` (allows two-qubit reduction), `BravyiKitaevMapper`
(logarithmic operator weight).

## Machine learning — Qiskit Machine Learning

Quantum kernels for SVMs, variational classifiers (VQC), and quantum neural
networks (`SamplerQNN` / `EstimatorQNN`) that bridge to PyTorch. Import paths and
constructor signatures vary noticeably across `qiskit-machine-learning`
releases — treat the sketch below as the shape and verify against installed docs.

```python
# Quantum-kernel SVM (conceptual):
# 1. build a feature map (e.g. a ZZ feature map)
# 2. wrap it in a FidelityQuantumKernel
# 3. compute the kernel matrix and pass to sklearn's SVC(kernel="precomputed")
```

## Optimization — Qiskit Optimization

Model quadratic/integer/linear programs as a `QuadraticProgram`, convert to an
Ising Hamiltonian, and solve with a `MinimumEigenOptimizer` backed by QAOA or an
exact solver. Application classes cover MaxCut, portfolio optimization, TSP, and
bin packing. Confirm import paths against the installed `qiskit-optimization`.

## Time evolution

```python
from qiskit.quantum_info import SparsePauliOp
from qiskit.synthesis import SuzukiTrotter

H = SparsePauliOp(["XX", "YY", "ZZ"], coeffs=[1.0, 1.0, 1.0])
evo = SuzukiTrotter(order=2, reps=10)      # Trotterized e^{-iHt}
```

## Practical guidance

- **Start tiny.** Validate correctness on 2-3 qubits with a local simulator
  before scaling or touching hardware.
- **Develop on simulators.** Use `StatevectorEstimator` / `StatevectorSampler`,
  then swap in Runtime primitives — the loop code is identical.
- **Track convergence.** Log the cost each iteration; plot it to catch
  barren-plateau stalls and bad initializations.
- **Use Sessions** for VQE/QAOA so you do not re-queue every iteration.
- **Checkpoint** parameters and energies to JSON so long runs survive restarts.
- **Ecosystem lag:** Nature / ML / Optimization release behind the core SDK; pin
  compatible versions and read each package's own docs for exact signatures.
