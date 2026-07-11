# Visualization

Draw circuits, plot measurement results, and visualize quantum states. Requires
the visualization extra:

```bash
uv pip install "qiskit[visualization]" matplotlib
uv pip install pylatexenc      # only for the 'latex' circuit drawer
```

## Circuit drawings

```python
print(qc.draw())                     # ASCII text (default)
print(qc.draw("text", fold=-1))      # never wrap long circuits
fig = qc.draw("mpl")                 # matplotlib Figure
qc.draw("latex")                     # LaTeX (needs pylatexenc)
latex_src = qc.draw("latex_source")  # raw LaTeX string
```

Common `mpl` options:

```python
qc.draw("mpl", reverse_bits=True)    # flip qubit ordering
qc.draw("mpl", fold=20)              # wrap at 20 columns
qc.draw("mpl", idle_wires=False)     # hide unused wires
qc.draw("mpl", style="iqp")          # IBM Quantum styling; "bw" for grayscale
```

Custom gate colors:

```python
style = {"displaycolor": {
    "h":  ("#FA74A6", "#000000"),
    "cx": ("#A8D0DB", "#000000"),
}}
qc.draw("mpl", style=style)
```

## Measurement histograms

```python
from qiskit.visualization import plot_histogram

counts = result[0].data.meas.get_counts()
plot_histogram(counts)

# overlay several runs
plot_histogram([counts_sim, counts_hw], legend=["Simulator", "Hardware"])

# options
plot_histogram(counts, sort="value", bar_labels=True, figsize=(12, 6))
```

## Quantum-state visualization

Build a state from a measurement-free circuit, then plot it. States grow as 2^n,
so these are for small circuits / debugging.

```python
from qiskit.quantum_info import Statevector, DensityMatrix
from qiskit.visualization import (
    plot_bloch_multivector, plot_state_city,
    plot_state_qsphere, plot_state_hinton,
)

qc = QuantumCircuit(2); qc.h(0); qc.cx(0, 1)   # NO measurements
state = Statevector(qc)

plot_bloch_multivector(state)   # per-qubit Bloch spheres
plot_state_city(state)          # real/imag amplitude "city"
plot_state_qsphere(state)       # amplitude + phase on a sphere
plot_state_hinton(state)        # amplitude magnitudes as a Hinton grid
plot_state_city(DensityMatrix(qc))   # density matrix also accepted
```

Single Bloch vector:

```python
from qiskit.visualization import plot_bloch_vector
plot_bloch_vector([0, 1, 0])   # Bloch coordinates [x, y, z]
```

## Backend topology and errors

```python
from qiskit.visualization import plot_gate_map, plot_error_map, plot_circuit_layout

plot_gate_map(backend)                       # qubit connectivity
plot_error_map(backend)                      # per-qubit / per-link error rates
plot_circuit_layout(isa_circuit, backend)    # where a transpiled circuit landed
```

## Saving figures

Each helper returns a matplotlib `Figure`:

```python
fig = qc.draw("mpl")
fig.savefig("circuit.png", dpi=300, bbox_inches="tight")
fig.savefig("circuit.pdf", bbox_inches="tight")   # vector
fig.savefig("circuit.svg", bbox_inches="tight")

plot_histogram(counts).savefig("results.png", dpi=300, bbox_inches="tight")
```

Publication defaults:

```python
import matplotlib.pyplot as plt
plt.rcParams.update({"figure.dpi": 300, "font.size": 12})
qc.draw("mpl", style="iqp").savefig("fig.png", dpi=600, bbox_inches="tight")
```

## Troubleshooting

- **`No module named 'matplotlib'`** — `uv pip install matplotlib`.
- **LaTeX drawer fails** — `uv pip install pylatexenc`.
- **Circuit too large to render** — fold (`fold=50`) or save to file at lower dpi
  instead of displaying inline.
- **No plot in Jupyter** — run `%matplotlib inline` at the top of the notebook.

For data plots beyond these built-ins (custom convergence curves, styled charts),
use `matplotlib` / `seaborn` directly.
