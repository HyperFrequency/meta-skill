# Time Evolution and Dynamics Solvers

All solvers share the same skeleton: a Hamiltonian, an initial state, a
list of times, optional collapse operators, and optional `e_ops`
(observables to record). They return a `Result` object with `.states`
and/or `.expect`.

| Function      | Equation solved                         | State type        |
| ------------- | --------------------------------------- | ----------------- |
| `sesolve`     | Schrodinger (unitary)                   | ket               |
| `mesolve`     | Lindblad master equation                | density matrix    |
| `mcsolve`     | Quantum trajectories (Monte Carlo)      | ket ensemble      |
| `brmesolve`   | Bloch-Redfield master equation          | density matrix    |
| `fmmesolve`   | Floquet-Markov master equation          | density matrix    |
| `ssesolve`    | Stochastic Schrodinger equation         | ket ensemble      |
| `smesolve`    | Stochastic master equation              | density matrix    |

## sesolve — closed systems

```python
import numpy as np, qutip as qt
N = 10
psi0 = qt.basis(N, 0)
H = qt.num(N)
tlist = np.linspace(0, 10, 100)

result = qt.sesolve(H, psi0, tlist, e_ops=[qt.num(N)])
result.states       # list of kets (empty if only e_ops requested)
result.expect[0]    # <n>(t)
```

## mesolve — open systems

Add collapse (Lindblad jump) operators. Each `c_op` is `sqrt(rate) *
operator`.

```python
kappa = 0.1
c_ops = [np.sqrt(kappa) * qt.destroy(N)]
result = qt.mesolve(H, qt.coherent(N, 2.0), tlist, c_ops, e_ops=[qt.num(N)])
```

### Multiple / thermal dissipation channels

```python
kappa, gamma, nth = 0.1, 0.05, 0.5   # loss, dephasing, thermal occupation
c_ops = [
    np.sqrt(kappa * (1 + nth)) * qt.destroy(N),   # thermal decay
    np.sqrt(kappa * nth)       * qt.create(N),    # thermal excitation
    np.sqrt(gamma)             * qt.num(N),       # pure dephasing
]
```

`mesolve` accepts a ket or a density matrix as the initial state; it always
evolves the density matrix.

## Time-dependent Hamiltonians

Three coefficient formats, fastest first:

```python
# 1. String (compiled) — fastest
H = [qt.num(N), [qt.destroy(N) + qt.create(N), 'cos(w*t)']]
result = qt.sesolve(H, psi0, tlist, args={'w': 1.0})

# 2. Python callable  f(t, args) -> coefficient
def drive(t, args):
    return np.exp(-t/args['tau']) * np.sin(args['w'] * t)
H = [qt.num(N), [qt.destroy(N) + qt.create(N), drive]]
result = qt.sesolve(H, psi0, tlist, args={'w': 1.0, 'tau': 5.0})

# 3. QobjEvo — a reusable, updatable time-dependent operator
H_td = qt.QobjEvo([qt.num(N), [qt.destroy(N) + qt.create(N), drive]],
                  args={'w': 1.0, 'tau': 5.0})
```

Collapse operators can be time-dependent with the same list syntax:
`c_ops = [[qt.destroy(N), kappa_t]]` where `kappa_t(t, args)` returns the
coefficient.

## mcsolve — quantum trajectories

Averages `ntraj` stochastic wavefunction trajectories. Useful for quantum
jumps and photon-counting statistics, and it uses less memory than
`mesolve` for large systems.

```python
result = qt.mcsolve(H, qt.coherent(N, 2.0), tlist, c_ops,
                    e_ops=[qt.num(N)], ntraj=500)
result.expect[0]        # trajectory-averaged <n>(t)
```

Trajectory jump records (collapse times and which collapse operator fired)
are exposed on the result — the exact attribute names differ between QuTiP
v4 and v5 (`col_times` / `col_which` in v4). Confirm against
`qutip.__version__` and the result object's attributes before relying on
them. To retain per-trajectory states, request state storage in the solver
options.

## brmesolve — Bloch-Redfield (weak coupling)

Provide coupling operators paired with a bath power-spectrum callback
`S(w)`.

```python
def ohmic(w):
    return 0.1 * w if w >= 0 else 0.0
a_ops = [[qt.sigmax(), ohmic]]
result = qt.brmesolve(qt.sigmaz(), qt.basis(2, 0), tlist, a_ops,
                      e_ops=[qt.sigmaz(), qt.sigmax()])
```

## fmmesolve — Floquet (periodic driving)

For `H(t + T) = H(t)`. The Floquet-basis construction and `fmmesolve`
interface changed between v4 (`floquet_modes(...)` free functions) and v5
(the `FloquetBasis` class). See `advanced.md` for both; do not mix them.

## Stochastic solvers (continuous measurement)

`ssesolve` / `smesolve` model homodyne/heterodyne detection through
stochastic collapse operators `sc_ops`. The API for selecting the
measurement type (a `method`/`noise` argument) differs across versions;
check the docstring for your installed version.

## Propagators

```python
U = (-1j * H * t).expm()             # single unitary propagator
psi_t = U * psi0

U_list = qt.propagator(H, tlist, c_ops)   # (super)operator propagators
```

## Steady states

```python
rho_ss = qt.steadystate(H, c_ops)                 # default direct solve
rho_ss = qt.steadystate(H, c_ops, method='eigen') # also 'svd', 'power'
# verify:
assert (qt.liouvillian(H, c_ops) * qt.operator_to_vector(rho_ss)).norm() < 1e-10
```

## Correlation functions

```python
taulist = np.linspace(0, 10, 200)
corr = qt.correlation_2op_1t(H, rho0, taulist, c_ops,
                             qt.destroy(N), qt.create(N))
w, S = qt.spectrum_correlation_fft(taulist, corr)   # power spectrum
```

Higher-order (`correlation_3op_1t`, `correlation_4op_1t`) and two-time
(`correlation_2op_2t`) variants exist; see `analysis.md`.

## Solver options

In QuTiP 5 solver options are passed as a plain dict; the v4 `Options`
class still works as a compatibility shim. Common keys:

```python
options = {
    'nsteps': 10000,      # max internal integration steps
    'atol': 1e-8,         # absolute tolerance
    'rtol': 1e-6,         # relative tolerance
    'method': 'adams',    # 'bdf' for stiff problems
    'store_states': True,
    'store_final_state': True,
    'progress_bar': True,
}
result = qt.mesolve(H, psi0, tlist, c_ops, options=options)
```

If a solver reports it cannot reach a requested time, the fix is usually a
larger `nsteps`, `method='bdf'`, or slightly looser tolerances.

## Saving results

`Result` objects and `Qobj` can be serialized; the exact save/load helpers
(`qsave`/`qload`, `Result` I/O) vary by version — check the docstring
rather than assuming a signature.
