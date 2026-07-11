---
name: qutip
version: 0.1.0
description: >-
  Simulate open and closed quantum systems with QuTiP (Quantum Toolbox in
  Python): build states and operators as Qobj, evolve them with
  Schrodinger / Lindblad-master / Monte-Carlo / Bloch-Redfield / Floquet
  solvers, and compute entropy, fidelity, entanglement, correlation
  functions, steady states, and Wigner/Bloch visualizations. Use for
  open-system dynamics, decoherence, quantum optics, cavity and circuit
  QED, spin ensembles, and educational physics simulations where you model
  Hamiltonians and dissipation directly. NOT for gate-based
  quantum-computing circuits, algorithms, or hardware execution (use
  `qiskit`, `cirq`, or `pennylane`), and not for post-quantum cryptography
  (see `rust-pq-crypto`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause"
---

# QuTiP: Quantum Toolbox in Python

## Overview

QuTiP represents every quantum object — kets, bras, density matrices,
operators, and superoperators — as a single `Qobj` class carrying a
tensor-product dimension structure. From those objects you build
Hamiltonians and collapse operators, then hand them to a solver that
integrates the dynamics. The library covers both **closed** systems
(unitary Schrodinger evolution) and **open** systems (Lindblad master
equation, quantum trajectories, Bloch-Redfield, Floquet, and hierarchical
equations of motion), plus a full analysis and phase-space visualization
layer.

This skill is a router. It shows the minimal API to get moving and points
you to `references/` for exhaustive signatures, options, and worked
examples.

## When to Use This Skill

Reach for QuTiP when the task is **physics of a quantum system defined by a
Hamiltonian and dissipation channels**, for example:

- Open-system / dissipative dynamics: decoherence, damping, dephasing,
  thermalization modeled with Lindblad collapse operators.
- Quantum optics and cavity/circuit QED: Jaynes-Cummings, driven cavities,
  photon statistics, emission spectra.
- Master-equation and quantum-trajectory (Monte Carlo) simulations, weak
  coupling (Bloch-Redfield), periodic driving (Floquet), or strong /
  non-Markovian coupling (HEOM).
- Entanglement and information measures: concurrence, negativity, von
  Neumann entropy, fidelity, trace distance.
- Phase-space and state visualization: Bloch sphere, Wigner and Husimi-Q
  functions, Fock distributions, Hinton diagrams.
- Spin ensembles with permutational symmetry (PIQS / Dicke states).

## When NOT to Use This Skill

- **Gate-based quantum computing** — writing circuits, running algorithms,
  or executing on hardware/simulators. Use `qiskit`, `cirq`, or
  `pennylane`. (QuTiP's optional `qutip-qip` package adds gates for
  small-scale study, but it is not a hardware SDK.)
- **Post-quantum cryptography** — that is `rust-pq-crypto`, unrelated to
  physics simulation.
- **Very large Hilbert spaces** where dense/sparse state-vector integration
  will not fit in memory — tensor-network or specialized HPC libraries fit
  better.
- **Pure plotting** with no quantum content — use `matplotlib` or
  `scientific-visualization` directly.

## Installation

```bash
pip install qutip           # core library
pip install qutip-qip       # optional: gates, circuits (for study, not hardware)
```

QuTiP 5 is the current major line. A few APIs moved between v4 and v5
(solver options, the Floquet interface, HEOM import paths); the references
flag these where they matter. Check `qutip.__version__` if a signature does
not match.

## Quick Start

```python
import numpy as np
import qutip as qt

# A closed two-level system precessing under sigma_z.
psi0 = qt.basis(2, 0)                 # |0>
H = qt.sigmaz()
tlist = np.linspace(0, 10, 100)

result = qt.sesolve(H, psi0, tlist, e_ops=[qt.sigmaz()])
expectation_sigmaz = result.expect[0]   # <sigma_z>(t)
```

## Core Capabilities

### 1. Quantum objects, states, and operators

Build states (`basis`, `coherent`, `fock`, `thermal_dm`, `bell_state`),
operators (`destroy`, `create`, `num`, `sigmax/y/z`, `jmat`, `displace`,
`squeeze`), and composite systems (`tensor`, `qeye`, `ptrace`). Every
object exposes `.dag()`, `.tr()`, `.norm()`, `.eigenstates()`, and
`.expm()`.

```python
a = qt.destroy(10)                    # annihilation operator, N=10
psi = qt.coherent(10, alpha=2.0)      # coherent state |alpha>
n_avg = qt.expect(qt.num(10), psi)    # <n>
psi_AB = qt.tensor(qt.basis(2, 0), qt.basis(2, 1))   # |01>
```

See `references/core-concepts.md` for the full `Qobj` API, spin/angular-
momentum operators, tensor products, partial trace, Liouvillians, and
canonical Hamiltonians (Jaynes-Cummings, driven, spin chains).

### 2. Time evolution and dynamics

Pick the solver by the physics, not the syntax — the call signatures are
nearly identical.

| Solver       | Use it for                                             |
| ------------ | ------------------------------------------------------ |
| `sesolve`    | Pure states, unitary (closed) evolution — fastest      |
| `mesolve`    | Lindblad master equation; dissipation/decoherence      |
| `mcsolve`    | Quantum trajectories, quantum jumps, photon counting   |
| `brmesolve`  | Weak system-bath coupling (Bloch-Redfield, secular)    |
| `fmmesolve`  | Time-periodic Hamiltonians (Floquet-Markov)            |
| `ssesolve` / `smesolve` | Continuous measurement (homodyne/heterodyne) |

```python
# Open system: damped oscillator via a Lindblad collapse operator.
c_ops = [np.sqrt(0.1) * qt.destroy(10)]        # decay rate kappa = 0.1
result = qt.mesolve(H, psi0, tlist, c_ops, e_ops=[qt.num(10)])
```

See `references/solvers.md` for time-dependent Hamiltonians (string /
function / `QobjEvo`), multi-channel and time-dependent dissipation,
`mcsolve` trajectory data, propagators, steady states, and solver options.

### 3. Analysis and measurement

Compute expectation values, entropies, entanglement, distances, and
correlation functions on states or evolution results.

```python
S = qt.entropy_vn(rho)                # von Neumann entropy
C = qt.concurrence(rho)               # two-qubit entanglement
F = qt.fidelity(psi1, psi2)           # state fidelity in [0, 1]
rho_ss = qt.steadystate(H, c_ops)     # long-time steady state
```

See `references/analysis.md` for entropy/coherence measures, fidelity and
distance metrics, entanglement (negativity, logarithmic negativity),
projective/POVM measurement, two- to four-operator correlation functions,
emission spectra, and steady-state methods.

### 4. Visualization

```python
b = qt.Bloch(); b.add_states(psi); b.show()          # Bloch sphere
xvec = np.linspace(-5, 5, 200)
W = qt.wigner(psi, xvec, xvec)                        # Wigner function
qt.plot_fock_distribution(psi)                        # photon-number histogram
```

See `references/visualization.md` for Bloch animations, Wigner/Q-function
surface plots, Fock distributions over time, Hinton diagrams, and matrix
histograms.

### 5. Advanced methods

Floquet theory for periodic driving, HEOM for non-Markovian / strong
coupling, PIQS for permutationally-symmetric spin ensembles, stochastic
solvers, superoperator/Kraus channel algebra, Krylov methods for large
systems, and parallel parameter sweeps.

See `references/advanced.md` for the full treatment, including the v4-to-v5
differences in the Floquet and HEOM interfaces.

## Efficiency and Failure Modes

- **Truncate the Hilbert space** to the smallest dimension that still
  captures the dynamics, then confirm results are unchanged when you raise
  it. Fock-space truncation that is too small silently distorts high-photon
  dynamics.
- **Prefer `sesolve`** for pure states — it evolves a vector, not a density
  matrix, and is much faster than `mesolve`.
- **Use `e_ops`** to record only the observables you need instead of
  storing every state; storing all states of a large system is the usual
  cause of memory blowups.
- **String-format time dependence** (e.g. `'cos(w*t)'`) compiles and runs
  faster than Python-callback coefficients.
- **Stiff dynamics**: switch the integrator to the BDF method and raise
  `nsteps` if the solver reports it cannot reach a time point.
- **`mcsolve` convergence**: increase `ntraj` until the averaged
  expectation values and their reported standard deviation stabilize;
  trajectories parallelize across CPUs automatically.
- **Import errors on gates**: circuit gates live in the separate
  `qutip-qip` package, not core QuTiP.

Deeper troubleshooting lives alongside the relevant reference file.

## External Resources

- Documentation: https://qutip.readthedocs.io/
- Tutorials: https://qutip.org/qutip-tutorials/
- Source: https://github.com/qutip/qutip
