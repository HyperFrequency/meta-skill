# Quantum Chemistry

The `qml.qchem` module turns a molecule into a qubit Hamiltonian you can minimize with VQE, plus
chemistry-aware ansatze and mappings.

## Build a molecular Hamiltonian

```python
import pennylane as qml
from pennylane import qchem
from pennylane import numpy as np

symbols = ["H", "H"]
coords = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.74])  # flat (x,y,z) per atom, Angstrom

H, n_qubits = qchem.molecular_hamiltonian(
    symbols, coords,
    charge=0,
    mult=1,             # spin multiplicity
    basis="sto-3g",     # sto-3g (minimal) -> 6-31g -> cc-pvdz (larger, costlier)
    mapping="jordan_wigner",   # or "bravyi_kitaev", "parity"
)
```

`molecular_hamiltonian` returns the qubit-space Hamiltonian and the qubit count. Larger basis
sets and more atoms mean more qubits and more Hamiltonian terms — start with `sto-3g`.

**Active space** — reduce qubits by restricting to chemically relevant orbitals:

```python
H, n_qubits = qchem.molecular_hamiltonian(
    symbols, coords, active_electrons=2, active_orbitals=2)
```

## VQE ground state

```python
dev = qml.device("default.qubit", wires=n_qubits)
hf = qchem.hf_state(electrons=2, orbitals=n_qubits)   # Hartree-Fock occupation, e.g. [1,1,0,0]

def ansatz(params, wires):
    qml.BasisState(hf, wires=wires)
    for i in range(len(wires)):
        qml.RY(params[i], wires=i)
    for i in range(len(wires) - 1):
        qml.CNOT(wires=[i, i + 1])

@qml.qnode(dev)
def energy(params):
    ansatz(params, wires=range(n_qubits))
    return qml.expval(H)

opt = qml.GradientDescentOptimizer(stepsize=0.4)
params = np.random.normal(0, np.pi, n_qubits, requires_grad=True)
for n in range(100):
    params, e = opt.step_and_cost(energy, params)
    if n % 20 == 0:
        print(f"step {n}: E = {e:.8f} Ha")
```

## UCCSD ansatz (chemically motivated)

Unitary Coupled Cluster with Singles and Doubles is the standard accuracy-oriented ansatz.

```python
singles, doubles = qchem.excitations(electrons=2, orbitals=n_qubits)
s_wires, d_wires = qchem.excitations_to_wires(singles, doubles)

@qml.qnode(dev)
def uccsd_energy(params):
    qml.UCCSD(params, wires=range(n_qubits),
              s_wires=s_wires, d_wires=d_wires, init_state=hf)
    return qml.expval(H)

params = np.zeros(len(singles) + len(doubles), requires_grad=True)
opt = qml.AdamOptimizer(stepsize=0.1)
for _ in range(100):
    params, e = opt.step_and_cost(uccsd_energy, params)
```

For very small molecules, the primitive excitation gates `qml.SingleExcitation` and
`qml.DoubleExcitation` (Givens rotations) are a lighter alternative to the full `UCCSD` template.

## Fermion-to-qubit mappings

Pass `mapping=` to `molecular_hamiltonian`, or map fermionic operators directly:

```python
from pennylane import fermi
op = fermi.FermiC(0) * fermi.FermiA(1)     # a_0^dagger a_1
qubit_op = qml.jordan_wigner(op)           # also: qml.bravyi_kitaev, qml.parity_transform
```

`bravyi_kitaev` and `parity` often reduce circuit depth or qubit count relative to
`jordan_wigner` for some systems — worth benchmarking.

## Custom Hamiltonians

```python
H = 0.2 * qml.PauliZ(0) - 0.8 * (qml.PauliZ(0) @ qml.PauliZ(1)) + 0.5 * (qml.PauliX(0) @ qml.PauliX(1))
# or explicitly:
H = qml.Hamiltonian([0.2, -0.8, 0.5],
                    [qml.PauliZ(0), qml.PauliZ(0) @ qml.PauliZ(1), qml.PauliX(0) @ qml.PauliX(1)])
```

## Bond dissociation curve

Sweep the bond length, rebuild the Hamiltonian, and run VQE at each point:

```python
energies = []
for d in np.linspace(0.5, 3.0, 20):
    coords = np.array([0.0, 0.0, 0.0, 0.0, 0.0, d])
    H, nq = qchem.molecular_hamiltonian(["H", "H"], coords, basis="sto-3g")
    energies.append(run_vqe(H, nq))   # your VQE routine returning the converged energy
```

## Molecular properties

```python
# Dipole moment operator (returns a list of observables, one per Cartesian axis)
dipole_ops = qchem.dipole_moment(qchem.Molecule(symbols, coords))()
# Particle number, useful as a sanity check that the ansatz conserves electrons
N = qml.qchem.particle_number(n_qubits)
```

Some property helpers changed signatures across PennyLane versions (function vs. `Molecule`
object); confirm the exact call against the installed `qml.qchem` docs.

## Practices

1. Start with `sto-3g` and small active spaces; upgrade the basis only for production accuracy.
2. Always initialize VQE from the Hartree-Fock state (`qchem.hf_state`).
3. Use UCCSD (or excitation gates) when you need chemical accuracy; hardware-efficient ansatze
   are cheaper but risk barren plateaus and miss correlation.
4. Validate energies against a classical reference (FCI/CCSD) on small molecules before trusting
   novel systems.
5. Report energies in Hartree (Ha); multiply differences by 627.5 for kcal/mol.
