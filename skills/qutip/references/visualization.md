# Visualization

QuTiP's plotting helpers build on Matplotlib. They return `(fig, ax)` (or
draw onto axes you pass in) so you can compose them into larger figures.

## Bloch sphere

```python
import qutip as qt
import matplotlib.pyplot as plt

b = qt.Bloch()
b.add_states((qt.basis(2, 0) + qt.basis(2, 1)).unit())   # a state
b.add_vectors([1, 0, 0])                                 # a raw vector
b.add_points([[0, 1, 0], [0, -1, 0]])                    # points
b.show()
```

Appearance controls: `b.sphere_color`, `b.sphere_alpha`, `b.frame_alpha`,
`b.vector_color`, `b.point_color`, `b.point_marker`, `b.font_size`,
`b.view = [azimuth, elevation]`. Save with `b.save('bloch.png')`.

### Animating an evolution

Drive the sphere from the `.states` of a solver result with Matplotlib's
`FuncAnimation`, clearing and redrawing each frame:

```python
from matplotlib.animation import FuncAnimation

states = result.states
b = qt.Bloch()

def animate(i):
    b.clear()
    b.add_states(states[i])
    b.make_sphere()
    return b.axes

anim = FuncAnimation(b.fig, animate, frames=len(states), interval=50)
plt.show()
```

## Wigner function (phase space)

The Wigner quasi-probability can go negative — that negativity is the
signature of non-classical states.

```python
import numpy as np
xvec = np.linspace(-5, 5, 200)
W = qt.wigner(psi, xvec, xvec)

fig, ax = plt.subplots(figsize=(6, 6))
cont = ax.contourf(xvec, xvec, W, 100, cmap='RdBu')
ax.set_xlabel('Re(alpha)'); ax.set_ylabel('Im(alpha)')
plt.colorbar(cont, ax=ax)
```

Use `qt.wigner_cmap(W)` for a colormap that emphasizes the negative
regions. For a 3D surface, feed `np.meshgrid(xvec, xvec)` and `W` to
`ax.plot_surface` on a 3D axis.

## Husimi Q-function

Always non-negative, a smoothed phase-space distribution.

```python
Q = qt.qfunc(psi, xvec, xvec)
```

For evaluating the Q-function of one state at many grids, the batched
`qt.QFunc(rho)` object is more efficient than repeated `qfunc` calls.

## Fock-state (photon-number) distribution

```python
qt.plot_fock_distribution(qt.coherent(20, 2))
```

Pass `fig=`/`ax=` to place several distributions side by side, e.g. to
contrast coherent vs thermal vs Fock states, or to show the distribution at
successive times from `result.states`.

## Matrix visualization

```python
qt.hinton(rho)                       # weighted-square Hinton diagram
qt.matrix_histogram(H.full())        # 3D bars of matrix elements
```

`matrix_histogram` accepts a `bar_type` selecting what the bar height
encodes (real, imaginary, absolute value, or phase) and `xlabels`/`ylabels`
for basis labels. Plot real and imaginary parts as adjacent subplots to see
a complex operator fully.

## Energy-level diagrams

There is no single built-in; draw eigenenergies as horizontal lines:

```python
evals = H.eigenenergies()
fig, ax = plt.subplots()
for i, E in enumerate(evals[:10]):
    ax.hlines(E, 0, 1, linewidth=2)
    ax.text(1.1, E, f'|{i}>', va='center')
ax.set_ylabel('Energy'); ax.set_xticks([])
```

## Expectation values and correlations over time

Solver results are plain arrays — plot them directly.

```python
result = qt.mesolve(H, psi0, tlist, c_ops, e_ops=[qt.num(N)])
plt.plot(tlist, result.expect[0]); plt.xlabel('Time'); plt.ylabel('<n>')

# correlation function and its spectrum
corr = qt.correlation_2op_1t(H, rho0, taulist, c_ops, qt.create(N), qt.destroy(N))
plt.plot(taulist, np.real(corr))
w, S = qt.spectrum_correlation_fft(taulist, corr)
plt.plot(w, S)
```

## Saving figures

```python
fig.savefig('plot.png', dpi=300, bbox_inches='tight')
fig.savefig('plot.pdf', bbox_inches='tight')
```

For general (non-quantum) plotting concerns, defer to `matplotlib` or
`scientific-visualization`.
