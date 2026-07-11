# Core Concepts: Qobj, States, Operators, Composition

Everything in QuTiP is a `Qobj`. It wraps a (usually sparse) matrix plus a
`dims` structure that records the tensor-product factorization of the
Hilbert space. Get this structure right and the rest of the library
composes cleanly; get it wrong and you will see dimension-mismatch errors.

## The Qobj class

```python
import qutip as qt

psi = qt.basis(2, 0)     # ket: ground state of a 2-level system
rho = qt.fock_dm(5, 2)   # density matrix for the n=2 Fock state
H = qt.sigmaz()          # operator: Pauli Z
```

Useful attributes and methods:

| Member          | Meaning                                             |
| --------------- | --------------------------------------------------- |
| `.dims`         | Nested list encoding subsystem dimensions           |
| `.shape`        | Matrix shape                                         |
| `.type`         | `'ket'`, `'bra'`, `'oper'`, or `'super'`             |
| `.isherm`       | True if Hermitian (checked, cached)                 |
| `.dag()`        | Hermitian conjugate                                 |
| `.tr()`         | Trace                                               |
| `.norm()`       | Norm (2-norm for kets, trace norm for operators)    |
| `.unit()`       | Normalized copy                                      |
| `.proj()`       | Projector `|psi><psi|` from a ket                   |
| `.expm()`       | Matrix exponential                                  |
| `.eigenstates()`| `(eigenvalues, eigenkets)`                          |
| `.eigenenergies()` | eigenvalues only                                 |
| `.groundstate()`| `(E0, ground_ket)`                                  |
| `.full()`       | Dense NumPy array                                   |

## States

### Fock, coherent, thermal

```python
N = 10                          # truncated Hilbert-space dimension
qt.basis(N, n)                  # Fock state |n>  (alias: qt.fock(N, n))
qt.coherent(N, alpha=1+1j)      # coherent state |alpha>
qt.coherent_dm(N, alpha=2)      # its density matrix
qt.thermal_dm(N, n_avg=2.0)     # thermal state, mean photon number n_avg
qt.maximally_mixed_dm(2)        # I/d
```

### Spin and multi-qubit

```python
qt.spin_state(1/2, 1/2)              # spin-up for spin-1/2
qt.spin_coherent(1/2, theta, phi)    # spin coherent state
qt.basis([2, 2, 2], [0, 1, 0])       # |010> for three qubits
qt.bell_state('00')                  # (|00> + |11>)/sqrt(2)
```

## Operators

### Bosonic ladder

```python
a = qt.destroy(N)   # annihilation
qt.create(N)        # creation (a.dag())
qt.num(N)           # number operator a.dag()*a
qt.displace(N, alpha)   # displacement D(alpha)
qt.squeeze(N, z)        # squeezing S(z)
```

### Pauli and angular momentum

```python
qt.sigmax(); qt.sigmay(); qt.sigmaz()
qt.sigmap()             # sigma_+ = (sigma_x + i sigma_y)/2
qt.sigmam()             # sigma_-
qt.jmat(j, 'x')         # J_x for arbitrary spin j; also 'y','z','+','-'
```

## Building composite systems

`tensor` combines subsystems; operators acting on one factor are padded
with identities on the others.

```python
H_total = qt.tensor(qt.sigmaz(), qt.sigmax())   # sigma_z (x) sigma_x
qt.qeye([2, 2])                                  # identity on two qubits
qt.tensor(qt.sigmaz(), qt.qeye(2), qt.qeye(2))   # sigma_z on qubit 0 of 3
```

### Partial trace

Reduce a composite state to a subsystem by tracing out the others. The
index argument names the subsystems to **keep**.

```python
rho = qt.bell_state('00').proj()
rho_A = qt.ptrace(rho, 0)     # keep subsystem 0, trace out 1
rho_AC = qt.ptrace(rho_ABC, [0, 2])   # keep 0 and 2
```

## Expectation values and variance

```python
qt.expect(qt.num(N), psi)                 # <n>; works on kets and rho
qt.expect([a, qt.create(N), qt.num(N)], psi)   # list -> list of values
qt.variance(qt.num(N), psi)               # <n^2> - <n>^2
```

## Superoperators and Liouvillians

Open-system generators live in the `'super'` type. The Lindblad generator
is assembled from a Hamiltonian and collapse operators.

```python
H = qt.num(N)
c_ops = [np.sqrt(0.1) * qt.destroy(N)]
L = qt.liouvillian(H, c_ops)

# Explicit Lindblad form, if you want the pieces:
L = -1j * (qt.spre(H) - qt.spost(H)) + qt.lindblad_dissipator(a, a)
```

Channel-representation conversions (`super`, `choi`, `kraus`, `chi`) are
covered in `advanced.md`.

## Quantum gates (optional, requires `qutip-qip`)

Gates are for small-scale study, not hardware execution — for circuits use
`qiskit`, `cirq`, or `pennylane`.

```python
from qutip_qip.operations import cnot, snot, rx, ry, rz, swap, toffoli
```

## Canonical Hamiltonians

### Jaynes-Cummings (cavity + two-level atom, RWA)

```python
N = 10
a = qt.tensor(qt.destroy(N), qt.qeye(2))   # cavity
sm = qt.tensor(qt.qeye(N), qt.sigmam())    # atom
wc, wa, g = 1.0, 1.0, 0.05
H = wc * a.dag()*a + wa * sm.dag()*sm + g * (a.dag()*sm + a*sm.dag())
```

### Driven (time-dependent)

```python
H0, H1 = qt.sigmaz(), qt.sigmax()
H = [H0, [H1, 'sin(w*t)']]      # list form; args={'w': 1.0} passed to solver
```

### Heisenberg spin chain

Build term by term over neighboring sites, padding each single-site
operator into the full tensor space with `qt.qeye(2)` on the other sites.
See `solvers.md` for how time-dependent list-Hamiltonians are consumed.

## Utilities

```python
qt.rand_ket(N); qt.rand_dm(N); qt.rand_herm(N); qt.rand_unitary(N)
qt.commutator(A, B)          # [A, B]
qt.commutator(A, B, 'anti')  # {A, B}
(-1j * H * t).expm()         # time-evolution operator U(t)
```
