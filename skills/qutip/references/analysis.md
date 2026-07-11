# Analysis and Measurement

Functions here take states (kets or density matrices) or evolution results
and return physical quantities. Most accept either a pure state or a
density matrix.

## Expectation values and variance

```python
import numpy as np, qutip as qt
qt.expect(qt.num(N), psi)                    # <n>, ket or rho
qt.expect([qt.num(N), qt.destroy(N)], psi)   # list -> list
qt.variance(qt.num(N), psi)                  # <n^2> - <n>^2
# during evolution:
result = qt.mesolve(H, psi0, tlist, c_ops, e_ops=[qt.num(N)])
n_t = result.expect[0]
```

## Entropy measures

```python
qt.entropy_vn(rho)              # von Neumann  -Tr(rho log rho)
qt.entropy_linear(rho)         # linear entropy  1 - Tr(rho^2)
qt.entropy_mutual(rho, 0, 1)   # mutual information I(A:B)
qt.entropy_conditional(rho, 0) # conditional entropy S(A|B)
```

Entanglement entropy of a bipartite pure state is the von Neumann entropy
of a reduced density matrix:

```python
rho = qt.bell_state('00').proj()
S_ent = qt.entropy_vn(qt.ptrace(rho, 0))
```

Note the logarithm base convention (bits vs nats) can differ; check the
function's docstring if the absolute value matters.

## Fidelity and distance measures

```python
qt.fidelity(psi1, psi2)     # state fidelity in [0, 1]
qt.tracedist(rho1, rho2)    # trace distance (1/2)Tr|rho1 - rho2|
qt.hilbert_dist(rho1, rho2) # Hilbert-Schmidt distance
qt.bures_dist(rho1, rho2)   # Bures distance
qt.bures_angle(rho1, rho2)  # Bures angle
qt.process_fidelity(U1, U2) # fidelity between processes/superoperators
```

## Entanglement measures

```python
qt.concurrence(rho)                 # two-qubit; 1 = maximally entangled
qt.negativity(rho, 0)               # partial transpose w.r.t. subsystem 0
qt.logarithmic_negativity(rho, 0)
```

Purity is just `(rho * rho).tr()` (1 for pure, 1/d for maximally mixed).

## Measurement

Measurement helpers live in `qutip.measurement` (importable from the top
level in current versions).

```python
from qutip.measurement import measure, measure_observable, measurement_statistics

psi = (qt.basis(2, 0) + qt.basis(2, 1)).unit()

# projective measurement of an observable -> (eigenvalue, collapsed state)
value, collapsed = measure_observable(psi, qt.sigmaz())

# all outcomes and probabilities for a set of measurement operators
outcomes, probabilities = measurement_statistics(psi, [M0, M1])
```

POVM measurement is supported through `measure_povm` /
`measurement_statistics_povm`. Argument order and return tuples have
shifted across versions -- verify against the installed docstring before
depending on the exact shape.

## Correlation functions and spectra

```python
taulist = np.linspace(0, 10, 200)

# single-time <A(t+tau) B(t)>
corr = qt.correlation_2op_1t(H, rho0, taulist, c_ops, qt.destroy(N), qt.create(N))

# two-time <A(t) B(tau)>
corr2 = qt.correlation_2op_2t(H, rho0, tlist, taulist, c_ops,
                              qt.destroy(N), qt.create(N))

# three- and four-operator variants
qt.correlation_3op_1t(H, rho0, taulist, c_ops, A, B, C)
qt.correlation_4op_1t(H, rho0, taulist, c_ops, A, B, C, D)

# power spectrum
w, S = qt.spectrum_correlation_fft(taulist, corr)
# or directly over a frequency grid:
spec = qt.spectrum(H, np.linspace(0, 2, 200), c_ops, qt.destroy(N), qt.create(N))
```

## Steady state

```python
rho_ss = qt.steadystate(H, c_ops)                  # 'direct' by default
rho_ss = qt.steadystate(H, c_ops, method='eigen')  # 'svd', 'power' also
n_ss = qt.expect(qt.num(N), rho_ss)
```

## Matrix analysis

```python
evals, ekets = H.eigenstates()
E0, ground = H.groundstate()
U = (H * t).expm()          # matrix exponential
rho.logm(); rho.sqrtm()     # matrix log / square root
qt.partial_transpose(rho, [0, 1])   # PPT entanglement test input
```

## Physical-validity checks

```python
H.isherm                                   # Hermitian?
abs(psi.norm() - 1.0) < 1e-10              # normalized?
abs(rho.tr() - 1.0) < 1e-10 and all(rho.eigenenergies() >= -1e-12)  # valid rho?
qt.commutator(A, B).norm() < 1e-10         # commute?
```

## Random objects (testing / sampling)

```python
qt.rand_ket(N); qt.rand_dm(N); qt.rand_herm(N); qt.rand_unitary(N)
qt.rand_dm(N, rank=2)         # constrained rank (keyword may vary by version)
```
