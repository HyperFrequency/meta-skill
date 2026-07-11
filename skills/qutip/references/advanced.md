# Advanced Methods

Specialized regimes beyond the standard master-equation workflow. Several
of these interfaces changed between QuTiP v4 and v5 — the differences are
flagged inline. Check `qutip.__version__` when a signature does not match.

## Floquet theory (periodic driving)

For `H(t + T) = H(t)`. Floquet analysis diagonalizes the one-period
evolution, giving quasi-energies and stroboscopic modes.

**v5** organizes this around the `FloquetBasis` class, which computes the
modes and quasi-energies and transforms states between the lab and Floquet
frames. **v4** exposed free functions (`floquet_modes`,
`floquet_states`, `floquet_state_decomposition`,
`floquet_markov_mesolve`). Both drive dissipative dynamics through
`fmmesolve`. Do not mix the two APIs.

Conceptually, the workflow is:

1. Build the periodic Hamiltonian (list form with a `'cos(w*t)'`-style
   coefficient) and set the period `T = 2*pi/w_drive`.
2. Construct the Floquet basis / modes for one period.
3. Decompose the initial state into that basis.
4. Evolve with `fmmesolve`, supplying collapse operators and `T`/`args`.

Consult the docstring of the version you have for the exact constructor and
argument order.

## Hierarchical Equations of Motion (HEOM)

Numerically exact open-system dynamics for **non-Markovian, strong**
system-bath coupling, where Lindblad/Bloch-Redfield break down. You supply
the bath through its correlation-function decomposition.

Import path differs by version: **v5** uses `qutip.solver.heom`; **v4** used
`qutip.nonmarkov.heom`.

```python
# v5 import
from qutip.solver.heom import HEOMSolver, BosonicBath, DrudeLorentzBath

# General bosonic bath from an exponential expansion of the correlation function
bath = BosonicBath(Q, ck_real, vk_real)          # Q = coupling operator

# Or a Drude-Lorentz (overdamped Brownian) bath, common in condensed matter
bath = DrudeLorentzBath(Q, lam, gamma, T, Nk)    # reorg energy, cutoff, temp, Matsubara terms

hsolver = HEOMSolver(H_sys, [bath], max_depth=5)  # truncation depth of the hierarchy
result = hsolver.run(rho0, tlist)
```

Convergence is governed by two truncations: the hierarchy `max_depth` and
the number of Matsubara terms `Nk`. Raise each until the reduced dynamics
stop changing. Multiple baths are passed as a list.

## Permutational invariance (PIQS)

For ensembles of identical two-level systems, PIQS works in the
permutationally-symmetric subspace, so the state space grows polynomially
rather than as 2^N.

```python
from qutip.piqs import jspin, Dicke

Jz = jspin(N, 'z')            # collective spin operator ('x','y','z','+','-')
system = Dicke(N=N, emission=1.0, dephasing=0.5)   # collective Liouvillian
```

`qt.dicke(N, j, m)` constructs a Dicke state `|j, m>`. The `Dicke` object
builds the Liouvillian for collective emission/dephasing/pumping, which you
then evolve or solve for steady state.

## Bloch-Redfield with a thermal bath

`brmesolve` (see `solvers.md`) takes coupling operators paired with a bath
power spectrum `S(w)`. To include temperature, weight positive and negative
frequencies by the Bose-Einstein occupation so detailed balance holds:

```python
def thermal_spectrum(w):
    T = 1.0
    if abs(w) < 1e-10:
        return 0.1 * T
    n_th = 1.0 / (np.exp(abs(w) / T) - 1.0)
    return 0.1 * abs(w) * (n_th + (1.0 if w >= 0 else 0.0))

a_ops = [[qt.sigmax(), thermal_spectrum]]
```

## Superoperators and quantum channels

```python
L = qt.liouvillian(H, c_ops)
qt.spre(H); qt.spost(H); qt.sprepost(A, B)   # left / right / both multiplication

# representation conversions
qt.to_choi(L); qt.to_kraus(L); qt.to_super(choi)   # (v5 to_* helpers)
```

Build a channel from Kraus operators and apply it in vectorized form:

```python
# Depolarizing channel
p = 0.1
kraus = [np.sqrt(1 - 3*p/4)*qt.qeye(2), np.sqrt(p/4)*qt.sigmax(),
         np.sqrt(p/4)*qt.sigmay(), np.sqrt(p/4)*qt.sigmaz()]
E = qt.kraus_to_super(kraus)
rho_out = qt.vector_to_operator(E * qt.operator_to_vector(rho_in))
```

Amplitude damping (T1) and phase damping (T2) have standard two-Kraus
forms you can assemble the same way. Function names for the super/choi/kraus
conversions were reorganized in v5 (`to_super`, `to_choi`, `to_kraus`);
confirm the exact helper in your version.

## Stochastic solvers with continuous measurement

`ssesolve` / `smesolve` unravel the dynamics under continuous homodyne or
heterodyne detection via stochastic collapse operators `sc_ops`. The keyword
selecting the detection scheme has changed across versions — read the
docstring rather than hardcoding a `noise`/`method` value.

## Krylov subspace method

For a single large-dimension closed system, `qt.krylovsolve` propagates
without forming dense propagators:

```python
result = qt.krylovsolve(H, psi0, tlist, krylov_dim=10, e_ops=[qt.num(N)])
```

## Parallel parameter sweeps

Sweep a parameter across trajectories or independent simulations with the
built-in map helpers (they distribute across CPUs):

```python
from qutip import parallel_map, serial_map     # serial_map for debugging

def run(gamma):
    c_ops = [np.sqrt(gamma) * qt.destroy(N)]
    return qt.mesolve(H, psi0, tlist, c_ops, e_ops=[qt.num(N)]).expect[0]

results = parallel_map(run, np.linspace(0, 1, 20))
```

## Performance checklist

1. Truncate the Hilbert space; verify results are stable as you raise it.
2. `sesolve` (state vector) beats `mesolve` (density matrix) for pure
   states.
3. String time-dependence compiles and outruns Python callbacks.
4. Record only the observables you need via `e_ops`; avoid `store_states`
   for large systems.
5. `mcsolve` trades exactness for lower memory and parallel scaling — tune
   `ntraj` for convergence.
6. Krylov methods for very large single-system propagation.
7. For non-Markovian/strong coupling, HEOM is the correct tool but is the
   most expensive — budget both `max_depth` and `Nk`.
